#!/usr/bin/env bash
set -e

# ========================================================
#  Sonde 2.0 — Build & Run Windows Binary Under Wine
# ========================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="x86_64-pc-windows-gnu"

echo "===> [Sonde 2.0 Wine] Preparing cross-compilation for Windows ($TARGET)..."

# Ensure Rust target is installed
if ! rustup target list | grep -q "$TARGET (installed)"; then
    echo "===> Installing rust target $TARGET..."
    rustup target add "$TARGET"
fi

cd "$SCRIPT_DIR/src-tauri"

echo "===> Building Windows binary..."
cargo build --release --target "$TARGET" -j 1

WIN_BIN="$SCRIPT_DIR/src-tauri/target/$TARGET/release/sonde-rs.exe"

if [ -f "$WIN_BIN" ]; then
    echo "===> [SUCCESS] Windows executable built: $WIN_BIN"
    
    if command -v wine >/dev/null 2>&1; then
        echo "===> Launching Sonde under Wine..."
        wine "$WIN_BIN" "$@"
    else
        echo "===> Wine is not installed. To run, copy $WIN_BIN to a Windows machine or install wine."
    fi
else
    echo "===> [ERROR] Build completed but $WIN_BIN was not created."
    exit 1
fi
