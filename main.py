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
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

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
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")
if not os.path.exists(PROMPTS_DIR):
    os.makedirs(PROMPTS_DIR)

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

class LLMCorrector:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.history = []
        self.system_prompt = self.load_prompt("default.txt")
        self.enabled = False

    def load_prompt(self, filename):
        try:
            with open(os.path.join(PROMPTS_DIR, filename), 'r') as f:
                return f.read()
        except Exception as e:
            print(f"Error loading prompt {filename}: {e}")
            return "Sei un assistente che corregge trascrizioni."

    def save_prompt(self, filename, content):
        try:
            with open(os.path.join(PROMPTS_DIR, filename), 'w') as f:
                f.write(content)
            self.system_prompt = content
            return True
        except Exception as e:
            print(f"Error saving prompt {filename}: {e}")
            return False

    def correct(self, text):
        if not self.enabled or not text.strip():
            self.history.append(text)
            if len(self.history) > 10:
                self.history.pop(0)
            return text

        context = "\n".join(self.history)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Context:\n{context}\n\nPhrase to correct:\n{text}"}
        ]

        try:
            # Attempt with max_completion_tokens (for reasoning models)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_completion_tokens=150
            )
            corrected_text = response.choices[0].message.content.strip()
            self.history.append(corrected_text)
            if len(self.history) > 10:
                self.history.pop(0)
            return corrected_text
        except Exception as e:
            print(f"LLM Error (max_completion_tokens): {e}")
            # Fallback to max_tokens (for standard models)
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=150
                )
                corrected_text = response.choices[0].message.content.strip()
                self.history.append(corrected_text)
                if len(self.history) > 10:
                    self.history.pop(0)
                return corrected_text
            except Exception as e2:
                print(f"LLM Error (max_tokens): {e2}")
                return text

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
                        # Typing is now handled in update_callback (AppWindow) after optional correction
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

    def start_listening(self):
        self.paused = False
        self.status_callback("Listening...")

    def stop_listening(self):
        self.paused = True
        self.status_callback("Paused.")

    def stop_app(self):
        self.running = False

class InputDialog(Gtk.Window):
    def __init__(self, parent, title, message, callback):
        super().__init__(title=title)
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(300, 150)
        self.callback = callback
        
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        vbox.set_margin_start(20)
        vbox.set_margin_end(20)
        self.set_child(vbox)
        
        lbl = Gtk.Label(label=message)
        vbox.append(lbl)
        
        self.entry = Gtk.Entry()
        vbox.append(self.entry)
        
        hbox = Gtk.Box(spacing=10)
        hbox.set_halign(Gtk.Align.CENTER)
        vbox.append(hbox)
        
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda x: self.close())
        hbox.append(btn_cancel)
        
        btn_ok = Gtk.Button(label="OK")
        btn_ok.connect("clicked", self.on_ok)
        hbox.append(btn_ok)
        
    def on_ok(self, btn):
        text = self.entry.get_text()
        if text:
            self.callback(text)
        self.close()

