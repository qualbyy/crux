"""
Custom QWebEngineView for Zinc Browser
Handles zoom, custom context menus, zinc:// internal schemes, status reporting,
URL cleaner, and Copy as cURL.
"""
from pathlib import Path
from PyQt6.QtCore import pyqtSignal, QUrl, Qt
from PyQt6.QtWidgets import QMenu, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from config import DEFAULT_HOME_URL
from core.adblock import clean_tracking_parameters

STARTPAGE_PATH = Path(__file__).resolve().parent.parent / "resources" / "startpage.html"
WELCOME_PATH = Path(__file__).resolve().parent.parent / "resources" / "welcome.html"
SETTINGS_PATH = Path(__file__).resolve().parent.parent / "resources" / "settings.html"
HISTORY_PATH = Path(__file__).resolve().parent.parent / "resources" / "history.html"
DOWNLOADS_PATH = Path(__file__).resolve().parent.parent / "resources" / "downloads.html"

class ZincWebPage(QWebEnginePage):
    link_hovered = pyqtSignal(str)

    def __init__(self, profile: QWebEngineProfile, parent=None):
        super().__init__(profile, parent)
        self._view = parent

    def view(self):
        return self._view or self.parent()

    def acceptNavigationRequest(self, url: QUrl, _type: QWebEnginePage.NavigationType, isMainFrame: bool) -> bool:
        try:
            url_str = url.toString()
            if url_str.startswith("zephyrium://") or url_str.startswith("zinc://"):
                from PyQt6.QtCore import QTimer
                v = self.view()
                if v and hasattr(v, "navigate"):
                    QTimer.singleShot(0, lambda u=url_str: v.navigate(u))
                return False
            return super().acceptNavigationRequest(url, _type, isMainFrame)
        except Exception as e:
            print(f"Error in acceptNavigationRequest: {e}")
            return False

    def createWindow(self, _type: QWebEnginePage.WebWindowType) -> QWebEnginePage:
        try:
            v = self.view()
            if v:
                win = v._get_main_window()
                if win and hasattr(win, "tab_manager"):
                    new_tab_id = win.tab_manager.create_tab()
                    new_view = win.tab_manager.get_tab_view(new_tab_id)
                    if new_view:
                        return new_view.page()
        except Exception as e:
            print(f"Error in createWindow: {e}")
        return super().createWindow(_type)


