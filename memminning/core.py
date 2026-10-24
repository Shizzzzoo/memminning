"""No GTK dependency: discovery, policy, durable transactions and restoration."""
from __future__ import annotations

import contextlib
import dataclasses
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
import uuid
from . import __version__

ROOT = Path(__file__).resolve().parent.parent
STATE = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'memminning'
SELF_UUID = 'memminning@local'
# Positive allowlist: unknown services are never actionable.
OPTIONAL_SERVICES = {
    'tracker-miner-fs-3.service', 'tracker-extract-3.service',
    'localsearch-3.service', 'localsearch-extractor-3.service',
    'baloo_file.service', 'kde-baloo.service', 'tumblerd.service',
    'rygel.service',
}
PROTECTED_EXT = ('memminning', 'accessib', 'screen-reader', 'screenreader',
                 'screen-lock', 'screenlock', 'lockscreen', 'lock-screen', 'osk', 'keyboard', 'auth')
log = logging.getLogger('memminning')


def setup_logging():
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(STATE, 0o700)
    if not log.handlers:
        handler = RotatingFileHandler(STATE / 'events.log', maxBytes=512_000, backupCount=3)
        os.chmod(STATE / 'events.log', 0o600)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        log.addHandler(handler)
        log.setLevel(logging.INFO)


class OperationError(RuntimeError):
    pass


def run(args, timeout=20):
    """Argument arrays only; never execute a shell or request root."""
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=timeout,
                                env={**os.environ, 'LC_ALL': 'C', 'SYSTEMD_COLORS': '0'})
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise OperationError(f'{args[0]} unavailable or timed out: {exc}') from exc
    if result.returncode:
        raise OperationError(f'{args[0]}: {(result.stderr or result.stdout).strip()[:800]}')
    return result.stdout


def properties(text):
    return dict(line.split('=', 1) for line in text.splitlines() if '=' in line)


def memory():
    values = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        values[key] = int(value.split()[0]) * 1024
    return values


def mib(value):
    return f'{value / 1048576:,.0f} MiB' if value is not None else 'Not attributable'


@dataclasses.dataclass
class Item:
    id: str
    name: str
    kind: str
    detail: str
    memory: int | None = None
    actions: tuple[str, ...] = ()
    risk: str = 'Inventory only'


@dataclasses.dataclass
class Snapshot:
    items: list[Item]
    warnings: list[str]
    memory: dict
    environment: dict


class Backend:
    def extensions(self):
        return set(run(['gnome-extensions', 'list', '--enabled']).splitlines())

    def extension(self, target, enabled):
        run(['gnome-extensions', 'enable' if enabled else 'disable', target])
        if (target in self.extensions()) != enabled:
            raise OperationError('GNOME did not confirm the extension setting change')

    def service(self, target):
        return properties(run(['systemctl', '--user', 'show', target,
            '--property=Id,LoadState,ActiveState,MemoryCurrent,MemoryHigh,RequiredBy,BoundBy,RefuseManualStop,TriggeredBy,ControlGroup']))

    def stop(self, target):
        run(['systemctl', '--user', 'stop', target])
        if self.service(target).get('ActiveState') not in ('inactive', 'failed'):
            raise OperationError(f'{target} did not stop (it may have been reactivated)')

    def start(self, target):
        run(['systemctl', '--user', 'start', target])
        if self.service(target).get('ActiveState') != 'active':
            raise OperationError(f'{target} did not become active')

    def limit(self, target, value):
        run(['systemctl', '--user', 'set-property', '--runtime', target, f'MemoryHigh={value}'])
        if self.service(target).get('MemoryHigh') != str(value):
            raise OperationError(f'{target} did not confirm its memory limit')

    def boot(self):
        return Path('/proc/sys/kernel/random/boot_id').read_text().strip()

    def arm(self, session, seconds):
        args = ['systemd-run', '--user', '--quiet', '--collect', f'--unit=memminning-restore-{session}',
                f'--on-active={seconds}s', '--timer-property=AccuracySec=1s',
                '--timer-property=RemainAfterElapse=no',
                '--property=Restart=on-failure', '--property=RestartSec=30s',
                '--property=Type=exec', '--expand-environment=no',
                f'--setenv=XDG_STATE_HOME={STATE.parent}',
                '/usr/bin/python3', str(ROOT / 'run.py'), '--restore-session', session]
        run(args)
        run(['systemctl', '--user', 'is-active', f'memminning-restore-{session}.timer'])


