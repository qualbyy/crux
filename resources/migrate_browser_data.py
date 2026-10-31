#!/usr/bin/env python3
import os
import sys
import glob
import json
import shutil
import sqlite3
import tempfile

def get_peanuts_key():
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        salt = b'saltysalt'
        iv = b' ' * 16
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA1(),
            length=16,
            salt=salt,
            iterations=1,
        )
        return kdf.derive(b'peanuts'), iv
    except Exception:
        return None, None

def decrypt_val(encrypted_bytes, key, iv):
    if not encrypted_bytes:
        return ""
    if not key or not iv:
        try:
            return encrypted_bytes.decode('utf-8', errors='ignore')
        except Exception:
            return ""
    if encrypted_bytes.startswith(b'v10') or encrypted_bytes.startswith(b'v11'):
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
            enc_payload = encrypted_bytes[3:]
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
            decryptor = cipher.decryptor()
            dec = decryptor.update(enc_payload) + decryptor.finalize()
            pad = dec[-1]
            if isinstance(pad, int) and 0 < pad <= 16:
                dec = dec[:-pad]
            return dec.decode('utf-8', errors='ignore')
        except Exception:
            return ""
    try:
        return encrypted_bytes.decode('utf-8', errors='ignore')
    except Exception:
        return ""

def copy_and_open_db(db_path):
    if not os.path.exists(db_path):
        return None, None
    tmp = tempfile.mktemp(suffix=".sqlite")
    try:
        shutil.copy2(db_path, tmp)
        conn = sqlite3.connect(tmp)
        return conn, tmp
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        return None, None

def migrate_chromium_profile(profile_dir, key, iv, sonde_conn):
    passwords_count = 0
    cookies_count = 0
    s_cur = sonde_conn.cursor()

    # Passwords from Login Data and Login Data For Account
    for ldb_name in ["Login Data For Account", "Login Data"]:
        ldb_path = os.path.join(profile_dir, ldb_name)
        conn, tmp = copy_and_open_db(ldb_path)
        if conn:
            try:
                c = conn.cursor()
                c.execute("SELECT origin_url, username_value, password_value FROM logins")
                for u, user, p_enc in c.fetchall():
                    if not u:
                        continue
                    p = decrypt_val(p_enc, key, iv)
                    if p or user:
                        s_cur.execute(
                            "INSERT OR IGNORE INTO passwords (url, username, password) VALUES (?, ?, ?)",
                            (u, user or "", p or "")
                        )
                        passwords_count += 1
            except Exception:
                pass
            finally:
                conn.close()
                if os.path.exists(tmp):
                    os.remove(tmp)

    # Cookies
    for cdb_name in ["Cookies", "Network/Cookies"]:
        cdb_path = os.path.join(profile_dir, cdb_name)
        conn, tmp = copy_and_open_db(cdb_path)
        if conn:
            try:
                c = conn.cursor()
                c.execute("SELECT host_key, name, encrypted_value, path, is_secure, expires_utc FROM cookies")
                for host, cname, val_enc, path, secure, exp in c.fetchall():
                    if not host or not cname:
                        continue
                    val = decrypt_val(val_enc, key, iv)
                    if val:
                        s_cur.execute(
                            "INSERT OR REPLACE INTO cookies (host, name, value, path, is_secure, expires) VALUES (?, ?, ?, ?, ?, ?)",
                            (host, cname, val, path or "/", 1 if secure else 0, exp or 0)
                        )
                        cookies_count += 1
            except Exception:
                pass
            finally:
                conn.close()
                if os.path.exists(tmp):
                    os.remove(tmp)

    sonde_conn.commit()
    return passwords_count, cookies_count

