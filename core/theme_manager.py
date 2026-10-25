"""
Dynamic Theme and Color Engine for Zephyrium Browser
Supports Dark (Minimal Claude Code), Light (Clean Paper), and custom Accent Colors.
"""
from PyQt6.QtWidgets import QApplication

def generate_stylesheet(theme: str = "dark", accent: str = "#fe8019") -> str:
    if theme == "light":
        bg_base = "#f8fafc"
        bg_surface = "#ffffff"
        bg_elevated = "#f1f5f9"
        border_muted = "#cbd5e1"
        border_subtle = "#e2e8f0"
        border_active = accent
        text_primary = "#1e293b"
        text_bright = "#0f172a"
        text_muted = "#64748b"
        selection_bg = "#e2e8f0"
        selection_color = "#0f172a"
    else:  # dark
        bg_base = "#18181b"
        bg_surface = "#262624"
        bg_elevated = "#2d2d2a"
        border_muted = "#3f3f46"
        border_subtle = "#2b2b29"
        border_active = accent
        text_primary = "#d4d4d8"
        text_bright = "#f5f5f0"
        text_muted = "#71717a"
        selection_bg = "#2d2d2a"
        selection_color = "#f5f5f0"

    qss = f"""
    * {{
        font-family: "Iosevka Nerd Font", "JetBrains Mono", "DejaVu Sans Mono", monospace;
        font-size: 13px;
        border-radius: 0px;
    }}

    QMainWindow, QWidget {{
        background-color: {bg_base};
        color: {text_primary};
        border: none;
    }}

    QFrame, QGroupBox {{
        background-color: {bg_surface};
        border: 1px solid {border_muted};
        border-radius: 0px;
        padding: 0px;
    }}

    QSplitter, QStackedWidget {{
        border: none;
        background: transparent;
        padding: 0px;
        margin: 0px;
    }}

    #sidebar, #verticalTabsPanel, #downloadsDrawer, #notesPanel, #aiPanel {{
        background-color: {bg_surface};
        border-right: 1px solid {border_muted};
    }}

    #rightSidebar {{
        background-color: {bg_surface};
        border-left: 1px solid {border_muted};
    }}

    QSplitter::handle {{
        background-color: {border_muted};
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QSplitter::handle:vertical {{
        height: 1px;
    }}

    QPushButton, QToolButton {{
        background-color: {bg_surface};
        color: {text_primary};
        border: 1px solid {border_muted};
        border-radius: 0px;
        padding: 4px 8px;
        min-height: 24px;
        font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace;
        font-size: 12px;
    }}

    QPushButton:hover, QToolButton:hover {{
        background-color: {bg_elevated};
        border-color: {border_active};
        color: {text_bright};
    }}

    QPushButton:pressed, QToolButton:pressed {{
        background-color: {bg_base};
        border-color: {accent};
        color: {text_bright};
    }}

    QPushButton:disabled, QToolButton:disabled {{
        background-color: {bg_base};
        color: {text_muted};
        border-color: {border_subtle};
    }}

    QPushButton#accentWarmBtn {{
        background-color: transparent;
        border: 1px solid {accent};
        color: {accent};
        font-weight: bold;
    }}

    QPushButton#accentWarmBtn:hover {{
        background-color: {bg_elevated};
        border: 1px solid {accent};
        color: {accent};
    }}

    QPushButton#accentWarmBtn:pressed {{
        background-color: {bg_base};
        border: 1px solid {accent};
        color: {accent};
    }}

    QLineEdit, QTextEdit, QPlainTextEdit, QTextBrowser {{
        background-color: {bg_base};
        border: 1px solid {border_muted};
        border-radius: 0px;
        color: {text_primary};
        padding: 5px 8px;
        selection-background-color: {selection_bg};
        selection-color: {selection_color};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QTextBrowser:focus {{
        border: 1px solid {accent};
        background-color: {bg_base};
    }}

    QLineEdit::placeholder {{
        color: {text_muted};
    }}

    QComboBox {{
        background-color: {bg_base};
        border: 1px solid {border_muted};
        border-radius: 0px;
        color: {text_primary};
        padding: 4px 8px;
        min-height: 24px;
        font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace;
        font-size: 12px;
    }}

    QComboBox:focus {{
        border: 1px solid {accent};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 18px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {bg_surface};
        border: 1px solid {border_muted};
        color: {text_primary};
        selection-background-color: {bg_elevated};
        selection-color: {text_bright};
        outline: none;
        padding: 4px;
    }}

    QComboBox QAbstractItemView::item {{
        min-height: 26px;
        padding: 4px 8px;
        border: none;
    }}

    QComboBox QAbstractItemView::item:hover {{
        background-color: {bg_elevated};
        color: {text_bright};
    }}

    QComboBox QAbstractItemView::item:selected {{
        background-color: {bg_elevated};
        color: {accent};
    }}

    QComboBox QAbstractItemView QScrollBar:vertical {{
        background-color: {bg_surface};
        width: 8px;
        margin: 0px;
    }}

    QComboBox QAbstractItemView QScrollBar::handle:vertical {{
        background-color: {border_muted};
        min-height: 20px;
    }}

    QComboBox QAbstractItemView QScrollBar::handle:vertical:hover {{
        background-color: {accent};
    }}

    QCheckBox {{
        color: {text_primary};
        spacing: 6px;
        font-family: "Iosevka Nerd Font", "JetBrains Mono", monospace;
        font-size: 12px;
    }}

    QCheckBox::indicator {{
        width: 14px;
        height: 14px;
        background-color: {bg_surface};
        border: 1px solid {border_muted};
    }}

    QCheckBox::indicator:checked {{
        background-color: {accent};
        border-color: {accent};
    }}

    QDialog {{
        background-color: {bg_base};
        color: {text_primary};
    }}

    QListWidget {{
        background-color: {bg_surface};
        border: none;
        outline: none;
    }}

    QListWidget#verticalTabsList::item {{
        background-color: {bg_surface};
        color: {text_primary};
        border-bottom: 1px solid {border_subtle};
        padding: 0px;
        margin: 0px;
        min-height: 36px;
        height: 36px;
    }}

    QListWidget#verticalTabsList::item:hover {{
        background-color: {bg_elevated};
        color: {text_bright};
        border-left: 2px solid {border_muted};
    }}

    QListWidget#verticalTabsList::item:selected {{
        background-color: {bg_base};
        color: {text_bright};
        border-left: 2px solid {accent};
        border-right: none;
    }}

    QStatusBar {{
        background-color: {bg_base};
        color: {text_muted};
        border-top: 1px solid {border_muted};
        min-height: 28px;
        max-height: 28px;
        font-size: 11px;
        padding: 0 4px;
    }}

    QStatusBar QLabel {{
        color: {text_muted};
        padding: 0 4px;
    }}

    QProgressBar {{
        background-color: {bg_base};
        border: 1px solid {border_muted};
        border-radius: 0px;
        text-align: center;
        color: {text_primary};
        font-size: 10px;
        height: 12px;
    }}

    QProgressBar::chunk {{
        background-color: {accent};
    }}

    QScrollBar:vertical {{
        border: none;
        background: {bg_base};
        width: 6px;
        margin: 0px;
    }}

    QScrollBar::handle:vertical {{
        background: {border_muted};
        min-height: 20px;
    }}

    QScrollBar::handle:vertical:hover {{
        background: {border_active};
    }}

    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}

    QScrollBar:horizontal {{
        border: none;
        background: {bg_base};
        height: 6px;
        margin: 0px;
    }}

    QScrollBar::handle:horizontal {{
        background: {border_muted};
        min-width: 20px;
    }}

    QScrollBar::handle:horizontal:hover {{
        background: {border_active};
    }}

    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    QMenu {{
        background-color: {bg_surface};
        border: 1px solid {border_muted};
        padding: 4px 0px;
    }}

    QMenu::item {{
        background-color: transparent;
        color: {text_primary};
        padding: 6px 16px;
    }}

    QMenu::item:selected {{
        background-color: {bg_elevated};
        color: {text_bright};
    }}

    QMenu::separator {{
        height: 1px;
        background-color: {border_muted};
        margin: 4px 0px;
    }}

    QToolTip {{
        background-color: {bg_surface};
        color: {text_bright};
        border: 1px solid {border_active};
        padding: 4px 8px;
        font-size: 11px;
    }}

    QTabBar::close-button {{
        image: none;
        background: transparent;
        border: none;
        border-radius: 0px;
        padding: 0px;
        margin: 0px;
    }}
    """

    tab_bg = "#e2e8f0" if theme == "light" else "#27272a"
    tab_hover = "#cbd5e1" if theme == "light" else "#323238"

    qss += f"""
    #horizontalTabContainer {{
        background-color: {bg_base};
        border-bottom: 1px solid {border_muted};
    }}

    QTabBar {{
        background: transparent;
    }}

    QTabBar::tab {{
        background: {tab_bg};
        color: {text_muted};
        border: 1px solid {border_muted};
        border-bottom: none;
        border-radius: 0px;
        padding: 0px 8px;
        height: 26px;
        min-width: 90px;
        max-width: 220px;
        font-size: 11px;
        margin-right: 2px;
    }}

    QTabBar::tab:selected {{
        background: {bg_surface};
        color: {text_bright};
        border: 1px solid {border_muted};
        border-bottom: 2px solid {accent};
        font-weight: bold;
    }}

    QTabBar::tab:hover {{
        background: {tab_hover};
        color: {text_bright};
    }}

    #topBar {{
        background-color: {bg_surface};
        border-bottom: 1px solid {border_muted};
    }}

    QLineEdit#urlBar {{
        background-color: {bg_base};
        border: 1px solid {border_muted};
        border-radius: 0px;
        padding: 3px 8px;
        color: {text_bright};
        font-size: 12px;
    }}

    QLineEdit#urlBar:focus {{
        border: 1px solid {accent};
    }}

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
        background-color: {bg_base};
        border: 1px solid {border_muted};
        border-bottom: 2px solid {accent};
        color: {accent};
    }}
    """
    return qss

def apply_app_theme(app: QApplication, theme: str = "dark", accent: str = "#fe8019") -> None:
    if not app:
        return
    qss = generate_stylesheet(theme, accent)
    app.setStyleSheet(qss)
    for widget in app.allWidgets():
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

