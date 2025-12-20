import os
import fcntl
from evdev import ecodes as e
from dotenv import load_dotenv

# --- Paths and Environment ---
CONFIG_DIR = os.path.expanduser("~/.config/parlatype")
ENV_PATH = os.path.join(CONFIG_DIR, ".env")

def init_config():
    # Load environment variables
    # Try loading from user config directory first
    load_dotenv(ENV_PATH)
    # Also try default locations (cwd, etc) as fallback/override
    load_dotenv()

def get_model_path():
    # Check local path (development or bundled)
    local_path = os.path.join(os.path.dirname(__file__), "../../models/vosk-model-it-0.22")
    if os.path.exists(local_path):
        return os.path.abspath(local_path)
    
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

# Prompts directories
SYSTEM_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "../../prompts")
PROMPTS_DIR = os.path.expanduser("~/.local/share/parlatype/prompts")

if not os.path.exists(PROMPTS_DIR):
    try:
        os.makedirs(PROMPTS_DIR)
    except Exception:
        pass

# Character mapping for Italian Keyboard Layout
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

# Single Instance Lock
LOCK_FILE = os.path.join(os.path.expanduser("~/.cache"), "parlatype.lock")

def request_lock():
    try:
        lock_dir = os.path.dirname(LOCK_FILE)
        if not os.path.exists(lock_dir):
            os.makedirs(lock_dir)
        fp = open(LOCK_FILE, 'w')
        fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fp
    except (IOError, OSError):
        return None
