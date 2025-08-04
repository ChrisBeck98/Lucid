from PyQt5.QtWidgets import (
    QWidget, QListWidget, QVBoxLayout, QLabel, QHBoxLayout,
    QPushButton, QListWidgetItem, QInputDialog, QMenu, QAction
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
        icon = QLabel()
        icon_pixmap = QPixmap("assets/logo-colour.svg").scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon.setPixmap(icon_pixmap)
        header.addWidget(icon)

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
        self.chat_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chat_list.customContextMenuRequested.connect(self.show_context_menu)
        layout.addWidget(self.chat_list)


        self.refresh()

    def refresh(self):
        self.chat_list.clear()
        for i, chat in enumerate(self.tray_ref.chat_windows):
            title = getattr(chat, "custom_name", f"Chat {i + 1}")
            model = chat.config.get("selected_model", "Unknown")
            title += f" ({model})"


            preview = self.get_last_user_message(chat)

            widget = QWidget()
            vbox = QVBoxLayout(widget)
            vbox.setContentsMargins(10, 10, 10, 10)

            title_label = QLabel(title)
            title_label.setStyleSheet("font-weight: bold;")
            vbox.addWidget(title_label)

            preview_label = QLabel(preview)
            preview_label.setWordWrap(True)
            preview_label.setStyleSheet("color: #6688cc; font-size: 10pt;")
            vbox.addWidget(preview_label)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint())
            self.chat_list.addItem(item)
            self.chat_list.setItemWidget(item, widget)


    def focus_chat(self, item):
        index = self.chat_list.row(item)
        if 0 <= index < len(self.tray_ref.chat_windows):
            chat = self.tray_ref.chat_windows[index]

            if not chat.isVisible():
                # Position chat to the right of the manager
                if self.isVisible():
                    mgr_geom = self.geometry()
                    x = mgr_geom.x() + mgr_geom.width() + 10
                    y = mgr_geom.y()
                    chat.move(x, y)

                chat.show()

            chat.raise_()
            chat.activateWindow()
            chat.setFocus()


    def get_last_user_message(self, chat):
        user_messages = [msg for sender, msg in getattr(chat, "message_history", []) if sender == "You"]
        if not user_messages:
            return "(No messages yet)"
        
        last_msg = user_messages[-1].strip().replace('\n', ' ')
        lines = last_msg.split('. ')
        preview = ". ".join(lines[:2])
        return preview[:100] + ("…" if len(preview) > 100 else "")

    def show_context_menu(self, position):
        item = self.chat_list.itemAt(position)
        if not item:
            return

        index = self.chat_list.row(item)
        if not (0 <= index < len(self.tray_ref.chat_windows)):
            return

        chat = self.tray_ref.chat_windows[index]

        menu = QMenu()

        open_action = QAction("Open Chat", self)
        open_action.triggered.connect(lambda: self.focus_chat(item))
        menu.addAction(open_action)

        rename_action = QAction("Rename Chat", self)
        rename_action.triggered.connect(lambda: self.rename_chat(index))
        menu.addAction(rename_action)

        delete_action = QAction("Delete Chat", self)
        delete_action.triggered.connect(lambda: self.delete_chat(index))
        menu.addAction(delete_action)

        menu.exec_(self.chat_list.viewport().mapToGlobal(position))

    def rename_chat(self, index):
        chat = self.tray_ref.chat_windows[index]
        current_name = getattr(chat, "custom_name", f"Chat {index + 1}")
        new_name, ok = QInputDialog.getText(self, "Rename Chat", "Enter a new name:", text=current_name)
        if ok and new_name.strip():
            chat.custom_name = new_name.strip()
            self.refresh()

    def delete_chat(self, index):
        chat = self.tray_ref.chat_windows[index]
        chat.hide()
        chat.deleteLater()  # schedules it for deletion
        del self.tray_ref.chat_windows[index]  # remove it manually
        self.refresh()  # update the chat list

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and hasattr(self, "drag_pos"):
            self.move(event.globalPos() - self.drag_pos)
            event.accept()




