import sys
import threading
import keyboard
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QObject, pyqtSignal, QTimer
from tray import TrayApp

class HotkeyManager(QObject):
    open_chat_signal = pyqtSignal()
    open_chat_voice_signal = pyqtSignal()

    def __init__(self, config, tray_ref):
        super().__init__()
        self.config = config
        self.tray_ref = tray_ref
        self.hotkeys = []

        self.open_chat_signal.connect(self.tray_ref.toggle_chat_window)

        def open_with_voice():
            if not self.tray_ref.chat_windows:
                return
            chat_window = self.tray_ref.chat_windows[0]
            if not chat_window.isVisible():
                self.tray_ref.toggle_chat_window()
                QTimer.singleShot(300, chat_window.start_voice_recognition)
            else:
                chat_window.start_voice_recognition()

        self.open_chat_voice_signal.connect(open_with_voice)


    def register(self):
        self.clear()
        try:
            open_shortcut = self.config.get("shortcut_open_chat", "ctrl+l").lower()
            voice_shortcut = self.config.get("shortcut_open_chat_voice", "ctrl+shift+l").lower()

            self.hotkeys.append(keyboard.add_hotkey(open_shortcut, lambda: self.open_chat_signal.emit()))
            self.hotkeys.append(keyboard.add_hotkey(voice_shortcut, lambda: self.open_chat_voice_signal.emit()))
        except Exception as e:
            print("[Hotkey Registration Error]:", e)

    def clear(self):
        for hotkey in self.hotkeys:
            try:
                keyboard.remove_hotkey(hotkey)
            except:
                pass
        self.hotkeys = []

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    tray_icon_path = "assets/logo-colour.svg"
    tray = TrayApp(tray_icon_path)
    tray.show()

    # Register hotkeys safely
    tray.hotkey_manager = HotkeyManager(tray.config, tray)
    tray.hotkey_manager.register()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
