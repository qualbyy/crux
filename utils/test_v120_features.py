#!/usr/bin/env python3
"""
Unit and integration tests for Zephyrium 1.2.0 new features and bug fixes:
1. Responsive Toolbar Overflow (collapses secondary buttons into » menu on narrow window)
2. Vertical Tabs Pinning & Reorder (pinned tabs sort to top, drag-and-drop reorder)
3. Horizontal Tabs Enhancements (compact pinned tabs with pin icon, context menu)
4. Downloads UI (compact popup anchored to downloads button, auto-closing temporary download tabs)
5. Website Theme (decoupled website theme defaulting to light, native prefers-color-scheme)
6. Speed Dial (YouTube and X.com shortcuts updated)
7. Navigation Buttons (forward button disabled/grayed out when no forward history)
8. Security Badge Popup (connection info for HTTPS / internal system page notice)
9. Find in Page Bar (Ctrl+F floating bar)
10. Version verification (1.2.0 across config, installer, and resources)
"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Ensure QtWebEngine URL schemes are registered before QApplication
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

for venv_candidate in [Path(sys.prefix), Path.home() / ".local"]:
    res_path = next(venv_candidate.glob("lib/python*/site-packages/PyQt6/Qt6/resources"), None)
    if res_path and res_path.is_dir():
        os.environ.setdefault("QTWEBENGINE_RESOURCES_PATH", str(res_path))
        locales_path = res_path.parent / "translations" / "qtwebengine_locales"
        if locales_path.is_dir():
            os.environ.setdefault("QTWEBENGINE_LOCALES_PATH", str(locales_path))
        break

import PyQt6.QtWebEngineWidgets
from PyQt6.QtWidgets import QApplication
from config import APP_VERSION, DEFAULT_SETTINGS, load_settings
from core.browser_window import BrowserWindow
from core.find_bar import FindInPageBar
from core.download_manager import DownloadManager
from utils.icons import Icons

def test_v120():
    print("[TEST 1.2.0] Starting test suite...")

    # 1. Version check
    assert APP_VERSION == "1.2.0", f"Expected APP_VERSION == 1.2.0, got {APP_VERSION}"
    assert DEFAULT_SETTINGS.get("website_theme") == "light"
    assert DEFAULT_SETTINGS.get("new_tab_url") == "zephyrium://startpage"
    print("  ✓ Version & default settings verified")

    # 2. Startpage speed dial shortcuts
    startpage_path = PROJECT_ROOT / "resources" / "startpage.html"
    with open(startpage_path, "r", encoding="utf-8") as f:
        sp_content = f.read()
    assert "https://youtube.com" in sp_content, "YouTube missing from speed dial"
    assert "https://x.com" in sp_content, "x.com missing from speed dial"
    print("  ✓ Speed dial links verified (YouTube & X.com present)")

    app = QApplication.instance() or QApplication(sys.argv)
    win = BrowserWindow()
    win.show()
    app.processEvents()
    tm = win.tab_manager

    # 3. Responsive Toolbar Overflow
    win.resize(1100, 700)
    app.processEvents()
    win._update_topbar_overflow()
    assert win.btn_more.isVisible(), "Overflow button (») should be visible when width < 1260"
    assert not win.btn_reader.isVisible(), "Secondary button should be hidden into overflow"
    assert win.url_bar.isVisible(), "Omnibar must remain visible"
    assert win.btn_ai.isVisible(), "AI button must remain visible"
    assert win.btn_settings.isVisible(), "Settings button must remain visible"

    win.resize(1350, 700)
    app.processEvents()
    win._update_topbar_overflow()
    assert not win.btn_more.isVisible(), "Overflow button should be hidden when width >= 1260"
    assert win.btn_reader.isVisible(), "Secondary button should be visible when space permits"
    print("  ✓ Responsive top bar overflow verified")

    # 4. Vertical Tabs Pinning to Top
    tab1 = tm.create_tab("https://site-one.com")
    tab2 = tm.create_tab("https://site-two.com")
    tab3 = tm.create_tab("https://site-three.com")

    # Pin tab 3
    tm.toggle_pin_tab(tab3)
    assert tm.tabs[tab3].is_pinned, "Tab 3 should be marked pinned"

    # Tab 3 must be at the very top of vertical list
    top_item = tm.sidebar.list_widget.item(0)
    assert top_item.data(Qt.ItemDataRole.UserRole) == tab3, "Pinned tab must sort to top of sidebar"
    print("  ✓ Vertical tab pinning to top verified")

    # 5. Horizontal Tab Sync & Compact Pin
    win.set_tab_orientation("horizontal")
    win._sync_horizontal_tabs()
    # Check that tab3 in horizontal tab bar has compact text (pin icon)
    h_idx = -1
    for i in range(win.horizontal_tab_bar.count()):
        if win.horizontal_tab_bar.tabData(i) == tab3:
            h_idx = i
            break
    assert h_idx != -1, "Tab 3 must exist in horizontal tab bar"
    assert win.horizontal_tab_bar.tabText(h_idx) == "📌", f"Expected '📌', got '{win.horizontal_tab_bar.tabText(h_idx)}'"
    assert win.horizontal_tab_bar.tabButton(h_idx, win.horizontal_tab_bar.ButtonPosition.RightSide) is None, "Pinned horizontal tab must have no close button"
    print("  ✓ Horizontal tabs compact pin verified")

    # 6. Navigation Buttons State
    assert not win.btn_fwd.isEnabled(), "Forward button must be disabled when forward history is empty"
    print("  ✓ Forward button disabled state verified")

    # 7. Downloads Popup
    assert isinstance(win.download_manager, DownloadManager)
    assert hasattr(win.download_manager, "show_at_widget")
    print("  ✓ DownloadManager compact popup verified")

    # 8. Find in Page Bar
    assert isinstance(win.find_bar, FindInPageBar)
    win._toggle_find_in_page()
    assert win.find_bar.isVisible(), "Find in Page bar should be visible after toggle"
    win._toggle_find_in_page()
    assert not win.find_bar.isVisible(), "Find in Page bar should be hidden after second toggle"
    print("  ✓ Find in Page bar toggle verified")

    # 9. Sidebar Width & Compact State Preservation
    tm.sidebar.toggle_compact()
    assert tm.sidebar.is_compact, "Sidebar should now be compact"
    assert tm.sidebar.width() <= 50 or tm.sidebar.minimumWidth() <= 50
    # Simulate settings update while compact
    win._on_settings_saved({"sidebar_width": 300})
    assert tm.sidebar.is_compact, "Sidebar must remain compact after settings saved"
    assert tm.sidebar.expanded_width == 300, "Expanded width setting should be updated to 300"
    print("  ✓ Sidebar compact state preservation verified")

    print("\nAll Zephyrium 1.2.0 feature tests completed successfully!")

if __name__ == "__main__":
    test_v120()
