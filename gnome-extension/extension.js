import Gio from 'gi://Gio';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

export default class MemminningExtension extends Extension {
    enable() {
        this._indicator = new PanelMenu.Button(0.0, 'Memminning');
        this._indicator.add_child(new St.Icon({
            icon_name: 'speedometer-symbolic', style_class: 'system-status-icon',
        }));
        const open = new PopupMenu.PopupMenuItem('Open Memminning');
        open.connect('activate', () => {
            try {
                const app = Gio.DesktopAppInfo.new('io.github.memminning.Memminning.desktop');
                if (!app)
                    throw new Error('Run the Memminning installer first.');
                app.launch([], global.create_app_launch_context(0, -1));
            } catch (error) {
                console.error(error);
                Main.notify('Memminning', error.message);
            }
        });
        this._indicator.menu.addMenuItem(open);
        this._indicator.menu.addMenuItem(new PopupMenu.PopupMenuItem(
            'Review changes in the app before starting', {reactive: false}));
        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
