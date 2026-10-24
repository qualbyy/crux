"""
Scratchpad & Notes Panel for Zephyrium
Claude Code Minimal Dark aesthetic (Monospace, 1px border, Auto-save)
"""
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton
)
from config import NOTES_FILE

class NotesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("notesWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header info
        header = QHBoxLayout()
        title = QLabel("SCRATCHPAD // AUTOSAVE")
        title.setStyleSheet("font-size: 11px; font-weight: bold; color: #71717a; letter-spacing: 1px;")
        
        self.save_status = QLabel("SYNCED")
        self.save_status.setStyleSheet("color: #10b981; font-size: 10px; font-weight: bold;")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.save_status)
        layout.addLayout(header)

        # Editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Quick notes, code snippets, temporary clipboard...")
        layout.addWidget(self.editor)

        # Footer stats
        self.footer = QLabel("0 chars | 0 words")
        self.footer.setStyleSheet("color: #71717a; font-size: 11px;")
        layout.addWidget(self.footer)

        # Auto-save debounce timer
        self.save_timer = QTimer(self)
        self.save_timer.setInterval(1000)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_notes)

        self.editor.textChanged.connect(self._on_text_changed)

        self._load_notes()

    def _load_notes(self) -> None:
        if NOTES_FILE.exists():
            try:
                with open(NOTES_FILE, "r", encoding="utf-8") as f:
                    self.editor.setPlainText(f.read())
            except Exception as e:
                print(f"Error loading notes: {e}")

    def _on_text_changed(self) -> None:
        self.save_status.setText("EDITING...")
        self.save_status.setStyleSheet("color: #f59e0b; font-size: 10px;")
        self.save_timer.start()

        # Update stats
        text = self.editor.toPlainText()
        chars = len(text)
        words = len(text.split())
        self.footer.setText(f"{chars} chars | {words} words")

    def _save_notes(self) -> None:
        try:
            with open(NOTES_FILE, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            self.save_status.setText("SYNCED")
            self.save_status.setStyleSheet("color: #10b981; font-size: 10px;")
        except Exception as e:
            self.save_status.setText("SAVE ERR")
            self.save_status.setStyleSheet("color: #ef4444; font-size: 10px;")

    def update_theme(self, theme: str = "dark", accent: str = "#fe8019") -> None:
        self.editor.setStyleSheet("")
