"""
Main Browser Window for Zinc Browser
Claude Code Minimal Dark aesthetic (Square UI, 0px radius, 1px borders, Zinc/Slate)
Features: 3 Layout Modes (Minimal Dark, Classic Material, Vim Mode),
Collapsible / Compact sidebar, Adblock Whitelist, and Tor Proxy.
"""
from PyQt6.QtCore import Qt, QUrl, QTimer, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QProgressBar, QSplitter, QStatusBar,
    QTabBar, QMenu, QApplication
)
from PyQt6.QtGui import QKeySequence, QShortcut, QAction, QKeyEvent
from PyQt6.QtNetwork import QNetworkProxy
from PyQt6.QtWebEngineCore import QWebEngineProfile

from config import APP_NAME, APP_VERSION, CONTAINERS, load_settings, save_settings
from core.adblock import AdBlockerInterceptor, clean_tracking_parameters
from core.profile_manager import ProfileManager
from core.tab_manager import TabManager
from core.command_palette import CommandPalette
from core.download_manager import DownloadManager
from core.settings_window import SettingsWindow
from sidebar.panel import SidePanel
from utils.icons import Icons
from utils.bookmarks import DataStore
from core.onboarding import OnboardingDialog
from core.password_prompt import PasswordSaveBanner
from core.i18n import t

