"""
Password Autofill and Credential Suggestions for Zephyrium Browser
Integrates ~/.config/zephyrium/passwords.json with web forms.
"""
import json
import urllib.parse
from pathlib import Path
from typing import List, Dict, Optional
from config import CONFIG_DIR

PASSWORDS_FILE = CONFIG_DIR / "passwords.json"
NEVER_SAVE_FILE = CONFIG_DIR / "never_save_passwords.json"

class PasswordAutofillManager:
    @staticmethod
    def load_passwords() -> List[Dict]:
        if not PASSWORDS_FILE.exists():
            return []
        try:
            with open(PASSWORDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception as e:
            print(f"[Autofill] Failed to load passwords: {e}")
            return []

    @staticmethod
    def load_never_save() -> List[str]:
        if not NEVER_SAVE_FILE.exists():
            return []
        try:
            with open(NEVER_SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [str(d).lower().strip() for d in data if d] if isinstance(data, list) else []
        except Exception as e:
            print(f"[Autofill] Failed to load never_save: {e}")
            return []

    @staticmethod
    def _extract_domain(url_or_domain: str) -> str:
        s = str(url_or_domain or "").strip().lower()
        if "://" in s:
            try:
                parsed = urllib.parse.urlparse(s)
                return parsed.netloc.lower() or s
            except Exception:
                return s
        return s

    @staticmethod
    def is_never_save(url_or_domain: str) -> bool:
        if not url_or_domain:
            return False
        domain = PasswordAutofillManager._extract_domain(url_or_domain)
        never_list = PasswordAutofillManager.load_never_save()
        for item in never_list:
            if item == domain or domain.endswith("." + item) or item.endswith("." + domain):
                return True
        return False

    @staticmethod
    def add_never_save(url_or_domain: str) -> bool:
        if not url_or_domain:
            return False
        try:
            domain = PasswordAutofillManager._extract_domain(url_or_domain)
            never_list = PasswordAutofillManager.load_never_save()
            if domain not in never_list:
                never_list.append(domain)
                with open(NEVER_SAVE_FILE, "w", encoding="utf-8") as f:
                    json.dump(never_list, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Autofill] Failed to add never_save: {e}")
            return False

    @staticmethod
    def remove_never_save(domain: str) -> bool:
        try:
            domain_clean = str(domain or "").strip().lower()
            never_list = PasswordAutofillManager.load_never_save()
            never_list = [d for d in never_list if d.lower() != domain_clean]
            with open(NEVER_SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(never_list, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Autofill] Failed to remove never_save: {e}")
            return False

    @staticmethod
    def save_credential(url: str, username: str, password: str = "") -> bool:
        if not url or not username:
            return False
        try:
            vault = PasswordAutofillManager.load_passwords()
            # Check existing
            for entry in vault:
                if entry.get("url") == url and entry.get("username") == username:
                    if password:
                        entry["password"] = password
                    with open(PASSWORDS_FILE, "w", encoding="utf-8") as f:
                        json.dump(vault, f, indent=2, ensure_ascii=False)
                    return True

            import time
            vault.append({
                "url": url,
                "username": username,
                "password": password,
                "imported_at": int(time.time())
            })
            with open(PASSWORDS_FILE, "w", encoding="utf-8") as f:
                json.dump(vault, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[Autofill] Failed to save credential: {e}")
            return False

    @staticmethod
    def should_prompt_save(url: str, username: str, password: str) -> bool:
        if not url or url.startswith(("zephyrium://", "zinc://", "about:")):
            return False
        if not password or len(password.strip()) == 0:
            return False
        if PasswordAutofillManager.is_never_save(url):
            return False

        domain = PasswordAutofillManager._extract_domain(url)
        vault = PasswordAutofillManager.load_passwords()
        for entry in vault:
            entry_domain = PasswordAutofillManager._extract_domain(entry.get("url", ""))
            # If domain matches, username matches, and password is identical, do not prompt
            if (entry_domain == domain or domain.endswith("." + entry_domain) or entry_domain.endswith("." + domain)) and \
               entry.get("username", "").strip() == username.strip() and \
               entry.get("password", "") == password:
                return False
        return True

    @staticmethod
    def get_matches_for_url(url: str) -> List[Dict]:
        if not url or url.startswith("zephyrium://") or url.startswith("zinc://") or url.startswith("about:"):
            return []
        
        try:
            parsed = urllib.parse.urlparse(url)
            host = parsed.netloc.lower()
            if not host:
                return []
            
            # Clean common prefixes (e.g. accounts.google.com -> google.com match)
            host_parts = host.split(".")
            root_domain = ".".join(host_parts[-2:]) if len(host_parts) >= 2 else host

            matches = []
            vault = PasswordAutofillManager.load_passwords()
            for entry in vault:
                entry_url = entry.get("url", "")
                if not entry_url:
                    continue
                try:
                    entry_parsed = urllib.parse.urlparse(entry_url)
                    entry_host = entry_parsed.netloc.lower()
                    if host in entry_host or entry_host in host or root_domain in entry_host:
                        matches.append(entry)
                except Exception:
                    continue
            return matches
        except Exception as e:
            print(f"[Autofill] Error matching URL: {e}")
            return []

    @staticmethod
    def generate_injection_js(matches: List[Dict]) -> str:
        if not matches:
            return ""

        # JSON serialize matches safely for embedding
        serialized = json.dumps(matches)

        js_code = f"""
        (function() {{
            if (window.__zephyrium_autofill_injected) return;
            window.__zephyrium_autofill_injected = true;

            const credentials = {serialized};
            if (!credentials || credentials.length === 0) return;

            function initAutofill() {{
                const pwdInputs = document.querySelectorAll('input[type="password"]');
                const userInputs = document.querySelectorAll('input[type="email"], input[name*="user"], input[name*="login"], input[id*="user"], input[id*="login"], input[autocomplete="username"], input[type="text"]');

                if (userInputs.length === 0 && pwdInputs.length === 0) return;

                const primaryUser = userInputs.length > 0 ? userInputs[0] : null;
                const primaryPwd = pwdInputs.length > 0 ? pwdInputs[0] : null;

                // 1. Datalist attached to username input
                if (primaryUser) {{
                    let dl = document.getElementById('__zephyrium_datalist__');
                    if (!dl) {{
                        dl = document.createElement('datalist');
                        dl.id = '__zephyrium_datalist__';
                        document.body.appendChild(dl);
                    }}
                    dl.innerHTML = '';
                    credentials.forEach(cred => {{
                        const opt = document.createElement('option');
                        opt.value = cred.username;
                        opt.label = 'Zephyrium Vault';
                        dl.appendChild(opt);
                    }});
                    primaryUser.setAttribute('list', '__zephyrium_datalist__');

                    primaryUser.addEventListener('input', function(e) {{
                        const entered = e.target.value;
                        const match = credentials.find(c => c.username === entered);
                        if (match && match.password && primaryPwd) {{
                            primaryPwd.value = match.password;
                            primaryPwd.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            primaryPwd.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }});
                }}

                // 2. Interactive Autofill Badge near password field or user field
                const anchor = primaryPwd || primaryUser;
                if (anchor && !document.getElementById('__zephyrium_pill__')) {{
                    const pill = document.createElement('div');
                    pill.id = '__zephyrium_pill__';
                    pill.style.position = 'fixed';
                    pill.style.bottom = '18px';
                    pill.style.right = '20px';
                    pill.style.zIndex = '2147483647';
                    pill.style.backgroundColor = '#18181b';
                    pill.style.color = '#f5f5f0';
                    pill.style.border = '1px solid #38bdf8';
                    pill.style.boxShadow = '0 4px 12px rgba(0,0,0,0.5)';
                    pill.style.padding = '8px 14px';
                    pill.style.fontFamily = 'monospace';
                    pill.style.fontSize = '12px';
                    pill.style.cursor = 'pointer';
                    pill.style.display = 'flex';
                    pill.style.alignItems = 'center';
                    pill.style.gap = '8px';
                    pill.style.transition = 'all 0.2s ease';

                    const cred = credentials[0];
                    pill.innerHTML = `<span style="color: #38bdf8; font-weight: bold;">[ZEPHYRIUM]</span> Autofill <strong>${{cred.username}}</strong> <span style="font-size:10px; color:#71717a;">×</span>`;

                    pill.addEventListener('click', function(e) {{
                        if (e.target.innerText === '×') {{
                            pill.remove();
                            return;
                        }}
                        if (primaryUser) {{
                            primaryUser.value = cred.username;
                            primaryUser.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            primaryUser.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        if (primaryPwd && cred.password) {{
                            primaryPwd.value = cred.password;
                            primaryPwd.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            primaryPwd.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        pill.style.backgroundColor = '#10b981';
                        pill.innerHTML = `<span style="color:#ffffff;">✓ Autofilled!</span>`;
                        setTimeout(() => pill.remove(), 1500);
                    }});

                    document.body.appendChild(pill);
                }}
            }}

            if (document.readyState === 'loading') {{
                document.addEventListener('DOMContentLoaded', initAutofill);
            }} else {{
                initAutofill();
            }}
        }})();
        """
        return js_code

    @staticmethod
    def generate_capture_js() -> str:
        return """
        (function() {
            if (window.__zephyrium_capture_injected) return;
            window.__zephyrium_capture_injected = true;

            function findUsername(pwdInput) {
                const form = pwdInput.form || pwdInput.closest('form');
                if (form) {
                    const inputs = Array.from(form.querySelectorAll('input'));
                    const pIndex = inputs.indexOf(pwdInput);
                    // Search backwards from password input for the nearest text/email input
                    for (let i = pIndex - 1; i >= 0; i--) {
                        const inp = inputs[i];
                        const t = (inp.type || 'text').toLowerCase();
                        if (['text', 'email', 'tel'].includes(t) && inp.value && inp.value.trim().length > 0) {
                            return inp.value.trim();
                        }
                    }
                    // Search forward if not found
                    for (let inp of inputs) {
                        const t = (inp.type || 'text').toLowerCase();
                        if (['text', 'email', 'tel'].includes(t) && inp.value && inp.value.trim().length > 0) {
                            return inp.value.trim();
                        }
                    }
                }
                // Fallback: look globally on page for any filled username/email
                const candidates = document.querySelectorAll('input[type="email"], input[name*="user" i], input[name*="login" i], input[id*="user" i], input[id*="login" i], input[autocomplete="username" i], input[type="text"]');
                for (let inp of candidates) {
                    if (inp.value && inp.value.trim().length > 0 && inp !== pwdInput) {
                        return inp.value.trim();
                    }
                }
                return "";
            }

            function sendCapture(pwdInput) {
                if (!pwdInput || !pwdInput.value) return;
                const pwd = pwdInput.value;
                const user = findUsername(pwdInput);
                const url = window.location.href;
                if (!pwd || pwd.length === 0) return;

                const cmd = "zephyrium://action/prompt-save-password?url=" + encodeURIComponent(url) +
                            "&username=" + encodeURIComponent(user) +
                            "&password=" + encodeURIComponent(pwd);
                console.log("ZEPHYRIUM_IPC:" + cmd);
            }

            // 1. Listen on form submit
            document.addEventListener('submit', function(e) {
                const form = e.target;
                if (form && form.querySelector) {
                    const pwd = form.querySelector('input[type="password"]');
                    if (pwd && pwd.value) {
                        sendCapture(pwd);
                    }
                }
            }, true);

            // 2. Listen on Enter key in password field
            document.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.keyCode === 13) {
                    const t = e.target;
                    if (t && t.type === 'password' && t.value) {
                        sendCapture(t);
                    }
                }
            }, true);

            // 3. Listen on click of submit / login buttons
            document.addEventListener('click', function(e) {
                const btn = e.target.closest('button, input[type="submit"], [role="button"]');
                if (btn) {
                    const form = btn.form || btn.closest('form');
                    const pwd = form ? form.querySelector('input[type="password"]') : document.querySelector('input[type="password"]');
                    if (pwd && pwd.value) {
                        setTimeout(() => sendCapture(pwd), 50);
                    }
                }
            }, true);
        })();
        """
