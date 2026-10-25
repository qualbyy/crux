"""
Split View Manager for Zinc Browser
Side-by-side or stacked dual web view container using QSplitter
"""
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from core.web_view import ZincWebView
from core.profile_manager import ProfileManager

class SplitViewContainer(QWidget):
    focus_changed = pyqtSignal(ZincWebView)
    title_changed = pyqtSignal(str)
    url_changed = pyqtSignal(QUrl)

    def __init__(self, profile_manager: ProfileManager, primary_view: ZincWebView, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.primary_view = primary_view
        self.secondary_view: ZincWebView = None
        self.is_split = False
        self.active_view = primary_view

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setHandleWidth(1)
        self.splitter.addWidget(self.primary_view)
        self._layout.addWidget(self.splitter)

        self._bind_view(self.primary_view)

    def split(self, url: QUrl = None, orientation: Qt.Orientation = Qt.Orientation.Horizontal) -> None:
        if self.is_split and self.secondary_view:
            return  # Already split

        self.splitter.setOrientation(orientation)
        
        # Create secondary view in same profile or default
        profile = self.profile_manager.get_profile(self.primary_view.container_id)
        self.secondary_view = ZincWebView(profile, self.primary_view.container_id, self)
        
        if url:
            self.secondary_view.load(url)
        else:
            self.secondary_view.navigate("zephyrium://startpage")

        self.splitter.addWidget(self.secondary_view)
        self.splitter.setSizes([int(self.width() / 2), int(self.width() / 2)])
        self.is_split = True

        self._bind_view(self.secondary_view)
        self.active_view = self.secondary_view
        self.secondary_view.setFocus()

    def close_split(self) -> None:
        if not self.is_split or not self.secondary_view:
            return

        self.secondary_view.setParent(None)
        self.secondary_view.deleteLater()
        self.secondary_view = None
        self.is_split = False
        self.active_view = self.primary_view
        self.primary_view.setFocus()
        self.title_changed.emit(self.primary_view.title())
        self.url_changed.emit(self.primary_view.url())

    def toggle_split(self, url: QUrl = None) -> bool:
        if self.is_split:
            self.close_split()
            return False
        else:
            self.split(url)
            return True

    def toggle_orientation(self) -> None:
        if not self.is_split:
            return
        current = self.splitter.orientation()
        new_orient = Qt.Orientation.Vertical if current == Qt.Orientation.Horizontal else Qt.Orientation.Horizontal
        self.splitter.setOrientation(new_orient)

    @property
    def views(self):
        v = [self.primary_view]
        if self.is_split and self.secondary_view:
            v.append(self.secondary_view)
        return v

    def get_active_view(self) -> ZincWebView:
        if self.is_split and self.secondary_view and self.secondary_view.hasFocus():
            return self.secondary_view
        return self.primary_view

    def _bind_view(self, view: ZincWebView) -> None:
        view.titleChanged.connect(lambda t: self._on_title_changed(view, t))
        view.urlChanged.connect(lambda u: self._on_url_changed(view, u))

    def _on_title_changed(self, view: ZincWebView, title: str) -> None:
        if view == self.get_active_view():
            self.title_changed.emit(title)

    def _on_url_changed(self, view: ZincWebView, url: QUrl) -> None:
        if view == self.get_active_view():
            self.url_changed.emit(url)
