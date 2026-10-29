"""
Claude Code Terminal AI Assistant Panel for Zephyrium
Aesthetic: Anthropic Minimal Dark / Terminal Interface
Features: Dynamic Gemini Model Fetching & Recommendation Algorithm,
In-Browser Key Setup, and Interactive Page Q&A.
"""
import os
import re
import html
import json
import urllib.request
from typing import List, Tuple
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextBrowser,
    QLineEdit, QPushButton, QFrame, QDialog, QComboBox, QListView
)
from config import load_settings, save_settings
from core.i18n import t, get_current_language, LANGUAGES

def format_markdown_to_html(md_text: str, accent: str = "#fe8019") -> str:
    """
    Renders Markdown text to rich HTML with styled code blocks,
    inline code, bold, italic, headers, bullet lists, and links.
    """
    # 1. Extract and preserve code blocks
    code_blocks = []
    def save_code_block(match):
        lang = match.group(1) or ""
        code = match.group(2)
        idx = len(code_blocks)
        escaped_code = html.escape(code.strip("\n"))
        lang_badge = f"<div style='color: #71717a; font-size: 10px; font-weight: bold; margin-bottom: 4px; border-bottom: 1px solid #3f3f46; padding-bottom: 2px;'>{html.escape(lang.upper())}</div>" if lang else ""
        html_block = (
            f"<div style='background-color: #18181b; border: 1px solid #3f3f46; padding: 8px 10px; margin: 6px 0; font-family: monospace;'>"
            f"{lang_badge}"
            f"<pre style='margin: 0; padding: 0; color: #f5f5f0; font-size: 11px; white-space: pre-wrap; word-break: break-all;'>"
            f"<code>{escaped_code}</code></pre></div>"
        )
        code_blocks.append(html_block)
        return f"@@CODEBLOCK{idx}@@"

    text = re.sub(r'```([a-zA-Z0-9_\-\+]*)\n(.*?)```', save_code_block, md_text, flags=re.DOTALL)

    # 2. Extract inline code
    inline_codes = []
    def save_inline_code(match):
        code = match.group(1)
        idx = len(inline_codes)
        escaped_code = html.escape(code)
        html_code = f"<code style='background-color: #27272a; color: {accent}; padding: 1px 4px; border: 1px solid #3f3f46; font-family: monospace; font-size: 11px;'>{escaped_code}</code>"
        inline_codes.append(html_code)
        return f"@@INLINECODE{idx}@@"

    text = re.sub(r'`([^`\n]+)`', save_inline_code, text)

    # 3. Escape HTML for the rest
    text = html.escape(text)

    # 4. Headers (###, ##, #)
    text = re.sub(r'^###\s+(.*)$', r"<h4 style='color: #f5f5f0; margin: 8px 0 4px 0; font-size: 12px; font-weight: bold;'>\1</h4>", text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.*)$', r"<h3 style='color: #f5f5f0; margin: 10px 0 4px 0; font-size: 13px; font-weight: bold;'>\1</h3>", text, flags=re.MULTILINE)
    text = re.sub(r'^#\s+(.*)$', r"<h2 style='color: #f5f5f0; margin: 12px 0 6px 0; font-size: 14px; font-weight: bold;'>\1</h2>", text, flags=re.MULTILINE)

    # 5. Bold & Italic
    text = re.sub(r'\*\*(.+?)\*\*', r"<b style='color: #f5f5f0;'>\1</b>", text)
    text = re.sub(r'\*(.+?)\*', r"<i>\1</i>", text)

    # 6. Bullet lists
    text = re.sub(r'^[*\-]\s+(.*)$', r"<div style='margin-left: 12px;'>• \1</div>", text, flags=re.MULTILINE)

    # 7. Convert line breaks (except where block tags handled it)
    text = text.replace("\n", "<br>")

    # 8. Restore inline code
    for idx, html_code in enumerate(inline_codes):
        text = text.replace(f"@@INLINECODE{idx}@@", html_code)

    # 9. Restore code blocks
    for idx, html_block in enumerate(code_blocks):
        text = text.replace(f"@@CODEBLOCK{idx}@@", html_block)

    return text

