#!/usr/bin/env python3
"""
Comprehensive Verification Suite for Zephyrium v1.3.6
Covers checklist items:
1. Version consistency (1.3.6 across config, installer, settings)
2. Ollama local LLM settings, worker, and detector
3. Containers discovery UI in settings.html
4. File manager launcher logic (prioritizing GUI file managers)
5. Password autofill SPA & Google multi-step patterns
6. Claude Code Minimal Dark Task Manager (zephyrium://tasks) with active tab guard
7. Ephemeral incognito profile isolation
8. TabManager active tab suspension guard
9. Primary browser menu (☰) & DevTools QSplitter integration
"""
import sys
import os
import unittest
from unittest.mock import patch
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Setup Chromium/QtWebEngine resource and scheme registration before QApplication
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtWebEngineCore import QWebEngineUrlScheme

for s_name in [b"crux", b"zephyrium", b"zinc"]:
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
        if not locales_path.is_dir():
            locales_path = res_path / "translations" / "qtwebengine_locales"
        if locales_path.is_dir():
            os.environ.setdefault("QTWEBENGINE_LOCALES_PATH", str(locales_path))
        break

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)

from config import APP_VERSION, CONFIG_DIR, DEFAULT_SETTINGS, load_settings
from utils.bookmarks import open_folder_in_file_manager
from core.password_autofill import PasswordAutofillManager
from core.adblock import AdBlockerInterceptor as AdBlocker
from core.profile_manager import ProfileManager
from core.tab_manager import TabManager
from core.web_view import ZincWebView

