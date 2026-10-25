"""
Cross-platform system and vault authentication for Zephyrium Browser.
Supports Linux (sudo) and Windows (LogonUserW WinAPI & master password fallback).
"""
import sys
import os
import getpass
import hashlib
from pathlib import Path
from config import CONFIG_DIR

MASTER_KEY_FILE = CONFIG_DIR / "vault_master.hash"

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def has_master_password() -> bool:
    return MASTER_KEY_FILE.exists()

def set_master_password(password: str) -> bool:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(MASTER_KEY_FILE, "w", encoding="utf-8") as f:
            f.write(_hash_password(password))
        return True
    except Exception as e:
        print(f"[Auth] Failed to set master password: {e}")
        return False

def verify_vault_password(password: str) -> bool:
    if not password:
        return False

    # Check local master password first if set
    if MASTER_KEY_FILE.exists():
        try:
            with open(MASTER_KEY_FILE, "r", encoding="utf-8") as f:
                saved_hash = f.read().strip()
            if saved_hash and _hash_password(password) == saved_hash:
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
                return True
        except Exception as e:
            print(f"[Auth] Windows LogonUserW failed: {e}")
            
        # If user has no master password configured yet and Windows logon wasn't matched,
        # allow setting this as the master password on first unlock if requested, or return False
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
            return (res.returncode == 0)
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
