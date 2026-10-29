"""
Terminal-style Download Manager for Zinc Browser
Claude Code Minimal Dark aesthetic (Square UI, ASCII progress bars)
"""
import os
import subprocess
from pathlib import Path
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QFileDialog
)
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest

class DownloadItemWidget(QFrame):
    def __init__(self, item: QWebEngineDownloadRequest, accent: str = "#a855f7", parent=None):
        super().__init__(parent)
        self.item = item
        self.accent = accent
        self.setObjectName("downloadItem")
        self.setStyleSheet("""
            #downloadItem {
                background-color: #18181b;
                border: 1px solid #3f3f46;
                padding: 8px;
                margin-bottom: 6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Header: filename and status
        header_layout = QHBoxLayout()
        filename = Path(item.downloadFileName()).name
        self.filename_label = QLabel(f"FILE: {filename}")
        self.filename_label.setStyleSheet("color: #f5f5f0; font-weight: bold;")
        
        self.status_label = QLabel("[QUEUED]")
        self.status_label.setStyleSheet("color: #94a3b8;")

        header_layout.addWidget(self.filename_label)
        header_layout.addStretch()
        header_layout.addWidget(self.status_label)
        layout.addLayout(header_layout)

        # ASCII Progress Bar
        self.progress_label = QLabel("[--------------------] 0%")
        self.progress_label.setStyleSheet(f"color: {accent}; font-family: monospace;")
        layout.addWidget(self.progress_label)

        # Meta & Actions
        footer_layout = QHBoxLayout()
        self.info_label = QLabel("0 KB / ? KB")
        self.info_label.setStyleSheet("color: #71717a; font-size: 11px;")
        
        self.action_btn = QPushButton("CANCEL")
        self.action_btn.setFixedHeight(22)
        self.action_btn.clicked.connect(self._on_action_clicked)

        footer_layout.addWidget(self.info_label)
        footer_layout.addStretch()
        footer_layout.addWidget(self.action_btn)
        layout.addLayout(footer_layout)

        # Connect download request signals
        self.item.receivedBytesChanged.connect(self._on_progress)
        self.item.stateChanged.connect(self._on_state_changed)

    def _on_progress(self) -> None:
        received = self.item.receivedBytes()
        total = self.item.totalBytes()
        
        if total > 0:
            percent = int((received / total) * 100)
            bars = int(percent / 5)
            spaces = 20 - bars
            bar_str = f"[{'=' * bars}{'>' if bars < 20 else ''}{'-' * max(0, spaces - 1)}] {percent}%"
            self.progress_label.setText(bar_str)
            self.info_label.setText(f"{self._format_bytes(received)} / {self._format_bytes(total)}")
        else:
            self.progress_label.setText(f"[DOWNLOADING...] {self._format_bytes(received)}")
            self.info_label.setText(f"{self._format_bytes(received)}")

    def _on_state_changed(self, state: QWebEngineDownloadRequest.DownloadState) -> None:
        if state == QWebEngineDownloadRequest.DownloadState.DownloadInProgress:
            self.status_label.setText("[DOWNLOADING]")
            self.status_label.setStyleSheet("color: #38bdf8;")
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            self.status_label.setText("[DONE]")
            self.status_label.setStyleSheet("color: #10b981;")
            self.progress_label.setText("[====================] 100%")
            self.progress_label.setStyleSheet("color: #10b981; font-family: monospace;")
            self.action_btn.setText("OPEN")
            try:
                is_incognito = False
                try:
                    if hasattr(self.item, "page") and self.item.page() and self.item.page().profile():
                        is_incognito = self.item.page().profile().isOffTheRecord()
                except Exception:
                    pass
                if not is_incognito:
                    from utils.bookmarks import DataStore
                    path = os.path.join(self.item.downloadDirectory(), self.item.downloadFileName())
                    DataStore.add_download(self.item.downloadFileName(), path, self.item.totalBytes(), "completed")
            except Exception:
                pass
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadCancelled:
            self.status_label.setText("[CANCELLED]")
            self.status_label.setStyleSheet("color: #ef4444;")
            self.action_btn.setEnabled(False)
        elif state == QWebEngineDownloadRequest.DownloadState.DownloadInterrupted:
            self.status_label.setText("[ERROR]")
            self.status_label.setStyleSheet("color: #ef4444;")

    def _on_action_clicked(self) -> None:
        if self.item.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted:
            path = self.item.downloadDirectory() + "/" + self.item.downloadFileName()
            if os.path.exists(path):
                from PyQt6.QtGui import QDesktopServices
                from PyQt6.QtCore import QUrl
                QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        elif self.item.state() == QWebEngineDownloadRequest.DownloadState.DownloadInProgress:
            self.item.cancel()

    @staticmethod
    def _format_bytes(size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"


class DownloadManager(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("downloadsPopup")
        self.setFixedWidth(360)
        self.setMinimumHeight(180)
        self.setMaximumHeight(420)
        self.accent = "#a855f7"
        self.theme = "dark"
        if parent and hasattr(parent, "settings"):
            self.accent = parent.settings.get("accent_color", "#a855f7")
            self.theme = parent.settings.get("theme", "dark")

        self._init_ui()
        self.update_style()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        title = QLabel("DOWNLOADS // ACTIVE")
        title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {self.accent}; letter-spacing: 1px;")

        self.btn_open_folder = QPushButton("FOLDER")
        self.btn_open_folder.setFixedHeight(22)
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.clicked.connect(self._open_folder)

        self.btn_clear = QPushButton("CLEAR")
        self.btn_clear.setFixedHeight(22)
        self.btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear.clicked.connect(self._clear_completed)

        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.hide)

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.btn_open_folder)
        header.addWidget(self.btn_clear)
        header.addWidget(self.close_btn)
        main_layout.addLayout(header)

        # Scroll area for items
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")

        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setContentsMargins(0, 0, 0, 0)
        self.items_layout.setSpacing(6)

        self.empty_label = QLabel("No active downloads")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #71717a; font-size: 12px; padding: 20px 0;")
        self.items_layout.addWidget(self.empty_label)

        self.items_layout.addStretch()

        self.scroll.setWidget(self.items_container)
        main_layout.addWidget(self.scroll)

    def update_style(self, theme: str = None, accent: str = None) -> None:
        if theme:
            self.theme = theme
        if accent:
            self.accent = accent
        bg = "#18181b" if self.theme == "dark" else "#ffffff"
        border = self.accent
        text = "#f5f5f0" if self.theme == "dark" else "#0f172a"
        self.setStyleSheet(f"""
            #downloadsPopup {{
                background-color: {bg};
                border: 1px solid {border};
            }}
            QPushButton {{
                background-color: transparent;
                border: 1px solid #3f3f46;
                color: {text};
                font-size: 10px;
                padding: 2px 6px;
            }}
            QPushButton:hover {{
                border-color: {self.accent};
                color: {self.accent};
            }}
        """)

    def _open_folder(self) -> None:
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        default_dir = str(Path.home() / "Downloads")
        QDesktopServices.openUrl(QUrl.fromLocalFile(default_dir))

    def _clear_completed(self) -> None:
        # Remove completed or cancelled items from view
        to_remove = []
        for i in range(self.items_layout.count()):
            widget = self.items_layout.itemAt(i).widget()
            if isinstance(widget, DownloadItemWidget):
                state = widget.item.state()
                if state in [QWebEngineDownloadRequest.DownloadState.DownloadCompleted,
                             QWebEngineDownloadRequest.DownloadState.DownloadCancelled,
                             QWebEngineDownloadRequest.DownloadState.DownloadInterrupted]:
                    to_remove.append(widget)
        for w in to_remove:
            self.items_layout.removeWidget(w)
            w.deleteLater()
        self._check_empty()

    def _check_empty(self) -> None:
        count = sum(1 for i in range(self.items_layout.count()) if isinstance(self.items_layout.itemAt(i).widget(), DownloadItemWidget))
        if count == 0:
            self.empty_label.show()
        else:
            self.empty_label.hide()

    def show_at_widget(self, target_widget: QWidget) -> None:
        if not target_widget:
            self.show()
            return
        g_pos = target_widget.mapToGlobal(target_widget.rect().bottomLeft())
        x = g_pos.x() - (self.width() - target_widget.width())
        y = g_pos.y() + 4
        if x < 10:
            x = 10
        self.move(x, y)
        self.show()
        self.raise_()

    def handle_download(self, item: QWebEngineDownloadRequest) -> None:
        default_dir = str(Path.home() / "Downloads")
        os.makedirs(default_dir, exist_ok=True)

        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save File",
            os.path.join(default_dir, item.downloadFileName())
        )

        if not target_path:
            item.cancel()
            return

        item.setDownloadDirectory(str(Path(target_path).parent))
        item.setDownloadFileName(Path(target_path).name)
        item.accept()

        self.empty_label.hide()
        widget = DownloadItemWidget(item, accent=getattr(self, "accent", "#a855f7"))
        self.items_layout.insertWidget(0, widget)

        parent = self.parent()
        if parent and hasattr(parent, "btn_downloads") and parent.btn_downloads.isVisible():
            self.show_at_widget(parent.btn_downloads)
        elif parent and hasattr(parent, "btn_more") and parent.btn_more.isVisible():
            self.show_at_widget(parent.btn_more)
        else:
            self.show()
