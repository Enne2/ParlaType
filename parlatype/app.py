import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gio, Adw
from .ui.window import AppWindow

class ParlaTypeApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="net.enne2.parlatype",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = AppWindow(self)
        win.present()
