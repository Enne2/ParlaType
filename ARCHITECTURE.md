# ParlaType Architecture

This document describes the modular architecture of ParlaType, designed for maintainability, readability, and scalability.

## Directory Structure

The project is organized as a Python package named `parlatype`:

```text
parlatype/
├── __init__.py            # Package initialization
├── core/                  # Business logic and hardware interaction
│   ├── __init__.py
│   ├── config.py          # Constants, paths, and environment configuration
│   ├── transcriber.py     # Vosk speech recognition engine
│   ├── keyboard.py        # Virtual keyboard input injection (evdev)
│   └── corrector.py       # LLM-based text correction (OpenAI)
└── ui/                    # Graphical User Interface (GTK 4 / Libadwaita)
    ├── __init__.py
    ├── window.py          # Main application window
    ├── settings.py        # Settings and prompt management window
    ├── dialogs.py         # Reusable UI dialogs
    └── tray.py            # System tray icon integration
```

## Component Responsibilities

### Core Modules

- **`core.config`**: Centralized management of system paths (Vosk models, prompts, config files), environment variables (`.env`), and hardware constants like the Italian keyboard `CHAR_MAP`. It also handles the single-instance application lock.
- **`core.transcriber`**: Encapsulates the `Transcriber` thread. It manages the `pyaudio` stream and the `vosk` recognizer. It communicates with the UI via thread-safe callbacks.
- **`core.keyboard`**: Manages the `VirtualKeyboard` class using `evdev/uinput`. It handles the translation of UTF-8 characters into low-level Linux input events, with specific support for Italian accented characters.
- **`core.corrector`**: Implements the `LLMCorrector` class. It handles communication with the OpenAI API, prompt loading/saving, and maintains a short history of transcriptions for context-aware correction.

### UI Modules

- **`ui.window`**: The `AppWindow` class, inheriting from `Adw.ApplicationWindow`. It manages the main interface state (Start/Stop, LLM toggle, status display) and coordinates between the transcriber and the keyboard.
- **`ui.settings`**: The `SettingsWindow` class. Provides a tabbed interface for configuring API keys, selecting LLM models, and editing system prompts.
- **`ui.dialogs`**: Contains helper windows like `InputDialog` for creating new prompt files.
- **`ui.tray`**: (Optional) Logic for the system tray icon using the `trayer` library, allowing the app to run in the background.

## Data Flow

1.  **Audio Input**: `core.transcriber` captures audio and sends partial/final text to `ui.window`.
2.  **Processing**: If LLM correction is enabled, `ui.window` sends the text to `core.corrector`.
3.  **Output**: The final (possibly corrected) text is sent to `core.keyboard` for injection into the active window and displayed in the `ui.window` log.

## Entry Point

The root `main.py` acts as a thin wrapper that initializes the application lock and launches the `ParlaTypeApp` defined in the `parlatype` package.
