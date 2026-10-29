"""
Multi-Account Containers / Profile Isolation Manager for Zinc Browser
Ensures clean User-Agent and isolation across all profiles.
"""
import re
from typing import Dict
from PyQt6.QtCore import QObject
from PyQt6.QtWebEngineCore import QWebEngineProfile
from config import CONTAINERS, PROFILES_DIR
from core.adblock import AdBlockerInterceptor
from core.privacy_shield import install_privacy_shield
from core.userscript_manager import UserscriptManager

def get_clean_user_agent(raw_ua: str) -> str:
    """Strips QtWebEngine identifiers from User-Agent to ensure standard Chrome compatibility."""
    if not raw_ua:
        return ""
    # Strip QtWebEngine/X.X.X
    cleaned = re.sub(r'\s*QtWebEngine/\S+', '', raw_ua).strip()
    return cleaned

class ProfileManager(QObject):
    def __init__(self, adblocker: AdBlockerInterceptor, parent=None, is_incognito: bool = False):
        super().__init__(parent)
        self.adblocker = adblocker
        self.is_incognito = is_incognito
        self.userscript_manager = UserscriptManager(self)
        self._profiles: Dict[str, QWebEngineProfile] = {}
        self._clean_ua = ""
        self._setup_profiles()
        self.userscript_manager.scripts_changed.connect(self._reapply_extensions)

    def _reapply_extensions(self) -> None:
        for p in self._profiles.values():
            self.userscript_manager.apply_to_profile(p)
            install_privacy_shield(p)

    def _setup_profiles(self) -> None:
        from core.web_view import CruxSchemeHandler
        self._scheme_handler = CruxSchemeHandler(self)
        
        default_prof = QWebEngineProfile.defaultProfile()
        self._clean_ua = get_clean_user_agent(default_prof.httpUserAgent())
        if self._clean_ua:
            default_prof.setHttpUserAgent(self._clean_ua)

        try:
            default_prof.installUrlSchemeHandler(b"crux", self._scheme_handler)
            default_prof.installUrlSchemeHandler(b"zephyrium", self._scheme_handler)
            default_prof.installUrlSchemeHandler(b"zinc", self._scheme_handler)
            install_privacy_shield(default_prof)
            self.userscript_manager.apply_to_profile(default_prof)
        except Exception:
            pass

        for profile_id, meta in CONTAINERS.items():
            if self.is_incognito or meta["storage"] == "ephemeral":
                # Off-the-record / Incognito profile (100% in-memory only, no disk IO or locks)
                profile = QWebEngineProfile(self)
            else:
                profile_path = PROFILES_DIR / profile_id
                profile_path.mkdir(parents=True, exist_ok=True)
                profile = QWebEngineProfile(f"crux-profile-{profile_id}", self)
                profile.setPersistentStoragePath(str(profile_path / "storage"))
                profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies)
                profile.setCachePath(str(profile_path / "cache"))

            if self._clean_ua:
                profile.setHttpUserAgent(self._clean_ua)

            # Install scheme handlers for internal crux://, zephyrium:// and zinc:// pages
            try:
                profile.installUrlSchemeHandler(b"crux", self._scheme_handler)
                profile.installUrlSchemeHandler(b"zephyrium", self._scheme_handler)
                profile.installUrlSchemeHandler(b"zinc", self._scheme_handler)
            except Exception:
                pass

            # Register shared adblock interceptor and privacy shield
            profile.setUrlRequestInterceptor(self.adblocker)
            install_privacy_shield(profile)
            self.userscript_manager.apply_to_profile(profile)
            self._profiles[profile_id] = profile

    def get_profile(self, profile_id: str, is_incognito: bool = False) -> QWebEngineProfile:
        if self.is_incognito or is_incognito:
            return self._profiles.get("incognito", self._profiles.get(profile_id, QWebEngineProfile(self)))
        return self._profiles.get(profile_id, self._profiles.get("default", QWebEngineProfile.defaultProfile()))

    def get_meta(self, profile_id: str) -> dict:
        return CONTAINERS.get(profile_id, CONTAINERS["default"])

    def list_containers(self) -> Dict[str, dict]:
        return CONTAINERS
