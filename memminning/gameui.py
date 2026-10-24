"""Gaming dashboard presentation, with optional progress and no system-action policy."""
from datetime import datetime, timedelta
from pathlib import Path
import threading
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk, Gdk, Gio, GLib, GdkPixbuf, Pango
from . import __version__
from .core import ROOT, log, run
from .progress import Profile, COMPANIONS, CHARACTER_FRAMING, MILESTONES, THEMES, defaults, tier, unlocked_themes

CSS = b'''
window.memminning { background: #101613; color: #e8eee9; font-family: "Adwaita Sans", "Noto Sans", sans-serif; font-size: 14px; }
.memminning headerbar { background: #101613; border-bottom: 1px solid #27352d; }
.sidebar { background: #131b17; border-right: 1px solid #29372e; padding: 23px 16px; }
.brand { font-size: 22px; font-weight: 800; letter-spacing: -0.7px; }
.eyebrow { font-size: 10px; font-weight: 800; letter-spacing: 1.8px; color: #91a99a; }
.hero { font-size: 36px; font-weight: 800; letter-spacing: -1.4px; }
.section-title { font-size: 19px; font-weight: 750; }
.muted { color: #a0b3a5; }
.small { font-size: 12px; }
.accent { color: #b4ed96; }
.hero-card { background: linear-gradient(115deg, #233a29, #17251d); border: 1px solid #3c5841; border-radius: 21px; padding: 20px; }
.chip { border-radius: 20px; background: #304533; color: #c8eeb7; padding: 5px 10px; font-size: 11px; font-weight: 700; }
.card { background: #18221c; border: 1px solid #2d3d32; border-radius: 16px; padding: 18px; }
.metric { background: #18221c; border: 1px solid #2d3d32; border-radius: 14px; padding: 17px; }
.metric-value { font-size: 27px; font-weight: 750; color: #e3f4dd; }
.status { background: #17231b; border-bottom: 1px solid #2a3c30; padding: 9px 18px; color: #bad0c0; font-size: 12px; }
.notice { background: #343021; color: #f3dfad; border-radius: 10px; padding: 12px; }
.avatar { border-radius: 17px; background: radial-gradient(ellipse at center, #385045, #17251d); }
.profile { border-radius: 13px; background: #1d2c22; padding: 14px; }
.nav { border: 0; box-shadow: none; background: transparent; color: #adc0b1; padding: 12px; font-weight: 600; }
.nav:checked { background: #2b3d2e; color: #d4f4c4; }
button { border-radius: 9px; transition: background-color 140ms ease, border-color 140ms ease; }
button:hover { background-color: #364a3b; }
button:focus-visible { outline: 2px solid #b4ed96; outline-offset: 2px; }
button.suggested-action { background: #b4ed96; color: #142111; font-weight: 800; box-shadow: none; }
button.suggested-action:hover { background: #c9f6b3; }
button.companion { background: #18221c; border: 2px solid #2d3d32; padding: 8px; }
button.companion:checked { border-color: #b4ed96; background: #243728; }
button.companion:hover { background: #2b3c2f; }
.step { border-radius: 9px; background: #253329; padding: 10px; color: #9caf9f; font-size: 12px; font-weight: 600; }
.step.done { background: #344c33; color: #d3edbe; }
list { background: transparent; }
row { background: #19231d; border-radius: 10px; margin: 3px 0; padding: 12px; }
row:hover { background: #24342a; }
progressbar trough { min-height: 5px; background: #314335; border-radius: 4px; }
progressbar progress { min-height: 5px; background: #b4ed96; border-radius: 4px; }
.footer { background: #151e18; border-top: 1px solid #2c3b30; padding: 12px 20px; }
.error { color: #ffb4ae; }
.memminning.amber .hero-card { background: linear-gradient(115deg, #43361e, #242317); border-color: #675330; }
.memminning.amber button.suggested-action { background: #f0ce8d; }
.memminning.amber .accent { color: #f0ce8d; }
.memminning.teal .hero-card { background: linear-gradient(115deg, #1d3c39, #182725); border-color: #34635a; }
.memminning.teal button.suggested-action { background: #98dfd4; }
.memminning.teal .accent { color: #98dfd4; }
.memminning.violet .hero-card { background: linear-gradient(115deg, #362b46, #211c2b); border-color: #59476e; }
.memminning.violet button.suggested-action { background: #d1b4f0; }
.memminning.violet .accent { color: #d1b4f0; }
.memminning.professional { background: #16191e; }
.professional .sidebar { background: #1b1f25; }
.professional .hero-card { background: #222931; border-color: #3b4651; }
.professional .hero { font-size: 28px; }
.reduced-motion * { transition: none; animation: none; }
'''


