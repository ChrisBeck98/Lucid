from PyQt5.QtWidgets import QTextEdit, QMenu, QAction
from PyQt5.QtGui import QTextCharFormat, QTextCursor, QColor
from PyQt5.QtCore import Qt, QPoint
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
            self.blockSignals(True)
            cursor = self.textCursor()
            cursor.beginEditBlock()

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

            self.misspelled_words = self.spellchecker.unknown(words)
            for word in self.misspelled_words:
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

    def contextMenuEvent(self, event):
        cursor = self.cursorForPosition(event.pos())
        cursor.select(QTextCursor.WordUnderCursor)
        word = cursor.selectedText().strip()

        menu = QMenu(self)

        if word.isalpha() and word in getattr(self, 'misspelled_words', []):
            suggestions = self.spellchecker.candidates(word)
            top_suggestions = list(suggestions)[:3] if suggestions else []

            if top_suggestions:
                for suggestion in top_suggestions:
                    action = QAction(suggestion, self)
                    action.triggered.connect(lambda _, s=suggestion, c=QTextCursor(cursor): self.replace_word(c, s))
                    menu.addAction(action)
            else:
                no_suggestion_action = QAction("(No suggestions)", self)
                no_suggestion_action.setEnabled(False)
                menu.addAction(no_suggestion_action)

            menu.addSeparator()

        # Always add basic edit actions
        cut_action = QAction("Cut", self)
        cut_action.triggered.connect(self.cut)
        menu.addAction(cut_action)

        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy)
        menu.addAction(copy_action)

        paste_action = QAction("Paste", self)
        paste_action.triggered.connect(self.paste)
        menu.addAction(paste_action)

        menu.exec_(self.mapToGlobal(event.pos()))



    def replace_word(self, cursor, replacement):
        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(replacement)
        cursor.endEditBlock()
        self.highlight_misspellings()
