"""
Content Blocker / Adblocker Interceptor & URL Cleaner for Zinc Browser
Built on QWebEngineUrlRequestInterceptor with persistent Whitelist support.
"""
import json
import urllib.parse
from pathlib import Path
from typing import Set
from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo
from config import ADBLOCK_DOMAINS, CONFIG_DIR

WHITELIST_FILE = CONFIG_DIR / "adblock_whitelist.json"

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "_ga", "msclkid", "si", "igshid", "yclid", "mc_eid"
}

def clean_tracking_parameters(url_str: str) -> str:
    """Strips tracking analytics tags (utm, fbclid, etc.) from URLs."""
    try:
        parsed = urllib.parse.urlparse(url_str)
        if not parsed.query:
            return url_str
        qs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered = [(k, v) for k, v in qs if k.lower() not in TRACKING_PARAMS]
        new_query = urllib.parse.urlencode(filtered)
        return urllib.parse.urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ))
    except Exception:
        return url_str


class AdBlockerInterceptor(QWebEngineUrlRequestInterceptor):
    request_blocked = pyqtSignal(str)  # Emits blocked URL string
    whitelist_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.enabled = True
        self.blocked_count = 0
        self.blocked_domains: Set[str] = set(ADBLOCK_DOMAINS)
        self.whitelist: Set[str] = set()
        self._load_whitelist()

    def _load_whitelist(self) -> None:
        if WHITELIST_FILE.exists():
            try:
                with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.whitelist = set(data)
            except Exception:
                self.whitelist = set()

    def _save_whitelist(self) -> None:
        try:
            with open(WHITELIST_FILE, "w", encoding="utf-8") as f:
                json.dump(list(self.whitelist), f, indent=2)
            self.whitelist_changed.emit()
        except Exception as e:
            print(f"Error saving whitelist: {e}")

    def interceptRequest(self, info: QWebEngineUrlRequestInfo) -> None:
        if not self.enabled:
            return

        request_url: QUrl = info.requestUrl()
        host = request_url.host().lower()
        full_url = request_url.toString().lower()

        # Whitelist check
        if any(w in host for w in self.whitelist):
            return

        # Fast matching against blocked domains
        for domain in self.blocked_domains:
            if domain in host or domain in full_url:
                info.block(True)
                self.blocked_count += 1
                self.request_blocked.emit(full_url)
                return

    def toggle(self) -> bool:
        self.enabled = not self.enabled
        return self.enabled

    def add_domain(self, domain: str) -> None:
        clean = domain.strip().lower()
        if clean:
            self.blocked_domains.add(clean)

    def add_whitelist(self, domain: str) -> None:
        clean = domain.strip().lower()
        if clean:
            self.whitelist.add(clean)
            self._save_whitelist()

    def remove_whitelist(self, domain: str) -> None:
        clean = domain.strip().lower()
        if clean in self.whitelist:
            self.whitelist.remove(clean)
            self._save_whitelist()

    def is_whitelisted(self, domain: str) -> bool:
        clean = domain.strip().lower()
        return any(w in clean for w in self.whitelist)
