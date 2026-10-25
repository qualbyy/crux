"""
Custom QWebEngineView for Zephyrium Browser
Handles zoom, custom context menus, zephyrium:// internal schemes via native SchemeHandler,
status reporting, URL cleaner, Reader Mode, PiP, and AI Quick Actions.
"""
from pathlib import Path
import sys
import urllib.parse
from PyQt6.QtCore import pyqtSignal, QUrl, Qt, QBuffer, QIODevice
from PyQt6.QtWidgets import QMenu, QApplication
from PyQt6.QtGui import QAction
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEnginePage, QWebEngineProfile, QWebEngineSettings,
    QWebEngineFullScreenRequest, QWebEngineUrlSchemeHandler,
    QWebEngineUrlRequestJob
)
from config import DEFAULT_HOME_URL
from core.adblock import clean_tracking_parameters

def get_resource_path(filename: str) -> Path:
    # 1. PyInstaller onefile or onedir _MEIPASS
    if hasattr(sys, "_MEIPASS"):
        for cand in [Path(sys._MEIPASS) / "resources" / filename, Path(sys._MEIPASS) / filename]:
            if cand.exists():
                return cand
    # 2. Frozen executable directory (_internal or adjacent)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        for cand in [
            exe_dir / "_internal" / "resources" / filename,
            exe_dir / "resources" / filename,
            exe_dir / filename
        ]:
            if cand.exists():
                return cand
    # 3. Source directory
    base = Path(__file__).resolve().parent.parent
    for cand in [
        base / "resources" / filename,
        base / filename
    ]:
        if cand.exists():
            return cand
    return Path(__file__).resolve().parent.parent / "resources" / filename

STARTPAGE_PATH = get_resource_path("startpage.html")
WELCOME_PATH = get_resource_path("welcome.html")
SETTINGS_PATH = get_resource_path("settings.html")
HISTORY_PATH = get_resource_path("history.html")
DOWNLOADS_PATH = get_resource_path("downloads.html")


class ZephyriumSchemeHandler(QWebEngineUrlSchemeHandler):
    """
    Native URL scheme handler for zephyrium:// and zinc:// internal pages.
    Serves HTML/assets directly through Chromium's network stack without file:// restrictions.
    """
    def requestStarted(self, job: QWebEngineUrlRequestJob) -> None:
        try:
            url = job.requestUrl()
            host = url.host().lower()
            path = url.path().strip("/")
            resource = host or path

            filename = None
            mime = b"text/html; charset=utf-8"

            if resource in ["startpage", "start", "new-tab", "open-tab"]:
                filename = "startpage.html"
            elif resource in ["settings", "preferences", "config", "vault", "about"]:
                filename = "settings.html"
            elif resource in ["history"]:
                filename = "history.html"
            elif resource in ["downloads"]:
                filename = "downloads.html"
            elif resource in ["welcome"]:
                filename = "welcome.html"
            elif resource.endswith(".svg"):
                filename = resource.split("/")[-1]
                mime = b"image/svg+xml"
            elif resource.endswith(".png"):
                filename = resource.split("/")[-1]
                mime = b"image/png"
            elif resource.endswith(".ico"):
                filename = resource.split("/")[-1]
                mime = b"image/x-icon"
            elif resource.endswith(".css"):
                filename = resource.split("/")[-1]
                mime = b"text/css"
            elif resource.endswith(".js"):
                filename = resource.split("/")[-1]
                mime = b"application/javascript"

            if not filename:
                job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
                return

            file_path = get_resource_path(filename)
            if not file_path.exists():
                job.fail(QWebEngineUrlRequestJob.Error.UrlNotFound)
                return

            with open(file_path, "rb") as f:
                content = f.read()

            if mime.startswith(b"text/html"):
                from config import load_settings
                s = load_settings()
                th = s.get("theme", "dark")
                acc = s.get("accent_color", "#fe8019")
                lang = s.get("language", "ru")

                tab = ""
                query = url.query()
                if query:
                    qs = urllib.parse.parse_qs(query)
                    if "tab" in qs:
                        tab = qs["tab"][0]
                if resource in ["vault", "about"]:
                    tab = resource

                inject_js = f"""
                <script>
                    window.ZEPHYRIUM_THEME = "{th}";
                    window.ZEPHYRIUM_ACCENT = "{acc}";
                    window.ZEPHYRIUM_LANG = "{lang}";
                    window.ZEPHYRIUM_TAB = "{tab}";
                    try {{
                        if (!window.location.search) {{
                            let _q = [];
                            if ('{th}') _q.push('theme=' + encodeURIComponent('{th}'));
                            if ('{acc}') _q.push('accent=' + encodeURIComponent('{acc}'));
                            if ('{lang}') _q.push('lang=' + encodeURIComponent('{lang}'));
                            if ('{tab}') _q.push('tab=' + encodeURIComponent('{tab}'));
                            history.replaceState(null, '', '?' + _q.join('&') + window.location.hash);
                        }}
                    }} catch(e) {{}}
                </script>
                """
                content_str = content.decode("utf-8", errors="replace")
                if "<head>" in content_str:
                    content_str = content_str.replace("<head>", f"<head>{inject_js}", 1)
                elif "<html>" in content_str:
                    content_str = content_str.replace("<html>", f"<html><head>{inject_js}</head>", 1)
                else:
                    content_str = inject_js + content_str
                content = content_str.encode("utf-8")

            buf = QBuffer(job)
            buf.setData(content)
            buf.open(QIODevice.OpenModeFlag.ReadOnly)
            job.reply(mime, buf)
        except Exception as e:
            print(f"Error serving zephyrium resource: {e}")
            job.fail(QWebEngineUrlRequestJob.Error.RequestFailed)

