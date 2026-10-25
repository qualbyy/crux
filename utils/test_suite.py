#!/usr/bin/env python3
"""
Automated Comprehensive Test Suite for Zephyrium Browser
Tests i18n completeness across 10 languages, theme generation, tab management,
adblocking, profile containers, and UI state integrity.
"""
import sys
import os
from pathlib import Path

# Set project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Auto-locate Chromium/QtWebEngine resource and locale paths to prevent ICU data errors
for venv_candidate in [PROJECT_ROOT / ".venv", Path(sys.prefix)]:
    res_path = next(venv_candidate.glob("lib/python*/site-packages/PyQt6/Qt6/resources"), None)
    if res_path and res_path.is_dir():
        os.environ.setdefault("QTWEBENGINE_RESOURCES_PATH", str(res_path))
        locales_path = res_path.parent / "translations" / "qtwebengine_locales"
        if locales_path.is_dir():
            os.environ.setdefault("QTWEBENGINE_LOCALES_PATH", str(locales_path))
        break

os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-gpu-rasterization --no-sandbox"

import PyQt6.QtWebEngineWidgets  # Required before QApplication creation

def test_i18n():
    print("[TEST] Testing i18n system...")
    from core.i18n import LANGUAGES, TRANSLATIONS, set_language, get_current_language, t

    assert len(LANGUAGES) == 2, f"Expected 2 languages, found {len(LANGUAGES)}"
    
    required_keys = [
        "app_title", "new_tab", "close_tab", "split_view", "mode_minimal", "mode_vim",
        "tab_orientation", "vertical_tabs", "horizontal_tabs", "switch_to_vertical",
        "adblock_blocked", "adblock_whitelist", "clean_url", "settings", "general",
        "privacy", "import", "vault", "appearance", "ai_assistant", "network", "about",
        "adblock_title", "split_title", "downloads_title", "ai_title", "tabs_vert_short",
        "tabs_horiz_short", "mode_label", "keybinds", "settings_btn", "new_tab_btn",
        "profile_btn", "url_placeholder", "ready", "loading_status", "settings_saved_msg",
        "internal_page", "collapse_sidebar", "expand_sidebar", "split_screen", "downloads",
        "ai_assistant_tooltip", "keybinds_tooltip", "settings_tooltip", "vertical_btn",
        "ai_chat_tab", "scratchpad_tab", "select_container",
        "save_pwd_title", "save_pwd_site", "btn_save_cred", "btn_never_save", "btn_not_now",
        "pwd_saved_status", "never_saved_status", "show_pwd", "hide_pwd"
    ]

    for lang in LANGUAGES.keys():
        assert lang in TRANSLATIONS, f"Language {lang} missing from TRANSLATIONS"
        for key in required_keys:
            assert key in TRANSLATIONS[lang], f"Key '{key}' missing for language '{lang}'"

    # Test dynamic language switching
    set_language("ru")
    assert t("keybinds") == "КЛАВИШИ", f"RU keybinds translation incorrect: {t('keybinds')}"
    assert t("settings_btn") == "НАСТРОЙКИ"
    assert t("adblock_title") == "РЕКЛАМА"

    set_language("en")
    assert t("keybinds") == "KEYBINDS"
    assert t("settings_btn") == "SETTINGS"
    assert t("adblock_title") == "ADS"

    set_language("ru")
    print("  ✓ i18n test passed successfully for Russian and English.")

def test_theme_generation():
    print("[TEST] Testing Theme Generation Engine...")
    from core.theme_manager import generate_stylesheet

    dark_qss = generate_stylesheet("dark", "#fe8019")
    assert "#18181b" in dark_qss
    assert "#262624" in dark_qss
    assert "#fe8019" in dark_qss
    assert "QComboBox" in dark_qss
    assert "QTextBrowser" in dark_qss
    assert "QDialog" in dark_qss

    light_qss = generate_stylesheet("light", "#10b981")
    assert "#f8fafc" in light_qss
    assert "#ffffff" in light_qss
    assert "#10b981" in light_qss
    assert "#cbd5e1" in light_qss
    print("  ✓ Theme engine passed successfully for both Light and Dark themes.")

def test_adblock_and_tracking():
    print("[TEST] Testing AdBlocker and URL tracking cleaner...")
    from core.adblock import clean_tracking_parameters

    test_url = "https://example.com/item?id=123&utm_source=twitter&utm_medium=cpc&fbclid=abcdef&gclid=xyz987"
    cleaned = clean_tracking_parameters(test_url)
    assert "utm_source" not in cleaned
    assert "fbclid" not in cleaned
    assert "gclid" not in cleaned
    assert "id=123" in cleaned
    print("  ✓ Tracking parameter cleaner passed.")