def service_reason(p):
    if p.get('LoadState') != 'loaded' or p.get('ActiveState') != 'active':
        return 'Service must be loaded and active'
    if p.get('Id') not in OPTIONAL_SERVICES:
        return 'Service identity is outside the allowlist'
    if p.get('RequiredBy') or p.get('BoundBy') or p.get('RefuseManualStop') == 'yes':
        return 'Dependency or stop protection prevents changes'
    if p.get('TriggeredBy'):
        return 'Socket/timer activation may immediately restart this service'
    return ''


def extension_allowed(target):
    return (bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.@+\-]*', target)) and
            not any(token in target.lower() for token in PROTECTED_EXT))


def scan(backend=None):
    backend = backend or Backend()
    items, warnings = [], []
    mem = memory()
    env = {'os': platform.freedesktop_os_release().get('PRETTY_NAME', platform.system()),
           'kernel': platform.release(), 'desktop': os.getenv('XDG_CURRENT_DESKTOP', 'unknown'),
           'session': os.getenv('XDG_SESSION_TYPE', 'unknown'), 'version': __version__}
    # All readable processes, without collecting private command-line arguments.
    denied = 0
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            s = properties((proc / 'status').read_text().replace(':\t', '='))
            rss = int(s.get('VmRSS', '0 kB').split()[0]) * 1024
            uid = int(s['Uid'].split()[0])
            items.append(Item(f'pid:{proc.name}', s.get('Name', proc.name), 'Processes',
                f'PID {proc.name} · UID {uid} · RSS includes shared pages; not additive. '
                'Close applications normally after saving your work.', rss))
        except (OSError, ValueError, KeyError):
            denied += 1
    if denied:
        warnings.append(f'{denied} processes exited or could not be read during scanning.')
    for user in (True, False):
        try:
            command = ['systemctl'] + (['--user'] if user else [])
            entries = json.loads(run(command + ['list-units', '--type=service', '--all', '--output=json']))
            for entry in entries:
                target = entry['unit']
                active = entry.get('active', 'unknown')
                actions, amount = (), None
                detail = f'{target} · {active}'
                if user and target in OPTIONAL_SERVICES and active == 'active':
                    p = backend.service(target)
                    reason = service_reason(p)
                    detail += ' · ' + (reason or 'Optional indexing/media service; search or sharing will pause.')
                    if not reason:
                        actions = ('stop',)
                        if Path('/sys/fs/cgroup/cgroup.controllers').exists() and p.get('MemoryHigh'):
                            actions += ('limit',)
                    raw = p.get('MemoryCurrent', '')
                    amount = int(raw) if raw.isdigit() and int(raw) < 2**63 else None
                items.append(Item(f'user:{target}' if user else f'system:{target}',
                    entry.get('description') or target, 'User services' if user else 'System services',
                    detail, amount, actions, 'Review required' if actions else 'Protected / inventory only'))
        except (OperationError, ValueError, KeyError) as exc:
            warnings.append(f'{"User" if user else "System"} service scan incomplete: {exc}')
    try:
        enabled = backend.extensions()
        installed = set(run(['gnome-extensions', 'list']).splitlines())
        for target in sorted(installed):
            active = target in enabled
            allowed = active and extension_allowed(target) and 'GNOME' in env['desktop'].upper()
            items.append(Item(f'gnome:{target}', target, 'GNOME extensions',
                f'{"Enabled" if active else "Disabled"} · Shares GNOME Shell memory; per-extension RAM is unavailable. '
                'Disabling may change your desktop controls or interrupt extension features.',
                actions=('disable',) if allowed else (), risk='Review required' if allowed else 'Protected / inactive'))
    except OperationError as exc:
        warnings.append(f'Live GNOME extension state unavailable: {exc}')
    # Known plugin stores: inventory only, including installed but inactive plugins.
    home = Path.home()
    data = Path(os.getenv('XDG_DATA_HOME', home / '.local/share'))
    config = Path(os.getenv('XDG_CONFIG_HOME', home / '.config'))
    stores = [
        ('GNOME files', data / 'gnome-shell/extensions', '*'),
        ('GNOME files', Path('/usr/share/gnome-shell/extensions'), '*'),
        ('KDE plugins', data / 'plasma/plasmoids', '*'),
        ('KDE plugins', Path('/usr/share/plasma/plasmoids'), '*'),
        ('KDE plugins', data / 'kwin/scripts', '*'),
        ('KDE plugins', Path('/usr/share/kwin/scripts'), '*'),
        ('Cinnamon plugins', data / 'cinnamon/applets', '*'),
        ('Cinnamon plugins', data / 'cinnamon/extensions', '*'),
        ('Cinnamon plugins', Path('/usr/share/cinnamon/applets'), '*'),
        ('Cinnamon plugins', Path('/usr/share/cinnamon/extensions'), '*'),
        ('XFCE plugins', Path('/usr/share/xfce4/panel/plugins'), '*.desktop'),
        ('Autostart', config / 'autostart', '*.desktop'),
        ('Autostart', Path('/etc/xdg/autostart'), '*.desktop'),
        ('Editor extensions', home / '.vscode/extensions', '*/package.json'),
        ('Editor extensions', home / '.vscode-oss/extensions', '*/package.json'),
        ('Editor extensions', home / '.cursor/extensions', '*/package.json'),
    ]
    for browser in ('chromium', 'google-chrome', 'BraveSoftware/Brave-Browser', 'microsoft-edge', 'vivaldi'):
        stores.append(('Browser extensions', config / browser, '*/Extensions/*'))
    stores += [('Browser extensions', home / '.mozilla/firefox', '*/extensions/*'),
               ('Browser extensions', home / '.var/app/org.mozilla.firefox/.mozilla/firefox', '*/extensions/*'),
               ('Browser extensions', home / '.var/app/org.chromium.Chromium/config/chromium', '*/Extensions/*')]
    for kind, base, pattern in stores:
        try:
            for path in sorted(base.glob(pattern)):
                items.append(Item(f'file:{path}', path.parent.name if path.name == 'package.json' else path.name,
                    kind, f'{path} · Installed artifact; runtime state/RAM unknown. Manage through its host application.'))
        except OSError as exc:
            warnings.append(f'Could not inspect {base}: {exc}')
    for executable, args, kind in [('flatpak', ['list', '--columns=application,name'], 'Flatpak apps'),
                                   ('snap', ['list'], 'Snap apps')]:
        import shutil
        if shutil.which(executable):
            try:
                for line in run([executable, *args], timeout=10).splitlines():
                    items.append(Item(f'{executable}:{line.split()[0]}', line, kind,
                                      'Installed application; its live memory is included in Processes.'))
            except OperationError as exc:
                warnings.append(str(exc))
    for key, note in [('Cached', 'Reclaimable file cache: Linux manages this automatically.'),
                      ('SReclaimable', 'Reclaimable kernel objects; not additional application RAM.'),
                      ('SUnreclaim', 'Kernel memory; protected.'),
                      ('Shmem', 'Shared memory/tmpfs: may contain active application data.'),
                      ('SwapFree', 'Free swap capacity, not physical RAM.')]:
        items.append(Item(f'memory:{key}', key, 'Memory overview', note, mem.get(key)))
    warnings.append('Coverage is best effort: readable processes, systemd services, known desktop/browser/editor plugin stores, '
                    'autostart and installed sandbox apps. Custom profiles, other users’ private files, containers and GPU VRAM '
                    'are not exhaustively inspected. Installed plugins are not necessarily running; memory rows overlap.')
    log.info('Scan completed: %d entries, %d notices', len(items), len(warnings))
    return Snapshot(items, warnings, mem, env)


