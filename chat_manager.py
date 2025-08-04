from PyQt5.QtWidgets import (
    QWidget, QListWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QPushButton
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap


class ChatManagerWindow(QWidget):
    def __init__(self, tray_ref):
        super().__init__()
        self.tray_ref = tray_ref

        self.setWindowTitle("Lucid Chat Manager")
        self.setFixedSize(600, 500)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
            QWidget {
                background-color: #000c18;
                border: 1px solid #334455;
                border-radius: 10px;
                color: #aaccff;
                font-family: 'Segoe UI', sans-serif;
            }
            QListWidget {
                background-color: #001626;
                border: none;
                padding: 8px;
                font-size: 11pt;
                color: #aaccff;
            }
            QListWidget::item:selected {
                background-color: #334455;
            }
            QPushButton {
                background-color: #223344;
                color: #aaccff;
                border: none;
                border-radius: 6px;
                padding: 4px 6px;
            }
            QPushButton:hover {
                background-color: #334455;
            }
            QLabel {
                color: #aaccff;
            }
        """)

        # Layouts
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # --- Header Bar ---
        header = QHBoxLayout()
        logo = QLabel()
        pixmap = QPixmap("assets/logo-colour.svg").scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setPixmap(pixmap)
        header.addWidget(logo)

        header.addStretch()

        # New Chat (+)
        new_btn = QPushButton("+")
        new_btn.setToolTip("New Chat")
        new_btn.setFixedSize(30, 30)
        new_btn.clicked.connect(self.tray_ref.open_new_chat_window)
        header.addWidget(new_btn)

        # Settings (⚙)
        settings_btn = QPushButton("⚙")
        settings_btn.setToolTip("Settings")
        settings_btn.setFixedSize(30, 30)
        settings_btn.clicked.connect(self.tray_ref.open_settings_window)
        header.addWidget(settings_btn)

        # Close (✖)
        close_btn = QPushButton("✖")
        close_btn.setToolTip("Close Manager")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.hide)
        header.addWidget(close_btn)

        layout.addLayout(header)

        # --- Chat List ---
        self.chat_list = QListWidget()
        self.chat_list.itemClicked.connect(self.focus_chat)
        layout.addWidget(self.chat_list)

        self.refresh()

    def refresh(self):
        self.chat_list.clear()
        for i, chat in enumerate(self.tray_ref.chat_windows):
            title = f"Chat {i + 1} ({chat.config.get('selected_model', 'Unknown')})"
            self.chat_list.addItem(title)

    def focus_chat(self, item):
        index = self.chat_list.row(item)
        if 0 <= index < len(self.tray_ref.chat_windows):
            chat = self.tray_ref.chat_windows[index]
            chat.show()
            chat.raise_()
            chat.activateWindow()
            chat.setFocus()
