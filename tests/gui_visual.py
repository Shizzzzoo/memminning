"""Capture live, read-only pages using an isolated UI profile."""
import sys
from pathlib import Path
import tempfile
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memminning.gui import App
from memminning.core import Engine, Store
from memminning.progress import Profile
from gi.repository import Gtk, GLib

scratch = tempfile.TemporaryDirectory(prefix='memminning-visual-')
profile = Profile(scratch.name)
preferences = Profile().read()
preferences.update(professional=False, sound=False, reduced_motion=True, custom_avatar=False)
profile.write(preferences)
app = App()
app.set_application_id('io.github.memminning.VisualTest')
app.engine = Engine(store=Store(scratch.name))
app.connect_after('activate', lambda _a: app.window.set_default_size(1260, 960))
state = {'stage': 0, 'ticks': 0, 'passed': False}
root = Path(__file__).resolve().parents[1]


def capture(name):
    paintable = Gtk.WidgetPaintable.new(app.window)
    snapshot = Gtk.Snapshot.new()
    paintable.snapshot(snapshot, app.window.get_width(), app.window.get_height())
    node = snapshot.to_node()
    if node is None:
        raise AssertionError('Window did not render')
    texture = app.window.get_renderer().render_texture(node, None)
    texture.save_to_png(str(root / 'docs' / name))
    print('Captured', name)


def step():
    try:
        state['ticks'] += 1
        if state['ticks'] > 60:
            raise AssertionError('Visual check timed out')
        if not app.snapshot or app.busy:
            return True
        stage = state['stage']
        if stage == 0:
            app.navigate('dashboard')
            app.stack.get_visible_child().get_vadjustment().set_value(560 if '--roster' in sys.argv else 0)
        elif stage == 5:
            if '--roster' in sys.argv:
                capture('characters-v0.2.1.png')
                state['passed'] = True
                app.quit()
                return False
            capture('dashboard-v0.2.1.png')
            app.navigate('inventory')
        elif stage == 7:
            capture('inventory-v0.2.1.png')
            app.preference('professional', True)
            app.navigate('dashboard')
            app.stack.get_visible_child().get_vadjustment().set_value(0)
        elif stage == 9:
            assert not app.hero_avatar.get_visible()
            capture('professional-v0.2.1.png')
            app.preference('professional', False)
            app.navigate('settings')
        elif stage == 11:
            capture('preferences-v0.2.1.png')
            state['passed'] = True
            app.quit()
            return False
        state['stage'] += 1
        return True
    except Exception:
        traceback.print_exc()
        app.quit()
        return False


GLib.timeout_add_seconds(1, step)
app.run([])
scratch.cleanup()
sys.exit(0 if state['passed'] else 1)
