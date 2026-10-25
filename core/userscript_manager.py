"""
Userscript & UserCSS Extension Engine for Zephyrium Browser
Compatible with Violentmonkey / Greasemonkey metadata format (// ==UserScript==)
and user stylesheets. Injects via native Chromium QWebEngineScriptCollection.
"""
import os
import re
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from PyQt6.QtCore import QObject, pyqtSignal, QUrl
from PyQt6.QtWebEngineCore import QWebEngineScript, QWebEngineProfile
from config import CONFIG_DIR

SCRIPTS_DIR = CONFIG_DIR / "userscripts"
STYLES_DIR = CONFIG_DIR / "userstyles"
META_FILE = CONFIG_DIR / "extensions_meta.json"

SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
STYLES_DIR.mkdir(parents=True, exist_ok=True)


class UserscriptManager(QObject):
    scripts_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.meta: Dict[str, Any] = self._load_meta()

    def _load_meta(self) -> Dict[str, Any]:
        if META_FILE.exists():
            try:
                with open(META_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"userscripts": {}, "userstyles": {}}

    def _save_meta(self) -> None:
        try:
            with open(META_FILE, "w", encoding="utf-8") as f:
                json.dump(self.meta, f, indent=2, ensure_ascii=False)
            self.scripts_changed.emit()
        except Exception as e:
            print(f"Error saving extensions meta: {e}")

    def parse_userscript_metadata(self, code: str) -> Dict[str, Any]:
        meta = {
            "name": "Unnamed Script",
            "matches": [],
            "run_at": "document-end",
            "description": "",
            "version": "1.0"
        }
        in_meta = False
        for line in code.splitlines():
            line = line.strip()
            if "// ==UserScript==" in line:
                in_meta = True
                continue
            if "// ==/UserScript==" in line:
                break
            if in_meta and line.startswith("//"):
                content = line[2:].strip()
                if content.startswith("@name"):
                    meta["name"] = content[5:].strip()
                elif content.startswith("@match"):
                    meta["matches"].append(content[6:].strip())
                elif content.startswith("@include"):
                    meta["matches"].append(content[8:].strip())
                elif content.startswith("@run-at"):
                    meta["run_at"] = content[7:].strip()
                elif content.startswith("@description"):
                    meta["description"] = content[12:].strip()
                elif content.startswith("@version"):
                    meta["version"] = content[8:].strip()
        return meta

    def save_script(self, filename: str, code: str, enabled: bool = True) -> Dict[str, Any]:
        if not filename.endswith(".user.js"):
            filename += ".user.js"
        fpath = SCRIPTS_DIR / filename
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(code)

        parsed = self.parse_userscript_metadata(code)
        parsed["filename"] = filename
        parsed["enabled"] = enabled
        self.meta["userscripts"][filename] = parsed
        self._save_meta()
        return parsed

    def save_style(self, filename: str, css: str, match: str = "*", enabled: bool = True) -> Dict[str, Any]:
        if not filename.endswith(".user.css"):
            filename += ".user.css"
        fpath = STYLES_DIR / filename
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(css)

        meta = {
            "name": filename.replace(".user.css", ""),
            "filename": filename,
            "match": match,
            "enabled": enabled
        }
        self.meta["userstyles"][filename] = meta
        self._save_meta()
        return meta

    def toggle_script(self, filename: str) -> bool:
        if filename in self.meta["userscripts"]:
            cur = self.meta["userscripts"][filename].get("enabled", True)
            self.meta["userscripts"][filename]["enabled"] = not cur
            self._save_meta()
            return not cur
        return False

    def toggle_style(self, filename: str) -> bool:
        if filename in self.meta["userstyles"]:
            cur = self.meta["userstyles"][filename].get("enabled", True)
            self.meta["userstyles"][filename]["enabled"] = not cur
            self._save_meta()
            return not cur
        return False

    def delete_script(self, filename: str) -> None:
        fpath = SCRIPTS_DIR / filename
        if fpath.exists():
            fpath.unlink()
        if filename in self.meta["userscripts"]:
            del self.meta["userscripts"][filename]
            self._save_meta()

    def delete_style(self, filename: str) -> None:
        fpath = STYLES_DIR / filename
        if fpath.exists():
            fpath.unlink()
        if filename in self.meta["userstyles"]:
            del self.meta["userstyles"][filename]
            self._save_meta()

    def list_all(self) -> Dict[str, Any]:
        return {
            "userscripts": list(self.meta.get("userscripts", {}).values()),
            "userstyles": list(self.meta.get("userstyles", {}).values())
        }

    def apply_to_profile(self, profile: QWebEngineProfile) -> None:
        """Compiles and registers all active userscripts and userstyles into QWebEngineProfile."""
        try:
            scripts_collection = profile.scripts()
            # Clear previously injected custom extensions
            for s in scripts_collection.toList():
                if s.name().startswith("zephyrium_user_"):
                    scripts_collection.remove(s)

            # 1. Ingest Userscripts
            for fn, meta in self.meta.get("userscripts", {}).items():
                if not meta.get("enabled", True):
                    continue
                fpath = SCRIPTS_DIR / fn
                if not fpath.exists():
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        code = f.read()

                    script = QWebEngineScript()
                    script.setName(f"zephyrium_user_js_{fn}")
                    script.setSourceCode(code)
                    if meta.get("run_at") == "document-start":
                        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
                    else:
                        script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
                    script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
                    script.setRunsOnSubFrames(True)
                    scripts_collection.insert(script)
                except Exception as e:
                    print(f"Error loading userscript {fn}: {e}")

            # 2. Ingest UserStyles (wrapped as stylesheet injection scripts)
            for fn, meta in self.meta.get("userstyles", {}).items():
                if not meta.get("enabled", True):
                    continue
                fpath = STYLES_DIR / fn
                if not fpath.exists():
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        css = f.read()
                    escaped_css = css.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
                    inject_js = f"""
                    (function() {{
                        const styleId = 'zephyrium-style-{fn}';
                        if (!document.getElementById(styleId)) {{
                            const st = document.createElement('style');
                            st.id = styleId;
                            st.textContent = `{escaped_css}`;
                            (document.head || document.documentElement).appendChild(st);
                        }}
                    }})();
                    """
                    script = QWebEngineScript()
                    script.setName(f"zephyrium_user_css_{fn}")
                    script.setSourceCode(inject_js)
                    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
                    script.setWorldId(QWebEngineScript.ScriptWorldId.ApplicationWorld)
                    script.setRunsOnSubFrames(True)
                    scripts_collection.insert(script)
                except Exception as e:
                    print(f"Error loading userstyle {fn}: {e}")
        except Exception as e:
            print(f"Error applying extensions to profile: {e}")