class Store:
    def __init__(self, directory=STATE):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.directory, 0o700)
        self.path = self.directory / 'session.json'

    @contextlib.contextmanager
    def lock(self):
        with (self.directory / 'session.lock').open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            yield

    def read(self):
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text())
            if data.get('schema') != 1 or not isinstance(data.get('actions'), list):
                raise ValueError('unsupported journal format')
            return data
        except (ValueError, OSError) as exc:
            raise OperationError(f'Cannot read recovery journal; preserve it for diagnosis: {exc}') from exc

    def write(self, state):
        tmp = self.path.with_suffix('.tmp')
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as handle:
            json.dump(state, handle, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, self.path)
        directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)


class Engine:
    def __init__(self, backend=None, store=None):
        self.backend = backend or Backend()
        self.store = store or Store()

    def prepare(self, choices, minutes, limit_mib=256):
        if not 1 <= minutes <= 480:
            raise OperationError('Duration must be 1–480 minutes')
        if not 64 <= limit_mib <= 16384:
            raise OperationError('Soft memory limit must be 64–16384 MiB')
        if not choices:
            raise OperationError('Select at least one action')
        actions, seen = [], set()
        for item_id, action in choices:
            if item_id in seen:
                raise OperationError('Only one action per target is allowed')
            seen.add(item_id)
            kind, target = item_id.split(':', 1)
            record = {'kind': kind, 'target': target, 'action': action, 'status': 'planned'}
            if kind == 'gnome' and action == 'disable' and extension_allowed(target):
                if target not in self.backend.extensions():
                    raise OperationError(f'{target} is no longer enabled; rescan')
                record['before'] = True
            elif kind == 'user' and target in OPTIONAL_SERVICES and action in ('stop', 'limit'):
                state = self.backend.service(target)
                reason = service_reason(state)
                if reason:
                    raise OperationError(f'{target}: {reason}')
                if action == 'limit':
                    value = state.get('MemoryHigh', '')
                    if not (value == 'infinity' or value.isdigit()):
                        raise OperationError(f'{target}: MemoryHigh is unavailable')
                    record['before'] = value
                    record['after'] = str(limit_mib * 1048576)
                    if value.isdigit() and int(value) <= int(record['after']):
                        raise OperationError(f'{target} already has an equal or tighter limit')
                else:
                    record['before'] = 'active'
            else:
                raise OperationError(f'Protected or unsupported target: {item_id}')
            actions.append(record)
        return actions

    def begin(self, choices, minutes, limit_mib=256):
        with self.store.lock():
            old = self.store.read()
            if old and old['status'] != 'restored':
                raise OperationError('An existing session needs restoration first')
            actions = self.prepare(choices, minutes, limit_mib)
            state = {'schema': 1, 'id': uuid.uuid4().hex, 'boot': self.backend.boot(),
                     'status': 'arming', 'deadline': time.time() + minutes * 60,
                     'actions': actions, 'started': time.time()}
            self.store.write(state)
            try:
                # Restoration must exist before the first desktop mutation.
                self.backend.arm(state['id'], minutes * 60)
                state['status'] = 'active'
                self.store.write(state)
                for record in actions:
                    # Write intent before every action, covering crashes after the mutation.
                    target = record['target']
                    # Revalidate at execution time; discovery is never authorization.
                    self.prepare([(f"{record['kind']}:{target}", record['action'])], minutes, limit_mib)
                    record['status'] = 'pending'
                    self.store.write(state)
                    if record['action'] == 'disable':
                        self.backend.extension(target, False)
                    elif record['action'] == 'stop':
                        self.backend.stop(target)
                    else:
                        # Do not replace a limit changed since the review/preflight.
                        if self.backend.service(target).get('MemoryHigh') != record['before']:
                            record['status'] = 'planned'
                            self.store.write(state)
                            raise OperationError('Memory limit changed during preflight; rescan')
                        self.backend.limit(target, record['after'])
                    record['status'] = 'applied'
                    self.store.write(state)
                    log.info('Applied %s to %s', record['action'], target)
            except Exception:
                log.exception('Session failed; attempting rollback')
                self._restore(state)
                raise
            state['activation_complete'] = True
            self.store.write(state)
            return state

    def restore(self, session=None):
        with self.store.lock():
            state = self.store.read()
            if not state or state['status'] == 'restored' or (session and state['id'] != session):
                return []
            return self._restore(state)

    def _restore(self, state):
        errors = []
        same_boot = state['boot'] == self.backend.boot()
        state['status'] = 'restoring'
        self.store.write(state)
        for record in reversed(state['actions']):
            if record['status'] not in ('pending', 'applied', 'error'):
                continue
            target = record['target']
            try:
                # Journal targets are validated too; never trust arbitrary files as commands.
                if record['kind'] == 'gnome' and record['action'] == 'disable' and extension_allowed(target):
                    if target not in self.backend.extensions():
                        self.backend.extension(target, True)
                elif record['kind'] == 'user' and target in OPTIONAL_SERVICES:
                    if same_boot:
                        current = self.backend.service(target)
                        if record['action'] == 'stop':
                            if current.get('ActiveState') == 'inactive':
                                self.backend.start(target)
                            elif current.get('ActiveState') != 'active':
                                raise OperationError('Service is in an unexpected state; inspect it before retrying')
                        elif record['action'] == 'limit':
                            value = current.get('MemoryHigh')
                            before = record['before']
                            if not (before == 'infinity' or str(before).isdigit()):
                                raise OperationError('Invalid saved MemoryHigh value')
                            if value == record['after']:
                                self.backend.limit(target, before)
                            elif value != before:
                                raise OperationError('MemoryHigh changed outside Memminning; resolve the conflict and retry')
                        else:
                            raise OperationError('Unsupported journal action')
                    # Runtime limits disappear at reboot; never start services from a previous boot.
                else:
                    raise OperationError('Journal contains a protected or unsupported target')
                record['status'] = 'restored'
                record.pop('error', None)
                log.info('Restored %s', target)
            except Exception as exc:
                record['status'] = 'error'
                record['error'] = str(exc)
                errors.append(f'{target}: {exc}')
                log.exception('Restoration failed for %s', target)
            self.store.write(state)
        state['status'] = 'recovery-needed' if errors else 'restored'
        if not errors:
            state['completed_at'] = time.time()
        self.store.write(state)
        if not errors:
            # Progress is optional: its failure must never interrupt restoration.
            try:
                from .progress import Profile
                Profile(self.store.directory).completed(state)
            except Exception:
                log.exception('Recovery succeeded but optional progress could not be recorded')
        return errors


def export_report(snapshot, engine):
    """No network, process command lines, environment dump, or browser contents."""
    report = {'version': __version__, 'created': time.time(), 'environment': snapshot.environment,
              'memory': snapshot.memory, 'counts': {}, 'notices': snapshot.warnings,
              'session': engine.store.read()}
    for item in snapshot.items:
        report['counts'][item.kind] = report['counts'].get(item.kind, 0) + 1
    path = engine.store.directory / f'diagnostics-{time.time_ns()}.json'
    text = json.dumps(report, indent=2).replace(str(Path.home()), '~')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as handle:
        handle.write(text)
    return path
