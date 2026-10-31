#!/usr/bin/env bash
set -e

# Sonde — Quick Native Linux Release Build Script
# Minimal RAM footprint (1 compiler worker thread)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/src-tauri"

echo "===> [Sonde] Building optimized release binary for Linux (x86_64)..."
cargo build --release -j 1

OUTPUT_BIN="$SCRIPT_DIR/src-tauri/target/release/sonde-rs"

if [ -f "$OUTPUT_BIN" ]; then
    mkdir -p "$HOME/.local/bin"
    cp --remove-destination "$OUTPUT_BIN" "$HOME/.local/bin/sonde-rs"
    ln -sf "$HOME/.local/bin/sonde-rs" "$HOME/.local/bin/sonde"
    ln -sf "$HOME/.local/bin/sonde-rs" "$HOME/.local/bin/sonde-browser"
    
    # Desktop shortcut
    if [ -d "$HOME/.local/share/applications" ]; then
        cp "$SCRIPT_DIR/sonde.desktop" "$HOME/.local/share/applications/sonde.desktop" || true
    fi

    echo "===> [SUCCESS] Sonde binary built and installed:"
    echo "       - Binary:  $HOME/.local/bin/sonde-rs"
    echo "       - Command: sonde (or sonde-browser)"
else
    echo "===> [ERROR] Build completed but binary not found."
    exit 1
fi
