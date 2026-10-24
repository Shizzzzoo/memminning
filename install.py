#!/usr/bin/python3
"""Per-user installation, also usable to install a reviewed update. No sudo."""
import argparse
import os
import subprocess
from pathlib import Path
import shlex
import shutil
import sys

from memminning.core import Store


def check_dependencies():
    if sys.version_info < (3, 10):
        sys.exit('Python 3.10 or newer is required. See docs/INSTALLATION.md.')
    try:
        import gi
        gi.require_version('Gtk', '4.0')
        gi.require_version('Adw', '1')
        from gi.repository import Gtk, Adw
    except (ImportError, ValueError) as exc:
        sys.exit(f'Missing GTK/PyGObject dependency: {exc}. See docs/INSTALLATION.md.')
    if (Gtk.get_major_version(), Gtk.get_minor_version()) < (4, 10):
        sys.exit('GTK 4.10 or newer is required for the avatar file chooser.')
    if (Adw.get_major_version(), Adw.get_minor_version()) < (1, 2):
        sys.exit('libadwaita 1.2 or newer is required.')
    for executable in ('systemctl', 'systemd-run'):
        if not shutil.which(executable):
            sys.exit(f'{executable} is required. Non-systemd systems are unsupported.')
    try:
        version = subprocess.run(['systemctl', '--version'], capture_output=True, text=True, check=True, timeout=10)
        if int(version.stdout.split()[1]) < 254:
            sys.exit('systemd 254 or newer is required for restoration timers.')
    except (ValueError, IndexError, OSError, subprocess.SubprocessError) as exc:
        sys.exit(f'Could not determine systemd version: {exc}')
    print('Dependency check passed: Python, GTK, libadwaita and systemd. Desktop-session access is checked when the app runs.')


def main():
    parser = argparse.ArgumentParser(description='Install or update Memminning for the current user')
    parser.add_argument('--check', action='store_true', help='Check software dependencies without installing')
    parser.add_argument('--with-character-art', action='store_true',
                        help='Download and verify the optional third-party game character portraits')
    args = parser.parse_args()
    check_dependencies()
    if args.check:
        return
    if os.geteuid() == 0:
        sys.exit('Run this installer as your desktop user, not root.')
    source = Path(__file__).resolve().parent
    home = Path.home()
    data = Path(os.getenv('XDG_DATA_HOME', home / '.local/share'))
    config = Path(os.getenv('XDG_CONFIG_HOME', home / '.config'))
    destination = data / 'memminning/app'
    store = Store()
    with store.lock():
        current = store.read()
        if current and current['status'] != 'restored':
            sys.exit('Restore the current Memminning session before installing or updating.')
        if args.with_character_art:
            from memminning.artwork import fetch_artwork
            try:
                fetch_artwork(source / 'assets')
            except Exception as exc:
                sys.exit(f'Artwork download failed; installation was not changed: {exc}')
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source / 'memminning', destination / 'memminning', dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copytree(source / 'assets', destination / 'assets', dirs_exist_ok=True)
        # Remove only the obsolete, app-owned generated portrait sheet.
        (destination / 'assets/companions.png').unlink(missing_ok=True)
        shutil.copy2(source / 'run.py', destination / 'run.py')
        for document in source.glob('*.md'):
            shutil.copy2(document, destination / document.name)
        shutil.copy2(source / 'LICENSE', destination / 'LICENSE')
        (destination / 'docs').mkdir(exist_ok=True)
        for document in (source / 'docs').glob('*.md'):
            shutil.copy2(document, destination / 'docs' / document.name)
        for directory in ('images', 'releases'):
            shutil.copytree(source / 'docs' / directory, destination / 'docs' / directory, dirs_exist_ok=True)
        bin_dir = home / '.local/bin'
        bin_dir.mkdir(parents=True, exist_ok=True)
        launcher = bin_dir / 'memminning'
        launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 ' + shlex.quote(str(destination / 'run.py')) + ' "$@"\n')
        launcher.chmod(0o755)
        # Desktop Exec quoting is distinct from shell quoting.
        escaped = str(destination / 'run.py').replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
        exec_line = f'/usr/bin/python3 "{escaped}"'
        apps = data / 'applications'
        apps.mkdir(parents=True, exist_ok=True)
        (apps / 'io.github.memminning.Memminning.desktop').write_text(
            '[Desktop Entry]\nType=Application\nName=Memminning\nComment=Review memory use and temporary gaming mode\n'
            f'Exec={exec_line}\nIcon=utilities-system-monitor\nTerminal=false\nCategories=System;Monitor;\nStartupNotify=true\n')
        autostart = config / 'autostart'
        autostart.mkdir(parents=True, exist_ok=True)
        (autostart / 'io.github.memminning.Recovery.desktop').write_text(
            '[Desktop Entry]\nType=Application\nName=Memminning recovery\n'
            f'Exec={exec_line} --recover\nTerminal=false\nNoDisplay=true\nX-GNOME-Autostart-Delay=10\n')
        extension = data / 'gnome-shell/extensions/memminning@local'
        shutil.copytree(source / 'gnome-extension', extension, dirs_exist_ok=True)
    print(f'Installed Memminning to {destination}')
    print(f'Launch from your application menu or {launcher}')
    print('The GNOME panel extension is installed but not enabled. After logging out and in, enable Memminning in Extensions.')
    print('No gaming-mode actions have been applied. Login recovery runs only when a saved session needs restoration.')


if __name__ == '__main__':
    main()
