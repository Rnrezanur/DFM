#!/usr/bin/env bash
# DFM (Download Fast Manager) Ubuntu / Linux Launcher

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for virtual environment
if [ -d "$SCRIPT_DIR/.venv" ]; then
    PYTHON_EXEC="$SCRIPT_DIR/.venv/bin/python"
elif [ -d "$HOME/.dfm/venv" ]; then
    PYTHON_EXEC="$HOME/.dfm/venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="python3"
else
    echo "Error: python3 is not installed. Please install it with: sudo apt install python3"
    exit 1
fi

exec "$PYTHON_EXEC" "$SCRIPT_DIR/main.py" "$@"
