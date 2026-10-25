#!/usr/bin/env bash
# Zephyrium Standalone Release Build Script
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "=== Building Zephyrium Release ==="

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
    --name zephyrium \
    --add-data "resources:resources" \
    --add-data "style.qss:." \
    --collect-all PyQt6 \
    --collect-all PyQt6_WebEngine \
    --hidden-import PyQt6.QtWebEngineCore \
    --hidden-import PyQt6.QtWebEngineWidgets \
    "$SCRIPT_DIR/main.py"

echo "Bundling QtWebEngine runtime libraries..."
PYQT_DIR="$VENV_DIR/lib/python3.14/site-packages/PyQt6"
TARGET_PYQT="$SCRIPT_DIR/dist/zephyrium/_internal/PyQt6"

cp -rv "$PYQT_DIR"/QtWebEngine* "$TARGET_PYQT/" 2>/dev/null || true
mkdir -p "$TARGET_PYQT/Qt6/lib" "$TARGET_PYQT/Qt6/libexec" "$TARGET_PYQT/Qt6/resources" "$TARGET_PYQT/Qt6/translations"
cp -rv "$PYQT_DIR"/Qt6/lib/libQt6WebEngine* "$TARGET_PYQT/Qt6/lib/" 2>/dev/null || true
cp -rv "$PYQT_DIR"/Qt6/libexec/QtWebEngineProcess "$TARGET_PYQT/Qt6/libexec/" 2>/dev/null || true
cp -rv "$PYQT_DIR"/Qt6/resources/* "$TARGET_PYQT/Qt6/resources/" 2>/dev/null || true
cp -rv "$PYQT_DIR"/Qt6/translations/qtwebengine* "$TARGET_PYQT/Qt6/translations/" 2>/dev/null || true

cp "$SCRIPT_DIR/zephyrium.desktop" "$SCRIPT_DIR/dist/zephyrium/"
cp "$SCRIPT_DIR/resources/zephyrium.svg" "$SCRIPT_DIR/dist/zephyrium/"

echo "Packaging release archive..."
VERSION=$(grep -oP 'APP_VERSION\s*=\s*"\K[^"]+' "$SCRIPT_DIR/config.py" || echo "1.0.1")
ARCHIVE="zephyrium-v${VERSION}-linux-x86_64.tar.gz"

cd "$SCRIPT_DIR/dist"
tar -czvf "$ARCHIVE" zephyrium
sha256sum "$ARCHIVE" > "${ARCHIVE}.sha256"

echo "=== Build Complete! ==="
ls -lh "$SCRIPT_DIR/dist/$ARCHIVE"*