def text(value, css=None, wrap=False):
    widget = Gtk.Label(label=value, xalign=0, wrap=wrap)
    if css:
        for name in css.split():
            widget.add_css_class(name)
    return widget


def box(vertical=True, spacing=12, css=None):
    widget = Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, spacing=spacing)
    if css:
        widget.add_css_class(css)
    return widget


def pad(widget, amount):
    for side in ('top', 'bottom', 'start', 'end'):
        getattr(widget, f'set_margin_{side}')(amount)
    return widget


def clear(widget):
    child = widget.get_first_child()
    while child:
        nxt = child.get_next_sibling()
        widget.remove(child)
        child = nxt


class GamingUI:
    def initialize_profile(self):
        self.profile = Profile(self.engine.store.directory)
        self.profile_state = defaults()
        self.profile_warning = ''
        self._profile_stamp = None
        self._avatar_cache = {}
        self._refreshing = False
        self._last_session_status = None
        try:
            self.profile_state = self.profile.read()
        except Exception as exc:
            self.profile_warning = str(exc)
            log.exception('Optional profile could not be read')

    def profile_action(self, operation):
        try:
            result = operation()
            self.profile_state = self.profile.read()
            self.profile_warning = ''
            if isinstance(result, list) and result:
                names = ', '.join(m[1] for m in MILESTONES if m[0] in result)
                self.feedback(f'Milestone reached: {names}', celebrate=True)
            self.refresh_profile()
            return result
        except Exception as exc:
            self.profile_warning = str(exc)
            log.exception('Optional profile operation failed')
            self.feedback('Progress could not be saved. Resource controls are still available.')
            return None

    def avatar(self, index, size, custom=False):
        picture = Gtk.Picture(can_shrink=True, content_fit=Gtk.ContentFit.COVER,
                              width_request=size, height_request=size,
                              halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        picture.set_size_request(size, size)
        clip = box(spacing=0, css='avatar')
        clip.set_overflow(Gtk.Overflow.HIDDEN)
        clip.append(picture)
        clip.set_halign(Gtk.Align.CENTER)
        clip.set_valign(Gtk.Align.CENTER)
        try:
            custom_path = self.profile.directory / 'avatar.png'
            if custom and self.profile_state['custom_avatar'] and custom_path.exists():
                # Downsample at load so a large imported avatar never stays decoded at full size.
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(custom_path), size, size, False)
                picture.set_paintable(Gdk.Texture.new_for_pixbuf(pixbuf))
            else:
                key = (index, size)
                if key not in self._avatar_cache:
                    character = COMPANIONS[index][0]
                    asset = ROOT / 'assets/characters' / f'{character}.png'
                    if not asset.is_file():
                        clip.remove(picture)
                        clip.append(Gtk.Image(icon_name='applications-games-symbolic', pixel_size=size))
                        clip.set_tooltip_text('Character art is optional. Install with --with-character-art, or choose your own avatar in Preferences.')
                        return clip
                    sprite = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(asset), 512, 512, True)
                    if character in CHARACTER_FRAMING:
                        x, y, w, h = CHARACTER_FRAMING[character]
                        width, height = sprite.get_width(), sprite.get_height()
                        sprite = sprite.new_subpixbuf(int(x * width), int(y * height),
                                                      int(w * width), int(h * height))
                    sprite = sprite.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
                    self._avatar_cache[key] = Gdk.Texture.new_for_pixbuf(sprite)
                picture.set_paintable(self._avatar_cache[key])
        except Exception:
            log.exception('Avatar artwork could not be loaded')
            clip.remove(picture)
            clip.append(Gtk.Image(icon_name='applications-games-symbolic', pixel_size=size))
        return clip

    def build_shell(self):
        self.initialize_profile()
        self._system_animations = Gtk.Settings.get_default().get_property('gtk-enable-animations')
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        self.window = Adw.ApplicationWindow(application=self, title='Memminning', default_width=1260, default_height=900)
        self.window.add_css_class('memminning')
        self.window.set_size_request(880, 620)
        outer = box(spacing=0)
        header = Adw.HeaderBar()
        self.header_label = text('MEMMINNING  /  GAME READY', 'eyebrow')
        header.set_title_widget(self.header_label)
        self.scan_button = Gtk.Button(label='Scan system', tooltip_text='Rescan system · Ctrl+R')
        self.scan_button.connect('clicked', lambda _: self.start_scan())
        header.pack_start(self.scan_button)
        self.report_button = Gtk.Button(icon_name='document-save-symbolic', tooltip_text='Export local diagnostics')
        self.report_button.connect('clicked', self.report)
        header.pack_end(self.report_button)
        help_button = Gtk.Button(icon_name='help-about-symbolic', tooltip_text='Capabilities, risks and recovery')
        help_button.connect('clicked', self.about)
        header.pack_end(help_button)
        self.sound_button = Gtk.ToggleButton(icon_name='audio-volume-muted-symbolic', tooltip_text='Milestone sounds (off by default)')
        self.sound_button.connect('toggled', lambda w: self.preference('sound', w.get_active()))
        header.pack_end(self.sound_button)
        outer.append(header)
        self.status = text('Scanning your system…', 'status', True)
        outer.append(self.status)
        body = box(False, 0)
        body.set_vexpand(True)
        self.sidebar = box(spacing=12, css='sidebar')
        self.sidebar.set_size_request(205, -1)
        brand = box(False, 8)
        brand.append(Gtk.Image(icon_name='applications-games-symbolic', pixel_size=26))
        brand.append(text('memminning', 'brand'))
        self.sidebar.append(brand)
        self.sidebar.append(text('LESS BACKGROUND. MORE PLAY.', 'eyebrow'))
        self.profile_box = box(css='profile')
        self.sidebar.append(self.profile_box)
        self.nav_buttons = {}
        for key, title, icon in [('dashboard', 'Command center', 'view-grid-symbolic'),
                                 ('inventory', 'System inventory', 'view-list-symbolic'),
                                 ('guide', 'Field guide', 'help-browser-symbolic'),
                                 ('settings', 'Preferences', 'emblem-system-symbolic')]:
            button = Gtk.ToggleButton()
            button.add_css_class('nav')
            if self.nav_buttons:
                button.set_group(next(iter(self.nav_buttons.values())))
            inside = box(False, 10)
            inside.append(Gtk.Image(icon_name=icon))
            inside.append(text(title))
            button.set_child(inside)
            button.connect('clicked', lambda _w, page=key: self.navigate(page))
            self.nav_buttons[key] = button
            self.sidebar.append(button)
        spacer = box()
        spacer.set_vexpand(True)
        self.sidebar.append(spacer)
        self.sidebar.append(text('YOUR DESKTOP, YOUR RULES', 'eyebrow'))
        self.sidebar.append(text('Nothing changes until you\nreview and approve it.', 'muted small', True))
        self.sidebar.append(text(f'Arch-first · v{__version__}\nLocal progress · no account', 'muted small'))
        body.append(self.sidebar)
        self.stack = Gtk.Stack(hexpand=True, vexpand=True, transition_type=Gtk.StackTransitionType.CROSSFADE,
                               transition_duration=150)
        self.toast = Adw.ToastOverlay()
        self.toast.set_child(self.stack)
        body.append(self.toast)
        outer.append(body)
        self.build_dashboard()
        self.build_inventory()
        self.build_guide()
        self.build_settings()
        footer = box(False, 12, 'footer')
        self.footer_text = text('Choose what to pause. Keep a way back.', 'muted small', True)
        self.footer_text.set_hexpand(True)
        footer.append(self.footer_text)
        self.restore_button = Gtk.Button(label='Restore now', tooltip_text='Restore original settings · Ctrl+Shift+R')
        self.restore_button.connect('clicked', self.restore)
        footer.append(self.restore_button)
        self.review_button = Gtk.Button(label='Review gaming mode')
        self.review_button.add_css_class('suggested-action')
        self.review_button.connect('clicked', self.review)
        footer.append(self.review_button)
        outer.append(footer)
        self.window.set_content(outer)
        self.add_shortcuts()
        self.refresh_profile()
        self.navigate('dashboard')
        self.window.present()
        GLib.timeout_add_seconds(3, self.tick)
        self.start_scan()

    def page(self, name):
        content = pad(box(spacing=16), 26)
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                   vscrollbar_policy=Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(content)
        self.stack.add_named(scroll, name)
        return content

    def build_dashboard(self):
        self.dashboard = self.page('dashboard')
        self.hero_card = box(False, 20, 'hero-card')
        copy = box(spacing=10)
        copy.set_hexpand(True)
        self.hero_eyebrow = text('YOUR PRE-GAME CHECKPOINT', 'eyebrow')
        copy.append(self.hero_eyebrow)
        self.hero_title = text('More room.\nMore adventure.', 'hero')
        copy.append(self.hero_title)
        self.hero_description = text('A little breathing room for your next big build.', 'muted', True)
        copy.append(self.hero_description)
        self.game_chip = text('MINECRAFT · SANDBOX', 'chip')
        self.game_chip.set_halign(Gtk.Align.START)
        copy.append(self.game_chip)
        cta = Gtk.Button(label='Review background activity  →', halign=Gtk.Align.START)
        cta.add_css_class('suggested-action')
        cta.connect('clicked', lambda _: self.navigate('inventory'))
        copy.append(cta)
        self.hero_card.append(copy)
        self.hero_avatar = box(spacing=0)
        self.hero_avatar.set_valign(Gtk.Align.CENTER)
        self.hero_card.append(self.hero_avatar)
        self.dashboard.append(self.hero_card)
        metrics = box(False, 12)
        metrics.set_homogeneous(True)
        self.metric_labels = []
        for title, note in [('Available RAM', 'Live system reading'), ('Swap in use', 'Lower is not always better'),
                            ('Reviewable targets', 'You choose every change')]:
            tile = box(spacing=6, css='metric')
            tile.append(text(title, 'muted small'))
            value = text('—', 'metric-value')
            self.metric_labels.append(value)
            tile.append(value)
            tile.append(text(note, 'muted small'))
            metrics.append(tile)
        self.dashboard.append(metrics)
        self.route_card = box(spacing=12, css='card')
        self.route_title = text('A good session has a return path.', 'section-title')
        self.route_card.append(self.route_title)
        route = box(False, 8)
        route.set_homogeneous(True)
        self.steps = []
        for title in ('01  Scan', '02  Review', '03  Ready to play', '04  Restore'):
            step = text(title, 'step')
            route.append(step)
            self.steps.append(step)
        self.route_card.append(route)
        self.route_note = text('Start by seeing what is running. No process is selected automatically.', 'muted small', True)
        self.route_card.append(self.route_note)
        self.dashboard.append(self.route_card)
        self.companion_section = box(spacing=12)
        title_row = box(False)
        title = text('Choose your character', 'section-title')
        title.set_hexpand(True)
        title_row.append(title)
        title_row.append(text('8 characters · cosmetic only', 'muted small'))
        self.companion_section.append(title_row)
        filter_row = box(False, 10)
        filter_row.append(text('Game', 'muted small'))
        self.character_filter = Gtk.DropDown.new_from_strings(['All games', 'Minecraft', 'Fortnite', 'VALORANT'])
        self.character_filter.connect('notify::selected', lambda *_: self.filter_characters())
        filter_row.append(self.character_filter)
        self.companion_section.append(filter_row)
        cards = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
                            min_children_per_line=2, max_children_per_line=4, column_spacing=10, row_spacing=10)
        self.companion_buttons = {}
        for index, (key, name, game, _description) in enumerate(COMPANIONS):
            button = Gtk.ToggleButton()
            button.add_css_class('companion')
            if self.companion_buttons:
                button.set_group(next(iter(self.companion_buttons.values())))
            content = box(spacing=6)
            content.append(self.avatar(index, 100))
            name_label = text(name, 'section-title')
            name_label.set_halign(Gtk.Align.CENTER)
            content.append(name_label)
            game_label = text(game, 'muted small')
            game_label.set_halign(Gtk.Align.CENTER)
            content.append(game_label)
            button.set_child(content)
            button.connect('clicked', lambda _w, k=key: self.select_companion(k))
            self.companion_buttons[key] = button
            cards.insert(button, -1)
        self.companion_section.append(cards)
        self.dashboard.append(self.companion_section)
        self.growth = box(False, 14)
        self.mastery_card = box(css='card')
        self.mastery_card.set_hexpand(True)
        self.mastery_card.append(text('Master your setup', 'section-title'))
        self.milestone_list = box(spacing=9)
        self.mastery_card.append(self.milestone_list)
        self.growth.append(self.mastery_card)
        self.history_card = box(css='card')
        self.history_card.set_hexpand(True)
        self.history_card.append(text('Your safe returns', 'section-title'))
        self.history_text = text('', 'muted', True)
        self.history_text.set_max_width_chars(40)
        self.history_card.append(self.history_text)
        self.week_text = text('', 'small accent', True)
        self.history_card.append(self.week_text)
        self.history_card.append(text('No streaks to lose. No points for\nstopping more processes.', 'muted small', True))
        self.growth.append(self.history_card)
        self.dashboard.append(self.growth)

    def build_inventory(self):
        content = pad(box(spacing=14), 22)
        content.append(text('Know what’s running.', 'hero'))
        content.append(text('Installed does not mean active. Memory readings overlap; they are not promised savings.', 'muted', True))
        toolbar = box(False, 10)
        self.search = Gtk.SearchEntry(placeholder_text='Search processes, services or extensions…', hexpand=True)
        self.search.connect('search-changed', lambda _: self.render_items())
        toolbar.append(self.search)
        self.filter = Gtk.DropDown.new_from_strings(['Reviewable targets', 'All inventory', 'Processes', 'User services',
            'System services', 'GNOME extensions', 'Browser extensions', 'Editor extensions', 'Autostart',
            'KDE plugins', 'Cinnamon plugins', 'XFCE plugins', 'Memory overview', 'Flatpak apps', 'Snap apps'])
        self.filter.connect('notify::selected', lambda *_: self.render_items())
        toolbar.append(self.filter)
        content.append(toolbar)
        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        scroll = Gtk.ScrolledWindow(vexpand=True, min_content_height=140, hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroll.set_child(self.listbox)
        content.append(scroll)
        self.list_count = text('No actions selected', 'muted small', True)
        content.append(self.list_count)
        controls = box(False, 10)
        controls.append(text('Restore after'))
        self.duration = Gtk.SpinButton.new_with_range(1, 480, 5)
        self.duration.set_value(60)
        self.duration.set_tooltip_text('Timer continues after closing this window. Maximum 8 hours.')
        controls.append(self.duration)
        controls.append(text('minutes   ·   Soft limit'))
        self.limit = Gtk.SpinButton.new_with_range(64, 16384, 64)
        self.limit.set_value(256)
        self.limit.set_tooltip_text('MemoryHigh per selected service. May increase swap and latency; not a hard cap.')
        controls.append(self.limit)
        controls.append(text('MiB per service'))
        content.append(controls)
        self.notices = text('', 'muted small', True)
        self.notices.set_selectable(True)
        expander = Gtk.Expander(label='Scan coverage & notices')
        notice_scroll = Gtk.ScrolledWindow(max_content_height=100, propagate_natural_height=True)
        notice_scroll.set_child(self.notices)
        expander.set_child(notice_scroll)
        content.append(expander)
        self.stack.add_named(content, 'inventory')

    def build_guide(self):
        page = self.page('guide')
        page.append(text('Learn the controls.', 'hero'))
        page.append(text('Five useful habits. Every feature is available from day one.', 'muted', True))
        for _key, title, goal, meaning in MILESTONES:
            card = box(spacing=5, css='card')
            card.append(text(title, 'section-title'))
            card.append(text(goal, 'accent'))
            card.append(text(meaning, 'muted', True))
            page.append(card)
        card = box(css='card')
        card.append(text('Keyboard shortcuts', 'section-title'))
        card.append(text('Ctrl+F   Search system inventory\nCtrl+R   Rescan system\nCtrl+Shift+R   Restore original settings\nCtrl+,   Preferences', wrap=True))
        page.append(card)
        page.append(text('Preparing your desktop does not launch a game or choose emulator settings. Game labels describe '
                         'character origins, not detected installs or performance guarantees. Choosing a character does not change game compatibility with Linux.', 'muted small', True))

    def build_settings(self):
        page = self.page('settings')
        page.append(text('Make this your space.', 'hero'))
        page.append(text('Quiet by default. Personal when you want it.', 'muted'))
        self.switches = {}
        for key, title, description in [
            ('professional', 'Professional Mode', 'Hide character art, badges and progression. Keep every system and recovery control.'),
            ('sound', 'Milestone sounds', 'Play a short system sound for a newly earned milestone. Off by default; silent in Professional Mode.'),
            ('reduced_motion', 'Reduce motion', 'Disable page transitions and celebration animations. System animation preferences are also respected.')]:
            row = box(False, 20, 'card')
            words = box(spacing=5)
            words.set_hexpand(True)
            words.append(text(title, 'section-title'))
            detail = text(description, 'muted', True)
            detail.set_max_width_chars(70)
            words.append(detail)
            row.append(words)
            switch = Gtk.Switch(valign=Gtk.Align.CENTER)
            switch.connect('notify::active', lambda w, _p, k=key: self.preference(k, w.get_active()))
            row.append(switch)
            self.switches[key] = switch
            page.append(row)
        themes = box(css='card')
        themes.append(text('A little color, earned through useful habits.', 'section-title'))
        themes.append(text('Cosmetic rewards only. Safety, scanning and advanced controls never need unlocking.', 'muted small', True))
        self.theme_row = box(False, 10)
        themes.append(self.theme_row)
        page.append(themes)
        custom = box(css='card')
        custom.append(text('Bring your own avatar', 'section-title'))
        custom.append(text('Choose a local PNG or JPEG—your own Minecraft skin portrait, favorite character, or personal artwork. '
                           'The avatar is stored locally and never uploaded.', 'muted', True))
        buttons = box(False, 10)
        import_button = Gtk.Button(label='Choose avatar image…')
        import_button.connect('clicked', self.import_avatar)
        buttons.append(import_button)
        self.reset_avatar = Gtk.Button(label='Use character artwork')
        self.reset_avatar.connect('clicked', lambda _: self.preference('custom_avatar', False))
        buttons.append(self.reset_avatar)
        custom.append(buttons)
        page.append(custom)
        self.profile_notice = text('', 'muted small', True)
        self.profile_notice.set_selectable(True)
        page.append(self.profile_notice)

    def navigate(self, page):
        self.stack.set_visible_child_name(page)
        self.nav_buttons[page].set_active(True)

    def filter_characters(self):
        game = self.character_filter.get_selected_item().get_string()
        for key, _name, origin, _description in COMPANIONS:
            child = self.companion_buttons[key].get_parent()
            child.set_visible(game == 'All games' or game == origin)

    def preference(self, key, value):
        if self._refreshing or self.profile_state.get(key) == value:
            return
        self.profile_action(lambda: self.profile.preference(key, value))

    def select_companion(self, key):
        if self._refreshing:
            return
        self.profile_action(lambda: self.profile.preference('companion', key))
        self.preference('custom_avatar', False)
        name = next(c[1] for c in COMPANIONS if c[0] == key)
        self.feedback(f'{name} is ready for your next session.')

    def refresh_profile(self):
        if not self.window:
            return
        self._refreshing = True
        try:
            p = self.profile_state
            professional = p['professional']
            reduced = p['reduced_motion'] or not self._system_animations
            Gtk.Settings.get_default().set_property('gtk-enable-animations', not (reduced or professional))
            for name in (*THEMES, 'professional', 'reduced-motion'):
                self.window.remove_css_class(name)
            self.window.add_css_class(p['theme'])
            if professional:
                self.window.add_css_class('professional')
            if reduced or professional:
                self.window.add_css_class('reduced-motion')
            self.stack.set_transition_type(Gtk.StackTransitionType.NONE if reduced or professional else Gtk.StackTransitionType.CROSSFADE)
            for key, switch in self.switches.items():
                switch.set_active(p[key])
            self.sound_button.set_active(p['sound'])
            self.sound_button.set_icon_name('audio-volume-high-symbolic' if p['sound'] and not professional else 'audio-volume-muted-symbolic')
            self.sound_button.set_sensitive(not professional)
            self.switches['sound'].set_sensitive(not professional)
            for widget in (self.companion_section, self.growth, self.hero_avatar, self.game_chip):
                widget.set_visible(not professional)
            companion_index = next(i for i, c in enumerate(COMPANIONS) if c[0] == p['companion'])
            companion = COMPANIONS[companion_index]
            self.companion_buttons[p['companion']].set_active(True)
            self.header_label.set_text('MEMMINNING  /  RESOURCE CONTROL' if professional else 'MEMMINNING  /  GAME READY')
            self.hero_eyebrow.set_text('SYSTEM RESOURCE OVERVIEW' if professional else 'YOUR PRE-GAME CHECKPOINT')
            self.route_title.set_text('Temporary session workflow' if professional else 'A good session has a return path.')
            self.hero_title.set_text('System overview' if professional else 'More room.\nMore adventure.')
            self.hero_description.set_text('Review memory use and plan temporary changes.' if professional else companion[3])
            self.game_chip.set_text(companion[2].upper())
            clear(self.hero_avatar)
            if not professional:
                self.hero_avatar.append(self.avatar(companion_index, 160, custom=True))
            clear(self.profile_box)
            if professional:
                self.profile_box.append(text('SYSTEM UTILITY', 'eyebrow'))
                self.profile_box.append(text('Professional Mode', 'section-title'))
            else:
                row = box(False, 10)
                row.append(self.avatar(companion_index, 46, custom=True))
                words = box(spacing=4)
                words.append(text('YOUR CHARACTER', 'eyebrow'))
                words.append(text('Custom avatar' if p['custom_avatar'] else companion[1], 'section-title'))
                row.append(words)
                self.profile_box.append(row)
                count = sum(key in p['milestones'] for key, *_ in MILESTONES)
                self.profile_box.append(text(f'{tier(p)} · {count}/5 habits learned', 'muted small'))
                self.profile_box.append(Gtk.ProgressBar(fraction=count / 5))
            clear(self.milestone_list)
            for key, title, goal, _meaning in MILESTONES:
                done = key in p['milestones']
                row = text(('✓  ' if done else '○  ') + title, 'accent' if done else 'muted')
                row.set_tooltip_text(goal)
                self.milestone_list.append(row)
            sessions = sorted(p['sessions'].values(), key=lambda s: s['completed'], reverse=True)
            if sessions:
                self.history_text.set_text(f'{len(sessions)} restored session' + ('s' if len(sessions) != 1 else '') +
                    '\n\n' + '\n'.join(datetime.fromtimestamp(s['completed']).strftime('%d %b · %H:%M  ✓ Restored') for s in sessions[:3]))
            else:
                self.history_text.set_text('Your first safe return starts here.\n\nCompleted sessions appear after their original settings have been restored.')
            cutoff = datetime.now() - timedelta(days=7)
            weekly = sum(s['completed'] >= cutoff.timestamp() for s in sessions)
            self.week_text.set_text(f'{weekly} safe returns in the last 7 days')
            clear(self.theme_row)
            unlocked = unlocked_themes(p)
            for theme, requirement in zip(THEMES, ('Always available', 'Complete a scan', 'Open a valid review', 'Restore a completed session')):
                button = Gtk.Button(label=('✓ ' if p['theme'] == theme else '') + theme.title())
                button.set_sensitive(theme in unlocked)
                button.set_tooltip_text(requirement)
                button.connect('clicked', lambda _w, t=theme: self.preference('theme', t))
                self.theme_row.append(button)
            self.reset_avatar.set_sensitive(p['custom_avatar'])
            self.profile_notice.set_text(self.profile_warning or f'Progress and preferences: {self.profile.path}\n'
                'No streak penalties, leaderboards, accounts or telemetry. Character artwork is cached locally; source credits are included with the app.')
        finally:
            self._refreshing = False

    def refresh_session_ui(self, session):
        active = bool(session and session['status'] != 'restored')
        restored = bool(session and session.get('activation_complete') and session['status'] == 'restored')
        reviewed = (self._reviewed_plan is not None and self._reviewed_plan == tuple(sorted(self.choices.items())))
        done = [bool(self.snapshot), reviewed or bool(session and session.get('activation_complete')),
                bool(session and session.get('activation_complete')), restored]
        for step, completed in zip(self.steps, done):
            if completed:
                step.add_css_class('done')
            else:
                step.remove_css_class('done')
        count = len(self.choices)
        self.footer_text.set_text(f'{count} action' + ('s' if count != 1 else '') + ' selected · Review before applying.' if count else
                                 'Choose what to pause. Keep a way back.')
        if active:
            self.route_note.set_text('Temporary changes are active or need recovery. Restore now is always available.')
        elif restored:
            self.route_note.set_text('Original settings restored. Your desktop is ready for whatever comes next.')
        else:
            self.route_note.set_text('Scan → review exact changes → play → restore. No process is selected automatically.')
        # The timer can update progress while the GUI is closed or idle.
        try:
            stamp = self.profile.path.stat().st_mtime_ns if self.profile.path.exists() else None
            if stamp != self._profile_stamp:
                previous = set(self.profile_state['milestones'])
                self.profile_state = self.profile.read()
                self._profile_stamp = stamp
                new = set(self.profile_state['milestones']) - previous
                if new:
                    names = ', '.join(m[1] for m in MILESTONES if m[0] in new)
                    self.feedback(f'Milestone reached: {names}', celebrate=True)
                self.refresh_profile()
        except Exception as exc:
            log.warning('Optional progress refresh failed: %s', exc)
        status = (session.get('id'), session.get('status')) if session else None
        if (self._last_session_status and status and self._last_session_status[0] == status[0] and
                self._last_session_status[1] != 'restored' and status[1] == 'restored'):
            self.feedback('✓ Original settings restored. Safe return complete.')
        self._last_session_status = status

    def feedback(self, message, celebrate=False):
        if not hasattr(self, 'toast'):
            return
        if celebrate and self.profile_state['professional']:
            return
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self.toast.add_toast(toast)
        if celebrate and self.profile_state['sound'] and not self.profile_state['professional']:
            def sound():
                try:
                    run(['/usr/bin/paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'], timeout=3)
                except Exception:
                    log.debug('Optional milestone sound unavailable')
            threading.Thread(target=sound, daemon=True).start()

    def add_shortcuts(self):
        for name, shortcut, callback in [
            ('search', '<Control>f', self.shortcut_search),
            ('rescan', '<Control>r', self.shortcut_scan),
            ('restore', '<Control><Shift>r', lambda: self.restore(None) if not self.busy else None),
            ('preferences', '<Control>comma', lambda: self.navigate('settings'))]:
            action = Gio.SimpleAction.new(name, None)
            action.connect('activate', lambda _a, _p, cb=callback: cb())
            self.add_action(action)
            self.set_accels_for_action('app.' + name, [shortcut])

    def shortcut_search(self):
        self.navigate('inventory')
        self.search.grab_focus()
        self.profile_action(lambda: self.profile.award('shortcut'))

    def shortcut_scan(self):
        if not self.busy:
            self.start_scan()
            self.profile_action(lambda: self.profile.award('shortcut'))

    def import_avatar(self, _button):
        dialog = Gtk.FileDialog(title='Choose your avatar')
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filter_ = Gtk.FileFilter()
        filter_.set_name('PNG or JPEG images')
        filter_.add_mime_type('image/png')
        filter_.add_mime_type('image/jpeg')
        filters.append(filter_)
        dialog.set_filters(filters)
        def chosen(dialog, result):
            try:
                selected = dialog.open_finish(result)
                source = selected.get_path()
                if not source:
                    raise ValueError('Choose a local image file')
                self.save_custom_avatar(source)
                self.feedback('Custom avatar saved locally.')
            except GLib.Error as exc:
                if not exc.matches(Gtk.dialog_error_quark(), Gtk.DialogError.DISMISSED):
                    self.message('Avatar could not be loaded', str(exc))
            except Exception as exc:
                self.message('Avatar could not be loaded', str(exc))
        dialog.open(self.window, None, chosen)

    def save_custom_avatar(self, source):
        path = Path(source)
        if path.stat().st_size > 10 * 1024 * 1024:
            raise ValueError('Choose an image smaller than 10 MiB')
        info, width, height = GdkPixbuf.Pixbuf.get_file_info(source)
        if not info or info.get_name() not in ('png', 'jpeg') or width * height > 25_000_000:
            raise ValueError('Choose a PNG/JPEG image under 25 megapixels')
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(source, 384, 384, True)
        destination = self.profile.directory / 'avatar.png'
        temporary = destination.with_suffix('.tmp')
        pixbuf.savev(str(temporary), 'png', [], [])
        temporary.chmod(0o600)
        temporary.replace(destination)
        self.profile_action(lambda: self.profile.preference('custom_avatar', True))
