"""
Password Save Prompt Banner for Crux Browser
Floats non-intrusively in the top-right corner when login/password submission is detected.
Allows saving to vault, adding to exclusions ('Больше не спрашивать'), or dismissing.
Anthropic Minimal Dark aesthetic (Square UI, 0px border-radius, 1px border, monospace typography).
"""
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QWidget, QGridLayout
)
from core.i18n import t
from core.password_autofill import PasswordAutofillManager

class PasswordSaveBanner(QFrame):
    saved = pyqtSignal(str, str)     # (url, username)
    dismissed = pyqtSignal()
    never_save = pyqtSignal(str)     # (domain)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("passwordSaveBanner")
        self.setFixedSize(390, 185)

        self.current_url = ""
        self.current_domain = ""
        self.accent = "#a855f7"
        self.theme = "dark"
        self.is_password_visible = False

        # Outer Frame layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(8)

        # Header Row
        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        self.title_label = QLabel(f"[ {t('save_pwd_title')} ]")
        self.title_label.setObjectName("pwdPromptTitle")
        self.title_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {self.accent}; letter-spacing: 1px;")

        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(22, 22)
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.hide)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_close)
        main_layout.addLayout(header_layout)

        # Site domain label
        self.domain_label = QLabel()
        self.domain_label.setStyleSheet("font-size: 11px; color: #a1a1aa;")
        main_layout.addWidget(self.domain_label)

        # Form: Username & Password fields
        form_layout = QGridLayout()
        form_layout.setContentsMargins(0, 2, 0, 2)
        form_layout.setHorizontalSpacing(8)
        form_layout.setVerticalSpacing(6)

        self.lbl_user = QLabel(f"{t('username')}:")
        self.lbl_user.setStyleSheet("font-size: 11px; color: #71717a; font-weight: bold;")
        self.input_user = QLineEdit()
        self.input_user.setFixedHeight(26)

        self.lbl_pwd = QLabel(f"{t('password')}:")
        self.lbl_pwd.setStyleSheet("font-size: 11px; color: #71717a; font-weight: bold;")

        pwd_row = QHBoxLayout()
        pwd_row.setSpacing(4)
        pwd_row.setContentsMargins(0, 0, 0, 0)
        self.input_pwd = QLineEdit()
        self.input_pwd.setFixedHeight(26)
        self.input_pwd.setEchoMode(QLineEdit.EchoMode.Password)

        self.btn_toggle_pwd = QPushButton(t("show_pwd"))
        self.btn_toggle_pwd.setFixedHeight(26)
        self.btn_toggle_pwd.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_toggle_pwd.clicked.connect(self._toggle_password_peek)
        pwd_row.addWidget(self.input_pwd, stretch=1)
        pwd_row.addWidget(self.btn_toggle_pwd)

        form_layout.addWidget(self.lbl_user, 0, 0)
        form_layout.addWidget(self.input_user, 0, 1)
        form_layout.addWidget(self.lbl_pwd, 1, 0)
        form_layout.addLayout(pwd_row, 1, 1)
        main_layout.addLayout(form_layout)

        # Feedback / Status label (for "Сохранено" confirmation)
        self.status_feedback = QLabel()
        self.status_feedback.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_feedback.setStyleSheet("font-size: 10px; font-weight: bold; color: #10b981;")
        self.status_feedback.hide()
        main_layout.addWidget(self.status_feedback)

        # Buttons Row
        self.btns_layout = QHBoxLayout()
        self.btns_layout.setSpacing(6)

        self.btn_save = QPushButton(t("btn_save_cred"))
        self.btn_save.setFixedHeight(28)
        self.btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_save.clicked.connect(self._on_save_clicked)

        self.btn_never = QPushButton(t("btn_never_save"))
        self.btn_never.setFixedHeight(28)
        self.btn_never.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_never.clicked.connect(self._on_never_clicked)

        self.btn_not_now = QPushButton(t("btn_not_now"))
        self.btn_not_now.setFixedHeight(28)
        self.btn_not_now.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_not_now.clicked.connect(self.hide)

        self.btns_layout.addWidget(self.btn_save, stretch=2)
        self.btns_layout.addWidget(self.btn_never, stretch=3)
        self.btns_layout.addWidget(self.btn_not_now, stretch=2)
        main_layout.addLayout(self.btns_layout)

        self.update_theme("dark", "#a855f7")

    def set_credentials(self, url: str, username: str, password: str) -> None:
        self.current_url = url
        self.current_domain = PasswordAutofillManager._extract_domain(url)
        self.domain_label.setText(f"{t('save_pwd_site')} {self.current_domain}")
        self.input_user.setText(username or "")
        self.input_pwd.setText(password or "")
        self.input_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.is_password_visible = False
        self.btn_toggle_pwd.setText(t("show_pwd"))
        self.status_feedback.hide()
        self.btn_save.setEnabled(True)
        self.btn_never.setEnabled(True)
        self.btn_not_now.setEnabled(True)

    def _toggle_password_peek(self) -> None:
        self.is_password_visible = not self.is_password_visible
        if self.is_password_visible:
            self.input_pwd.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_toggle_pwd.setText(t("hide_pwd"))
        else:
            self.input_pwd.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_toggle_pwd.setText(t("show_pwd"))

    def _on_save_clicked(self) -> None:
        user = self.input_user.text().strip()
        pwd = self.input_pwd.text()
        if not user or not pwd:
            return

        PasswordAutofillManager.save_credential(self.current_url or self.current_domain, user, pwd)
        self.status_feedback.setText(f"✓ {t('pwd_saved_status')}")
        self.status_feedback.setStyleSheet("font-size: 11px; font-weight: bold; color: #10b981;")
        self.status_feedback.show()
        self.btn_save.setEnabled(False)
        self.saved.emit(self.current_url, user)
        QTimer.singleShot(900, self.hide)

    def _on_never_clicked(self) -> None:
        PasswordAutofillManager.add_never_save(self.current_url or self.current_domain)
        self.status_feedback.setText(f"✓ {t('never_saved_status')}")
        self.status_feedback.setStyleSheet("font-size: 11px; font-weight: bold; color: #f59e0b;")
        self.status_feedback.show()
        self.btn_never.setEnabled(False)
        self.never_save.emit(self.current_domain)
        QTimer.singleShot(900, self.hide)

    def update_theme(self, theme: str = "dark", accent: str = "#a855f7") -> None:
        self.theme = theme
        self.accent = accent
        bg = "#18181b" if theme == "dark" else "#ffffff"
        fg = "#f5f5f0" if theme == "dark" else "#0f172a"
        border_muted = "#3f3f46" if theme == "dark" else "#cbd5e1"
        btn_bg = "#27272a" if theme == "dark" else "#f1f5f9"

        self.setStyleSheet(f"""
            QFrame#passwordSaveBanner {{
                background-color: {bg};
                border: 1px solid {accent};
                border-radius: 0px;
            }}
            QLabel {{
                color: {fg};
                font-family: monospace;
            }}
            QLineEdit {{
                background-color: {btn_bg};
                border: 1px solid {border_muted};
                color: {fg};
                font-family: monospace;
                font-size: 11px;
                padding: 2px 6px;
                border-radius: 0px;
            }}
            QLineEdit:focus {{
                border-color: {accent};
            }}
            QPushButton {{
                background-color: {btn_bg};
                border: 1px solid {border_muted};
                color: {fg};
                font-family: monospace;
                font-size: 10px;
                font-weight: bold;
                border-radius: 0px;
                padding: 2px 6px;
            }}
            QPushButton:hover {{
                border-color: {accent};
                color: {accent};
            }}
            QPushButton#btnSaveCred {{
                background-color: {accent};
                color: #0f172a;
                border: 1px solid {accent};
            }}
            QPushButton#btnSaveCred:hover {{
                opacity: 0.9;
            }}
        """)
        self.btn_save.setObjectName("btnSaveCred")
        self.btn_save.setStyleSheet(f"background-color: {accent}; color: #0f172a; font-weight: bold; border: 1px solid {accent};")
        self.title_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {accent}; letter-spacing: 1px;")

    def retranslate_ui(self) -> None:
        self.title_label.setText(f"[ {t('save_pwd_title')} ]")
        if self.current_domain:
            self.domain_label.setText(f"{t('save_pwd_site')} {self.current_domain}")
        self.lbl_user.setText(f"{t('username')}:")
        self.lbl_pwd.setText(f"{t('password')}:")
        self.btn_toggle_pwd.setText(t("hide_pwd") if self.is_password_visible else t("show_pwd"))
        self.btn_save.setText(t("btn_save_cred"))
        self.btn_never.setText(t("btn_never_save"))
        self.btn_not_now.setText(t("btn_not_now"))
