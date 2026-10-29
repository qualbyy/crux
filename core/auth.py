"""
Cross-platform system and vault authentication for Zephyrium Browser.
Features AES-256 / Fernet PBKDF2 encryption for stored credentials.
Supports Linux (sudo) and Windows (LogonUserW WinAPI & master password fallback).
"""
import sys
import os
import json
import base64
import getpass
import platform
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet
from config import CONFIG_DIR

MASTER_KEY_FILE = CONFIG_DIR / "vault_master.hash"
_ACTIVE_VAULT_PASSPHRASE = ""

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def get_machine_seed(legacy: bool = False) -> str:
    if legacy:
        return f"{getpass.getuser()}:{platform.node()}:zephyrium_vault_seed_v1"
    return f"{getpass.getuser()}:{platform.node()}:crux_vault_seed_v1"

def derive_vault_key(passphrase: str = "", legacy: bool = False) -> bytes:
    effective = passphrase if passphrase else _ACTIVE_VAULT_PASSPHRASE or get_machine_seed(legacy)
    salt = b"zephyrium_vault_salt_v1" if legacy else b"crux_vault_salt_v1"
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(effective.encode("utf-8")))

def encrypt_vault_data(data: list, passphrase: str = "") -> dict:
    key = derive_vault_key(passphrase, legacy=False)
    f = Fernet(key)
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return {
        "version": 2,
        "encrypted": True,
        "ciphertext": f.encrypt(raw).decode("utf-8")
    }

def decrypt_vault_data(payload: any, passphrase: str = "") -> list:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and payload.get("encrypted"):
        # Try modern crux key first
        try:
            key = derive_vault_key(passphrase, legacy=False)
            f = Fernet(key)
            raw = f.decrypt(payload["ciphertext"].encode("utf-8"))
            return json.loads(raw.decode("utf-8"))
        except Exception:
            # Fall back to legacy zephyrium key
            try:
                key_leg = derive_vault_key(passphrase, legacy=True)
                f_leg = Fernet(key_leg)
                raw = f_leg.decrypt(payload["ciphertext"].encode("utf-8"))
                return json.loads(raw.decode("utf-8"))
            except Exception:
                pass
    return []

def has_master_password() -> bool:
    return MASTER_KEY_FILE.exists()

def set_master_password(password: str) -> bool:
    global _ACTIVE_VAULT_PASSPHRASE
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        from utils.bookmarks import atomic_save_json
        # Also re-encrypt passwords.json with new master key
        from core.password_autofill import PasswordAutofillManager, PASSWORDS_FILE
        existing_passwords = PasswordAutofillManager.load_passwords()

        with open(MASTER_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(_hash_password(password))

        _ACTIVE_VAULT_PASSPHRASE = password
        if existing_passwords:
            enc_payload = encrypt_vault_data(existing_passwords, password)
            atomic_save_json(PASSWORDS_FILE, enc_payload)

        return True
    except Exception as e:
        print(f"[Auth] Failed to set master password: {e}")
        return False

def verify_vault_password(password: str) -> bool:
    global _ACTIVE_VAULT_PASSPHRASE
    if not password:
        return False

    # Check local master password first if set
    if MASTER_KEY_FILE.exists():
        try:
            with open(MASTER_KEY_FILE, "r", encoding="utf-8") as f:
                saved_hash = f.read().strip()
            if saved_hash and _hash_password(password) == saved_hash:
                _ACTIVE_VAULT_PASSPHRASE = password
                return True
        except Exception as e:
            print(f"[Auth] Error checking master password: {e}")

    # Platform-specific authentication
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            username = getpass.getuser()
            LOGON32_LOGON_INTERACTIVE = 2
            LOGON32_PROVIDER_DEFAULT = 0
            token = wintypes.HANDLE()
            advapi32 = ctypes.windll.advapi32
            kernel32 = ctypes.windll.kernel32

            success = advapi32.LogonUserW(
                username,
                None,
                password,
                LOGON32_LOGON_INTERACTIVE,
                LOGON32_PROVIDER_DEFAULT,
                ctypes.byref(token)
            )
            if success:
                kernel32.CloseHandle(token)
                _ACTIVE_VAULT_PASSPHRASE = password
                return True
        except Exception as e:
            print(f"[Auth] Windows LogonUserW failed: {e}")
        return False
    else:
        # Linux / Unix sudo check
        import subprocess
        try:
            res = subprocess.run(
                ["sudo", "-k", "-S", "-v"],
                input=password.encode("utf-8") + b"\n",
                capture_output=True,
                timeout=6
            )
            if res.returncode == 0:
                _ACTIVE_VAULT_PASSPHRASE = password
                return True
            return False
        except Exception as e:
            print(f"[Auth] Linux sudo verification error: {e}")
            return False

def get_auth_prompt_title(lang: str = "ru") -> str:
    if sys.platform == "win32":
        return "Авторизация Windows" if lang == "ru" else "Windows Authentication"
    return "Авторизация sudo" if lang == "ru" else "Sudo Authentication"

def get_auth_input_placeholder(lang: str = "ru") -> str:
    if sys.platform == "win32":
        return "Пароль Windows..." if lang == "ru" else "Windows password..."
    return "Пароль sudo..." if lang == "ru" else "Sudo password..."
