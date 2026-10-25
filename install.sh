#!/usr/bin/env bash
# ==============================================================================
# Zephyrium Universal One-Line Installer for Linux
# Installs standalone binary release to ~/.local/share/zephyrium & creates desktop shortcut
# ==============================================================================
set -e

REPO="qualbyy/zephyrium"
INSTALL_DIR="$HOME/.local/share/zephyrium"
BIN_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"

echo "=== Zephyrium Browser Installer ==="
echo "[1/4] Detecting architecture and latest release..."

ARCH=$(uname -m)
if [ "$ARCH" != "x86_64" ]; then
    echo "Error: Only x86_64 architecture is supported at this time (detected: $ARCH)."
    exit 1
fi

LATEST_TAG=$(curl -sSL "https://api.github.com/repos/$REPO/releases/latest" | grep '"tag_name":' | head -n 1 | cut -d '"' -f 4)
if [ -z "$LATEST_TAG" ]; then
    LATEST_TAG="v1.2.0"
fi
VERSION="${LATEST_TAG#v}"
TAR_NAME="zephyrium-v${VERSION}-linux-x86_64.tar.gz"
DOWNLOAD_URL="https://github.com/$REPO/releases/download/$LATEST_TAG/$TAR_NAME"

echo "[2/4] Downloading Zephyrium $LATEST_TAG ($TAR_NAME)..."
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

curl -fSL --progress-bar "$DOWNLOAD_URL" -o "$TMP_DIR/$TAR_NAME"

echo "[3/4] Installing to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$DESKTOP_DIR" "$ICON_DIR"
rm -rf "$INSTALL_DIR"/*
tar -xzf "$TMP_DIR/$TAR_NAME" -C "$TMP_DIR"
cp -r "$TMP_DIR/zephyrium"/* "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/zephyrium"

# Symlink executable to ~/.local/bin
ln -sf "$INSTALL_DIR/zephyrium" "$BIN_DIR/zephyrium"
ln -sf "$INSTALL_DIR/zephyrium" "$BIN_DIR/zephyrium-browser"

# Install application icon
if [ -f "$INSTALL_DIR/zephyrium.svg" ]; then
    cp "$INSTALL_DIR/zephyrium.svg" "$ICON_DIR/zephyrium.svg"
fi

# Create desktop entry
cat <<EOF > "$DESKTOP_DIR/zephyrium.desktop"
[Desktop Entry]
Version=1.0
Name=Zephyrium
GenericName=Web Browser
Comment=Fast, keyboard-driven web browser
Exec=$BIN_DIR/zephyrium %u
Terminal=false
Type=Application
Icon=zephyrium
Categories=Network;WebBrowser;
MimeType=text/html;text/xml;application/xhtml+xml;application/xml;x-scheme-handler/http;x-scheme-handler/https;x-scheme-handler/zephyrium;
StartupWMClass=zephyrium
StartupNotify=true
Actions=NewTab;Incognito;Work;Dev;

[Desktop Action NewTab]
Name=New Tab
Exec=$BIN_DIR/zephyrium zephyrium://startpage

[Desktop Action Incognito]
Name=Open in Incognito Container
Exec=$BIN_DIR/zephyrium --container incognito

[Desktop Action Work]
Name=Open in Work Container
Exec=$BIN_DIR/zephyrium --container work

[Desktop Action Dev]
Name=Open in Dev Container
Exec=$BIN_DIR/zephyrium --container dev
EOF
chmod +x "$DESKTOP_DIR/zephyrium.desktop"

# Update desktop database if command exists
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo "[4/4] Installation Complete!"
echo "--------------------------------------------------"
echo "Zephyrium $LATEST_TAG installed successfully."
echo "Launch with: zephyrium"
echo "Or find 'Zephyrium' in your application menu."
echo "--------------------------------------------------"
