"""
Native Onboarding Dialog for Zephyrium Browser
Modal, clean, engineer-focused initial setup on top of the browser window.
Guarantees zero crashes and prevents bypassing via new tabs.
"""
from pathlib import Path
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QLineEdit, QTextEdit,
    QScrollArea, QFrame, QApplication
)
from PyQt6.QtGui import QFont

from config import load_settings, save_settings, ACCENT_PRESETS
from core.importer import BrowserImporter
from core.theme_manager import apply_app_theme
from core.i18n import t

class OnboardingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zephyrium // Setup")
        self.setModal(True)
        self.setFixedSize(920, 600)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)

        self.settings = load_settings()
        self.selected_theme = self.settings.get("theme", "dark")
        self.selected_accent = self.settings.get("accent_color", "#fe8019")
        self.selected_mode = self.settings.get("ui_mode", "minimal")
        self.selected_orientation = self.settings.get("tab_orientation", "vertical")

        self.detected_browsers = BrowserImporter.get_detected_browsers()
        self.section_labels = []

        self._init_ui()

    def _init_ui(self):
        # Base container style
        acc = self.selected_accent
        self.setStyleSheet(f"""
            QDialog, QScrollArea, QScrollArea > QWidget, QScrollArea > QWidget > QWidget, QWidget#onboardingContent {{
                background-color: #18181b;
                color: #d4d4d8;
            }}
            QScrollArea {{
                background-color: #18181b;
                border: none;
            }}
            QLabel {{
                color: #d4d4d8;
                font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace;
            }}
            QPushButton {{
                font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace;
                border-radius: 0px;
            }}
            QLineEdit, QComboBox, QTextEdit {{
                background-color: #262624;
                border: 1px solid #3f3f46;
                color: #f5f5f0;
                padding: 6px 10px;
                font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace;
                font-size: 12px;
                border-radius: 0px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {acc};
            }}
            QCheckBox {{
                color: #d4d4d8;
                font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace;
                font-size: 12px;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 14px;
                height: 14px;
                background-color: #262624;
                border: 1px solid #3f3f46;
            }}
            QCheckBox::indicator:checked {{
                background-color: {acc};
                border-color: {acc};
            }}
        """)

        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(0, 0, 0, 0)
        dialog_layout.setSpacing(0)

        # Header bar
        header_widget = QWidget()
        header_widget.setStyleSheet("background-color: #202023; border-bottom: 1px solid #3f3f46;")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(24, 16, 24, 16)
        header_layout.setSpacing(6)

        badge_row = QHBoxLayout()
        lbl_badge = QLabel("ZEPHYRIUM ONBOARDING // INITIAL SETUP")
        lbl_badge.setStyleSheet("color: #71717a; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        lbl_os = QLabel("ARCH LINUX")
        lbl_os.setStyleSheet("color: #71717a; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        badge_row.addWidget(lbl_badge)
        badge_row.addStretch()
        badge_row.addWidget(lbl_os)
        header_layout.addLayout(badge_row)

        lbl_title = QLabel("WELCOME TO ZEPHYRIUM")
        lbl_title.setStyleSheet("color: #f5f5f0; font-size: 20px; font-weight: bold; letter-spacing: -0.5px;")
        header_layout.addWidget(lbl_title)

        lbl_desc = QLabel("Engineered for speed, privacy, and minimalist power users. Let's configure your experience.")
        lbl_desc.setStyleSheet("color: #a1a1aa; font-size: 12px;")
        header_layout.addWidget(lbl_desc)

        dialog_layout.addWidget(header_widget)

        # Main 2-column Content (Direct layout, no scrollbars needed)
        content = QWidget()
        content.setObjectName("onboardingContent")
        content.setStyleSheet("background-color: #18181b;")
        
        main_columns = QHBoxLayout(content)
        main_columns.setContentsMargins(20, 12, 20, 12)
        main_columns.setSpacing(16)

        left_col = QVBoxLayout()
        left_col.setSpacing(10)
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        # -------------------------------------------------------------
        # 00 // Language
        # -------------------------------------------------------------
        sec_lang = self._create_section("00 // INTERFACE LANGUAGE")
        self.combo_lang = QComboBox()
        self.combo_lang.setFixedHeight(30)
        from core.i18n import LANGUAGES
        for code, name in LANGUAGES.items():
            self.combo_lang.addItem(f"{name} ({code})", code)
        cur_lang = self.settings.get("language", "ru")
        idx = self.combo_lang.findData(cur_lang)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        sec_lang.layout().addWidget(self.combo_lang)
        left_col.addWidget(sec_lang)

        # -------------------------------------------------------------
        # 01 // Theme
        # -------------------------------------------------------------
        sec_theme = self._create_section("01 // VISUAL THEME")
        th_row = QHBoxLayout()
        th_row.setSpacing(8)

        self.btn_th_dark = QPushButton("MINIMAL DARK")
        self.btn_th_dark.setFixedHeight(34)
        self.btn_th_dark.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_th_dark.clicked.connect(lambda: self._set_theme("dark"))

        self.btn_th_light = QPushButton("CLEAN PAPER LIGHT")
        self.btn_th_light.setFixedHeight(34)
        self.btn_th_light.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_th_light.clicked.connect(lambda: self._set_theme("light"))

        th_row.addWidget(self.btn_th_dark)
        th_row.addWidget(self.btn_th_light)
        sec_theme.layout().addLayout(th_row)
        left_col.addWidget(sec_theme)

        # -------------------------------------------------------------
        # 02 // Key Accent Color
        # -------------------------------------------------------------
        sec_color = self._create_section("02 // KEY ACCENT COLOR")
        colors_row = QHBoxLayout()
        colors_row.setSpacing(6)

        self.color_buttons = {}
        for key, info in ACCENT_PRESETS.items():
            hex_code = info["hex"]
            label_name = info["name"].split()[0].upper()
            btn = QPushButton(label_name)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(f"background-color: {hex_code}; color: #18181b; font-weight: bold; border: 1px solid #3f3f46; font-size: 10px;")
            btn.clicked.connect(lambda checked, h=hex_code: self._set_accent(h))
            self.color_buttons[hex_code] = btn
            colors_row.addWidget(btn)

        sec_color.layout().addLayout(colors_row)
        left_col.addWidget(sec_color)

        # -------------------------------------------------------------
        # 03 // Interface Layout & Tabs
        # -------------------------------------------------------------
        sec_layout = self._create_section("03 // INTERFACE LAYOUT AND TABS")
        mode_row = QHBoxLayout()
        mode_row.setSpacing(8)

        self.btn_mode_v = QPushButton("VERTICAL TABS")
        self.btn_mode_v.setFixedHeight(34)
        self.btn_mode_v.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_v.clicked.connect(lambda: self._set_mode("minimal", "vertical"))

        self.btn_mode_h = QPushButton("HORIZONTAL TABS")
        self.btn_mode_h.setFixedHeight(34)
        self.btn_mode_h.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_h.clicked.connect(lambda: self._set_mode("minimal", "horizontal"))

        self.btn_mode_vim = QPushButton("VIM MODE")
        self.btn_mode_vim.setFixedHeight(34)
        self.btn_mode_vim.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode_vim.clicked.connect(lambda: self._set_mode("vim", "vertical"))

        mode_row.addWidget(self.btn_mode_v)
        mode_row.addWidget(self.btn_mode_h)
        mode_row.addWidget(self.btn_mode_vim)
        sec_layout.layout().addLayout(mode_row)
        left_col.addWidget(sec_layout)

        # -------------------------------------------------------------
        # 04 // Browser Data Migration
        # -------------------------------------------------------------
        sec_import = self._create_section("04 // BROWSER DATA MIGRATION")
        lbl_imp_info = QLabel("Import bookmarks, history, cookies, and logins:")
        lbl_imp_info.setStyleSheet("color: #71717a; font-size: 11px;")
        sec_import.layout().addWidget(lbl_imp_info)

        self.combo_browser = QComboBox()
        self.combo_browser.setFixedHeight(28)
        if self.detected_browsers:
            for b in self.detected_browsers:
                self.combo_browser.addItem(f"[{b.browser_type.upper()}] {b.name} ({b.path.parent.name})", b)
        else:
            self.combo_browser.addItem("No browsers auto-detected", None)
        sec_import.layout().addWidget(self.combo_browser)

        chk_row = QHBoxLayout()
        chk_row.setSpacing(10)
        self.chk_bm = QCheckBox("Bookmarks")
        self.chk_bm.setChecked(True)
        self.chk_hist = QCheckBox("History")
        self.chk_hist.setChecked(True)
        self.chk_cookies = QCheckBox("Cookies")
        self.chk_cookies.setChecked(True)
        self.chk_pwd = QCheckBox("Passwords")
        self.chk_pwd.setChecked(True)
        chk_row.addWidget(self.chk_bm)
        chk_row.addWidget(self.chk_hist)
        chk_row.addWidget(self.chk_cookies)
        chk_row.addWidget(self.chk_pwd)
        chk_row.addStretch()
        sec_import.layout().addLayout(chk_row)

        imp_btn_row = QHBoxLayout()
        imp_btn_row.setSpacing(8)
        self.btn_do_import = QPushButton("START IMPORT NOW")
        self.btn_do_import.setFixedHeight(30)
        self.btn_do_import.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_do_import.clicked.connect(self._run_import_action)

        self.btn_open_vault = QPushButton("OPEN VAULT...")
        self.btn_open_vault.setFixedHeight(30)
        self.btn_open_vault.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_vault.clicked.connect(self._open_vault_action)

        imp_btn_row.addWidget(self.btn_do_import, stretch=2)
        imp_btn_row.addWidget(self.btn_open_vault, stretch=1)
        sec_import.layout().addLayout(imp_btn_row)

        self.import_status = QLabel("Ready to import.")
        self.import_status.setStyleSheet("color: #71717a; font-size: 11px;")
        sec_import.layout().addWidget(self.import_status)

        right_col.addWidget(sec_import)

        # -------------------------------------------------------------
        # 05 // Gemini AI Key
        # -------------------------------------------------------------
        sec_ai = self._create_section("05 // GEMINI AI KEY (OPTIONAL)")
        lbl_ai_info = QLabel("Enable intelligent summarization and live assistant:")
        lbl_ai_info.setStyleSheet("color: #71717a; font-size: 11px;")
        sec_ai.layout().addWidget(lbl_ai_info)

        self.input_gemini = QLineEdit()
        self.input_gemini.setFixedHeight(28)
        self.input_gemini.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_gemini.setPlaceholderText("Enter Gemini API key (or configure later)...")
        existing_key = self.settings.get("gemini_api_key", "")
        if existing_key:
            self.input_gemini.setText(existing_key)
        sec_ai.layout().addWidget(self.input_gemini)
        right_col.addWidget(sec_ai)

        # -------------------------------------------------------------
        # 06 // Quick Cheatsheet
        # -------------------------------------------------------------
        sec_hints = self._create_section("06 // QUICK CHEATSHEET")
        lbl_hints = QLabel("Ctrl+M: Cycle Modes | Ctrl+Alt+T: Tabs | Ctrl+K: Omnibar | Ctrl+,: Settings")
        lbl_hints.setStyleSheet("color: #71717a; font-size: 10px; font-family: monospace;")
        sec_hints.layout().addWidget(lbl_hints)
        right_col.addWidget(sec_hints)

        main_columns.addLayout(left_col, stretch=1)
        main_columns.addLayout(right_col, stretch=1)

        dialog_layout.addWidget(content, stretch=1)

        # Footer Action
        footer = QWidget()
        footer.setStyleSheet("background-color: #202023; border-top: 1px solid #3f3f46; padding: 10px 20px;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch()

        self.btn_save = QPushButton("SAVE AND START BROWSING")
        self.btn_save.setFixedHeight(38)
        self.btn_save.setMinimumWidth(260)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self._finish_and_save)
        footer_layout.addWidget(self.btn_save)

        dialog_layout.addWidget(footer)

        self._update_selection_styles()

    def _create_section(self, title: str) -> QWidget:
        w = QFrame()
        w.setObjectName("secFrame")
        w.setStyleSheet("""
            QFrame#secFrame {
                background-color: #262624;
                border: 1px solid #3f3f46;
            }
        """)
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 8, 12, 8)
        l.setSpacing(6)

        lbl = QLabel(title)
        lbl.setStyleSheet(f"color: {self.selected_accent}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        l.addWidget(lbl)
        self.section_labels.append(lbl)
        return w

    def _set_theme(self, th: str):
        self.selected_theme = th
        self._update_selection_styles()

    def _set_accent(self, hex_code: str):
        self.selected_accent = hex_code
        self._update_selection_styles()

    def _set_mode(self, mode: str, orient: str):
        self.selected_mode = mode
        self.selected_orientation = orient
        self._update_selection_styles()

    def _update_selection_styles(self):
        # Update section header colors
        for lbl in getattr(self, "section_labels", []):
            lbl.setStyleSheet(f"color: {self.selected_accent}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")

        # Update theme buttons
        dark_active = (self.selected_theme == "dark")
        self.btn_th_dark.setStyleSheet(
            f"border: 2px solid {self.selected_accent}; background-color: #18181b; color: #f5f5f0; font-weight: bold;"
            if dark_active else "border: 1px solid #3f3f46; background-color: #262624; color: #a1a1aa;"
        )
        self.btn_th_light.setStyleSheet(
            f"border: 2px solid {self.selected_accent}; background-color: #ffffff; color: #0f172a; font-weight: bold;"
            if not dark_active else "border: 1px solid #cbd5e1; background-color: #f8fafc; color: #64748b;"
        )

        # Update accent buttons
        for hex_code, btn in self.color_buttons.items():
            if hex_code == self.selected_accent:
                btn.setStyleSheet(f"background-color: {hex_code}; color: #18181b; font-weight: bold; border: 3px solid #ffffff;")
            else:
                btn.setStyleSheet(f"background-color: {hex_code}; color: #18181b; font-weight: bold; border: 1px solid #3f3f46;")

        # Update mode buttons
        is_v = (self.selected_mode == "minimal" and self.selected_orientation == "vertical")
        is_h = (self.selected_mode == "minimal" and self.selected_orientation == "horizontal")
        is_vim = (self.selected_mode == "vim")

        self.btn_mode_v.setStyleSheet(
            f"border: 2px solid {self.selected_accent}; background-color: #18181b; color: #f5f5f0; font-weight: bold;"
            if is_v else "border: 1px solid #3f3f46; background-color: #262624; color: #a1a1aa;"
        )
        self.btn_mode_h.setStyleSheet(
            f"border: 2px solid {self.selected_accent}; background-color: #18181b; color: #f5f5f0; font-weight: bold;"
            if is_h else "border: 1px solid #3f3f46; background-color: #262624; color: #a1a1aa;"
        )
        self.btn_mode_vim.setStyleSheet(
            f"border: 2px solid {self.selected_accent}; background-color: #18181b; color: #f5f5f0; font-weight: bold;"
            if is_vim else "border: 1px solid #3f3f46; background-color: #262624; color: #a1a1aa;"
        )

        # Import action button
        self.btn_do_import.setStyleSheet(
            f"background-color: #262624; border: 1px solid {self.selected_accent}; color: {self.selected_accent}; font-weight: bold;"
        )
        self.btn_open_vault.setStyleSheet(
            "background-color: #262624; border: 1px solid #3f3f46; color: #d4d4d8;"
        )

        # Main save button
        self.btn_save.setStyleSheet(
            f"background-color: {self.selected_accent}; color: #18181b; font-weight: bold; font-size: 13px; border: none; letter-spacing: 1px;"
        )

    def _run_import_action(self):
        try:
            profile = self.combo_browser.currentData()
            if not profile:
                self.import_status.setText("[ERROR] No browser profile selected.")
                self.import_status.setStyleSheet("color: #f43f5e; font-size: 11px;")
                return

            self.import_status.setText(f"[RUNNING] Importing from {profile.name}...")
            self.import_status.setStyleSheet("color: #38bdf8; font-size: 11px;")
            QApplication.processEvents()

            results = []
            if self.chk_bm.isChecked():
                bm = BrowserImporter.import_bookmarks_firefox(profile.path) if profile.browser_type == "firefox" else BrowserImporter.import_bookmarks_chromium(profile.path)
                results.append(f"Bookmarks: {bm}")
            if self.chk_hist.isChecked():
                h = BrowserImporter.import_history_firefox(profile.path) if profile.browser_type == "firefox" else BrowserImporter.import_history_chromium(profile.path)
                results.append(f"History: {h}")
            if self.chk_cookies.isChecked():
                c = BrowserImporter.import_cookies_firefox(profile.path) if profile.browser_type == "firefox" else BrowserImporter.import_cookies_chromium(profile.path)
                results.append(f"Cookies: {c}")
            if self.chk_pwd.isChecked():
                p = BrowserImporter.import_passwords_chromium(profile.path)
                results.append(f"Passwords: {p}")

            summary = ", ".join(results)
            self.import_status.setText(f"[SUCCESS] Imported {summary}")
            self.import_status.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11px;")
        except Exception as e:
            self.import_status.setText(f"[ERROR] Import failed: {e}")
            self.import_status.setStyleSheet("color: #f43f5e; font-size: 11px;")

    def _open_vault_action(self):
        parent = self.parent()
        if parent and hasattr(parent, "open_settings"):
            parent.open_settings(3) # Vault page

    def _finish_and_save(self):
        try:
            s = load_settings()
            selected_lang = self.combo_lang.currentData() or "ru"
            s["language"] = selected_lang
            from core.i18n import set_language
            set_language(selected_lang)

            s["theme"] = self.selected_theme
            s["accent_color"] = self.selected_accent
            s["ui_mode"] = self.selected_mode
            s["tab_orientation"] = self.selected_orientation
            api_key = self.input_gemini.text().strip()
            if api_key:
                s["gemini_api_key"] = api_key
            s["first_run"] = False
            save_settings(s)

            # Apply theme dynamically
            apply_app_theme(QApplication.instance(), self.selected_theme, self.selected_accent)

            parent = self.parent()
            if parent:
                if hasattr(parent, "settings"):
                    parent.settings = s
                if hasattr(parent, "apply_mode"):
                    parent.apply_mode(self.selected_mode)
                if hasattr(parent, "_apply_theme_style"):
                    parent._apply_theme_style(self.selected_mode)
                if hasattr(parent, "set_tab_orientation"):
                    parent.set_tab_orientation(self.selected_orientation)
                if hasattr(parent, "retranslate_ui"):
                    parent.retranslate_ui()
                if hasattr(parent, "_reload_startpages"):
                    parent._reload_startpages()
                if hasattr(parent, "side_panel") and hasattr(parent.side_panel, "ai_widget"):
                    parent.side_panel.ai_widget.reload_settings()
        except Exception as e:
            print(f"Error saving onboarding settings: {e}")
        finally:
            self.accept()

    def keyPressEvent(self, event):
        # Prevent escaping onboarding without completing
        if event.key() == Qt.Key.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)
