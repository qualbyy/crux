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