class ZincWebPage(QWebEnginePage):
    link_hovered = pyqtSignal(str)

    def __init__(self, profile: QWebEngineProfile, parent=None):
        super().__init__(profile, parent)
        self._view = parent
        self.featurePermissionRequested.connect(self._on_feature_permission_requested)

    def view(self):
        return self._view or self.parent()

    def _on_feature_permission_requested(self, securityOrigin: QUrl, feature: QWebEnginePage.Feature):
        # Auto-grant permissions for Clipboard, Notifications, Audio/Video on secure web apps
        try:
            self.setFeaturePermission(securityOrigin, feature, QWebEnginePage.PermissionPolicy.PermissionGrantedByUser)
        except Exception as e:
            print(f"Error setting feature permission: {e}")

    def javaScriptAlert(self, securityOrigin: QUrl, msg: str) -> None:
        from PyQt6.QtWidgets import QMessageBox
        parent = self.view()
        title = securityOrigin.host() or "Notice"
        QMessageBox.information(parent, title, msg)

    def javaScriptConfirm(self, securityOrigin: QUrl, msg: str) -> bool:
        from PyQt6.QtWidgets import QMessageBox
        parent = self.view()
        title = securityOrigin.host() or "Confirmation"
        res = QMessageBox.question(
            parent,
            title,
            msg,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok
        )
        return res == QMessageBox.StandardButton.Ok

    def chooseFiles(self, mode: QWebEnginePage.FileSelectionMode, oldFiles: list[str], acceptedMimeTypes: list[str]) -> list[str]:
        from PyQt6.QtWidgets import QFileDialog
        parent = self.view()
        try:
            if mode == QWebEnginePage.FileSelectionMode.FileSelectOpenMultiple:
                files, _ = QFileDialog.getOpenFileNames(parent, "Select Files", "", ";;".join(acceptedMimeTypes) if acceptedMimeTypes else "All Files (*)")
                return files or oldFiles
            elif mode == QWebEnginePage.FileSelectionMode.FileSelectOpen:
                f, _ = QFileDialog.getOpenFileName(parent, "Select File", "", ";;".join(acceptedMimeTypes) if acceptedMimeTypes else "All Files (*)")
                return [f] if f else oldFiles
            elif mode == QWebEnginePage.FileSelectionMode.FileSelectUploadFolder:
                folder = QFileDialog.getExistingDirectory(parent, "Select Folder to Upload")
                if folder:
                    import os
                    all_files = []
                    for root, _, filenames in os.walk(folder):
                        for fn in filenames:
                            all_files.append(os.path.join(root, fn))
                    return all_files
                return oldFiles
        except Exception as e:
            print(f"Error in chooseFiles: {e}")
        return super().chooseFiles(mode, oldFiles, acceptedMimeTypes)

    def javaScriptPrompt(self, securityOrigin: QUrl, msg: str, defaultValue: str) -> tuple[bool, str]:
        if msg.startswith("ZEPHYRIUM_CMD:") or msg.startswith("zephyrium:") or msg.startswith("zinc:"):
            cmd = msg[len("ZEPHYRIUM_CMD:"):] if msg.startswith("ZEPHYRIUM_CMD:") else msg
            v = self.view()
            if v and hasattr(v, "handle_host_cmd"):
                v.handle_host_cmd(cmd)
            return True, "ok"
        return super().javaScriptPrompt(securityOrigin, msg, defaultValue)

    def javaScriptConsoleMessage(self, level, message: str, lineNumber: int, sourceID: str):
        if message.startswith("ZEPHYRIUM_IPC:") or message.startswith("zephyrium:") or message.startswith("zinc:"):
            cmd = message[len("ZEPHYRIUM_IPC:"):] if message.startswith("ZEPHYRIUM_IPC:") else message
            v = self.view()
            if v and hasattr(v, "handle_host_cmd"):
                v.handle_host_cmd(cmd)
            return
        super().javaScriptConsoleMessage(level, message, lineNumber, sourceID)

    def acceptNavigationRequest(self, url: QUrl, _type: QWebEnginePage.NavigationType, isMainFrame: bool) -> bool:
        try:
            url_str = url.toString()
            if url_str.startswith("zephyrium://") or url_str.startswith("zinc://"):
                v = self.view()
                if v and hasattr(v, "handle_host_cmd"):
                    # Non-navigating commands / actions should not alter the current page DOM
                    if any(url_str.startswith(p) for p in [
                        "zephyrium://live-setting", "zinc://live-setting",
                        "zephyrium://apply-settings", "zinc://apply-settings",
                        "zephyrium://action/", "zinc://action/",
                        "zephyrium://setup", "zinc://setup"
                    ]):
                        v.handle_host_cmd(url_str)
                        return False
                    # Real page navigation (zephyrium://settings, zephyrium://downloads, etc.)
                    return True
                return True
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
                    # Open blank tab and let the popup caller navigate to its intended destination
                    new_tab_id = win.tab_manager.create_tab(url="about:blank")
                    new_view = win.tab_manager.get_tab_view(new_tab_id)
                    if new_view:
                        win.tab_manager.select_tab(new_tab_id)
                        return new_view.page()
        except Exception as e:
            print(f"Error in createWindow: {e}")
        return super().createWindow(_type)


