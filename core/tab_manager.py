"""
Vertical Tab Manager for Zinc Browser
Claude Code Minimal Dark aesthetic (Square UI, 0px radius, 1px borders)
Features: Collapsible / Compact Mode (54px vs 240px), Tab Suspension & Memory Saving
"""
import time
import html
from typing import List, Dict, Optional
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QSize, QTimer, QPoint, QMimeData
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QListWidget,
    QListWidgetItem, QLabel, QStackedWidget, QMenu, QFrame, QSizePolicy,
    QAbstractItemView
)
from core.split_view import SplitViewContainer
from core.web_view import ZincWebView
from core.profile_manager import ProfileManager
from utils.icons import Icons
from config import CONTAINERS
from core.i18n import t

class TabItemData:
    def __init__(self, tab_id: int, container_id: str, split_container: SplitViewContainer):
        self.tab_id = tab_id
        self.container_id = container_id
        self.split_container = split_container
        self.title = "New Tab"
        self.url = ""
        self.is_suspended = False
        self.is_pinned = False
        self.is_audible = False
        self.is_muted = False
        self.group = ""
        self.last_active_time = time.time()


class TabItemWidget(QWidget):
    close_clicked = pyqtSignal(int)
    mute_clicked = pyqtSignal(int)

    def __init__(self, tab_data: TabItemData, parent=None):
        super().__init__(parent)
        self.tab_data = tab_data
        self.is_compact = False
        self.theme = "dark"
        self.accent = "#a855f7"
        self.is_active = False

        self.setObjectName("tabItemWidget")
        self.setFixedHeight(36)
        self.setStyleSheet("""
            QWidget#tabItemWidget {
                background: transparent;
                border: none;
            }
        """)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(6, 2, 6, 2)
        self._layout.setSpacing(6)

        # Tab Indicator (clean glyph or pin)
        self.indicator = QLabel("▪")
        self.indicator.setFixedSize(16, 18)
        self.indicator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.indicator.setStyleSheet("color: #71717a; font-size: 11px; background: transparent; border: none;")
        self._layout.addWidget(self.indicator)

        # Container badge (e.g. WRK, PER, DEV, INC)
        self.container_badge = QLabel()
        self.container_badge.setFixedHeight(16)
        self.container_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.container_badge.hide()
        self._layout.addWidget(self.container_badge)

        # Title Label
        self.title_label = QLabel(tab_data.title)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.title_label.setMinimumWidth(0)
        self.title_label.setStyleSheet("color: #d4d4d8; font-size: 13px; font-weight: 500; border: none; background: transparent;")
        self._layout.addWidget(self.title_label, stretch=1)

        # Audio / Mute indicator button
        self.audio_btn = QPushButton("VOL")
        self.audio_btn.setFixedSize(28, 18)
        self.audio_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.audio_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #3f3f46;
                color: #a855f7;
                font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace;
                font-size: 9px;
                font-weight: bold;
                padding: 0;
            }
        """)
        self.audio_btn.clicked.connect(lambda: self.mute_clicked.emit(self.tab_data.tab_id))
        self.audio_btn.hide()
        self._layout.addWidget(self.audio_btn)

        # Close button
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(20, 20)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #71717a;
                font-size: 14px;
                padding: 0;
            }
            QPushButton:hover {
                color: #ef4444;
                background-color: #2d2d2a;
            }
        """)
        self.close_btn.clicked.connect(lambda: self.close_clicked.emit(self.tab_data.tab_id))
        self._layout.addWidget(self.close_btn)
        self.refresh_ui()

    def refresh_ui(self) -> None:
        # Update container badge
        cid = getattr(self.tab_data, "container_id", "default")
        if cid and cid != "default" and cid in CONTAINERS:
            meta = CONTAINERS[cid]
            b_text = meta.get("badge", cid[:3].upper())
            b_col = meta.get("color", self.accent)
            self.container_badge.setText(b_text)
            self.container_badge.setStyleSheet(f"color: {b_col}; border: 1px solid {b_col}; font-size: 8px; font-weight: bold; padding: 0 2px; border-radius: 2px; background: transparent;")
            self.container_badge.show()
        else:
            self.container_badge.hide()

        if self.tab_data.is_pinned:
            self.indicator.setText("PIN")
            self.indicator.setStyleSheet(f"color: {self.accent}; font-size: 9px; font-weight: bold; border: 1px solid {self.accent}; padding: 1px;")
            self.indicator.setFixedWidth(24)
            self.close_btn.hide()
        elif self.tab_data.is_suspended:
            self.indicator.setText("ZZZ")
            self.indicator.setStyleSheet(f"color: {self.accent}; font-size: 8px; font-weight: bold; border: 1px solid {self.accent}; padding: 1px;")
            self.indicator.setFixedWidth(24)
            self.close_btn.show()
        else:
            self.indicator.setText("▪")
            self.indicator.setStyleSheet("color: #71717a; font-size: 11px; background: transparent; border: none;")
            self.indicator.setFixedWidth(16)
            self.close_btn.show()

        if getattr(self.tab_data, "is_audible", False) or getattr(self.tab_data, "is_muted", False):
            self.audio_btn.setText("MUTE" if self.tab_data.is_muted else "VOL")
            self.audio_btn.setStyleSheet(f"background: transparent; border: 1px solid {self.accent}; color: {self.accent}; font-family: monospace; font-size: 9px; font-weight: bold; padding: 0;")
            self.audio_btn.setToolTip(t("unmute_tab") if self.tab_data.is_muted else t("mute_tab"))
            self.audio_btn.show()
        else:
            self.audio_btn.hide()

        self.set_title(self.tab_data.title)

    def update_theme(self, theme: str = "dark", accent: str = "#a855f7") -> None:
        self.theme = theme
        self.accent = accent
        close_hover_bg = "#e2e8f0" if theme == "light" else "#3f3f46"
        close_color = "#64748b" if theme == "light" else "#71717a"
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                color: {close_color};
                font-size: 14px;
                padding: 0;
            }}
            QPushButton:hover {{
                color: #ef4444;
                background-color: {close_hover_bg};
            }}
        """)
        self.refresh_ui()
        self.set_active(self.is_active)

    def set_title(self, title: str) -> None:
        clean = title.strip() if title else "New Tab"
        if self.tab_data.group:
            clean = f"[{self.tab_data.group}] {clean}"
        if len(clean) > 28:
            clean = clean[:25] + "..."
        self.title_label.setText(clean)
        if self.is_compact:
            self.setToolTip(f"{title}\n{self.tab_data.url}")

    def set_active(self, active: bool) -> None:
        self.is_active = active
        text_color = ("#0f172a" if active else "#334155") if self.theme == "light" else ("#f5f5f0" if active else "#d4d4d8")
        font_weight = "bold" if active else "500"
        self.title_label.setStyleSheet(f"color: {text_color}; font-weight: {font_weight}; font-size: 13px; border: none; background: transparent;")
        if self.is_compact:
            border_c = self.accent if active else ("#cbd5e1" if self.theme == "light" else "#3f3f46")
            text_c = self.accent if active else ("#64748b" if self.theme == "light" else "#a1a1aa")
            bg = "rgba(148, 163, 184, 0.15)" if active else "transparent"
            self.indicator.setStyleSheet(f"""
                color: {text_c};
                border: 1px solid {border_c};
                border-radius: 0px;
                font-size: 12px;
                font-weight: bold;
                background: {bg};
            """)
        else:
            ind_c = self.accent if active else ("#94a3b8" if self.theme == "light" else "#71717a")
            self.indicator.setStyleSheet(f"color: {ind_c}; font-size: 11px; background: transparent; border: none;")

    def set_suspended(self, suspended: bool) -> None:
        if suspended:
            self.indicator.setText("z")
            if self.is_compact:
                self.indicator.setStyleSheet("color: #71717a; border: 1px dashed #71717a; font-size: 10px; font-weight: bold;")
            else:
                self.indicator.setStyleSheet("color: #71717a; font-size: 10px;")
            self.title_label.setStyleSheet("color: #71717a; font-style: italic; font-size: 13px; border: none;")
        else:
            self.indicator.setText("▪")
            self.set_active(self.is_active)

    def set_compact(self, is_compact: bool) -> None:
        self.is_compact = is_compact
        if is_compact:
            self.title_label.hide()
            self.close_btn.hide()
            self._layout.setContentsMargins(0, 2, 0, 2)
            self._layout.setSpacing(0)
            self._layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.indicator.setFixedSize(26, 26)
            self.set_active(self.is_active)
            self.setToolTip(f"{self.tab_data.title}\n{self.tab_data.url}")
            if getattr(self.tab_data, "is_audible", False) or getattr(self.tab_data, "is_muted", False):
                self.indicator.hide()
                self.audio_btn.show()
            else:
                self.indicator.show()
                self.audio_btn.hide()
        else:
            self.title_label.show()
            self.close_btn.show()
            self.indicator.show()
            self._layout.setContentsMargins(6, 2, 6, 2)
            self._layout.setSpacing(6)
            self._layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
            self.indicator.setFixedSize(16, 18)
            self.set_active(self.is_active)
            self.setToolTip("")
            self.refresh_ui()


class DraggableTabListWidget(QListWidget):
    tab_reordered = pyqtSignal(int, int)  # from_row, to_row

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self._drag_start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
            item = self.itemAt(self._drag_start_pos)
            if item:
                self.setCurrentItem(item)
        super().mousePressEvent(event)

    def startDrag(self, supportedActions):
        pos = getattr(self, "_drag_start_pos", None)
        item = self.itemAt(pos) if pos else self.currentItem()
        if not item:
            item = self.currentItem()
        if not item:
            return
        source_row = self.row(item)
        if source_row < 0:
            return

        mime_data = QMimeData()
        mime_data.setData("application/x-crux-tab-row", str(source_row).encode("utf-8"))
        mime_data.setData("application/x-zephyrium-tab-row", str(source_row).encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        widget = self.itemWidget(item) or getattr(item, "_stored_widget", None)
        if widget:
            try:
                pixmap = widget.grab()
                drag.setPixmap(pixmap)
                drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
            except Exception:
                pass

        # Execute drag safely without letting Qt's internal move remove or delete items
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-crux-tab-row") or event.mimeData().hasFormat("application/x-zephyrium-tab-row"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-crux-tab-row") or event.mimeData().hasFormat("application/x-zephyrium-tab-row"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if not (event.mimeData().hasFormat("application/x-crux-tab-row") or event.mimeData().hasFormat("application/x-zephyrium-tab-row")):
            event.ignore()
            return

        try:
            if event.mimeData().hasFormat("application/x-crux-tab-row"):
                source_row = int(event.mimeData().data("application/x-crux-tab-row").data().decode("utf-8"))
            else:
                source_row = int(event.mimeData().data("application/x-zephyrium-tab-row").data().decode("utf-8"))
        except Exception:
            event.ignore()
            return

        pos = event.position().toPoint()
        target_item = self.itemAt(pos)
        if target_item:
            target_row = self.row(target_item)
        else:
            # Dropped into empty area below tabs
            target_row = self.count() - 1

        if 0 <= source_row < self.count() and 0 <= target_row < self.count() and source_row != target_row:
            self.move_tab_row(source_row, target_row)
            self.tab_reordered.emit(source_row, target_row)
            event.acceptProposedAction()
        else:
            event.accept()

    def move_tab_row(self, from_row: int, to_row: int) -> None:
        if from_row == to_row or from_row < 0 or to_row < 0 or from_row >= self.count() or to_row >= self.count():
            return
        it = self.item(from_row)
        if not it:
            return
        w = self.itemWidget(it) or getattr(it, "_stored_widget", None)
        it = self.takeItem(from_row)
        if w:
            it._stored_widget = w
        self.insertItem(to_row, it)
        if w:
            self.setItemWidget(it, w)
        self.setCurrentRow(to_row)



class VerticalTabSidebar(QWidget):
    tab_selected = pyqtSignal(int)
    tab_closed = pyqtSignal(int)
    new_tab_requested = pyqtSignal(str)  # container_id
    new_tab_container_requested = pyqtSignal(str, str)  # url, container_id
    reopen_in_container_requested = pyqtSignal(int, str)  # tab_id, container_id
    duplicate_tab_requested = pyqtSignal(int)
    split_tab_requested = pyqtSignal(int)
    suspend_tab_requested = pyqtSignal(int)
    pin_tab_requested = pyqtSignal(int)
    mute_tab_requested = pyqtSignal(int)
    set_tab_group_requested = pyqtSignal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("verticalTabsPanel")
        self.setFixedWidth(240)
        self.is_compact = False
        self.expanded_width = 240

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(8, 8, 8, 8)
        self._main_layout.setSpacing(6)

        # 1. Expanded Header Container: "+ NEW TAB" button + Container + Collapse Button
        self.row_expanded = QWidget()
        row_exp_layout = QHBoxLayout(self.row_expanded)
        row_exp_layout.setContentsMargins(0, 0, 0, 0)
        row_exp_layout.setSpacing(4)
        
        self.btn_new_tab = QPushButton("+ NEW TAB")
        self.btn_new_tab.setObjectName("accentBtn")
        self.btn_new_tab.setFixedHeight(26)
        self.btn_new_tab.clicked.connect(lambda: self.new_tab_requested.emit("crux://startpage"))
        self.btn_new_tab.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_new_tab.customContextMenuRequested.connect(lambda p: self._show_containers_menu())

        self.btn_new_tab_menu = QPushButton("▾")
        self.btn_new_tab_menu.setObjectName("accentBtn")
        self.btn_new_tab_menu.setFixedSize(20, 26)
        self.btn_new_tab_menu.setToolTip("Open Tab in Container Profile...")
        self.btn_new_tab_menu.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_new_tab_menu.clicked.connect(lambda: self._show_containers_menu())

        self.btn_collapse = QPushButton("<")
        self.btn_collapse.setFixedSize(26, 26)
        self.btn_collapse.setToolTip("Collapse Sidebar to Compact Mode (Ctrl+[)")
        self.btn_collapse.clicked.connect(self.toggle_compact)

        row_exp_layout.addWidget(self.btn_new_tab, stretch=1)
        row_exp_layout.addWidget(self.btn_new_tab_menu)
        row_exp_layout.addWidget(self.btn_collapse)
        self._main_layout.addWidget(self.row_expanded)

        # 2. Compact Header Container: Clean centered vertical stack
        self.row_compact = QWidget()
        row_comp_layout = QVBoxLayout(self.row_compact)
        row_comp_layout.setContentsMargins(0, 0, 0, 0)
        row_comp_layout.setSpacing(4)
        row_comp_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.btn_expand_compact = QPushButton(">")
        self.btn_expand_compact.setFixedSize(28, 28)
        self.btn_expand_compact.setToolTip("Expand Sidebar (Ctrl+[)")
        self.btn_expand_compact.clicked.connect(self.toggle_compact)

        self.btn_new_tab_compact = QPushButton("+")
        self.btn_new_tab_compact.setObjectName("accentBtn")
        self.btn_new_tab_compact.setFixedSize(28, 28)
        self.btn_new_tab_compact.setToolTip("New Tab (Ctrl+T) | Right-click for Containers")
        self.btn_new_tab_compact.clicked.connect(lambda: self.new_tab_requested.emit("default"))
        self.btn_new_tab_compact.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_new_tab_compact.customContextMenuRequested.connect(lambda p: self._show_containers_menu())

        row_comp_layout.addWidget(self.btn_expand_compact)
        row_comp_layout.addWidget(self.btn_new_tab_compact)
        self.row_compact.hide()
        self._main_layout.addWidget(self.row_compact)

        # Tabs List
        self.list_widget = DraggableTabListWidget(self)
        self.list_widget.setObjectName("verticalTabsList")
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setHorizontalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
        self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_widget.currentRowChanged.connect(self._on_row_changed)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._show_tab_context_menu)
        self._main_layout.addWidget(self.list_widget)

        self.current_theme = "dark"
        self.current_accent = "#fe8019"
        self.update_theme(self.current_theme, self.current_accent)

    def set_expanded_width(self, width: int) -> None:
        try:
            self.expanded_width = int(width)
        except Exception:
            return
        if not self.is_compact:
            self.setFixedWidth(self.expanded_width)
            for row in range(self.list_widget.count()):
                item = self.list_widget.item(row)
                if item:
                    item.setSizeHint(QSize(max(180, self.expanded_width - 20), 36))

    def toggle_compact(self) -> bool:
        self.is_compact = not self.is_compact
        target_w = 50 if self.is_compact else getattr(self, "expanded_width", 240)

        if self.is_compact:
            self.setFixedWidth(50)
            self._main_layout.setContentsMargins(4, 6, 4, 6)
            self.row_expanded.hide()
            self.row_compact.show()
        else:
            self.setFixedWidth(getattr(self, "expanded_width", 240))
            self._main_layout.setContentsMargins(8, 8, 8, 8)
            self.row_compact.hide()
            self.row_expanded.show()

        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if self.is_compact:
                item.setSizeHint(QSize(42, 36))
            else:
                item.setSizeHint(QSize(max(180, getattr(self, "expanded_width", 240) - 20), 36))
            widget = self.list_widget.itemWidget(item)
            if isinstance(widget, TabItemWidget):
                widget.set_compact(self.is_compact)

        return self.is_compact

    def _on_row_changed(self, row: int) -> None:
        if row >= 0:
            item = self.list_widget.item(row)
            if item:
                tab_id = item.data(Qt.ItemDataRole.UserRole)
                self.tab_selected.emit(tab_id)

    def _show_tab_context_menu(self, pos) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        tab_id = item.data(Qt.ItemDataRole.UserRole)
        
        tab_data = None
        tm = self.parent()
        if tm and hasattr(tm, "tabs") and tab_id in tm.tabs:
            tab_data = tm.tabs[tab_id]

        menu = QMenu(self)

        # Pin / Unpin
        is_pinned = tab_data.is_pinned if tab_data else False
        act_pin = menu.addAction("Unpin Tab" if is_pinned else "Pin Tab")
        act_pin.triggered.connect(lambda: self.pin_tab_requested.emit(tab_id))

        # Groups Submenu
        group_menu = menu.addMenu("Group Tab")
        act_no_group = group_menu.addAction("No Group (Clear)")
        act_no_group.triggered.connect(lambda: self.set_tab_group_requested.emit(tab_id, ""))

        existing_groups = set()
        if tm and hasattr(tm, "tabs"):
            for td in tm.tabs.values():
                if td.group:
                    existing_groups.add(td.group)
        if existing_groups:
            group_menu.addSeparator()
            for g in sorted(existing_groups):
                act_g = group_menu.addAction(f"Move to '{g}'")
                act_g.triggered.connect(lambda checked, grp=g: self.set_tab_group_requested.emit(tab_id, grp))

        group_menu.addSeparator()
        act_new_group = group_menu.addAction("Add to New Group...")
        act_new_group.triggered.connect(lambda: self._prompt_new_group(tab_id))

        menu.addSeparator()

        # Mute / Unmute
        is_muted = tab_data.is_muted if tab_data else False
        act_mute = menu.addAction(t("unmute_tab") if is_muted else t("mute_tab"))
        act_mute.triggered.connect(lambda: self.mute_tab_requested.emit(tab_id))

        act_dup = menu.addAction(t("duplicate_tab"))
        act_dup.triggered.connect(lambda: self.duplicate_tab_requested.emit(tab_id))

        act_split = menu.addAction(t("split_view"))
        act_split.triggered.connect(lambda: self.split_tab_requested.emit(tab_id))

        tm = self.parent()
        is_active = (tm and hasattr(tm, "active_tab_id") and tm.active_tab_id == tab_id)
        if is_active:
            act_suspend = menu.addAction(t("suspend_tab") + f" [{t('tab_active_badge')}]")
            act_suspend.setEnabled(False)
            act_suspend.setToolTip(t("suspend_active_error"))
        else:
            act_suspend = menu.addAction(t("suspend_tab"))
            act_suspend.triggered.connect(lambda: self.suspend_tab_requested.emit(tab_id))

        # Reopen in Container Submenu
        from config import CONTAINERS
        reopen_title = t("reopen_in_container")
        reopen_menu = menu.addMenu(reopen_title)
        for c_key, c_info in CONTAINERS.items():
            badge = c_info.get("badge", c_key.upper())
            name = c_info.get("name", c_key.capitalize())
            act_c = reopen_menu.addAction(f"[{badge}] {name}")
            act_c.triggered.connect(lambda checked, ck=c_key: self.reopen_in_container_requested.emit(tab_id, ck))

        menu.addSeparator()

        act_close = menu.addAction(t("close_tab"))
        act_close.setEnabled(not is_pinned)
        act_close.triggered.connect(lambda: self.tab_closed.emit(tab_id))

        menu.exec(self.list_widget.mapToGlobal(pos))

    def _show_containers_menu(self) -> None:
        from config import CONTAINERS
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QCursor
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background-color: #18181b; border: 1px solid #3f3f46; color: #d4d4d8; font-family: monospace; font-size: 11px; padding: 4px; }
            QMenu::item { padding: 6px 14px; }
            QMenu::item:selected { background-color: #262624; color: #a855f7; }
        """)
        hdr = menu.addAction(t("profile_containers_header"))
        hdr.setEnabled(False)
        for c_key, c_info in CONTAINERS.items():
            badge = c_info.get("badge", c_key.upper())
            name = c_info.get("name", c_key.capitalize())
            act = menu.addAction(f"[{badge}] {name}")
            act.triggered.connect(lambda checked, ck=c_key: self.new_tab_container_requested.emit("crux://startpage", ck))
        menu.exec(QCursor.pos())

    def _prompt_new_group(self, tab_id: int) -> None:
        from PyQt6.QtWidgets import QInputDialog
        group_name, ok = QInputDialog.getText(self, "Tab Group", "Enter group name (e.g. Work, Dev, Research):")
        if ok and group_name.strip():
            self.set_tab_group_requested.emit(tab_id, group_name.strip())

    def retranslate_ui(self) -> None:
        self.btn_new_tab.setText(t("new_tab_btn"))
        self.btn_collapse.setToolTip(t("collapse_sidebar"))
        self.btn_expand_compact.setToolTip(t("expand_sidebar"))
        self.btn_new_tab_compact.setToolTip(t("new_tab"))

    def update_theme(self, theme: str = "dark", accent: str = "#a855f7") -> None:
        self.current_theme = theme
        self.current_accent = accent
        border_muted = "#3f3f46" if theme == "dark" else "#cbd5e1"
        bg_elevated = "#2d2d2a" if theme == "dark" else "#f1f5f9"
        text_bright = "#f5f5f0" if theme == "dark" else "#0f172a"
        accent_btn_style = f"""
            QPushButton#accentBtn {{
                background-color: transparent;
                border: 1px solid {border_muted};
                border-bottom: 2px solid {accent};
                color: {text_bright};
                font-weight: bold;
            }}
            QPushButton#accentBtn:hover {{
                background-color: {bg_elevated};
                border: 1px solid {border_muted};
                border-bottom: 2px solid {accent};
                color: {accent};
            }}
            QPushButton#accentBtn:pressed {{
                background-color: transparent;
                border: 1px solid {border_muted};
                border-bottom: 2px solid {accent};
                color: {accent};
            }}
        """
        self.btn_new_tab.setStyleSheet(accent_btn_style)
        self.btn_new_tab_compact.setStyleSheet(accent_btn_style)

        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item:
                widget = self.list_widget.itemWidget(item)
                if isinstance(widget, TabItemWidget):
                    widget.update_theme(theme, accent)

    def get_tab_widget(self, tab_id: int):
        for row in range(self.list_widget.count()):
            item = self.list_widget.item(row)
            if item:
                widget = self.list_widget.itemWidget(item)
                if isinstance(widget, TabItemWidget) and widget.tab_data.tab_id == tab_id:
                    return widget
        return None


