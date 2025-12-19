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

# Ensure GTK 3 compatibility
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GObject, GLib, Gdk

# Try to import AppIndicator3 for system tray support
try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3
except (ValueError, ImportError):
    AppIndicator3 = None

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

class AppWindow(Gtk.Window):
    """
    Main GTK Application Window.
    """
    def __init__(self):
        Gtk.Window.__init__(self, title="ParlaType - Speech to Text")
        self.set_border_width(10)
        self.set_default_size(400, 300)
        self.set_position(Gtk.WindowPosition.CENTER)

        # Main Layout
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        # Status Label
        self.status_label = Gtk.Label(label="Initializing...")
        vbox.pack_start(self.status_label, False, False, 0)

        # Text Area for logs/transcript
        self.textview = Gtk.TextView()
        self.textview.set_editable(False)
        self.textview.set_cursor_visible(False)
        self.textbuffer = self.textview.get_buffer()
        
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(self.textview)
        vbox.pack_start(scrolled_window, True, True, 0)

        # Buttons
        hbox = Gtk.Box(spacing=6)
        vbox.pack_start(hbox, False, False, 0)

        self.start_button = Gtk.Button(label="Start")
        self.start_button.connect("clicked", self.on_start_clicked)
        hbox.pack_start(self.start_button, True, True, 0)

        self.stop_button = Gtk.Button(label="Stop")
        self.stop_button.connect("clicked", self.on_stop_clicked)
        self.stop_button.set_sensitive(False)
        hbox.pack_start(self.stop_button, True, True, 0)

        self.hide_button = Gtk.Button(label="Hide")
        self.hide_button.connect("clicked", self.on_hide_clicked)
        hbox.pack_start(self.hide_button, True, True, 0)

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
        if AppIndicator3:
            self.indicator = AppIndicator3.Indicator.new(
                "parlatype-app",
                "microphone",
                AppIndicator3.IndicatorCategory.APPLICATION_STATUS
            )
            self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
            self.indicator.set_menu(self.build_menu())
        else:
            # Fallback for systems without AppIndicator
            self.status_icon = Gtk.StatusIcon()
            self.status_icon.set_from_icon_name("microphone")
            self.status_icon.set_tooltip_text("ParlaType")
            self.status_icon.connect("popup-menu", self.on_tray_popup)
            self.status_icon.set_visible(True)

    def build_menu(self):
        menu = Gtk.Menu()
        
        # Pause/Resume
        self.pause_item = Gtk.CheckMenuItem(label="Pause")
        self.pause_item.set_active(True) # Starts paused
        self.pause_item.connect("toggled", self.on_pause_toggled)
        menu.append(self.pause_item)
        
        # Separator
        menu.append(Gtk.SeparatorMenuItem())

        item_show = Gtk.MenuItem(label="Show/Hide")
        item_show.connect("activate", self.toggle_window)
        menu.append(item_show)

        item_quit = Gtk.MenuItem(label="Quit")
        item_quit.connect("activate", Gtk.main_quit)
        menu.append(item_quit)
        
        menu.show_all()
        return menu

    def on_pause_toggled(self, widget):
        if widget.get_active():
            self.on_stop_clicked(None)
        else:
            self.on_start_clicked(None)

    def on_start_clicked(self, widget):
        self.transcriber.start_listening()
        self.start_button.set_sensitive(False)
        self.stop_button.set_sensitive(True)
        
        # Sync menu item if triggered by button
        if hasattr(self, 'pause_item') and self.pause_item.get_active():
             self.pause_item.set_active(False)

        self._update_icon("microphone-sensitivity-high")

    def on_stop_clicked(self, widget):
        self.transcriber.stop_listening()
        self.start_button.set_sensitive(True)
        self.stop_button.set_sensitive(False)
        
        # Sync menu item if triggered by button
        if hasattr(self, 'pause_item') and not self.pause_item.get_active():
             self.pause_item.set_active(True)

        self._update_icon("microphone-sensitivity-muted")

    def _update_icon(self, icon_name):
        if AppIndicator3 and hasattr(self, 'indicator'):
            self.indicator.set_icon(icon_name)
        elif hasattr(self, 'status_icon'):
            self.status_icon.set_from_icon_name(icon_name)

    def on_hide_clicked(self, widget):
        self.hide()

    def update_status(self, message):
        self.status_label.set_text(message)

    def update_text(self, text, is_final):
        if is_final:
            end_iter = self.textbuffer.get_end_iter()
            self.textbuffer.insert(end_iter, f"\n[Final]: {text}")
            # Auto-scroll to bottom
            mark = self.textbuffer.create_mark("end", end_iter, False)
            self.textview.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)
        else:
            self.status_label.set_text(f"Listening: {text}")

    def on_tray_popup(self, icon, button, time):
        menu = self.build_menu()
        menu.popup(None, None, None, self.status_icon, button, time)

    def toggle_window(self, widget):
        if self.is_visible():
            self.hide()
        else:
            self.show_all()
            self.present()

    def on_destroy(self, widget):
        self.transcriber.stop_app()
        Gtk.main_quit()

if __name__ == "__main__":
    win = AppWindow()
    win.connect("destroy", win.on_destroy)
    win.show_all()
    Gtk.main()