class TestZephyriumV136(unittest.TestCase):

    def test_01_version_consistency(self):
        """Verify version 1.3.6 is consistent across config, installer, and settings HTML."""
        self.assertEqual(APP_VERSION, "1.3.6", f"Expected APP_VERSION == '1.3.6', got {APP_VERSION}")

        iss_path = PROJECT_ROOT / "installer.iss"
        with open(iss_path, "r", encoding="utf-8") as f:
            iss_content = f.read()
        self.assertIn('#define MyAppVersion "1.3.6"', iss_content, "installer.iss missing MyAppVersion 1.3.6")

        settings_path = PROJECT_ROOT / "resources" / "settings.html"
        with open(settings_path, "r", encoding="utf-8") as f:
            settings_html = f.read()
        self.assertIn("1.3.6 (Release)", settings_html, "settings.html missing '1.3.6 (Release)'")
        print("  ✓ 1. Version 1.3.6 verified across config.py, installer.iss, and settings.html")

    def test_02_ollama_ui_and_settings_integration(self):
        """Verify Ollama integration, settings fields, detector worker, and chat provider support."""
        settings_path = PROJECT_ROOT / "resources" / "settings.html"
        with open(settings_path, "r", encoding="utf-8") as f:
            settings_html = f.read()

        self.assertIn("setting-ai-provider", settings_html, "settings.html missing AI provider selector")
        self.assertIn("setting-ollama-url", settings_html, "settings.html missing Ollama URL input")
        self.assertIn("setting-ollama-model", settings_html, "settings.html missing Ollama model input")
        self.assertIn("testOllamaConnection", settings_html, "settings.html missing testOllamaConnection function")
        self.assertIn("onOllamaTestResult", settings_html, "settings.html missing onOllamaTestResult handler")

        # Test sidebar AI chat module
        from sidebar.ai_chat import OllamaDetectorWorker, OllamaWorker
        detector = OllamaDetectorWorker("http://localhost:11434")
        self.assertEqual(detector.base_url, "http://localhost:11434")

        worker = OllamaWorker(query="Hello", base_url="http://localhost:11434", model="llama3")
        self.assertEqual(worker.model, "llama3")
        print("  ✓ 2. Ollama local LLM integration and UI settings verified")

    def test_03_containers_discovery_section(self):
        """Verify multi-account containers are clearly exposed in settings.html and documented."""
        settings_path = PROJECT_ROOT / "resources" / "settings.html"
        with open(settings_path, "r", encoding="utf-8") as f:
            settings_html = f.read()

        self.assertIn('data-tab="containers"', settings_html, "settings.html missing containers tab button")
        self.assertIn('id="tab-containers"', settings_html, "settings.html missing tab-containers content block")
        self.assertIn("ЛИЧНЫЙ (PERSONAL)", settings_html, "settings.html missing Personal container card")
        self.assertIn("РАБОТА (WORK)", settings_html, "settings.html missing Work container card")
        self.assertIn("БАНКИНГ (BANKING)", settings_html, "settings.html missing Banking container card")
        self.assertIn("ШОПИНГ (SHOPPING)", settings_html, "settings.html missing Shopping container card")
        self.assertIn("ИЗОЛИРОВАННЫЙ (ISOLATED)", settings_html, "settings.html missing Isolated container card")
        print("  ✓ 3. Multi-account containers discovery UI verified")

    @patch("subprocess.Popen")
    def test_04_file_manager_launcher_priority(self, mock_popen):
        """Verify file manager opener prioritizes Dolphin, Nautilus, etc., over Filelight."""
        mock_popen.return_value = None
        test_dir = str(PROJECT_ROOT)
        result = open_folder_in_file_manager(test_dir)
        self.assertTrue(result, "open_folder_in_file_manager failed to launch handler")
        mock_popen.assert_called_once()
        called_args = mock_popen.call_args[0][0]
        self.assertNotIn("filelight", called_args[0].lower())
        print(f"  ✓ 4. System file manager opener verified (launched: {called_args[0]})")

    def test_05_autofill_multi_step_patterns(self):
        """Verify autofill multi-step script contains Google and modern SPA input patterns."""
        autofill_mgr = PasswordAutofillManager()
        script = autofill_mgr.generate_injection_js([{"username": "testuser", "password": "secretpass"}])

        self.assertIn("identifierId", script, "Script missing Google identifierId pattern")
        self.assertIn('type="email"', script, "Script missing email input selector")
        self.assertIn("__crux_last_user", script, "Script missing multi-step session storage logic")
        print("  ✓ 5. Password autofill SPA & Google multi-step patterns verified")

    def test_06_tasks_page_minimal_dark_aesthetic(self):
        """Verify zephyrium://tasks contains Claude Code Minimal Dark styling and metrics."""
        tasks_html = ZincWebView._generate_tasks_html(None)

        self.assertIn("#18181b", tasks_html, "Tasks HTML missing zinc-900 background")
        self.assertIn("ДИСПЕТЧЕР ЗАДАЧ", tasks_html, "Tasks HTML missing title")
        self.assertIn("ВСЕГО ВКЛАДОК", tasks_html, "Tasks HTML missing metrics card")
        self.assertIn("ЭКОНОМИЯ ОЗУ", tasks_html, "Tasks HTML missing RAM saving card")
        print("  ✓ 6. Claude Code Minimal Dark Tasks Manager verified")

    def test_07_pyqt6_components_structure(self):
        """Verify PyQt6 browser components load and configure properly."""
        adblocker = AdBlocker()
        pm = ProfileManager(adblocker)
        # Verify incognito profiles are in-memory (off the record)
        incognito_prof = pm.get_profile("default", is_incognito=True)
        self.assertTrue(incognito_prof.isOffTheRecord(), "Incognito profile must be off-the-record / in-memory")

        # Verify standard profiles are persistent
        regular_prof = pm.get_profile("work", is_incognito=False)
        self.assertFalse(regular_prof.isOffTheRecord(), "Regular profile should be persistent on disk")
        print("  ✓ 7. ProfileManager ephemeral incognito isolation verified")

    def test_08_tab_manager_hibernation_guard(self):
        """Verify active tab cannot be suspended."""
        adblocker = AdBlocker()
        pm = ProfileManager(adblocker)
        tm = TabManager(pm)
        tab_id = tm.create_tab("default", "https://example.com")
        self.assertEqual(tm.active_tab_id, tab_id)

        # Attempting to suspend the active tab MUST return False and not crash
        suspended = tm.suspend_tab(tab_id)
        self.assertFalse(suspended, "Active tab must NEVER be suspended!")
        self.assertFalse(tm.tabs[tab_id].is_suspended)
        print("  ✓ 8. Active tab suspension protection verified")

    def test_09_browser_window_menu_and_devtools(self):
        """Verify BrowserWindow has the new primary dropdown menu and DevTools splitter integration."""
        from core.browser_window import BrowserWindow
        win = BrowserWindow()

        # Check menu button
        self.assertTrue(hasattr(win, "btn_menu"), "BrowserWindow missing btn_menu (☰)")
        self.assertEqual(win.btn_menu.text(), "☰")

        # Check devtools vertical splitter
        self.assertTrue(hasattr(win, "main_vertical_splitter"), "BrowserWindow missing main_vertical_splitter")
        self.assertTrue(hasattr(win, "devtools_dock"), "BrowserWindow missing devtools_dock")
        self.assertTrue(hasattr(win, "open_devtools"), "BrowserWindow missing open_devtools method")
        self.assertTrue(hasattr(win, "close_devtools"), "BrowserWindow missing close_devtools method")

        # Check downloads folder launcher
        self.assertTrue(hasattr(win, "_open_downloads_folder"), "BrowserWindow missing _open_downloads_folder")

        win.close()
        print("  ✓ 9. Primary browser dropdown menu (☰) & DevTools QSplitter verified")

if __name__ == "__main__":
    unittest.main()
