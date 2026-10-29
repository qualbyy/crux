"""
Password Autofill and Credential Suggestions for Crux Browser
Integrates ~/.config/crux/passwords.json with web forms.
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
            from core.auth import decrypt_vault_data
            with open(PASSWORDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return decrypt_vault_data(data)
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
            from utils.bookmarks import atomic_save_json
            domain = PasswordAutofillManager._extract_domain(url_or_domain)
            never_list = PasswordAutofillManager.load_never_save()
            if domain not in never_list:
                never_list.append(domain)
                atomic_save_json(NEVER_SAVE_FILE, never_list)
            return True
        except Exception as e:
            print(f"[Autofill] Failed to add never_save: {e}")
            return False

    @staticmethod
    def remove_never_save(domain: str) -> bool:
        try:
            from utils.bookmarks import atomic_save_json
            domain_clean = str(domain or "").strip().lower()
            never_list = PasswordAutofillManager.load_never_save()
            never_list = [d for d in never_list if d.lower() != domain_clean]
            atomic_save_json(NEVER_SAVE_FILE, never_list)
            return True
        except Exception as e:
            print(f"[Autofill] Failed to remove never_save: {e}")
            return False

    @staticmethod
    def save_credential(url: str, username: str, password: str = "") -> bool:
        if not url or not username:
            return False
        try:
            from core.auth import encrypt_vault_data
            from utils.bookmarks import atomic_save_json
            vault = PasswordAutofillManager.load_passwords()
            # Check existing
            for entry in vault:
                if entry.get("url") == url and entry.get("username") == username:
                    if password:
                        entry["password"] = password
                    enc = encrypt_vault_data(vault)
                    atomic_save_json(PASSWORDS_FILE, enc)
                    return True

            import time
            vault.append({
                "url": url,
                "username": username,
                "password": password,
                "imported_at": int(time.time())
            })
            enc = encrypt_vault_data(vault)
            atomic_save_json(PASSWORDS_FILE, enc)
            return True
        except Exception as e:
            print(f"[Autofill] Failed to save credential: {e}")
            return False

    @staticmethod
    def should_prompt_save(url: str, username: str, password: str) -> bool:
        if not url or url.startswith(("crux://", "zephyrium://", "zinc://", "about:")):
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
        if not url or url.startswith(("crux://", "zephyrium://", "zinc://", "about:", "data:", "chrome://")):
            return []
        
        try:
            host = PasswordAutofillManager._extract_domain(url)
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
                entry_domain = PasswordAutofillManager._extract_domain(entry_url)
                if not entry_domain:
                    continue
                entry_parts = entry_domain.split(".")
                entry_root = ".".join(entry_parts[-2:]) if len(entry_parts) >= 2 else entry_domain
                if host == entry_domain or host.endswith("." + entry_domain) or entry_domain.endswith("." + host) or (root_domain and root_domain == entry_root):
                    matches.append(entry)
            return matches
        except Exception as e:
            print(f"[Autofill] Error matching URL: {e}")
            return []

    @staticmethod
    def generate_injection_js(matches: List[Dict]) -> str:
        if not matches:
            return ""

        serialized = json.dumps(matches)

        js_code = f"""
        (function() {{
            if (window.__crux_autofill_injected) return;
            window.__crux_autofill_injected = true;

            const credentials = {serialized};
            if (!credentials || credentials.length === 0) return;

            // Helper to set value with React / Vue / Google Closure setter triggers
            function setNativeInputValue(element, val) {{
                if (!element || val === undefined || val === null) return;
                try {{ element.focus(); }} catch(e) {{}}
                const prototype = window.HTMLInputElement.prototype;
                const setter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;
                if (setter) {{
                    setter.call(element, val);
                }} else {{
                    element.value = val;
                }}
                element.dispatchEvent(new Event('input', {{ bubbles: true, composed: true }}));
                try {{
                    element.dispatchEvent(new InputEvent('input', {{ bubbles: true, composed: true, inputType: 'insertText', data: val }}));
                }} catch(e) {{}}
                element.dispatchEvent(new Event('change', {{ bubbles: true, composed: true }}));
                element.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true, cancelable: true }}));
                element.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true, cancelable: true }}));
            }}

            function isSearchInput(el) {{
                if (!el) return true;
                const type = (el.type || '').toLowerCase();
                if (type === 'search') return true;
                const name = (el.name || '').toLowerCase();
                const id = (el.id || '').toLowerCase();
                const role = (el.getAttribute('role') || '').toLowerCase();
                const aria = (el.getAttribute('aria-label') || '').toLowerCase();
                const ph = (el.placeholder || '').toLowerCase();
                const cls = (el.className || '').toLowerCase();

                if (role === 'searchbox' || role === 'search') return true;
                if (['q', 'query', 'search', 'search_query', 's'].includes(name)) return true;
                if (id === 'search' || id.includes('search-input') || id.includes('searchbox')) return true;
                if (aria.includes('search') || aria.includes('поиск') || aria.includes('search github')) return true;
                if (ph.includes('search') || ph.includes('поиск') || ph.includes('find')) return true;
                if (cls.includes('search-input') || cls.includes('header-search')) return true;

                const form = el.form || el.closest('form');
                if (form) {{
                    const fRole = (form.getAttribute('role') || '').toLowerCase();
                    const fAction = (form.getAttribute('action') || '').toLowerCase();
                    if (fRole === 'search' || fAction.includes('search')) return true;
                }}
                return false;
            }}

            function isVisible(el) {{
                if (!el) return false;
                const s = window.getComputedStyle(el);
                if (s.display === 'none' || s.visibility === 'hidden') return false;
                const r = el.getBoundingClientRect();
                return (r.width > 0 && r.height > 0) || el.id === 'identifierId' || el.type === 'password' || (el.name && el.name.toLowerCase() === 'passwd');
            }}

            function findLoginInputs() {{
                const allPwds = Array.from(document.querySelectorAll('input[type="password"], input[name="Passwd" i], input[autocomplete*="password" i]')).filter(el => {{
                    return isVisible(el);
                }});

                const url = window.location.href.toLowerCase();
                const isAuthUrl = /accounts\\.google\\.com|login|signin|sign-in|auth|identifier|session|authorize|oauth|account|log-in|v3\\/signin/i.test(url);

                const userCandidates = Array.from(document.querySelectorAll(
                    'input#identifierId, input[name="identifier"], input[type="email"], ' +
                    'input[autocomplete="username"], input[autocomplete="email"], ' +
                    'input[name="login"], input[name="username"], input[name="user"], input[name="email"], ' +
                    'input#login_field, input#user_login, input#username, ' +
                    'input[id*="username" i], input[id*="login" i], input[name*="username" i], input[name*="login" i]'
                )).filter(el => {{
                    if (isSearchInput(el)) return false;
                    return isVisible(el);
                }});

                // Guard: If there is no password input AND this is not an auth URL, AND no explicit Google identifier/username attribute, ignore!
                if (allPwds.length === 0 && !isAuthUrl) {{
                    const hasExplicitLogin = userCandidates.some(el => el.id === 'identifierId' || el.getAttribute('autocomplete') === 'username');
                    if (!hasExplicitLogin) {{
                        return {{ userInput: null, pwdInput: null }};
                    }}
                }}

                const primaryPwd = allPwds.length > 0 ? allPwds[0] : null;
                let primaryUser = null;

                if (primaryPwd) {{
                    const form = primaryPwd.form || primaryPwd.closest('form');
                    if (form) {{
                        const formInputs = Array.from(form.querySelectorAll('input')).filter(el => !isSearchInput(el) && el !== primaryPwd);
                        const found = formInputs.find(el => {{
                            const t = (el.type || 'text').toLowerCase();
                            return ['text', 'email', 'tel'].includes(t) && isVisible(el);
                        }});
                        if (found) primaryUser = found;
                    }}
                }}

                if (!primaryUser && userCandidates.length > 0) {{
                    primaryUser = userCandidates[0];
                }}

                return {{ userInput: primaryUser, pwdInput: primaryPwd }};
            }}

                return {{ userInput: primaryUser, pwdInput: primaryPwd }};
            }}

            function performAutofill(cred, primaryUser, primaryPwd) {{
                if (primaryUser && cred.username) {{
                    setNativeInputValue(primaryUser, cred.username);
                    window.__crux_active_user = cred.username;
                    try {{
                        sessionStorage.setItem('__crux_last_user', cred.username);
                        if (cred.password) {{
                            sessionStorage.setItem('__crux_last_pass', cred.password);
                        }}
                    }} catch (e) {{}}
                }}

                if (primaryPwd && cred.password) {{
                    setNativeInputValue(primaryPwd, cred.password);
                }}

                // Show confirmation badge
                const pill = document.getElementById('__crux_pill__');
                if (pill) {{
                    pill.style.backgroundColor = '#10b981';
                    pill.style.borderColor = '#10b981';
                    pill.innerHTML = `<span style="color:#ffffff; font-weight:bold;">✓ Заполнено: ${{cred.username}}</span>`;
                    setTimeout(() => pill.remove(), 2000);
                }}
                const menu = document.getElementById('__crux_dropdown__');
                if (menu) menu.remove();
            }}

            function renderDropdown(anchor, primaryUser, primaryPwd) {{
                let menu = document.getElementById('__crux_dropdown__');
                if (!menu) {{
                    menu = document.createElement('div');
                    menu.id = '__crux_dropdown__';
                    menu.style.position = 'absolute';
                    menu.style.zIndex = '2147483647';
                    menu.style.backgroundColor = '#18181b';
                    menu.style.border = '1px solid #38bdf8';
                    menu.style.boxShadow = '0 6px 20px rgba(0,0,0,0.7)';
                    menu.style.fontFamily = 'monospace';
                    menu.style.fontSize = '12px';
                    menu.style.color = '#f5f5f0';
                    menu.style.minWidth = '260px';
                    menu.style.borderRadius = '0px';
                    document.body.appendChild(menu);
                }}

                const rect = anchor.getBoundingClientRect();
                menu.style.top = (rect.bottom + window.scrollY + 2) + 'px';
                menu.style.left = (rect.left + window.scrollX) + 'px';
                menu.style.width = Math.max(rect.width, 260) + 'px';
                menu.innerHTML = '';

                const header = document.createElement('div');
                header.style.padding = '5px 10px';
                header.style.backgroundColor = '#262624';
                header.style.borderBottom = '1px solid #3f3f46';
                header.style.fontSize = '10px';
                header.style.color = '#38bdf8';
                header.style.fontWeight = 'bold';
                header.style.display = 'flex';
                header.style.justifyContent = 'space-between';
                header.innerHTML = '<span>[ ZEPHYRIUM // ХРАНИЛИЩЕ ]</span><span style="cursor:pointer; color:#71717a;" id="__z_close_dd__">×</span>';
                menu.appendChild(header);

                header.querySelector('#__z_close_dd__').onclick = (e) => {{
                    e.stopPropagation();
                    menu.remove();
                }};

                credentials.forEach(cred => {{
                    const item = document.createElement('div');
                    item.style.padding = '8px 10px';
                    item.style.cursor = 'pointer';
                    item.style.borderBottom = '1px solid #27272a';
                    item.style.display = 'flex';
                    item.style.alignItems = 'center';
                    item.style.justifyContent = 'space-between';
                    item.innerHTML = `<div><div style="font-weight:bold; color:#f5f5f0;">${{cred.username}}</div><div style="font-size:10px; color:#71717a;">${{cred.url || ''}}</div></div><button style="background:transparent; border:1px solid #38bdf8; color:#38bdf8; font-family:monospace; font-size:10px; padding:3px 7px; cursor:pointer;">ВСТАВИТЬ</button>`;
                    item.onmouseover = () => {{ item.style.backgroundColor = '#27272a'; }};
                    item.onmouseout = () => {{ item.style.backgroundColor = 'transparent'; }};
                    item.onclick = (e) => {{
                        e.stopPropagation();
                        performAutofill(cred, primaryUser, primaryPwd);
                    }};
                    menu.appendChild(item);
                }});
            }}

            function renderFloatingPill(primaryUser, primaryPwd) {{
                if (document.getElementById('__crux_pill__')) return;
                const pill = document.createElement('div');
                pill.id = '__crux_pill__';
                pill.style.position = 'fixed';
                pill.style.top = '72px';
                pill.style.right = '20px';
                pill.style.zIndex = '2147483647';
                pill.style.backgroundColor = '#18181b';
                pill.style.color = '#f5f5f0';
                pill.style.border = '1px solid #38bdf8';
                pill.style.boxShadow = '0 4px 16px rgba(0,0,0,0.6)';
                pill.style.padding = '7px 12px';
                pill.style.fontFamily = 'monospace';
                pill.style.fontSize = '11px';
                pill.style.display = 'flex';
                pill.style.alignItems = 'center';
                pill.style.gap = '8px';
                pill.style.borderRadius = '0px';

                const cred = credentials[0];
                pill.innerHTML = `<span style="color:#38bdf8; font-weight:bold;">[ZEPHYRIUM]</span> Вход: <strong>${{cred.username}}</strong> <button id="__z_btn_fill__" style="background:#262624; border:1px solid #38bdf8; color:#38bdf8; font-family:monospace; font-size:10px; padding:2px 8px; cursor:pointer; font-weight:bold;">ЗАПОЛНИТЬ</button> <span id="__z_btn_close__" style="cursor:pointer; color:#71717a; font-size:12px; padding:0 2px;">×</span>`;

                pill.querySelector('#__z_btn_fill__').onclick = function(e) {{
                    e.stopPropagation();
                    performAutofill(cred, primaryUser, primaryPwd);
                }};
                pill.querySelector('#__z_btn_close__').onclick = function(e) {{
                    e.stopPropagation();
                    pill.remove();
                }};

                document.body.appendChild(pill);
            }}

            function attachAutofillUI() {{
                const {{ userInput, pwdInput }} = findLoginInputs();
                if (!userInput && !pwdInput) return;

                const primaryCred = credentials[0];

                // Auto-fill username if available and not yet filled
                if (userInput && !userInput.__z_autofilled) {{
                    if (!userInput.value && primaryCred.username) {{
                        setNativeInputValue(userInput, primaryCred.username);
                        userInput.__z_autofilled = true;
                        window.__crux_active_user = primaryCred.username;
                        try {{
                            sessionStorage.setItem('__crux_last_user', primaryCred.username);
                            if (primaryCred.password) {{
                                sessionStorage.setItem('__crux_last_pass', primaryCred.password);
                            }}
                        }} catch(e) {{}}
                    }}
                }}

                // Auto-fill password if available
                if (pwdInput && !pwdInput.__z_autofilled) {{
                    let passToFill = '';
                    if (userInput && primaryCred.password) {{
                        passToFill = primaryCred.password;
                    }} else if (!userInput) {{
                        // Multi-step form (e.g. Google login step 2)
                        let lastUser = '';
                        try {{
                            lastUser = sessionStorage.getItem('__crux_last_user') || window.__crux_active_user || '';
                            passToFill = sessionStorage.getItem('__crux_last_pass') || '';
                        }} catch(e) {{}}
                        if (!passToFill) {{
                            const match = credentials.find(c => c.username === lastUser) || primaryCred;
                            if (match && match.password) passToFill = match.password;
                        }}
                    }}
                    if (passToFill && !pwdInput.value) {{
                        setNativeInputValue(pwdInput, passToFill);
                        pwdInput.__z_autofilled = true;
                    }}
                }}

                // Datalist and interaction listeners
                if (userInput && !userInput.__z_listener_attached) {{
                    userInput.__z_listener_attached = true;
                    let dl = document.getElementById('__crux_datalist__');
                    if (!dl) {{
                        dl = document.createElement('datalist');
                        dl.id = '__crux_datalist__';
                        document.body.appendChild(dl);
                    }}
                    dl.innerHTML = '';
                    credentials.forEach(cred => {{
                        const opt = document.createElement('option');
                        opt.value = cred.username;
                        opt.label = 'Crux Vault';
                        dl.appendChild(opt);
                    }});
                    userInput.setAttribute('list', '__crux_datalist__');

                    userInput.addEventListener('focus', function() {{
                        renderDropdown(userInput, userInput, pwdInput);
                    }});

                    userInput.addEventListener('click', function() {{
                        renderDropdown(userInput, userInput, pwdInput);
                    }});

                    userInput.addEventListener('input', function(e) {{
                        const val = e.target.value;
                        const match = credentials.find(c => c.username === val);
                        if (match && match.password && pwdInput) {{
                            setNativeInputValue(pwdInput, match.password);
                        }}
                    }});
                }}

                if (pwdInput && !pwdInput.__z_listener_attached) {{
                    pwdInput.__z_listener_attached = true;
                    pwdInput.addEventListener('focus', function() {{
                        renderDropdown(pwdInput, userInput, pwdInput);
                    }});
                    pwdInput.addEventListener('click', function() {{
                        renderDropdown(pwdInput, userInput, pwdInput);
                    }});
                }}

                if (userInput || pwdInput) {{
                    renderFloatingPill(userInput, pwdInput);
                }}
            }}

            // Close dropdown when clicking outside
            document.addEventListener('click', function(e) {{
                const dd = document.getElementById('__crux_dropdown__');
                if (dd && !dd.contains(e.target)) {{
                    const isAnchor = (e.target.tagName === 'INPUT' && (e.target.type === 'password' || e.target.type === 'email' || e.target.id === 'identifierId'));
                    if (!isAnchor) {{
                        dd.remove();
                    }}
                }}
            }});

            // Multi-stage checking for SPAs
            attachAutofillUI();
            [200, 500, 1000, 2000, 3500].forEach(delay => {{
                setTimeout(attachAutofillUI, delay);
            }});

            const observer = new MutationObserver(() => {{
                attachAutofillUI();
            }});
            observer.observe(document.body || document.documentElement, {{
                childList: true,
                subtree: true
            }});

            document.addEventListener('focusin', function(e) {{
                if (e.target && e.target.tagName === 'INPUT') {{
                    attachAutofillUI();
                }}
            }}, true);
        }})();
        """
        return js_code

    @staticmethod
    def generate_capture_js() -> str:
        return """
        (function() {
            if (window.__crux_capture_injected) return;
            window.__crux_capture_injected = true;

            // Track any typed username / email across steps (for multi-step logins like Google)
            document.addEventListener('input', function(e) {
                const t = e.target;
                if (!t || t.tagName !== 'INPUT') return;
                const type = (t.type || 'text').toLowerCase();
                if (type === 'password') return;
                const val = (t.value || '').trim();
                if (val && (type === 'email' || t.id === 'identifierId' || t.name === 'identifier' || val.includes('@') || t.getAttribute('autocomplete') === 'username')) {
                    window.__crux_last_user = val;
                    try {
                        sessionStorage.setItem('__crux_last_user', val);
                    } catch (err) {}
                }
            }, true);

            function findUsername(pwdInput) {
                const form = pwdInput.form || pwdInput.closest('form');
                if (form) {
                    const inputs = Array.from(form.querySelectorAll('input'));
                    const pIndex = inputs.indexOf(pwdInput);
                    for (let i = pIndex - 1; i >= 0; i--) {
                        const inp = inputs[i];
                        const t = (inp.type || 'text').toLowerCase();
                        if (['text', 'email', 'tel'].includes(t) && inp.value && inp.value.trim().length > 0) {
                            return inp.value.trim();
                        }
                    }
                    for (let inp of inputs) {
                        const t = (inp.type || 'text').toLowerCase();
                        if (['text', 'email', 'tel'].includes(t) && inp.value && inp.value.trim().length > 0) {
                            return inp.value.trim();
                        }
                    }
                }

                // Check Google profile identifier or text elements on page showing user email
                const profileEl = document.querySelector('#profileIdentifier, [data-email], [data-profile-identifier], div[jsname="wP1ysz"]');
                if (profileEl && profileEl.textContent && profileEl.textContent.trim().length > 0) {
                    return profileEl.textContent.trim();
                }

                // Check stored username from step 1
                if (window.__crux_last_user) {
                    return window.__crux_last_user;
                }
                try {
                    const stored = sessionStorage.getItem('__crux_last_user');
                    if (stored) return stored;
                } catch (err) {}

                // Fallback: look globally for any filled email or username input
                const candidates = document.querySelectorAll('input[type="email"], input[id="identifierId"], input[name*="user" i], input[name*="login" i], input[id*="user" i], input[id*="login" i], input[autocomplete="username" i]');
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

                const cmd = "crux://action/prompt-save-password?url=" + encodeURIComponent(url) +
                            "&username=" + encodeURIComponent(user) +
                            "&password=" + encodeURIComponent(pwd);
                console.log("CRUX_IPC:" + cmd);
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

            // 3. Listen on click of submit / login / Next buttons
            document.addEventListener('click', function(e) {
                const btn = e.target.closest('button, input[type="submit"], [role="button"], #passwordNext, #identifierNext');
                if (btn) {
                    // If on step 1 (identifierNext), capture username to session
                    const idInp = document.querySelector('input[id="identifierId"], input[type="email"]');
                    if (idInp && idInp.value) {
                        window.__crux_last_user = idInp.value.trim();
                        try {
                            sessionStorage.setItem('__crux_last_user', idInp.value.trim());
                        } catch (err) {}
                    }

                    const form = btn.form || btn.closest('form');
                    const pwd = form ? form.querySelector('input[type="password"]') : document.querySelector('input[type="password"]');
                    if (pwd && pwd.value) {
                        setTimeout(() => sendCapture(pwd), 50);
                    }
                }
            }, true);
        })();
        """
