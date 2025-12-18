#!/bin/bash

# KeyTalk Installation Script
# Generates a .desktop file with correct paths and installs it.

# Get the absolute path of the directory containing this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_PATH="$DIR/.venv"
PYTHON_EXEC="$VENV_PATH/bin/python"
MAIN_SCRIPT="$DIR/main.py"
ICON_PATH="$DIR/keytalk.svg"
DESKTOP_FILE_PATH="$HOME/.local/share/applications/keytalk.desktop"

echo "=== KeyTalk Installer ==="
echo "Project directory detected: $DIR"

# 1. Check for Virtual Environment
if [ ! -f "$PYTHON_EXEC" ]; then
    echo "Warning: Virtual environment not found at $VENV_PATH"
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_PATH"
    
    if [ $? -ne 0 ]; then
        echo "Error creating virtual environment."
        exit 1
    fi
    
    echo "Installing dependencies..."
    "$PYTHON_EXEC" -m pip install -r "$DIR/requirements.txt"
    
    if [ $? -ne 0 ]; then
        echo "Error installing dependencies. Please check requirements.txt"
        exit 1
    fi
else
    echo "Virtual environment found."
fi

# 2. Generate .desktop file
echo "Generating $DESKTOP_FILE_PATH..."

mkdir -p "$HOME/.local/share/applications"

cat <<EOF > "$DESKTOP_FILE_PATH"
[Desktop Entry]
Name=KeyTalk
Comment=Speech-to-Text Virtual Keyboard
Exec=$PYTHON_EXEC $MAIN_SCRIPT
Icon=$ICON_PATH
Terminal=false
Type=Application
Categories=Utility;Accessibility;
StartupNotify=true
EOF

# 3. Update Desktop Database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications"
    echo "Desktop database updated."
else
    echo "Warning: 'update-desktop-database' not found. You might need to log out and back in to see the app."
fi

echo "=== Installation Complete ==="
echo "You can now launch KeyTalk from your applications menu."
echo "Note: Ensure your user is in the 'input' group to access the virtual keyboard:"
echo "sudo usermod -aG input \$USER"
