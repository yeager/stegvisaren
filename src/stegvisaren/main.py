import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gdk, Gio
import gettext, locale, os, json, time

__version__ = "0.1.0"
APP_ID = "se.danielnylander.stegvisaren"
LOCALE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'share', 'locale')
if not os.path.isdir(LOCALE_DIR): LOCALE_DIR = "/usr/share/locale"
try:
    locale.bindtextdomain(APP_ID, LOCALE_DIR)
    gettext.bindtextdomain(APP_ID, LOCALE_DIR)
    gettext.textdomain(APP_ID)
except Exception: pass
_ = gettext.gettext
def N_(s): return s


TEMPLATES = [
    {"name": N_("Brush Teeth"), "icon": "🪥", "steps": [N_("Get toothbrush"), N_("Add toothpaste"), N_("Brush top teeth"), N_("Brush bottom teeth"), N_("Spit and rinse"), N_("Done!")]},
    {"name": N_("Get Dressed"), "icon": "👕", "steps": [N_("Underwear"), N_("Socks"), N_("Pants"), N_("Shirt"), N_("Check in mirror")]},
    {"name": N_("Pack School Bag"), "icon": "🎒", "steps": [N_("Books"), N_("Pencil case"), N_("Lunch box"), N_("Water bottle"), N_("Close bag")]},
    {"name": N_("Bedtime"), "icon": "🌙", "steps": [N_("Put on pajamas"), N_("Brush teeth"), N_("Go to bathroom"), N_("Get into bed"), N_("Read a story"), N_("Lights off")]},
]

class MainWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title(_('Step Guide'))
        self.set_default_size(500, 550)
        self._current_step = 0
        self._current_task = None
        
        
        # Easter egg state
        self._egg_clicks = 0
        self._egg_timer = None

        header = Adw.HeaderBar()
        
        # Add clickable app icon for easter egg
        app_btn = Gtk.Button()
        app_btn.set_icon_name("se.danielnylander.stegvisaren")
        app_btn.add_css_class("flat")
        app_btn.set_tooltip_text(_("Stegvisaren"))
        app_btn.connect("clicked", self._on_icon_clicked)
        header.pack_start(app_btn)

        menu_btn = Gtk.MenuButton(icon_name='open-menu-symbolic')
        menu = Gio.Menu()
        menu.append(_('About'), 'app.about')
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)
        
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        # Template picker
        picker = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        picker.set_margin_top(24)
        picker.set_margin_start(24)
        picker.set_margin_end(24)
        picker.set_margin_bottom(24)
        
        title = Gtk.Label(label=_('What do you need to do?'))
        title.add_css_class('title-2')
        picker.append(title)
        
        for i, tmpl in enumerate(TEMPLATES):
            btn = Gtk.Button()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            box.set_margin_top(8)
            box.set_margin_bottom(8)
            box.set_margin_start(12)
            box.set_margin_end(12)
            icon = Gtk.Label(label=tmpl['icon'])
            icon.add_css_class('title-2')
            box.append(icon)
            info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            info.set_hexpand(True)
            name = Gtk.Label(label=_(tmpl['name']), xalign=0)
            name.add_css_class('title-4')
            info.append(name)
            count = Gtk.Label(label=_('%d steps') % len(tmpl['steps']), xalign=0)
            count.add_css_class('dim-label')
            info.append(count)
            box.append(info)
            btn.set_child(box)
            btn.add_css_class('card')
            btn.connect('clicked', self._start_task, i)
            picker.append(btn)
        
        self._stack.add_titled(picker, 'picker', _('Tasks'))
        
        # Step view
        step_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        step_page.set_valign(Gtk.Align.CENTER)
        step_page.set_margin_top(32)
        step_page.set_margin_bottom(32)
        step_page.set_margin_start(32)
        step_page.set_margin_end(32)
        
        self._step_icon = Gtk.Label()
        self._step_icon.add_css_class('title-1')
        step_page.append(self._step_icon)
        
        self._step_num = Gtk.Label()
        self._step_num.add_css_class('dim-label')
        step_page.append(self._step_num)
        
        self._step_text = Gtk.Label()
        self._step_text.add_css_class('title-1')
        self._step_text.set_wrap(True)
        self._step_text.set_justify(Gtk.Justification.CENTER)
        step_page.append(self._step_text)
        
        self._progress = Gtk.ProgressBar()
        step_page.append(self._progress)
        
        btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btns.set_halign(Gtk.Align.CENTER)
        
        self._done_btn = Gtk.Button(label=_('✓ Done!'))
        self._done_btn.add_css_class('suggested-action')
        self._done_btn.add_css_class('pill')
        self._done_btn.connect('clicked', self._next_step)
        btns.append(self._done_btn)
        
        step_page.append(btns)
        
        back = Gtk.Button(label=_('← Back'))
        back.add_css_class('pill')
        back.connect('clicked', lambda b: self._stack.set_visible_child_name('picker'))
        step_page.append(back)
        
        self._stack.add_titled(step_page, 'steps', _('Steps'))
        
        # Finished page
        done_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        done_page.set_valign(Gtk.Align.CENTER)
        done_icon = Gtk.Label(label='🌟')
        done_icon.add_css_class('title-1')
        done_page.append(done_icon)
        done_text = Gtk.Label(label=_('All done! Great job!'))
        done_text.add_css_class('title-1')
        done_page.append(done_text)
        restart = Gtk.Button(label=_('Do something else'))
        restart.add_css_class('pill')
        restart.connect('clicked', lambda b: self._stack.set_visible_child_name('picker'))
        done_page.append(restart)
        self._stack.add_titled(done_page, 'done', _('Done'))
        
        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        main.append(header)
        main.append(self._stack)
        self.set_content(main)
    
    def _start_task(self, btn, index):
        self._current_task = TEMPLATES[index]
        self._current_step = 0
        self._update_step()
        self._stack.set_visible_child_name('steps')
    
    def _update_step(self):
        task = self._current_task
        steps = task['steps']
        self._step_icon.set_text(task['icon'])
        self._step_num.set_text(_('Step %d of %d') % (self._current_step + 1, len(steps)))
        self._step_text.set_text(_(steps[self._current_step]))
        self._progress.set_fraction((self._current_step + 1) / len(steps))
    
    def _next_step(self, btn):
        steps = self._current_task['steps']
        if self._current_step < len(steps) - 1:
            self._current_step += 1
            self._update_step()
        else:
            self._stack.set_visible_child_name('done')
    def _on_icon_clicked(self, *args):
        """Handle clicks on app icon for easter egg."""
        self._egg_clicks += 1
        if self._egg_timer:
            GLib.source_remove(self._egg_timer)
        self._egg_timer = GLib.timeout_add(500, self._reset_egg)
        if self._egg_clicks >= 7:
            self._trigger_easter_egg()
            self._egg_clicks = 0

    def _reset_egg(self):
        """Reset easter egg click counter."""
        self._egg_clicks = 0
        self._egg_timer = None
        return False

    def _trigger_easter_egg(self):
        """Show the secret easter egg!"""
        try:
            # Play a fun sound
            import subprocess
            subprocess.Popen(['paplay', '/usr/share/sounds/freedesktop/stereo/complete.oga'], 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            # Fallback beep
            try:
                subprocess.Popen(['pactl', 'play-sample', 'bell'], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass

        # Show confetti message
        toast = Adw.Toast.new(_("🎉 Du hittade hemligheten!"))
        toast.set_timeout(3)
        
        # Create toast overlay if it doesn't exist
        if not hasattr(self, '_toast_overlay'):
            content = self.get_content()
            self._toast_overlay = Adw.ToastOverlay()
            self._toast_overlay.set_child(content)
            self.set_content(self._toast_overlay)
        
        self._toast_overlay.add_toast(toast)



class App(Adw.Application):
    def __init__(self):
        super().__init__(application_id='se.danielnylander.stegvisaren')
        self.connect('activate', self._on_activate)
        about = Gio.SimpleAction.new('about', None)
        about.connect('activate', self._on_about)
        self.add_action(about)
    def _on_activate(self, app): MainWindow(application=app).present()
    def _on_about(self, a, p):
        Adw.AboutDialog(application_name=_('Step Guide'), application_icon=APP_ID,
            version=__version__, developer_name='Daniel Nylander',
            website='https://github.com/yeager/stegvisaren', license_type=Gtk.License.GPL_3_0,
            comments=_('Break down tasks into visual steps'),
            developers=['Daniel Nylander <daniel@danielnylander.se>']).present(self.get_active_window())


def main():
    app = App()
    app.run()

if __name__ == "__main__":
    main()