def migrate_firefox_profile(profile_dir, sonde_conn):
    cookies_count = 0
    s_cur = sonde_conn.cursor()
    cdb_path = os.path.join(profile_dir, "cookies.sqlite")
    conn, tmp = copy_and_open_db(cdb_path)
    if conn:
        try:
            c = conn.cursor()
            c.execute("SELECT host, name, value, path, isSecure, expiry FROM moz_cookies")
            for host, cname, val, path, secure, exp in c.fetchall():
                if host and cname and val:
                    s_cur.execute(
                        "INSERT OR REPLACE INTO cookies (host, name, value, path, is_secure, expires) VALUES (?, ?, ?, ?, ?, ?)",
                        (host, cname, val, path or "/", 1 if secure else 0, exp or 0)
                    )
                    cookies_count += 1
            sonde_conn.commit()
        except Exception:
            pass
        finally:
            conn.close()
            if os.path.exists(tmp):
                os.remove(tmp)
    return 0, cookies_count

def run_migration():
    home = os.path.expanduser("~")
    sonde_dir = os.path.join(home, ".config", "sonde")
    os.makedirs(sonde_dir, exist_ok=True)
    sonde_db_path = os.path.join(sonde_dir, "sonde.db")

    s_conn = sqlite3.connect(sonde_db_path)
    s_cur = s_conn.cursor()
    s_cur.execute("""
        CREATE TABLE IF NOT EXISTS passwords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    s_cur.execute("""
        CREATE TABLE IF NOT EXISTS cookies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            host TEXT NOT NULL,
            name TEXT NOT NULL,
            value TEXT NOT NULL,
            path TEXT DEFAULT '/',
            is_secure INTEGER DEFAULT 0,
            expires INTEGER DEFAULT 0,
            UNIQUE(host, name, path)
        )
    """)
    s_cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    s_conn.commit()

    key, iv = get_peanuts_key()

    chromium_search_roots = [
        # Google Chrome Flatpak & Native
        os.path.join(home, ".var/app/com.google.Chrome/config/google-chrome"),
        os.path.join(home, ".config/google-chrome"),
        # Microsoft Edge Flatpak & Native
        os.path.join(home, ".var/app/com.microsoft.Edge/config/microsoft-edge"),
        os.path.join(home, ".config/microsoft-edge"),
        # Chromium & Brave
        os.path.join(home, ".config/chromium"),
        os.path.join(home, ".var/app/org.chromium.Chromium/config/chromium"),
        os.path.join(home, ".config/BraveSoftware/Brave-Browser"),
        os.path.join(home, ".var/app/com.brave.Browser/config/BraveSoftware/Brave-Browser"),
    ]

    total_passwords = 0
    total_cookies = 0
    migrated_sources = []

    for root in chromium_search_roots:
        if not os.path.isdir(root):
            continue
        # Check Default profile and Profile 1..9
        profile_dirs = [os.path.join(root, "Default")] + glob.glob(os.path.join(root, "Profile *"))
        for p_dir in profile_dirs:
            if os.path.isdir(p_dir):
                p_cnt, c_cnt = migrate_chromium_profile(p_dir, key, iv, s_conn)
                if p_cnt > 0 or c_cnt > 0:
                    total_passwords += p_cnt
                    total_cookies += c_cnt
                    migrated_sources.append(os.path.relpath(p_dir, home))

    # Firefox profiles
    firefox_roots = [
        os.path.join(home, ".mozilla/firefox"),
        os.path.join(home, ".var/app/org.mozilla.firefox/.mozilla/firefox")
    ]
    for f_root in firefox_roots:
        if os.path.isdir(f_root):
            for p_dir in glob.glob(os.path.join(f_root, "*.default*")):
                if os.path.isdir(p_dir):
                    p_cnt, c_cnt = migrate_firefox_profile(p_dir, s_conn)
                    if c_cnt > 0:
                        total_cookies += c_cnt
                        migrated_sources.append(os.path.relpath(p_dir, home))

    s_cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('auto_migrated_v1', 'true')")
    s_conn.commit()
    s_conn.close()

    result = {
        "status": "success",
        "passwords_migrated": total_passwords,
        "cookies_migrated": total_cookies,
        "sources": migrated_sources
    }
    print(json.dumps(result))
    return result

if __name__ == "__main__":
    run_migration()
