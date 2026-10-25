"""
Zephyrium Browser Configuration
Supports Claude Code Minimal Dark, Sleek Light, and Material 3 Expressive themes.
"""
import os
import sys
import json
from pathlib import Path

# Base Paths
APP_NAME = "Zephyrium"
APP_VERSION = "1.0.1"

if sys.platform == "win32":
    CONFIG_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Zephyrium"
else:
    CONFIG_DIR = Path.home() / ".config" / "zephyrium"
PROFILES_DIR = CONFIG_DIR / "profiles"
NOTES_FILE = CONFIG_DIR / "notes.txt"
BOOKMARKS_FILE = CONFIG_DIR / "bookmarks.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
DOWNLOADS_FILE = CONFIG_DIR / "downloads.json"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

CONFIG_DIR.mkdir(parents=True, exist_ok=True)
PROFILES_DIR.mkdir(parents=True, exist_ok=True)

# Default Settings
DEFAULT_SETTINGS = {
    "gemini_api_key": "",
    "ai_model": "gemini-2.5-flash",
    "ui_mode": "minimal",       # "minimal", "vim"
    "tab_orientation": "vertical",  # "vertical", "horizontal"
    "theme": "dark",            # "dark", "light"
    "accent_color": "#fe8019",  # Orange (#fe8019), Emerald (#10b981), Blue (#38bdf8), Purple (#a855f7), Rose (#f43f5e), Slate (#94a3b8)
    "language": "ru",
    "homepage": "zephyrium://startpage",
    "download_dir": str(Path.home() / "Downloads"),
    "restore_session": False,
    "adblock_enabled": True,
    "clean_urls": True,
    "send_dnt": True,
    "prevent_webrtc_leak": True,
    "font_family": "Iosevka Nerd Font",
    "font_size": 13,
    "sidebar_width": 240,
    "ai_persona": "You are an intelligent, engineer-focused AI assistant in Zephyrium Browser.",
    "gpu_accel": True,
    "proxy_host": "",
    "proxy_port": "",
    "first_run": True,
}

def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure defaults for any missing keys
            updated = False
            for k, v in DEFAULT_SETTINGS.items():
                if k not in data:
                    data[k] = v
                    updated = True
            if data.get("ui_mode") in ["classic", "expressive"]:
                data["ui_mode"] = "minimal"
                updated = True
            if data.get("tab_orientation") not in ["vertical", "horizontal"]:
                data["tab_orientation"] = "vertical"
                updated = True
            if updated:
                save_settings(data)
            return data
    except Exception:
        return dict(DEFAULT_SETTINGS)

def save_settings(settings: dict) -> None:
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving settings: {e}")

# Search Engine & URLs
SEARCH_ENGINE_URL = "https://duckduckgo.com/?q={query}"
DEFAULT_HOME_URL = "zephyrium://startpage"
WELCOME_URL = "zephyrium://welcome"

# Preset Accent Colors
ACCENT_PRESETS = {
    "orange": {"name": "Zephyrium Amber", "hex": "#fe8019"},
    "emerald": {"name": "Emerald Green", "hex": "#10b981"},
    "blue": {"name": "Sky Blue", "hex": "#38bdf8"},
    "purple": {"name": "Lavender Purple", "hex": "#a855f7"},
    "rose": {"name": "Nordic Rose", "hex": "#f43f5e"},
    "slate": {"name": "Monochrome Slate", "hex": "#94a3b8"},
}

# Design Tokens (Claude Code Minimal Dark)
COLORS = {
    "bg-base": "#18181b",
    "bg-surface": "#262624",
    "bg-elevated": "#2d2d2a",
    "border-muted": "#3f3f46",
    "border-subtle": "#2b2b29",
    "border-active": "#94a3b8",
    "text-primary": "#d4d4d8",
    "text-bright": "#f5f5f0",
    "text-muted": "#71717a",
    "accent": "#94a3b8",
    "accent-warm": "#fe8019",
    "status-success": "#10b981",
    "status-warning": "#f59e0b",
    "status-error": "#ef4444",
    "status-info": "#38bdf8",
}

# Multi-Account Containers / Profiles
CONTAINERS = {
    "default": {
        "name": "Default",
        "color": "#94a3b8",
        "storage": "persistent",
        "badge": "DEF",
        "letter": "D",
    },
    "work": {
        "name": "Work",
        "color": "#10b981",
        "storage": "persistent",
        "badge": "WRK",
        "letter": "W",
    },
    "personal": {
        "name": "Personal",
        "color": "#38bdf8",
        "storage": "persistent",
        "badge": "PER",
        "letter": "P",
    },
    "dev": {
        "name": "Dev",
        "color": "#fe8019",
        "storage": "persistent",
        "badge": "DEV",
        "letter": "X",
    },
    "incognito": {
        "name": "Incognito",
        "color": "#ef4444",
        "storage": "ephemeral",
        "badge": "INC",
        "letter": "I",
    },
}

# Adblock default hosts to block
ADBLOCK_DOMAINS = [
    "doubleclick.net",
    "google-analytics.com",
    "googlesyndication.com",
    "googletagmanager.com",
    "adservice.google.com",
    "adnxs.com",
    "criteo.com",
    "quantserve.com",
    "scorecardresearch.com",
    "taboola.com",
    "outbrain.com",
    "adroll.com",
    "analytics.twitter.com",
    "facebook.com/tr/",
    "an.yandex.ru",
    "mc.yandex.ru",
    "adfox.ru",
    "adverticum.net",
    "smartadserver.com",
    "zedo.com",
    "popads.net",
    "propellerads.com",
]
