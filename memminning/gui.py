"""Native GTK 4 UI. Scans and system operations run off the GTK thread."""
import threading
import time

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gio, GLib, Gtk, Gdk

from . import __version__
from .gameui import GamingUI
from .core import Engine, OperationError, export_report, log, memory, mib, scan

ACTION_LABELS = {'disable': 'Disable temporarily', 'stop': 'Stop temporarily', 'limit': 'Soft RAM limit'}



def label(text, css=None, wrap=False):
    widget = Gtk.Label(label=text, xalign=0, wrap=wrap)
    if css:
        widget.add_css_class(css)
    return widget


def margins(widget, n):
    for side in ('top', 'bottom', 'start', 'end'):
        getattr(widget, f'set_margin_{side}')(n)
    return widget


class App(GamingUI, Adw.Application):
    def __init__(self):
        super().__init__(application_id='io.github.memminning.Memminning', flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.connect('activate', self.activate)
        self.window = None
        self.snapshot = None
        self.engine = Engine()
        self.choices = {}
        self.busy = False
        self._reviewed_plan = None

    def activate(self, _app):
        if self.window:
            self.window.present()
            return
        self.build_shell()

    def work(self, function, done):
        if self.busy:
            return
        self.busy = True
        self.set_controls(False)
        def worker():
            try:
                result = function()
                GLib.idle_add(finish, result, None)
            except Exception as exc:
                log.exception('Background operation failed')
                GLib.idle_add(finish, None, str(exc))
        def finish(result, error):
            self.busy = False
            self.set_controls(True)
            if error:
                self.status.set_text('Action needs attention. Review the error and restore if needed.')
                self.message('Could not complete the action', error)
            else:
                done(result)
            self.tick()
            return False
        threading.Thread(target=worker, daemon=True).start()

    def set_controls(self, enabled):
        for widget in (self.scan_button, self.review_button, self.restore_button, self.report_button,
                       self.duration, self.limit, self.listbox):
            widget.set_sensitive(enabled)

    def start_scan(self):
        self.status.set_text('Scanning readable system activity…')
        def done(snapshot):
            self.snapshot = snapshot
            self.choices.clear()
            self._reviewed_plan = None
            self.notices.set_text('\n\n'.join(snapshot.warnings))
            self.render_items()
            self.profile_action(lambda: self.profile.award('scan'))
            self.feedback(f'Scan complete · {len(snapshot.items)} inventory entries. No changes applied.')
        self.work(scan, done)

    def render_items(self):
        if not self.snapshot:
            return
        child = self.listbox.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.listbox.remove(child)
            child = nxt
        category = self.filter.get_selected_item().get_string()
        query = self.search.get_text().strip().lower()
        shown = 0
        for item in sorted(self.snapshot.items, key=lambda i: (not bool(i.actions), -(i.memory or 0), i.name.lower())):
            if category == 'Reviewable targets' and not item.actions:
                continue
            if category not in ('Reviewable targets', 'All inventory') and item.kind != category:
                continue
            if query and query not in f'{item.name} {item.detail}'.lower():
                continue
            row = Gtk.Box(spacing=14)
            texts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5, hexpand=True)
            title = label(item.name)
            title.set_ellipsize(3)
            title.set_max_width_chars(45)
            title.set_tooltip_text(item.name)
            texts.append(title)
            detail = label(f'{item.kind} · {item.risk}\n{item.detail}', 'muted', True)
            detail.set_max_width_chars(55)
            texts.append(detail)
            row.append(texts)
            amount = label(mib(item.memory), 'muted')
            amount.set_size_request(95, -1)
            row.append(amount)
            if item.actions:
                values = ('keep', *item.actions)
                choice = Gtk.DropDown.new_from_strings(['Keep running', *[ACTION_LABELS[a] for a in item.actions]])
                choice.set_valign(Gtk.Align.CENTER)
                selected = self.choices.get(item.id, 'keep')
                choice.set_selected(values.index(selected) if selected in values else 0)
                choice.connect('notify::selected', self.choose, item.id, values)
                row.append(choice)
            else:
                protected = label('Read only', 'muted')
                protected.set_size_request(165, -1)
                row.append(protected)
            self.listbox.append(row)
            shown += 1
        if not shown:
            self.listbox.append(margins(label('No matching targets. Choose All inventory to see the rest of the scan.', 'muted', True), 20))
        self.list_count.set_text(f'{shown} entries shown · {len(self.choices)} actions selected · Nothing changes until you approve the review.')

    def choose(self, dropdown, _pspec, item_id, values):
        self._reviewed_plan = None
        action = values[dropdown.get_selected()]
        if action == 'keep':
            self.choices.pop(item_id, None)
        else:
            self.choices[item_id] = action
        self.list_count.set_text(f'{len(self.choices)} actions selected · Nothing changes until you approve the review.')
        self.refresh_session_ui(self.engine.store.read())

    def tick(self):
        if not self.window or self.busy:
            return True
        try:
            mem = memory()
            self.metric_labels[0].set_text(mib(mem['MemAvailable']))
            self.metric_labels[1].set_text(mib(mem['SwapTotal'] - mem['SwapFree']))
            self.metric_labels[2].set_text(str(sum(bool(i.actions) for i in self.snapshot.items)) if self.snapshot else '—')
            state = self.engine.store.read()
            self.refresh_session_ui(state)
            active = state and state['status'] != 'restored'
            self.restore_button.set_sensitive(bool(active))
            self.review_button.set_sensitive(not active and self.snapshot is not None)
            if active:
                left = max(0, int(state['deadline'] - time.time()))
                self.status.set_text(f"Session: {state['status']} · Restore in {left // 60}m {left % 60}s · "
                                     'You can close this window; the systemd restoration timer remains active.')
            elif self.snapshot:
                self.status.set_text(f"Ready · {self.snapshot.environment['os']} · {self.snapshot.environment['desktop']} · "
                                     'Review every change. Memory savings are not guaranteed.')
        except Exception as exc:
            self.status.set_text(f'Recovery status unavailable: {exc}')
            self.review_button.set_sensitive(False)
        return True

    def message(self, title, body):
        dialog = Adw.MessageDialog(transient_for=self.window, heading=title, body=body)
        dialog.add_response('ok', 'OK')
        dialog.present()

    def review(self, _button):
        if not self.choices:
            self.navigate('inventory')
            self.feedback('Choose a target’s temporary action first. Everything starts at Keep running.')
            return
        choices = list(self.choices.items())
        minutes, limit = self.duration.get_value_as_int(), self.limit.get_value_as_int()
        def prepared(_records):
            self._reviewed_plan = tuple(sorted(choices))
            self.profile_action(lambda: self.profile.award('review'))
            dialog = Gtk.Window(title='Review temporary changes', transient_for=self.window, modal=True,
                                default_width=680, default_height=560)
            dialog.add_css_class('memminning')
            box = margins(Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16), 24)
            box.append(label('Your gaming session', 'hero'))
            box.append(label(f'Restore after {minutes} minutes. Soft limit: {limit} MiB per selected service.', 'muted', True))
            details = '\n\n'.join(f'{ACTION_LABELS[action]}\n{target.split(":", 1)[1]}' for target, action in choices)
            scroll = Gtk.ScrolledWindow(vexpand=True, min_content_height=140)
            text = label(details, wrap=True)
            text.set_selectable(True)
            scroll.set_child(text)
            box.append(scroll)
            box.append(label('Extension features and desktop controls may disappear temporarily. Stopped services lose '
                'in-flight work and may restart through D-Bus. Soft limits can cause swapping and stutters; they do not '
                'guarantee free RAM. Restoration retries are logged, but cannot guarantee recovery after every failure. '
                'Changing the same targets elsewhere during this session can conflict with restoration.', 'notice', True))
            agree = Gtk.CheckButton(label='I reviewed these targets and saved any affected work.')
            box.append(agree)
            buttons = Gtk.Box(spacing=10, halign=Gtk.Align.END)
            cancel = Gtk.Button(label='Cancel')
            cancel.connect('clicked', lambda _: dialog.close())
            buttons.append(cancel)
            apply = Gtk.Button(label='Start temporary gaming mode', sensitive=False)
            apply.add_css_class('suggested-action')
            agree.connect('toggled', lambda w: apply.set_sensitive(w.get_active()))
            def start(_):
                dialog.close()
                self.status.set_text('Saving recovery state and applying reviewed actions…')
                def started(_state):
                    self.choices.clear()
                    self.render_items()
                    self.navigate('dashboard')
                    self.feedback('Temporary session started. Your restoration timer is armed.')
                self.work(lambda: self.engine.begin(choices, minutes, limit), started)
            apply.connect('clicked', start)
            buttons.append(apply)
            box.append(buttons)
            dialog.set_child(box)
            dialog.present()
        self.work(lambda: self.engine.prepare(choices, minutes, limit), prepared)

    def restore(self, _button):
        self.status.set_text('Restoring the original settings…')
        def done(errors):
            if errors:
                self.message('Some targets still need recovery', '\n'.join(errors))
            else:
                self.feedback('✓ Original settings restored. Rescan to refresh the inventory.')
        self.work(self.engine.restore, done)

    def report(self, _button):
        if not self.snapshot:
            return
        self.work(lambda: export_report(self.snapshot, self.engine),
                  lambda path: self.message('Diagnostics saved locally', f'{path}\n\nReview before sharing: '
                                            'the report includes extension/service identifiers and error messages. '
                                            'No data is uploaded. Detailed rotating logs are stored beside this file.'))

    def about(self, _button):
        self.message('Memminning ' + __version__,
            'Arch-first · GTK 4 · GNOME companion extension\n\n'
            'Action support: enabled GNOME extensions and allowlisted optional user services. '
            'KDE, Cinnamon, XFCE, browser/editor plugins, other processes and system services are inventoried only. '
            'Custom stores and other users’ private data may be absent.\n\n'
            'No root access, arbitrary process killing, cache flushing, hard memory caps, or telemetry. '
            'RSS values overlap and cannot be added to predict savings. Pausing a process does not release its RAM.\n\n'
            'Recovery: Restore now, or run “memminning --restore”. Login recovery is installed by install.py. '
            'A systemd timer survives closing the GUI. Reboot removes runtime limits; login recovery restores extensions.\n\n'
            'Updates: versioned local installation; restore before running the installer from a reviewed newer release. '
            'No update server or automatic downloads are configured.')


def main():
    return App().run([])