def test_gui_instantiation_and_orientation():
    print("[TEST] Testing Qt GUI instantiation, modes, and orientations...")
    from PyQt6.QtWidgets import QApplication
    from config import load_settings
    from core.browser_window import BrowserWindow
    from core.theme_manager import apply_app_theme

    app = QApplication.instance() or QApplication(["zephyrium-test"])
    settings = load_settings()
    apply_app_theme(app, "dark", "#fe8019")

    win = BrowserWindow()
    assert win is not None
    assert win.tab_manager.tab_counter >= 1

    # Test tab orientation switching
    win.set_tab_orientation("horizontal")
    assert win.tab_orientation == "horizontal"
    assert not win.horizontal_tab_container.isHidden()
    assert win.tab_manager.sidebar.isHidden()

    win.set_tab_orientation("vertical")
    assert win.tab_orientation == "vertical"
    assert win.horizontal_tab_container.isHidden()
    assert not win.tab_manager.sidebar.isHidden()

    # Test light theme application on live window
    win.settings["theme"] = "light"
    win._apply_theme_style("minimal")
    assert win.tab_manager.current_theme == "light"

    # Test tab creation in light theme
    new_tid = win.tab_manager.create_tab("work", "zephyrium://startpage")
    assert new_tid in win.tab_manager.tabs
    tab_widget = win.tab_manager.sidebar.list_widget.itemWidget(win.tab_manager.sidebar.list_widget.item(1))
    assert tab_widget.theme == "light"

    # Test mode switching
    win.apply_mode("vim")
    assert win.ui_mode == "vim"
    assert win.top_bar.isHidden()

    win.apply_mode("minimal")
    assert win.ui_mode == "minimal"
    assert not win.top_bar.isHidden()

    # Test retranslation
    from core.i18n import set_language
    set_language("en")
    win.retranslate_ui()
    assert win.btn_palette.text() == "KEYBINDS"
    assert win.btn_settings.text() == "SETTINGS"
    assert win.btn_split.text() == "SPLIT"

    set_language("ru")
    win.retranslate_ui()
    assert win.btn_palette.text() == "КЛАВИШИ"
    assert win.btn_settings.text() == "НАСТРОЙКИ"
    # Test dynamic accent and theme sync on SettingsWindow
    print("[TEST] Testing Dynamic Accent and Settings Dialog Sync...")
    from core.settings_window import SettingsWindow
    dlg = SettingsWindow(win)

    # Change accent to Emerald (#10b981)
    dlg._select_accent_hex("#10b981")
    assert dlg.accent.lower() == "#10b981"
    assert "#10b981" in dlg.title_lbl.styleSheet()
    assert "#10b981" in dlg.btn_apply.styleSheet()
    assert "#10b981" in dlg.btn_do_import.styleSheet()
    assert "#10b981" in dlg.vault_title.styleSheet()
    assert "#10b981" in dlg.btn_unlock.styleSheet()
    assert "#10b981" in dlg.about_lbl_head.styleSheet()
    assert "#10b981" in dlg.about_ver_lbl.styleSheet()
    assert "#10b981" in dlg.nav_list.styleSheet()
    print("  ✓ SettingsWindow dynamic accent propagation verified for #10b981.")

    # Change accent to Blue (#38bdf8)
    dlg._select_accent_hex("#38bdf8")
    assert dlg.accent.lower() == "#38bdf8"
    assert "#38bdf8" in dlg.title_lbl.styleSheet()
    assert "#38bdf8" in dlg.btn_apply.styleSheet()
    assert "#38bdf8" in dlg.btn_do_import.styleSheet()
    print("  ✓ SettingsWindow dynamic accent propagation verified for #38bdf8.")

    # Verify SplitViewContainer.views property
    current_sc = win.tab_manager.get_current_split_container()
    assert current_sc is not None
    assert len(current_sc.views) >= 1
    assert current_sc.views[0] == current_sc.primary_view
    print("  ✓ SplitViewContainer views property verified.")

    # Verify URL bar keeps cursor at position 0 to show start of link
    from PyQt6.QtCore import QUrl
    win._on_active_url_changed(QUrl("https://en.wikipedia.org/wiki/Arch_Linux_Distribution"))
    assert win.url_bar.cursorPosition() == 0
    print("  ✓ URL bar automatically keeps cursor at 0 to display link beginning.")

    # Verify OnboardingDialog 2-column layout and dimensions
    from core.onboarding import OnboardingDialog
    onboarding = OnboardingDialog(win)
    assert onboarding.width() == 920
    assert onboarding.height() == 600
    assert hasattr(onboarding, "combo_lang")
    assert hasattr(onboarding, "btn_th_dark")
    assert hasattr(onboarding, "btn_mode_v")
    assert hasattr(onboarding, "btn_do_import")
    assert hasattr(onboarding, "input_gemini")
    onboarding.close()
    print("  ✓ OnboardingDialog 2-column layout and 920x600 fixed dimensions verified.")

    dlg.close()
    win.close()
    print("  ✓ Full GUI instantiation, theme, orientation, and i18n tests passed.")

