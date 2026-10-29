"""
Bookmarks and History Manager for Zinc Browser
Now features atomic file writes to prevent data loss on crashes or power failures.
"""
import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any
from config import BOOKMARKS_FILE, HISTORY_FILE, DOWNLOADS_FILE

def atomic_save_json(file_path: Path, data: Any, indent: int = 2) -> bool:
    """Safely and atomically writes JSON data to disk using temporary file replacement."""
    tmp_path = None
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = file_path.with_name(f"{file_path.name}.{os.getpid()}.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
        return True
    except Exception as e:
        print(f"[AtomicSave] Error saving {file_path}: {e}")
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        return False

def open_folder_in_file_manager(folder_path: str) -> bool:
    """Opens directory in the user's primary file manager (Dolphin, Nautilus, etc.) instead of Filelight."""
    import sys, subprocess, shutil
    p = str(Path(folder_path).resolve())
    if sys.platform.startswith("linux"):
        # Check standard GUI file managers first to avoid opening disk analyzers like filelight
        for fm in ["dolphin", "nautilus", "thunar", "nemo", "pcmanfm", "caja", "io.elementary.files"]:
            if shutil.which(fm):
                try:
                    subprocess.Popen([fm, p])
                    return True
                except Exception:
                    pass
        # Fallback to gio open or xdg-open
        try:
            subprocess.Popen(["xdg-open", p])
            return True
        except Exception:
            pass
    from PyQt6.QtGui import QDesktopServices
    from PyQt6.QtCore import QUrl
    return QDesktopServices.openUrl(QUrl.fromLocalFile(p))

class DataStore:
    @staticmethod
    def load_bookmarks() -> List[Dict[str, str]]:
        if not BOOKMARKS_FILE.exists():
            default_bms = [
                {"title": "GitHub", "url": "https://github.com"},
                {"title": "DuckDuckGo", "url": "https://duckduckgo.com"},
                {"title": "MDN Web Docs", "url": "https://developer.mozilla.org"},
                {"title": "Python Docs", "url": "https://docs.python.org/3/"},
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
        atomic_save_json(BOOKMARKS_FILE, bookmarks)

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
        atomic_save_json(HISTORY_FILE, hist)

    @staticmethod
    def clear_history() -> None:
        atomic_save_json(HISTORY_FILE, [])

    @staticmethod
    def delete_history_item(url: str) -> None:
        hist = DataStore.load_history()
        hist = [h for h in hist if h.get("url") != url]
        atomic_save_json(HISTORY_FILE, hist)

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
        atomic_save_json(DOWNLOADS_FILE, downloads)

    @staticmethod
    def clear_downloads() -> None:
        atomic_save_json(DOWNLOADS_FILE, [])
