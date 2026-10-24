"""
Bookmarks and History Manager for Zinc Browser
"""
import json
import time
from typing import List, Dict
from config import BOOKMARKS_FILE, HISTORY_FILE, DOWNLOADS_FILE

class DataStore:
    @staticmethod
    def load_bookmarks() -> List[Dict[str, str]]:
        if not BOOKMARKS_FILE.exists():
            default_bms = [
                {"title": "Arch Linux", "url": "https://archlinux.org"},
                {"title": "Arch Wiki", "url": "https://wiki.archlinux.org"},
                {"title": "DuckDuckGo", "url": "https://duckduckgo.com"},
                {"title": "GitHub", "url": "https://github.com"},
            ]
            DataStore.save_bookmarks(default_bms)
            return default_bms
        try:
            with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def save_bookmarks(bookmarks: List[Dict[str, str]]) -> None:
        try:
            with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
                json.dump(bookmarks, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving bookmarks: {e}")

    @staticmethod
    def add_bookmark(title: str, url: str) -> bool:
        bms = DataStore.load_bookmarks()
        if any(b["url"] == url for b in bms):
            return False
        bms.append({"title": title or url, "url": url})
        DataStore.save_bookmarks(bms)
        return True

    @staticmethod
    def load_history() -> List[Dict[str, any]]:
        if not HISTORY_FILE.exists():
            return []
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def add_history(title: str, url: str) -> None:
        if not url or url.startswith("zephyrium://") or url.startswith("zinc://") or url.startswith("about:"):
            return
        hist = DataStore.load_history()
        entry = {
            "title": title or url,
            "url": url,
            "timestamp": int(time.time()),
        }
        # Prepend and limit to 1000 items
        hist = [h for h in hist if h.get("url") != url]
        hist.insert(0, entry)
        if len(hist) > 1000:
            hist = hist[:1000]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(hist, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history: {e}")

    @staticmethod
    def clear_history() -> None:
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error clearing history: {e}")

    @staticmethod
    def delete_history_item(url: str) -> None:
        hist = DataStore.load_history()
        hist = [h for h in hist if h.get("url") != url]
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(hist, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error deleting history item: {e}")

    @staticmethod
    def load_downloads() -> List[Dict[str, any]]:
        if not DOWNLOADS_FILE.exists():
            return []
        try:
            with open(DOWNLOADS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    @staticmethod
    def add_download(filename: str, path: str, size: int = 0, state: str = "completed") -> None:
        downloads = DataStore.load_downloads()
        entry = {
            "filename": filename,
            "path": path,
            "size": size,
            "state": state,
            "timestamp": int(time.time()),
        }
        downloads = [d for d in downloads if d.get("path") != path]
        downloads.insert(0, entry)
        if len(downloads) > 500:
            downloads = downloads[:500]
        try:
            with open(DOWNLOADS_FILE, "w", encoding="utf-8") as f:
                json.dump(downloads, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving download: {e}")

    @staticmethod
    def clear_downloads() -> None:
        try:
            with open(DOWNLOADS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error clearing downloads: {e}")