class TabManager(QWidget):
    active_tab_changed = pyqtSignal(SplitViewContainer)
    active_url_changed = pyqtSignal(QUrl)
    active_title_changed = pyqtSignal(str)
    all_tabs_closed = pyqtSignal()
    tabs_updated = pyqtSignal()

    def retranslate_ui(self) -> None:
        self.sidebar.retranslate_ui()

    def update_theme(self, theme: str = "dark", accent: str = "#a855f7") -> None:
        self.current_theme = theme
        self.current_accent = accent
        self.sidebar.update_theme(theme, accent)

    def __init__(self, profile_manager: ProfileManager, parent=None):
        super().__init__(parent)
        self.profile_manager = profile_manager
        self.current_theme = "dark"
        self.current_accent = "#a855f7"
        if parent and hasattr(parent, "settings"):
            self.current_theme = parent.settings.get("theme", "dark")
            self.current_accent = parent.settings.get("accent_color", "#a855f7")
        self.tabs: Dict[int, TabItemData] = {}
        self.tab_counter = 0
        self.active_tab_id = -1

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left Vertical Tabs Sidebar
        self.sidebar = VerticalTabSidebar(self)
        self.sidebar.tab_selected.connect(self.select_tab)
        self.sidebar.tab_closed.connect(self.close_tab)
        self.sidebar.new_tab_requested.connect(self.create_tab)
        self.sidebar.new_tab_container_requested.connect(lambda u, cid: self.create_tab(url=u, container_id=cid))
        self.sidebar.reopen_in_container_requested.connect(self.reopen_in_container)
        self.sidebar.duplicate_tab_requested.connect(self.duplicate_tab)
        self.sidebar.split_tab_requested.connect(self.split_active_tab)
        self.sidebar.suspend_tab_requested.connect(self.suspend_tab)
        self.sidebar.pin_tab_requested.connect(self.toggle_pin_tab)
        self.sidebar.mute_tab_requested.connect(self.toggle_mute_tab)
        self.sidebar.set_tab_group_requested.connect(self.set_tab_group)
        self.sidebar.list_widget.tab_reordered.connect(self._on_tabs_reordered)
        main_layout.addWidget(self.sidebar)

        # Center Stacked Widget
        self.stack = QStackedWidget(self)
        main_layout.addWidget(self.stack, stretch=1)

        # Background Tab Suspension Timer (checks idle tabs every 60s)
        self.suspend_timer = QTimer(self)
        self.suspend_timer.setInterval(60000)
        self.suspend_timer.timeout.connect(self._check_tab_suspension)
        self.suspend_timer.start()

    def get_tab_view(self, tab_id: int) -> Optional[ZincWebView]:
        if tab_id in self.tabs:
            sc = self.tabs[tab_id].split_container
            if sc:
                return sc.get_active_view()
        return None

    def reopen_in_container(self, tab_id: int, container_id: str) -> None:
        if tab_id not in self.tabs:
            return
        tab_data = self.tabs[tab_id]
        v = tab_data.split_container.get_active_view()
        url = getattr(tab_data, "url", "") or (v.url().toString() if v else "crux://startpage")
        if url.startswith("data:text/html") or url.startswith("data:"):
            url = "crux://startpage"
        if "startpage" in url.lower():
            url = "crux://startpage"
        self.create_tab(url=url, container_id=container_id)
        self.close_tab(tab_id)

    def create_tab(self, url: str = "crux://startpage", *args, **kwargs) -> int:
        target_url = url
        if args and isinstance(args[0], str) and ("://" in args[0] or args[0].startswith("about:") or args[0].startswith("crux:") or args[0].startswith("zephyrium:") or args[0].startswith("zinc:")):
            target_url = args[0]
        elif not ("://" in str(target_url) or str(target_url).startswith("about:") or str(target_url).startswith("crux:") or str(target_url).startswith("zephyrium:") or str(target_url).startswith("zinc:")):
            target_url = "crux://startpage"
            if args and isinstance(args[0], str):
                target_url = args[0]
        if "url" in kwargs and kwargs["url"]:
            target_url = kwargs["url"]

        if target_url in ["crux://startpage", "zephyrium://startpage", "default"]:
            win = self.parent()
            pref_url = ""
            if win and hasattr(win, "settings"):
                pref_url = win.settings.get("new_tab_url", "")
            if not pref_url:
                try:
                    from config import load_settings
                    pref_url = load_settings().get("new_tab_url", "")
                except Exception:
                    pass
            if pref_url and pref_url.strip():
                target_url = pref_url.strip()

        self.tab_counter += 1
        tab_id = self.tab_counter

        # Build Web View & Split Container (support container/profile selection)
        win = self.parent()
        is_win_incognito = getattr(win, "is_incognito", False)
        default_container = "incognito" if is_win_incognito else "default"
        container_id = kwargs.get("container_id", default_container)
        if args and isinstance(args[0], str) and args[0] in CONTAINERS:
            container_id = args[0]
        if is_win_incognito:
            container_id = "incognito"
        profile = self.profile_manager.get_profile(container_id)
        web_view = ZincWebView(profile, container_id)
        
        # Disable autoplay without user gesture to save bandwidth/RAM
        from PyQt6.QtWebEngineCore import QWebEngineSettings
        web_view.settings().setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, True)

        split_container = SplitViewContainer(self.profile_manager, web_view, self)

        tab_data = TabItemData(tab_id, container_id, split_container)
        self.tabs[tab_id] = tab_data

        # Stack widget
        self.stack.addWidget(split_container)

        # Sidebar list item
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, tab_id)
        
        # Set clean initial title based on target_url
        initial_title = "New Tab"
        if "settings" in target_url:
            initial_title = t("settings")
        elif "history" in target_url:
            initial_title = t("history_title")
        elif "downloads" in target_url:
            initial_title = t("downloads_title")
        elif "welcome" in target_url:
            initial_title = "Welcome"
        tab_data.title = initial_title
        tab_data.url = target_url

        item_widget = TabItemWidget(tab_data, self.sidebar.list_widget)
        item_widget.update_theme(getattr(self, "current_theme", "dark"), getattr(self, "current_accent", "#a855f7"))
        item_widget.close_clicked.connect(self.close_tab)
        item_widget.mute_clicked.connect(self.toggle_mute_tab)
        item._stored_widget = item_widget

        if self.sidebar.is_compact:
            item.setSizeHint(QSize(42, 36))
            item_widget.set_compact(True)
        else:
            item.setSizeHint(QSize(220, 36))

        self.sidebar.list_widget.addItem(item)
        self.sidebar.list_widget.setItemWidget(item, item_widget)

        # Signal connections for title & url
        split_container.title_changed.connect(lambda t: self._on_title_changed(tab_id, t))
        split_container.url_changed.connect(lambda u: self._on_url_changed(tab_id, u))
        web_view.titleChanged.connect(lambda t: self._on_title_changed(tab_id, t))
        web_view.urlChanged.connect(lambda u: self._on_url_changed(tab_id, u))
        web_view.page().recentlyAudibleChanged.connect(lambda aud, tid=tab_id: self._on_audible_changed(tid, aud))

        # Navigate
        web_view.navigate(target_url)

        self.select_tab(tab_id)
        self.tabs_updated.emit()
        return tab_id

    def toggle_pin_tab(self, tab_id: int) -> None:
        if tab_id in self.tabs:
            td = self.tabs[tab_id]
            td.is_pinned = not td.is_pinned

            # Reorder: pinned tabs always stay at the top of the list!
            curr_row = -1
            for row in range(self.sidebar.list_widget.count()):
                item = self.sidebar.list_widget.item(row)
                if item and item.data(Qt.ItemDataRole.UserRole) == tab_id:
                    curr_row = row
                    break

            if curr_row >= 0:
                if td.is_pinned:
                    target_row = 0
                    for row in range(self.sidebar.list_widget.count()):
                        if row == curr_row:
                            continue
                        other_item = self.sidebar.list_widget.item(row)
                        other_id = other_item.data(Qt.ItemDataRole.UserRole)
                        if other_id in self.tabs and self.tabs[other_id].is_pinned:
                            target_row += 1
                    if curr_row != target_row:
                        self.sidebar.list_widget.move_tab_row(curr_row, target_row)
                else:
                    pinned_count = sum(1 for t in self.tabs.values() if t.is_pinned)
                    if curr_row < pinned_count:
                        self.sidebar.list_widget.move_tab_row(curr_row, pinned_count)

            self._refresh_tab_item_widget(tab_id)
            self.tabs_updated.emit()

    def toggle_mute_tab(self, tab_id: int) -> None:
        if tab_id in self.tabs:
            td = self.tabs[tab_id]
            td.is_muted = not td.is_muted
            view = self.get_tab_view(tab_id)
            if view and hasattr(view, "page"):
                view.page().setAudioMuted(td.is_muted)
            self._refresh_tab_item_widget(tab_id)
            self.tabs_updated.emit()

    def _on_audible_changed(self, tab_id: int, audible: bool) -> None:
        if tab_id in self.tabs:
            self.tabs[tab_id].is_audible = audible
            self._refresh_tab_item_widget(tab_id)
            self.tabs_updated.emit()

    def _on_tabs_reordered(self, from_row: int, to_row: int) -> None:
        self.tabs_updated.emit()

    def set_tab_group(self, tab_id: int, group_name: str) -> None:
        if tab_id in self.tabs:
            td = self.tabs[tab_id]
            td.group = group_name.strip()
            self._refresh_tab_item_widget(tab_id)
            self.tabs_updated.emit()

    def _refresh_tab_item_widget(self, tab_id: int) -> None:
        for row in range(self.sidebar.list_widget.count()):
            item = self.sidebar.list_widget.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == tab_id:
                widget = self.sidebar.list_widget.itemWidget(item)
                if isinstance(widget, TabItemWidget):
                    widget.refresh_ui()
                break

    def select_tab(self, tab_id: int) -> None:
        if tab_id not in self.tabs:
            return

        tab_data = self.tabs[tab_id]
        clean_url = tab_data.url or "crux://startpage"
        if clean_url.startswith("data:text/html") or clean_url.startswith("data:"):
            clean_url = "crux://startpage"
            tab_data.url = clean_url
        clean_title = tab_data.title or "New Tab"

        # Wake up tab if suspended
        if tab_data.is_suspended:
            self.wake_tab(tab_id)

        self.active_tab_id = tab_id
        tab_data.last_active_time = time.time()
        self.stack.setCurrentWidget(tab_data.split_container)

        # Select corresponding row in sidebar
        for row in range(self.sidebar.list_widget.count()):
            item = self.sidebar.list_widget.item(row)
            is_active = (item.data(Qt.ItemDataRole.UserRole) == tab_id)
            if is_active:
                self.sidebar.list_widget.setCurrentRow(row)
            widget = self.sidebar.list_widget.itemWidget(item)
            if isinstance(widget, TabItemWidget):
                widget.set_active(is_active)

        self.active_tab_changed.emit(tab_data.split_container)
        # Always emit real URL and title, never data:text/html
        self.active_url_changed.emit(QUrl(clean_url))
        self.active_title_changed.emit(clean_title)

    def close_tab(self, tab_id: int) -> None:
        if tab_id not in self.tabs:
            return

        # Do not close pinned tabs via close button or shortcut
        if self.tabs[tab_id].is_pinned:
            return

        visible_count = self.sidebar.list_widget.count()

        # If it's the last tab in memory or last visible tab
        if len(self.tabs) <= 1 or visible_count <= 1:
            for tid, tab_data in list(self.tabs.items()):
                try:
                    self.stack.removeWidget(tab_data.split_container)
                    tab_data.split_container.deleteLater()
                except Exception:
                    pass
            self.tabs.clear()
            self.sidebar.list_widget.clear()
            self.all_tabs_closed.emit()
            return

        tab_data = self.tabs.pop(tab_id)
        self.stack.removeWidget(tab_data.split_container)
        tab_data.split_container.deleteLater()

        # Remove from sidebar list
        for row in range(self.sidebar.list_widget.count()):
            item = self.sidebar.list_widget.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == tab_id:
                self.sidebar.list_widget.takeItem(row)
                break

        # Safety check: if no tabs remain in sidebar after removal
        if self.sidebar.list_widget.count() == 0:
            for tid, td in list(self.tabs.items()):
                try:
                    self.stack.removeWidget(td.split_container)
                    td.split_container.deleteLater()
                except Exception:
                    pass
            self.tabs.clear()
            self.all_tabs_closed.emit()
            return

        # Select neighbor
        if self.active_tab_id == tab_id:
            next_row = max(0, min(self.sidebar.list_widget.currentRow(), self.sidebar.list_widget.count() - 1))
            if self.sidebar.list_widget.count() > 0:
                next_item = self.sidebar.list_widget.item(next_row)
                self.select_tab(next_item.data(Qt.ItemDataRole.UserRole))
        self.tabs_updated.emit()

    def duplicate_tab(self, tab_id: int) -> None:
        if tab_id in self.tabs:
            current_url = self.tabs[tab_id].split_container.get_active_view().url().toString()
            self.create_tab(current_url)

    def split_active_tab(self, tab_id: int = -1) -> None:
        target_id = tab_id if tab_id != -1 else self.active_tab_id
        if target_id in self.tabs:
            self.tabs[target_id].split_container.toggle_split()

    def suspend_tab(self, tab_id: int) -> bool:
        try:
            if tab_id not in self.tabs or tab_id == self.active_tab_id:
                return False
            tab_data = self.tabs[tab_id]
            if tab_data.is_suspended or tab_data.is_pinned or getattr(tab_data, "is_audible", False):
                return False

            if not tab_data.split_container:
                return False
            view = tab_data.split_container.get_active_view()
            if not view:
                return False
            view_url = view.url().toString() if (view and not view.url().isEmpty()) else ""
            url_str = getattr(tab_data, "url", "") or view_url or ""
            # Never suspend internal or special scheme pages (settings, startpage, history, etc.)
            if not url_str or any(url_str.startswith(s) for s in ["crux://", "zephyrium://", "zinc://", "about:", "chrome://", "data:"]):
                return False
            if any(k in url_str for k in ["settings.html", "startpage.html", "history.html", "downloads.html", "welcome.html"]):
                return False

            tab_data.is_suspended = True
            tab_data.url = url_str
            # Save scroll position
            try:
                view.page().runJavaScript(
                    "({x: window.scrollX, y: window.scrollY})",
                    lambda pos: setattr(tab_data, "saved_scroll", (pos.get("x", 0), pos.get("y", 0)) if isinstance(pos, dict) else (0, 0))
                )
            except Exception:
                pass
            acc = getattr(self, "current_accent", "#a855f7")
            th = getattr(self, "current_theme", "dark")
            bg = "#18181b" if th == "dark" else "#f8fafc"
            card_bg = "#262624" if th == "dark" else "#ffffff"
            card_border = "#3f3f46" if th == "dark" else "#cbd5e1"
            fg_title = "#d4d4d8" if th == "dark" else "#1e293b"
            fg_muted = "#71717a" if th == "dark" else "#64748b"
            clean_title = html.escape(tab_data.title or "Web Page")
            view.setHtml(f"""
                <!DOCTYPE html><html><head><meta charset="utf-8"><title>{clean_title}</title></head>
                <body onclick="window.location.reload()" style="background:{bg};color:{fg_muted};font-family:system-ui, -apple-system, sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:95vh;user-select:none;cursor:pointer;margin:0;">
                <div style="border:1px solid {card_border};border-radius:0px;padding:32px;background:{card_bg};text-align:center;max-width:420px;box-shadow:0 6px 20px rgba(0,0,0,0.4);font-family:monospace;">
                    <div style="font-size:22px;margin-bottom:12px;color:{acc};font-weight:bold;">[SLEEP]</div>
                    <div style="color:{acc};font-weight:bold;font-size:13px;letter-spacing:1px;margin-bottom:8px;">{t("tab_suspended_title")}</div>
                    <div style="color:{fg_title};font-size:14px;font-weight:bold;margin-bottom:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{clean_title}</div>
                    <div style="font-size:11px;color:{fg_muted};margin-bottom:16px;">{t("tab_suspended_hint")}</div>
                    <div style="font-size:11px;color:{acc};background:{bg};padding:6px 12px;border:1px solid {card_border};display:inline-block;">{t("wake_tab").upper()}</div>
                </div>
                </body></html>
            """)
            if hasattr(self, "sidebar") and hasattr(self.sidebar, "list_widget"):
                for row in range(self.sidebar.list_widget.count()):
                    item = self.sidebar.list_widget.item(row)
                    if item.data(Qt.ItemDataRole.UserRole) == tab_id:
                        widget = self.sidebar.list_widget.itemWidget(item)
                        if isinstance(widget, TabItemWidget):
                            widget.refresh_ui()
                        break
            self.tabs_updated.emit()
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False

    def wake_tab(self, tab_id: int) -> None:
        try:
            if tab_id in self.tabs:
                tab_data = self.tabs[tab_id]
                if tab_data.is_suspended:
                    tab_data.is_suspended = False
                    if not tab_data.split_container:
                        return
                    view = tab_data.split_container.get_active_view()
                    if not view:
                        return
                    target_url = tab_data.url or "crux://startpage"
                    if target_url.startswith("data:text/html") or target_url.startswith("data:"):
                        target_url = "crux://startpage"
                        tab_data.url = target_url
                    view.load(QUrl(target_url))
                    scroll_pos = getattr(tab_data, "saved_scroll", (0, 0))
                    if scroll_pos and (scroll_pos[0] > 0 or scroll_pos[1] > 0):
                        def _restore_scroll(ok):
                            if ok and view:
                                try:
                                    view.page().runJavaScript(f"window.scrollTo({scroll_pos[0]}, {scroll_pos[1]});")
                                except Exception:
                                    pass
                        try:
                            view.loadFinished.connect(_restore_scroll)
                        except Exception:
                            pass
                    if hasattr(self, "sidebar") and hasattr(self.sidebar, "list_widget"):
                        for row in range(self.sidebar.list_widget.count()):
                            item = self.sidebar.list_widget.item(row)
                            if item.data(Qt.ItemDataRole.UserRole) == tab_id:
                                widget = self.sidebar.list_widget.itemWidget(item)
                                if isinstance(widget, TabItemWidget):
                                    widget.refresh_ui()
                                break
                    self.tabs_updated.emit()
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _check_tab_suspension(self) -> None:
        try:
            from config import load_settings
            s = load_settings()
            hib_setting = s.get("tab_hibernation", "30")
            if hib_setting == "never":
                return
            try:
                timeout_sec = int(hib_setting) * 60
            except Exception:
                timeout_sec = 1800

            now = time.time()
            for tid, data in list(self.tabs.items()):
                if tid != self.active_tab_id and not data.is_suspended:
                    if (now - data.last_active_time) > timeout_sec:
                        self.suspend_tab(tid)
        except Exception:
            pass

    def get_current_split_container(self) -> Optional[SplitViewContainer]:
        if self.active_tab_id in self.tabs:
            return self.tabs[self.active_tab_id].split_container
        return None

    def get_current_view(self) -> Optional[ZincWebView]:
        sc = self.get_current_split_container()
        if sc:
            return sc.get_active_view()
        return None

    def _on_title_changed(self, tab_id: int, title: str) -> None:
        if tab_id in self.tabs:
            tab_data = self.tabs[tab_id]
            # NEVER overwrite title while tab is suspended or with data URIs
            if tab_data.is_suspended:
                return
            if title and title.strip() and not title.strip().startswith("data:text/html") and not title.strip().startswith("data:"):
                tab_data.title = title.strip()
            title_to_use = tab_data.title
            for row in range(self.sidebar.list_widget.count()):
                item = self.sidebar.list_widget.item(row)
                if item.data(Qt.ItemDataRole.UserRole) == tab_id:
                    widget = self.sidebar.list_widget.itemWidget(item)
                    if isinstance(widget, TabItemWidget):
                        widget.set_title(title_to_use)
                    break
            if tab_id == self.active_tab_id:
                self.active_title_changed.emit(title_to_use)
            self.tabs_updated.emit()

    def _on_url_changed(self, tab_id: int, url: QUrl) -> None:
        if tab_id in self.tabs:
            tab_data = self.tabs[tab_id]
            url_str = url.toString()
            # NEVER overwrite real URL if tab is suspended or with data URI
            if tab_data.is_suspended or url_str.startswith("data:text/html") or url_str.startswith("data:"):
                return
            tab_data.url = url_str
            if tab_id == self.active_tab_id:
                self.active_url_changed.emit(url)
