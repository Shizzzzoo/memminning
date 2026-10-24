"""Exercise GTK controls with fake service/extension operations and isolated state."""
import sys
from pathlib import Path
import tempfile
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_core import FakeBackend, EXT, TARGET
from memminning import gui
from memminning.core import Engine, Item, Snapshot, Store, memory
from gi.repository import Gtk, GLib

scratch = tempfile.TemporaryDirectory(prefix='memminning-gui-test-')
backend = FakeBackend()
app = gui.App()
app.set_application_id('io.github.memminning.InteractionTest')
app.engine = Engine(backend, Store(scratch.name))
gui.scan = lambda: Snapshot([
    Item(f'gnome:{EXT}', 'Test wallpaper', 'GNOME extensions', 'Isolated simulated target', actions=('disable',)),
    Item(f'user:{TARGET}', 'Test indexer', 'User services', 'Isolated simulated target', 1000, ('stop', 'limit')),
], [], memory(), {'os': 'Test environment', 'desktop': 'GNOME'})
state = {'step': 0, 'ticks': 0, 'passed': False}


def descendants(widget):
    yield widget
    child = widget.get_first_child()
    while child:
        yield from descendants(child)
        child = child.get_next_sibling()


def finish():
    for window in list(Gtk.Window.get_toplevels()):
        window.close()
    app.quit()
    return False


def step():
    try:
        state['ticks'] += 1
        if state['ticks'] > 120:
            raise AssertionError('GUI interactions timed out')
        if not app.snapshot or app.busy:
            return True
        if state['step'] == 0:
            assert not app.choices
            app.character_filter.set_selected(3)
            assert not app.companion_buttons['steve'].get_parent().get_visible()
            assert app.companion_buttons['jett'].get_parent().get_visible()
            app.character_filter.set_selected(0)
            assert all(b.get_parent().get_visible() for b in app.companion_buttons.values())
            app.companion_buttons['reyna'].emit('clicked')
            assert app.profile.read()['companion'] == 'reyna'
            app.switches['professional'].set_active(True)
            assert not app.hero_avatar.get_visible()
            assert not app.companion_section.get_visible()
            assert not app.growth.get_visible()
            assert app.restore_button.get_visible()
            assert app.review_button.get_sensitive()
            assert not app.sound_button.get_sensitive()
            app.switches['professional'].set_active(False)
            assert app.hero_avatar.get_visible()
            app.switches['reduced_motion'].set_active(True)
            assert app.stack.get_transition_type() == Gtk.StackTransitionType.NONE
            assert not Gtk.Settings.get_default().get_property('gtk-enable-animations')
            app.switches['reduced_motion'].set_active(False)
            assert Gtk.Settings.get_default().get_property('gtk-enable-animations') == app._system_animations
            app.save_custom_avatar(str(Path(__file__).resolve().parent / 'fixtures/avatar.png'))
            assert app.profile.read()['custom_avatar']
            assert (Path(scratch.name) / 'avatar.png').exists()
            app.reset_avatar.emit('clicked')
            assert not app.profile.read()['custom_avatar']
            app.activate_action('search', None)
            assert app.stack.get_visible_child_name() == 'inventory'
            assert 'shortcut' in app.profile.read()['milestones']
            app.filter.set_selected(5)
            dropdown = next(w for w in descendants(app.listbox) if isinstance(w, Gtk.DropDown))
            dropdown.set_selected(1)
            assert app.choices == {f'gnome:{EXT}': 'disable'}
            app.review_button.emit('clicked')
            state['step'] = 1
        elif state['step'] == 1:
            dialogs = [w for w in Gtk.Window.get_toplevels() if w.get_title() == 'Review temporary changes']
            if not dialogs:
                return True
            dialog = dialogs[0]
            consent = next(w for w in descendants(dialog) if isinstance(w, Gtk.CheckButton))
            apply = next(w for w in descendants(dialog) if isinstance(w, Gtk.Button) and w.get_label() == 'Start temporary gaming mode')
            assert not consent.get_active()
            assert not apply.get_sensitive()
            assert 'review' in app.profile.read()['milestones']
            consent.set_active(True)
            assert apply.get_sensitive()
            apply.emit('clicked')
            state['step'] = 2
        elif state['step'] == 2:
            assert app.engine.store.read()['status'] == 'active'
            assert EXT not in backend.enabled
            assert not app.profile.read()['sessions']
            assert app.restore_button.get_sensitive()
            app.restore_button.emit('clicked')
            state['step'] = 3
        elif state['step'] == 3:
            assert app.engine.store.read()['status'] == 'restored'
            assert EXT in backend.enabled
            app.tick()
            assert len(app.profile.read()['sessions']) == 1
            assert 'restore' in app.profile.read()['milestones']
            app.preference('theme', 'violet')
            assert app.profile.read()['theme'] == 'violet'
            assert app.window.has_css_class('violet')
            print('GUI interactions passed: avatars/import, preferences, reduced motion, shortcuts, review consent, fake apply/restore, milestones and theme unlock.')
            state['passed'] = True
            return finish()
        return True
    except Exception:
        traceback.print_exc()
        return finish()


GLib.timeout_add(250, step)
app.run([])
scratch.cleanup()
sys.exit(0 if state['passed'] else 1)