class PromptSettingsWindow(Gtk.Window):
    def __init__(self, parent, llm_corrector):
        super().__init__(title="Prompt Settings")
        self.set_transient_for(parent)
        self.set_modal(True)
        self.set_default_size(600, 400)
        self.llm_corrector = llm_corrector

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        self.set_child(vbox)

        # File selection
        hbox_file = Gtk.Box(spacing=10)
        vbox.append(hbox_file)
        
        self.file_combo = Gtk.ComboBoxText()
        self.refresh_file_list()
        self.file_combo.set_active(0)
        self.file_combo.connect("changed", self.on_file_changed)
        hbox_file.append(self.file_combo)

        new_btn = Gtk.Button(label="New")
        new_btn.connect("clicked", self.on_new_clicked)
        hbox_file.append(new_btn)

        # Text Area
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        vbox.append(scrolled)

        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD)
        self.textbuffer = self.textview.get_buffer()
        self.textbuffer.set_text(self.llm_corrector.system_prompt)
        scrolled.set_child(self.textview)

        # Save Button
        save_btn = Gtk.Button(label="Save & Apply")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self.on_save_clicked)
        vbox.append(save_btn)

    def refresh_file_list(self):
        self.file_combo.remove_all()
        files = [f for f in os.listdir(PROMPTS_DIR) if f.endswith(".txt")]
        for f in files:
            self.file_combo.append_text(f)
        if not files:
            self.file_combo.append_text("default.txt")

    def on_file_changed(self, widget):
        filename = widget.get_active_text()
        if filename:
            content = self.llm_corrector.load_prompt(filename)
            self.textbuffer.set_text(content)

    def on_new_clicked(self, widget):
        def on_filename_entered(filename):
            if not filename.endswith(".txt"):
                filename += ".txt"
            # Clear text buffer for new prompt
            self.textbuffer.set_text("")
            # Add to combo and select
            self.file_combo.append_text(filename)
            self.file_combo.set_active_id(filename) # This might not work if id not set, let's just select last
            # Since we just appended, it should be the last one
            # But we need to handle the combo logic. 
            # Simpler: just set the text in combo entry if it was editable, but it's not.
            # Let's refresh list? No, file doesn't exist yet.
            # We'll just pretend it's selected by setting a flag or just letting the user type.
            # Actually, the save button uses the combo active text.
            # We need to make sure the combo shows this new filename.
            # ComboBoxText doesn't easily allow setting arbitrary text if not in model.
            # So we add it.
            # But wait, refresh_file_list clears it.
            # Let's just add it.
            # self.file_combo.append_text(filename) # Already done above
            # Select it
            # To select by text in ComboBoxText is tricky without ID.
            # Let's iterate to find it.
            model = self.file_combo.get_model()
            iter_ = model.get_iter_first()
            while iter_:
                if model.get_value(iter_, 0) == filename:
                    self.file_combo.set_active_iter(iter_)
                    break
                iter_ = model.iter_next(iter_)
        
        InputDialog(self, "New Prompt", "Enter filename (e.g. my_prompt):", on_filename_entered).present()

    def on_save_clicked(self, widget):
        start, end = self.textbuffer.get_bounds()
        content = self.textbuffer.get_text(start, end, True)
        filename = self.file_combo.get_active_text()
        if not filename:
            filename = "custom.txt" # Fallback
        
        if self.llm_corrector.save_prompt(filename, content):
            self.close()

class AppWindow(Adw.ApplicationWindow):
    """
    Main GTK 4 Application Window using Libadwaita.
    """
    def __init__(self, app):
        super().__init__(application=app, title="ParlaType - Speech to Text")
        self.set_default_size(450, 350)
        
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
        menu.append("Prompt Settings", "win.prompt_settings")
        
        menu_btn = Gtk.MenuButton()
        menu_btn.set_icon_name("open-menu-symbolic")
        menu_btn.set_menu_model(menu)
        header.pack_end(menu_btn)
        
        # Actions
        action = Gio.SimpleAction.new("prompt_settings", None)
        action.connect("activate", self.on_prompt_settings)
        self.add_action(action)

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

    def on_prompt_settings(self, action, param):
        win = PromptSettingsWindow(self, self.llm_corrector)
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
                self.status_label.set_text("Correcting with LLM...")
                # Run in a separate thread to avoid blocking UI
                threading.Thread(target=self._process_correction, args=(text,)).start()
            else:
                self._finalize_text(text)
        else:
            self.status_label.set_text(f"Listening: {text}")

    def _process_correction(self, text):
        corrected = self.llm_corrector.correct(text)
        GLib.idle_add(self._finalize_text, corrected)

    def _finalize_text(self, text):
        timestamp = time.strftime('%H:%M:%S')
        end_iter = self.textbuffer.get_end_iter()
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
