import time
import threading
from gi.repository import Gtk, Gdk, GLib, Gio, Adw
from ..core.config import MODEL_PATH
from ..core.corrector import LLMCorrector
from ..core.keyboard import VirtualKeyboard
from ..core.transcriber import Transcriber
from .settings import SettingsWindow

# Tray icon support via trayer
try:
    import trayer
except ImportError:
    trayer = None

class AppWindow(Adw.ApplicationWindow):
    """
    Main GTK 4 Application Window using Libadwaita.
    """
    def __init__(self, app):
        super().__init__(application=app, title="ParlaType - Speech to Text")
        self.set_default_size(450, 350)
        self.set_icon_name("parlatype")
        
        self.llm_corrector = LLMCorrector()
        self.keyboard = VirtualKeyboard()

        # Main Layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(vbox)

        # Header Bar (Title and Close button)
        header = Adw.HeaderBar()
        vbox.append(header)
        
        # Menu Button in Header
        menu = Gio.Menu()
        menu.append("Settings", "app.settings")
        
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)
        
        # Actions
        action = Gio.SimpleAction.new("settings", None)
        action.connect("activate", self.on_settings)
        app.add_action(action)

        # Content Area
        content_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_vbox.set_margin_top(12)
        content_vbox.set_margin_bottom(12)
        content_vbox.set_margin_start(12)
        content_vbox.set_margin_end(12)
        vbox.append(content_vbox)

        # LLM Toggle
        hbox_llm = Gtk.Box(spacing=10)
        content_vbox.append(hbox_llm)
        
        llm_label = Gtk.Label(label="LLM Correction")
        hbox_llm.append(llm_label)
        
        self.llm_switch = Gtk.Switch()
        self.llm_switch.set_active(False)
        self.llm_switch.connect("state-set", self.on_llm_toggled)
        hbox_llm.append(self.llm_switch)

        # Status Area (Label + Spinner)
        hbox_status = Gtk.Box(spacing=10)
        content_vbox.append(hbox_status)

        self.status_label = Gtk.Label(label="Initializing...")
        self.status_label.set_halign(Gtk.Align.START)
        hbox_status.append(self.status_label)

        self.spinner = Gtk.Spinner()
        hbox_status.append(self.spinner)

        # Text Area for logs/transcript
        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textbuffer = self.textview.get_buffer()
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.set_child(self.textview)
        content_vbox.append(scrolled_window)

        # Buttons
        hbox = Gtk.Box(spacing=6)
        content_vbox.append(hbox)

        self.start_button = Gtk.Button(label="Start")
        self.start_button.add_css_class("suggested-action")
        self.start_button.connect("clicked", self.on_start_clicked)
        hbox.append(self.start_button)

        self.stop_button = Gtk.Button(label="Stop")
        self.stop_button.add_css_class("destructive-action")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        self.stop_button.set_sensitive(False)
        hbox.append(self.stop_button)

        self.hide_button = Gtk.Button(label="Hide")
        self.hide_button.connect("clicked", self.on_hide_clicked)
        hbox.append(self.hide_button)

        # Tray Icon Setup
        self._setup_tray_icon()

        # Initialize Transcriber
        if MODEL_PATH:
            self.transcriber = Transcriber(self.update_text, self.update_status)
            self.transcriber.start()
        else:
            self.update_status("Model not found! Please run 'parlatype-setup' to download it.")
            self.start_button.set_sensitive(False)
            self.stop_button.set_sensitive(False)
            self.textbuffer.set_text("Error: Vosk model not found.\n\nPlease run 'sudo parlatype-setup' in a terminal to download and install the Italian language model.")

    def _setup_tray_icon(self):
        if trayer:
            self.tray = trayer.TrayIcon(
                app_id="parlatype-app",
                title="ParlaType",
                icon_name="microphone-sensitivity-muted-symbolic"
            )
            self.tray.add_menu_item("Show/Hide", lambda *args: GLib.idle_add(self.toggle_window))
            self.tray.add_menu_separator()
            self.tray.add_menu_item("Start Listening", lambda *args: GLib.idle_add(self.on_start_clicked, None))
            self.tray.add_menu_item("Stop Listening", lambda *args: GLib.idle_add(self.on_stop_clicked, None))
            self.tray.add_menu_separator()
            self.tray.add_menu_item("Quit", lambda *args: GLib.idle_add(self.on_quit_clicked))
            
            self.tray.set_left_click(lambda *args: GLib.idle_add(self.toggle_window))
            self.tray.setup()
        else:
            print("Trayer not available. System tray icon will not be shown.")

    def on_settings(self, action, param):
        win = SettingsWindow(self, self.llm_corrector)
        win.present()

    def on_llm_toggled(self, widget, state):
        self.llm_corrector.enabled = state
        return False # Allow state change

    def on_quit_clicked(self):
        self.get_application().quit()

    def on_start_clicked(self, widget):
        self.transcriber.start_listening()
        self.start_button.set_sensitive(False)
        self.stop_button.set_sensitive(True)
        self._update_icon("microphone-sensitivity-high-symbolic")

    def on_stop_clicked(self, widget):
        self.transcriber.stop_listening()
        self.start_button.set_sensitive(True)
        self.stop_button.set_sensitive(False)
        self._update_icon("microphone-sensitivity-muted-symbolic")

    def _update_icon(self, icon_name):
        if hasattr(self, 'tray'):
            self.tray.change_icon(icon_name)

    def on_hide_clicked(self, widget):
        self.set_visible(False)

    def update_status(self, message):
        self.status_label.set_text(message)

    def update_text(self, text, is_final):
        if is_final:
            # Apply LLM correction if enabled
            if self.llm_corrector.enabled:
                self.status_label.set_text(f"Correcting: {text[:30]}...")
                self.spinner.start()
                # Run in a separate thread to avoid blocking UI
                threading.Thread(target=self._process_correction, args=(text,)).start()
            else:
                self._finalize_text(text)
        else:
            self.status_label.set_text(f"Listening: {text}")

    def _process_correction(self, text):
        corrected = self.llm_corrector.correct(text)
        GLib.idle_add(self._finalize_text, corrected, text)

    def _finalize_text(self, text, original_text=None):
        self.spinner.stop()
        timestamp = time.strftime('%H:%M:%S')
        end_iter = self.textbuffer.get_end_iter()
        
        if original_text and original_text != text:
            self.textbuffer.insert(end_iter, f"\n[{timestamp}] (Corrected): {text}")
            print(f"LLM Corrected: '{original_text}' -> '{text}'")
        else:
            self.textbuffer.insert(end_iter, f"\n[{timestamp}]: {text}")
            
        # Auto-scroll to bottom
        self.textview.scroll_to_iter(self.textbuffer.get_end_iter(), 0.0, False, 0.0, 0.0)
        self.status_label.set_text("Ready.")
        
        # Type the text
        self.keyboard.type_string(text + " ")

    def toggle_window(self):
        if self.get_visible():
            self.set_visible(False)
        else:
            self.set_visible(True)
            self.present()
