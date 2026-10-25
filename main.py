#!/usr/bin/env python3
"""
Zephyrium — Lightweight, Feature-Rich Web Browser
Design Code: Minimal Aesthetic & Vim Mode
"""
import sys
import os
import json
from pathlib import Path
import argparse

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Set Process ID / Name
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Zephyrium.Browser.App")
    except Exception:
        pass
else:
    try:
        import ctypes
        libc = ctypes.CDLL("libc.so.6")
        PR_SET_NAME = 15
        libc.prctl(PR_SET_NAME, b"zephyrium\0", 0, 0, 0)
    except Exception:
        pass

# GPU acceleration and engine flags
flags = [
    "--enable-gpu-rasterization",
    "--enable-zero-copy",
    "--ignore-gpu-blocklist",
]
if sys.platform.startswith("linux"):
    flags.append("--ozone-platform-hint=auto")
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(flags)

# Auto-locate Chromium/QtWebEngine resource and locale paths to prevent ICU data errors
candidates = [PROJECT_ROOT / ".venv", Path(sys.prefix)]
if hasattr(sys, "_MEIPASS"):
    candidates.insert(0, Path(sys._MEIPASS))
    candidates.insert(0, Path(sys._MEIPASS) / "PyQt6" / "Qt6")
if getattr(sys, "frozen", False):
    exe_dir = Path(sys.executable).parent
    candidates.insert(0, exe_dir)
    candidates.insert(0, exe_dir / "_internal")
    candidates.insert(0, exe_dir / "PyQt6" / "Qt6")
    candidates.insert(0, exe_dir / "_internal" / "PyQt6" / "Qt6")

# Windows DLL directory registration for Python 3.8+ (fixes DLL load failed while importing QtCore)
if sys.platform == "win32":
    # Must keep references to AddDllDirectory objects alive to prevent garbage collection!
    _dll_handles = []
    win_bin_dirs = []
    if hasattr(sys, "_MEIPASS"):
        win_bin_dirs.append(Path(sys._MEIPASS) / "PyQt6" / "Qt6" / "bin")
        win_bin_dirs.append(Path(sys._MEIPASS))
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        win_bin_dirs.append(exe_dir / "_internal" / "PyQt6" / "Qt6" / "bin")
        win_bin_dirs.append(exe_dir / "PyQt6" / "Qt6" / "bin")
        win_bin_dirs.append(exe_dir / "_internal")
        win_bin_dirs.append(exe_dir)
    for p in Path(sys.prefix).glob("**/site-packages/PyQt6/Qt6/bin"):
        win_bin_dirs.append(p)

    for bdir in win_bin_dirs:
        if bdir.is_dir():
            bdir_str = str(bdir)
            try:
                handle = os.add_dll_directory(bdir_str)
                _dll_handles.append(handle)
            except Exception:
                pass
            os.environ["PATH"] = bdir_str + os.pathsep + os.environ.get("PATH", "")

    # Also set default DLL directory via Win32 API as ultimate fallback
    try:
        import ctypes
        for bdir in win_bin_dirs:
            if bdir.is_dir():
                ctypes.windll.kernel32.SetDllDirectoryW(str(bdir))
                break
    except Exception:
        pass

for venv_candidate in candidates:
    res_path = next(venv_candidate.glob("lib/python*/site-packages/PyQt6/Qt6/resources"), None)
    if not res_path:
        win_res = venv_candidate / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "resources"
        if win_res.exists():
            res_path = win_res
    if not res_path:
        win_res2 = venv_candidate / "bin"
        if (venv_candidate / "resources" / "qtwebengine_resources.pak").exists():
            res_path = venv_candidate / "resources"
        elif (venv_candidate / "qtwebengine_resources.pak").exists():
            res_path = venv_candidate
    if res_path and res_path.is_dir():
        os.environ.setdefault("QTWEBENGINE_RESOURCES_PATH", str(res_path))
        locales_path = res_path.parent / "translations" / "qtwebengine_locales"
        if not locales_path.is_dir():
            locales_path = res_path / "translations" / "qtwebengine_locales"
        if locales_path.is_dir():
            os.environ.setdefault("QTWEBENGINE_LOCALES_PATH", str(locales_path))
        break

from PyQt6.QtCore import Qt, QCoreApplication
from PyQt6.QtWebEngineCore import QWebEngineUrlScheme

