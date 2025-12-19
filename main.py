#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ParlaType - Speech-to-Text Virtual Keyboard (Italian Edition)
=============================================================

ParlaType is a Python application that uses offline speech recognition (Vosk)
to transcribe speech and automatically type it as if it were a physical keyboard.

This version is specifically tuned for the **Italian language**, including:
- Pre-configured Italian Vosk model.
- Custom key mapping for Italian accented characters (à, è, é, ì, ò, ù).

Author: Matteo Benedetto (Enne2)
GitHub: https://github.com/Enne2
Website: http://enne2.net
License: MIT (or see repository for details)
"""

import sys
import os
import json
import time
import threading
import gi
import pyaudio
from vosk import Model, KaldiRecognizer
from evdev import UInput, ecodes as e

# Ensure GTK 4 compatibility
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1') # Using libadwaita for a modern look if available
from gi.repository import Gtk, Gdk, GLib, Gio, Adw

# Tray icon support via trayer
try:
    import trayer
except ImportError:
    trayer = None

# --- Configuration ---
def get_model_path():
    # Check local path (development or bundled)
    local_path = os.path.join(os.path.dirname(__file__), "models/vosk-model-it-0.22")
    if os.path.exists(local_path):
        return local_path
    
    # Check user data path
    user_path = os.path.expanduser("~/.local/share/parlatype/models/vosk-model-it-0.22")
    if os.path.exists(user_path):
        return user_path
        
    # Check system path
    system_path = "/usr/share/parlatype/models/vosk-model-it-0.22"
    if os.path.exists(system_path):
        return system_path
        
    return None

MODEL_PATH = get_model_path()
SAMPLE_RATE = 16000
FRAMES_PER_BUFFER = 8000
READ_CHUNK_SIZE = 4000

# Character mapping for Italian Keyboard Layout
# Maps characters to evdev key codes
CHAR_MAP = {
    'a': e.KEY_A, 'b': e.KEY_B, 'c': e.KEY_C, 'd': e.KEY_D, 'e': e.KEY_E,
    'f': e.KEY_F, 'g': e.KEY_G, 'h': e.KEY_H, 'i': e.KEY_I, 'j': e.KEY_J,
    'k': e.KEY_K, 'l': e.KEY_L, 'm': e.KEY_M, 'n': e.KEY_N, 'o': e.KEY_O,
    'p': e.KEY_P, 'q': e.KEY_Q, 'r': e.KEY_R, 's': e.KEY_S, 't': e.KEY_T,
    'u': e.KEY_U, 'v': e.KEY_V, 'w': e.KEY_W, 'x': e.KEY_X, 'y': e.KEY_Y,
    'z': e.KEY_Z,
    '0': e.KEY_0, '1': e.KEY_1, '2': e.KEY_2, '3': e.KEY_3, '4': e.KEY_4,
    '5': e.KEY_5, '6': e.KEY_6, '7': e.KEY_7, '8': e.KEY_8, '9': e.KEY_9,
    ' ': e.KEY_SPACE, '.': e.KEY_DOT, ',': e.KEY_COMMA, 
    '-': e.KEY_SLASH, '/': e.KEY_7, ';': e.KEY_COMMA, ':': e.KEY_DOT,
    '\n': e.KEY_ENTER
}

class VirtualKeyboard:
    """
    Handles virtual keyboard input injection using evdev.
    """
    def __init__(self):
        try:
            self.ui = UInput(name="Vosk-Keyboard-App")
            self.available = True
        except Exception as ex:
            print(f"[VirtualKeyboard] Error initializing uinput: {ex}")
            print("[VirtualKeyboard] Ensure you have permissions to access /dev/uinput (e.g., add user to 'input' group).")
            self.available = False

    def type_string(self, text: str):
        """
        Types a string character by character.
        """
        if not self.available:
            return
        
        for char in text:
            self._type_char(char)

    def _type_char(self, char: str):
        """
        Types a single character, handling shift and special Italian characters.
        """
        lower_char = char.lower()
        code = None
        shift = False

        # Handle Italian special characters and punctuation
        if char == 'à': code = e.KEY_APOSTROPHE
        elif char == 'è': code = e.KEY_LEFTBRACE
        elif char == 'é': 
            code = e.KEY_LEFTBRACE
            shift = True
        elif char == 'ì': code = e.KEY_EQUAL
        elif char == 'ò': code = e.KEY_SEMICOLON
        elif char == 'ù': code = e.KEY_BACKSLASH
        elif char == "'": code = e.KEY_MINUS
        elif lower_char in CHAR_MAP:
            code = CHAR_MAP[lower_char]
            if char.isupper():
                shift = True
        
        if code:
            self._send_key(code, shift)

    def _send_key(self, code, shift: bool):
        """
        Sends the key event to the virtual device.
        """
        if shift:
            self.ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 1)
        
        self.ui.write(e.EV_KEY, code, 1)
        self.ui.write(e.EV_KEY, code, 0)
        
        if shift:
            self.ui.write(e.EV_KEY, e.KEY_LEFTSHIFT, 0)
        
        self.ui.syn()
        time.sleep(0.01) # Small delay to ensure OS registers the keypress

    def close(self):
        """
        Closes the uinput device.
        """
        if self.available:
            self.ui.close()

class Transcriber(threading.Thread):
    """
    Background thread for audio recording and speech recognition.
    """
    def __init__(self, update_callback, status_callback):
        super().__init__()
        self.update_callback = update_callback
        self.status_callback = status_callback
        self.running = False
        self.paused = True
        self.daemon = True
        self.keyboard = VirtualKeyboard()
        self.model = None
        
        # Load Vosk Model
        self._load_model()

    def _load_model(self):
        if not os.path.exists(MODEL_PATH):
            self.status_callback(f"Error: Model not found at {MODEL_PATH}")
            self.model = None
        else:
            try:
                self.model = Model(MODEL_PATH)
                self.status_callback("Model loaded. Ready.")
            except Exception as e:
                self.status_callback(f"Error loading model: {e}")
                self.model = None

    def run(self):
        if not self.model:
            return

        self.rec = KaldiRecognizer(self.model, SAMPLE_RATE)
        self.p = pyaudio.PyAudio()
        
        stream = None
        try:
            stream = self.p.open(format=pyaudio.paInt16, 
                               channels=1, 
                               rate=SAMPLE_RATE, 
                               input=True, 
                               frames_per_buffer=FRAMES_PER_BUFFER)
            stream.start_stream()
            self.running = True
            
            while self.running:
                if self.paused:
                    time.sleep(0.1)
                    continue

                data = stream.read(READ_CHUNK_SIZE, exception_on_overflow=False)
                if len(data) == 0:
                    break
                
                if self.rec.AcceptWaveform(data):
                    res = json.loads(self.rec.Result())
                    text = res['text']
                    if text:
                        GLib.idle_add(self.update_callback, text, True)
                        self.keyboard.type_string(text + " ")
                else:
                    partial = json.loads(self.rec.PartialResult())
                    if partial['partial']:
                        GLib.idle_add(self.update_callback, partial['partial'], False)

        except Exception as e:
            GLib.idle_add(self.status_callback, f"Audio Error: {e}")
        finally:
            if stream:
                stream.stop_stream()
                stream.close()
            self.p.terminate()
            self.keyboard.close()

    def start_listening(self):
        self.paused = False
        self.status_callback("Listening...")

    def stop_listening(self):
        self.paused = True
        self.status_callback("Paused.")

    def stop_app(self):
        self.running = False

class AppWindow(Adw.ApplicationWindow):
    """
    Main GTK 4 Application Window using Libadwaita.
    """
    def __init__(self, app):
        super().__init__(application=app, title="ParlaType - Speech to Text")
        self.set_default_size(450, 350)

        # Main Layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_content(vbox)

        # Header Bar (Title and Close button)
        header = Adw.HeaderBar()
        vbox.append(header)

        # Content Area
        content_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_vbox.set_margin_top(12)
        content_vbox.set_margin_bottom(12)
        content_vbox.set_margin_start(12)
        content_vbox.set_margin_end(12)
        vbox.append(content_vbox)

        # Status Label
        self.status_label = Gtk.Label(label="Initializing...")
        self.status_label.set_halign(Gtk.Align.START)
        content_vbox.append(self.status_label)

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
            # Use lambda *args to handle any number of arguments from trayer
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
            timestamp = time.strftime('%H:%M:%S')
            end_iter = self.textbuffer.get_end_iter()
            self.textbuffer.insert(end_iter, f"\n[{timestamp}]: {text}")
            # Auto-scroll to bottom
            self.textview.scroll_to_iter(self.textbuffer.get_end_iter(), 0.0, False, 0.0, 0.0)
        else:
            self.status_label.set_text(f"Listening: {text}")

    def toggle_window(self):
        if self.get_visible():
            self.set_visible(False)
        else:
            self.set_visible(True)
            self.present()

class ParlaTypeApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="net.enne2.parlatype",
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = AppWindow(self)
        win.present()

if __name__ == "__main__":
    app = ParlaTypeApp()
    sys.exit(app.run(sys.argv))
