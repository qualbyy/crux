#!/usr/bin/env bash
# Crux Standalone Release Build Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=== Building Crux Release ==="

if [ ! -x "$VENV_DIR/bin/pyinstaller" ]; then
    echo "Installing PyInstaller in virtualenv..."
    "$VENV_DIR/bin/pip" install pyinstaller
fi

rm -rf "$SCRIPT_DIR/build" "$SCRIPT_DIR/dist"

echo "Running PyInstaller..."
"$VENV_DIR/bin/pyinstaller" \
    --noconfirm \
    --log-level=WARN \
    --clean \
    "$SCRIPT_DIR/crux.spec"

echo "Bundling QtWebEngine runtime libraries..."
PYQT_DIR=$(find "$VENV_DIR/lib" -type d -name "PyQt6" | head -n 1)
TARGET_PYQT="$SCRIPT_DIR/dist/crux/_internal/PyQt6"

if [ -d "$PYQT_DIR" ]; then
    cp -rv "$PYQT_DIR"/QtWebEngine* "$TARGET_PYQT/" 2>/dev/null || true
    mkdir -p "$TARGET_PYQT/Qt6/lib" "$TARGET_PYQT/Qt6/libexec" "$TARGET_PYQT/Qt6/resources" "$TARGET_PYQT/Qt6/translations"
    cp -rv "$PYQT_DIR"/Qt6/lib/libQt6WebEngine* "$TARGET_PYQT/Qt6/lib/" 2>/dev/null || true
    cp -rv "$PYQT_DIR"/Qt6/libexec/QtWebEngineProcess "$TARGET_PYQT/Qt6/libexec/" 2>/dev/null || true
    cp -rv "$PYQT_DIR"/Qt6/resources/* "$TARGET_PYQT/Qt6/resources/" 2>/dev/null || true
    cp -rv "$PYQT_DIR"/Qt6/translations/qtwebengine* "$TARGET_PYQT/Qt6/translations/" 2>/dev/null || true
fi

cp "$SCRIPT_DIR/crux.desktop" "$SCRIPT_DIR/dist/crux/"
cp "$SCRIPT_DIR/resources/crux.svg" "$SCRIPT_DIR/dist/crux/"
# Also copy legacy aliases
cp "$SCRIPT_DIR/zephyrium.desktop" "$SCRIPT_DIR/dist/crux/" 2>/dev/null || true
cp "$SCRIPT_DIR/resources/zephyrium.svg" "$SCRIPT_DIR/dist/crux/" 2>/dev/null || true

echo "Packaging release archive..."
VERSION=$(grep -oP 'APP_VERSION\s*=\s*"\K[^"]+' "$SCRIPT_DIR/config.py" || echo "1.3.6")
ARCHIVE="crux-v${VERSION}-linux-x86_64.tar.gz"

cd "$SCRIPT_DIR/dist"
tar -czvf "$ARCHIVE" crux
sha256sum "$ARCHIVE" > "${ARCHIVE}.sha256"

echo "=== Build Complete! ==="
ls -lh "$SCRIPT_DIR/dist/$ARCHIVE"*
