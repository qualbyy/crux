#!/usr/bin/env bash
# Crux Launch Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Auto-locate Chromium/QtWebEngine resource and locale paths to prevent ICU data errors
RESOURCES_DIR=$(find "$VENV_DIR/lib" -type d -path "*/PyQt6/Qt6/resources" 2>/dev/null | head -n 1)
if [ -n "$RESOURCES_DIR" ] && [ -d "$RESOURCES_DIR" ]; then
    export QTWEBENGINE_RESOURCES_PATH="$RESOURCES_DIR"
    LOCALES_DIR="$(dirname "$RESOURCES_DIR")/translations/qtwebengine_locales"
    if [ -d "$LOCALES_DIR" ]; then
        export QTWEBENGINE_LOCALES_PATH="$LOCALES_DIR"
    fi
fi

if [ -x "$VENV_DIR/bin/python3" ]; then
    exec "$VENV_DIR/bin/python3" "$SCRIPT_DIR/main.py" "$@"
else
    exec python3 "$SCRIPT_DIR/main.py" "$@"
fi
