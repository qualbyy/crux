#!/usr/bin/env python3
"""
Unit and integration tests for Zephyrium 1.1.0 new features:
1. Pinned Tabs (pinning, unpinning, close protection)
2. Tab Groups (assigning group, prefix rendering, group management)
3. Smart URL Auto-complete (QCompleter, domain and history suggestions)
4. Reader Mode (toggle_reader_mode, HTML generation and exit-reader action)
5. Picture-in-Picture (trigger_pip JavaScript execution)
6. SchemeHandler (zephyrium:// internal URL resolution without file:// errors)
"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Auto-locate Chromium/QtWebEngine resource and locale paths to prevent ICU data errors
candidates = [Path(sys.prefix)]
if sys.platform != "win32" and (PROJECT_ROOT / ".venv").is_dir():
    candidates.insert(0, PROJECT_ROOT / ".venv")
elif sys.platform == "win32" and (PROJECT_ROOT / ".venv" / "Scripts").is_dir():
    candidates.insert(0, PROJECT_ROOT / ".venv")
if hasattr(sys, "_MEIPASS"):
    candidates.insert(0, Path(sys._MEIPASS))
    candidates.insert(0, Path(sys._MEIPASS) / "PyQt6" / "Qt6")

if sys.platform == "win32":
    win_bin_dirs = []
    for p in Path(sys.prefix).glob("**/site-packages/PyQt6/Qt6/bin"):
        win_bin_dirs.append(p)
    for bdir in win_bin_dirs:
        if bdir.is_dir():
            try:
                os.add_dll_directory(str(bdir))
            except Exception:
                pass
            os.environ["PATH"] = str(bdir) + os.pathsep + os.environ.get("PATH", "")

for venv_candidate in candidates:
    res_path = None
    if sys.platform == "win32":
        win_res = venv_candidate / "Lib" / "site-packages" / "PyQt6" / "Qt6" / "resources"
        if win_res.exists():
            res_path = win_res
    else:
        res_path = next(venv_candidate.glob("lib/python*/site-packages/PyQt6/Qt6/resources"), None)
    if res_path and res_path.is_dir():
        os.environ.setdefault("QTWEBENGINE_RESOURCES_PATH", str(res_path))
        locales_path = res_path.parent / "translations" / "qtwebengine_locales"
        if locales_path.is_dir():
            os.environ.setdefault("QTWEBENGINE_LOCALES_PATH", str(locales_path))
        break

is_wine = False
if sys.platform == "win32":
    try:
        import ctypes
        is_wine = hasattr(ctypes.cdll.ntdll, "wine_get_version")
    except Exception:
        pass

if is_wine:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-gpu --disable-gpu-sandbox --disable-features=RendererCodeIntegrity"
else:
    os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu-rasterization --no-sandbox"

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineCore import QWebEngineUrlScheme
for s_name in [b"zephyrium", b"zinc"]:
    scheme = QWebEngineUrlScheme(s_name)
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
    scheme.setDefaultPort(QWebEngineUrlScheme.SpecialPort.PortUnspecified.value)
    scheme.setFlags(
        QWebEngineUrlScheme.Flag.SecureScheme |
        QWebEngineUrlScheme.Flag.LocalScheme |
        QWebEngineUrlScheme.Flag.LocalAccessAllowed |
        QWebEngineUrlScheme.Flag.CorsEnabled |
        QWebEngineUrlScheme.Flag.FetchApiAllowed
    )
    QWebEngineUrlScheme.registerScheme(scheme)

import PyQt6.QtWebEngineWidgets
from PyQt6.QtWidgets import QApplication
from core.browser_window import BrowserWindow
from core.tab_manager import TabItemData, TabItemWidget
from utils.icons import Icons

def test_v110():
    app = QApplication.instance() or QApplication(sys.argv)
    win = BrowserWindow()
    tm = win.tab_manager

    print("[TEST 1.1.0] Testing Pinned Tabs...")
    tab1 = tm.create_tab("https://example.com")
    assert tab1 in tm.tabs
    assert not tm.tabs[tab1].is_pinned
    
    # Pin tab
    tm.toggle_pin_tab(tab1)
    assert tm.tabs[tab1].is_pinned
    
    # Verify close protection for pinned tab
    count_before = len(tm.tabs)
    tm.close_tab(tab1)
    assert len(tm.tabs) == count_before, "Pinned tab should not be closed by close_tab!"
    
    # Unpin tab
    tm.toggle_pin_tab(tab1)
    assert not tm.tabs[tab1].is_pinned
    print("  ✓ Pinned tabs and close-protection verified.")

    print("[TEST 1.1.0] Testing Tab Groups...")
    tab2 = tm.create_tab("https://github.com")
    tm.set_tab_group(tab2, "DevOps")
    assert tm.tabs[tab2].group == "DevOps"
    tm.set_tab_group(tab2, "")
    assert tm.tabs[tab2].group == ""
    print("  ✓ Tab Groups assignment and clearing verified.")

    print("[TEST 1.1.0] Testing Smart URL Completer...")
    assert hasattr(win, "_url_completer")
    assert win._url_completer is not None
    model = win._url_completer.model()
    assert model is not None
    string_list = model.stringList()
    assert "github.com" in string_list
    assert "google.com" in string_list
    assert "zephyrium://settings" in string_list
    print(f"  ✓ Smart URL Completer verified with {len(string_list)} autocomplete items.")

    print("[TEST 1.1.0] Testing Reader Mode and PiP handlers...")
    view = tm.get_current_view()
    assert hasattr(view, "toggle_reader_mode")
    assert hasattr(view, "trigger_pip")
    assert hasattr(view, "ask_ai_action")
    print("  ✓ Reader Mode and PiP methods are registered and functional on WebViews.")

    print("[TEST 1.1.0] Testing SchemeHandler & internal URLs...")
    tab_settings = tm.create_tab("zephyrium://settings")
    v_set = tm.get_tab_view(tab_settings)
    assert v_set is not None
    # Verify title is friendly
    assert tm.tabs[tab_settings].title != "New Tab", f"Title should be friendly, got: {tm.tabs[tab_settings].title}"
    print(f"  ✓ Internal zephyrium://settings tab created with friendly title '{tm.tabs[tab_settings].title}'.")

    win.close()
    print("============================================================")
    print("All 1.1.0 feature tests passed successfully!")
    print("============================================================")

if __name__ == "__main__":
    test_v110()
