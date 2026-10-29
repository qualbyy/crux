#!/usr/bin/env bash
# ==============================================================================
# Crux Universal One-Line Installer for Linux
# Installs standalone binary release to ~/.local/share/crux & creates desktop shortcut
# ==============================================================================
set -e

REPO="qualbyy/zephyrium"
INSTALL_DIR="$HOME/.local/share/crux"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

echo "=== Crux Browser Installer ==="
echo "[1/4] Detecting architecture and latest release..."

ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
    echo "Error: Only x86_64 architecture is supported at this time (detected: $ARCH)."
    exit 1
fi

LATEST_TAG=$(curl -sSL "https://api.github.com/repos/$REPO/releases/latest" | grep '"tag_name":' | head -n 1 | cut -d '"' -f 4)
if [ -z "$LATEST_TAG" ]; then
    LATEST_TAG="v1.3.6"
fi
VERSION="${LATEST_TAG#v}"
TAR_NAME="crux-v${VERSION}-linux-x86_64.tar.gz"
DOWNLOAD_URL="https://github.com/$REPO/releases/download/$LATEST_TAG/$TAR_NAME"

echo "[2/4] Downloading Crux $LATEST_TAG ($TAR_NAME)..."
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

curl -fSL --progress-bar "$DOWNLOAD_URL" -o "$TMP_DIR/$TAR_NAME" || {
    # Fallback to zephyrium naming if crux asset not found
    FALLBACK_TAR="zephyrium-v${VERSION}-linux-x86_64.tar.gz"
    echo "Crux archive not found, trying $FALLBACK_TAR..."
    curl -fSL --progress-bar "https://github.com/$REPO/releases/download/$LATEST_TAG/$FALLBACK_TAR" -o "$TMP_DIR/$TAR_NAME"
}

echo "[3/4] Installing to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
rm -rf "$INSTALL_DIR"/*
tar -xzf "$TMP_DIR/$TAR_NAME" -C "$TMP_DIR"
if [ -d "$TMP_DIR/crux" ]; then
    cp -r "$TMP_DIR/crux"/* "$INSTALL_DIR/"
elif [ -d "$TMP_DIR/zephyrium" ]; then
    cp -r "$TMP_DIR/zephyrium"/* "$INSTALL_DIR/"
fi
chmod +x "$INSTALL_DIR/crux" 2>/dev/null || chmod +x "$INSTALL_DIR/zephyrium" 2>/dev/null || true

# Symlink executable to ~/.local/bin
EXEC_PATH="$INSTALL_DIR/crux"
if [ ! -f "$EXEC_PATH" ] && [ -f "$INSTALL_DIR/zephyrium" ]; then
    EXEC_PATH="$INSTALL_DIR/zephyrium"
fi
ln -sf "$EXEC_PATH" "$BIN_DIR/crux"
ln -sf "$EXEC_PATH" "$BIN_DIR/crux-browser"
ln -sf "$EXEC_PATH" "$BIN_DIR/zephyrium"
ln -sf "$EXEC_PATH" "$BIN_DIR/zephyrium-browser"

# Install application icon
if [ -f "$INSTALL_DIR/crux.svg" ]; then
    cp "$INSTALL_DIR/crux.svg" "$ICON_DIR/crux.svg"
    cp "$INSTALL_DIR/crux.svg" "$ICON_DIR/zephyrium.svg"
elif [ -f "$INSTALL_DIR/zephyrium.svg" ]; then
    cp "$INSTALL_DIR/zephyrium.svg" "$ICON_DIR/crux.svg"
fi

# Create desktop entry
cat <<EOF > "$DESKTOP_DIR/crux.desktop"
[Desktop Entry]
Version=1.0
Name=Crux
GenericName=Web Browser
Comment=Fast, keyboard-driven web browser
Exec=$BIN_DIR/crux %u
Terminal=false
Type=Application
Icon=crux
Categories=Network;WebBrowser;
MimeType=text/html;text/xml;application/xhtml+xml;application/xml;x-scheme-handler/http;x-scheme-handler/https;x-scheme-handler/crux;x-scheme-handler/zephyrium;
StartupWMClass=crux
StartupNotify=true
Actions=NewTab;Incognito;Work;Dev;

[Desktop Action NewTab]
Name=New Tab
Exec=$BIN_DIR/crux crux://startpage

[Desktop Action Incognito]
Name=Open in Incognito Container
Exec=$BIN_DIR/crux --container incognito

[Desktop Action Work]
Name=Open in Work Container
Exec=$BIN_DIR/crux --container work

[Desktop Action Dev]
Name=Open in Dev Container
Exec=$BIN_DIR/crux --container dev
EOF
chmod +x "$DESKTOP_DIR/crux.desktop"
cp "$DESKTOP_DIR/crux.desktop" "$DESKTOP_DIR/zephyrium.desktop" 2>/dev/null || true

# Update desktop database if command exists
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo "[4/4] Installation Complete!"
echo "--------------------------------------------------"
echo "Crux $LATEST_TAG installed successfully."
echo "Launch with: crux"
echo "Or find 'Crux' in your application menu."
echo "--------------------------------------------------"
