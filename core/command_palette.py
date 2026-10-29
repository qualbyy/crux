"""
Command Palette (Ctrl+K and :commands) for Zinc Browser
Claude Code Minimal Dark aesthetic (Square UI, 1px border, Monospace)
"""
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer, QThread
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget,
    QListWidgetItem, QLabel, QFrame
)
import urllib.request
import urllib.parse
import json
from utils.bookmarks import DataStore

class SearchSuggestWorker(QThread):
    suggestions_ready = pyqtSignal(str, list)

    def __init__(self, query: str):
        super().__init__()
        self.query = query

    def run(self):
        q = self.query.strip()
        if not q or len(q) < 2:
            return
        try:
            encoded = urllib.parse.quote(q)
            url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={encoded}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Crux/1.3.6"})
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                    self.suggestions_ready.emit(self.query, data[1][:6])
        except Exception:
            pass

class CommandPalette(QDialog):
    command_executed = pyqtSignal(str, str)  # (action, param)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(580, 360)
        self.setObjectName("commandPalette")

        self.setStyleSheet("""
            #commandPalette {
                background-color: #18181b;
                border: 1px solid #94a3b8;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header / Status
        header = QHBoxLayout()
        title = QLabel("COMMAND PALETTE // OMNIBAR")
        title.setStyleSheet("color: #71717a; font-size: 11px; letter-spacing: 1px; font-weight: bold;")
        
        shortcut_hint = QLabel("ESC to close | ENTER to select")
        shortcut_hint.setStyleSheet("color: #71717a; font-size: 10px;")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(shortcut_hint)
        layout.addLayout(header)

        # Search / Input Field
        parent = self.parent()
        acc = "#a855f7"
        if parent and hasattr(parent, "settings"):
            acc = parent.settings.get("accent_color", "#a855f7")

        input_container = QHBoxLayout()
        self.prompt_label = QLabel("&gt;")
        self.prompt_label.setStyleSheet(f"color: {acc}; font-weight: bold; font-size: 14px;")
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("Search, enter URL, or type :command...")
        self.input.setStyleSheet("""
            QLineEdit {
                background-color: #262624;
                border: 1px solid #3f3f46;
                color: #f5f5f0;
                font-size: 13px;
                padding: 6px 10px;
            }
            QLineEdit:focus {
                border-color: #94a3b8;
            }
        """)
        self.input.textChanged.connect(self._filter_items)
        self.input.returnPressed.connect(self._on_enter)

        input_container.addWidget(self.prompt_label)
        input_container.addWidget(self.input)
        layout.addLayout(input_container)

        # Result List
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: #18181b;
                border: 1px solid #3f3f46;
                outline: none;
            }}
            QListWidget::item {{
                background-color: #18181b;
                color: #d4d4d8;
                border-bottom: 1px solid #2b2b29;
                padding: 6px 8px;
            }}
            QListWidget::item:hover {{
                background-color: #262624;
                color: #f5f5f0;
            }}
            QListWidget::item:selected {{
                background-color: #2d2d2a;
                color: #f5f5f0;
                border-left: 2px solid {acc};
            }}
        """)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget)

        self.suggest_timer = QTimer(self)
        self.suggest_timer.setSingleShot(True)
        self.suggest_timer.setInterval(180)
        self.suggest_timer.timeout.connect(self._fetch_suggestions)
        self.suggest_worker = None

        self._static_commands = [
            ("navigate", "Navigate or Search DuckDuckGo", "URL or query"),
            ("tasks", ":tasks — Open Task Manager (Shift+Esc)", "tasks"),
            ("tabnew", ":tabnew [url] — Open a new tab", "tabnew"),
            ("close", ":close — Close current tab", "close"),
            ("snooze_tab", ":snooze — Snooze current tab to free RAM (💤)", "snooze"),
            ("snooze_others", ":snooze others — Snooze all background tabs", "snooze:others"),
            ("wake_all", ":wake all — Wake all snoozed tabs", "wake:all"),
            ("devtools", ":devtools / F12 — Toggle Chromium DevTools Dock", "devtools"),
            ("viewport", ":viewport — Toggle Responsive Mobile Emulator Bar", "viewport"),
            ("tab_work", ":container work — Open tab in Work container", "container:work"),
            ("tab_personal", ":container personal — Open tab in Personal container", "container:personal"),
            ("tab_dev", ":container dev — Open tab in Dev container", "container:dev"),
            ("tab_incognito", ":container incognito — Open Disposable incognito tab", "container:incognito"),
            ("find", ":find — Toggle Find in Page (Ctrl+F)", "find"),
            ("pin", ":pin — Pin/unpin active tab", "pin"),
            ("split", ":split — Toggle Split View (dual webview)", "split"),
            ("vsplit", ":vsplit — Toggle Vertical Split View", "vsplit"),
            ("ai", ":ai — Toggle Claude AI Assistant panel", "ai"),
            ("notes", ":notes — Toggle Scratchpad Notes panel", "notes"),
            ("downloads", ":downloads — Toggle Downloads popup", "downloads"),
            ("adblock", ":adblock — Toggle AdBlocker on/off", "adblock"),
            ("zoom_in", ":zoom in — Zoom in page (+10%)", "zoom:in"),
            ("zoom_out", ":zoom out — Zoom out page (-10%)", "zoom:out"),
            ("zoom_reset", ":zoom reset — Reset zoom (100%)", "zoom:reset"),
            ("bookmarks", ":bookmarks — Show saved bookmarks", "bookmarks"),
            ("history", ":history — Show browsing history", "history"),
            ("settings", ":settings — Settings & Import Passwords/Cookies/Bookmarks", "settings"),
            ("clean_cookies", ":cleardata — Clear cookies and cache", "cleardata"),
        ]

    def show_palette(self, initial_text: str = "") -> None:
        parent = self.parent()
        th = "dark"
        acc = "#a855f7"
        if parent and hasattr(parent, "settings"):
            th = parent.settings.get("theme", "dark")
            acc = parent.settings.get("accent_color", "#a855f7")
        
        bg_base = "#ffffff" if th == "light" else "#18181b"
        bg_input = "#f8fafc" if th == "light" else "#262624"
        border_muted = "#cbd5e1" if th == "light" else "#3f3f46"
        text_primary = "#1e293b" if th == "light" else "#d4d4d8"
        text_bright = "#0f172a" if th == "light" else "#f5f5f0"
        item_hover = "#f1f5f9" if th == "light" else "#262624"
        item_sel = "#e2e8f0" if th == "light" else "#2d2d2a"

        self.setStyleSheet(f"""
            #commandPalette {{
                background-color: {bg_base};
                border: 1px solid {border_muted};
            }}
        """)
        self.prompt_label.setStyleSheet(f"color: {acc}; font-weight: bold; font-size: 14px;")
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg_input};
                border: 1px solid {border_muted};
                color: {text_bright};
                font-size: 13px;
                padding: 6px 10px;
            }}
            QLineEdit:focus {{
                border-color: {acc};
            }}
        """)
        self.list_widget.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_base};
                border: 1px solid {border_muted};
                outline: none;
            }}
            QListWidget::item {{
                background-color: {bg_base};
                color: {text_primary};
                border-bottom: 1px solid {border_muted};
                padding: 6px 8px;
            }}
            QListWidget::item:hover {{
                background-color: {item_hover};
                color: {text_bright};
            }}
            QListWidget::item:selected {{
                background-color: {item_sel};
                color: {text_bright};
                border-left: 2px solid {acc};
            }}
        """)

        self.input.setText(initial_text)
        self._filter_items(initial_text)
        self.input.setFocus()
        self.input.selectAll()
        self.exec()

    def _filter_items(self, query: str) -> None:
        self.list_widget.clear()
        q = query.strip().lower()

        # Quick math calculator
        if q and any(op in q for op in ["+", "-", "*", "/", "%"]):
            try:
                safe_expr = q.replace("^", "**")
                if all(ch in "0123456789. +-/*%()e" for ch in safe_expr):
                    val = eval(safe_expr, {"__builtins__": None}, {})
                    calc_item = QListWidgetItem(f"🔢 {q} = {val}  (Enter to copy)")
                    calc_item.setData(Qt.ItemDataRole.UserRole, ("copy_clipboard", str(val)))
                    self.list_widget.addItem(calc_item)
            except Exception:
                pass

        # If user is typing a URL or general search
        if q and not q.startswith(":"):
            direct_item = QListWidgetItem(f"→ Open / Search: '{query}'")
            direct_item.setData(Qt.ItemDataRole.UserRole, ("navigate", query))
            self.list_widget.addItem(direct_item)

            if len(q) >= 2 and not q.startswith("http://") and not q.startswith("https://") and not q.startswith("file://"):
                self.suggest_timer.start()

        # Match open tabs across tab manager
        parent = self.parent()
        if parent and hasattr(parent, "tab_manager"):
            tm = parent.tab_manager
            for tid, tdata in list(tm.tabs.items()):
                title = tdata.title or "New Tab"
                url = tdata.url or ""
                cont = getattr(tdata, "container_id", "default")
                if not q or q in title.lower() or q in url.lower() or q in cont.lower():
                    status_prefix = "💤 " if getattr(tdata, "is_suspended", False) else "📑 "
                    badge = f"[{cont.upper()}] " if cont != "default" else ""
                    item = QListWidgetItem(f"{status_prefix}{badge}{title} — {url}")
                    item.setData(Qt.ItemDataRole.UserRole, ("switch_tab", str(tid)))
                    self.list_widget.addItem(item)

        # Match built-in commands
        for cmd_type, title, arg in self._static_commands:
            if not q or q in title.lower() or q in arg.lower() or (q.startswith(":") and q[1:] in arg.lower()):
                item = QListWidgetItem(f"[CMD] {title}")
                item.setData(Qt.ItemDataRole.UserRole, (cmd_type, arg))
                self.list_widget.addItem(item)

        # Match bookmarks
        bookmarks = DataStore.load_bookmarks()
        for bm in bookmarks:
            if not q or q in bm.get("title", "").lower() or q in bm.get("url", "").lower():
                item = QListWidgetItem(f"[BM] {bm.get('title', '')} — {bm.get('url', '')}")
                item.setData(Qt.ItemDataRole.UserRole, ("navigate", bm.get("url", "")))
                self.list_widget.addItem(item)

        # Match history
        try:
            history = DataStore.load_history()
            matched_history = 0
            for h in history:
                if q and (q in h.get("title", "").lower() or q in h.get("url", "").lower()):
                    item = QListWidgetItem(f"🕒 {h.get('title', '')} — {h.get('url', '')}")
                    item.setData(Qt.ItemDataRole.UserRole, ("navigate", h.get("url", "")))
                    self.list_widget.addItem(item)
                    matched_history += 1
                    if matched_history >= 8:
                        break
        except Exception:
            pass

        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _fetch_suggestions(self) -> None:
        q = self.input.text().strip()
        if not q or q.startswith(":") or len(q) < 2:
            return
        if self.suggest_worker and self.suggest_worker.isRunning():
            self.suggest_worker.terminate()
        self.suggest_worker = SearchSuggestWorker(q)
        self.suggest_worker.suggestions_ready.connect(self._on_suggestions_ready)
        self.suggest_worker.start()

    def _on_suggestions_ready(self, query: str, suggestions: list) -> None:
        if query.strip().lower() != self.input.text().strip().lower():
            return
        existing_texts = {self.list_widget.item(i).text() for i in range(self.list_widget.count())}
        insert_idx = 1 if self.list_widget.count() > 0 else 0
        for s in reversed(suggestions):
            label = f"🔍 {s}"
            if label not in existing_texts:
                item = QListWidgetItem(label)
                item.setData(Qt.ItemDataRole.UserRole, ("navigate", s))
                self.list_widget.insertItem(insert_idx, item)

    def _on_enter(self) -> None:
        text = self.input.text().strip()
        current_item = self.list_widget.currentItem()
        
        if text.startswith(":") and len(text) > 1:
            cmd = text[1:].strip().split(" ", 1)
            action = cmd[0]
            param = cmd[1] if len(cmd) > 1 else ""
            self.command_executed.emit(action, param)
            self.accept()
            return

        if current_item:
            action, param = current_item.data(Qt.ItemDataRole.UserRole)
            self.command_executed.emit(action, param)
            self.accept()
        elif text:
            self.command_executed.emit("navigate", text)
            self.accept()

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        action, param = item.data(Qt.ItemDataRole.UserRole)
        self.command_executed.emit(action, param)
        self.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() == Qt.Key.Key_Down:
            cur = self.list_widget.currentRow()
            if cur < self.list_widget.count() - 1:
                self.list_widget.setCurrentRow(cur + 1)
        elif event.key() == Qt.Key.Key_Up:
            cur = self.list_widget.currentRow()
            if cur > 0:
                self.list_widget.setCurrentRow(cur - 1)
        else:
            super().keyPressEvent(event)
