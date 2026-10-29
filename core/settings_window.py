"""
Settings & Configuration Window for Zinc Browser
Includes:
- Language Selector (10 languages via i18n)
- Privacy & AdBlock Whitelist Manager
- Browser Data Migration / Importer
- Protected Vault: Passwords & Cookies (Requires sudo authorization to view & export)
- Appearance & UI Layout Modes (Minimal Dark, Material Expressive, Vim Mode)
- Gemini AI Key & Dynamic Model Selector
- Advanced & Network Configuration
"""
import os
import sys
import json
import time
import subprocess
import csv
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QListWidget, QListWidgetItem, QLineEdit, QComboBox,
    QCheckBox, QFileDialog, QFrame, QSpinBox, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QMessageBox
)
from config import load_settings, save_settings, COLORS, CONFIG_DIR, ACCENT_PRESETS, APP_NAME, APP_VERSION
from core.importer import BrowserImporter, BrowserProfile, PASSWORDS_FILE, COOKIES_FILE
from core.adblock import WHITELIST_FILE, AdBlockerInterceptor
from core.i18n import t, LANGUAGES, set_language, get_current_language
from core.theme_manager import apply_app_theme
from PyQt6.QtWidgets import QApplication

class SettingsWindow(QDialog):
    settings_saved = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Dialog)
        self.setWindowTitle(f"Crux // {t('settings')}")
        self.resize(880, 620)
        self.setObjectName("settingsWindow")

        self.settings = load_settings()
        self.detected_browsers = BrowserImporter.get_detected_browsers()
        self.vault_unlocked = False

        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Header
        th = self.settings.get("theme", "dark")
        acc = self.settings.get("accent_color", "#a855f7")
        self.theme = th
        self.accent = acc

        head_layout = QHBoxLayout()
        self.title_lbl = QLabel(f"// {t('settings').upper()}")
        self.title_lbl.setStyleSheet(f"""
            color: {acc};
            font-size: 14px;
            font-weight: bold;
            font-family: "Iosevka Nerd Font", monospace;
        """)
        head_layout.addWidget(self.title_lbl)
        head_layout.addStretch()

        btn_close_x = QPushButton("×")
        btn_close_x.setFixedSize(24, 24)
        btn_close_x.clicked.connect(self.reject)
        head_layout.addWidget(btn_close_x)
        main_layout.addLayout(head_layout)

        # Body: Left navigation categories + Right stacked pages
        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)

        th = self.settings.get("theme", "dark")
        acc = self.settings.get("accent_color", "#a855f7")
        nav_bg = "#ffffff" if th == "light" else "#262624"
        nav_border = "#cbd5e1" if th == "light" else "#3f3f46"
        item_color = "#334155" if th == "light" else "#d4d4d8"
        item_hover_bg = "#f1f5f9" if th == "light" else "#2d2d2a"
        item_sel_bg = "#f8fafc" if th == "light" else "#18181b"
        item_border = "#e2e8f0" if th == "light" else "#2b2b29"
        text_bright = "#0f172a" if th == "light" else "#f5f5f0"

        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(245)
        self.nav_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {nav_bg};
                border: 1px solid {nav_border};
                outline: none;
            }}
            QListWidget::item {{
                color: {item_color};
                padding: 10px 12px;
                border-bottom: 1px solid {item_border};
                font-size: 12px;
            }}
            QListWidget::item:hover {{
                background-color: {item_hover_bg};
                color: {text_bright};
            }}
            QListWidget::item:selected {{
                background-color: {item_sel_bg};
                color: {text_bright};
                border-left: 2px solid {acc};
            }}
        """)
        self.nav_list.currentRowChanged.connect(self._on_category_changed)
        body_layout.addWidget(self.nav_list)

        # Pages Stack
        self.pages_stack = QStackedWidget()
        body_layout.addWidget(self.pages_stack, stretch=1)
        main_layout.addLayout(body_layout, stretch=1)

        # Initialize All 8 Pages
        self._init_general_page()
        self._init_privacy_page()
        self._init_import_page()
        self._init_vault_page()
        self._init_appearance_page()
        self._init_ai_page()
        self._init_network_page()
        self._init_about_page()

        # Footer
        footer = QHBoxLayout()
        self.status_lbl = QLabel("Ready")
        self.status_lbl.setStyleSheet("color: #71717a; font-size: 11px;")
        footer.addWidget(self.status_lbl)
        footer.addStretch()

        btn_cancel = QPushButton(t("cancel").upper())
        btn_cancel.clicked.connect(self.reject)

        self.btn_apply = QPushButton(t("save_apply_btn"))
        self.btn_apply.setObjectName("accentBtn")
        self.btn_apply.setStyleSheet(f"border-color: {acc}; color: {acc}; font-weight: bold; min-width: 140px;")
        self.btn_apply.clicked.connect(self._save_all)

        footer.addWidget(btn_cancel)
        footer.addWidget(self.btn_apply)
        main_layout.addLayout(footer)

        self.nav_list.setCurrentRow(0)

    def _add_category(self, title: str, widget: QWidget):
        item = QListWidgetItem(title)
        self.nav_list.addItem(item)
        self.pages_stack.addWidget(widget)

    def _on_category_changed(self, row: int):
        self.pages_stack.setCurrentIndex(row)

    # =========================================================================
    # 1. GENERAL PAGE
    # =========================================================================
    def _init_general_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        lbl_head = QLabel(f"01 // {t('general').upper()}")
        lbl_head.setProperty("class", "sectionHeader")
        layout.addWidget(lbl_head)

        # Language Selection
        layout.addWidget(QLabel(f"{t('language')}:"))
        self.combo_lang = QComboBox()
        current_lang = self.settings.get("language", get_current_language())
        for code, name in LANGUAGES.items():
            self.combo_lang.addItem(f"{name} ({code})", code)
        idx = self.combo_lang.findData(current_lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        layout.addWidget(self.combo_lang)

        # Homepage
        layout.addWidget(QLabel(t("homepage_url")))
        self.input_homepage = QLineEdit(self.settings.get("homepage", "crux://startpage"))
        layout.addWidget(self.input_homepage)

        # New Tab URL
        layout.addWidget(QLabel(t("new_tab_url_label")))
        self.input_new_tab_url = QLineEdit(self.settings.get("new_tab_url", self.settings.get("homepage", "crux://startpage")))
        layout.addWidget(self.input_new_tab_url)

        # Search Engine
        layout.addWidget(QLabel(t("search_engine")))
        self.combo_search = QComboBox()
        self.combo_search.addItem("DuckDuckGo (Privacy Focused)", "https://duckduckgo.com/?q={query}")
        self.combo_search.addItem("Google Search", "https://www.google.com/search?q={query}")
        self.combo_search.addItem("Brave Search", "https://search.brave.com/search?q={query}")
        self.combo_search.addItem("Kagi Search", "https://kagi.com/search?q={query}")
        layout.addWidget(self.combo_search)

        # Download Directory
        layout.addWidget(QLabel(t("downloads_dir")))
        dl_row = QHBoxLayout()
        self.input_download_dir = QLineEdit(self.settings.get("download_dir", str(Path.home() / "Downloads")))
        btn_browse_dl = QPushButton(t("browse"))
        btn_browse_dl.clicked.connect(self._browse_download_dir)
        dl_row.addWidget(self.input_download_dir, stretch=1)
        dl_row.addWidget(btn_browse_dl)
        layout.addLayout(dl_row)

        self.chk_restore_session = QCheckBox(t("restore_tabs"))
        self.chk_restore_session.setChecked(self.settings.get("restore_session", False))
        layout.addWidget(self.chk_restore_session)

        layout.addStretch()
        self._add_category(f"01 // {t('general')}", page)

    def _browse_download_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Downloads Directory", self.input_download_dir.text())
        if d:
            self.input_download_dir.setText(d)

    # =========================================================================
    # 2. PRIVACY & ADBLOCK PAGE
    # =========================================================================
    def _init_privacy_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_head = QLabel(f"02 // {t('privacy').upper()}")
        lbl_head.setProperty("class", "sectionHeader")
        layout.addWidget(lbl_head)

        self.chk_adblock = QCheckBox(t("enable_adblock"))
        self.chk_adblock.setChecked(self.settings.get("adblock_enabled", True))
        layout.addWidget(self.chk_adblock)

        self.chk_clean_urls = QCheckBox(t("clean_urls_label"))
        self.chk_clean_urls.setChecked(self.settings.get("clean_urls", True))
        layout.addWidget(self.chk_clean_urls)

        self.chk_dnt = QCheckBox(t("send_dnt_label"))
        self.chk_dnt.setChecked(self.settings.get("send_dnt", True))
        layout.addWidget(self.chk_dnt)

        self.chk_webrtc = QCheckBox(t("prevent_webrtc_label"))
        self.chk_webrtc.setChecked(self.settings.get("prevent_webrtc_leak", True))
        layout.addWidget(self.chk_webrtc)

        # Whitelist Section
        layout.addWidget(QLabel(t("whitelist_title")))
        wl_add_row = QHBoxLayout()
        self.input_wl_domain = QLineEdit()
        self.input_wl_domain.setPlaceholderText("e.g. example.com or github.com")
        btn_add_wl = QPushButton(t("add_domain_btn"))
        btn_add_wl.clicked.connect(self._add_to_whitelist)
        wl_add_row.addWidget(self.input_wl_domain, stretch=1)
        wl_add_row.addWidget(btn_add_wl)
        layout.addLayout(wl_add_row)

        self.list_wl = QListWidget()
        self.list_wl.setFixedHeight(100)
        self.list_wl.setStyleSheet("background: #18181b; border: 1px solid #3f3f46;")
        self._reload_whitelist_ui()
        layout.addWidget(self.list_wl)

        btn_remove_wl = QPushButton(t("remove_domain_btn"))
        btn_remove_wl.clicked.connect(self._remove_from_whitelist)
        layout.addWidget(btn_remove_wl)

        layout.addStretch()
        self._add_category(f"02 // {t('privacy')}", page)

    def _reload_whitelist_ui(self):
        self.list_wl.clear()
        if WHITELIST_FILE.exists():
            try:
                with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for d in data:
                        self.list_wl.addItem(d)
            except Exception:
                pass

    def _add_to_whitelist(self):
        dom = self.input_wl_domain.text().strip().lower()
        if not dom:
            return
        current = []
        if WHITELIST_FILE.exists():
            try:
                with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                    current = json.load(f)
            except Exception:
                current = []
        if dom not in current:
            current.append(dom)
            with open(WHITELIST_FILE, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
            self.input_wl_domain.clear()
            self._reload_whitelist_ui()

    def _remove_from_whitelist(self):
        item = self.list_wl.currentItem()
        if not item:
            return
        dom = item.text()
        current = []
        if WHITELIST_FILE.exists():
            try:
                with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                    current = json.load(f)
            except Exception:
                current = []
        if dom in current:
            current.remove(dom)
            with open(WHITELIST_FILE, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
            self._reload_whitelist_ui()

    # =========================================================================
    # 3. IMPORT PAGE
    # =========================================================================
    def _init_import_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        lbl_head = QLabel(f"03 // {t('import').upper()}")
        lbl_head.setProperty("class", "sectionHeader")
        layout.addWidget(lbl_head)

        layout.addWidget(QLabel(t("select_browser_import")))
        self.combo_browser = QComboBox()
        if self.detected_browsers:
            for b in self.detected_browsers:
                self.combo_browser.addItem(f"[{b.browser_type.upper()}] {b.name} ({b.path.parent.name})", b)
        else:
            self.combo_browser.addItem("No browsers auto-detected (specify custom path below)", None)
        layout.addWidget(self.combo_browser)

        layout.addWidget(QLabel(t("custom_profile_dir")))
        custom_row = QHBoxLayout()
        self.input_custom_path = QLineEdit()
        self.input_custom_path.setPlaceholderText("~/.config/google-chrome/Default or ~/.mozilla/firefox/...")
        btn_browse_custom = QPushButton(t("browse"))
        btn_browse_custom.clicked.connect(self._browse_custom_profile)
        custom_row.addWidget(self.input_custom_path, stretch=1)
        custom_row.addWidget(btn_browse_custom)
        layout.addLayout(custom_row)

        layout.addWidget(QLabel(t("items_to_import")))
        types_row = QHBoxLayout()
        self.chk_imp_bookmarks = QCheckBox(t("bookmarks"))
        self.chk_imp_bookmarks.setChecked(True)
        self.chk_imp_history = QCheckBox(t("history"))
        self.chk_imp_history.setChecked(True)
        self.chk_imp_cookies = QCheckBox(t("cookies"))
        self.chk_imp_cookies.setChecked(True)
        self.chk_imp_passwords = QCheckBox(t("passwords"))
        self.chk_imp_passwords.setChecked(True)
        types_row.addWidget(self.chk_imp_bookmarks)
        types_row.addWidget(self.chk_imp_history)
        types_row.addWidget(self.chk_imp_cookies)
        types_row.addWidget(self.chk_imp_passwords)
        layout.addLayout(types_row)

        action_row = QHBoxLayout()
        acc = getattr(self, "accent", "#a855f7")
        th = getattr(self, "theme", "dark")
        btn_bg = "#ffffff" if th == "light" else "#262624"
        self.btn_do_import = QPushButton(t("start_import_btn"))
        self.btn_do_import.setStyleSheet(f"background-color: {btn_bg}; border-color: {acc}; color: {acc}; font-weight: bold; padding: 6px 12px;")
        self.btn_do_import.clicked.connect(self._run_import)

        btn_imp_csv_pwd = QPushButton(t("import_csv_btn"))
        btn_imp_csv_pwd.clicked.connect(self._import_csv_dialog)
        action_row.addWidget(self.btn_do_import, stretch=1)
        action_row.addWidget(btn_imp_csv_pwd)
        layout.addLayout(action_row)

        self.import_log = QTextEdit()
        self.import_log.setReadOnly(True)
        self.import_log.setFixedHeight(120)
        self.import_log.setStyleSheet("background-color: #18181b; border: 1px solid #3f3f46; font-size: 11px;")
        layout.addWidget(self.import_log)

        layout.addStretch()
        self._add_category(f"03 // {t('import')}", page)

    def _browse_custom_profile(self):
        d = QFileDialog.getExistingDirectory(self, "Select Profile Directory", str(Path.home()))
        if d:
            self.input_custom_path.setText(d)

    def _import_csv_dialog(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select CSV Passwords File", str(Path.home()), "CSV Files (*.csv)")
        if f:
            count = BrowserImporter.import_from_csv_passwords(Path(f))
            self.import_log.append(f"[SUCCESS] Imported {count} passwords from CSV: {f}")

    def _run_import(self):
        try:
            selected_data = self.combo_browser.currentData()
            if selected_data:
                profile_path = selected_data.path
                btype = selected_data.browser_type
                name = selected_data.name
            else:
                custom_str = self.input_custom_path.text().strip()
                if not custom_str or not Path(custom_str).exists():
                    self.import_log.append("[ERROR] Please select or specify a valid profile directory.")
                    return
                profile_path = Path(custom_str)
                btype = "firefox" if "firefox" in custom_str.lower() else "chromium"
                name = "Custom Profile"

            self.import_log.append(f"[STARTING] Importing from {name} ({profile_path})...")

            if self.chk_imp_bookmarks.isChecked():
                bm_cnt = BrowserImporter.import_bookmarks_firefox(profile_path) if btype == "firefox" else BrowserImporter.import_bookmarks_chromium(profile_path)
                self.import_log.append(f" [OK] Bookmarks imported: {bm_cnt}")

            if self.chk_imp_history.isChecked():
                h_cnt = BrowserImporter.import_history_firefox(profile_path) if btype == "firefox" else BrowserImporter.import_history_chromium(profile_path)
                self.import_log.append(f" [OK] History entries imported: {h_cnt}")

            if self.chk_imp_cookies.isChecked():
                c_cnt = BrowserImporter.import_cookies_firefox(profile_path) if btype == "firefox" else BrowserImporter.import_cookies_chromium(profile_path)
                self.import_log.append(f" [OK] Cookies imported: {c_cnt}")

            if self.chk_imp_passwords.isChecked():
                p_cnt = BrowserImporter.import_passwords_chromium(profile_path)
                self.import_log.append(f" [OK] Password entries imported: {p_cnt}")

            self.import_log.append("[FINISHED] Migration completed successfully!")
        except Exception as e:
            self.import_log.append(f"[ERROR] Import failed: {e}")

    # =========================================================================
    # 4. VAULT (PASSWORDS & COOKIES) - PROTECTED BY SUDO
    # =========================================================================
    def _init_vault_page(self):
        page = QWidget()
        self.vault_main_layout = QVBoxLayout(page)
        self.vault_main_layout.setContentsMargins(12, 12, 12, 12)
        self.vault_main_layout.setSpacing(10)

        lbl_head = QLabel(f"04 // {t('vault').upper()} [PROTECTED]")
        lbl_head.setProperty("class", "sectionHeader")
        self.vault_main_layout.addWidget(lbl_head)

        self.vault_stack = QStackedWidget()
        self.vault_main_layout.addWidget(self.vault_stack, stretch=1)

        # STATE 0: Locked Screen
        locked_widget = QWidget()
        l_layout = QVBoxLayout(locked_widget)
        l_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_layout.setSpacing(12)

        lock_box = QFrame()
        lock_box.setFixedWidth(460)
        lock_box.setStyleSheet("background: #262624; border: 1px solid #3f3f46; padding: 16px;")
        lb_layout = QVBoxLayout(lock_box)
        lb_layout.setSpacing(10)

        acc = getattr(self, "accent", "#a855f7")
        self.vault_title = QLabel(t('vault_locked_title'))
        self.vault_title.setStyleSheet(f"color: {acc}; font-weight: bold; font-size: 13px;")
        desc = QLabel(t('vault_locked_desc'))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")

        lb_layout.addWidget(self.vault_title)
        lb_layout.addWidget(desc)

        lb_layout.addWidget(QLabel(t('sudo_password_label')))
        self.input_sudo_pwd = QLineEdit()
        self.input_sudo_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_sudo_pwd.setPlaceholderText("Password")
        self.input_sudo_pwd.returnPressed.connect(self._verify_sudo)
        lb_layout.addWidget(self.input_sudo_pwd)

        self.vault_error_lbl = QLabel("")
        self.vault_error_lbl.setStyleSheet("color: #ef4444; font-size: 11px; font-weight: bold; border: none; background: transparent; padding: 2px 0px;")
        self.vault_error_lbl.setVisible(False)
        lb_layout.addWidget(self.vault_error_lbl)

        self.btn_unlock = QPushButton(t('unlock_vault').upper())
        self.btn_unlock.setStyleSheet(f"background: {acc}; color: #18181b; font-weight: bold; padding: 6px;")
        self.btn_unlock.clicked.connect(self._verify_sudo)
        lb_layout.addWidget(self.btn_unlock)

        l_layout.addWidget(lock_box)
        self.vault_stack.addWidget(locked_widget)

        # STATE 1: Unlocked Screen
        unlocked_widget = QWidget()
        u_layout = QVBoxLayout(unlocked_widget)
        u_layout.setContentsMargins(0, 0, 0, 0)
        u_layout.setSpacing(8)

        # Unlocked Top Bar
        top_bar = QHBoxLayout()
        lbl_status = QLabel("[UNLOCKED] SUPERUSER SESSION")
        lbl_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        top_bar.addWidget(lbl_status)
        top_bar.addStretch()

        self.btn_view_passwords = QPushButton(t('passwords').upper())
        self.btn_view_passwords.clicked.connect(lambda: self.vault_sub_stack.setCurrentIndex(0))

        self.btn_view_cookies = QPushButton(t('cookies').upper())
        self.btn_view_cookies.clicked.connect(lambda: self.vault_sub_stack.setCurrentIndex(1))

        btn_lock = QPushButton(t('lock_vault').upper())
        btn_lock.setStyleSheet("border-color: #ef4444; color: #ef4444;")
        btn_lock.clicked.connect(self._lock_vault)

        top_bar.addWidget(self.btn_view_passwords)
        top_bar.addWidget(self.btn_view_cookies)
        top_bar.addWidget(btn_lock)
        u_layout.addLayout(top_bar)

        # Vault Sub Stack (Passwords vs Cookies)
        self.vault_sub_stack = QStackedWidget()
        u_layout.addWidget(self.vault_sub_stack, stretch=1)

        # SUB-PAGE 0: Passwords View
        pwd_page = QWidget()
        pp_layout = QVBoxLayout(pwd_page)
        pp_layout.setContentsMargins(0, 4, 0, 0)
        pp_layout.setSpacing(6)

        p_tools = QHBoxLayout()
        self.input_filter_pwd = QLineEdit()
        self.input_filter_pwd.setPlaceholderText("Filter passwords by domain or username...")
        self.input_filter_pwd.textChanged.connect(self._filter_passwords)

        btn_exp_csv = QPushButton(t('export_csv').upper())
        btn_exp_csv.clicked.connect(self._export_passwords_csv)

        btn_exp_json = QPushButton(t('export_json').upper())
        btn_exp_json.clicked.connect(self._export_passwords_json)

        p_tools.addWidget(self.input_filter_pwd, stretch=1)
        p_tools.addWidget(btn_exp_csv)
        p_tools.addWidget(btn_exp_json)
        pp_layout.addLayout(p_tools)

        self.table_passwords = QTableWidget(0, 4)
        self.table_passwords.setHorizontalHeaderLabels([t("domain"), t("username"), t("password"), t("actions")])
        self.table_passwords.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_passwords.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_passwords.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_passwords.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_passwords.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_passwords.setStyleSheet("background: #18181b; border: 1px solid #3f3f46;")
        pp_layout.addWidget(self.table_passwords)

        self.vault_sub_stack.addWidget(pwd_page)

        # SUB-PAGE 1: Cookies View
        cookie_page = QWidget()
        cp_layout = QVBoxLayout(cookie_page)
        cp_layout.setContentsMargins(0, 4, 0, 0)
        cp_layout.setSpacing(6)

        c_tools = QHBoxLayout()
        self.input_filter_cookie = QLineEdit()
        self.input_filter_cookie.setPlaceholderText(t("search_cookies"))
        self.input_filter_cookie.textChanged.connect(self._filter_cookies)

        btn_exp_c_netscape = QPushButton(t('export_netscape').upper())
        btn_exp_c_netscape.clicked.connect(self._export_cookies_netscape)

        btn_exp_c_json = QPushButton(t('export_json').upper())
        btn_exp_c_json.clicked.connect(self._export_cookies_json)

        c_tools.addWidget(self.input_filter_cookie, stretch=1)
        c_tools.addWidget(btn_exp_c_netscape)
        c_tools.addWidget(btn_exp_c_json)
        cp_layout.addLayout(c_tools)

        self.table_cookies = QTableWidget(0, 5)
        self.table_cookies.setHorizontalHeaderLabels([t("domain"), "Name", "Path", "Secure", "Value"])
        self.table_cookies.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_cookies.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_cookies.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_cookies.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_cookies.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table_cookies.setStyleSheet("background: #18181b; border: 1px solid #3f3f46;")
        cp_layout.addWidget(self.table_cookies)

        self.vault_sub_stack.addWidget(cookie_page)
        self.vault_stack.addWidget(unlocked_widget)

        self._add_category(f"04 // {t('vault')}", page)

    def _verify_sudo(self):
        pwd = self.input_sudo_pwd.text()
        if not pwd:
            self.vault_error_lbl.setText("Password cannot be empty.")
            self.vault_error_lbl.setVisible(True)
            return

        try:
            from core.auth import verify_vault_password
            if verify_vault_password(pwd):
                self.vault_unlocked = True
                self.input_sudo_pwd.clear()
                self.vault_error_lbl.setText("")
                self.vault_error_lbl.setVisible(False)
                self.vault_stack.setCurrentIndex(1)
                self._load_vault_data()
            else:
                self.vault_error_lbl.setText(t("wrong_sudo_password"))
                self.vault_error_lbl.setVisible(True)
        except Exception as e:
            self.vault_error_lbl.setText(f"System auth error: {e}")
            self.vault_error_lbl.setVisible(True)

    def _lock_vault(self):
        self.vault_unlocked = False
        self.input_sudo_pwd.clear()
        self.vault_error_lbl.setText("")
        self.vault_error_lbl.setVisible(False)
        self.vault_stack.setCurrentIndex(0)
        self.table_passwords.setRowCount(0)
        self.table_cookies.setRowCount(0)

    def _load_vault_data(self):
        self._load_passwords_table()
        self._load_cookies_table()

    def _load_passwords_table(self):
        self.table_passwords.setRowCount(0)
        if not PASSWORDS_FILE.exists():
            return
        try:
            with open(PASSWORDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.cached_passwords = data
            self._render_passwords(data)
        except Exception as e:
            print(f"Error loading passwords: {e}")

    def _render_passwords(self, items):
        self.table_passwords.setRowCount(0)
        for row, entry in enumerate(items):
            self.table_passwords.insertRow(row)
            url_item = QTableWidgetItem(entry.get("url", ""))
            user_item = QTableWidgetItem(entry.get("username", ""))
            raw_pwd = entry.get("password", "")
            pwd_item = QTableWidgetItem("••••••••" if raw_pwd else "")
            pwd_item.setData(Qt.ItemDataRole.UserRole, raw_pwd)

            self.table_passwords.setItem(row, 0, url_item)
            self.table_passwords.setItem(row, 1, user_item)
            self.table_passwords.setItem(row, 2, pwd_item)

            action_widget = QWidget()
            a_layout = QHBoxLayout(action_widget)
            a_layout.setContentsMargins(2, 2, 2, 2)
            a_layout.setSpacing(4)

            btn_reveal = QPushButton(t("show"))
            btn_reveal.setFixedHeight(22)
            btn_reveal.setStyleSheet("font-size: 10px; font-weight: bold; padding: 1px 6px;")
            btn_reveal.setToolTip("Show/Hide Password")
            btn_reveal.clicked.connect(lambda _, r=row: self._toggle_pwd_reveal(r))

            btn_copy = QPushButton(t("copy"))
            btn_copy.setFixedHeight(22)
            btn_copy.setStyleSheet("font-size: 10px; font-weight: bold; padding: 1px 6px;")
            btn_copy.setToolTip(t("copy_password"))
            btn_copy.clicked.connect(lambda _, p=raw_pwd: self._copy_to_clipboard(p))

            a_layout.addWidget(btn_reveal)
            a_layout.addWidget(btn_copy)
            self.table_passwords.setCellWidget(row, 3, action_widget)

    def _toggle_pwd_reveal(self, row: int):
        item = self.table_passwords.item(row, 2)
        widget = self.table_passwords.cellWidget(row, 3)
        if item:
            real_pwd = item.data(Qt.ItemDataRole.UserRole) or ""
            if item.text() == "••••••••":
                item.setText(real_pwd)
                if widget and widget.layout() and widget.layout().count() > 0:
                    btn = widget.layout().itemAt(0).widget()
                    if btn: btn.setText("HIDE")
            else:
                item.setText("••••••••")
                if widget and widget.layout() and widget.layout().count() > 0:
                    btn = widget.layout().itemAt(0).widget()
                    if btn: btn.setText(t("show"))

    def _filter_passwords(self, text: str):
        q = text.lower()
        filtered = [
            p for p in getattr(self, "cached_passwords", [])
            if q in p.get("url", "").lower() or q in p.get("username", "").lower()
        ]
        self._render_passwords(filtered)

    def _load_cookies_table(self):
        self.table_cookies.setRowCount(0)
        if not COOKIES_FILE.exists():
            return
        try:
            with open(COOKIES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.cached_cookies = data
            self._render_cookies(data)
        except Exception as e:
            print(f"Error loading cookies: {e}")

    def _render_cookies(self, items):
        self.table_cookies.setRowCount(0)
        for row, entry in enumerate(items[:2000]):  # Limit initial render for speed
            self.table_cookies.insertRow(row)
            self.table_cookies.setItem(row, 0, QTableWidgetItem(entry.get("host", "")))
            self.table_cookies.setItem(row, 1, QTableWidgetItem(entry.get("name", "")))
            self.table_cookies.setItem(row, 2, QTableWidgetItem(entry.get("path", "/")))
            self.table_cookies.setItem(row, 3, QTableWidgetItem("Yes" if entry.get("secure") else "No"))
            self.table_cookies.setItem(row, 4, QTableWidgetItem(entry.get("value", "") or entry.get("name", "")))

    def _filter_cookies(self, text: str):
        q = text.lower()
        filtered = [
            c for c in getattr(self, "cached_cookies", [])
            if q in c.get("host", "").lower() or q in c.get("name", "").lower()
        ]
        self._render_cookies(filtered)

    def _copy_to_clipboard(self, val: str):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(val)
        self.status_lbl.setText(t("copied"))

    def _export_passwords_csv(self):
        f, _ = QFileDialog.getSaveFileName(self, t("export_csv"), str(Path.home() / "passwords.csv"), "CSV Files (*.csv)")
        if not f:
            return
        try:
            with open(PASSWORDS_FILE, "r", encoding="utf-8") as jf:
                data = json.load(jf)
            with open(f, "w", newline="", encoding="utf-8") as cf:
                writer = csv.writer(cf)
                writer.writerow(["url", "username", "password"])
                for row in data:
                    writer.writerow([row.get("url", ""), row.get("username", ""), row.get("password", "")])
            self.status_lbl.setText(f"Exported {len(data)} passwords to {f}")
        except Exception as e:
            self.status_lbl.setText(f"Export error: {e}")

    def _export_passwords_json(self):
        f, _ = QFileDialog.getSaveFileName(self, t("export_json"), str(Path.home() / "passwords.json"), "JSON Files (*.json)")
        if not f:
            return
        try:
            with open(PASSWORDS_FILE, "r", encoding="utf-8") as jf:
                data = json.load(jf)
            with open(f, "w", encoding="utf-8") as out:
                json.dump(data, out, indent=2, ensure_ascii=False)
            self.status_lbl.setText(f"Exported passwords JSON to {f}")
        except Exception as e:
            self.status_lbl.setText(f"Export error: {e}")

    def _export_cookies_json(self):
        f, _ = QFileDialog.getSaveFileName(self, t("export_json"), str(Path.home() / "cookies.json"), "JSON Files (*.json)")
        if not f:
            return
        try:
            with open(COOKIES_FILE, "r", encoding="utf-8") as jf:
                data = json.load(jf)
            with open(f, "w", encoding="utf-8") as out:
                json.dump(data, out, indent=2, ensure_ascii=False)
            self.status_lbl.setText(f"Exported cookies JSON to {f}")
        except Exception as e:
            self.status_lbl.setText(f"Export error: {e}")

    def _export_cookies_netscape(self):
        f, _ = QFileDialog.getSaveFileName(self, t("export_netscape"), str(Path.home() / "cookies.txt"), "Text Files (*.txt)")
        if not f:
            return
        try:
            with open(COOKIES_FILE, "r", encoding="utf-8") as jf:
                data = json.load(jf)
            with open(f, "w", encoding="utf-8") as out:
                out.write("# Netscape HTTP Cookie File\n# http://curl.haxx.se/rfc/cookie_spec.html\n# This file was generated by Crux.\n\n")
                for c in data:
                    host = c.get("host", "")
                    include_sub = "TRUE" if host.startswith(".") else "FALSE"
                    path = c.get("path", "/")
                    secure = "TRUE" if c.get("secure") else "FALSE"
                    expires = str(int(c.get("expires", 0) / 1000000) if c.get("expires", 0) > 2000000000 else int(c.get("expires", int(time.time() + 86400 * 30))))
                    name = c.get("name", "")
                    val = c.get("value", "")
                    out.write(f"{host}\t{include_sub}\t{path}\t{secure}\t{expires}\t{name}\t{val}\n")
            self.status_lbl.setText(f"Exported {len(data)} cookies in Netscape format to {f}")
        except Exception as e:
            self.status_lbl.setText(f"Export error: {e}")

    # =========================================================================
    # 5. APPEARANCE PAGE
    # =========================================================================
    def _init_appearance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        lbl_head = QLabel(f"05 // {t('appearance').upper()}")
        lbl_head.setProperty("class", "sectionHeader")
        layout.addWidget(lbl_head)

        # Theme (Dark vs Light)
        layout.addWidget(QLabel(t("color_theme")))
        self.combo_theme = QComboBox()
        self.combo_theme.addItem(t("theme_dark"), "dark")
        self.combo_theme.addItem(t("theme_light"), "light")
        t_idx = self.combo_theme.findData(self.settings.get("theme", "dark"))
        if t_idx >= 0:
            self.combo_theme.setCurrentIndex(t_idx)
        layout.addWidget(self.combo_theme)

        # Website Theme (Separate from UI theme, default light)
        layout.addWidget(QLabel(t("website_theme_label")))
        self.combo_website_theme = QComboBox()
        self.combo_website_theme.addItem(t("website_theme_light"), "light")
        self.combo_website_theme.addItem(t("website_theme_dark"), "dark")
        self.combo_website_theme.addItem(t("website_theme_system"), "system")
        w_idx = self.combo_website_theme.findData(self.settings.get("website_theme", "light"))
        if w_idx >= 0:
            self.combo_website_theme.setCurrentIndex(w_idx)
        layout.addWidget(self.combo_website_theme)

        # Accent Color
        layout.addWidget(QLabel(t("primary_accent")))
        self.combo_accent = QComboBox()
        current_accent = self.settings.get("accent_color", "#a855f7").lower()
        for key, meta in ACCENT_PRESETS.items():
            self.combo_accent.addItem(f"{meta['name']} ({meta['hex']})", meta["hex"])
        
        # Match current accent
        found_accent = False
        for i in range(self.combo_accent.count()):
            if self.combo_accent.itemData(i).lower() == current_accent:
                self.combo_accent.setCurrentIndex(i)
                found_accent = True
                break
        if not found_accent:
            self.combo_accent.addItem(f"Custom ({current_accent})", current_accent)
            self.combo_accent.setCurrentIndex(self.combo_accent.count() - 1)
        layout.addWidget(self.combo_accent)

        # Quick Palette Swatches
        swatches_layout = QHBoxLayout()
        swatches_layout.setSpacing(6)
        for key, meta in ACCENT_PRESETS.items():
            s_btn = QPushButton(meta["name"].split()[0])
            s_btn.setFixedHeight(24)
            s_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {meta['hex']};
                    color: #18181b;
                    font-size: 10px;
                    font-weight: bold;
                    border: 1px solid #3f3f46;
                    border-radius: 2px;
                }}
                QPushButton:hover {{
                    border: 2px solid #ffffff;
                }}
            """)
            s_btn.clicked.connect(lambda _, h=meta["hex"]: self._select_accent_hex(h))
            swatches_layout.addWidget(s_btn)
        layout.addLayout(swatches_layout)

        layout.addWidget(QLabel(t("ui_mode_label")))
        self.combo_ui_mode = QComboBox()
        self.combo_ui_mode.addItem(f"{t('mode_minimal')}", "minimal")
        self.combo_ui_mode.addItem(f"{t('mode_vim')}", "vim")

        curr_mode = self.settings.get("ui_mode", "minimal")
        if curr_mode not in ["minimal", "vim"]:
            curr_mode = "minimal"
        idx = self.combo_ui_mode.findData(curr_mode)
        if idx >= 0:
            self.combo_ui_mode.setCurrentIndex(idx)
        layout.addWidget(self.combo_ui_mode)

        # Tab Orientation within Minimal Mode
        layout.addWidget(QLabel(t("tab_orientation")))
        self.combo_tab_orient = QComboBox()
        self.combo_tab_orient.addItem(t("vertical_tabs"), "vertical")
        self.combo_tab_orient.addItem(t("horizontal_tabs"), "horizontal")
        curr_orient = self.settings.get("tab_orientation", "vertical")
        o_idx = self.combo_tab_orient.findData(curr_orient)
        if o_idx >= 0:
            self.combo_tab_orient.setCurrentIndex(o_idx)
        layout.addWidget(self.combo_tab_orient)

        layout.addWidget(QLabel(t("font_family_label")))
        self.combo_font = QComboBox()
        self.combo_font.addItems([
            "Iosevka Nerd Font",
            "JetBrains Mono",
            "Fira Code",
            "DejaVu Sans Mono",
            "monospace"
        ])
        current_font = self.settings.get("font_family", "Iosevka Nerd Font")
        idx = self.combo_font.findText(current_font)
        if idx >= 0:
            self.combo_font.setCurrentIndex(idx)
        layout.addWidget(self.combo_font)

        layout.addWidget(QLabel(t("font_size_label")))
        self.spin_font_size = QSpinBox()
        self.spin_font_size.setRange(10, 16)
        self.spin_font_size.setValue(self.settings.get("font_size", 13))
        layout.addWidget(self.spin_font_size)

        layout.addWidget(QLabel(t("sidebar_width_label")))
        self.spin_sidebar_width = QSpinBox()
        self.spin_sidebar_width.setRange(180, 360)
        self.spin_sidebar_width.setValue(self.settings.get("sidebar_width", 240))
        layout.addWidget(self.spin_sidebar_width)

        layout.addStretch()
        self._add_category(f"05 // {t('appearance')}", page)

        self.combo_theme.currentIndexChanged.connect(lambda: self._update_dialog_theme_accent())
        self.combo_accent.currentIndexChanged.connect(lambda: self._update_dialog_theme_accent())

    def _select_accent_hex(self, hex_val: str):
        for i in range(self.combo_accent.count()):
            if self.combo_accent.itemData(i).lower() == hex_val.lower():
                self.combo_accent.setCurrentIndex(i)
                self._update_dialog_theme_accent(accent=hex_val)
                break

    def _update_dialog_theme_accent(self, theme: str = None, accent: str = None):
        th = theme or (self.combo_theme.currentData() if hasattr(self, "combo_theme") and self.combo_theme.currentData() else getattr(self, "theme", "dark"))
        acc = accent or (self.combo_accent.currentData() if hasattr(self, "combo_accent") and self.combo_accent.currentData() else getattr(self, "accent", "#a855f7"))
        self.accent = acc
        self.theme = th

        if hasattr(self, "title_lbl"):
            self.title_lbl.setStyleSheet(f"color: {acc}; font-size: 14px; font-weight: bold; font-family: 'Iosevka Nerd Font', monospace;")
        if hasattr(self, "btn_apply"):
            self.btn_apply.setStyleSheet(f"border-color: {acc}; color: {acc}; font-weight: bold; min-width: 140px;")
        if hasattr(self, "btn_do_import"):
            btn_bg = "#ffffff" if th == "light" else "#262624"
            self.btn_do_import.setStyleSheet(f"background-color: {btn_bg}; border-color: {acc}; color: {acc}; font-weight: bold; padding: 6px 12px;")
        if hasattr(self, "vault_title"):
            self.vault_title.setStyleSheet(f"color: {acc}; font-weight: bold; font-size: 13px;")
        if hasattr(self, "btn_unlock"):
            self.btn_unlock.setStyleSheet(f"background: {acc}; color: #18181b; font-weight: bold; padding: 6px;")
        if hasattr(self, "about_lbl_head"):
            self.about_lbl_head.setStyleSheet(f"color: {acc}; font-weight: bold; font-size: 13px;")
        if hasattr(self, "about_ver_lbl"):
            self.about_ver_lbl.setStyleSheet(f"font-size: 12px; color: {acc}; font-weight: bold;")
        if hasattr(self, "about_card"):
            card_bg = "#ffffff" if th == "light" else "#18181b"
            card_border = "#cbd5e1" if th == "light" else "#3f3f46"
            self.about_card.setStyleSheet(f"background: {card_bg}; border: 1px solid {card_border}; padding: 12px;")
        if hasattr(self, "nav_list"):
            nav_bg = "#ffffff" if th == "light" else "#262624"
            nav_border = "#cbd5e1" if th == "light" else "#3f3f46"
            item_color = "#334155" if th == "light" else "#d4d4d8"
            item_hover_bg = "#f1f5f9" if th == "light" else "#2d2d2a"
            item_sel_bg = "#f8fafc" if th == "light" else "#18181b"
            item_border = "#e2e8f0" if th == "light" else "#2b2b29"
            text_bright = "#0f172a" if th == "light" else "#f5f5f0"
            self.nav_list.setStyleSheet(f"""
                QListWidget {{
                    background-color: {nav_bg};
                    border: 1px solid {nav_border};
                    outline: none;
                }}
                QListWidget::item {{
                    color: {item_color};
                    padding: 10px 12px;
                    border-bottom: 1px solid {item_border};
                    font-size: 12px;
                }}
                QListWidget::item:hover {{
                    background-color: {item_hover_bg};
                    color: {text_bright};
                }}
                QListWidget::item:selected {{
                    background-color: {item_sel_bg};
                    color: {text_bright};
                    border-left: 2px solid {acc};
                }}
            """)

    # =========================================================================
    # 6. AI ASSISTANT PAGE
    # =========================================================================
    def _init_ai_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        lbl_head = QLabel(f"06 // {t('ai_assistant').upper()} (GEMINI API)")
        lbl_head.setProperty("class", "sectionHeader")
        layout.addWidget(lbl_head)

        layout.addWidget(QLabel(t("gemini_key_label")))
        self.input_ai_key = QLineEdit(self.settings.get("gemini_api_key", ""))
        self.input_ai_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        layout.addWidget(self.input_ai_key)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel(t("ai_model_label")))
        self.btn_fetch_models = QPushButton(t("fetch_models_btn"))
        self.btn_fetch_models.clicked.connect(self._fetch_models_for_settings)
        model_row.addStretch()
        model_row.addWidget(self.btn_fetch_models)
        layout.addLayout(model_row)

        self.combo_ai_model = QComboBox()
        default_models = [
            ("gemini-flash-lite-latest [LIGHT & FAST]", "gemini-flash-lite-latest"),
            ("gemini-2.5-flash [RECOMMENDED]", "gemini-2.5-flash"),
            ("gemini-3.8-flash-lite [LIGHT & FAST]", "gemini-3.8-flash-lite"),
            ("gemini-2.5-pro [DEEP REASONING]", "gemini-2.5-pro"),
        ]
        for label, mid in default_models:
            self.combo_ai_model.addItem(label, mid)

        curr_model = self.settings.get("ai_model", "gemini-2.5-flash")
        m_idx = self.combo_ai_model.findData(curr_model)
        if m_idx >= 0:
            self.combo_ai_model.setCurrentIndex(m_idx)
        else:
            self.combo_ai_model.addItem(f"{curr_model} [RECOMMENDED]", curr_model)
            self.combo_ai_model.setCurrentIndex(self.combo_ai_model.count() - 1)
        layout.addWidget(self.combo_ai_model)

        layout.addWidget(QLabel(t("ai_persona_label")))
        self.input_ai_persona = QTextEdit()
        self.input_ai_persona.setFixedHeight(70)
        self.input_ai_persona.setText(self.settings.get("ai_persona", "You are an intelligent, engineer-focused AI assistant in Crux."))
        layout.addWidget(self.input_ai_persona)

        layout.addStretch()
        self._add_category(f"06 // {t('ai_assistant')}", page)

    def _fetch_models_for_settings(self):
        key = self.input_ai_key.text().strip()
        if not key:
            self.status_lbl.setText("Please enter an API key first.")
            return
        from sidebar.ai_chat import ModelFetcherWorker
        self.settings_model_fetcher = ModelFetcherWorker(key)
        self.settings_model_fetcher.models_fetched.connect(self._on_settings_models_fetched)
        self.settings_model_fetcher.start()
        self.status_lbl.setText("Fetching models from Gemini API...")

    def _on_settings_models_fetched(self, models):
        self.combo_ai_model.blockSignals(True)
        self.combo_ai_model.clear()
        curr_m = self.settings.get("ai_model", "gemini-2.5-flash")
        selected_idx = 0
        for i, (label, mid) in enumerate(models):
            self.combo_ai_model.addItem(label, mid)
            if mid == curr_m:
                selected_idx = i
        self.combo_ai_model.setCurrentIndex(selected_idx)
        self.combo_ai_model.blockSignals(False)
        self.status_lbl.setText(f"Loaded {len(models)} models from API.")

    # =========================================================================
    # 7. NETWORK & ADVANCED PAGE
    # =========================================================================
    def _init_network_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        lbl_head = QLabel(f"07 // {t('network').upper()}")
        lbl_head.setProperty("class", "sectionHeader")
        layout.addWidget(lbl_head)

        self.chk_gpu = QCheckBox(t("enable_gpu"))
        self.chk_gpu.setChecked(self.settings.get("gpu_accel", True))
        layout.addWidget(self.chk_gpu)

        layout.addWidget(QLabel(t("proxy_server_label")))
        proxy_row = QHBoxLayout()
        self.input_proxy_host = QLineEdit(self.settings.get("proxy_host", ""))
        self.input_proxy_host.setPlaceholderText("e.g. 127.0.0.1")
        self.input_proxy_port = QLineEdit(self.settings.get("proxy_port", ""))
        self.input_proxy_port.setPlaceholderText("Port (e.g. 9050)")
        self.input_proxy_port.setFixedWidth(100)
        proxy_row.addWidget(self.input_proxy_host, stretch=1)
        proxy_row.addWidget(self.input_proxy_port)
        layout.addLayout(proxy_row)

        layout.addStretch()
        self._add_category(f"07 // {t('network')}", page)

    # =========================================================================
    # 8. ABOUT ZEPHYRIUM PAGE
    # =========================================================================
    def _init_about_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        acc = getattr(self, "accent", "#a855f7")
        th = getattr(self, "theme", "dark")
        card_bg = "#ffffff" if th == "light" else "#18181b"
        card_border = "#cbd5e1" if th == "light" else "#3f3f46"
        title_color = "#0f172a" if th == "light" else "#f5f5f0"
        desc_color = "#334155" if th == "light" else "#d4d4d8"

        self.about_lbl_head = QLabel(f"08 // {t('about').upper()}")
        self.about_lbl_head.setProperty("class", "sectionHeader")
        self.about_lbl_head.setStyleSheet(f"color: {acc}; font-weight: bold; font-size: 13px;")
        layout.addWidget(self.about_lbl_head)

        self.about_card = QFrame()
        self.about_card.setStyleSheet(f"background: {card_bg}; border: 1px solid {card_border}; padding: 12px;")
        ac_layout = QVBoxLayout(self.about_card)
        ac_layout.setSpacing(8)

        title_lbl = QLabel("ZEPHYRIUM BROWSER")
        title_lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {title_color};")
        ac_layout.addWidget(title_lbl)

        import platform
        arch_info = platform.machine() or "x86_64"
        os_info = "Windows" if sys.platform == "win32" else "Linux"
        self.about_ver_lbl = QLabel(f"Version {APP_VERSION} ({os_info} {arch_info})")
        self.about_ver_lbl.setStyleSheet(f"font-size: 12px; color: {acc}; font-weight: bold;")
        ac_layout.addWidget(self.about_ver_lbl)

        desc_lbl = QLabel(
            "A fast, keyboard-driven web browser built with PyQt6 and QtWebEngine.\n"
            "Engineered for power users, developers, and privacy advocates."
        )
        desc_lbl.setStyleSheet(f"color: {desc_color}; font-size: 12px;")
        ac_layout.addWidget(desc_lbl)

        layout.addWidget(self.about_card)

        # Technical details and author credentials
        details_frame = QFrame()
        details_frame.setStyleSheet("background: #262624; border: 1px solid #3f3f46; padding: 10px;")
        df_layout = QVBoxLayout(details_frame)
        df_layout.setSpacing(6)

        df_layout.addWidget(QLabel("<b>Engine:</b> Qt 6.x / QtWebEngine (Chromium)"))
        df_layout.addWidget(QLabel("<b>Author:</b> qualbyy"))
        df_layout.addWidget(QLabel("<b>Email:</b> qualbybox@gmail.com"))
        df_layout.addWidget(QLabel("<b>GitHub:</b> <a style='color:#38bdf8;' href='https://github.com/qualbyy'>https://github.com/qualbyy</a>"))
        df_layout.addWidget(QLabel("<b>License:</b> MIT License"))
        layout.addWidget(details_frame)

        # License text box
        lbl_lic = QLabel("License Agreement:")
        lbl_lic.setStyleSheet("color: #71717a; font-size: 11px;")
        layout.addWidget(lbl_lic)

        lic_text = QTextEdit()
        lic_text.setReadOnly(True)
        lic_text.setFixedHeight(90)
        lic_text.setStyleSheet("background: #18181b; border: 1px solid #3f3f46; font-size: 11px; color: #71717a;")
        lic_text.setText(
            "MIT License\n\n"
            "Copyright (c) 2026 qualbyy\n\n"
            "Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files (the \"Software\"), to deal "
            "in the Software without restriction, including without limitation the rights "
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies "
            "of the Software, and to permit persons to whom the Software is furnished to do so, "
            "subject to the following conditions:\n\n"
            "The above copyright notice and this permission notice shall be included in all copies "
            "or substantial portions of the Software."
        )
        layout.addWidget(lic_text)

        layout.addStretch()
        self._add_category(f"08 // {t('about')}", page)

    # =========================================================================
    # SAVE ALL
    # =========================================================================
    def _save_all(self):
        self.settings["homepage"] = self.input_homepage.text().strip()
        if hasattr(self, "input_new_tab_url"):
            self.settings["new_tab_url"] = self.input_new_tab_url.text().strip() or self.input_homepage.text().strip()
        self.settings["download_dir"] = self.input_download_dir.text().strip()
        self.settings["restore_session"] = self.chk_restore_session.isChecked()
        self.settings["adblock_enabled"] = self.chk_adblock.isChecked()
        self.settings["clean_urls"] = self.chk_clean_urls.isChecked()
        self.settings["send_dnt"] = self.chk_dnt.isChecked()
        self.settings["prevent_webrtc_leak"] = self.chk_webrtc.isChecked()
        self.settings["theme"] = self.combo_theme.currentData() or "dark"
        if hasattr(self, "combo_website_theme"):
            self.settings["website_theme"] = self.combo_website_theme.currentData() or "light"
        self.settings["accent_color"] = self.combo_accent.currentData() or "#a855f7"
        self.settings["font_family"] = self.combo_font.currentText()
        self.settings["font_size"] = self.spin_font_size.value()
        self.settings["sidebar_width"] = self.spin_sidebar_width.value()
        self.settings["ui_mode"] = self.combo_ui_mode.currentData() or "minimal"
        self.settings["tab_orientation"] = self.combo_tab_orient.currentData() or "vertical"
        self.settings["gemini_api_key"] = self.input_ai_key.text().strip()
        self.settings["ai_model"] = self.combo_ai_model.currentData() or self.combo_ai_model.currentText()
        self.settings["ai_persona"] = self.input_ai_persona.toPlainText().strip()
        self.settings["gpu_accel"] = self.chk_gpu.isChecked()
        self.settings["proxy_host"] = self.input_proxy_host.text().strip()
        self.settings["proxy_port"] = self.input_proxy_port.text().strip()

        # Language
        selected_lang = self.combo_lang.currentData() or "ru"
        self.settings["language"] = selected_lang
        set_language(selected_lang)

        # Apply theme immediately
        apply_app_theme(QApplication.instance(), self.settings["theme"], self.settings["accent_color"])

        save_settings(self.settings)
        self.settings_saved.emit(self.settings)
        self.status_lbl.setText("Settings saved successfully.")
        self.accept()
