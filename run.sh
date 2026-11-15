#!/usr/bin/env bash
# DFM (Download Fast Manager) Linux Launcher

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/target/release/dfm" ]; then
    exec "$SCRIPT_DIR/target/release/dfm" "$@"
elif [ -f "$SCRIPT_DIR/DFM.exe" ]; then
    exec wine "$SCRIPT_DIR/DFM.exe" "$@"
else
    exec cargo run --release -- "$@"
fi