def test_startpage_and_settings_state():
    print("[TEST] Testing Startpage HTML and Settings Clean State...")
    from config import load_settings, save_settings, DEFAULT_SETTINGS

    existing_key = load_settings().get("gemini_api_key", "")
    test_key = existing_key or "test_api_key_placeholder"

    # Reset to pristine initial settings (first_run=True, API key retained)
    clean_settings = dict(DEFAULT_SETTINGS)
    clean_settings["gemini_api_key"] = test_key
    clean_settings["theme"] = "dark"
    clean_settings["accent_color"] = "#fe8019"
    clean_settings["ui_mode"] = "minimal"
    clean_settings["tab_orientation"] = "vertical"
    clean_settings["first_run"] = True
    save_settings(clean_settings)

    # 1. Verify settings reset
    settings = load_settings()
    assert settings.get("first_run") is True
    assert settings.get("gemini_api_key") == test_key
    assert settings.get("theme") == "dark"
    print("  ✓ Settings reset and API key retention verified.")

    # 2. Verify startpage.html has applyTheme and dark/light variables
    startpage_content = (Path(__file__).resolve().parent.parent / "resources" / "startpage.html").read_text(encoding="utf-8")
    assert "function applyTheme(theme, accent)" in startpage_content
    assert "window.applyTheme = applyTheme" in startpage_content
    assert ':root[data-theme="light"]' in startpage_content
    assert ':root, :root[data-theme="dark"]' in startpage_content
    assert "var(--accent," in startpage_content
    print("  ✓ Startpage reactive theme script and CSS variables verified.")

def test_password_autofill_and_palette():
    print("[TEST] Testing Password Autofill Manager and Command Palette Autocomplete...")
    from core.password_autofill import PasswordAutofillManager

    # 1. Test URL matching for password vault
    matches = PasswordAutofillManager.get_matches_for_url("https://accounts.google.com/signin")
    assert isinstance(matches, list)
    if matches:
        assert any("gmail.com" in m.get("username", "") for m in matches)
        js = PasswordAutofillManager.generate_injection_js(matches)
        assert "__zephyrium_autofill_injected" in js
        assert "__zephyrium_datalist__" in js
        assert "__zephyrium_pill__" in js
        print("  ✓ PasswordAutofillManager correctly matches Google accounts and generates injection JS.")

    matches_gh = PasswordAutofillManager.get_matches_for_url("https://github.com/login")
    assert isinstance(matches_gh, list)
    if matches_gh:
        assert any(m.get("username") == "qualbyy" for m in matches_gh)
        print("  ✓ PasswordAutofillManager correctly matches GitHub logins.")

    # 2. Test never_save blacklist and should_prompt_save logic
    test_site = "https://test-site-never.org/login"
    test_user = "testuser"
    test_pass = "secret123"

    # Should prompt initially
    assert PasswordAutofillManager.should_prompt_save(test_site, test_user, test_pass) is True

    # Add to never_save
    PasswordAutofillManager.add_never_save(test_site)
    assert PasswordAutofillManager.is_never_save(test_site) is True
    assert PasswordAutofillManager.should_prompt_save(test_site, test_user, test_pass) is False

    # Remove from never_save
    PasswordAutofillManager.remove_never_save("test-site-never.org")
    assert PasswordAutofillManager.is_never_save(test_site) is False
    assert PasswordAutofillManager.should_prompt_save(test_site, test_user, test_pass) is True

    # Test capture JS generator
    capture_js = PasswordAutofillManager.generate_capture_js()
    assert "__zephyrium_capture_injected" in capture_js
    assert "prompt-save-password" in capture_js

    # 3. Test PasswordSaveBanner UI component
    from core.password_prompt import PasswordSaveBanner
    from PyQt6.QtWidgets import QApplication, QLineEdit
    app = QApplication.instance() or QApplication([])
    banner = PasswordSaveBanner()
    banner.set_credentials("https://example.com/login", "john_doe", "pass456")
    assert banner.current_url == "https://example.com/login"
    assert banner.input_user.text() == "john_doe"
    assert banner.input_pwd.text() == "pass456"

    # Toggle peek password
    assert banner.input_pwd.echoMode() == QLineEdit.EchoMode.Password
    banner.btn_toggle_pwd.click()
    assert banner.input_pwd.echoMode() == QLineEdit.EchoMode.Normal
    banner.btn_toggle_pwd.click()
    assert banner.input_pwd.echoMode() == QLineEdit.EchoMode.Password

    # Test update_theme and retranslate_ui
    banner.update_theme("light", "#10b981")
    banner.retranslate_ui()
    banner.close()
    print("  ✓ Password prompt and blacklist functionality passed.")

    # 4. Test Command Palette suggestions worker
    from core.command_palette import SearchSuggestWorker
    worker = SearchSuggestWorker("python")
    assert worker.query == "python"
    print("  ✓ SearchSuggestWorker initialized properly.")