class BrowserWindow(QMainWindow):
    def __init__(self, initial_mode: str = None):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} [Minimal]")
        self.resize(1280, 800)

        self.settings = load_settings()
        from core.i18n import set_language
        set_language(self.settings.get("language", "ru"))
        self.tab_orientation = self.settings.get("tab_orientation", "vertical")
        self.ui_mode = initial_mode or self.settings.get("ui_mode", "minimal")
        if self.ui_mode in ["classic", "expressive"]:
            self.ui_mode = "minimal"
        self.tor_enabled = False

        # Core subsystems
        self.adblocker = AdBlockerInterceptor(self)
        self.profile_manager = ProfileManager(self.adblocker, self)
        
        # Connect download handler on all profiles
        self.download_manager = DownloadManager(self)
        self.download_manager.hide()
        for prof in self.profile_manager._profiles.values():
            prof.downloadRequested.connect(self.download_manager.handle_download)

        # Root layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.root_layout = QVBoxLayout(central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        # 1. Top Horizontal Tab Bar (For "Classic / Chromium" Mode)
        self._init_horizontal_tab_bar()

        # 2. Top Navigation Toolbar
        self._init_top_bar()

        # 3. Main Workspace Splitter (Tabs + Web / Right Sidebars)
        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.workspace_splitter.setHandleWidth(1)

        # Tab Manager (Vertical Tabs + WebViews)
        self.tab_manager = TabManager(self.profile_manager, self)
        self.tab_manager.active_url_changed.connect(self._on_active_url_changed)
        self.tab_manager.active_title_changed.connect(self._on_active_title_changed)
        self.tab_manager.active_tab_changed.connect(self._on_active_tab_changed)
        self.tab_manager.tabs_updated.connect(self._on_tabs_updated)
        self.tab_manager.all_tabs_closed.connect(self._on_all_tabs_closed)
        self.workspace_splitter.addWidget(self.tab_manager)

        # Right Side Panel (AI Chat & Scratchpad Notes)
        self.side_panel = SidePanel(self)
        self.side_panel.close_requested.connect(self.side_panel.hide)
        self.side_panel.ai_widget.ask_context_page.connect(self._send_page_to_ai)
        self.side_panel.hide()
        self.workspace_splitter.addWidget(self.side_panel)

        # Downloads Drawer (collapsible)
        self.workspace_splitter.addWidget(self.download_manager)

        self.root_layout.addWidget(self.workspace_splitter, stretch=1)

        # 4. Status Bar & Vim Statusline
        self._init_status_bar()

        # 5. Command Palette Dialog
        self.command_palette = CommandPalette(self)
        self.command_palette.command_executed.connect(self._handle_command_action)

        # Floating Password Save Prompt Banner
        self.password_save_banner = PasswordSaveBanner(self)
        self.password_save_banner.hide()

        # 6. Global Shortcuts
        self._init_shortcuts()

        # Create initial default tab: Startpage
        self.tab_manager.create_tab("default", "zephyrium://startpage")

        # If first run, launch modal OnboardingDialog over everything
        if self.settings.get("first_run", True):
            QTimer.singleShot(150, self.show_onboarding)

        # Adblock signal for live counter
        self.adblocker.request_blocked.connect(self._on_ad_blocked)

        # Retranslate all UI labels, buttons, tooltips and placeholders
        self.retranslate_ui()

        # Apply Layout Mode
        self.apply_mode(self.ui_mode)

    def _init_horizontal_tab_bar(self) -> None:
        self.horizontal_tab_container = QWidget()
        self.horizontal_tab_container.setObjectName("horizontalTabContainer")
        self.horizontal_tab_container.setFixedHeight(34)
        h_layout = QHBoxLayout(self.horizontal_tab_container)
        h_layout.setContentsMargins(6, 4, 6, 0)
        h_layout.setSpacing(4)

        self.horizontal_tab_bar = QTabBar()
        self.horizontal_tab_bar.setDrawBase(False)
        self.horizontal_tab_bar.setTabsClosable(False)  # Custom square close button used instead of native circle
        self.horizontal_tab_bar.setMovable(True)
        self.horizontal_tab_bar.currentChanged.connect(self._on_horizontal_tab_selected)
        self.horizontal_tab_bar.tabBarClicked.connect(self._on_horizontal_tab_clicked)

        btn_new_h_tab = QPushButton("+")
        btn_new_h_tab.setFixedSize(26, 26)
        btn_new_h_tab.clicked.connect(lambda: self.tab_manager.create_tab("zephyrium://startpage"))

        self.btn_toggle_vertical = QPushButton("VERTICAL")
        self.btn_toggle_vertical.setFixedHeight(26)
        self.btn_toggle_vertical.setToolTip("Switch to Vertical Tabs")
        self.btn_toggle_vertical.clicked.connect(lambda: self.set_tab_orientation("vertical"))

        h_layout.addWidget(self.horizontal_tab_bar)
        h_layout.addWidget(btn_new_h_tab)
        h_layout.addStretch()
        h_layout.addWidget(self.btn_toggle_vertical)

        self.root_layout.addWidget(self.horizontal_tab_container)
        self.horizontal_tab_container.hide()

    def _init_top_bar(self) -> None:
        self.top_bar = QWidget()
        self.top_bar.setObjectName("topBar")
        self.top_bar.setFixedHeight(38)

        layout = QHBoxLayout(self.top_bar)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(6)

        # Nav Buttons
        self.btn_back = QPushButton(Icons.BACK)
        self.btn_back.setFixedSize(28, 28)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.clicked.connect(self._on_back)

        self.btn_fwd = QPushButton(Icons.FORWARD)
        self.btn_fwd.setFixedSize(28, 28)
        self.btn_fwd.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fwd.clicked.connect(self._on_forward)

        self.btn_reload = QPushButton(Icons.RELOAD)
        self.btn_reload.setFixedSize(28, 28)
        self.btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reload.clicked.connect(self._on_reload)

        layout.addWidget(self.btn_back)
        layout.addWidget(self.btn_fwd)
        layout.addWidget(self.btn_reload)

        # Security Badge
        self.ssl_badge = QPushButton(Icons.LOCK_SECURE)
        self.ssl_badge.setFixedHeight(28)
        self.ssl_badge.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.ssl_badge)

        # URL Bar
        self.url_bar = QLineEdit()
        self.url_bar.setObjectName("urlBar")
        self.url_bar.setPlaceholderText("Enter URL or search... (or Ctrl+K)")
        self.url_bar.setFixedHeight(28)
        self.url_bar.returnPressed.connect(self._on_url_entered)
        self.url_bar.editingFinished.connect(lambda: self.url_bar.setCursorPosition(0))
        layout.addWidget(self.url_bar, stretch=1)

        # Action Buttons
        self.btn_adblock = QPushButton(f"{Icons.ADBLOCK}: 0")
        self.btn_adblock.setFixedHeight(28)
        self.btn_adblock.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_adblock.setToolTip("AdBlocker & Privacy Protection")
        self.btn_adblock.clicked.connect(self._show_adblock_menu)
        layout.addWidget(self.btn_adblock)

        self.btn_split = QPushButton(Icons.SPLIT)
        self.btn_split.setFixedHeight(28)
        self.btn_split.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_split.setToolTip("Toggle Split Screen (Ctrl+\\)")
        self.btn_split.clicked.connect(lambda: self.tab_manager.split_active_tab())
        layout.addWidget(self.btn_split)

        self.btn_history = QPushButton(t("history_title"))
        self.btn_history.setFixedHeight(28)
        self.btn_history.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_history.setToolTip("Browsing History (zephyrium://history)")
        self.btn_history.clicked.connect(self._show_history_menu)
        layout.addWidget(self.btn_history)

        self.btn_downloads = QPushButton(Icons.DOWNLOADS)
        self.btn_downloads.setFixedHeight(28)
        self.btn_downloads.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_downloads.setToolTip("Toggle Downloads (Ctrl+Shift+D)")
        self.btn_downloads.clicked.connect(self._show_downloads_menu)
        layout.addWidget(self.btn_downloads)

        self.btn_ai = QPushButton(Icons.AI)
        self.btn_ai.setObjectName("accentWarmBtn")
        self.btn_ai.setFixedHeight(28)
        self.btn_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai.setToolTip("Toggle Claude AI & Notes (Ctrl+B)")
        self.btn_ai.clicked.connect(self._toggle_sidebar)
        layout.addWidget(self.btn_ai)

        self.btn_tab_orient = QPushButton("TABS: VERT" if self.tab_orientation == "vertical" else "TABS: HORIZ")
        self.btn_tab_orient.setFixedHeight(28)
        self.btn_tab_orient.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_orient.setToolTip("Toggle Tab Orientation: Vertical / Horizontal (Ctrl+Alt+T)")
        self.btn_tab_orient.clicked.connect(lambda: self.set_tab_orientation("horizontal" if self.tab_orientation == "vertical" else "vertical"))
        layout.addWidget(self.btn_tab_orient)

        self.btn_mode = QPushButton("MODE: MINIMAL")
        self.btn_mode.setFixedHeight(28)
        self.btn_mode.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mode.setToolTip("Switch UI Mode: Minimal or Vim (Ctrl+M)")
        self.btn_mode.clicked.connect(self._show_mode_menu)
        layout.addWidget(self.btn_mode)

        self.btn_palette = QPushButton("KEYBINDS")
        self.btn_palette.setFixedHeight(28)
        self.btn_palette.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_palette.setToolTip("Open Command Palette & Keybinds (Ctrl+K)")
        self.btn_palette.clicked.connect(lambda: self.command_palette.show_palette())
        layout.addWidget(self.btn_palette)

        self.btn_settings = QPushButton("SETTINGS")
        self.btn_settings.setFixedHeight(28)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setToolTip("Open Settings & Browser Data Importer (Ctrl+,)")
        self.btn_settings.clicked.connect(self.open_settings)
        layout.addWidget(self.btn_settings)

        self.root_layout.addWidget(self.top_bar)

    def _init_status_bar(self) -> None:
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        # Vim command input in status bar
        acc = self.settings.get("accent_color", "#fe8019")
        th = self.settings.get("theme", "dark")
        vim_bg = "#18181b" if th == "dark" else "#ffffff"
        vim_fg = "#f5f5f0" if th == "dark" else "#0f172a"

        self.vim_prompt_label = QLabel(":")
        self.vim_prompt_label.setStyleSheet(f"color: {acc}; font-weight: bold; font-size: 13px;")
        self.vim_prompt_label.hide()
        self.status_bar.addWidget(self.vim_prompt_label)

        self.vim_input = QLineEdit()
        self.vim_input.setFixedHeight(22)
        self.vim_input.setStyleSheet(f"""
            QLineEdit {{
                background: {vim_bg};
                border: 1px solid {acc};
                color: {vim_fg};
                font-family: monospace;
                font-size: 12px;
                padding: 2px 4px;
            }}
        """)
        self.vim_input.returnPressed.connect(self._on_vim_command_entered)
        self.vim_input.hide()
        self.status_bar.addWidget(self.vim_input, stretch=1)

        self.status_label = QLabel("READY")
        self.status_bar.addWidget(self.status_label, stretch=1)

        self.zoom_label = QLabel("100%")
        self.status_bar.addPermanentWidget(self.zoom_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedSize(100, 12)
        self.progress_bar.hide()
        self.status_bar.addPermanentWidget(self.progress_bar)

        self.status_vim_exit_btn = QPushButton(t("exit_vim"))
        self.status_vim_exit_btn.setObjectName("statusVimExitBtn")
        self.status_vim_exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.status_vim_exit_btn.setFixedHeight(22)
        self.status_vim_exit_btn.clicked.connect(lambda: self.apply_mode("minimal"))
        self.status_vim_exit_btn.hide()
        self.status_bar.addPermanentWidget(self.status_vim_exit_btn)

    def _init_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+K"), self, lambda: self.command_palette.show_palette())
        QShortcut(QKeySequence("Ctrl+L"), self, lambda: (self.url_bar.setFocus(), self.url_bar.selectAll()))
        QShortcut(QKeySequence("Ctrl+T"), self, lambda: self.tab_manager.create_tab("zephyrium://startpage"))
        QShortcut(QKeySequence("Ctrl+W"), self, lambda: self.tab_manager.close_tab(self.tab_manager.active_tab_id))
        QShortcut(QKeySequence("Ctrl+\\"), self, lambda: self.tab_manager.split_active_tab())
        QShortcut(QKeySequence("Ctrl+Alt+T"), self, lambda: self.set_tab_orientation("horizontal" if self.tab_orientation == "vertical" else "vertical"))
        QShortcut(QKeySequence("Ctrl+B"), self, self._toggle_sidebar)
        QShortcut(QKeySequence("Ctrl+Shift+D"), self, self._toggle_downloads)
        QShortcut(QKeySequence("Ctrl+R"), self, self._on_reload)
        QShortcut(QKeySequence("F5"), self, self._on_reload)
        QShortcut(QKeySequence("Ctrl+Shift+R"), self, self._on_hard_reload)
        QShortcut(QKeySequence("Ctrl+="), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl++"), self, self._zoom_in)
        QShortcut(QKeySequence("Ctrl+-"), self, self._zoom_out)
        QShortcut(QKeySequence("Ctrl+0"), self, self._zoom_reset)
        QShortcut(QKeySequence("F11"), self, self._toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+,"), self, self.open_settings)
        QShortcut(QKeySequence("Ctrl+M"), self, self._cycle_modes)
        QShortcut(QKeySequence("Ctrl+["), self, self._toggle_sidebar_compact)

    def set_tab_orientation(self, orient: str) -> None:
        self.tab_orientation = orient
        self.settings["tab_orientation"] = orient
        save_settings(self.settings)
        if hasattr(self, "btn_tab_orient"):
            self.btn_tab_orient.setText(t("tabs_vert_short") if orient == "vertical" else t("tabs_horiz_short"))
        if self.ui_mode == "minimal":
            if orient == "horizontal":
                self.tab_manager.sidebar.hide()
                self.horizontal_tab_container.show()
                self._sync_horizontal_tabs()
            else:
                self.horizontal_tab_container.hide()
                self.tab_manager.sidebar.show()

    def _on_tabs_updated(self) -> None:
        if self.tab_orientation == "horizontal":
            self._sync_horizontal_tabs()

    def apply_mode(self, mode: str) -> None:
        if mode in ["classic", "expressive"]:
            mode = "minimal"
        self.ui_mode = mode
        self.settings["ui_mode"] = mode
        save_settings(self.settings)

        if mode == "vim":
            self.btn_mode.setText(f"{t('mode_label')}: {t('mode_vim')}".upper())
            self.top_bar.hide()
            self.horizontal_tab_container.hide()
            self.tab_manager.sidebar.hide()
            self.status_bar.show()
            self.status_label.setText(t("vim_hint"))
            if hasattr(self, "status_vim_exit_btn"):
                self.status_vim_exit_btn.setText(t("exit_vim"))
                self.status_vim_exit_btn.show()
        else:  # "minimal"
            self.btn_mode.setText(f"{t('mode_label')}: {t('mode_minimal')}".upper())
            if hasattr(self, "status_vim_exit_btn"):
                self.status_vim_exit_btn.hide()
            self.top_bar.show()
            self.status_bar.show()
            self.set_tab_orientation(self.tab_orientation)
            self._apply_theme_style("minimal")
            self.status_label.setText(t("ready"))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "password_save_banner") and self.password_save_banner.isVisible():
            bx = self.width() - self.password_save_banner.width() - 20
            by = (self.top_bar.height() + 8) if (self.ui_mode != "vim" and self.top_bar.isVisible()) else 12
            self.password_save_banner.move(bx, by)

    def show_password_save_prompt(self, url: str, username: str, password: str) -> None:
        if not hasattr(self, "password_save_banner"):
            return
        bx = self.width() - self.password_save_banner.width() - 20
        by = (self.top_bar.height() + 8) if (self.ui_mode != "vim" and self.top_bar.isVisible()) else 12
        self.password_save_banner.move(bx, by)
        self.password_save_banner.set_credentials(url, username, password)
        th = self.settings.get("theme", "dark")
        acc = self.settings.get("accent_color", "#fe8019")
        self.password_save_banner.update_theme(th, acc)
        self.password_save_banner.retranslate_ui()
        self.password_save_banner.show()
        self.password_save_banner.raise_()

    def _apply_theme_style(self, mode: str = "minimal") -> None:
        th = self.settings.get("theme", "dark")
        acc = self.settings.get("accent_color", "#fe8019")
        from core.theme_manager import apply_app_theme, generate_stylesheet
        qss = generate_stylesheet(th, acc)
        apply_app_theme(QApplication.instance(), th, acc)
        self.setStyleSheet(qss)
        self.horizontal_tab_container.setStyleSheet("")
        self.horizontal_tab_bar.setStyleSheet("")
        self.top_bar.setStyleSheet("")
        self.url_bar.setStyleSheet("")
        self.status_bar.setStyleSheet("")
        if hasattr(self, "tab_manager"):
            self.tab_manager.update_theme(th, acc)
        if hasattr(self, "side_panel"):
            self.side_panel.update_theme(th, acc)
        if hasattr(self, "btn_ai"):
            bg_elevated = "#2d2d2a" if th == "dark" else "#f1f5f9"
            self.btn_ai.setStyleSheet(f"""
                QPushButton#accentWarmBtn {{
                    background-color: transparent;
                    border: 1px solid {acc};
                    color: {acc};
                    font-weight: bold;
                }}
                QPushButton#accentWarmBtn:hover {{
                    background-color: {bg_elevated};
                    border: 1px solid {acc};
                    color: {acc};
                }}
                QPushButton#accentWarmBtn:pressed {{
                    background-color: transparent;
                    border: 1px solid {acc};
                    color: {acc};
                }}
            """)
        if hasattr(self, "vim_prompt_label"):
            self.vim_prompt_label.setStyleSheet(f"color: {acc}; font-weight: bold; font-size: 13px;")
        if hasattr(self, "vim_input"):
            vim_bg = "#18181b" if th == "dark" else "#ffffff"
            vim_fg = "#f5f5f0" if th == "dark" else "#0f172a"
            self.vim_input.setStyleSheet(f"""
                QLineEdit {{
                    background: {vim_bg};
                    border: 1px solid {acc};
                    color: {vim_fg};
                    font-family: monospace;
                    font-size: 12px;
                    padding: 2px 4px;
                }}
            """)
        if hasattr(self, "status_vim_exit_btn"):
            btn_bg = "#27272a" if th == "dark" else "#f1f5f9"
            self.status_vim_exit_btn.setStyleSheet(f"""
                QPushButton#statusVimExitBtn {{
                    background-color: {btn_bg};
                    color: {acc};
                    border: 1px solid {acc};
                    font-family: monospace;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 1px 10px;
                    margin: 2px 4px;
                    border-radius: 0px;
                }}
                QPushButton#statusVimExitBtn:hover {{
                    background-color: {acc};
                    color: {btn_bg};
                }}
            """)
        if hasattr(self, "password_save_banner"):
            self.password_save_banner.update_theme(th, acc)
        self._reload_startpages()

    def _reload_startpages(self) -> None:
        th = self.settings.get("theme", "dark")
        acc = self.settings.get("accent_color", "#fe8019")
        lang = self.settings.get("language", "ru")
        from PyQt6.QtGui import QColor
        if hasattr(self, "tab_manager") and hasattr(self.tab_manager, "tabs"):
            for tab_id, tab_data in self.tab_manager.tabs.items():
                if hasattr(tab_data, "split_container"):
                    sc = tab_data.split_container
                    views = getattr(sc, "views", [sc.primary_view] if hasattr(sc, "primary_view") else [])
                    for v in views:
                        if v and hasattr(v, "url"):
                            url_str = v.url().toString()
                            if any(p in url_str for p in ["startpage.html", "settings.html", "history.html", "downloads.html"]):
                                v.page().setBackgroundColor(QColor("#18181b" if th == "dark" else "#f8fafc"))
                                js = f"""
                                (function() {{
                                    if (window.applyTheme) {{ window.applyTheme('{th}', '{acc}'); }}
                                    else {{
                                        document.documentElement.setAttribute('data-theme', '{th}');
                                        document.documentElement.style.setProperty('--accent', '{acc}');
                                    }}
                                    if (window.applyLanguage) {{ window.applyLanguage('{lang}'); }}
                                }})();
                                """
                                v.page().runJavaScript(js)

    def retranslate_ui(self) -> None:
        self.btn_adblock.setText(f"{t('adblock_title')}: {self.adblocker.blocked_count}")
        self.btn_adblock.setToolTip(t("enable_adblock"))
        self.btn_split.setText(t("split_title"))
        self.btn_split.setToolTip(t("split_screen"))
        if hasattr(self, "btn_history"):
            self.btn_history.setText(t("history_title"))
            self.btn_history.setToolTip(t("history_title"))
        self.btn_downloads.setText(t("downloads_title"))
        self.btn_downloads.setToolTip(t("downloads"))
        self.btn_ai.setText(t("ai_title"))
        self.btn_ai.setToolTip(t("ai_assistant_tooltip"))
        self.btn_tab_orient.setText(t("tabs_vert_short") if self.tab_orientation == "vertical" else t("tabs_horiz_short"))
        self.btn_tab_orient.setToolTip(t("tab_orientation"))
        self.btn_mode.setText(f"{t('mode_label')}: {t('mode_' + self.ui_mode)}".upper())
        self.btn_mode.setToolTip(t("ui_mode_label"))
        self.btn_palette.setText(t("keybinds"))
        self.btn_palette.setToolTip(t("keybinds_tooltip"))
        self.btn_settings.setText(t("settings_btn"))
        self.btn_settings.setToolTip(t("settings_tooltip"))
        self.url_bar.setPlaceholderText(t("url_placeholder"))
        if hasattr(self, "btn_toggle_vertical"):
            self.btn_toggle_vertical.setText(t("vertical_btn"))
            self.btn_toggle_vertical.setToolTip(t("switch_to_vertical"))
        if self.ui_mode == "vim":
            self.status_label.setText(t("vim_hint"))
        else:
            self.status_label.setText(t("ready"))
        if hasattr(self, "status_vim_exit_btn"):
            self.status_vim_exit_btn.setText(t("exit_vim"))
        v = self.tab_manager.get_current_view()
        if v:
            url_str = v.url().toString()
            if "startpage.html" in url_str or "welcome.html" in url_str:
                self.ssl_badge.setText(t("internal_page"))
        if hasattr(self, "tab_manager"):
            self.tab_manager.retranslate_ui()
        if hasattr(self, "side_panel"):
            self.side_panel.retranslate_ui()
        if hasattr(self, "password_save_banner"):
            self.password_save_banner.retranslate_ui()

    def _cycle_modes(self) -> None:
        modes = ["minimal", "vim"]
        curr_idx = modes.index(self.ui_mode) if self.ui_mode in modes else 0
        next_mode = modes[(curr_idx + 1) % len(modes)]
        self.apply_mode(next_mode)

    def _show_mode_menu(self) -> None:
        menu = QMenu(self)
        act_min = menu.addAction(t("mode_minimal"))
        act_min.triggered.connect(lambda: self.apply_mode("minimal"))

        act_vim = menu.addAction(t("mode_vim"))
        act_vim.triggered.connect(lambda: self.apply_mode("vim"))

        menu.exec(self.btn_mode.mapToGlobal(self.btn_mode.rect().bottomLeft()))

    def _toggle_sidebar_compact(self) -> None:
        self.tab_manager.sidebar.toggle_compact()

    def tabs_ordered(self):
        res = []
        for row in range(self.tab_manager.sidebar.list_widget.count()):
            item = self.tab_manager.sidebar.list_widget.item(row)
            if item:
                tid = item.data(Qt.ItemDataRole.UserRole)
                if tid in self.tab_manager.tabs:
                    res.append((tid, self.tab_manager.tabs[tid]))
        return res

    def _sync_horizontal_tabs(self) -> None:
        self.horizontal_tab_bar.setUpdatesEnabled(False)
        self.horizontal_tab_bar.blockSignals(True)

        ordered = self.tabs_ordered()
        expected_tids = [tid for tid, _ in ordered]

        # 1. Remove tabs that no longer exist
        i = 0
        while i < self.horizontal_tab_bar.count():
            tid = self.horizontal_tab_bar.tabData(i)
            if tid not in expected_tids:
                self.horizontal_tab_bar.removeTab(i)
            else:
                i += 1

        # 2. Update existing or insert new tabs in correct order
        for idx, (tid, data) in enumerate(ordered):
            title_text = data.title or "New Tab"
            
            if idx < self.horizontal_tab_bar.count() and self.horizontal_tab_bar.tabData(idx) == tid:
                # Update text in place if changed
                if self.horizontal_tab_bar.tabText(idx) != title_text:
                    self.horizontal_tab_bar.setTabText(idx, title_text)
            else:
                # Insert tab at this position
                ins_idx = self.horizontal_tab_bar.insertTab(idx, title_text)
                self.horizontal_tab_bar.setTabData(ins_idx, tid)

                # Custom Crisp Square Close Button
                close_btn = QPushButton("×")
                close_btn.setFixedHeight(24)
                close_btn.setFixedWidth(20)
                close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                close_btn.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        border-radius: 0px;
                        color: #71717a;
                        font-size: 14px;
                        font-weight: bold;
                        padding: 0px;
                        margin: 0px 2px 0px 4px;
                        text-align: center;
                    }
                    QPushButton:hover {
                        background-color: #ef4444;
                        color: #ffffff;
                        border-radius: 0px;
                    }
                """)
                close_btn.clicked.connect(lambda _, t_id=tid: self._close_horizontal_tab(t_id))
                self.horizontal_tab_bar.setTabButton(ins_idx, QTabBar.ButtonPosition.RightSide, close_btn)

            if tid == self.tab_manager.active_tab_id:
                self.horizontal_tab_bar.setCurrentIndex(idx)

        # 3. Clean up any excess tabs
        while self.horizontal_tab_bar.count() > len(ordered):
            self.horizontal_tab_bar.removeTab(self.horizontal_tab_bar.count() - 1)

        self.horizontal_tab_bar.blockSignals(False)
        self.horizontal_tab_bar.setUpdatesEnabled(True)

    def _on_horizontal_tab_selected(self, index: int) -> None:
        if index >= 0:
            tid = self.horizontal_tab_bar.tabData(index)
            if tid is not None and tid in self.tab_manager.tabs:
                self.tab_manager.select_tab(tid)

    def _on_horizontal_tab_clicked(self, index: int) -> None:
        if index >= 0:
            tid = self.horizontal_tab_bar.tabData(index)
            if tid is not None and tid in self.tab_manager.tabs:
                self.tab_manager.select_tab(tid)

    def _close_horizontal_tab(self, tab_id: int) -> None:
        self.tab_manager.close_tab(tab_id)
        self._sync_horizontal_tabs()

    def _on_all_tabs_closed(self) -> None:
        self.close()
        app = QApplication.instance()
        if app:
            app.quit()

    def _show_adblock_menu(self) -> None:
        menu = QMenu(self)
        v = self.tab_manager.get_current_view()
        curr_host = v.url().host() if v else ""

        # Toggle status
        act_toggle = menu.addAction(f"{t('adblock_title')}: {'ON' if self.adblocker.enabled else 'OFF'}")
        act_toggle.triggered.connect(self._toggle_adblock)

        menu.addSeparator()

        # Whitelist domain
        if curr_host:
            is_wl = self.adblocker.is_whitelisted(curr_host)
            if is_wl:
                act_wl = menu.addAction(t("adblock_unwhitelist", domain=curr_host))
                act_wl.triggered.connect(lambda: self.adblocker.remove_whitelist(curr_host))
            else:
                act_wl = menu.addAction(t("adblock_whitelist", domain=curr_host))
                act_wl.triggered.connect(lambda: self.adblocker.add_whitelist(curr_host))

        # Clean URL
        act_clean = menu.addAction(t("clean_url"))
        act_clean.triggered.connect(self._clean_active_url)

        # Tor Proxy
        act_tor = menu.addAction(t("tor_proxy", status='ON' if self.tor_enabled else 'OFF'))
        act_tor.triggered.connect(self._toggle_tor_proxy)

        menu.addSeparator()
        act_settings = menu.addAction(t("adblock_settings_tab"))
        act_settings.triggered.connect(lambda: self.tab_manager.create_tab("default", "zephyrium://settings?tab=adblock"))

        menu.exec(self.btn_adblock.mapToGlobal(self.btn_adblock.rect().bottomLeft()))

    def _show_history_menu(self) -> None:
        menu = QMenu(self)
        from utils.bookmarks import DataStore
        history_items = DataStore.load_history()

        recent = history_items[:10]
        if recent:
            for item in recent:
                title = item.get("title", "")
                url = item.get("url", "")
                display = (title[:36] + "...") if len(title) > 36 else (title or url)
                act = menu.addAction(f"{display} ({url[:28]}...)")
                act.triggered.connect(lambda checked, u=url: self._navigate_active_tab(u))
        else:
            act_none = menu.addAction(t("no_history"))
            act_none.setEnabled(False)

        menu.addSeparator()

        act_full = menu.addAction(t("open_full_history"))
        act_full.triggered.connect(lambda: self.tab_manager.create_tab("default", "zephyrium://history"))

        act_clear = menu.addAction(t("clear_history"))
        act_clear.triggered.connect(self._clear_history_action)

        act_settings = menu.addAction(t("history_settings"))
        act_settings.triggered.connect(lambda: self.tab_manager.create_tab("default", "zephyrium://settings?tab=general"))

        menu.exec(self.btn_history.mapToGlobal(self.btn_history.rect().bottomLeft()))

    def _show_downloads_menu(self) -> None:
        menu = QMenu(self)
        from utils.bookmarks import DataStore
        downloads = DataStore.load_downloads()

        recent = downloads[:8]
        if recent:
            for item in recent:
                fname = item.get("filename", "File")
                fpath = item.get("path", "")
                display = (fname[:32] + "...") if len(fname) > 32 else fname
                act = menu.addAction(f"[FILE] {display}")
                act.triggered.connect(lambda checked, p=fpath: self._open_downloaded_file(p))
        else:
            act_none = menu.addAction(t("no_downloads"))
            act_none.setEnabled(False)

        menu.addSeparator()

        act_all = menu.addAction(t("open_all_downloads"))
        act_all.triggered.connect(lambda: self.tab_manager.create_tab("default", "zephyrium://downloads"))

        act_folder = menu.addAction(t("open_downloads_folder"))
        act_folder.triggered.connect(self._open_downloads_folder)

        act_clear = menu.addAction(t("clear_downloads"))
        act_clear.triggered.connect(self._clear_downloads_action)

        act_settings = menu.addAction(t("downloads_settings"))
        act_settings.triggered.connect(lambda: self.tab_manager.create_tab("default", "zephyrium://settings?tab=downloads"))

        menu.exec(self.btn_downloads.mapToGlobal(self.btn_downloads.rect().bottomLeft()))

    def _navigate_active_tab(self, url: str) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            v.navigate(url)

    def _clear_history_action(self) -> None:
        from utils.bookmarks import DataStore
        DataStore.clear_history()
        self.status_label.setText("Browsing history cleared.")

    def _clear_downloads_action(self) -> None:
        from utils.bookmarks import DataStore
        DataStore.clear_downloads()
        self.status_label.setText("Downloads list cleared.")

    def _open_downloads_folder(self) -> None:
        from PyQt6.QtGui import QDesktopServices
        from pathlib import Path
        ddir = self.settings.get("download_dir", str(Path.home() / "Downloads"))
        QDesktopServices.openUrl(QUrl.fromLocalFile(ddir))

    def _open_downloaded_file(self, path: str) -> None:
        import os, subprocess
        if path and os.path.exists(path):
            subprocess.Popen(["xdg-open", path])

    def _clean_active_url(self) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            clean = clean_tracking_parameters(v.url().toString())
            v.load(QUrl(clean))
            self.status_label.setText("Tracking tags cleaned from URL.")

    def _toggle_tor_proxy(self) -> None:
        if not self.tor_enabled:
            proxy = QNetworkProxy(QNetworkProxy.ProxyType.Socks5Proxy, "127.0.0.1", 9050)
            QNetworkProxy.setApplicationProxy(proxy)
            self.tor_enabled = True
            self.status_label.setText("TOR PROXY ACTIVE [127.0.0.1:9050]")
        else:
            QNetworkProxy.setApplicationProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
            self.tor_enabled = False
            self.status_label.setText("TOR PROXY DISABLED [Direct]")

    def _on_back(self) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            v.back()

    def _on_forward(self) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            v.forward()

    def _on_reload(self) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            v.reload()

    def _on_hard_reload(self) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            from PyQt6.QtWebEngineCore import QWebEnginePage
            v.triggerPageAction(QWebEnginePage.WebAction.ReloadAndBypassCache)

    def _on_url_entered(self) -> None:
        text = self.url_bar.text().strip()
        if text in ["zephyrium://settings", "zinc://settings", "about:settings", "about:preferences"]:
            self.open_settings()
            return
        if text in ["zephyrium://about", "zinc://about"]:
            self.open_settings("about")
            return
        if text in ["zephyrium://welcome", "zinc://welcome"]:
            self.show_onboarding()
            return
        if text in ["zephyrium://vault", "zinc://vault"]:
            self.open_settings("vault")
            return
        if text in ["zephyrium://history", "zinc://history", "about:history"]:
            self.tab_manager.create_tab("default", "zephyrium://history")
            return
        if text in ["zephyrium://downloads", "zinc://downloads", "about:downloads"]:
            self.tab_manager.create_tab("default", "zephyrium://downloads")
            return
        v = self.tab_manager.get_current_view()
        if v:
            v.navigate(text)

    def _toggle_sidebar(self) -> None:
        if self.side_panel.isVisible():
            self.side_panel.hide()
        else:
            self.side_panel.show()
            self.side_panel.switch_tab(0)

    def _toggle_downloads(self) -> None:
        if self.download_manager.isVisible():
            self.download_manager.hide()
        else:
            self.download_manager.show()

    def _toggle_adblock(self) -> None:
        enabled = self.adblocker.toggle()
        state_str = "ON" if enabled else "OFF"
        self.btn_adblock.setText(f"{t('adblock_title')}: {self.adblocker.blocked_count} [{state_str}]")
        self.status_label.setText(f"{t('adblock_title')}: {state_str}")

    def _on_ad_blocked(self, url: str) -> None:
        self.btn_adblock.setText(f"{t('adblock_title')}: {self.adblocker.blocked_count}")

    def _zoom_in(self) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            z = v.zoom_in()
            self.zoom_label.setText(f"{int(z * 100)}%")

    def _zoom_out(self) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            z = v.zoom_out()
            self.zoom_label.setText(f"{int(z * 100)}%")

    def _zoom_reset(self) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            z = v.zoom_reset()
            self.zoom_label.setText(f"{int(z * 100)}%")

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _on_active_url_changed(self, url: QUrl) -> None:
        url_str = url.toString()
        if "welcome.html" in url_str:
            self.url_bar.setText("zephyrium://welcome")
            self.ssl_badge.setText("INTERNAL")
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        elif "startpage.html" in url_str:
            self.url_bar.setText("zephyrium://startpage")
            self.ssl_badge.setText("INTERNAL")
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        elif "settings.html" in url_str:
            self.url_bar.setText("zephyrium://settings")
            self.ssl_badge.setText("INTERNAL")
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        elif "history.html" in url_str:
            self.url_bar.setText("zephyrium://history")
            self.ssl_badge.setText("INTERNAL")
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        elif "downloads.html" in url_str:
            self.url_bar.setText("zephyrium://downloads")
            self.ssl_badge.setText("INTERNAL")
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        else:
            self.url_bar.setText(url_str)
            if url.scheme() == "https":
                self.ssl_badge.setText(Icons.LOCK_SECURE)
                self.ssl_badge.setStyleSheet("color: #10b981; font-weight: bold;")
            else:
                self.ssl_badge.setText(Icons.LOCK_INSECURE)
                self.ssl_badge.setStyleSheet("color: #ef4444; font-weight: bold;")
            v = self.tab_manager.get_current_view()
            if v:
                DataStore.add_history(v.title(), url_str)

        # Ensure start of URL is always visible
        self.url_bar.setCursorPosition(0)

        if self.ui_mode == "vim":
            self.status_label.setText(f"[VIM] {url_str}")

    def _on_active_title_changed(self, title: str) -> None:
        clean_title = f"{title} — {APP_NAME}" if title else APP_NAME
        self.setWindowTitle(clean_title)
        if self.tab_orientation == "horizontal":
            self._sync_horizontal_tabs()

    def _on_active_tab_changed(self, split_container) -> None:
        view = split_container.get_active_view()
        view.loadProgress.connect(self._on_load_progress)
        view.status_message.connect(self.status_label.setText)
        view.ask_ai_selection.connect(self._on_ai_selection_requested)

        # Sync active URL in omnibar and ensure beginning of URL is visible
        cur_u = view.url().toString()
        if "startpage.html" in cur_u:
            self.url_bar.setText("zephyrium://startpage")
        elif "welcome.html" in cur_u:
            self.url_bar.setText("zephyrium://welcome")
        elif "settings.html" in cur_u:
            self.url_bar.setText("zephyrium://settings")
        elif "history.html" in cur_u:
            self.url_bar.setText("zephyrium://history")
        elif "downloads.html" in cur_u:
            self.url_bar.setText("zephyrium://downloads")
        elif cur_u:
            self.url_bar.setText(cur_u)
        self.url_bar.setCursorPosition(0)

        self.zoom_label.setText(f"{int(view.get_zoom() * 100)}%")

        if self.tab_orientation == "horizontal":
            self._sync_horizontal_tabs()

    def _on_ai_selection_requested(self, selected_text: str) -> None:
        self.side_panel.show()
        self.side_panel.switch_tab(0)
        self.side_panel.ai_widget._append_user(f"Explain selection:\n{selected_text}")
        self.side_panel.ai_widget._process_ai_query(f"Explain and summarize this selected text:\n\n{selected_text}")

    def _on_load_progress(self, progress: int) -> None:
        if progress < 100:
            self.progress_bar.show()
            self.progress_bar.setValue(progress)
            self.status_label.setText(t("loading_status", progress=progress))
        else:
            self.progress_bar.hide()
            self.status_label.setText(t("ready") if self.ui_mode != "vim" else f"[VIM] {self.url_bar.text()}")

    def _send_page_to_ai(self) -> None:
        v = self.tab_manager.get_current_view()
        if not v:
            return
        title = v.title()
        url = v.url().toString()
        v.page().runJavaScript(
            "document.body.innerText.substring(0, 6000);",
            lambda text: self.side_panel.ai_widget.receive_page_summary(title, url, text or "")
        )

    def _handle_command_action(self, action: str, param: str) -> None:
        v = self.tab_manager.get_current_view()
        if action == "navigate" or action in ["o", "open"]:
            target = param if param else "zephyrium://startpage"
            if v:
                v.navigate(target)
        elif action in ["t", "tabnew"]:
            self.tab_manager.create_tab(param or "zephyrium://startpage")
        elif action in ["q", "close"]:
            self.tab_manager.close_tab(self.tab_manager.active_tab_id)
        elif action == "split":
            self.tab_manager.split_active_tab()
        elif action == "vsplit":
            sc = self.tab_manager.get_current_split_container()
            if sc:
                sc.toggle_orientation()
        elif action == "adblock":
            self._toggle_adblock()
        elif action == "ai":
            self._toggle_sidebar()
            self.side_panel.switch_tab(0)
        elif action == "notes":
            self._toggle_sidebar()
            self.side_panel.switch_tab(1)
        elif action == "downloads":
            self._toggle_downloads()
        elif action == "mode":
            if param in ["minimal", "vim"]:
                self.apply_mode(param)
        elif action.startswith("zoom"):
            sub = param or action.split(":")[-1]
            if sub == "in":
                self._zoom_in()
            elif sub == "out":
                self._zoom_out()
            else:
                self._zoom_reset()
        elif action in ["settings", "preferences", "config"]:
            self.open_settings()
        elif action == "quit":
            self.close()

    def show_onboarding(self) -> None:
        dlg = OnboardingDialog(self)
        dlg.exec()

    def open_settings(self, tab: str = "") -> None:
        target_url = "zephyrium://settings"
        if tab:
            target_url += f"?tab={tab}"
        if hasattr(self, "tab_manager") and hasattr(self.tab_manager, "tabs"):
            for tab_id, tab_data in self.tab_manager.tabs.items():
                sc = tab_data.split_container if hasattr(tab_data, "split_container") else tab_data
                v = sc.get_active_view() if hasattr(sc, "get_active_view") else None
                if v and "settings.html" in v.url().toString():
                    self.tab_manager.switch_tab(tab_id)
                    if tab:
                        v.navigate(target_url)
                    return
            self.tab_manager.create_tab("default", target_url)

    def _on_settings_saved(self, settings: dict) -> None:
        self.settings = settings
        if "language" in settings:
            from core.i18n import set_language
            set_language(settings["language"])
        self.retranslate_ui()
        from core.theme_manager import apply_app_theme
        apply_app_theme(QApplication.instance(), settings.get("theme", "dark"), settings.get("accent_color", "#fe8019"))
        self._apply_theme_style(self.ui_mode)
        self._reload_startpages()
        if "tab_orientation" in settings and settings["tab_orientation"] != self.tab_orientation:
            self.set_tab_orientation(settings["tab_orientation"])
        if "ui_mode" in settings and settings["ui_mode"] != self.ui_mode:
            self.apply_mode(settings["ui_mode"])
        if "adblock_enabled" in settings:
            if settings["adblock_enabled"] != self.adblocker.enabled:
                self._toggle_adblock()
        if "sidebar_width" in settings:
            self.tab_manager.sidebar.setFixedWidth(settings["sidebar_width"])
        if hasattr(self, "side_panel") and hasattr(self.side_panel, "ai_widget"):
            self.side_panel.ai_widget.reload_settings()
        self.status_label.setText(t("settings_saved_msg"))

    # --- VIM MODE SUPPORT ---
    def keyPressEvent(self, event: QKeyEvent):
        if self.ui_mode == "vim":
            if self.vim_input.isVisible():
                if event.key() == Qt.Key.Key_Escape:
                    self._close_vim_prompt()
                    return
            else:
                if event.key() == Qt.Key.Key_Escape:
                    self.apply_mode("minimal")
                    return
                key_text = event.text()
                if key_text == ":":
                    self._open_vim_prompt(":")
                    return
                elif key_text == "o":
                    self._open_vim_prompt(":open ")
                    return
                elif key_text == "t":
                    self._open_vim_prompt(":tabnew ")
                    return
                elif key_text in ["d", "x"]:
                    self.tab_manager.close_tab(self.tab_manager.active_tab_id)
                    return
                elif key_text == "r":
                    self._on_reload()
                    return
                elif key_text == "R":
                    self._on_hard_reload()
                    return
                elif key_text == "J":
                    self._vim_next_tab()
                    return
                elif key_text == "K":
                    self._vim_prev_tab()
                    return
                elif key_text == "H":
                    self._on_back()
                    return
                elif key_text == "L":
                    self._on_forward()
                    return
                elif key_text == "y":
                    v = self.tab_manager.get_current_view()
                    if v:
                        QApplication.clipboard().setText(v.url().toString())
                        self.status_label.setText(f"[VIM] Copied URL to clipboard")
                    return

        super().keyPressEvent(event)

    def _open_vim_prompt(self, prefix: str = ":") -> None:
        self.status_label.hide()
        self.vim_prompt_label.show()
        self.vim_input.show()
        self.vim_input.setText(prefix)
        self.vim_input.setFocus()

    def _close_vim_prompt(self) -> None:
        self.vim_input.hide()
        self.vim_prompt_label.hide()
        self.status_label.show()
        v = self.tab_manager.get_current_view()
        if v:
            v.setFocus()

    def _on_vim_command_entered(self) -> None:
        cmd_text = self.vim_input.text().strip()
        self._close_vim_prompt()
        if not cmd_text:
            return

        if cmd_text.startswith(":"):
            cmd_text = cmd_text[1:].strip()

        parts = cmd_text.split(" ", 1)
        action = parts[0]
        param = parts[1] if len(parts) > 1 else ""

        if action in ["o", "open"]:
            self._handle_command_action("open", param)
        elif action in ["t", "tabnew"]:
            self._handle_command_action("tabnew", param)
        elif action in ["q", "close", "bdelete"]:
            self._handle_command_action("close", "")
        elif action in ["b", "buffer"]:
            try:
                idx = int(param) - 1
                row_items = self.tabs_ordered()
                if 0 <= idx < len(row_items):
                    self.tab_manager.select_tab(row_items[idx][0])
            except Exception:
                pass
        elif action == "mode":
            if param in ["minimal", "expressive", "classic", "vim"]:
                self.apply_mode("expressive" if param == "classic" else param)
        elif action == "settings":
            self.open_settings()
        elif action == "help":
            self.command_palette.show_palette(":help")
        else:
            self._handle_command_action("open", cmd_text)

    def _vim_next_tab(self) -> None:
        rows = self.tabs_ordered()
        if len(rows) > 1:
            curr_idx = next((i for i, (tid, _) in enumerate(rows) if tid == self.tab_manager.active_tab_id), 0)
            next_idx = (curr_idx + 1) % len(rows)
            self.tab_manager.select_tab(rows[next_idx][0])

    def _vim_prev_tab(self) -> None:
        rows = self.tabs_ordered()
        if len(rows) > 1:
            curr_idx = next((i for i, (tid, _) in enumerate(rows) if tid == self.tab_manager.active_tab_id), 0)
            prev_idx = (curr_idx - 1) % len(rows)
            self.tab_manager.select_tab(rows[prev_idx][0])
