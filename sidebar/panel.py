"""
Right Sidebar Container for Zephyrium
Houses AI Assistant and Notes Panels with square toggle buttons
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QStackedWidget
)
from sidebar.ai_chat import AIChatWidget
from sidebar.notes import NotesWidget
from utils.icons import Icons

from core.i18n import t

class SidePanel(QWidget):
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("rightSidebar")
        self.setMinimumWidth(320)
        self.setMaximumWidth(420)
        self.theme = "dark"
        self.accent = "#fe8019"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Tab bar header
        tab_header = QHBoxLayout()
        tab_header.setSpacing(6)

        self.btn_ai = QPushButton(t("ai_chat_tab"))
        self.btn_ai.setObjectName("accentWarmBtn")
        self.btn_ai.setFixedHeight(28)
        self.btn_ai.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_ai.clicked.connect(lambda: self.switch_tab(0))

        self.btn_notes = QPushButton(t("scratchpad_tab"))
        self.btn_notes.setFixedHeight(28)
        self.btn_notes.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_notes.clicked.connect(lambda: self.switch_tab(1))

        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #3f3f46;
                color: #a1a1aa;
                font-size: 14px;
                font-weight: bold;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #ef4444;
                border-color: #ef4444;
                color: #ffffff;
            }
        """)
        self.btn_close.clicked.connect(self.close_requested.emit)

        tab_header.addWidget(self.btn_ai)
        tab_header.addWidget(self.btn_notes)
        tab_header.addStretch()
        tab_header.addWidget(self.btn_close)
        layout.addLayout(tab_header)

        # Stack
        self.stack = QStackedWidget()
        self.ai_widget = AIChatWidget(self)
        self.notes_widget = NotesWidget(self)

        self.stack.addWidget(self.ai_widget)
        self.stack.addWidget(self.notes_widget)
        layout.addWidget(self.stack)

        self.switch_tab(0)

    def switch_tab(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        active_bg = "#f1f5f9" if self.theme == "light" else "#2d2d2a"
        inactive_bg = "#ffffff" if self.theme == "light" else "#262624"
        text_primary = "#1e293b" if self.theme == "light" else "#d4d4d8"
        text_bright = "#0f172a" if self.theme == "light" else "#f5f5f0"
        border_muted = "#cbd5e1" if self.theme == "light" else "#3f3f46"

        if index == 0:
            self.btn_ai.setStyleSheet(f"border-color: {self.accent}; color: {self.accent}; background-color: {active_bg}; font-weight: bold;")
            self.btn_notes.setStyleSheet(f"border-color: {border_muted}; color: {text_primary}; background-color: {inactive_bg};")
        else:
            self.btn_notes.setStyleSheet(f"border-color: {self.accent}; color: {text_bright}; background-color: {active_bg}; font-weight: bold;")
            self.btn_ai.setStyleSheet(f"border-color: {border_muted}; color: {text_primary}; background-color: {inactive_bg};")

    def update_theme(self, theme: str = "dark", accent: str = "#fe8019") -> None:
        self.theme = theme
        self.accent = accent
        self.switch_tab(self.stack.currentIndex())
        if hasattr(self, "ai_widget") and hasattr(self.ai_widget, "update_theme"):
            self.ai_widget.update_theme(theme, accent)
        if hasattr(self, "notes_widget") and hasattr(self.notes_widget, "update_theme"):
            self.notes_widget.update_theme(theme, accent)

    def retranslate_ui(self) -> None:
        self.btn_ai.setText(t("ai_chat_tab"))
        self.btn_notes.setText(t("scratchpad_tab"))
        self.btn_ai.setToolTip(t("ai_assistant_tooltip"))
        self.btn_notes.setToolTip(t("scratchpad_tab"))
        if hasattr(self, "ai_widget") and hasattr(self.ai_widget, "retranslate_ui"):
            self.ai_widget.retranslate_ui()
