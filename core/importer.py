"""
Universal Browser Data Importer for Zinc Browser
Imports Bookmarks, Browsing History, Cookies, and Passwords/Logins
from Chrome, Chromium, Brave, Edge, Firefox, and Flatpak browsers.
"""
import os
import sys
import shutil
import sqlite3
import json
import time
from pathlib import Path
from typing import Dict, List, Tuple
from config import BOOKMARKS_FILE, HISTORY_FILE, CONFIG_DIR
from utils.bookmarks import DataStore

PASSWORDS_FILE = CONFIG_DIR / "passwords.json"
COOKIES_FILE = CONFIG_DIR / "cookies.json"

class BrowserProfile:
    def __init__(self, name: str, browser_type: str, path: Path):
        self.name = name
        self.browser_type = browser_type  # 'chromium' or 'firefox'
        self.path = path


class BrowserImporter:
    @staticmethod
    def get_detected_browsers() -> List[BrowserProfile]:
        profiles = []
        home = Path.home()

        if sys.platform == "win32":
            local_appdata = Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local"))
            roaming_appdata = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
            win_candidates = [
                ("Google Chrome", "chromium", local_appdata / "Google" / "Chrome" / "User Data" / "Default"),
                ("Microsoft Edge", "chromium", local_appdata / "Microsoft" / "Edge" / "User Data" / "Default"),
                ("Brave Browser", "chromium", local_appdata / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default"),
                ("Vivaldi", "chromium", local_appdata / "Vivaldi" / "User Data" / "Default"),
                ("Opera", "chromium", roaming_appdata / "Opera Software" / "Opera Stable"),
            ]
            for name, btype, path in win_candidates:
                if path.exists() and path.is_dir():
                    profiles.append(BrowserProfile(name, btype, path))

            ff_win = roaming_appdata / "Mozilla" / "Firefox" / "Profiles"
            if ff_win.exists():
                for profile_dir in ff_win.glob("*.default*"):
                    if profile_dir.is_dir():
                        profiles.append(BrowserProfile(f"Mozilla Firefox ({profile_dir.name})", "firefox", profile_dir))
                        break
            return profiles

        candidates = [
            # Flatpak Chromium-based
            ("Google Chrome (Flatpak)", "chromium", home / ".var/app/com.google.Chrome/config/google-chrome/Default"),
            ("Microsoft Edge (Flatpak)", "chromium", home / ".var/app/com.microsoft.Edge/config/microsoft-edge/Default"),
            ("Chromium (Flatpak)", "chromium", home / ".var/app/org.chromium.Chromium/config/chromium/Default"),
            ("Ungoogled Chromium (Flatpak)", "chromium", home / ".var/app/io.github.ungoogled_software.ungoogled_chromium/config/chromium/Default"),
            ("Brave (Flatpak)", "chromium", home / ".var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser/Default"),
            ("Falkon (Flatpak)", "falkon", home / ".var/app/org.kde.falkon/config/falkon/profiles/default"),

            # Native Chromium-based
            ("Google Chrome", "chromium", home / ".config/google-chrome/Default"),
            ("Chromium", "chromium", home / ".config/chromium/Default"),
            ("Brave Browser", "chromium", home / ".config/BraveSoftware/Brave-Browser/Default"),
            ("Microsoft Edge", "chromium", home / ".config/microsoft-edge/Default"),
            ("Vivaldi", "chromium", home / ".config/vivaldi/Default"),
            ("Opera", "chromium", home / ".config/opera"),
        ]

        for name, btype, path in candidates:
            if path.exists() and path.is_dir():
                profiles.append(BrowserProfile(name, btype, path))

        # Firefox (Flatpak & Native)
        ff_roots = [
            ("Mozilla Firefox (Flatpak)", home / ".var/app/org.mozilla.firefox/.mozilla/firefox"),
            ("Mozilla Firefox", home / ".mozilla/firefox"),
            ("LibreWolf (Flatpak)", home / ".var/app/io.gitlab.librewolf-community/.librewolf"),
            ("Waterfox (Flatpak)", home / ".var/app/net.waterfox.waterfox/.waterfox"),
        ]
        for ff_name, root in ff_roots:
            if root.exists():
                for profile_dir in root.glob("*.default*"):
                    if profile_dir.is_dir():
                        profiles.append(BrowserProfile(f"{ff_name} ({profile_dir.name})", "firefox", profile_dir))
                        break

        return profiles

    @staticmethod
    def import_bookmarks_chromium(profile_path: Path) -> int:
        bm_file = profile_path / "Bookmarks"
        if not bm_file.exists():
            bm_file = profile_path / "bookmarks.json"
        if not bm_file.exists():
            return 0

        try:
            with open(bm_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            count = 0
            existing = DataStore.load_bookmarks()
            urls = {b["url"] for b in existing}

            def parse_node(node):
                nonlocal count
                if isinstance(node, dict):
                    if node.get("type") == "url":
                        u = node.get("url")
                        t = node.get("name") or u
                        if u and u not in urls:
                            existing.append({"title": t, "url": u})
                            urls.add(u)
                            count += 1
                    for child in node.get("children", []):
                        parse_node(child)

            roots = data.get("roots", {})
            for root_key in roots:
                parse_node(roots[root_key])

            if count > 0:
                DataStore.save_bookmarks(existing)
            return count
        except Exception as e:
            print(f"Error importing Chromium bookmarks: {e}")
            return 0

    @staticmethod
    def import_bookmarks_firefox(profile_path: Path) -> int:
        places_db = profile_path / "places.sqlite"
        if not places_db.exists():
            return 0

        tmp_db = Path("/tmp/places_bm_tmp.sqlite")
        try:
            shutil.copy2(places_db, tmp_db)
            conn = sqlite3.connect(tmp_db)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT b.title, p.url 
                FROM moz_bookmarks b
                JOIN moz_places p ON b.fk = p.id
                WHERE p.url NOT LIKE 'place:%'
            """)
            rows = cursor.fetchall()
            conn.close()

            existing = DataStore.load_bookmarks()
            urls = {b["url"] for b in existing}
            count = 0
            for title, url in rows:
                if url and url not in urls:
                    existing.append({"title": title or url, "url": url})
                    urls.add(url)
                    count += 1

            if count > 0:
                DataStore.save_bookmarks(existing)
            return count
        except Exception as e:
            print(f"Error importing Firefox bookmarks: {e}")
            return 0
        finally:
            if tmp_db.exists():
                tmp_db.unlink()

    @staticmethod
    def import_history_chromium(profile_path: Path) -> int:
        hist_file = profile_path / "History"
        if not hist_file.exists():
            return 0

        tmp_hist = Path("/tmp/history_tmp.sqlite")
        try:
            shutil.copy2(hist_file, tmp_hist)
            conn = sqlite3.connect(tmp_hist)
            cursor = conn.cursor()
            cursor.execute("SELECT title, url, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 500")
            rows = cursor.fetchall()
            conn.close()

            existing = DataStore.load_history()
            urls = {h.get("url") for h in existing}
            count = 0
            for title, url, lvt in rows:
                if url and url not in urls:
                    existing.append({
                        "title": title or url,
                        "url": url,
                        "timestamp": int(time.time()),
                    })
                    urls.add(url)
                    count += 1

            if count > 0:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(existing[:1000], f, indent=2, ensure_ascii=False)
            return count
        except Exception as e:
            print(f"Error importing Chromium history: {e}")
            return 0
        finally:
            if tmp_hist.exists():
                tmp_hist.unlink()

    @staticmethod
    def import_history_firefox(profile_path: Path) -> int:
        places_file = profile_path / "places.sqlite"
        if not places_file.exists():
            return 0

        tmp_places = Path("/tmp/places_hist_tmp.sqlite")
        try:
            shutil.copy2(places_file, tmp_places)
            conn = sqlite3.connect(tmp_places)
            cursor = conn.cursor()
            cursor.execute("SELECT title, url, visit_count FROM moz_places ORDER BY last_visit_date DESC LIMIT 500")
            rows = cursor.fetchall()
            conn.close()

            existing = DataStore.load_history()
            urls = {h.get("url") for h in existing}
            count = 0
            for title, url, _ in rows:
                if url and not url.startswith("place:") and url not in urls:
                    existing.append({
                        "title": title or url,
                        "url": url,
                        "timestamp": int(time.time()),
                    })
                    urls.add(url)
                    count += 1

            if count > 0:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(existing[:1000], f, indent=2, ensure_ascii=False)
            return count
        except Exception as e:
            print(f"Error importing Firefox history: {e}")
            return 0
        finally:
            if tmp_places.exists():
                tmp_places.unlink()

    @staticmethod
    def import_cookies_chromium(profile_path: Path) -> int:
        cookie_file = profile_path / "Network" / "Cookies"
        if not cookie_file.exists():
            cookie_file = profile_path / "Cookies"
        if not cookie_file.exists():
            return 0

        tmp_cookies = Path("/tmp/cookies_tmp.sqlite")
        try:
            shutil.copy2(cookie_file, tmp_cookies)
            conn = sqlite3.connect(tmp_cookies)
            cursor = conn.cursor()
            cursor.execute("SELECT host_key, name, path, expires_utc, is_secure, is_httponly FROM cookies LIMIT 1000")
            rows = cursor.fetchall()
            conn.close()

            cookies_list = []
            for host, name, path, expires, secure, httponly in rows:
                cookies_list.append({
                    "host": host,
                    "name": name,
                    "path": path,
                    "expires": expires,
                    "secure": bool(secure),
                    "httponly": bool(httponly),
                })

            if cookies_list:
                with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                    json.dump(cookies_list, f, indent=2)
            return len(cookies_list)
        except Exception as e:
            print(f"Error importing Chromium cookies: {e}")
            return 0
        finally:
            if tmp_cookies.exists():
                tmp_cookies.unlink()

    @staticmethod
    def import_cookies_firefox(profile_path: Path) -> int:
        cookie_file = profile_path / "cookies.sqlite"
        if not cookie_file.exists():
            return 0

        tmp_cookies = Path("/tmp/ff_cookies_tmp.sqlite")
        try:
            shutil.copy2(cookie_file, tmp_cookies)
            conn = sqlite3.connect(tmp_cookies)
            cursor = conn.cursor()
            cursor.execute("SELECT host, name, path, expiry, isSecure, isHttpOnly FROM moz_cookies LIMIT 1000")
            rows = cursor.fetchall()
            conn.close()

            cookies_list = []
            for host, name, path, expires, secure, httponly in rows:
                cookies_list.append({
                    "host": host,
                    "name": name,
                    "path": path,
                    "expires": expires,
                    "secure": bool(secure),
                    "httponly": bool(httponly),
                })

            if cookies_list:
                with open(COOKIES_FILE, "w", encoding="utf-8") as f:
                    json.dump(cookies_list, f, indent=2)
            return len(cookies_list)
        except Exception as e:
            print(f"Error importing Firefox cookies: {e}")
            return 0
        finally:
            if tmp_cookies.exists():
                tmp_cookies.unlink()

    @staticmethod
    def _decrypt_chromium_password(blob: bytes) -> str:
        if not blob:
            return ""
        if isinstance(blob, str):
            return blob
        try:
            if blob.startswith(b"v10") or blob.startswith(b"v11"):
                import hashlib
                from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
                key = hashlib.pbkdf2_hmac("sha1", b"peanuts", b"saltysalt", 1, 16)
                iv = b" " * 16
                cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
                decryptor = cipher.decryptor()
                dec = decryptor.update(blob[3:]) + decryptor.finalize()
                if dec:
                    pad_len = dec[-1]
                    if 1 <= pad_len <= 16:
                        dec = dec[:-pad_len]
                    return dec.decode("utf-8", errors="ignore")
            return blob.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    @staticmethod
    def import_passwords_chromium(profile_path: Path) -> int:
        login_file = profile_path / "Login Data"
        if not login_file.exists():
            return 0

        tmp_logins = Path("/tmp/logins_tmp.sqlite")
        try:
            shutil.copy2(login_file, tmp_logins)
            conn = sqlite3.connect(tmp_logins)
            cursor = conn.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins WHERE username_value != ''")
            rows = cursor.fetchall()
            conn.close()

            vault = []
            if PASSWORDS_FILE.exists():
                try:
                    with open(PASSWORDS_FILE, "r", encoding="utf-8") as f:
                        vault = json.load(f)
                except Exception:
                    vault = []

            existing_keys = {(v["url"], v["username"]): v for v in vault}
            count = 0
            for url, username, pwd_blob in rows:
                dec_pwd = BrowserImporter._decrypt_chromium_password(pwd_blob)
                key = (url, username)
                if key not in existing_keys:
                    vault.append({
                        "url": url,
                        "username": username,
                        "password": dec_pwd,
                        "imported_at": int(time.time()),
                    })
                    count += 1
                elif not existing_keys[key].get("password") and dec_pwd:
                    existing_keys[key]["password"] = dec_pwd
                    count += 1

            if count > 0:
                with open(PASSWORDS_FILE, "w", encoding="utf-8") as f:
                    json.dump(vault, f, indent=2, ensure_ascii=False)
            return count
        except Exception as e:
            print(f"Error importing passwords: {e}")
            return 0
        finally:
            if tmp_logins.exists():
                tmp_logins.unlink()

    @staticmethod
    def import_from_csv_passwords(csv_path: Path) -> int:
        if not csv_path.exists():
            return 0
        import csv
        vault = []
        if PASSWORDS_FILE.exists():
            try:
                with open(PASSWORDS_FILE, "r", encoding="utf-8") as f:
                    vault = json.load(f)
            except Exception:
                vault = []
        existing = {(v["url"], v["username"]) for v in vault}
        count = 0
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get("url") or row.get("URL") or row.get("origin_url") or ""
                    user = row.get("username") or row.get("Username") or ""
                    pwd = row.get("password") or row.get("Password") or ""
                    if url and user and (url, user) not in existing:
                        vault.append({
                            "url": url,
                            "username": user,
                            "password": pwd,
                            "imported_at": int(time.time()),
                        })
                        existing.add((url, user))
                        count += 1
            if count > 0:
                with open(PASSWORDS_FILE, "w", encoding="utf-8") as f:
                    json.dump(vault, f, indent=2, ensure_ascii=False)
            return count
        except Exception as e:
            print(f"Error importing CSV passwords: {e}")
            return 0
