"""
Visual verification and screenshot capture script for Zephyrium browser.
Captures screenshots of:
1. Main browser window in Russian with vertical tabs (clean tabs, no containers)
2. Horizontal tab mode (clean tabs, no container prefixes, correct localized button)
3. Settings page (General, Privacy, Appearance, About with GitHub and Telegram buttons)
"""
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (
    "--enable-gpu-rasterization "
    "--enable-zero-copy "
    "--ignore-gpu-blocklist "
    "--ozone-platform-hint=auto"
)
for venv_candidate in [PROJECT_ROOT / ".venv", Path(sys.prefix)]:
    res_path = next(venv_candidate.glob("lib/python*/site-packages/PyQt6/Qt6/resources"), None)
    if res_path and res_path.is_dir():
        os.environ.setdefault("QTWEBENGINE_RESOURCES_PATH", str(res_path))
        locales_path = res_path.parent / "translations" / "qtwebengine_locales"
        if locales_path.is_dir():
            os.environ.setdefault("QTWEBENGINE_LOCALES_PATH", str(locales_path))
        break

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView

def capture_visuals():
    from config import load_settings, save_settings
    s = load_settings()
    s["first_run"] = False
    s["language"] = "ru"
    s["theme"] = "dark"
    s["tab_orientation"] = "vertical"
    save_settings(s)

    app = QApplication.instance() or QApplication(sys.argv)
    from core.theme_manager import apply_app_theme
    apply_app_theme(app, "dark", s.get("accent_color", "#fe8019"))

    from core.browser_window import BrowserWindow
    win = BrowserWindow()
    win.resize(1280, 800)
    win.show()
    app.processEvents()

    screenshot_dir = Path("/home/qualbyy/.gemini/antigravity/brain/ca341344-639c-4e9a-bb18-360b6b6ab68a")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    # 1. Main window with vertical tabs
    app.processEvents()
    QTest.qWait(600)
    app.processEvents()
    pix1 = win.grab()
    path1 = screenshot_dir / "verify_vertical_ru.png"
    pix1.save(str(path1), "PNG")
    print(f"Captured: {path1}", flush=True)

    # 2. Switch to horizontal tabs
    win.set_tab_orientation("horizontal")
    win.tab_manager.create_tab("https://example.com")
    app.processEvents()
    QTest.qWait(600)
    app.processEvents()
    pix2 = win.grab()
    path2 = screenshot_dir / "verify_horizontal_ru.png"
    pix2.save(str(path2), "PNG")
    print(f"Captured: {path2}", flush=True)

    # 3. Test horizontal tab clicking
    win.tab_manager.select_tab(1)
    app.processEvents()
    QTest.qWait(300)
    app.processEvents()
    pix3 = win.grab()
    path3 = screenshot_dir / "verify_horizontal_click.png"
    pix3.save(str(path3), "PNG")
    print(f"Captured: {path3}", flush=True)

    # 4. Open Settings Tab (About tab)
    win.tab_manager.create_tab("zephyrium://about")
    app.processEvents()
    QTest.qWait(1000)
    app.processEvents()
    pix4 = win.grab()
    path4 = screenshot_dir / "verify_settings_about.png"
    pix4.save(str(path4), "PNG")
    print(f"Captured: {path4}", flush=True)

    # 5. Switch to Vertical again and take screenshot
    win.set_tab_orientation("vertical")
    app.processEvents()
    QTest.qWait(600)
    app.processEvents()
    pix5 = win.grab()
    path5 = screenshot_dir / "verify_vertical_settings.png"
    pix5.save(str(path5), "PNG")
    print(f"Captured: {path5}", flush=True)

    # 6. Test Vim mode and corner exit button
    win.apply_mode("vim")
    app.processEvents()
    QTest.qWait(600)
    app.processEvents()
    assert win.vim_exit_btn.isVisible(), "vim_exit_btn should be visible in vim mode"
    assert win.status_vim_exit_btn.isVisible(), "status_vim_exit_btn should be visible in vim mode"
    pix6 = win.grab()
    path6 = screenshot_dir / "verify_vim_mode.png"
    pix6.save(str(path6), "PNG")
    print(f"Captured: {path6}", flush=True)

    # 7. Test exiting Vim mode via corner exit button
    win.vim_exit_btn.click()
    app.processEvents()
    QTest.qWait(600)
    app.processEvents()
    assert not win.vim_exit_btn.isVisible(), "vim_exit_btn should be hidden in minimal mode"
    assert win.ui_mode == "minimal", "Mode should be restored to minimal"
    pix7 = win.grab()
    path7 = screenshot_dir / "verify_vim_exited.png"
    pix7.save(str(path7), "PNG")
    print(f"Captured: {path7}", flush=True)

    # 8. Open Settings Tab and verify
    win.tab_manager.create_tab("zephyrium://settings")
    app.processEvents()
    QTest.qWait(1200)
    app.processEvents()
    active_view = win.tab_manager.get_current_view()
    assert active_view is not None
    assert "settings.html" in active_view.url().toString()
    
    # Simulate changing settings live (e.g. accent color and language)
    active_view.page().runJavaScript("if (window.applySettingLive) window.applySettingLive('accent_color', '#38bdf8');")
    app.processEvents()
    QTest.qWait(600)
    app.processEvents()
    assert "about:blank#blocked" not in active_view.url().toString(), f"URL got blocked: {active_view.url().toString()}"
    assert "settings.html" in active_view.url().toString(), f"Page navigated away: {active_view.url().toString()}"

    active_view.page().runJavaScript("if (window.applySettingLive) window.applySettingLive('theme', 'dark');")
    app.processEvents()
    QTest.qWait(600)
    app.processEvents()
    assert "about:blank#blocked" not in active_view.url().toString(), f"URL got blocked: {active_view.url().toString()}"

    pix8 = win.grab()
    path8 = screenshot_dir / "verify_settings_ru.png"
    pix8.save(str(path8), "PNG")
    print(f"Captured: {path8}", flush=True)

    win.close()
    app.processEvents()
    print("All verification screenshots captured successfully.", flush=True)
    sys.exit(0)

if __name__ == "__main__":
    capture_visuals()
