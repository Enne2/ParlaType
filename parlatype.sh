#!/bin/bash
# ParlaType Launcher

APP_DIR="/usr/share/parlatype"
VENV_DIR="$APP_DIR/venv"

# Check if venv exists, if not (though it should be created by RPM %post), try to create it or fail
if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found at $VENV_DIR."
    echo "Attempting to create it (may require sudo)..."
    sudo python3 -m venv "$VENV_DIR"
    sudo "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"
fi

# Run the application
source "$VENV_DIR/bin/activate"
python3 "$APP_DIR/main.py" "$@"
