from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent


class EnterSendTextEdit(QTextEdit):
    def __init__(self, send_callback):
        super().__init__()
        self.send_callback = send_callback

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() == Qt.ShiftModifier:
                super().keyPressEvent(event)  # Allow new line with Shift+Enter
            else:
                self.send_callback()  # Send on Enter
        else:
            super().keyPressEvent(event)
