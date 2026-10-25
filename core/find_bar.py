"""
Find in Page Minimal Floating Bar for Zephyrium Browser
Claude Code Minimal Dark aesthetic (Square UI, 0px radius, 1px borders)
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton
)

class FindInPageBar(QFrame):
    find_next_requested = pyqtSignal(str)
    find_prev_requested = pyqtSignal(str)
    close_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("findInPageBar")
        self.setFixedHeight(34)
        self.setMinimumWidth(320)
        self.accent = "#fe8019"
        self.theme = "dark"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(6)

        self.label_prefix = QLabel("FIND:")
        self.label_prefix.setStyleSheet("font-size: 11px; font-weight: bold; color: #71717a;")
        layout.addWidget(self.label_prefix)

        self.input_search = QLineEdit()
        self.input_search.setFixedHeight(24)
        self.input_search.setPlaceholderText("Search in page... (Enter for next)")
        self.input_search.textChanged.connect(self._on_text_changed)
        self.input_search.returnPressed.connect(self._on_next)
        layout.addWidget(self.input_search, stretch=1)

        self.label_count = QLabel("")
        self.label_count.setStyleSheet("font-size: 11px; color: #94a3b8; font-family: monospace; min-width: 40px;")
        layout.addWidget(self.label_count)

        self.btn_prev = QPushButton("<")
        self.btn_prev.setFixedSize(22, 22)
        self.btn_prev.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_prev.setToolTip("Find Previous (Shift+Enter)")
        self.btn_prev.clicked.connect(self._on_prev)
        layout.addWidget(self.btn_prev)

        self.btn_next = QPushButton(">")
        self.btn_next.setFixedSize(22, 22)
        self.btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_next.setToolTip("Find Next (Enter)")
        self.btn_next.clicked.connect(self._on_next)
        layout.addWidget(self.btn_next)

        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setToolTip("Close (Esc)")
        self.btn_close.clicked.connect(self.close_bar)
        layout.addWidget(self.btn_close)

        self.update_style()

    def update_style(self, theme: str = "dark", accent: str = "#fe8019") -> None:
        self.theme = theme
        self.accent = accent
        bg = "#18181b" if theme == "dark" else "#ffffff"
        border = "#3f3f46" if theme == "dark" else "#cbd5e1"
        fg = "#f5f5f0" if theme == "dark" else "#0f172a"

        self.setStyleSheet(f"""
            QFrame#findInPageBar {{
                background-color: {bg};
                border: 1px solid {accent};
                border-radius: 0px;
            }}
            QLineEdit {{
                background-color: transparent;
                border: 1px solid {border};
                color: {fg};
                font-size: 12px;
                padding: 2px 6px;
                border-radius: 0px;
            }}
            QLineEdit:focus {{
                border-color: {accent};
            }}
            QPushButton {{
                background-color: transparent;
                border: 1px solid {border};
                color: {fg};
                font-size: 11px;
                font-weight: bold;
                border-radius: 0px;
            }}
            QPushButton:hover {{
                border-color: {accent};
                color: {accent};
            }}
        """)

    def _on_text_changed(self, text: str) -> None:
        if text:
            self.find_next_requested.emit(text)
        else:
            self.label_count.setText("")

    def _on_next(self) -> None:
        text = self.input_search.text()
        if text:
            self.find_next_requested.emit(text)

    def _on_prev(self) -> None:
        text = self.input_search.text()
        if text:
            self.find_prev_requested.emit(text)

    def set_match_result(self, active_match: int, total_matches: int) -> None:
        if total_matches > 0:
            self.label_count.setText(f"{active_match}/{total_matches}")
            self.label_count.setStyleSheet(f"font-size: 11px; color: {self.accent}; font-family: monospace;")
        else:
            if self.input_search.text():
                self.label_count.setText("0/0")
                self.label_count.setStyleSheet("font-size: 11px; color: #ef4444; font-family: monospace;")
            else:
                self.label_count.setText("")

    def show_find(self) -> None:
        self.show()
        self.raise_()
        self.input_search.setFocus()
        self.input_search.selectAll()

    def close_bar(self) -> None:
        self.hide()
        self.close_requested.emit()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_bar()
            event.accept()
        else:
            super().keyPressEvent(event)
