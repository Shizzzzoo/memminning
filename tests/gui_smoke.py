"""Read-only smoke test on a real desktop; no gaming actions are applied."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from memminning.core import setup_logging
from memminning.gui import App, GLib
setup_logging()
app = App()
app.set_application_id('io.github.memminning.ReadOnlySmoke')
if '--small' in sys.argv:
    app.connect_after('activate', lambda _a: app.window.set_default_size(1000, 720))
result = {'passed': False, 'attempts': 0}


def check():
    result['attempts'] += 1
    if app.snapshot and not app.busy:
        app.filter.set_selected(1)
        app.search.set_text('gnome')
        app.render_items()
        app.search.set_text('')
        app.filter.set_selected(0)
        app.render_items()
        app.tick()
        assert app.listbox.get_first_child() is not None
        assert app.metric_labels[0].get_text() != '—'
        result['passed'] = True
        print(f'GUI smoke passed: {len(app.snapshot.items)} inventory entries; search, filters, metrics rendered')
        if '--screenshot' in sys.argv:
            GLib.timeout_add_seconds(5, capture)
        else:
            app.quit()
        return False
    if result['attempts'] > 45:
        print('GUI scan did not complete within 45 seconds', file=sys.stderr)
        app.quit()
        return False
    return True



def capture():
    try:
        from gi.repository import Gtk
        paintable = Gtk.WidgetPaintable.new(app.window)
        snapshot = Gtk.Snapshot.new()
        paintable.snapshot(snapshot, app.window.get_width(), app.window.get_height())
        node = snapshot.to_node()
        if node is None:
            raise RuntimeError('Window has no rendered snapshot')
        texture = app.window.get_renderer().render_texture(node, None)
        texture.save_to_png('/tmp/memminning-ui.png')
        print('Saved /tmp/memminning-ui.png')
    except Exception as exc:
        result['passed'] = False
        print(f'Visual capture failed: {exc}', file=sys.stderr)
    finally:
        app.quit()
    return False

GLib.timeout_add_seconds(1, check)
app.run([])
sys.exit(0 if result['passed'] else 1)