class ZincWebView(QWebEngineView):
    status_message = pyqtSignal(str)
    open_split_requested = pyqtSignal(QUrl)
    open_new_tab_requested = pyqtSignal(QUrl)
    ask_ai_selection = pyqtSignal(str)
    ask_ai_action = pyqtSignal(str, str)

    def __init__(self, profile: QWebEngineProfile, container_id: str = "default", parent=None):
        super().__init__(parent)
        self.container_id = container_id
        self._profile = profile
        self.is_reader_mode = False
        self.original_url_before_reader = None
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

        # Enable HTML5 FullScreen API for YouTube and video players
        for s_obj in [self.settings(), self.page().settings()]:
            s_obj.setAttribute(QWebEngineSettings.WebAttribute.FullScreenSupportEnabled, True)
            s_obj.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
            s_obj.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
            s_obj.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
            s_obj.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            s_obj.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            s_obj.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)
            s_obj.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
            s_obj.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
            s_obj.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        self.page().fullScreenRequested.connect(self._on_fullscreen_requested)

        # Password and Credential Autofill on page load
        self.loadFinished.connect(self._on_page_load_finished)

    def _on_fullscreen_requested(self, request: QWebEngineFullScreenRequest) -> None:
        toggle_on = request.toggleOn()
        request.accept()
        win = self._get_main_window()
        if win and hasattr(win, "handle_fullscreen_request"):
            win.handle_fullscreen_request(toggle_on)

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
                extensions = win.profile_manager.userscript_manager.list_all() if (win and hasattr(win, "profile_manager")) else {}
                
                ck_file = CONFIG_DIR / "cookies.json"
                passwords = []  # Locked behind sudo authentication
                cookies = []
                if ck_file.exists():
                    try:
                        with open(ck_file, "r", encoding="utf-8") as f:
                            cookies = json.load(f)
                    except Exception:
                        cookies = []

                payload = json.dumps({"settings": s, "whitelist": wl, "passwords": passwords, "cookies": cookies, "extensions": extensions})
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

        # Website theme preference and PiP video overlay injection
        try:
            from config import load_settings
            s = load_settings()
            ws_theme = s.get("website_theme", "light")
            if ws_theme in ["light", "dark"]:
                theme_js = f"""
                (function() {{
                    let meta = document.querySelector('meta[name="color-scheme"]');
                    if (!meta) {{
                        meta = document.createElement('meta');
                        meta.name = 'color-scheme';
                        document.head.appendChild(meta);
                    }}
                    meta.content = '{ws_theme}';
                }})();
                """
                self.page().runJavaScript(theme_js)

            pip_overlay_js = """
            (function() {
                function setupVideoPiP(video) {
                    if (video.__pip_btn_attached) return;
                    video.__pip_btn_attached = true;

                    const btn = document.createElement('button');
                    btn.innerHTML = '⧉ PiP';
                    btn.title = 'Picture-in-Picture';
                    btn.style.cssText = `
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        z-index: 2147483647;
                        background: rgba(24, 24, 27, 0.85);
                        color: #fe8019;
                        border: 1px solid #fe8019;
                        border-radius: 0px;
                        padding: 3px 7px;
                        font-size: 11px;
                        font-family: monospace;
                        font-weight: bold;
                        cursor: pointer;
                        opacity: 0;
                        transition: opacity 0.2s ease;
                        pointer-events: auto;
                    `;

                    const parent = video.parentElement;
                    if (parent) {
                        const computed = window.getComputedStyle(parent);
                        if (computed.position === 'static') {
                            parent.style.position = 'relative';
                        }
                        parent.appendChild(btn);

                        const showBtn = () => { btn.style.opacity = '0.9'; };
                        const hideBtn = () => { btn.style.opacity = '0'; };

                        parent.addEventListener('mouseenter', showBtn);
                        parent.addEventListener('mouseleave', hideBtn);
                        video.addEventListener('mouseenter', showBtn);
                        video.addEventListener('mouseleave', hideBtn);
                        btn.addEventListener('mouseenter', () => { btn.style.opacity = '1'; });
                    }

                    btn.addEventListener('click', async (e) => {
                        e.stopPropagation();
                        e.preventDefault();
                        try {
                            video.disablePictureInPicture = false;
                            if (document.pictureInPictureElement) {
                                await document.exitPictureInPicture();
                            } else if (video.requestPictureInPicture) {
                                await video.requestPictureInPicture();
                            }
                        } catch(err) {
                            console.error('PiP Error:', err);
                        }
                    });
                }

                function findVideos(root = document) {
                    let list = Array.from(root.querySelectorAll('video'));
                    try {
                        root.querySelectorAll('*').forEach(el => {
                            if (el.shadowRoot) {
                                list = list.concat(findVideos(el.shadowRoot));
                            }
                        });
                    } catch(e) {}
                    return list;
                }

                function scanVideos() {
                    findVideos().forEach(setupVideoPiP);
                }

                scanVideos();
                const observer = new MutationObserver(scanVideos);
                if (document.body) {
                    observer.observe(document.body, { childList: true, subtree: true });
                }
            })();
            """
            self.page().runJavaScript(pip_overlay_js)
        except Exception as e:
            print(f"[Theme/PiP Injection Error] {e}")

        try:
            from core.password_autofill import PasswordAutofillManager
            matches = PasswordAutofillManager.get_matches_for_url(u)
            if matches:
                js = PasswordAutofillManager.generate_injection_js(matches)
                if js:
                    self.page().runJavaScript(js)
            capture_js = PasswordAutofillManager.generate_capture_js()
            if capture_js:
                self.page().runJavaScript(capture_js)
        except Exception as e:
            print(f"[Autofill Error] {e}")

    def handle_host_cmd(self, url_clean: str) -> None:
        if not url_clean:
            return
        if url_clean.startswith("zephyrium://setup") or url_clean.startswith("zinc://setup"):
            self._apply_setup(url_clean)
            return
        if url_clean.startswith("zephyrium://live-setting") or url_clean.startswith("zinc://live-setting"):
            self._apply_live_setting(url_clean)
            return
        if url_clean.startswith("zephyrium://apply-settings") or url_clean.startswith("zinc://apply-settings"):
            self._apply_settings_from_url(url_clean)
            return
        if url_clean.startswith("zephyrium://action/") or url_clean.startswith("zinc://action/"):
            self._handle_action(url_clean)
            return
        if url_clean.startswith("zephyrium://new-tab") or url_clean.startswith("zinc://new-tab") or url_clean.startswith("zephyrium://open-tab"):
            try:
                import urllib.parse
                parsed = urllib.parse.urlparse(url_clean)
                qs = urllib.parse.parse_qs(parsed.query)
                target = qs.get("url", [""])[0]
                win = self._get_main_window()
                if win and hasattr(win, "tab_manager"):
                    win.tab_manager.create_tab(url=target or "zephyrium://startpage")
            except Exception as e:
                print(f"Error handling new-tab navigation: {e}")
            return
        self.navigate(url_clean)

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
        ws_th = s.get("website_theme", "light")

        is_internal = (url_clean.startswith("zephyrium://") or
                       url_clean.startswith("zinc://") or
                       url_clean.startswith("about:") or
                       "startpage.html" in url_clean or
                       "settings.html" in url_clean or
                       "history.html" in url_clean or
                       "downloads.html" in url_clean)

        if is_internal:
            self.page().setBackgroundColor(QColor("#18181b" if th == "dark" else "#ffffff"))
        else:
            if s.get("clean_urls", True):
                try:
                    from core.privacy_shield import strip_tracking_params
                    url_clean = strip_tracking_params(url_clean)
                except Exception:
                    pass
            if ws_th == "dark":
                self.page().setBackgroundColor(QColor("#121212"))
            else:
                self.page().setBackgroundColor(QColor("#ffffff"))

        if url_clean in ["zephyrium://startpage", "zinc://startpage", "about:blank"]:
            self.load(QUrl("zephyrium://startpage"))
            return

        if url_clean in ["zephyrium://welcome", "zinc://welcome"]:
            win = self._get_main_window()
            if win and hasattr(win, "show_onboarding"):
                win.show_onboarding()
            else:
                self.load(QUrl("zephyrium://startpage"))
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
            target_scheme_url = url_clean if url_clean.startswith("zephyrium://") else "zephyrium://settings"
            self.load(QUrl(target_scheme_url))
            return

        if url_clean.startswith("zephyrium://history") or url_clean.startswith("zinc://history") or url_clean in ["about:history"]:
            self.load(QUrl("zephyrium://history"))
            return

        if url_clean.startswith("zephyrium://downloads") or url_clean.startswith("zinc://downloads") or url_clean in ["about:downloads"]:
            self.load(QUrl("zephyrium://downloads"))
            return

        if url_clean in ["zephyrium://about", "zinc://about", "about:about"]:
            self.load(QUrl("zephyrium://settings?tab=about"))
            return

        if url_clean in ["zephyrium://vault", "zinc://vault"]:
            self.load(QUrl("zephyrium://settings?tab=vault"))
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
                        sb = win.tab_manager.sidebar
                        try:
                            val = int(s.get("sidebar_width", 240))
                            if hasattr(sb, "set_expanded_width"):
                                sb.set_expanded_width(val)
                            elif not getattr(sb, "is_compact", False):
                                sb.setFixedWidth(val)
                        except Exception:
                            pass
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
            if "website_theme" in params:
                s["website_theme"] = params["website_theme"][0]
            if "new_tab_url" in params:
                s["new_tab_url"] = params["new_tab_url"][0]
            if "tab_hibernation" in params:
                s["tab_hibernation"] = params["tab_hibernation"][0]

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

            if action == "exit-reader":
                self.toggle_reader_mode()
                return
            elif action == "clear-history":
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
            elif action == "open-scripts-dir":
                from core.userscript_manager import SCRIPTS_DIR
                from PyQt6.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(SCRIPTS_DIR)))
            elif action == "toggle-userscript":
                target_fn = qs.get("name", [""])[0]
                win = self._get_main_window()
                if win and hasattr(win, "profile_manager"):
                    win.profile_manager.userscript_manager.toggle_script(target_fn)
            elif action == "toggle-userstyle":
                target_fn = qs.get("name", [""])[0]
                win = self._get_main_window()
                if win and hasattr(win, "profile_manager"):
                    win.profile_manager.userscript_manager.toggle_style(target_fn)
            elif action == "open-file":
                fpath = qs.get("path", [""])[0]
                if fpath:
                    unquoted = urllib.parse.unquote(fpath)
                    if os.path.exists(unquoted):
                        QDesktopServices.openUrl(QUrl.fromLocalFile(unquoted))
            elif action == "unlock-vault":
                import json
                from config import CONFIG_DIR
                from core.auth import verify_vault_password
                pwd_input = qs.get("password", [""])[0]
                unquoted_pwd = urllib.parse.unquote(pwd_input)
                is_valid = verify_vault_password(unquoted_pwd)

                if is_valid:
                    pw_file = CONFIG_DIR / "passwords.json"
                    passwords = []
                    if pw_file.exists():
                        try:
                            with open(pw_file, "r", encoding="utf-8") as f:
                                passwords = json.load(f)
                        except Exception:
                            passwords = []
                    payload = json.dumps(passwords)
                    self.page().runJavaScript(f"if (window.onVaultAuthSuccess) window.onVaultAuthSuccess({payload});")
                else:
                    self.page().runJavaScript("if (window.onVaultAuthFailed) window.onVaultAuthFailed();")
            elif action == "delete-password":
                from config import CONFIG_DIR
                import json
                domain = qs.get("domain", [""])[0]
                username = qs.get("username", [""])[0]
                pw_file = CONFIG_DIR / "passwords.json"
                pwds = []
                if pw_file.exists():
                    try:
                        with open(pw_file, "r", encoding="utf-8") as f:
                            pwds = json.load(f)
                        pwds = [p for p in pwds if not (p.get("url") == domain and p.get("username") == username)]
                        with open(pw_file, "w", encoding="utf-8") as f:
                            json.dump(pwds, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        print(f"Error deleting password: {e}")
                payload = json.dumps(pwds)
                self.page().runJavaScript(f"if (window.onPasswordDeleted) window.onPasswordDeleted({payload});")
            elif action == "delete-cookie":
                from config import CONFIG_DIR
                import json
                host = qs.get("host", [""])[0]
                name = qs.get("name", [""])[0]
                ck_file = CONFIG_DIR / "cookies.json"
                cks = []
                if ck_file.exists():
                    try:
                        with open(ck_file, "r", encoding="utf-8") as f:
                            cks = json.load(f)
                        cks = [c for c in cks if not (c.get("host") == host and c.get("name") == name)]
                        with open(ck_file, "w", encoding="utf-8") as f:
                            json.dump(cks, f, indent=2, ensure_ascii=False)
                    except Exception as e:
                        print(f"Error deleting cookie: {e}")
                payload = json.dumps(cks)
                self.page().runJavaScript(f"if (window.onCookieDeleted) window.onCookieDeleted({payload});")
            elif action == "prompt-save-password":
                url_param = qs.get("url", [""])[0]
                user_param = qs.get("username", [""])[0]
                pwd_param = qs.get("password", [""])[0]
                from core.password_autofill import PasswordAutofillManager
                if PasswordAutofillManager.should_prompt_save(url_param, user_param, pwd_param):
                    win = self._get_main_window()
                    if win and hasattr(win, "show_password_save_prompt"):
                        win.show_password_save_prompt(url_param, user_param, pwd_param)
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

        # Selection & AI Quick Actions
        selected_text = self.selectedText().strip()
        if selected_text:
            ai_menu = menu.addMenu("✦ Zephyrium AI")
            act_explain = ai_menu.addAction("Explain Selection")
            act_explain.triggered.connect(lambda: self.ask_ai_action.emit("explain", selected_text))
            act_trans = ai_menu.addAction("Translate to Russian")
            act_trans.triggered.connect(lambda: self.ask_ai_action.emit("translate", selected_text))
            act_tldr = ai_menu.addAction("Summarize (TL;DR)")
            act_tldr.triggered.connect(lambda: self.ask_ai_action.emit("summarize", selected_text))
            
            act_ai_custom = ai_menu.addAction(f"Ask in Chat ('{selected_text[:20]}...')")
            act_ai_custom.triggered.connect(lambda: self.ask_ai_selection.emit(selected_text))
            menu.addSeparator()

        # Media & Page Modes
        act_pip = menu.addAction("Picture-in-Picture (PiP)")
        act_pip.triggered.connect(self.trigger_pip)

        act_reader = menu.addAction("Toggle Reader Mode")
        act_reader.triggered.connect(self.toggle_reader_mode)

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

    def trigger_pip(self) -> None:
        js = """
        (async function() {
            try {
                function findVideos(root = document) {
                    let list = Array.from(root.querySelectorAll('video'));
                    try {
                        root.querySelectorAll('*').forEach(el => {
                            if (el.shadowRoot) {
                                list = list.concat(findVideos(el.shadowRoot));
                            }
                        });
                    } catch(e) {}
                    return list;
                }
                const videos = findVideos();
                let video = videos.find(v => !v.paused && v.currentTime > 0) || videos[0];
                if (!video) return 'no_video';
                video.disablePictureInPicture = false;
                if (document.pictureInPictureElement) {
                    await document.exitPictureInPicture();
                    return 'exited';
                }
                if (video.requestPictureInPicture) {
                    await video.requestPictureInPicture();
                    return 'entered';
                }
                return 'not_supported';
            } catch (err) {
                return 'error: ' + (err ? err.message : String(err));
            }
        })();
        """
        def _cb(res):
            if res == 'no_video':
                self.status_message.emit("PiP: No video element found on page")
            elif res == 'entered':
                self.status_message.emit("PiP: Video detached into Picture-in-Picture window")
            elif res == 'exited':
                self.status_message.emit("PiP: Video returned to webpage")
            elif res and str(res).startswith('error'):
                self.status_message.emit(f"PiP Error: {res}")
        self.page().runJavaScript(js, _cb)

    def toggle_reader_mode(self) -> None:
        if self.is_reader_mode:
            self.is_reader_mode = False
            if self.original_url_before_reader:
                self.load(self.original_url_before_reader)
            else:
                self.reload()
            self.status_message.emit("Exited Reader Mode")
            return

        self.original_url_before_reader = self.url()
        js = """
        (function() {
            try {
                const title = document.title || 'Reader Mode';
                const article = document.querySelector('article') ||
                                document.querySelector('main') ||
                                document.querySelector('.post-content') ||
                                document.querySelector('.article-content') ||
                                document.querySelector('#content') ||
                                document.querySelector('.content') ||
                                document.body;
                if (!article) return null;
                const clone = article.cloneNode(true);
                const toRemove = ['nav', 'header', 'footer', 'aside', 'script', 'style', 'iframe', '.ad', '.ads', '.banner', '.social', '.comments', '.sidebar'];
                toRemove.forEach(sel => {
                    clone.querySelectorAll(sel).forEach(el => el.remove());
                });
                return {
                    title: title,
                    html: clone.innerHTML
                };
            } catch(e) {
                return null;
            }
        })();
        """
        def _cb(data):
            if not data or not data.get('html'):
                self.status_message.emit("Reader Mode: Unable to extract readable article content")
                return

            from config import load_settings
            s = load_settings()
            th = s.get("theme", "dark")
            acc = s.get("accent_color", "#fe8019")
            bg = "#18181b" if th == "dark" else "#f8fafc"
            fg = "#d4d4d8" if th == "dark" else "#1e293b"
            card_bg = "#262624" if th == "dark" else "#ffffff"
            border = "#3f3f46" if th == "dark" else "#e2e8f0"
            font_family = s.get("font_family", "system-ui, -apple-system, sans-serif")

            reader_html = f"""<!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{data.get('title', 'Reader Mode')}</title>
                <style>
                    body {{
                        background-color: {bg};
                        color: {fg};
                        font-family: {font_family};
                        line-height: 1.75;
                        font-size: 16px;
                        margin: 0;
                        padding: 40px 20px;
                        display: flex;
                        justify-content: center;
                    }}
                    .reader-container {{
                        max-width: 740px;
                        width: 100%;
                    }}
                    .reader-header {{
                        margin-bottom: 32px;
                        border-bottom: 2px solid {acc};
                        padding-bottom: 16px;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                    }}
                    .reader-title {{
                        font-size: 24px;
                        font-weight: bold;
                        color: {acc};
                    }}
                    .btn-exit {{
                        background: {card_bg};
                        color: {fg};
                        border: 1px solid {border};
                        padding: 6px 12px;
                        cursor: pointer;
                        font-family: inherit;
                        font-size: 12px;
                    }}
                    .btn-exit:hover {{
                        border-color: {acc};
                        color: {acc};
                    }}
                    img {{
                        max-width: 100%;
                        height: auto;
                        display: block;
                        margin: 20px auto;
                    }}
                    pre, code {{
                        background: {card_bg};
                        border: 1px solid {border};
                        padding: 2px 6px;
                        font-family: monospace;
                    }}
                    pre {{
                        padding: 12px;
                        overflow-x: auto;
                    }}
                    a {{
                        color: {acc};
                        text-decoration: underline;
                    }}
                </style>
            </head>
            <body>
                <div class="reader-container">
                    <div class="reader-header">
                        <div class="reader-title">{data.get('title', '')}</div>
                        <button class="btn-exit" onclick="window.location.href='zephyrium://action/exit-reader'">[ВЫЙТИ ИЗ ЧТЕНИЯ]</button>
                    </div>
                    <div class="reader-body">
                        {data.get('html', '')}
                    </div>
                </div>
            </body>
            </html>"""
            self.is_reader_mode = True
            self.setHtml(reader_html, self.original_url_before_reader)
            self.status_message.emit("Reader Mode: Active (Press button or [ВЫЙТИ ИЗ ЧТЕНИЯ] to exit)")

        self.page().runJavaScript(js, _cb)

    def _copy_as_curl(self) -> None:
        u = self.url().toString()
        curl_cmd = f"curl -sL '{u}' -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Zephyrium/1.2.0'"
        from_pyqt_clipboard(curl_cmd)

    def _inspect_element(self) -> None:
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        self.triggerPageAction(QWebEnginePage.WebAction.InspectElement)

def from_pyqt_clipboard(text: str):
    cb = QApplication.clipboard()
    if cb:
        cb.setText(text)
