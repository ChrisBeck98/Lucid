# widgets/enter_send_textedit.py

from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtGui import QTextCharFormat, QTextCursor, QColor
from PyQt5.QtCore import Qt
from spellchecker import SpellChecker
import re

class EnterSendTextEdit(QTextEdit):
    def __init__(self, on_enter_callback=None, parent=None):
        super().__init__(parent)
        self.on_enter_callback = on_enter_callback
        self.spellchecker = SpellChecker()
        self.textChanged.connect(self.highlight_misspellings)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers():
            if self.on_enter_callback:
                self.on_enter_callback()
            return
        super().keyPressEvent(event)

    def highlight_misspellings(self):
        try:
            self.blockSignals(True)  # Prevent recursive textChanged
            cursor = self.textCursor()
            cursor.beginEditBlock()

            # Clear previous formatting
            fmt_clear = QTextCharFormat()
            fmt_clear.setUnderlineStyle(QTextCharFormat.NoUnderline)
            fmt_clear.setForeground(QColor("#aaccff"))
            cursor.select(QTextCursor.Document)
            cursor.setCharFormat(fmt_clear)

            text = self.toPlainText()
            words = re.findall(r"\b\w+\b", text)
            if not words:
                cursor.endEditBlock()
                return

            misspelled = self.spellchecker.unknown(words)
            for word in misspelled:
                self._underline_word(word)

            cursor.endEditBlock()
        except Exception as e:
            print("[Spellcheck Error]", e)
        finally:
            self.blockSignals(False)

    def _underline_word(self, word):
        doc = self.document()
        cursor = QTextCursor(doc)

        fmt = QTextCharFormat()
        fmt.setUnderlineColor(QColor("red"))
        fmt.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)

        while True:
            cursor = doc.find(word, cursor)
            if cursor.isNull():
                break
            cursor.mergeCharFormat(fmt)
