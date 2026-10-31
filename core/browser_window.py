"""
Main Browser Window for Zinc Browser
Claude Code Minimal Dark aesthetic (Square UI, 0px radius, 1px borders, Zinc/Slate)
Features: 3 Layout Modes (Minimal Dark, Classic Material, Vim Mode),
Collapsible / Compact sidebar, Adblock Whitelist, and Tor Proxy.
"""
from PyQt6.QtCore import Qt, QUrl, QTimer, QSize, QStringListModel, QPoint
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QProgressBar, QSplitter, QStatusBar,
    QTabBar, QMenu, QApplication, QCompleter, QComboBox, QSpinBox
)
from PyQt6.QtGui import QKeySequence, QShortcut, QAction, QKeyEvent, QCursor
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
from core.find_bar import FindInPageBar
from core.i18n import t

class BrowserWindow(QMainWindow):
    def __init__(self, initial_mode: str = None, is_incognito: bool = False):
        super().__init__()
        self.is_incognito = is_incognito
        title_mode = "[INCOGNITO]" if is_incognito else "[Minimal]"
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} {title_mode}")
        self.resize(1280, 800)

        self.settings = load_settings()
        from core.i18n import set_language
        set_language(self.settings.get("language", "ru"))
        self.tab_orientation = self.settings.get("tab_orientation", "vertical")
        self.ui_mode = initial_mode or self.settings.get("ui_mode", "minimal")
        if self.ui_mode in ["classic", "expressive"]:
            self.ui_mode = "minimal"
        self.tor_enabled = False
        self.is_fullscreen_active = False
        self._was_maximized_before_fullscreen = False
        self.is_mobile_mode = False

        # Core subsystems
        self.adblocker = AdBlockerInterceptor(self)
        self.profile_manager = ProfileManager(self.adblocker, self, is_incognito=self.is_incognito)
        
        # Connect download handler on all profiles
        self.download_manager = DownloadManager(self)
        self.download_manager.hide()
        for prof in self.profile_manager._profiles.values():
            prof.downloadRequested.connect(self._on_download_requested)

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

        # 2.5 Responsive Viewport Bar
        self._init_viewport_bar()
        self.root_layout.addWidget(self.viewport_bar)

        # 3. Main Workspace & DevTools Vertical Splitter
        self.main_vertical_splitter = QSplitter(Qt.Orientation.Vertical, self)
        self.main_vertical_splitter.setHandleWidth(2)
        self.main_vertical_splitter.addWidget(self.workspace_splitter)

        # 3.5 Embedded Chromium DevTools Dock
        self._init_devtools_dock()
        self.main_vertical_splitter.addWidget(self.devtools_dock)
        self.main_vertical_splitter.setStretchFactor(0, 1)
        self.main_vertical_splitter.setStretchFactor(1, 0)

        self.root_layout.addWidget(self.main_vertical_splitter, stretch=1)

        # Find in Page Floating Bar
        self.find_bar = FindInPageBar(self)
        self.find_bar.find_next_requested.connect(lambda q: self._on_find_in_page(q, forward=True))
        self.find_bar.find_prev_requested.connect(lambda q: self._on_find_in_page(q, forward=False))
        self.find_bar.close_requested.connect(self._on_find_bar_closed)
        self.find_bar.hide()
        self.root_layout.addWidget(self.find_bar)

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

        # Create initial tabs: restore session if configured and not incognito, else default tab
        restored = False
        if not self.is_incognito and self.settings.get("restore_session", False):
            import json
            from config import CONFIG_DIR
            sess_file = CONFIG_DIR / "session.json"
            if sess_file.exists():
                try:
                    with open(sess_file, "r", encoding="utf-8") as f:
                        saved_tabs = json.load(f)
                    if isinstance(saved_tabs, list) and saved_tabs:
                        for entry in saved_tabs:
                            if isinstance(entry, dict):
                                u = entry.get("url", "")
                                cid = entry.get("container_id", "default")
                                is_pin = entry.get("is_pinned", False)
                            else:
                                u = str(entry)
                                cid = "default"
                                is_pin = False
                            if u and not u.startswith("about:blank") and not u.startswith("data:"):
                                tid = self.tab_manager.create_tab(url=u, container_id=cid)
                                if is_pin and tid:
                                    self.tab_manager.toggle_pin_tab(tid)
                        restored = True
                except Exception as e:
                    print(f"[Session Restore Error] {e}")

        if not restored:
            initial_url = self.settings.get("new_tab_url", self.settings.get("homepage", "crux://startpage"))
            init_cid = "incognito" if self.is_incognito else "default"
            self.tab_manager.create_tab(url=initial_url, container_id=init_cid)

        # If first run, launch modal OnboardingDialog over everything
        if self.settings.get("first_run", True) and not self.is_incognito:
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
        self.horizontal_tab_bar.tabMoved.connect(self._on_horizontal_tab_moved)
        self.horizontal_tab_bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.horizontal_tab_bar.customContextMenuRequested.connect(self._show_horizontal_tab_context_menu)

        btn_new_h_tab = QPushButton("+")
        btn_new_h_tab.setFixedSize(26, 26)
        btn_new_h_tab.clicked.connect(lambda: self.tab_manager.create_tab(self.settings.get("new_tab_url", "crux://startpage")))

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
        self.btn_back.setEnabled(False)

        self.btn_fwd = QPushButton(Icons.FORWARD)
        self.btn_fwd.setFixedSize(28, 28)
        self.btn_fwd.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_fwd.clicked.connect(self._on_forward)
        self.btn_fwd.setEnabled(False)

        self.btn_reload = QPushButton(Icons.RELOAD)
        self.btn_reload.setFixedSize(28, 28)
        self.btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_reload.clicked.connect(self._on_reload)

        layout.addWidget(self.btn_back)
        layout.addWidget(self.btn_fwd)
        layout.addWidget(self.btn_reload)

        # Security Badge (Clickable SSL / Info Popup)
        self.ssl_badge = QPushButton(Icons.LOCK_SECURE)
        self.ssl_badge.setFixedHeight(28)
        self.ssl_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.ssl_badge.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")
        self.ssl_badge.clicked.connect(self._show_security_info)
        layout.addWidget(self.ssl_badge)

        # URL Bar with Smart Auto-Complete
        self.url_bar = QLineEdit()
        self.url_bar.setObjectName("urlBar")
        self.url_bar.setPlaceholderText("Enter URL or search... (or Ctrl+K)")
        self.url_bar.setFixedHeight(28)
        self.url_bar.setMinimumWidth(180)
        self.url_bar.returnPressed.connect(self._on_url_entered)
        layout.addWidget(self.url_bar, stretch=1)
        self._init_url_completer()

        # Action Buttons (Retired from top bar; parented to hidden container to prevent tiling WM window spawning)
        self._retired_btn_container = QWidget(self)
        self._retired_btn_container.hide()

        self.btn_reader = QPushButton(Icons.READER, self._retired_btn_container)
        self.btn_reader.clicked.connect(self._on_reader_mode_clicked)

        self.btn_pip = QPushButton(Icons.PIP, self._retired_btn_container)
        self.btn_pip.clicked.connect(self._on_pip_clicked)

        self.btn_adblock = QPushButton(f"{Icons.ADBLOCK}: 0", self._retired_btn_container)
        self.btn_adblock.clicked.connect(self._show_adblock_menu)

        self.btn_split = QPushButton(Icons.SPLIT, self._retired_btn_container)
        self.btn_split.clicked.connect(lambda: self.tab_manager.split_active_tab())

        self.btn_history = QPushButton(t("history_title"), self._retired_btn_container)
        self.btn_history.clicked.connect(self._show_history_menu)

        self.btn_downloads = QPushButton(Icons.DOWNLOADS, self._retired_btn_container)
        self.btn_downloads.clicked.connect(self._toggle_downloads)

        self.btn_tab_orient = QPushButton("TABS: VERT" if self.tab_orientation == "vertical" else "TABS: HORIZ", self._retired_btn_container)
        self.btn_tab_orient.clicked.connect(lambda: self.set_tab_orientation("horizontal" if self.tab_orientation == "vertical" else "vertical"))

        self.btn_mode = QPushButton("MODE: MINIMAL", self._retired_btn_container)
        self.btn_mode.clicked.connect(self._show_mode_menu)

        self.btn_palette = QPushButton("KEYBINDS", self._retired_btn_container)
        self.btn_palette.clicked.connect(lambda: self.command_palette.show_palette())

        self.btn_ai = QPushButton(Icons.AI, self._retired_btn_container)
        self.btn_ai.clicked.connect(self._toggle_sidebar)

        self.btn_more = QPushButton(getattr(Icons, "MORE", "»"), self._retired_btn_container)
        self.btn_more.clicked.connect(self._show_overflow_menu)

        # Primary Browser Dropdown Menu (Consistent monospace font, no emoji)
        self.btn_menu = QPushButton(t("menu_btn"))
        self.btn_menu.setObjectName("accentBtn")
        self.btn_menu.setFixedHeight(28)
        self.btn_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_menu.setStyleSheet("font-family: \"Iosevka Nerd Font\", \"JetBrains Mono\", monospace; font-size: 12px; font-weight: bold; padding: 4px 10px;")
        self.btn_menu.setToolTip(t("main_menu_tooltip"))
        self.btn_menu.clicked.connect(self._show_main_browser_menu)
        layout.addWidget(self.btn_menu)
        self.btn_settings = self.btn_menu  # Backward-compatibility alias

        # Pinned Toolbar Buttons Management
        self._pinned_btns = {}
        self._update_pinned_toolbar()

        self.root_layout.addWidget(self.top_bar)

    def _init_status_bar(self) -> None:
        self.status_bar = QStatusBar(self)
        self.setStatusBar(self.status_bar)

        # Vim command input in status bar
        acc = self.settings.get("accent_color", "#a855f7")
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
        QShortcut(QKeySequence("Ctrl+T"), self, lambda: self.tab_manager.create_tab(self.settings.get("new_tab_url", "crux://startpage")))
        QShortcut(QKeySequence("Ctrl+N"), self, self._open_new_window)
        QShortcut(QKeySequence("Ctrl+W"), self, lambda: self.tab_manager.close_tab(self.tab_manager.active_tab_id))
        QShortcut(QKeySequence("Ctrl+F"), self, self._toggle_find_in_page)
        QShortcut(QKeySequence("Ctrl+Shift+N"), self, self._open_incognito_window)
        QShortcut(QKeySequence("F10"), self, self._show_main_browser_menu)
        QShortcut(QKeySequence("Alt+F"), self, self._show_main_browser_menu)
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
        QShortcut(QKeySequence("F12"), self, self._toggle_devtools)
        QShortcut(QKeySequence("Ctrl+Shift+I"), self, self._toggle_devtools)
        QShortcut(QKeySequence("Ctrl+Shift+M"), self, self._toggle_viewport_bar)
        QShortcut(QKeySequence("Shift+Esc"), self, lambda: self.tab_manager.create_tab("crux://tasks"))

    def set_tab_orientation(self, orient: str) -> None:
        self.tab_orientation = orient
        self.settings["tab_orientation"] = orient
        save_settings(self.settings)
        if hasattr(self, "btn_tab_orient"):
            self.btn_tab_orient.setText(t("tabs_vert_short") if orient == "vertical" else t("tabs_horiz_short"))
        if self.ui_mode == "minimal":
            if orient == "horizontal":
                if hasattr(self, "tab_manager") and hasattr(self.tab_manager, "sidebar"):
                    self.tab_manager.sidebar.list_widget.setUpdatesEnabled(False)
                    self.tab_manager.sidebar.hide()
                self.horizontal_tab_container.show()
                self._sync_horizontal_tabs()
            else:
                self.horizontal_tab_container.hide()
                if hasattr(self, "tab_manager") and hasattr(self.tab_manager, "sidebar"):
                    self.tab_manager.sidebar.show()
                    self.tab_manager.sidebar.list_widget.setUpdatesEnabled(True)

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

    def handle_fullscreen_request(self, toggle_on: bool) -> None:
        self.is_fullscreen_active = toggle_on
        if toggle_on:
            self._was_maximized_before_fullscreen = self.isMaximized()
            self.top_bar.hide()
            self.horizontal_tab_container.hide()
            if hasattr(self, "tab_manager") and hasattr(self.tab_manager, "sidebar"):
                self.tab_manager.sidebar.hide()
            if hasattr(self, "side_panel"):
                self.side_panel.hide()
            self.status_bar.hide()
            if hasattr(self, "password_save_banner"):
                self.password_save_banner.hide()
            self.showFullScreen()
        else:
            if getattr(self, "_was_maximized_before_fullscreen", False):
                self.showMaximized()
            else:
                self.showNormal()
            self.apply_mode(self.ui_mode)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_topbar_overflow()
        if hasattr(self, "password_save_banner") and self.password_save_banner.isVisible():
            bx = self.width() - self.password_save_banner.width() - 20
            by = (self.top_bar.height() + 8) if (self.ui_mode != "vim" and self.top_bar.isVisible()) else 12
            self.password_save_banner.move(bx, by)

    def closeEvent(self, event) -> None:
        if not getattr(self, "is_incognito", False) and self.settings.get("restore_session", False):
            session_data = []
            for tid, tab_data in self.tabs_ordered():
                v = self.tab_manager.get_tab_view(tid)
                u = getattr(tab_data, "url", "")
                if not u and v:
                    u = v.url().toString()
                if u and not u.startswith("about:blank") and not u.startswith("data:"):
                    session_data.append({
                        "url": u,
                        "container_id": getattr(tab_data, "container_id", "default"),
                        "title": getattr(tab_data, "title", "New Tab"),
                        "is_pinned": getattr(tab_data, "is_pinned", False),
                    })
            from config import CONFIG_DIR
            from utils.bookmarks import atomic_save_json
            try:
                atomic_save_json(CONFIG_DIR / "session.json", session_data)
            except Exception as e:
                print(f"[Session Save Error] {e}")
        super().closeEvent(event)

    def show_password_save_prompt(self, url: str, username: str, password: str) -> None:
        if not hasattr(self, "password_save_banner"):
            return
        bx = self.width() - self.password_save_banner.width() - 20
        by = (self.top_bar.height() + 8) if (self.ui_mode != "vim" and self.top_bar.isVisible()) else 12
        self.password_save_banner.move(bx, by)
        self.password_save_banner.set_credentials(url, username, password)
        th = self.settings.get("theme", "dark")
        acc = self.settings.get("accent_color", "#a855f7")
        self.password_save_banner.update_theme(th, acc)
        self.password_save_banner.retranslate_ui()
        self.password_save_banner.show()
        self.password_save_banner.raise_()

    def _apply_theme_style(self, mode: str = "minimal") -> None:
        th = self.settings.get("theme", "dark")
        acc = self.settings.get("accent_color", "#a855f7")
        from core.theme_manager import apply_app_theme, generate_stylesheet
        qss = generate_stylesheet(th, acc)
        apply_app_theme(QApplication.instance(), th, acc)
        self.setStyleSheet(qss)
        self.horizontal_tab_container.setStyleSheet("")
        self.horizontal_tab_bar.setStyleSheet("")
        self.top_bar.setStyleSheet("")
        self.url_bar.setStyleSheet("")
        if hasattr(self, "status_bar"):
            self.status_bar.setStyleSheet("")
        if hasattr(self, "_apply_completer_style"):
            self._apply_completer_style()
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
        if hasattr(self, "download_manager"):
            self.download_manager.update_style(th, acc)
        self._reload_startpages()

    def _reload_startpages(self) -> None:
        th = self.settings.get("theme", "dark")
        acc = self.settings.get("accent_color", "#a855f7")
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
                            if any(p in url_str for p in ["startpage", "settings", "history", "downloads", "tasks", "welcome", "vault", "about"]):
                                v.page().setBackgroundColor(QColor("#18181b" if th == "dark" else "#f8fafc"))
                                if any(x in url_str for x in ["tasks", "processes"]):
                                    v.reload()
                                else:
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
        if hasattr(self, "btn_back"):
            self.btn_back.setToolTip(t("nav_back"))
        if hasattr(self, "btn_fwd"):
            self.btn_fwd.setToolTip(t("nav_forward"))
        if hasattr(self, "btn_reload"):
            self.btn_reload.setToolTip(t("nav_reload"))
        if hasattr(self, "ssl_badge"):
            self.ssl_badge.setToolTip(t("nav_ssl"))
        if hasattr(self, "btn_menu"):
            self.btn_menu.setText(t("menu_btn"))
            self.btn_menu.setToolTip(t("main_menu_tooltip"))
        elif hasattr(self, "btn_settings"):
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
            if any(k in url_str for k in ["startpage", "welcome", "settings", "history", "downloads", "tasks", "crux://", "zephyrium://", "zinc://"]):
                self.ssl_badge.setText(t("internal_page"))
        if hasattr(self, "tab_manager"):
            self.tab_manager.retranslate_ui()
        if hasattr(self, "side_panel"):
            self.side_panel.retranslate_ui()
        if hasattr(self, "password_save_banner"):
            self.password_save_banner.retranslate_ui()
        if hasattr(self, "download_manager"):
            self.download_manager.retranslate_ui()
        self._update_pinned_toolbar()
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
            title_text = f"[PIN] {data.title}" if data.is_pinned else (data.title or "New Tab")
            
            if idx < self.horizontal_tab_bar.count() and self.horizontal_tab_bar.tabData(idx) == tid:
                # Update text in place if changed
                if self.horizontal_tab_bar.tabText(idx) != title_text:
                    self.horizontal_tab_bar.setTabText(idx, title_text)
                self.horizontal_tab_bar.setTabToolTip(idx, data.title or "New Tab")
                if data.is_pinned:
                    self.horizontal_tab_bar.setTabButton(idx, QTabBar.ButtonPosition.RightSide, None)
                else:
                    if self.horizontal_tab_bar.tabButton(idx, QTabBar.ButtonPosition.RightSide) is None:
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
                        self.horizontal_tab_bar.setTabButton(idx, QTabBar.ButtonPosition.RightSide, close_btn)
            else:
                # Insert tab at this position
                ins_idx = self.horizontal_tab_bar.insertTab(idx, title_text)
                self.horizontal_tab_bar.setTabData(ins_idx, tid)
                self.horizontal_tab_bar.setTabToolTip(ins_idx, data.title or "New Tab")

                if not data.is_pinned:
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
                else:
                    self.horizontal_tab_bar.setTabButton(ins_idx, QTabBar.ButtonPosition.RightSide, None)

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

    def _on_horizontal_tab_moved(self, from_idx: int, to_idx: int) -> None:
        if from_idx != to_idx and hasattr(self, "tab_manager"):
            self.tab_manager.sidebar.list_widget.move_tab_row(from_idx, to_idx)

    def _close_horizontal_tab(self, tab_id: int) -> None:
        self.tab_manager.close_tab(tab_id)
        self._sync_horizontal_tabs()

    def _show_horizontal_tab_context_menu(self, pos) -> None:
        idx = self.horizontal_tab_bar.tabAt(pos)
        if idx < 0:
            return
        tid = self.horizontal_tab_bar.tabData(idx)
        if tid is None or tid not in self.tab_manager.tabs:
            return
        tab_data = self.tab_manager.tabs[tid]

        menu = QMenu(self)

        is_pinned = tab_data.is_pinned
        act_pin = menu.addAction(t("unpin_tab") if is_pinned else t("pin_tab"))
        act_pin.triggered.connect(lambda: self.tab_manager.toggle_pin_tab(tid))

        is_muted = getattr(tab_data, "is_muted", False)
        act_mute = menu.addAction(t("unmute_tab") if is_muted else t("mute_tab"))
        act_mute.triggered.connect(lambda: self.tab_manager.toggle_mute_tab(tid))

        menu.addSeparator()

        act_dup = menu.addAction(t("duplicate_tab"))
        act_dup.triggered.connect(lambda: self.tab_manager.duplicate_tab(tid))

        act_split = menu.addAction(t("split_view"))
        act_split.triggered.connect(lambda: self.tab_manager.split_active_tab(tid))

        menu.addSeparator()

        act_close = menu.addAction(t("close_tab"))
        act_close.setEnabled(not is_pinned)
        act_close.triggered.connect(lambda: self.tab_manager.close_tab(tid))

        menu.exec(self.horizontal_tab_bar.mapToGlobal(pos))

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
        act_settings.triggered.connect(lambda: self.tab_manager.create_tab("default", "crux://settings?tab=adblock"))

        self._exec_menu_anchored(menu, getattr(self, "btn_adblock", None))

    def _exec_menu_anchored(self, menu: QMenu, anchor_btn: QWidget = None) -> None:
        """Executes a popup menu aligned neatly under the target anchor button or top-right MENU button with boundary safety."""
        target = anchor_btn
        if not target or not target.isVisible():
            target = getattr(self, "btn_menu", getattr(self, "btn_settings", None))
        menu.adjustSize()
        menu_w = menu.sizeHint().width()
        if target and target.isVisible():
            g_pos = target.mapToGlobal(target.rect().bottomLeft())
            # Align right edge of menu with right edge of button
            x = g_pos.x() + target.width() - menu_w
            y = g_pos.y() + 2
            if x < 10:
                x = 10
            menu.exec(QPoint(x, y))
        elif self.isVisible():
            p_geo = self.geometry()
            x = p_geo.x() + p_geo.width() - menu_w - 20
            y = p_geo.y() + 70
            if x < 10:
                x = 10
            menu.exec(QPoint(x, y))
        else:
            menu.exec(QCursor.pos())

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
        act_full.triggered.connect(lambda: self.tab_manager.create_tab("default", "crux://history"))

        act_clear = menu.addAction(t("clear_history"))
        act_clear.triggered.connect(self._clear_history_action)

        act_settings = menu.addAction(t("history_settings"))
        act_settings.triggered.connect(lambda: self.tab_manager.create_tab("default", "crux://settings?tab=general"))

        self._exec_menu_anchored(menu, getattr(self, "btn_history", None))

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
        act_all.triggered.connect(lambda: self.tab_manager.create_tab("default", "crux://downloads"))

        act_folder = menu.addAction(t("open_downloads_folder"))
        act_folder.triggered.connect(self._open_downloads_folder)

        act_clear = menu.addAction(t("clear_downloads"))
        act_clear.triggered.connect(self._clear_downloads_action)

        act_settings = menu.addAction(t("downloads_settings"))
        act_settings.triggered.connect(lambda: self.tab_manager.create_tab("default", "crux://settings?tab=downloads"))

        self._exec_menu_anchored(menu, getattr(self, "btn_downloads", None))

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
        from utils.bookmarks import open_folder_in_file_manager
        from pathlib import Path
        ddir = self.settings.get("download_dir", str(Path.home() / "Downloads"))
        open_folder_in_file_manager(ddir)

    def _open_downloaded_file(self, path: str) -> None:
        import os
        from PyQt6.QtGui import QDesktopServices
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

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

    def _init_url_completer(self) -> None:
        self._url_completer = QCompleter(self)
        self._url_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._url_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._url_completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.url_bar.setCompleter(self._url_completer)
        self._apply_completer_style()
        self._update_url_completer()

    def _apply_completer_style(self) -> None:
        if not hasattr(self, "_url_completer"):
            return
        popup = self._url_completer.popup()
        if popup:
            th = self.settings.get("theme", "dark")
            acc = self.settings.get("accent_color", "#a855f7")
            bg = "#18181b" if th == "dark" else "#ffffff"
            text_color = "#d4d4d8" if th == "dark" else "#1e293b"
            border_col = "#3f3f46" if th == "dark" else "#cbd5e1"
            popup.setStyleSheet(f"""
                QAbstractItemView {{
                    background-color: {bg};
                    color: {text_color};
                    border: 1px solid {border_col};
                    border-radius: 0px;
                    selection-background-color: {acc};
                    selection-color: #ffffff;
                    font-family: monospace;
                    font-size: 12px;
                    padding: 4px;
                    outline: none;
                }}
            """)

    def _update_url_completer(self) -> None:
        suggestions = [
            "google.com", "github.com", "youtube.com", "reddit.com", "yandex.ru",
            "wikipedia.org", "duckduckgo.com", "habr.com", "vk.com", "telegram.org",
            "archlinux.org", "kde.org", "gitlab.com", "stackoverflow.com",
            "news.ycombinator.com", "chatgpt.com", "developer.mozilla.org",
            "crux://startpage", "crux://settings", "crux://history", "crux://downloads"
        ]
        try:
            hist = DataStore.get_history()
            for item in hist[:100]:
                u = item.get("url", "")
                if u and u not in suggestions:
                    suggestions.append(u)
        except Exception:
            pass
        model = QStringListModel(suggestions, self._url_completer)
        self._url_completer.setModel(model)

    def _on_reader_mode_clicked(self) -> None:
        v = self.tab_manager.get_current_view()
        if v and hasattr(v, "toggle_reader_mode"):
            v.toggle_reader_mode()

    def _on_pip_clicked(self) -> None:
        v = self.tab_manager.get_current_view()
        if v and hasattr(v, "trigger_pip"):
            v.trigger_pip()

    def _on_ai_action(self, action: str, text: str) -> None:
        self.side_panel.show()
        self.side_panel.switch_tab(0)
        prompts = {
            "explain": f"Explain the following text or code concisely:\n\n{text}",
            "translate": f"Translate the following text into Russian accurately:\n\n{text}",
            "summarize": f"Summarize the key points of the following text:\n\n{text}",
        }
        prompt = prompts.get(action, text)
        if hasattr(self.side_panel, "ai_widget"):
            self.side_panel.ai_widget._append_user(f"[{action.upper()}]\n{text}")
            self.side_panel.ai_widget._process_ai_query(prompt)
        elif hasattr(self.side_panel, "ai_chat"):
            self.side_panel.ai_chat.input_field.setPlainText(prompt)
            self.side_panel.ai_chat.send_message()

    def _on_url_entered(self) -> None:
        text = self.url_bar.text().strip()
        if not text:
            return
        if text in ["crux://settings", "zephyrium://settings", "zinc://settings", "about:settings", "about:preferences"]:
            self.open_settings()
            return
        if text in ["crux://about", "zephyrium://about", "zinc://about"]:
            self.open_settings("about")
            return
        if text in ["crux://welcome", "zephyrium://welcome", "zinc://welcome"]:
            self.show_onboarding()
            return
        if text in ["crux://vault", "zephyrium://vault", "zinc://vault"]:
            self.open_settings("vault")
            return
        if text in ["crux://history", "zephyrium://history", "zinc://history", "about:history"]:
            self.tab_manager.create_tab("default", "crux://history")
            return
        if text in ["crux://downloads", "zephyrium://downloads", "zinc://downloads", "about:downloads"]:
            self.tab_manager.create_tab("default", "crux://downloads")
            return
        if text in ["crux://tasks", "zephyrium://tasks", "zinc://tasks", "about:tasks"]:
            self.tab_manager.create_tab("default", "crux://tasks")
            return
        v = self.tab_manager.get_current_view()
        if v:
            v.navigate(text)
            v.setFocus()
            self._update_url_completer()

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
            if hasattr(self, "btn_downloads") and self.btn_downloads.isVisible():
                self.download_manager.show_at_widget(self.btn_downloads)
            elif hasattr(self, "btn_menu") and self.btn_menu.isVisible():
                self.download_manager.show_at_widget(self.btn_menu)
            elif hasattr(self, "btn_more") and self.btn_more.isVisible():
                self.download_manager.show_at_widget(self.btn_more)
            else:
                self.download_manager.show_at_widget(None)

    def _on_download_requested(self, item) -> None:
        url_str = item.url().toString()
        filename = item.downloadFileName()
        if filename.endswith(".user.js") or url_str.endswith(".user.js") or ".user.js?" in url_str:
            item.cancel()
            self._prompt_install_userscript(url_str, filename)
            return
        self.download_manager.handle_download(item)

    def _prompt_install_userscript(self, url_str: str, filename: str) -> None:
        import html
        import urllib.request
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtCore import QThread, pyqtSignal

        class UserscriptFetchThread(QThread):
            success = pyqtSignal(str, str, str)
            failed = pyqtSignal(str)

            def __init__(self, u, fn):
                super().__init__()
                self.u = u
                self.fn = fn

            def run(self):
                try:
                    req = urllib.request.Request(self.u, headers={"User-Agent": "Mozilla/5.0 Crux/1.3.6"})
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        code = resp.read().decode("utf-8", errors="replace")
                        self.success.emit(self.u, self.fn, code)
                except Exception as e:
                    self.failed.emit(str(e))

        def _on_success(u, fn, code):
            if not code or not code.strip():
                self._show_status_message(t("userscript_empty_err"))
                return
            meta = self.profile_manager.userscript_manager.parse_userscript_metadata(code)
            name = meta.get("name") or fn
            ver = meta.get("version") or "1.0"
            desc = meta.get("description") or t("userscript_no_desc")
            matches = ", ".join(meta.get("matches", [])) or t("userscript_all_sites")

            msg = QMessageBox(self)
            msg.setWindowTitle(t("userscript_install_title"))
            msg.setText(f"<b>{t('userscript_install_prompt')}</b><br><br>"
                        f"<b>{t('userscript_name_label')}</b> {html.escape(name)}<br>"
                        f"<b>{t('userscript_ver_label')}</b> {html.escape(ver)}<br>"
                        f"<b>{t('userscript_sites_label')}</b> <code>{html.escape(matches)}</code><br>"
                        f"<b>{t('userscript_desc_label')}</b> {html.escape(desc)}")
            msg.setIcon(QMessageBox.Icon.Question)
            btn_install = msg.addButton(t("btn_install"), QMessageBox.ButtonRole.AcceptRole)
            btn_cancel = msg.addButton(t("cancel"), QMessageBox.ButtonRole.RejectRole)
            msg.exec()

            if msg.clickedButton() == btn_install:
                clean_name = fn if fn.endswith(".user.js") else f"{name}.user.js"
                self.profile_manager.userscript_manager.save_script(clean_name, code)
                self._show_status_message(t("userscript_installed_success", name=name))

        def _on_failed(err):
            self._show_status_message(t("userscript_load_err", err=err))

        self._us_fetcher = UserscriptFetchThread(url_str, filename)
        self._us_fetcher.success.connect(_on_success)
        self._us_fetcher.failed.connect(_on_failed)
        self._us_fetcher.start()

    def _update_pinned_toolbar(self) -> None:
        """Dynamically manages user-pinned shortcut buttons in top toolbar next to MENU."""
        if not hasattr(self, "top_bar") or not self.top_bar.layout():
            return
        layout = self.top_bar.layout()
        pinned = self.settings.get("pinned_toolbar", ["downloads", "history"])
        if not isinstance(pinned, list):
            pinned = ["downloads", "history"]

        configs = {
            "downloads": {
                "text": t("pin_btn_downloads"),
                "tooltip": t("downloads_menu"),
                "callback": self._toggle_downloads,
                "menu_anchor": "btn_downloads",
            },
            "history": {
                "text": t("pin_btn_history"),
                "tooltip": t("history_menu"),
                "callback": self._show_history_menu,
                "menu_anchor": "btn_history",
            },
            "bookmarks": {
                "text": t("pin_btn_bookmarks"),
                "tooltip": t("bookmarks_menu"),
                "callback": self._show_bookmarks_menu,
                "menu_anchor": "btn_bookmarks",
            },
            "reader": {
                "text": t("pin_btn_reader"),
                "tooltip": t("reader_mode_menu"),
                "callback": self._on_reader_mode_clicked,
                "menu_anchor": "btn_reader",
            },
            "split": {
                "text": t("pin_btn_split"),
                "tooltip": f"{t('split_view')} (Ctrl+\\)",
                "callback": lambda: self.tab_manager.split_active_tab(),
                "menu_anchor": "btn_split",
            },
            "ai": {
                "text": t("pin_btn_ai"),
                "tooltip": t("ai_assistant_menu"),
                "callback": self._toggle_sidebar,
                "menu_anchor": "btn_ai",
            },
        }

        # Remove buttons no longer pinned
        for key in list(self._pinned_btns.keys()):
            if key not in pinned:
                btn = self._pinned_btns.pop(key)
                layout.removeWidget(btn)
                btn.setParent(None)
                btn.deleteLater()

        menu_idx = layout.indexOf(self.btn_menu)
        if menu_idx < 0:
            menu_idx = layout.count()

        # Add or update pinned buttons
        for key in pinned:
            if key not in configs:
                continue
            cfg = configs[key]
            if key in self._pinned_btns:
                b = self._pinned_btns[key]
                b.setText(cfg["text"])
                b.setToolTip(cfg["tooltip"])
            else:
                b = QPushButton(cfg["text"])
                b.setFixedHeight(28)
                b.setCursor(Qt.CursorShape.PointingHandCursor)
                b.setStyleSheet("font-family: \"Iosevka Nerd Font\", \"JetBrains Mono\", monospace; font-size: 11px; font-weight: bold; padding: 3px 8px;")
                b.setToolTip(cfg["tooltip"])
                b.clicked.connect(cfg["callback"])
                layout.insertWidget(menu_idx, b)
                self._pinned_btns[key] = b
                # Also expose on self for anchor lookup
                setattr(self, f"btn_{key}", b)
                menu_idx += 1

    def toggle_pin_action(self, action_key: str) -> None:
        """Toggles pinning an action button in top toolbar and saves settings."""
        from config import save_settings
        pinned = list(self.settings.get("pinned_toolbar", ["downloads", "history"]))
        if action_key in pinned:
            pinned.remove(action_key)
            self._show_status_message(t("pin_toolbar_removed", action=action_key.upper()))
        else:
            pinned.append(action_key)
            self._show_status_message(t("pin_toolbar_added", action=action_key.upper()))
        self.settings["pinned_toolbar"] = pinned
        save_settings(self.settings)
        self._update_pinned_toolbar()

    def _update_topbar_overflow(self) -> None:
        pass

    def _show_overflow_menu(self) -> None:
        menu = QMenu(self)

        act_reader = menu.addAction(f"{Icons.READER} {t('reader_mode') if hasattr(self, 'btn_reader') else 'Reader Mode'}")
        act_reader.triggered.connect(self._on_reader_mode_clicked)

        act_pip = menu.addAction(f"{Icons.PIP} Picture-in-Picture")
        act_pip.triggered.connect(self._on_pip_clicked)

        blocked = self.adblocker.blocked_count if hasattr(self, "adblocker") else 0
        act_ads = menu.addAction(f"{Icons.ADBLOCK} AdBlocker ({blocked} blocked)")
        act_ads.triggered.connect(self._show_adblock_menu)

        menu.addSeparator()

        act_split = menu.addAction(f"{Icons.SPLIT} {t('split_view')}")
        act_split.triggered.connect(lambda: self.tab_manager.split_active_tab())

        act_hist = menu.addAction(f"{t('history_title')}")
        act_hist.triggered.connect(self._show_history_menu)

        act_dl = menu.addAction(f"{Icons.DOWNLOADS} {t('downloads_title')}")
        act_dl.triggered.connect(self._toggle_downloads)

        menu.addSeparator()

        tab_txt = t("tabs_horiz_short") if self.tab_orientation == "vertical" else t("tabs_vert_short")
        act_tab = menu.addAction(f"Tabs: {tab_txt}")
        act_tab.triggered.connect(lambda: self.set_tab_orientation("horizontal" if self.tab_orientation == "vertical" else "vertical"))

        act_mode = menu.addAction(f"{t('mode_label')}: {t('mode_' + self.ui_mode)}".upper())
        act_mode.triggered.connect(self._show_mode_menu)

        act_pal = menu.addAction(f"{t('keybinds')} (Ctrl+K)")
        act_pal.triggered.connect(lambda: self.command_palette.show_palette())

        menu.exec(self.btn_more.mapToGlobal(self.btn_more.rect().bottomLeft()))

    def _show_security_info(self) -> None:
        v = self.tab_manager.get_current_view()
        u_str = v.url().toString() if v else ""
        menu = QMenu(self)

        is_internal = any(k in u_str for k in ["crux://", "zephyrium://", "zinc://", "about:", "startpage.html", "settings.html", "history.html", "downloads.html"])
        if is_internal:
            act_title = menu.addAction(f"[SECURE] {t('security_internal_title')}")
            act_title.setEnabled(False)
            menu.addSeparator()
            act_desc = menu.addAction(t("security_internal_desc"))
            act_desc.setEnabled(False)
        elif u_str.startswith("https://"):
            import urllib.parse
            host = urllib.parse.urlparse(u_str).hostname or "Site"
            act_title = menu.addAction(f"[SECURE] {t('security_secure_title')}")
            act_title.setEnabled(False)
            menu.addSeparator()
            act_host = menu.addAction(f"Host: {host}")
            act_host.setEnabled(False)
            act_desc = menu.addAction(t("security_secure_desc"))
            act_desc.setEnabled(False)
            act_tls = menu.addAction("TLS 1.3 / 256-bit AES encryption")
            act_tls.setEnabled(False)
        else:
            act_title = menu.addAction(f"[INSECURE] {t('security_insecure_title')}")
            act_title.setEnabled(False)
            menu.addSeparator()
            act_desc = menu.addAction(t("security_insecure_desc"))
            act_desc.setEnabled(False)

        menu.exec(self.ssl_badge.mapToGlobal(self.ssl_badge.rect().bottomLeft()))

    def _update_nav_buttons(self) -> None:
        v = self.tab_manager.get_current_view()
        if v and hasattr(v, "history"):
            h = v.history()
            self.btn_back.setEnabled(h.canGoBack())
            self.btn_fwd.setEnabled(h.canGoForward())
        else:
            self.btn_back.setEnabled(False)
            self.btn_fwd.setEnabled(False)

    def _on_view_load_finished(self, success: bool) -> None:
        self._update_nav_buttons()

    def _toggle_find_in_page(self) -> None:
        if self.find_bar.isVisible():
            self.find_bar.close_bar()
        else:
            self.find_bar.show_find()

    def _on_find_in_page(self, query: str, forward: bool = True) -> None:
        v = self.tab_manager.get_current_view()
        if not v or not query:
            return
        from PyQt6.QtWebEngineCore import QWebEnginePage
        flags = QWebEnginePage.FindFlag(0)
        if not forward:
            flags |= QWebEnginePage.FindFlag.FindBackward
        v.findText(query, flags, lambda found: self.find_bar.set_match_result(1 if found else 0, 1 if found else 0))

    def _on_find_bar_closed(self) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            from PyQt6.QtWebEngineCore import QWebEnginePage
            v.findText("", QWebEnginePage.FindFlag(0))

    def _open_incognito_window(self) -> None:
        incog_win = BrowserWindow(is_incognito=True)
        if not hasattr(self, "_sub_windows"):
            self._sub_windows = []
        self._sub_windows.append(incog_win)
        incog_win.show()

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
        if "welcome" in url_str:
            self.url_bar.setText("crux://welcome")
            self.ssl_badge.setText(t("internal_page"))
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        elif "startpage" in url_str:
            self.url_bar.setText("crux://startpage")
            self.ssl_badge.setText(t("internal_page"))
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        elif "settings" in url_str:
            self.url_bar.setText(url_str if (url_str.startswith("crux://") or url_str.startswith("zephyrium://")) else "crux://settings")
            self.ssl_badge.setText(t("internal_page"))
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        elif "history" in url_str:
            self.url_bar.setText("crux://history")
            self.ssl_badge.setText(t("internal_page"))
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        elif "downloads" in url_str:
            self.url_bar.setText("crux://downloads")
            self.ssl_badge.setText(t("internal_page"))
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        elif "tasks" in url_str or "taskmanager" in url_str:
            self.url_bar.setText("crux://tasks")
            self.ssl_badge.setText(t("internal_page"))
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        elif url_str.startswith("crux://") or url_str.startswith("zephyrium://") or url_str.startswith("zinc://"):
            self.url_bar.setText(url_str)
            self.ssl_badge.setText(t("internal_page"))
            self.ssl_badge.setStyleSheet("color: #94a3b8;")
        else:
            self.url_bar.setText(url_str)
            if url.scheme() == "https":
                self.ssl_badge.setText(Icons.LOCK_SECURE)
                self.ssl_badge.setStyleSheet("color: #10b981; font-weight: bold;")
            elif url.scheme() == "http":
                self.ssl_badge.setText(Icons.LOCK_INSECURE)
                self.ssl_badge.setStyleSheet("color: #ef4444; font-weight: bold;")
            else:
                self.ssl_badge.setText("PAGE")
                self.ssl_badge.setStyleSheet("color: #94a3b8;")
            v = self.tab_manager.get_current_view()
            if v and v.title():
                active_tab = self.tab_manager.tabs.get(self.tab_manager.active_tab_id)
                is_tab_incognito = getattr(self, "is_incognito", False) or (active_tab and getattr(active_tab, "container_id", "") == "incognito")
                if not is_tab_incognito:
                    DataStore.add_history(v.title(), url_str)

        # Ensure start of URL is visible only if user is not currently focused on the URL bar
        if not self.url_bar.hasFocus():
            self.url_bar.setCursorPosition(0)

        self._update_nav_buttons()

        if self.ui_mode == "vim":
            self.status_label.setText(f"[VIM] {url_str}")

    def _on_active_title_changed(self, title: str) -> None:
        title_mode = "[INCOGNITO]" if getattr(self, "is_incognito", False) else f"[{self.ui_mode.capitalize()}]"
        if title and title.strip():
            clean_title = f"{title.strip()} — {APP_NAME}"
        else:
            clean_title = f"{APP_NAME} v{APP_VERSION} {title_mode}"
        self.setWindowTitle(clean_title)
        if self.tab_orientation == "horizontal":
            self._sync_horizontal_tabs()

    def _on_active_tab_changed(self, split_container) -> None:
        view = split_container.get_active_view()
        view.loadProgress.connect(self._on_load_progress)
        view.status_message.connect(self.status_label.setText)
        view.ask_ai_selection.connect(self._on_ai_selection_requested)
        if hasattr(view, "ask_ai_action"):
            view.ask_ai_action.connect(self._on_ai_action)

        self._update_nav_buttons()
        try:
            view.urlChanged.disconnect(self._update_nav_buttons)
        except Exception:
            pass
        view.urlChanged.connect(self._update_nav_buttons)
        try:
            view.loadFinished.disconnect(self._on_view_load_finished)
        except Exception:
            pass
        view.loadFinished.connect(self._on_view_load_finished)

        # Switch DevTools target to the newly active tab
        if hasattr(self, "devtools_dock") and self.devtools_dock.isVisible():
            if view and hasattr(view, "page"):
                view.page().setDevToolsPage(self.devtools_view.page())
                host = view.url().host() or "Local Page"
                self.devtools_title.setText(f"DevTools — {host}")

        # Sync active URL in omnibar and ensure beginning of URL is visible
        cur_u = view.url().toString()
        active_tab = self.tab_manager.tabs.get(self.tab_manager.active_tab_id)
        saved_u = getattr(active_tab, "url", "") if active_tab else ""
        if cur_u.startswith("data:"):
            cur_u = saved_u or "crux://startpage"
        if "startpage" in cur_u:
            self.url_bar.setText("crux://startpage")
        elif "welcome" in cur_u:
            self.url_bar.setText("crux://welcome")
        elif "settings" in cur_u:
            self.url_bar.setText(cur_u if (cur_u.startswith("crux://") or cur_u.startswith("zephyrium://")) else "crux://settings")
        elif "history" in cur_u:
            self.url_bar.setText("crux://history")
        elif "downloads" in cur_u:
            self.url_bar.setText("crux://downloads")
        elif "tasks" in cur_u or "taskmanager" in cur_u:
            self.url_bar.setText("crux://tasks")
        elif cur_u:
            self.url_bar.setText(cur_u)
        if not self.url_bar.hasFocus():
            self.url_bar.setCursorPosition(0)

        self.zoom_label.setText(f"{int(view.get_zoom() * 100)}%")

        if getattr(self, "is_mobile_mode", False):
            self._apply_mobile_mode_to_view(view)
        else:
            self._restore_desktop_view(view)

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

    def _show_status_message(self, msg: str, timeout: int = 3000) -> None:
        try:
            if hasattr(self, "status_label") and self.status_label:
                self.status_label.setText(str(msg))
            if hasattr(self, "status_bar") and self.status_bar:
                self.status_bar.showMessage(str(msg), timeout)
        except Exception:
            pass

    def _handle_command_action(self, action: str, param: str) -> None:
        v = self.tab_manager.get_current_view()
        if action == "navigate" or action in ["o", "open"]:
            target = param if param else "crux://startpage"
            if v:
                v.navigate(target)
        elif action in ["t", "tabnew"]:
            self.tab_manager.create_tab(param or "crux://startpage")
        elif action in ["tasks", "taskmanager"]:
            self.tab_manager.create_tab("crux://tasks")
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
        elif action == "switch_tab":
            try:
                self.tab_manager.select_tab(int(param))
            except Exception:
                pass
        elif action == "copy_clipboard":
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(param)
            self._show_status_message(f"Copied: {param}")
        elif action == "snooze_tab":
            self._show_status_message(t("snooze_active_error"))
        elif action == "snooze_others":
            try:
                count = 0
                for tid in list(self.tab_manager.tabs.keys()):
                    if tid != self.tab_manager.active_tab_id:
                        if self.tab_manager.suspend_tab(tid):
                            count += 1
                self._show_status_message(t("snooze_others_success", count=count))
            except Exception as e:
                self._show_status_message(t("snooze_err", e=e))
        elif action == "wake_all":
            try:
                for tid in list(self.tab_manager.tabs.keys()):
                    self.tab_manager.wake_tab(tid)
                self._show_status_message(t("wake_all_success"))
            except Exception as e:
                self._show_status_message(t("wake_err", e=e))
        elif action == "find":
            self._toggle_find_in_page()
        elif action == "pin":
            self.tab_manager.toggle_pin_tab(self.tab_manager.active_tab_id)
        elif action.startswith("container:"):
            c_id = action.split(":")[-1]
            self.tab_manager.create_tab(url="crux://startpage", container_id=c_id)
        elif action in ["clean_cookies", "cleardata"]:
            try:
                from PyQt6.QtWebEngineCore import QWebEngineProfile
                QWebEngineProfile.defaultProfile().clearHttpCache()
                self._show_status_message("Browser cache cleared")
            except Exception:
                pass
        elif action == "devtools":
            self._toggle_devtools()
        elif action == "viewport":
            self._toggle_viewport_bar()
        elif action in ["settings", "preferences", "config"]:
            self.open_settings()
        elif action == "quit":
            self.close()

    def show_onboarding(self) -> None:
        dlg = OnboardingDialog(self)
        dlg.exec()

    def _open_new_window(self) -> None:
        new_win = BrowserWindow(is_incognito=False)
        if not hasattr(self, "_sub_windows"):
            self._sub_windows = []
        self._sub_windows.append(new_win)
        new_win.show()

    def _show_shortcuts_dialog(self) -> None:
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextBrowser, QPushButton, QHBoxLayout
        dlg = QDialog(self)
        dlg.setWindowTitle(t("keybinds_help_window_title"))
        dlg.setFixedSize(540, 520)
        dlg.setStyleSheet("""
            QDialog { background-color: #18181b; border: 1px solid #3f3f46; }
            QLabel { color: #a855f7; font-family: monospace; font-weight: bold; font-size: 13px; }
            QTextBrowser { background-color: #262624; border: 1px solid #3f3f46; color: #d4d4d8; font-family: monospace; font-size: 11px; }
            QPushButton { background-color: #262624; border: 1px solid #a855f7; color: #a855f7; font-family: monospace; font-weight: bold; padding: 6px 14px; }
            QPushButton:hover { background-color: #a855f7; color: #18181b; }
        """)
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)
        title = QLabel(t("keybinds_help_title"))
        lay.addWidget(title)

        tb = QTextBrowser(dlg)
        html_keys = f"""
        <table style='width:100%; border-collapse:collapse; color:#d4d4d8; font-family:monospace;'>
            <tr style='border-bottom:1px solid #3f3f46; color:#a855f7;'>
                <th style='padding:6px; text-align:left;'>{t("keybinds_col_key")}</th>
                <th style='padding:6px; text-align:left;'>{t("keybinds_col_action")}</th>
            </tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + T</b></td><td>{t("keybind_new_tab")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + W</b></td><td>{t("keybind_close_tab")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + N</b></td><td>{t("keybind_new_win")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + Shift + N</b></td><td>{t("keybind_incognito_win")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + K / Ctrl + L</b></td><td>{t("keybind_cmd_palette")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + F</b></td><td>{t("keybind_find_in_page")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>F12 / Ctrl + Shift + I</b></td><td>{t("keybind_devtools")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Shift + Esc</b></td><td>{t("keybind_task_mgr")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + B</b></td><td>{t("keybind_ai_panel")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + Shift + D</b></td><td>{t("keybind_downloads_popup")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + H</b></td><td>{t("keybind_history")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + Shift + O</b></td><td>{t("keybind_bookmarks")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + Alt + R</b></td><td>{t("keybind_reader_mode")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + Alt + P</b></td><td>{t("keybind_pip")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + [</b></td><td>{t("keybind_toggle_sidebar")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + \\</b></td><td>{t("keybind_split_view")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>F11</b></td><td>{t("keybind_fullscreen")}</td></tr>
            <tr><td style='padding:5px; color:#38bdf8;'><b>Ctrl + ,</b></td><td>{t("keybind_settings")}</td></tr>
            <tr style='border-top:1px solid #3f3f46;'><td colspan='2' style='padding-top:8px; color:#a855f7;'><b>{t("keybinds_vim_section")}:</b></td></tr>
            <tr><td style='padding:4px; color:#a855f7;'><b>j / k</b></td><td>{t("keybind_vim_scroll_lines")}</td></tr>
            <tr><td style='padding:4px; color:#a855f7;'><b>d / u</b></td><td>{t("keybind_vim_scroll_half")}</td></tr>
            <tr><td style='padding:4px; color:#a855f7;'><b>gg / G</b></td><td>{t("keybind_vim_top_bottom")}</td></tr>
            <tr><td style='padding:4px; color:#a855f7;'><b>t / x</b></td><td>{t("keybind_vim_tab_new_close")}</td></tr>
            <tr><td style='padding:4px; color:#a855f7;'><b>J / K</b></td><td>{t("keybind_vim_tab_next_prev")}</td></tr>
            <tr><td style='padding:4px; color:#a855f7;'><b>o / :</b></td><td>{t("keybind_vim_open")}</td></tr>
        </table>
        """
        tb.setHtml(html_keys)
        lay.addWidget(tb)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        btn_close = QPushButton(t("btn_close"))
        btn_close.clicked.connect(dlg.accept)
        btn_box.addWidget(btn_close)
        lay.addLayout(btn_box)
        dlg.exec()

    def _show_main_browser_menu(self) -> None:
        try:
            from PyQt6.QtWidgets import QMenu, QWidgetAction, QWidget, QHBoxLayout, QPushButton, QLabel
            from PyQt6.QtCore import Qt, QPoint
            from PyQt6.QtGui import QCursor

            menu = QMenu(self)
            menu.setStyleSheet("""
                QMenu {
                    background-color: #18181b;
                    border: 1px solid #3f3f46;
                    color: #d4d4d8;
                    font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace;
                    font-size: 12px;
                    padding: 6px;
                }
                QMenu::item {
                    padding: 6px 20px 6px 14px;
                    border-radius: 0px;
                }
                QMenu::item:selected {
                    background-color: #27272a;
                    color: #a855f7;
                }
                QMenu::separator {
                    height: 1px;
                    background: #27272a;
                    margin: 4px 6px;
                }
            """)

            # 1. Graphical Zoom & Scale Controller
            zoom_action = QWidgetAction(menu)
            zoom_w = QWidget(menu)
            zoom_w.setStyleSheet("""
                QWidget { background-color: #18181b; }
                QLabel { color: #d4d4d8; font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace; font-size: 12px; }
                QPushButton {
                    background-color: #27272a;
                    border: 1px solid #3f3f46;
                    color: #d4d4d8;
                    border-radius: 0px;
                    padding: 3px 8px;
                    font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #a855f7;
                    color: #ffffff;
                    border-color: #c084fc;
                }
            """)
            zoom_layout = QHBoxLayout(zoom_w)
            zoom_layout.setContentsMargins(14, 6, 14, 6)
            zoom_layout.setSpacing(6)

            lbl_zoom = QLabel(t("zoom_label"))
            lbl_zoom.setFixedHeight(24)
            lbl_zoom.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            lbl_zoom.setStyleSheet("font-weight: bold; color: #a855f7; padding-top: 1px;")
            zoom_layout.addWidget(lbl_zoom)

            btn_z_minus = QPushButton("－")
            btn_z_minus.setToolTip(t("zoom_out"))
            btn_z_minus.setFixedSize(28, 24)
            btn_z_minus.setCursor(Qt.CursorShape.PointingHandCursor)

            cur_v = self.tab_manager.get_current_view()
            cur_pct = int(cur_v.get_zoom() * 100) if cur_v else 100
            lbl_z_val = QLabel(f"{cur_pct}%")
            lbl_z_val.setFixedSize(46, 24)
            lbl_z_val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_z_val.setStyleSheet("font-weight: bold; color: #f4f4f5; padding-top: 1px;")

            btn_z_plus = QPushButton("＋")
            btn_z_plus.setToolTip(t("zoom_in"))
            btn_z_plus.setFixedSize(28, 24)
            btn_z_plus.setCursor(Qt.CursorShape.PointingHandCursor)

            btn_z_reset = QPushButton("100%")
            btn_z_reset.setToolTip(t("zoom_reset"))
            btn_z_reset.setFixedHeight(24)
            btn_z_reset.setCursor(Qt.CursorShape.PointingHandCursor)

            btn_z_fs = QPushButton("[FS]")
            btn_z_fs.setToolTip(t("fullscreen"))
            btn_z_fs.setFixedHeight(24)
            btn_z_fs.setCursor(Qt.CursorShape.PointingHandCursor)

            def _do_zoom_out():
                self._zoom_out()
                v = self.tab_manager.get_current_view()
                if v:
                    lbl_z_val.setText(f"{int(v.get_zoom() * 100)}%")

            def _do_zoom_in():
                self._zoom_in()
                v = self.tab_manager.get_current_view()
                if v:
                    lbl_z_val.setText(f"{int(v.get_zoom() * 100)}%")

            def _do_zoom_reset():
                self._zoom_reset()
                lbl_z_val.setText("100%")

            def _do_fs():
                menu.close()
                self._toggle_fullscreen()

            btn_z_minus.clicked.connect(_do_zoom_out)
            btn_z_plus.clicked.connect(_do_zoom_in)
            btn_z_reset.clicked.connect(_do_zoom_reset)
            btn_z_fs.clicked.connect(_do_fs)

            zoom_layout.addWidget(btn_z_minus)
            zoom_layout.addWidget(lbl_z_val)
            zoom_layout.addWidget(btn_z_plus)
            zoom_layout.addWidget(btn_z_reset)
            zoom_layout.addWidget(btn_z_fs)

            zoom_action.setDefaultWidget(zoom_w)
            menu.addAction(zoom_action)

            # 2. Instant Mobile Mode Action
            is_mob = getattr(self, "is_mobile_mode", False)
            act_viewport = menu.addAction(t("mobile_mode_on") if is_mob else t("mobile_mode_off"))
            act_viewport.triggered.connect(self.toggle_mobile_mode)

            menu.addSeparator()

            # 3. Quick Reading & Media Actions
            act_reader = menu.addAction(t("reader_mode_menu"))
            act_reader.triggered.connect(self._on_reader_mode_clicked)

            act_pip = menu.addAction(t("pip_mode_menu"))
            act_pip.triggered.connect(self._on_pip_clicked)

            # Tab Orientation Submenu
            tab_menu = menu.addMenu(t("tab_layout_menu"))
            act_vert = tab_menu.addAction(("[x] " if self.tab_orientation == "vertical" else "    ") + t("tab_vertical_menu"))
            act_vert.triggered.connect(lambda: self.set_tab_orientation("vertical"))
            act_horiz = tab_menu.addAction(("[x] " if self.tab_orientation == "horizontal" else "    ") + t("tab_horizontal_menu"))
            act_horiz.triggered.connect(lambda: self.set_tab_orientation("horizontal"))

            # UI Mode Submenu
            ui_menu = menu.addMenu(t("ui_mode_menu"))
            act_min = ui_menu.addAction(("[x] " if self.ui_mode == "minimal" else "    ") + t("ui_mode_minimal"))
            act_min.triggered.connect(lambda: self.switch_ui_mode("minimal"))
            act_vim = ui_menu.addAction(("[x] " if self.ui_mode == "vim" else "    ") + t("ui_mode_vim"))
            act_vim.triggered.connect(lambda: self.switch_ui_mode("vim"))

            # Windows & Tabs
            menu.addSeparator()
            act_new_tab = menu.addAction(f"{t('new_tab')} (Ctrl+T)")
            act_new_tab.triggered.connect(lambda: self.tab_manager.create_tab(self.settings.get("new_tab_url", "crux://startpage")))

            # Container Submenu
            from config import CONTAINERS
            cont_menu = menu.addMenu(t("new_container_tab"))
            for ck, cinfo in CONTAINERS.items():
                badge = cinfo.get("badge", ck.upper())
                name = cinfo.get("name", ck.capitalize())
                act_c = cont_menu.addAction(f"[{badge}] {name}")
                act_c.triggered.connect(lambda checked, c_id=ck: self.tab_manager.create_tab("crux://startpage", container_id=c_id))

            act_new_win = menu.addAction(t("new_window"))
            act_new_win.triggered.connect(self._open_new_window)

            act_incog = menu.addAction(t("incognito_window"))
            act_incog.triggered.connect(self._open_incognito_window)

            # View & Tools
            menu.addSeparator()
            act_find = menu.addAction(t("find_in_page"))
            act_find.triggered.connect(self._toggle_find_in_page)

            act_split = menu.addAction(f"{t('split_view')} (Ctrl+\\)")
            act_split.triggered.connect(lambda: self.tab_manager.split_active_tab())

            act_tasks = menu.addAction(t("task_manager"))
            act_tasks.triggered.connect(lambda: self.tab_manager.create_tab("crux://tasks"))

            act_devtools = menu.addAction(t("devtools"))
            act_devtools.triggered.connect(self._toggle_devtools)

            act_snooze_others = menu.addAction(t("snooze_background_tabs"))
            act_snooze_others.triggered.connect(lambda: self._handle_command_action("snooze_others", ""))

            act_wake_all = menu.addAction(t("wake_all_tabs"))
            act_wake_all.triggered.connect(lambda: self._handle_command_action("wake_all", ""))

            # Data & Panels
            menu.addSeparator()
            act_dl = menu.addAction(t("downloads_menu"))
            act_dl.triggered.connect(self._toggle_downloads)

            act_hist = menu.addAction(t("history_menu"))
            act_hist.triggered.connect(self._open_full_history)

            act_bm = menu.addAction(t("bookmarks_menu"))
            act_bm.triggered.connect(self._toggle_bookmarks_panel)

            act_ai = menu.addAction(t("ai_assistant_menu"))
            act_ai.triggered.connect(self._toggle_sidebar)

            act_adblock = menu.addAction(t("adblock_menu_count", count=getattr(self.adblocker, "blocked_count", 0)))
            act_adblock.triggered.connect(self._show_adblock_menu)

            # Pin to Toolbar Submenu
            pin_menu = menu.addMenu(t("pin_toolbar_menu"))
            pinned_list = self.settings.get("pinned_toolbar", ["downloads", "history"])
            pin_options = [
                ("downloads", t("pin_opt_downloads")),
                ("history", t("pin_opt_history")),
                ("bookmarks", t("pin_opt_bookmarks")),
                ("reader", t("pin_opt_reader")),
                ("split", t("pin_opt_split")),
                ("ai", t("pin_opt_ai")),
            ]
            for opt_key, opt_label in pin_options:
                is_p = (opt_key in pinned_list)
                pref = "[x] " if is_p else "    "
                act_p = pin_menu.addAction(pref + opt_label)
                act_p.triggered.connect(lambda checked, k=opt_key: self.toggle_pin_action(k))

            # Settings
            menu.addSeparator()
            act_settings = menu.addAction(t("browser_settings_menu"))
            act_settings.triggered.connect(self.open_settings)

            btn = getattr(self, "btn_menu", getattr(self, "btn_settings", None))
            self._exec_menu_anchored(menu, btn)
        except Exception:
            import traceback
            traceback.print_exc()

    def _open_full_history(self) -> None:
        self.tab_manager.create_tab("default", "crux://history")

    def _toggle_bookmarks_panel(self) -> None:
        self._show_bookmarks_menu()

    def _open_command_palette(self) -> None:
        if hasattr(self, "command_palette"):
            self.command_palette.show_palette()

    def switch_ui_mode(self, mode: str) -> None:
        self.apply_mode(mode)

    def _show_bookmarks_menu(self) -> None:
        try:
            from PyQt6.QtWidgets import QMenu
            from PyQt6.QtCore import QPoint
            from PyQt6.QtGui import QCursor
            from utils.bookmarks import DataStore

            bm_menu = QMenu(self)
            bm_menu.setStyleSheet("""
                QMenu {
                    background-color: #18181b;
                    border: 1px solid #3f3f46;
                    color: #d4d4d8;
                    font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace;
                    font-size: 12px;
                    padding: 6px;
                }
                QMenu::item {
                    padding: 6px 20px 6px 14px;
                }
                QMenu::item:selected {
                    background-color: #27272a;
                    color: #a855f7;
                }
                QMenu::separator {
                    height: 1px;
                    background: #27272a;
                    margin: 4px 6px;
                }
            """)

            act_add = bm_menu.addAction(t("add_bookmark"))
            v = self.tab_manager.get_current_view()
            if v:
                act_add.triggered.connect(self._add_current_page_to_bookmarks)
            else:
                act_add.setEnabled(False)

            bm_menu.addSeparator()

            bms = DataStore.load_bookmarks()
            if bms:
                for bm in bms[:20]:
                    title = bm.get("title", "") or bm.get("url", "")
                    url = bm.get("url", "")
                    display = (title[:36] + "...") if len(title) > 36 else title
                    act = bm_menu.addAction(f"[BM] {display}")
                    act.triggered.connect(lambda checked, u=url: self.tab_manager.create_tab("default", u))
            else:
                act_empty = bm_menu.addAction(t("no_bookmarks"))
                act_empty.setEnabled(False)

            btn = getattr(self, "btn_bookmarks", getattr(self, "btn_menu", None))
            self._exec_menu_anchored(bm_menu, btn)
        except Exception:
            import traceback
            traceback.print_exc()

    def _add_current_page_to_bookmarks(self) -> None:
        try:
            from utils.bookmarks import DataStore
            v = self.tab_manager.get_current_view()
            if v:
                url = v.url().toString()
                title = v.title() or url
                if url and not url.startswith("crux://"):
                    DataStore.add_bookmark(title, url)
                    if hasattr(self, "status_label"):
                        self.status_label.setText(t("bookmark_saved", title=title[:32]))
        except Exception:
            import traceback
            traceback.print_exc()

    def _apply_mobile_mode_to_view(self, view) -> None:
        if not view:
            return
        w = self.vp_width_spin.value() if hasattr(self, "vp_width_spin") else 390
        h = self.vp_height_spin.value() if hasattr(self, "vp_height_spin") else 844
        view.setFixedSize(w, h)
        if view.page() and view.page().profile():
            mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
            view.page().profile().setHttpUserAgent(mobile_ua)

    def _restore_desktop_view(self, view) -> None:
        if not view:
            return
        view.setMinimumSize(0, 0)
        view.setMaximumSize(16777215, 16777215)
        if view.page() and view.page().profile():
            desktop_ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Crux/1.3.6"
            view.page().profile().setHttpUserAgent(desktop_ua)

    def toggle_mobile_mode(self) -> None:
        self.is_mobile_mode = not getattr(self, "is_mobile_mode", False)
        v = self.tab_manager.get_current_view()
        if self.is_mobile_mode:
            if hasattr(self, "viewport_bar"):
                self.viewport_bar.show()
                if hasattr(self, "vp_preset_combo"):
                    self.vp_preset_combo.blockSignals(True)
                    self.vp_preset_combo.setCurrentIndex(1)  # iPhone 15/16 (390 x 844)
                    self.vp_preset_combo.blockSignals(False)
                if hasattr(self, "vp_width_spin"):
                    self.vp_width_spin.blockSignals(True)
                    self.vp_width_spin.setValue(390)
                    self.vp_width_spin.blockSignals(False)
                if hasattr(self, "vp_height_spin"):
                    self.vp_height_spin.blockSignals(True)
                    self.vp_height_spin.setValue(844)
                    self.vp_height_spin.blockSignals(False)
                if hasattr(self, "vp_ua_combo"):
                    self.vp_ua_combo.blockSignals(True)
                    self.vp_ua_combo.setCurrentIndex(1)  # Mobile iPhone Safari UA
                    self.vp_ua_combo.blockSignals(False)
            if v:
                self._apply_mobile_mode_to_view(v)
                v.reload()
            if hasattr(self, "status_label"):
                self.status_label.setText(t("mobile_mode_status_on"))
        else:
            if hasattr(self, "viewport_bar"):
                self.viewport_bar.hide()
                if hasattr(self, "vp_preset_combo"):
                    self.vp_preset_combo.blockSignals(True)
                    self.vp_preset_combo.setCurrentIndex(0)
                    self.vp_preset_combo.blockSignals(False)
                if hasattr(self, "vp_ua_combo"):
                    self.vp_ua_combo.blockSignals(True)
                    self.vp_ua_combo.setCurrentIndex(0)
                    self.vp_ua_combo.blockSignals(False)
            if v:
                self._restore_desktop_view(v)
                v.reload()
            if hasattr(self, "status_label"):
                self.status_label.setText(t("mobile_mode_status_off"))

    def open_settings(self, tab: str = "") -> None:
        target_url = "crux://settings"
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
        apply_app_theme(QApplication.instance(), settings.get("theme", "dark"), settings.get("accent_color", "#a855f7"))
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
            try:
                sb_w = int(settings["sidebar_width"])
                if hasattr(self.tab_manager.sidebar, "set_expanded_width"):
                    self.tab_manager.sidebar.set_expanded_width(sb_w)
                elif not getattr(self.tab_manager.sidebar, "is_compact", False):
                    self.tab_manager.sidebar.setFixedWidth(sb_w)
            except Exception:
                pass
        if hasattr(self, "side_panel") and hasattr(self.side_panel, "ai_widget"):
            self.side_panel.ai_widget.reload_settings()
        self.status_label.setText(t("settings_saved_msg"))

    # --- RESPONSIVE VIEWPORT & DEVELOPER TOOLS ---
    def _init_viewport_bar(self) -> None:
        self.viewport_bar = QWidget()
        self.viewport_bar.setFixedHeight(34)
        th = self.settings.get("theme", "dark")
        acc = self.settings.get("accent_color", "#a855f7")
        bar_bg = "#18181b" if th == "dark" else "#e2e8f0"
        bar_fg = "#d4d4d8" if th == "dark" else "#1e293b"
        self.viewport_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {bar_bg};
                border-bottom: 1px solid #27272a;
            }}
            QLabel {{
                color: {bar_fg};
                font-size: 11px;
                font-weight: bold;
                font-family: monospace;
            }}
            QComboBox, QSpinBox {{
                background-color: #27272a;
                border: 1px solid #3f3f46;
                color: #f4f4f5;
                font-size: 11px;
                font-family: monospace;
                padding: 1px 4px;
                border-radius: 3px;
            }}
            QPushButton {{
                background-color: #27272a;
                border: 1px solid #3f3f46;
                color: #d4d4d8;
                font-size: 11px;
                font-family: monospace;
                padding: 2px 6px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: #a855f7;
                color: #ffffff;
                border-color: #c084fc;
            }}
        """)
        vb_layout = QHBoxLayout(self.viewport_bar)
        vb_layout.setContentsMargins(8, 2, 8, 2)
        vb_layout.setSpacing(6)

        title = QLabel("Viewport:")
        vb_layout.addWidget(title)

        self.vp_preset_combo = QComboBox()
        self.vp_preset_combo.addItems([
            "Responsive (100%)",
            "iPhone 15/16 (390 x 844)",
            "Google Pixel 8 (412 x 915)",
            "iPad Pro 11\" (834 x 1194)",
            "Laptop (1366 x 768)",
            "Desktop FHD (1920 x 1080)",
        ])
        self.vp_preset_combo.currentIndexChanged.connect(self._on_viewport_preset_changed)
        vb_layout.addWidget(self.vp_preset_combo)

        vb_layout.addWidget(QLabel("W:"))
        self.vp_width_spin = QSpinBox()
        self.vp_width_spin.setRange(320, 3840)
        self.vp_width_spin.setValue(390)
        self.vp_width_spin.valueChanged.connect(self._on_viewport_custom_size)
        vb_layout.addWidget(self.vp_width_spin)

        vb_layout.addWidget(QLabel("H:"))
        self.vp_height_spin = QSpinBox()
        self.vp_height_spin.setRange(320, 2160)
        self.vp_height_spin.setValue(844)
        self.vp_height_spin.valueChanged.connect(self._on_viewport_custom_size)
        vb_layout.addWidget(self.vp_height_spin)

        btn_rotate = QPushButton("Rotate")
        btn_rotate.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rotate.setToolTip("Rotate orientation (swap width and height)")
        btn_rotate.clicked.connect(self._rotate_viewport)
        vb_layout.addWidget(btn_rotate)

        vb_layout.addWidget(QLabel("UA:"))
        self.vp_ua_combo = QComboBox()
        self.vp_ua_combo.addItems([
            "Default UA",
            "Mobile (iPhone Safari)",
            "Mobile (Android Chrome)",
            "Desktop (Chrome)",
        ])
        self.vp_ua_combo.currentIndexChanged.connect(self._on_viewport_ua_changed)
        vb_layout.addWidget(self.vp_ua_combo)

        vb_layout.addStretch()

        btn_close_vp = QPushButton(Icons.CLOSE)
        btn_close_vp.setFixedSize(20, 20)
        btn_close_vp.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close_vp.clicked.connect(self._toggle_viewport_bar)
        vb_layout.addWidget(btn_close_vp)

        self.viewport_bar.hide()

    def _toggle_viewport_bar(self) -> None:
        self.toggle_mobile_mode()

    def _rotate_viewport(self) -> None:
        w = self.vp_width_spin.value()
        h = self.vp_height_spin.value()
        self.vp_width_spin.blockSignals(True)
        self.vp_height_spin.blockSignals(True)
        self.vp_width_spin.setValue(h)
        self.vp_height_spin.setValue(w)
        self.vp_width_spin.blockSignals(False)
        self.vp_height_spin.blockSignals(False)
        self._set_viewport_size(h, w)

    def _on_viewport_preset_changed(self, index: int) -> None:
        presets = [
            (0, 0),         # Responsive (auto)
            (390, 844),     # iPhone
            (412, 915),     # Pixel
            (834, 1194),    # iPad
            (1366, 768),    # Laptop
            (1920, 1080),   # FHD
        ]
        if 0 <= index < len(presets):
            w, h = presets[index]
            if w == 0 and h == 0:
                self.is_mobile_mode = False
                v = self.tab_manager.get_current_view()
                self._restore_desktop_view(v)
                if hasattr(self, "vp_ua_combo"):
                    self.vp_ua_combo.blockSignals(True)
                    self.vp_ua_combo.setCurrentIndex(0)
                    self.vp_ua_combo.blockSignals(False)
                if v:
                    v.reload()
            else:
                self.is_mobile_mode = True
                self.vp_width_spin.blockSignals(True)
                self.vp_height_spin.blockSignals(True)
                self.vp_width_spin.setValue(w)
                self.vp_height_spin.setValue(h)
                self.vp_width_spin.blockSignals(False)
                self.vp_height_spin.blockSignals(False)
                self._set_viewport_size(w, h)
                if index in (1, 2) and hasattr(self, "vp_ua_combo"):
                    self.vp_ua_combo.blockSignals(True)
                    self.vp_ua_combo.setCurrentIndex(index)
                    self.vp_ua_combo.blockSignals(False)
                    self._on_viewport_ua_changed(index)

    def _on_viewport_custom_size(self) -> None:
        w = self.vp_width_spin.value()
        h = self.vp_height_spin.value()
        self._set_viewport_size(w, h)

    def _set_viewport_size(self, w: int, h: int) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            if w <= 0 or h <= 0:
                v.setMaximumSize(16777215, 16777215)
                v.setMinimumSize(0, 0)
            else:
                v.setFixedSize(w, h)

    def _reset_viewport_size(self) -> None:
        v = self.tab_manager.get_current_view()
        if v:
            v.setMaximumSize(16777215, 16777215)
            v.setMinimumSize(0, 0)

    def _on_viewport_ua_changed(self, index: int) -> None:
        ua_map = {
            0: "",
            1: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            2: "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
            3: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
        target_ua = ua_map.get(index, "")
        v = self.tab_manager.get_current_view()
        if v and v.page():
            prof = v.page().profile()
            if prof:
                if target_ua:
                    prof.setHttpUserAgent(target_ua)
                else:
                    prof.setHttpUserAgent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Crux/1.3.6")
                v.reload()

    def _init_devtools_dock(self) -> None:
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        from PyQt6.QtGui import QColor
        self.devtools_dock = QWidget()
        self.devtools_dock.setMinimumHeight(120)
        self.devtools_dock.setStyleSheet("background: #18181b;")
        dt_layout = QVBoxLayout(self.devtools_dock)
        dt_layout.setContentsMargins(0, 0, 0, 0)
        dt_layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(28)
        header.setStyleSheet("background: #18181b; border-top: 1px solid #3f3f46; border-bottom: 1px solid #27272a;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(8, 0, 8, 0)

        self.devtools_title = QLabel("DevTools (Chromium Inspector)")
        self.devtools_title.setStyleSheet("color: #a855f7; font-weight: bold; font-size: 11px; font-family: monospace;")
        h_layout.addWidget(self.devtools_title)
        h_layout.addStretch()

        btn_close_dt = QPushButton(Icons.CLOSE)
        btn_close_dt.setFixedSize(22, 22)
        btn_close_dt.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close_dt.setStyleSheet("""
            QPushButton {
                border: 1px solid #3f3f46;
                color: #a1a1aa;
                font-weight: bold;
                font-size: 11px;
                background: #262624;
                border-radius: 0px;
            }
            QPushButton:hover {
                color: #ffffff;
                background: #ef4444;
                border-color: #ef4444;
            }
        """)
        btn_close_dt.clicked.connect(self.close_devtools)
        h_layout.addWidget(btn_close_dt)

        dt_layout.addWidget(header)
        self.devtools_view = QWebEngineView()
        self.devtools_view.page().setBackgroundColor(QColor("#18181b"))
        self.devtools_view.loadFinished.connect(self._apply_devtools_theme)
        dt_layout.addWidget(self.devtools_view)
        self.devtools_dock.hide()

    def _apply_devtools_theme(self, ok: bool) -> None:
        js = """
        (function() {
            try {
                if (window.Common && window.Common.settings) {
                    window.Common.settings.createSetting('uiTheme', 'dark').set('dark');
                }
            } catch(e) {}
            try {
                if (window.DevToolsAPI && DevToolsAPI.setPreference) {
                    DevToolsAPI.setPreference('uiTheme', '"dark"');
                }
            } catch(e) {}
        })();
        """
        if self.devtools_view and self.devtools_view.page():
            self.devtools_view.page().runJavaScript(js)

    def open_devtools(self, inspect: bool = False) -> None:
        v = self.tab_manager.get_current_view()
        if not v or not v.page():
            return
        v.page().setDevToolsPage(self.devtools_view.page())
        host = v.url().host() or "Local Page"
        self.devtools_title.setText(f"DevTools — {host}")
        self.devtools_dock.show()
        if hasattr(self, "main_vertical_splitter"):
            total_h = self.main_vertical_splitter.height() or 800
            dt_h = max(240, int(total_h * 0.35))
            self.main_vertical_splitter.setSizes([total_h - dt_h, dt_h])
        if inspect:
            from PyQt6.QtWebEngineCore import QWebEnginePage
            v.triggerPageAction(QWebEnginePage.WebAction.InspectElement)

    def close_devtools(self) -> None:
        self.devtools_dock.hide()
        v = self.tab_manager.get_current_view()
        if v and v.page():
            v.page().setDevToolsPage(None)

    def _toggle_devtools(self) -> None:
        if self.devtools_dock.isVisible():
            self.close_devtools()
        else:
            self.open_devtools()

    # --- VIM MODE SUPPORT ---
    def keyPressEvent(self, event: QKeyEvent):
        # Fullscreen Escape and F11 handling
        if getattr(self, "is_fullscreen_active", False) or self.isFullScreen():
            if event.key() == Qt.Key.Key_Escape:
                v = self.tab_manager.get_current_view()
                if v and hasattr(v, "page"):
                    from PyQt6.QtWebEngineCore import QWebEnginePage
                    v.page().triggerAction(QWebEnginePage.WebAction.ExitFullScreen)
                self.handle_fullscreen_request(False)
                return
            elif event.key() == Qt.Key.Key_F11:
                self.handle_fullscreen_request(not self.is_fullscreen_active)
                return

        if event.key() == Qt.Key.Key_F11:
            self.handle_fullscreen_request(not getattr(self, "is_fullscreen_active", False))
            return

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
