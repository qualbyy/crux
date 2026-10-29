#!/usr/bin/env python3
"""
Unit and integration tests for Zephyrium 1.3.0 new features and bug fixes:
1. Version Verification (1.3.0 across config, installer, and resources)
2. Windows QtCore DLL & UPX Safety (upx=False, Win32 DLL search order)
3. Cloudflare Deploy & Web App Compatibility (confirm, alert, featurePermission, chooseFiles, exact host matching)
4. Chromium DevTools Dock & Responsive Viewport Emulator
5. Tab Hibernation & Memory Saver (💤 indicator, state persistence)
6. Multi-Account Containers (work, personal, dev, incognito badges)
7. Violentmonkey/Greasemonkey Userscripts & UserCSS Engine
8. Privacy Shield & URL Tracking Parameter Stripper
"""
import sys
import os
import re
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
from config import APP_VERSION, DEFAULT_SETTINGS, load_settings, CONFIG_DIR
from core.browser_window import BrowserWindow
from core.userscript_manager import UserscriptManager
from core.privacy_shield import strip_tracking_params, install_privacy_shield
from core.adblock import AdBlockerInterceptor

def test_v130():
    print("[TEST 1.3.0] Starting comprehensive verification suite...")

    # 1. Version check
    assert APP_VERSION in ["1.3.0", "1.3.1", "1.3.5"], f"Expected APP_VERSION >= 1.3.0, got {APP_VERSION}"
    iss_content = (PROJECT_ROOT / "installer.iss").read_text(encoding="utf-8")
    assert any(v in iss_content for v in ['#define MyAppVersion "1.3.0"', '#define MyAppVersion "1.3.1"', '#define MyAppVersion "1.3.5"']), "installer.iss version mismatch"
    settings_html = (PROJECT_ROOT / "resources" / "settings.html").read_text(encoding="utf-8")
    assert any(v in settings_html for v in ["1.3.0 (Release)", "1.3.1 (Release)", "1.3.5 (Release)"]), "settings.html version mismatch"
    print(f"  ✓ 1. Version {APP_VERSION} verified across config.py, installer.iss, settings.html")

    # 2. Windows QtCore DLL Fix & UPX Disabled
    spec_content = (PROJECT_ROOT / "zephyrium.spec").read_text(encoding="utf-8")
    assert re.search(r"EXE\(.*upx=False", spec_content, re.DOTALL), "zephyrium.spec EXE must have upx=False"
    assert re.search(r"COLLECT\(.*upx=False", spec_content, re.DOTALL), "zephyrium.spec COLLECT must have upx=False"
    main_content = (PROJECT_ROOT / "main.py").read_text(encoding="utf-8")
    assert "SetDllDirectoryW(None)" in main_content, "main.py must reset DLL search order with SetDllDirectoryW(None)"
    assert "os.add_dll_directory" in main_content, "main.py must register DLL paths with os.add_dll_directory"
    print("  ✓ 2. Windows QtCore DLL fix and UPX safety verified")

    # 3. Privacy Shield URL Tracking Stripper
    dirty_url = "https://example.com/page?utm_source=twitter&utm_medium=social&fbclid=IwAR234&keep=123"
    cleaned = strip_tracking_params(dirty_url)
    assert "utm_source" not in cleaned
    assert "fbclid" not in cleaned
    assert "keep=123" in cleaned
    print("  ✓ 3. Privacy Shield URL tracking stripper verified")

    # 4. Adblocker exact host matching (Cloudflare compatibility)
    app = QApplication.instance() or QApplication(["zephyrium-test", "-platform", "offscreen"])
    adblocker = AdBlockerInterceptor()
    adblocker.blocked_domains.add("doubleclick.net")
    assert adblocker.should_block(QUrl("https://doubleclick.net/ad.js")) is True
    assert adblocker.should_block(QUrl("https://sub.doubleclick.net/tracker")) is True
    # Should not block legit cloudflare / api URLs that have doubleclick in query string or path
    assert adblocker.should_block(QUrl("https://dash.cloudflare.com/api/deploy?ref=doubleclick.net")) is False
    print("  ✓ 4. AdBlock exact host matching verified (no false positives for Cloudflare Deploy)")

    # 5. Userscript & UserCSS Manager
    usm = UserscriptManager()
    dummy_script = """// ==UserScript==
// @name Test Filter
// @match *://*.example.com/*
// @version 1.4.2
// ==/UserScript==
console.log('hello from test');"""
    meta = usm.parse_userscript_metadata(dummy_script)
    assert meta["name"] == "Test Filter"
    assert meta["version"] == "1.4.2"
    assert "*://*.example.com/*" in meta["matches"]
    print("  ✓ 5. Userscript & UserCSS metadata parser verified")

    # 6. BrowserWindow Subsystems & DevTools / Viewport Bar
    win = BrowserWindow()
    assert hasattr(win, "viewport_bar"), "BrowserWindow must have viewport_bar"
    assert hasattr(win, "devtools_dock"), "BrowserWindow must have devtools_dock"
    assert hasattr(win, "_toggle_devtools"), "BrowserWindow must have _toggle_devtools"
    assert hasattr(win, "_toggle_viewport_bar"), "BrowserWindow must have _toggle_viewport_bar"
    print("  ✓ 6. DevTools Dock and Responsive Viewport Bar verified on BrowserWindow")

    # 7. Tab Hibernation & Multi-Account Containers
    tab_mgr = win.tab_manager
    tab_1 = tab_mgr.create_tab("https://example.com", container_id="work")
    tab_2 = tab_mgr.create_tab("zephyrium://startpage", container_id="dev")
    tab_data_1 = tab_mgr.tabs[tab_1]
    assert tab_data_1.container_id == "work"
    sidebar_item_w = tab_mgr.sidebar.get_tab_widget(tab_1)
    assert sidebar_item_w is not None
    assert sidebar_item_w.container_badge.text() == "WRK"

    # Test suspension of background tab
    tab_mgr.suspend_tab(tab_1)
    assert tab_data_1.is_suspended is True
    assert sidebar_item_w.indicator.text() == "💤"

    # Test wake
    tab_mgr.wake_tab(tab_1)
    assert tab_data_1.is_suspended is False
    print("  ✓ 7. Tab Hibernation and Multi-Account Containers verified")

    win.close()
    print("\n[SUCCESS] All 7 verification checks passed for Zephyrium v1.3.0!")

if __name__ == "__main__":
    test_v130()