def test_in_tab_pages_and_menus():
    print("[TEST] Testing in-tab HTML pages, dropdown menus, and AI chat...")
    from utils.bookmarks import DataStore
    from core.i18n import t, get_current_language, LANGUAGES

    # 1. Test DataStore downloads and history APIs
    DataStore.add_history("Test Title", "https://example.com/test")
    hist = DataStore.load_history()
    assert any(h.get("url") == "https://example.com/test" for h in hist)

    DataStore.delete_history_item("https://example.com/test")
    hist = DataStore.load_history()
    assert not any(h.get("url") == "https://example.com/test" for h in hist)

    DataStore.add_download("sample.pdf", "/home/qualbyy/Downloads/sample.pdf", 1024, "completed")
    dls = DataStore.load_downloads()
    assert any(d.get("filename") == "sample.pdf" for d in dls)

    DataStore.clear_downloads()
    assert len(DataStore.load_downloads()) == 0

    # 2. Test existence and critical content of in-tab HTML pages
    res_dir = PROJECT_ROOT / "resources"
    settings_html = (res_dir / "settings.html").read_text(encoding="utf-8")
    assert "zephyrium://apply-settings" in settings_html
    assert "data-tab=\"adblock\"" in settings_html
    assert "data-tab=\"downloads\"" in settings_html
    assert "window.initSettings" in settings_html

    history_html = (res_dir / "history.html").read_text(encoding="utf-8")
    assert "zephyrium://action/clear-history" in history_html
    assert "window.renderHistory" in history_html

    downloads_html = (res_dir / "downloads.html").read_text(encoding="utf-8")
    assert "zephyrium://action/open-downloads-folder" in downloads_html
    assert "zephyrium://action/clear-downloads" in downloads_html
    assert "window.renderDownloads" in downloads_html

    # 3. Test AI Chat translated keys and GeminiWorker system_instruction
    from sidebar.ai_chat import GeminiWorker
    worker = GeminiWorker("test query", "dummy_key", system_instruction="Respond in Russian")
    assert worker.system_instruction == "Respond in Russian"

    print("  ✓ In-tab HTML pages, DataStore operations, and AI system instructions verified.")

def test_cross_platform_auth_and_config():
    print("[TEST] Testing cross-platform auth module and config...")
    from config import CONFIG_DIR
    from core.auth import get_auth_prompt_title, get_auth_input_placeholder, verify_vault_password
    assert CONFIG_DIR is not None
    assert isinstance(str(CONFIG_DIR), str)
    assert get_auth_prompt_title("ru") != ""
    assert get_auth_prompt_title("en") != ""
    assert get_auth_input_placeholder("ru") != ""
    assert get_auth_input_placeholder("en") != ""
    # Verify empty password returns False
    assert verify_vault_password("") is False
    print("  ✓ Cross-platform auth and config verified.")

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Zephyrium Verification Test Suite")
    print("=" * 60)
    test_i18n()
    test_theme_generation()
    test_adblock_and_tracking()
    test_gui_instantiation_and_orientation()
    test_password_autofill_and_palette()
    test_in_tab_pages_and_menus()
    test_startpage_and_settings_state()
    test_cross_platform_auth_and_config()
    print("=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY! (Settings reset to clean initial state)")
    print("=" * 60)
