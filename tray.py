from PyQt5.QtWidgets import QSystemTrayIcon, QWidget, QVBoxLayout, QPushButton, QApplication
from PyQt5.QtCore import Qt, QPropertyAnimation, QPoint, QEventLoop
from PyQt5.QtGui import QIcon, QCursor, QMouseEvent
from chat_window import ChatWindow
from settings_window import SettingsWindow
from config.config_manager import load_config


class TrayApp(QSystemTrayIcon):
    def __init__(self, icon_path, parent=None):
        super().__init__(QIcon(icon_path), parent)

        chat_open = False
        self.config = load_config()

        self.chat_windows = []
        self.icon_path = icon_path  # Save for reuse
        self.open_new_chat_window()

        self.settings_window = SettingsWindow(self.chat_windows, icon_path, self.config)

        self.setToolTip("Lucid")
        self.menu_popup = None




        self.activated.connect(self.tray_click)

    def tray_click(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.toggle_chat_window()    
        elif reason == QSystemTrayIcon.Context:
            self.show_popup_menu()


    def toggle_chat_window(self):
        if not self.chat_windows:
            return

        chat_window = self.chat_windows[0]
        if chat_window.isVisible():
            self.animate_hide(chat_window)
        else:
            self.position_chat_window(chat_window)
            self.animate_show(chat_window)


    def position_chat_window(self, chat_window):
        screen = QApplication.primaryScreen().availableGeometry()
        x = screen.width() - chat_window.width() - 10
        y = screen.height() - chat_window.height()
        chat_window.move(x, y)


    def animate_show(self, chat_window):
        screen = QApplication.primaryScreen().availableGeometry()
        end_pos = chat_window.pos()
        start_pos = QPoint(end_pos.x(), screen.height())
        chat_window.move(start_pos)
        chat_window.show()
        chat_window.activateWindow()
        chat_window.setFocus()

        animation = QPropertyAnimation(chat_window, b"pos")
        animation.setDuration(300)
        animation.setStartValue(start_pos)
        animation.setEndValue(end_pos)
        animation.start()
        chat_window._animation = animation  # Prevent GC


    def animate_hide(self, chat_window):
        screen = QApplication.primaryScreen().availableGeometry()
        start_pos = chat_window.pos()
        end_pos = QPoint(start_pos.x(), screen.height())

        animation = QPropertyAnimation(chat_window, b"pos")
        animation.setDuration(300)
        animation.setStartValue(start_pos)
        animation.setEndValue(end_pos)

        def on_finished():
            chat_window.hide()

        animation.finished.connect(on_finished)
        animation.start()
        chat_window._animation = animation  # Prevent GC


    def show_popup_menu(self):
        if self.menu_popup is None:
            self.menu_popup = QWidget()
            self.menu_popup.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
            self.menu_popup.setFixedSize(120, 160)
            self.menu_popup.setStyleSheet("""
                QWidget {
                    background-color: #000c18;
                    border-radius: 8px;
                    border: 1px solid #334455;
                }
                QPushButton {
                    background-color: #223344;
                    color: #aaccff;
                    border: none;
                    border-radius: 6px;
                    padding: 6px;
                }
                QPushButton:hover {
                    background-color: #334455;
                }
            """)
            layout = QVBoxLayout()

            new_chat_button = QPushButton("New Chat")
            new_chat_button.clicked.connect(self.open_new_chat_window)
            layout.addWidget(new_chat_button)

            settings_button = QPushButton("Settings")
            settings_button.clicked.connect(self.open_settings_window)
            layout.addWidget(settings_button)

            quit_button = QPushButton("Quit")
            quit_button.clicked.connect(QApplication.quit)
            layout.addWidget(quit_button)

            self.menu_popup.setLayout(layout)

        cursor_pos = QCursor.pos()
        self.menu_popup.move(cursor_pos.x(), cursor_pos.y() - self.menu_popup.height())
        self.menu_popup.show()

    def open_settings_window(self):
        self.settings_window.show()
        self.settings_window.activateWindow()
        self.settings_window.setFocus()


    def open_new_chat_window(self):
        chat_window = ChatWindow(self.icon_path, self.config, self)
        chat_window.show()
        chat_window.activateWindow()
        chat_window.setFocus()
        self.chat_windows.append(chat_window)

        # Remove closed windows from the list
        chat_window.destroyed.connect(lambda: self.chat_windows.remove(chat_window))