for s_name in [b"zephyrium", b"zinc"]:
    scheme = QWebEngineUrlScheme(s_name)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
    scheme.setDefaultPort(QWebEngineUrlScheme.SpecialPort.PortUnspecified.value)
    scheme.setFlags(
        QWebEngineUrlScheme.Flag.LocalScheme |
        QWebEngineUrlScheme.Flag.LocalAccessAllowed |
        QWebEngineUrlScheme.Flag.CorsEnabled |
        QWebEngineUrlScheme.Flag.FetchApiAllowed
    )
    QWebEngineUrlScheme.registerScheme(scheme)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtNetwork import QLocalSocket, QLocalServer

from config import APP_NAME, APP_VERSION, CONFIG_DIR, load_settings
from core.browser_window import BrowserWindow
from core.theme_manager import apply_app_theme

IPC_NAME = "zephyrium_ipc_sock"

def load_stylesheet(app: QApplication) -> None:
    settings = load_settings()
    apply_app_theme(app, settings.get("theme", "dark"), settings.get("accent_color", "#fe8019"))
    
    custom_qss = CONFIG_DIR / "custom.qss"
    if custom_qss.exists():
        try:
            with open(custom_qss, "r", encoding="utf-8") as f:
                app.setStyleSheet(app.styleSheet() + "\n" + f.read())
        except Exception:
            pass

class IPCServer(QLocalServer):
    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.newConnection.connect(self._on_connection)
        self.removeServer(IPC_NAME)
        self.listen(IPC_NAME)

    def _on_connection(self):
        client = self.nextPendingConnection()
        if client:
            client.waitForReadyRead(500)
            data = client.readAll().data().decode("utf-8")
            try:
                cmd = json.loads(data)
                url = cmd.get("url", "zephyrium://startpage")
                container = cmd.get("container", "default")
                mode = cmd.get("mode")
                if mode and mode in ["minimal", "vim"]:
                    self.window.apply_mode(mode)
                if url in ["zephyrium://welcome", "zinc://welcome"]:
                    self.window.show_onboarding()
                else:
                    self.window.tab_manager.create_tab(container, url)
                self.window.raise_()
                self.window.activateWindow()
            except Exception:
                pass
            client.close()

def main():
    settings = load_settings()
    default_target = "zephyrium://startpage"

    parser = argparse.ArgumentParser(description=f"{APP_NAME} v{APP_VERSION}")
    parser.add_argument("url", nargs="?", default=default_target, help="Initial URL to open")
    parser.add_argument("--container", "-c", default="default", help="Container profile to open (default, work, personal, dev, incognito)")
    parser.add_argument("--mode", "-m", choices=["minimal", "vim"], default=None, help="UI Layout mode (minimal, vim)")
    args = parser.parse_args()

    # Qt Application setup
    app = QApplication(sys.argv)
    
    # Wayland app_id and Desktop integration: MUST match zephyrium.desktop
    app.setDesktopFileName("zephyrium.desktop")
    app.setApplicationName("zephyrium")
    app.setApplicationDisplayName("Zephyrium")
    app.setOrganizationName("Zephyrium")
    app.setOrganizationDomain("zephyrium.org")

    # Fast IPC Check: If another instance is already running, send command and exit!
    sock = QLocalSocket()
    sock.connectToServer(IPC_NAME)
    if sock.waitForConnected(300):
        msg = json.dumps({"url": args.url, "container": args.container, "mode": args.mode})
        sock.write(msg.encode("utf-8"))
        sock.flush()
        sock.waitForBytesWritten(500)
        sock.close()
        sys.exit(0)

    # Monospace typography priority: Iosevka Nerd Font -> JetBrains Mono -> Monospace
    font = QFont(settings.get("font_family", "Iosevka Nerd Font"), 10)
    font.setStyleHint(QFont.StyleHint.Monospace)
    app.setFont(font)

    # Apply application dynamic theme
    load_stylesheet(app)

    # Set Application & Window Icon
    icon_path = Path(__file__).resolve().parent / "resources" / "zephyrium.svg"
    if not icon_path.exists():
        icon_path = Path(__file__).resolve().parent / "resources" / "zinc-browser.svg"
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
        app.setWindowIcon(app_icon)

    # Launch window
    window = BrowserWindow(initial_mode=args.mode)
    window.setObjectName("ZephyriumBrowserWindow")
    if icon_path.exists():
        window.setWindowIcon(app_icon)
    
    # If a specific url was given on CLI and differs from initial tab, open it
    if args.url in ["zephyrium://welcome", "zinc://welcome"]:
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(150, window.show_onboarding)
    elif args.url != "zephyrium://startpage" or args.container != "default":
        window.tab_manager.create_tab(args.container, args.url)

    # Start IPC server to accept future CLI tabs
    ipc_server = IPCServer(window, app)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