def rank_and_format_models(models: List[str]) -> List[Tuple[str, str]]:
    """
    Ranks models giving priority to Flash-Lite and Flash,
    returns tuples of (display_label, model_id).
    """
    recommended = []
    others = []

    for m in models:
        # Avoid embedding, tts, and vision-only models
        if any(x in m.lower() for x in ["tts", "embedding", "imagen", "audio", "whisper"]):
            continue

        if "flash-lite" in m.lower() or "3.8-flash-lite" in m.lower():
            recommended.append((f"{m} [LIGHT & FAST]", m, 1))
        elif "flash" in m.lower():
            recommended.append((f"{m} [RECOMMENDED]", m, 2))
        elif "pro" in m.lower():
            others.append((f"{m} [DEEP REASONING]", m, 3))
        else:
            others.append((m, m, 4))

    recommended.sort(key=lambda x: (x[2], x[1]))
    others.sort(key=lambda x: (x[2], x[1]))
    all_sorted = recommended + others
    return [(label, mid) for label, mid, _ in all_sorted]


class ModelFetcherWorker(QThread):
    models_fetched = pyqtSignal(list)

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key

    def run(self):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={self.api_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "Zephyrium/1.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                raw_models = [
                    m["name"].replace("models/", "")
                    for m in data.get("models", [])
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
                ranked = rank_and_format_models(raw_models)
                self.models_fetched.emit(ranked)
        except Exception as e:
            fallback = [
                ("gemini-flash-lite-latest [LIGHT & FAST]", "gemini-flash-lite-latest"),
                ("gemini-2.5-flash [RECOMMENDED]", "gemini-2.5-flash"),
                ("gemini-2.5-pro [DEEP REASONING]", "gemini-2.5-pro"),
            ]
            self.models_fetched.emit(fallback)


class GeminiWorker(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, query: str, api_key: str, model: str = "gemini-2.5-flash", system_instruction: str = None):
        super().__init__()
        self.query = query
        self.api_key = api_key
        self.model = model
        self.system_instruction = system_instruction

    def run(self):
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            payload = {
                "contents": [{"parts": [{"text": self.query}]}]
            }
            if self.system_instruction:
                payload["systemInstruction"] = {
                    "parts": [{"text": self.system_instruction}]
                }
            
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode())
                candidates = result.get("candidates", [])
                if candidates and "content" in candidates[0]:
                    parts = candidates[0]["content"].get("parts", [])
                    if parts:
                        text = parts[0].get("text", "")
                        self.response_ready.emit(text)
                        return
                self.error_occurred.emit("Empty response received from Gemini API.")
        except Exception as e:
            self.error_occurred.emit(str(e))


class OllamaWorker(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, query: str, base_url: str = "http://localhost:11434", model: str = "llama3", system_instruction: str = None):
        super().__init__()
        self.query = query
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self.model = model or "llama3"
        self.system_instruction = system_instruction

    def run(self):
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": self.query,
                "stream": False
            }
            if self.system_instruction:
                payload["system"] = self.system_instruction

            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                response_text = data.get("response", "")
                if response_text:
                    self.response_ready.emit(response_text)
                    return
                self.error_occurred.emit("Empty response received from Ollama.")
        except Exception as e:
            self.error_occurred.emit(f"Ollama connection error: {e}")


class OllamaDetectorWorker(QThread):
    ollama_detected = pyqtSignal(bool, list)  # (is_online, models_list)

    def __init__(self, base_url: str = "http://localhost:11434"):
        super().__init__()
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")

    def run(self):
        try:
            url = f"{self.base_url}/api/tags"
            req = urllib.request.Request(url, headers={"User-Agent": "Zephyrium/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name") for m in data.get("models", []) if m.get("name")]
                    self.ollama_detected.emit(True, models)
                    return
        except Exception:
            pass
        self.ollama_detected.emit(False, [])


