#!/usr/bin/env bash
# ==============================================================================
# DFM (Download Fast Manager) - Ubuntu / Debian Installation Script (Pure Rust)
# ==============================================================================

set -e

echo "=========================================================="
echo "      Installing DFM (Download Fast Manager) on Ubuntu     "
echo "=========================================================="

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Install system dependencies (build-essential, pkg-config, libssl-dev)
echo "[1/4] Installing system prerequisites..."
if command -v sudo &>/dev/null; then
    sudo apt-get update
    sudo apt-get install -y build-essential pkg-config libssl-dev libgl1-mesa-dev libx11-dev
else
    apt-get update
    apt-get install -y build-essential pkg-config libssl-dev libgl1-mesa-dev libx11-dev
fi

# 2. Check for Rust/Cargo
if ! command -v cargo &>/dev/null; then
    echo "[2/4] Installing Rust toolchain..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# 3. Build DFM release binary
echo "[3/4] Compiling DFM in release mode..."
cd "$SCRIPT_DIR"
cargo build --release

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
Comment=High-performance IDM alternative in 100% pure Rust
Exec=$SCRIPT_DIR/target/release/dfm %U
Icon=dfm
Terminal=false
Categories=Network;FileTransfer;Utility;
MimeType=x-scheme-handler/dfm;
StartupNotify=true
EOF

chmod +x "$DESKTOP_DIR/dfm.desktop"
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

echo "=========================================================="
echo "  DFM (Pure Rust) has been successfully installed!"
echo "  You can start DFM from your application menu or by running:"
echo "    $SCRIPT_DIR/target/release/dfm"
echo "=========================================================="
