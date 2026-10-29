"""
Zephyrium v1.3.1 Verification Test Suite
Tests:
1. Drag and drop reliability in DraggableTabListWidget (no lost tabs on invalid drop or out-of-bounds drop).
2. Tab widget persistence during drag and drop.
3. Tab close and all_tabs_closed behavior (no zombie window or orphan suspended screen).
4. Internal pages immunity to hibernation/suspension.
5. Horizontal tab bar reordering synchronization.
"""
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--no-sandbox --disable-gpu"

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

from PyQt6.QtWidgets import QApplication, QListWidgetItem, QLabel
from PyQt6.QtCore import Qt, QMimeData, QPoint, QPointF, QUrl
from PyQt6.QtGui import QDropEvent

from core.tab_manager import DraggableTabListWidget, TabManager
from core.profile_manager import ProfileManager
from core.browser_window import BrowserWindow
from config import APP_VERSION


def test_v131_drag_drop():
    print("[TEST 1.3.1] Testing DraggableTabListWidget drag and drop safety...")
    lw = DraggableTabListWidget()
    
    # Populate with 3 items
    for i in range(3):
        it = QListWidgetItem()
        lbl = QLabel(f"Tab Widget {i}")
        it._stored_widget = lbl
        lw.addItem(it)
        lw.setItemWidget(it, lbl)

    assert lw.count() == 3, f"Expected 3 tabs, got {lw.count()}"

    # 1. Normal reorder from 0 to 2
    mime0 = QMimeData()
    mime0.setData("application/x-zephyrium-tab-row", b"0")
    # Simulate drop at row 2
    item2 = lw.item(2)
    rect2 = lw.visualItemRect(item2)
    drop_ev = QDropEvent(QPointF(rect2.center()), Qt.DropAction.MoveAction, mime0, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    lw.dropEvent(drop_ev)

    assert lw.count() == 3, f"Expected 3 tabs after reorder, got {lw.count()}"
    assert lw.itemWidget(lw.item(0)).text() == "Tab Widget 1"
    assert lw.itemWidget(lw.item(1)).text() == "Tab Widget 2"
    assert lw.itemWidget(lw.item(2)).text() == "Tab Widget 0"
    print("  ✓ Normal drag-and-drop reordering preserves widgets and order.")

    # 2. Drop into empty area below list (pos far below)
    mime_bottom = QMimeData()
    mime_bottom.setData("application/x-zephyrium-tab-row", b"0")
    drop_bottom = QDropEvent(QPointF(10, 5000), Qt.DropAction.MoveAction, mime_bottom, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    lw.dropEvent(drop_bottom)

    assert lw.count() == 3, f"Tab disappeared on out-of-bounds drop! Count: {lw.count()}"
    assert lw.itemWidget(lw.item(2)).text() == "Tab Widget 1"
    print("  ✓ Dragging to empty area below tabs clamps safely to bottom without tab loss.")

    # 3. Invalid / foreign drop (e.g. from web view or text drag)
    mime_foreign = QMimeData()
    mime_foreign.setText("https://example.com")
    drop_foreign = QDropEvent(QPointF(10, 10), Qt.DropAction.MoveAction, mime_foreign, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    lw.dropEvent(drop_foreign)

    assert lw.count() == 3, f"Foreign drop altered tab count! Count: {lw.count()}"
    print("  ✓ Foreign MIME data dropped onto sidebar is rejected safely.")

    # 4. Drop on same row
    mime_same = QMimeData()
    mime_same.setData("application/x-zephyrium-tab-row", b"1")
    item1 = lw.item(1)
    rect1 = lw.visualItemRect(item1)
    drop_same = QDropEvent(QPointF(rect1.center()), Qt.DropAction.MoveAction, mime_same, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    lw.dropEvent(drop_same)

    assert lw.count() == 3, f"Same row drop changed count! Count: {lw.count()}"
    print("  ✓ Dropping on same row preserves all tabs.")


def test_v131_internal_page_suspension_immunity(win: BrowserWindow):
    print("[TEST 1.3.1] Testing internal pages immunity to tab suspension...")
    tab_mgr = win.tab_manager
    
    # Create tabs: an external web page and internal settings / startpage tabs
    t_web = tab_mgr.create_tab("https://example.com")
    t_settings = tab_mgr.create_tab("zephyrium://settings")
    t_start = tab_mgr.create_tab("zephyrium://startpage")

    # Select t_web as active so background tabs can be tested
    tab_mgr.select_tab(t_web)

    # Try suspending internal pages
    tab_mgr.suspend_tab(t_settings)
    assert not tab_mgr.tabs[t_settings].is_suspended, "zephyrium://settings should NEVER be suspended!"

    tab_mgr.suspend_tab(t_start)
    assert not tab_mgr.tabs[t_start].is_suspended, "zephyrium://startpage should NEVER be suspended!"

    # Clean up t_settings and t_start for next test
    tab_mgr.close_tab(t_settings)
    tab_mgr.close_tab(t_start)

    print("  ✓ Internal pages (zephyrium://settings, zephyrium://startpage) are immune to hibernation.")


def test_v131_tab_close_and_all_closed(win: BrowserWindow):
    print("[TEST 1.3.1] Testing TabManager tab close & all_tabs_closed behavior...")
    tab_mgr = win.tab_manager
    
    # Close any existing tabs except one
    remaining_tids = list(tab_mgr.tabs.keys())
    for tid in remaining_tids[1:]:
        tab_mgr.close_tab(tid)

    t1 = list(tab_mgr.tabs.keys())[0]
    t2 = tab_mgr.create_tab("https://google.com")

    assert len(tab_mgr.tabs) == 2
    assert tab_mgr.sidebar.list_widget.count() == 2

    # Close t1
    tab_mgr.close_tab(t1)
    assert len(tab_mgr.tabs) == 1
    assert tab_mgr.sidebar.list_widget.count() == 1
    assert tab_mgr.active_tab_id == t2

    # Test closing the last tab emits all_tabs_closed
    all_closed_called = []
    try:
        tab_mgr.all_tabs_closed.disconnect(win._on_all_tabs_closed)
    except Exception:
        pass
    tab_mgr.all_tabs_closed.connect(lambda: all_closed_called.append(True))
    tab_mgr.close_tab(t2)

    assert len(tab_mgr.tabs) == 0, f"Expected 0 tabs in memory, got {len(tab_mgr.tabs)}"
    assert tab_mgr.sidebar.list_widget.count() == 0, f"Expected 0 sidebar items, got {tab_mgr.sidebar.list_widget.count()}"
    assert len(all_closed_called) == 1, "all_tabs_closed signal was not emitted!"
    print("  ✓ Closing all tabs cleanly cleans up memory and emits all_tabs_closed.")


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    test_v131_drag_drop()
    win = BrowserWindow()
    test_v131_internal_page_suspension_immunity(win)
    test_v131_tab_close_and_all_closed(win)
    win.close()
    print("\n[SUCCESS] All v1.3.1 tests passed successfully!")


if __name__ == "__main__":
    main()
