#!/usr/bin/env bash
# ==============================================================================
# DFM (Download Fast Manager) - Ubuntu / Debian Installation Script
# ==============================================================================

set -e

echo "=========================================================="
echo "      Installing DFM (Download Fast Manager) on Ubuntu     "
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Install system dependencies (Python, PyQt6, FFmpeg)
echo "[1/4] Installing system prerequisites (python3, ffmpeg, pip)..."
if command -v sudo &>/dev/null; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv python3-pyqt6 ffmpeg
else
    apt-get update
    apt-get install -y python3 python3-pip python3-venv python3-pyqt6 ffmpeg
fi

# 2. Setup Python environment and dependencies
echo "[2/4] Installing Python packages (yt-dlp, requests, pyqtdarktheme)..."
# Create a dedicated virtual environment if pip refuses system-wide install (Ubuntu 23.04+ PEP 668)
VENV_DIR="$HOME/.dfm/venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR" --system-site-packages
fi
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install yt-dlp requests pyqtdarktheme

# 3. Setup CLI launcher
echo "[3/4] Configuring executable launcher..."
chmod +x "$SCRIPT_DIR/run.sh"

LAUNCHER_SCRIPT="/usr/local/bin/dfm"
if command -v sudo &>/dev/null; then
    sudo bash -c "cat << 'EOF' > $LAUNCHER_SCRIPT
#!/usr/bin/env bash
exec \"$HOME/.dfm/venv/bin/python\" \"$SCRIPT_DIR/main.py\" \"\$@\"
EOF"
    sudo chmod +x "$LAUNCHER_SCRIPT"
else
    mkdir -p "$HOME/.local/bin"
    cat << EOF > "$HOME/.local/bin/dfm"
#!/usr/bin/env bash
exec "$HOME/.dfm/venv/bin/python" "$SCRIPT_DIR/main.py" "\$@"
EOF
    chmod +x "$HOME/.local/bin/dfm"
fi

# 4. Setup Desktop Application Menu Entry and Icon
echo "[4/4] Setting up Desktop icon and application shortcut..."
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
mkdir -p "$ICON_DIR"
cp "$SCRIPT_DIR/assets/dfm_icon.png" "$ICON_DIR/dfm.png"

DESKTOP_DIR="$HOME/.local/share/applications"
mkdir -p "$DESKTOP_DIR"

cat << EOF > "$DESKTOP_DIR/dfm.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=DFM Downloader
GenericName=Internet Download Manager
Comment=High-Speed Multi-Threaded Download Accelerator and Video Grabber
Exec=dfm %U
Icon=dfm
Terminal=false
Categories=Network;FileTransfer;
MimeType=x-scheme-handler/dfm;
StartupNotify=true
StartupWMClass=DFM
EOF

chmod +x "$DESKTOP_DIR/dfm.desktop"

# Refresh desktop database if available
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

echo ""
echo "=========================================================="
echo "   ✓ DFM has been successfully installed on your Ubuntu!  "
echo "=========================================================="
echo "You can now start DFM by:"
echo "  1. Searching 'DFM Downloader' in Ubuntu Applications (Super / Windows key)"
echo "  2. Running 'dfm' in your terminal"
echo "  3. Running './run.sh' from this folder"
echo "=========================================================="
