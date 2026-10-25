"""
Multi-Account Containers / Profile Isolation Manager for Zinc Browser
"""
from typing import Dict
from PyQt6.QtCore import QObject
from PyQt6.QtWebEngineCore import QWebEngineProfile
from config import CONTAINERS, PROFILES_DIR
from core.adblock import AdBlockerInterceptor

class ProfileManager(QObject):
    def __init__(self, adblocker: AdBlockerInterceptor, parent=None):
        super().__init__(parent)
        self.adblocker = adblocker
        self._profiles: Dict[str, QWebEngineProfile] = {}
        self._setup_profiles()

    def _setup_profiles(self) -> None:
        from core.web_view import ZephyriumSchemeHandler
        self._scheme_handler = ZephyriumSchemeHandler(self)
        try:
            QWebEngineProfile.defaultProfile().installUrlSchemeHandler(b"zephyrium", self._scheme_handler)
            QWebEngineProfile.defaultProfile().installUrlSchemeHandler(b"zinc", self._scheme_handler)
        except Exception:
            pass

        for profile_id, meta in CONTAINERS.items():
            if meta["storage"] == "ephemeral":
                # Off-the-record / Incognito profile (in-memory only)
                profile = QWebEngineProfile(self)
            else:
                profile_path = PROFILES_DIR / profile_id
                profile_path.mkdir(parents=True, exist_ok=True)
                profile = QWebEngineProfile(f"zephyrium-profile-{profile_id}", self)
                profile.setPersistentStoragePath(str(profile_path / "storage"))
                profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
                profile.setCachePath(str(profile_path / "cache"))

            # Install scheme handlers for internal zephyrium:// and zinc:// pages
            try:
                profile.installUrlSchemeHandler(b"zephyrium", self._scheme_handler)
                profile.installUrlSchemeHandler(b"zinc", self._scheme_handler)
            except Exception:
                pass

            # Register shared adblock interceptor
            profile.setUrlRequestInterceptor(self.adblocker)
            self._profiles[profile_id] = profile

    def get_profile(self, profile_id: str) -> QWebEngineProfile:
        return self._profiles.get(profile_id, self._profiles.get("default", QWebEngineProfile.defaultProfile()))

    def get_meta(self, profile_id: str) -> dict:
        return CONTAINERS.get(profile_id, CONTAINERS["default"])

    def list_containers(self) -> Dict[str, dict]:
        return CONTAINERS
