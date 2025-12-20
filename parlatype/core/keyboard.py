import time
from evdev import UInput, ecodes as e
from .config import CHAR_MAP

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