class KeyConfigDialog(QDialog):
    key_saved = pyqtSignal(str)
    config_saved = pyqtSignal(dict)

    def __init__(self, current_key: str, accent: str = "#fe8019", parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setFixedSize(500, 320)
        self.accent = accent
        self.settings = load_settings()
        self.setStyleSheet(f"""
            QDialog {{
                background-color: #18181b;
                border: 1px solid #94a3b8;
            }}
            QLabel {{
                color: #d4d4d8;
                font-family: "Iosevka Nerd Font", monospace;
                font-size: 11px;
            }}
            QLineEdit, QComboBox {{
                background-color: #262624;
                border: 1px solid #3f3f46;
                color: #f5f5f0;
                font-family: "Iosevka Nerd Font", monospace;
                font-size: 11px;
                padding: 5px 8px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {accent};
            }}
            QPushButton {{
                background-color: #262624;
                border: 1px solid #3f3f46;
                color: #d4d4d8;
                font-family: "Iosevka Nerd Font", monospace;
                font-size: 11px;
                padding: 5px 12px;
            }}
            QPushButton:hover {{
                border-color: #94a3b8;
                color: #f5f5f0;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel(f"AI ASSISTANT CONFIGURATION // GEMINI & OLLAMA")
        title.setStyleSheet(f"color: {accent}; font-weight: bold; font-size: 11px; letter-spacing: 1px;")
        layout.addWidget(title)

        # Provider Selector
        row_prov = QHBoxLayout()
        lbl_p = QLabel("ACTIVE PROVIDER:")
        lbl_p.setFixedWidth(130)
        self.combo_provider = QComboBox()
        self.combo_provider.addItem("Google Gemini (Cloud)", "gemini")
        self.combo_provider.addItem("Ollama (Local / Self-hosted)", "ollama")
        cur_prov = self.settings.get("ai_provider", "gemini")
        self.combo_provider.setCurrentIndex(1 if cur_prov == "ollama" else 0)
        row_prov.addWidget(lbl_p)
        row_prov.addWidget(self.combo_provider)
        layout.addLayout(row_prov)

        # Gemini Section
        lbl_gem_title = QLabel("--- GOOGLE GEMINI SETTINGS ---")
        lbl_gem_title.setStyleSheet("color: #71717a; font-weight: bold;")
        layout.addWidget(lbl_gem_title)

        row_key = QHBoxLayout()
        lbl_k = QLabel("GEMINI API KEY:")
        lbl_k.setFixedWidth(130)
        self.input_key = QLineEdit(current_key)
        self.input_key.setPlaceholderText("AIzaSy... / AQ.Ab8...")
        self.input_key.setEchoMode(QLineEdit.EchoMode.PasswordEchoOnEdit)
        row_key.addWidget(lbl_k)
        row_key.addWidget(self.input_key)
        layout.addLayout(row_key)

        # Ollama Section
        lbl_oll_title = QLabel("--- OLLAMA LOCAL LLM SETTINGS ---")
        lbl_oll_title.setStyleSheet("color: #71717a; font-weight: bold;")
        layout.addWidget(lbl_oll_title)

        row_url = QHBoxLayout()
        lbl_u = QLabel("SERVER URL:")
        lbl_u.setFixedWidth(130)
        self.input_ollama_url = QLineEdit(self.settings.get("ollama_url", "http://localhost:11434"))
        row_url.addWidget(lbl_u)
        row_url.addWidget(self.input_ollama_url)
        layout.addLayout(row_url)

        row_m = QHBoxLayout()
        lbl_m = QLabel("DEFAULT MODEL:")
        lbl_m.setFixedWidth(130)
        self.input_ollama_model = QLineEdit(self.settings.get("ollama_model", "llama3"))
        row_m.addWidget(lbl_m)
        row_m.addWidget(self.input_ollama_model)
        layout.addLayout(row_m)

        # Test Ollama Button & status
        row_test = QHBoxLayout()
        self.btn_test = QPushButton("TEST OLLAMA CONNECTION")
        self.btn_test.clicked.connect(self._test_ollama)
        self.lbl_test_status = QLabel("Status: Idle")
        self.lbl_test_status.setStyleSheet("color: #71717a;")
        row_test.addWidget(self.btn_test)
        row_test.addWidget(self.lbl_test_status)
        row_test.addStretch()
        layout.addLayout(row_test)

        layout.addStretch()

        btns_layout = QHBoxLayout()
        btns_layout.addStretch()

        btn_cancel = QPushButton(t("cancel").upper())
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton(t("save_settings").upper())
        btn_save.setStyleSheet(f"border-color: {accent}; color: {accent}; font-weight: bold;")
        btn_save.clicked.connect(self._save)

        btns_layout.addWidget(btn_cancel)
        btns_layout.addWidget(btn_save)
        layout.addLayout(btns_layout)

    def _test_ollama(self):
        self.lbl_test_status.setText("Checking...")
        self.lbl_test_status.setStyleSheet("color: #38bdf8;")
        self.test_worker = OllamaDetectorWorker(self.input_ollama_url.text().strip())
        self.test_worker.ollama_detected.connect(self._on_test_result)
        self.test_worker.start()

    def _on_test_result(self, is_online: bool, models: list):
        if is_online:
            count = len(models)
            model_info = f"Online ({count} models: {', '.join(models[:3])})" if models else "Online (No models)"
            self.lbl_test_status.setText(model_info[:40])
            self.lbl_test_status.setStyleSheet("color: #10b981; font-weight: bold;")
        else:
            self.lbl_test_status.setText("Offline / Unreachable")
            self.lbl_test_status.setStyleSheet("color: #ef4444; font-weight: bold;")

    def _save(self):
        key = self.input_key.text().strip()
        provider = self.combo_provider.currentData()
        ollama_url = self.input_ollama_url.text().strip() or "http://localhost:11434"
        ollama_model = self.input_ollama_model.text().strip() or "llama3"

        self.key_saved.emit(key)
        self.config_saved.emit({
            "gemini_api_key": key,
            "ai_provider": provider,
            "ollama_url": ollama_url,
            "ollama_model": ollama_model,
        })
        self.accept()


class AIChatWidget(QWidget):
    ask_context_page = pyqtSignal()  # Request active tab content

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("aiWidget")

        self.settings = load_settings()
        self.api_key = self.settings.get("gemini_api_key", "").strip()
        self.provider = self.settings.get("ai_provider", "gemini")
        self.active_model = self.settings.get("ai_model", "gemini-2.5-flash")
        self.ollama_url = self.settings.get("ollama_url", "http://localhost:11434")
        self.ollama_model = self.settings.get("ollama_model", "llama3")
        self.accent = self.settings.get("accent_color", "#fe8019")
        self.cached_page_context = ""
        self.worker = None
        self.ollama_online = False
        self.ollama_models = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header 1: Title, Provider Switcher, Status, Config Button
        header = QHBoxLayout()
        header.setSpacing(6)
        self.title_lbl = QLabel("ZEPHYRIUM // AI")
        self.title_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {self.accent}; letter-spacing: 1px;")
        
        self.btn_provider = QPushButton(f"[{self.provider.upper()}]")
        self.btn_provider.setFixedHeight(24)
        self.btn_provider.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_provider.setStyleSheet(f"font-size: 10px; font-weight: bold; color: {self.accent}; border: 1px solid #3f3f46; padding: 0 6px;")
        self.btn_provider.setToolTip("Click to toggle AI provider (GEMINI / OLLAMA)")
        self.btn_provider.clicked.connect(self._toggle_provider)

        self.status = QLabel()
        self.status.setFixedHeight(24)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_key = QPushButton(t("key_btn"))
        self.btn_key.setFixedHeight(24)
        self.btn_key.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_key.setStyleSheet("font-size: 10px; padding: 0px 8px; font-weight: bold; min-height: 22px; max-height: 24px;")
        self.btn_key.setToolTip("Configure Gemini API Key & Ollama Local LLM")
        self.btn_key.clicked.connect(self.open_key_dialog)

        header.addWidget(self.title_lbl)
        header.addStretch()
        header.addWidget(self.btn_provider)
        header.addWidget(self.status)
        header.addWidget(self.btn_key)
        layout.addLayout(header)

        # Header 2: Dynamic Model Selector
        model_row = QHBoxLayout()
        model_row.setSpacing(6)
        self.model_lbl = QLabel(f"{t('ai_model_label').split(':')[0].upper()}:")
        self.model_lbl.setFixedHeight(30)
        self.model_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.model_lbl.setStyleSheet("color: #71717a; font-size: 10px; font-weight: bold; padding: 0px 8px; border: 1px solid #3f3f46; background-color: #262624; min-height: 28px; max-height: 28px;")
        
        self.combo_model = QComboBox()
        self.combo_model.setObjectName("aiModelCombo")
        self.combo_model.setFixedHeight(30)
        self.combo_model.setView(QListView())
        self.combo_model.setMaxVisibleItems(10)
        self.combo_model.setStyleSheet("""
            QComboBox#aiModelCombo {
                min-height: 28px;
                max-height: 28px;
                padding: 0px 8px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        self.combo_model.currentIndexChanged.connect(self._on_model_changed)

        model_row.addWidget(self.model_lbl)
        model_row.addWidget(self.combo_model, stretch=1)
        layout.addLayout(model_row)

        # Chat Transcript
        self.transcript = QTextBrowser()
        self.transcript.setOpenExternalLinks(True)
        layout.addWidget(self.transcript)

        # Quick Actions (Symmetric equal width buttons)
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        self.btn_summarize = QPushButton(t("summarize_page"))
        self.btn_summarize.setFixedHeight(30)
        self.btn_summarize.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_summarize.clicked.connect(self._on_summarize_clicked)
        
        self.btn_clear = QPushButton(t("clear_chat"))
        self.btn_clear.setFixedHeight(30)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self.clear_transcript)

        actions_layout.addWidget(self.btn_summarize, stretch=1)
        actions_layout.addWidget(self.btn_clear, stretch=1)
        layout.addLayout(actions_layout)

        # Input Box
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        self.input_field = QLineEdit()
        self.input_field.setFixedHeight(32)
        self.input_field.setStyleSheet("min-height: 30px; max-height: 30px; padding: 0px 8px;")
        self.input_field.setPlaceholderText(t("ai_input_placeholder"))
        self.input_field.returnPressed.connect(self._on_send)

        self.btn_send = QPushButton(t("run_btn"))
        self.btn_send.setObjectName("accentWarmBtn")
        self.btn_send.setFixedHeight(32)
        self.btn_send.setStyleSheet(f"min-height: 30px; max-height: 30px; padding: 0px 14px; border: 1px solid {self.accent}; color: {self.accent}; font-weight: bold;")
        self.btn_send.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_send.clicked.connect(self._on_send)

        input_layout.addWidget(self.input_field, stretch=1)
        input_layout.addWidget(self.btn_send)
        layout.addLayout(input_layout)

        self._update_status_display()
        self._update_model_list()

        # Start Ollama auto-detector in background
        self.ollama_detector = OllamaDetectorWorker(self.ollama_url)
        self.ollama_detector.ollama_detected.connect(self._on_ollama_detected)
        self.ollama_detector.start()

    def _toggle_provider(self):
        new_provider = "ollama" if self.provider == "gemini" else "gemini"
        self._set_provider(new_provider)

    def _set_provider(self, prov: str):
        self.provider = prov
        self.settings["ai_provider"] = prov
        save_settings(self.settings)
        self.btn_provider.setText(f"[{self.provider.upper()}]")
        self._update_status_display()
        self._update_model_list()
        self._append_system(f"Switched AI Provider to: {self.provider.upper()}")

    def _on_ollama_detected(self, is_online: bool, models: list):
        self.ollama_online = is_online
        self.ollama_models = models
        if self.provider == "ollama":
            self._update_status_display()
            self._update_model_list()

    def _update_model_list(self):
        if self.provider == "ollama":
            items = []
            if self.ollama_models:
                for m in self.ollama_models:
                    items.append((f"{m} [LOCAL]", m))
            else:
                items = [
                    (f"{self.ollama_model} [LOCAL DEFAULT]", self.ollama_model),
                    ("llama3 [LOCAL]", "llama3"),
                    ("mistral [LOCAL]", "mistral"),
                    ("deepseek-r1 [LOCAL]", "deepseek-r1"),
                    ("qwen2.5 [LOCAL]", "qwen2.5"),
                ]
            self.combo_model.blockSignals(True)
            self.combo_model.clear()
            sel_idx = 0
            for i, (label, mid) in enumerate(items):
                self.combo_model.addItem(label, mid)
                if mid == self.ollama_model or mid == self.active_model:
                    sel_idx = i
            self.combo_model.setCurrentIndex(sel_idx)
            self.combo_model.blockSignals(False)
        else:
            if self.api_key:
                self._fetch_models()
            else:
                initial_models = [
                    ("gemini-2.5-flash [RECOMMENDED]", "gemini-2.5-flash"),
                    ("gemini-flash-lite-latest [LIGHT & FAST]", "gemini-flash-lite-latest"),
                    ("gemini-2.5-pro [DEEP REASONING]", "gemini-2.5-pro"),
                    ("gemini-2.0-flash [STABLE]", "gemini-2.0-flash"),
                ]
                self._on_models_fetched(initial_models)

    def _fetch_models(self) -> None:
        self.model_fetcher = ModelFetcherWorker(self.api_key)
        self.model_fetcher.models_fetched.connect(self._on_models_fetched)
        self.model_fetcher.start()

    def _on_models_fetched(self, models: List[Tuple[str, str]]) -> None:
        if self.provider != "gemini":
            return
        self.combo_model.blockSignals(True)
        self.combo_model.clear()
        selected_idx = 0
        for i, (label, mid) in enumerate(models):
            self.combo_model.addItem(label, mid)
            if mid == self.active_model:
                selected_idx = i
        self.combo_model.setCurrentIndex(selected_idx)
        self.combo_model.blockSignals(False)

    def _on_model_changed(self, index: int) -> None:
        mid = self.combo_model.currentData()
        if mid:
            if self.provider == "ollama":
                self.ollama_model = mid
                self.settings["ollama_model"] = mid
            else:
                self.active_model = mid
                self.settings["ai_model"] = mid
            save_settings(self.settings)
            self._append_system(f"Switched model to: {mid}")

    def _update_status_display(self) -> None:
        if self.provider == "ollama":
            if self.ollama_online:
                self.status.setText("OLLAMA // ONLINE")
                self.status.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold; border: 1px solid #10b981; padding: 0px 6px; min-height: 22px; max-height: 24px;")
            else:
                self.status.setText("OLLAMA // OFFLINE")
                self.status.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: bold; border: 1px solid #f59e0b; padding: 0px 6px; min-height: 22px; max-height: 24px;")
        else:
            if self.api_key:
                self.status.setText(t("ai_online"))
                self.status.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold; border: 1px solid #10b981; padding: 0px 6px; min-height: 22px; max-height: 24px;")
            else:
                self.status.setText(t("ai_no_key"))
                self.status.setStyleSheet("color: #f59e0b; font-size: 10px; font-weight: bold; border: 1px solid #f59e0b; padding: 0px 6px; min-height: 22px; max-height: 24px;")

    def retranslate_ui(self) -> None:
        self.btn_key.setText(t("key_btn"))
        self.btn_summarize.setText(t("summarize_page"))
        self.btn_clear.setText(t("clear_chat"))
        self.btn_send.setText(t("run_btn"))
        self.input_field.setPlaceholderText(t("ai_input_placeholder"))
        if hasattr(self, "model_lbl"):
            self.model_lbl.setText(f"{t('ai_model_label').split(':')[0].upper()}:")
        self._update_status_display()

    def open_key_dialog(self) -> None:
        dlg = KeyConfigDialog(self.api_key, accent=getattr(self, "accent", "#fe8019"), parent=self)
        dlg.key_saved.connect(self.save_api_key)
        dlg.config_saved.connect(self._on_config_saved)
        dlg.exec()

    def _on_config_saved(self, cfg: dict) -> None:
        self.api_key = cfg.get("gemini_api_key", "").strip()
        self.provider = cfg.get("ai_provider", "gemini")
        self.ollama_url = cfg.get("ollama_url", "http://localhost:11434").strip()
        self.ollama_model = cfg.get("ollama_model", "llama3").strip()
        self.settings.update(cfg)
        save_settings(self.settings)
        self.btn_provider.setText(f"[{self.provider.upper()}]")
        self._update_status_display()
        self._update_model_list()
        self._append_system("AI configuration updated and saved.")
        self.ollama_detector = OllamaDetectorWorker(self.ollama_url)
        self.ollama_detector.ollama_detected.connect(self._on_ollama_detected)
        self.ollama_detector.start()

    def save_api_key(self, new_key: str) -> None:
        self.api_key = new_key.strip()
        self.settings["gemini_api_key"] = self.api_key
        save_settings(self.settings)
        self._update_status_display()
        self._append_system("Gemini API Key updated and saved to settings.")
        if self.provider == "gemini":
            self._fetch_models()

    def reload_settings(self) -> None:
        self.settings = load_settings()
        self.api_key = self.settings.get("gemini_api_key", "").strip()
        self.provider = self.settings.get("ai_provider", "gemini")
        self.active_model = self.settings.get("ai_model", "gemini-2.5-flash")
        self.ollama_url = self.settings.get("ollama_url", "http://localhost:11434")
        self.ollama_model = self.settings.get("ollama_model", "llama3")
        self.accent = self.settings.get("accent_color", "#fe8019")
        self.btn_provider.setText(f"[{self.provider.upper()}]")
        self._update_status_display()
        self._update_model_list()

    def _append_system(self, msg: str) -> None:
        self.transcript.append(f"<div style='color: #71717a; margin-bottom: 8px;'>[SYSTEM] {msg}</div>")

    def _append_user(self, msg: str) -> None:
        self.transcript.append(
            f"<div style='margin-top: 8px; margin-bottom: 4px;'>"
            f"<span style='color: #94a3b8; font-weight: bold;'>&gt; USER:</span> "
            f"<span style='color: #f5f5f0;'>{msg}</span>"
            f"</div>"
        )

    def _append_assistant(self, msg: str) -> None:
        formatted = format_markdown_to_html(msg, self.accent)
        prov_tag = "OLLAMA" if self.provider == "ollama" else "GEMINI"
        model_tag = self.ollama_model if self.provider == "ollama" else self.active_model
        self.transcript.append(
            f"<div style='margin-bottom: 12px; padding-left: 8px; border-left: 2px solid {self.accent};'>"
            f"<span style='color: {self.accent}; font-weight: bold;'>{prov_tag} [{model_tag}]:</span><br>"
            f"<div style='color: #d4d4d8; line-height: 1.4; margin-top: 4px;'>{formatted}</div>"
            f"</div>"
        )

    def _on_send(self) -> None:
        text = self.input_field.text().strip()
        if not text:
            return
        self.input_field.clear()

        if text.startswith("/key"):
            parts = text.split(" ", 1)
            if len(parts) > 1 and parts[1].strip():
                self.save_api_key(parts[1].strip())
            else:
                self.open_key_dialog()
            return

        if text.startswith("/provider"):
            parts = text.split()
            if len(parts) > 1 and parts[1].lower() in ["gemini", "ollama"]:
                self._set_provider(parts[1].lower())
            else:
                self._toggle_provider()
            return
        elif text == "/ollama":
            self._set_provider("ollama")
            return
        elif text == "/gemini":
            self._set_provider("gemini")
            return
        elif text == "/models":
            self._update_model_list()
            self._append_system("Refreshed models list.")
            return

        self._append_user(text)

        if text.startswith("/help"):
            self._append_assistant(
                "Commands:\n"
                "- /help: Show command list\n"
                "- /provider <gemini|ollama>: Switch active provider\n"
                "- /ollama: Quick-switch to Ollama Local LLM\n"
                "- /gemini: Quick-switch to Google Gemini Cloud API\n"
                "- /key <api_key>: Set Gemini API key directly\n"
                "- /models: Refresh models for current provider\n"
                "- /clear: Clear chat transcript\n"
                "- @page <question>: Ask questions grounded in active webpage content\n"
                "- /info: System & model diagnostics\n"
                "- Click 'SUMMARIZE PAGE' to generate structured summary"
            )
        elif text.startswith("/clear"):
            self.clear_transcript()
        elif text.startswith("/info"):
            import platform
            self._append_assistant(
                f"Host: {platform.node()}\n"
                f"OS: {platform.system()} {platform.release()} ({platform.machine()})\n"
                f"Engine: Chromium (Qt6WebEngine)\n"
                f"Active Model: {self.active_model}\n"
                f"Aesthetic: Anthropic Minimal Dark (Zinc 900 / Square UI)"
            )
        elif text.startswith("@page"):
            q = text.replace("@page", "").strip()
            self._ask_about_page(q)
        elif "summarize" in text.lower():
            self._on_summarize_clicked()
        else:
            self._process_ai_query(text)

    def _ask_about_page(self, question: str) -> None:
        if not self.cached_page_context:
            self.ask_context_page.emit()
            self._pending_page_question = question
            return

        prompt = (
            f"You are a sharp AI assistant in Zephyrium. Answer the user's question "
            f"strictly based on the following web page content:\n\n"
            f"Web Page Context:\n{self.cached_page_context[:5000]}\n\n"
            f"User Question: {question}"
        )
        self._process_ai_query(prompt)

    def _process_ai_query(self, query: str) -> None:
        provider = self.provider or self.settings.get("ai_provider", "gemini")
        lang_code = get_current_language()
        lang_name = LANGUAGES.get(lang_code, "Russian")
        system_instruction = (
            f"You are Zephyrium AI Assistant, integrated directly into Zephyrium Minimal Browser. "
            f"CRITICAL REQUIREMENT: You must ALWAYS communicate and respond in {lang_name} ({lang_code}), "
            f"matching the user's interface language setting, unless the user explicitly requests another language. "
            f"Keep explanations concise, precise, technical, and engineer-focused."
        )

        if provider == "ollama":
            ollama_url = self.ollama_url or self.settings.get("ollama_url", "http://localhost:11434")
            ollama_model = self.ollama_model or self.settings.get("ollama_model", "llama3")
            self.status.setText(f"OLLAMA // THINKING")
            self.status.setStyleSheet(f"color: {getattr(self, 'accent', '#fe8019')}; font-size: 10px; font-weight: bold;")
            self.worker = OllamaWorker(query, base_url=ollama_url, model=ollama_model, system_instruction=system_instruction)
            self.worker.response_ready.connect(self._on_worker_response)
            self.worker.error_occurred.connect(self._on_worker_error)
            self.worker.start()
            return

        key = self.api_key or os.environ.get("GEMINI_API_KEY")
        if not key:
            self._append_assistant(
                "Gemini API Key is not set!\n\n"
                "You can configure it directly by clicking '[KEY]' in the header, "
                "typing: /key <your_gemini_api_key>, or switching to Ollama local provider in Settings."
            )
            return

        self.status.setText(t("ai_thinking"))
        self.status.setStyleSheet(f"color: {getattr(self, 'accent', '#fe8019')}; font-size: 10px; font-weight: bold;")

        self.worker = GeminiWorker(query, key, model=self.active_model, system_instruction=system_instruction)
        self.worker.response_ready.connect(self._on_worker_response)
        self.worker.error_occurred.connect(self._on_worker_error)
        self.worker.start()

    def _on_worker_response(self, text: str) -> None:
        self._update_status_display()
        self._append_assistant(text)

    def _on_worker_error(self, err: str) -> None:
        self._update_status_display()
        self._append_assistant(f"Error during API call: {err}")

    def _on_summarize_clicked(self) -> None:
        self._pending_page_question = None
        self.ask_context_page.emit()

    def receive_page_summary(self, title: str, url: str, content: str) -> None:
        self.cached_page_context = f"Title: {title}\nURL: {url}\n\n{content}"
        
        if getattr(self, "_pending_page_question", None):
            q = self._pending_page_question
            self._pending_page_question = None
            self._ask_about_page(q)
            return

        self._append_user(f"Summarize page: '{title}' ({url})")
        prompt = (
            f"You are a concise, engineer-focused AI assistant in Zephyrium. "
            f"Summarize the following web page content with bullet points and key takeaways:\n\n"
            f"Page Title: {title}\n"
            f"URL: {url}\n\n"
            f"Content:\n{content[:5000]}"
        )
        self._process_ai_query(prompt)

    def clear_transcript(self) -> None:
        self.transcript.clear()
        self._append_system("Session cleared.")

    def update_theme(self, theme: str = "dark", accent: str = "#fe8019") -> None:
        self.accent = accent
        if hasattr(self, "title_lbl"):
            self.title_lbl.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {accent}; letter-spacing: 1px;")
        self.transcript.setStyleSheet("")
        if hasattr(self, "input_field"):
            self.input_field.setStyleSheet("min-height: 30px; max-height: 30px; padding: 0px 8px;")
        if hasattr(self, "combo_model"):
            self.combo_model.setStyleSheet("min-height: 28px; max-height: 28px; padding: 0px 8px;")
        if hasattr(self, "btn_send"):
            self.btn_send.setStyleSheet(f"min-height: 30px; max-height: 30px; padding: 0px 14px; border: 1px solid {accent}; color: {accent}; font-weight: bold;")
        self._update_status_display()