class ZincWebView(QWebEngineView):
    status_message = pyqtSignal(str)
    open_split_requested = pyqtSignal(QUrl)
    open_new_tab_requested = pyqtSignal(QUrl)
    ask_ai_selection = pyqtSignal(str)

    def __init__(self, profile: QWebEngineProfile, container_id: str = "default", parent=None):
        super().__init__(parent)
        self.container_id = container_id
        self._profile = profile
        self._custom_page = ZincWebPage(profile, self)
        self.setPage(self._custom_page)

        # Connect page hover
        self.page().linkHovered.connect(self._on_link_hovered)

        # Context menu policy
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

        # Zoom level tracker
        self._zoom = 1.0

        # Sync page background color to avoid white flash
        from config import load_settings
        from PyQt6.QtGui import QColor
        s = load_settings()
        th = s.get("theme", "dark")
        self.page().setBackgroundColor(QColor("#18181b" if th == "dark" else "#f8fafc"))

        # Password and Credential Autofill on page load
        self.loadFinished.connect(self._on_page_load_finished)

    def _on_page_load_finished(self, success: bool) -> None:
        if not success:
            return
        import json
        u = self.url().toString()
        if "settings.html" in u:
            try:
                from config import load_settings, CONFIG_DIR
                s = load_settings()
                win = self._get_main_window()
                wl = list(win.adblocker.whitelist) if hasattr(win, "adblocker") else []
                
                pw_file = CONFIG_DIR / "passwords.json"
                ck_file = CONFIG_DIR / "cookies.json"
                passwords = []
                cookies = []
                if pw_file.exists():
                    try:
                        with open(pw_file, "r", encoding="utf-8") as f:
                            passwords = json.load(f)
                    except Exception:
                        passwords = []
                if ck_file.exists():
                    try:
                        with open(ck_file, "r", encoding="utf-8") as f:
                            cookies = json.load(f)
                    except Exception:
                        cookies = []

                payload = json.dumps({"settings": s, "whitelist": wl, "passwords": passwords, "cookies": cookies})
                self.page().runJavaScript(f"if (window.initSettings) window.initSettings({payload});")
            except Exception as e:
                print(f"[Settings Init Error] {e}")
            return
        if "history.html" in u:
            try:
                from utils.bookmarks import DataStore
                from config import load_settings
                s = load_settings()
                lang = s.get("language", "ru")
                items = json.dumps(DataStore.load_history())
                self.page().runJavaScript(f"if (window.applyLanguage) window.applyLanguage('{lang}'); if (window.renderHistory) window.renderHistory({items});")
            except Exception as e:
                print(f"[History Init Error] {e}")
            return
        if "downloads.html" in u:
            try:
                from utils.bookmarks import DataStore
                from config import load_settings
                s = load_settings()
                lang = s.get("language", "ru")
                items = json.dumps(DataStore.load_downloads())
                self.page().runJavaScript(f"if (window.applyLanguage) window.applyLanguage('{lang}'); if (window.renderDownloads) window.renderDownloads({items});")
            except Exception as e:
                print(f"[Downloads Init Error] {e}")
            return

        if not u or u.startswith("zephyrium://") or u.startswith("zinc://") or u.startswith("about:"):
            return
        try:
            from core.password_autofill import PasswordAutofillManager
            matches = PasswordAutofillManager.get_matches_for_url(u)
            if matches:
                js = PasswordAutofillManager.generate_injection_js(matches)
                if js:
                    self.page().runJavaScript(js)
        except Exception as e:
            print(f"[Autofill Error] {e}")

    def navigate(self, url_input: str) -> None:
        url_clean = url_input.strip()
        if not url_clean:
            return

        import urllib.parse
        from config import load_settings
        from PyQt6.QtGui import QColor

        s = load_settings()
        th = s.get("theme", "dark")
        acc = s.get("accent_color", "#fe8019")
        lang = s.get("language", "ru")
        self.page().setBackgroundColor(QColor("#18181b" if th == "dark" else "#f8fafc"))

        if url_clean in ["zephyrium://startpage", "zinc://startpage", "about:blank"]:
            u = QUrl.fromLocalFile(str(STARTPAGE_PATH))
            u.setQuery(f"theme={th}&accent={urllib.parse.quote(acc)}&lang={lang}")
            self.load(u)
            return

        if url_clean in ["zephyrium://welcome", "zinc://welcome"]:
            win = self._get_main_window()
            if win and hasattr(win, "show_onboarding"):
                win.show_onboarding()
            else:
                self.load(QUrl.fromLocalFile(str(STARTPAGE_PATH)))
            return

        if url_clean.startswith("zephyrium://setup") or url_clean.startswith("zinc://setup"):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._apply_setup(url_clean))
            return

        if url_clean.startswith("zephyrium://live-setting") or url_clean.startswith("zinc://live-setting"):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._apply_live_setting(url_clean))
            return

        if url_clean.startswith("zephyrium://apply-settings") or url_clean.startswith("zinc://apply-settings"):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._apply_settings_from_url(url_clean))
            return

        if url_clean.startswith("zephyrium://action/") or url_clean.startswith("zinc://action/"):
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(0, lambda: self._handle_action(url_clean))
            return

        if url_clean.startswith("zephyrium://settings") or url_clean.startswith("zinc://settings") or url_clean in ["about:settings", "about:preferences"]:
            parsed = urllib.parse.urlparse(url_clean)
            qs = urllib.parse.parse_qs(parsed.query)
            tab = qs.get("tab", [""])[0]
            u = QUrl.fromLocalFile(str(SETTINGS_PATH))
            query_str = f"theme={th}&accent={urllib.parse.quote(acc)}&lang={lang}"
            if tab:
                query_str += f"&tab={urllib.parse.quote(tab)}"
            u.setQuery(query_str)
            self.load(u)
            return

        if url_clean.startswith("zephyrium://history") or url_clean.startswith("zinc://history") or url_clean in ["about:history"]:
            u = QUrl.fromLocalFile(str(HISTORY_PATH))
            u.setQuery(f"theme={th}&accent={urllib.parse.quote(acc)}&lang={lang}")
            self.load(u)
            return

        if url_clean.startswith("zephyrium://downloads") or url_clean.startswith("zinc://downloads") or url_clean in ["about:downloads"]:
            u = QUrl.fromLocalFile(str(DOWNLOADS_PATH))
            u.setQuery(f"theme={th}&accent={urllib.parse.quote(acc)}&lang={lang}")
            self.load(u)
            return

        if url_clean in ["zephyrium://about", "zinc://about", "about:about"]:
            u = QUrl.fromLocalFile(str(SETTINGS_PATH))
            u.setQuery(f"theme={th}&accent={urllib.parse.quote(acc)}&tab=about&lang={lang}")
            self.load(u)
            return

        if url_clean in ["zephyrium://vault", "zinc://vault"]:
            u = QUrl.fromLocalFile(str(SETTINGS_PATH))
            u.setQuery(f"theme={th}&accent={urllib.parse.quote(acc)}&tab=vault&lang={lang}")
            self.load(u)
            return

        if url_clean.startswith("zephyrium://new-tab") or url_clean.startswith("zinc://new-tab") or url_clean.startswith("zephyrium://open-tab"):
            try:
                parsed = urllib.parse.urlparse(url_clean)
                qs = urllib.parse.parse_qs(parsed.query)
                target = qs.get("url", [""])[0]
                win = self._get_main_window()
                if win and hasattr(win, "tab_manager"):
                    win.tab_manager.create_tab(url=target or "zephyrium://startpage")
            except Exception as e:
                print(f"Error handling new-tab navigation: {e}")
            return

        if url_clean.startswith("http://") or url_clean.startswith("https://") or url_clean.startswith("file://"):
            # Clean tracking tags automatically
            cleaned = clean_tracking_parameters(url_clean)
            self.load(QUrl(cleaned))
        elif "." in url_clean and " " not in url_clean:
            cleaned = clean_tracking_parameters("https://" + url_clean)
            self.load(QUrl(cleaned))
        else:
            # Search query via DuckDuckGo
            from config import SEARCH_ENGINE_URL
            self.load(QUrl(SEARCH_ENGINE_URL.format(query=QUrl.toPercentEncoding(url_clean).data().decode())))

    def _get_main_window(self):
        win = self.window()
        if hasattr(win, "set_tab_orientation"):
            return win
        for w in QApplication.topLevelWidgets():
            if hasattr(w, "set_tab_orientation"):
                return w
        return win

    def _apply_setup(self, url_clean: str) -> None:
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url_clean)
            params = urllib.parse.parse_qs(parsed.query)
            from config import load_settings, save_settings
            s = load_settings()
            if "theme" in params:
                s["theme"] = params["theme"][0]
            if "accent" in params:
                s["accent_color"] = params["accent"][0]
            if "mode" in params:
                s["ui_mode"] = params["mode"][0]
            if "orientation" in params:
                s["tab_orientation"] = params["orientation"][0]
            if "api_key" in params and params["api_key"][0]:
                s["gemini_api_key"] = params["api_key"][0]
            s["first_run"] = False
            save_settings(s)

            # Apply theme dynamically
            from core.theme_manager import apply_app_theme
            apply_app_theme(QApplication.instance(), s.get("theme", "dark"), s.get("accent_color", "#fe8019"))

            win = self._get_main_window()
            if win:
                if hasattr(win, "set_tab_orientation") and "orientation" in params:
                    win.set_tab_orientation(s["tab_orientation"])
                if hasattr(win, "apply_mode") and "mode" in params:
                    win.apply_mode(s["ui_mode"])
                if hasattr(win, "side_panel") and hasattr(win.side_panel, "ai_widget"):
                    win.side_panel.ai_widget.reload_settings()
        except Exception as e:
            print(f"Error applying setup: {e}")
        finally:
            self.load(QUrl.fromLocalFile(str(STARTPAGE_PATH)))

    def _apply_live_setting(self, url_str: str) -> None:
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url_str)
            qs = urllib.parse.parse_qs(parsed.query)
            key = qs.get("key", [""])[0]
            val = qs.get("value", [""])[0]
            if not key:
                return

            from config import load_settings, save_settings
            s = load_settings()

            if key in ["adblock_enabled", "clean_urls", "send_dnt", "prevent_webrtc_leak", "restore_session"]:
                s[key] = val.lower() in ["true", "1"]
            elif key in ["sidebar_width", "font_size"]:
                try:
                    s[key] = int(val)
                except Exception:
                    pass
            else:
                s[key] = val

            save_settings(s)

            win = self._get_main_window()
            if win:
                win.settings = s
                if key in ["theme", "accent_color"]:
                    th = s.get("theme", "dark")
                    acc = s.get("accent_color", "#fe8019")
                    from core.theme_manager import apply_app_theme
                    apply_app_theme(QApplication.instance(), th, acc)
                    if hasattr(win, "_apply_theme_style"):
                        win._apply_theme_style(getattr(win, "ui_mode", "minimal"))
                    if hasattr(win, "_reload_startpages"):
                        win._reload_startpages()
                elif key == "language":
                    from core.i18n import set_language
                    set_language(val)
                    if hasattr(win, "retranslate_ui"):
                        win.retranslate_ui()
                    if hasattr(win, "_reload_startpages"):
                        win._reload_startpages()
                elif key == "ui_mode":
                    if hasattr(win, "apply_mode"):
                        win.apply_mode(val)
                elif key == "tab_orientation":
                    if hasattr(win, "set_tab_orientation"):
                        win.set_tab_orientation(val)
                elif key == "sidebar_width":
                    if hasattr(win, "tab_manager") and hasattr(win.tab_manager, "sidebar"):
                        win.tab_manager.sidebar.setFixedWidth(s.get("sidebar_width", 240))
                elif key == "adblock_enabled":
                    if hasattr(win, "adblocker"):
                        win.adblocker.enabled = s.get("adblock_enabled", True)
                        if hasattr(win, "btn_adblock"):
                            win.btn_adblock.setText(f"{t('adblock_title')}: {win.adblocker.blocked_count}")
        except Exception as e:
            print(f"Error applying live setting: {e}")

    def _apply_settings_from_url(self, url_str: str) -> None:
        try:
            import urllib.parse
            parsed = urllib.parse.urlparse(url_str)
            params = urllib.parse.parse_qs(parsed.query)
            from config import load_settings, save_settings
            s = load_settings()

            if "language" in params:
                s["language"] = params["language"][0]
            if "homepage" in params:
                s["homepage"] = params["homepage"][0]
            if "theme" in params:
                s["theme"] = params["theme"][0]
            if "accent_color" in params:
                s["accent_color"] = params["accent_color"][0]
            if "ui_mode" in params:
                s["ui_mode"] = params["ui_mode"][0]
            if "tab_orientation" in params:
                s["tab_orientation"] = params["tab_orientation"][0]
            if "sidebar_width" in params:
                try:
                    s["sidebar_width"] = int(params["sidebar_width"][0])
                except Exception:
                    pass
            if "adblock_enabled" in params:
                s["adblock_enabled"] = params["adblock_enabled"][0].lower() in ["true", "1"]
            if "clean_urls" in params:
                s["clean_urls"] = params["clean_urls"][0].lower() in ["true", "1"]
            if "send_dnt" in params:
                s["send_dnt"] = params["send_dnt"][0].lower() in ["true", "1"]
            if "prevent_webrtc_leak" in params:
                s["prevent_webrtc_leak"] = params["prevent_webrtc_leak"][0].lower() in ["true", "1"]
            if "download_dir" in params:
                s["download_dir"] = params["download_dir"][0]
            if "gemini_api_key" in params:
                s["gemini_api_key"] = params["gemini_api_key"][0]
            if "ai_model" in params:
                s["ai_model"] = params["ai_model"][0]
            if "ai_persona" in params:
                s["ai_persona"] = params["ai_persona"][0]
            if "restore_session" in params:
                s["restore_session"] = params["restore_session"][0].lower() in ["true", "1"]

            save_settings(s)

            win = self._get_main_window()
            if win:
                if "whitelist" in params and hasattr(win, "adblocker"):
                    wl_raw = params["whitelist"][0]
                    new_wl = set(d.strip() for d in wl_raw.split(",") if d.strip())
                    win.adblocker.whitelist = new_wl
                    win.adblocker.save_whitelist()

                if hasattr(win, "_on_settings_saved"):
                    win._on_settings_saved(s)
        except Exception as e:
            print(f"Error applying settings from URL: {e}")

    def _handle_action(self, url_str: str) -> None:
        try:
            import os
            import urllib.parse
            parsed = urllib.parse.urlparse(url_str)
            action = parsed.path.lstrip("/")
            qs = urllib.parse.parse_qs(parsed.query)

            if action == "clear-history":
                from utils.bookmarks import DataStore
                DataStore.clear_history()
                self.navigate("zephyrium://history")
            elif action == "delete-history":
                from utils.bookmarks import DataStore
                url_to_del = qs.get("url", [""])[0]
                if url_to_del:
                    DataStore.delete_history_item(urllib.parse.unquote(url_to_del))
                self.navigate("zephyrium://history")
            elif action == "clear-downloads":
                from utils.bookmarks import DataStore
                DataStore.clear_downloads()
                self.navigate("zephyrium://downloads")
            elif action == "open-downloads-folder":
                from config import load_settings
                from PyQt6.QtGui import QDesktopServices
                s = load_settings()
                ddir = s.get("download_dir", str(Path.home() / "Downloads"))
                QDesktopServices.openUrl(QUrl.fromLocalFile(ddir))
            elif action == "open-file":
                import subprocess
                fpath = qs.get("path", [""])[0]
                if fpath:
                    unquoted = urllib.parse.unquote(fpath)
                    if os.path.exists(unquoted):
                        subprocess.Popen(["xdg-open", unquoted])
            elif action == "delete-password":
                from config import CONFIG_DIR
                import json
                domain = qs.get("domain", [""])[0]
                username = qs.get("username", [""])[0]
                pw_file = CONFIG_DIR / "passwords.json"
                if pw_file.exists():
                    try:
                        with open(pw_file, "r", encoding="utf-8") as f:
                            pwds = json.load(f)
                        pwds = [p for p in pwds if not (p.get("url") == domain and p.get("username") == username)]
                        with open(pw_file, "w", encoding="utf-8") as f:
                            json.dump(pwds, f, indent=2)
                    except Exception as e:
                        print(f"Error deleting password: {e}")
                self.navigate("zephyrium://settings?tab=vault")
            elif action == "delete-cookie":
                from config import CONFIG_DIR
                import json
                host = qs.get("host", [""])[0]
                name = qs.get("name", [""])[0]
                ck_file = CONFIG_DIR / "cookies.json"
                if ck_file.exists():
                    try:
                        with open(ck_file, "r", encoding="utf-8") as f:
                            cks = json.load(f)
                        cks = [c for c in cks if not (c.get("host") == host and c.get("name") == name)]
                        with open(ck_file, "w", encoding="utf-8") as f:
                            json.dump(cks, f, indent=2)
                    except Exception as e:
                        print(f"Error deleting cookie: {e}")
                self.navigate("zephyrium://settings?tab=vault")
        except Exception as e:
            print(f"Error handling action: {e}")

    def zoom_in(self) -> float:
        self._zoom = min(3.0, round(self._zoom + 0.1, 2))
        self.setZoomFactor(self._zoom)
        return self._zoom

    def zoom_out(self) -> float:
        self._zoom = max(0.25, round(self._zoom - 0.1, 2))
        self.setZoomFactor(self._zoom)
        return self._zoom

    def zoom_reset(self) -> float:
        self._zoom = 1.0
        self.setZoomFactor(self._zoom)
        return self._zoom

    def get_zoom(self) -> float:
        return self._zoom

    def _on_link_hovered(self, url: str) -> None:
        self.status_message.emit(url)

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        
        # Navigation actions
        act_back = menu.addAction("Back")
        act_back.setEnabled(self.history().canGoBack())
        act_back.triggered.connect(self.back)

        act_fwd = menu.addAction("Forward")
        act_fwd.setEnabled(self.history().canGoForward())
        act_fwd.triggered.connect(self.forward)

        act_reload = menu.addAction("Reload")
        act_reload.triggered.connect(self.reload)

        menu.addSeparator()

        # Selection actions
        selected_text = self.selectedText()
        if selected_text:
            act_ai = menu.addAction(f"Ask Gemini about '{selected_text[:20]}...'")
            act_ai.triggered.connect(lambda: self.ask_ai_selection.emit(selected_text))
            menu.addSeparator()

        # Split view action
        act_split = menu.addAction("Open in Split View")
        act_split.triggered.connect(lambda: self.open_split_requested.emit(self.url()))

        # Copy URL action
        act_copy = menu.addAction("Copy Clean URL")
        act_copy.triggered.connect(lambda: from_pyqt_clipboard(clean_tracking_parameters(self.url().toString())))

        # Copy as cURL
        act_curl = menu.addAction("Copy as cURL")
        act_curl.triggered.connect(self._copy_as_curl)

        menu.addSeparator()

        # DevTools inspection
        act_inspect = menu.addAction("Inspect Element")
        act_inspect.triggered.connect(self._inspect_element)

        menu.exec(self.mapToGlobal(pos))

    def _copy_as_curl(self) -> None:
        u = self.url().toString()
        curl_cmd = f"curl -sL '{u}' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Zephyrium/1.0'"
        from_pyqt_clipboard(curl_cmd)

    def _inspect_element(self) -> None:
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        self.triggerPageAction(QWebEnginePage.WebAction.InspectElement)

def from_pyqt_clipboard(text: str):
    cb = QApplication.clipboard()
    if cb:
        cb.setText(text)
