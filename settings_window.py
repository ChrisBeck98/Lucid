from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTabWidget, QHBoxLayout, QCheckBox, QFrame,
    QScrollArea, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from config.config_manager import load_config, save_config
import os
import sys
import asyncio
import threading
import subprocess
import json
import shutil
from edge_tts import Communicate
from playsound3 import playsound
import ctypes
import winreg

ENABLED_MODELS = []

class SettingsWindow(QWidget):
    def __init__(self, chat_window_ref, icon_path, config):
        super().__init__()
        self.chat_window_ref = chat_window_ref
        self.config = config

        self.setWindowTitle("Lucid Settings")
        self.setFixedSize(640, 480)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setObjectName("SettingsWindow")

        self.ollama_installed = shutil.which("ollama") is not None
        self.installed_ollama_models = self.get_installed_ollama_models() if self.ollama_installed else []
        self.ollama_model_dropdown = None
        self.openai_url_field = None

        self.setStyleSheet("""
            QFrame#OuterFrame {
                border: 1px solid #334455;
                border-radius: 12px;
            }
            QWidget#SettingsWindow {
                background-color: #000c18;
                color: #6688cc;
                border: 1px solid #334455;
                border-radius: 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12pt;
            }
            QLineEdit:disabled {
                background-color: #0a1a2a;
                color: #555;
                border: 1px solid #334455;
                border-radius: 6px;
                padding: 4px;
            }
            QComboBox:disabled {
                    color: #555;
                           }
            QLineEdit, QComboBox {
                background-color: #001626;
                color: #aaccff;
                border: 1px solid #334455;
                border-radius: 6px;
                padding: 4px;
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
            QLabel {
                color: #6688cc;
            }
            QCheckBox {
                color: #aaccff;
            }
            QTabWidget::pane {
                border: none;
            }
            QTabBar::tab {
                background: #001626;
                color: #aaccff;
                padding: 6px;
                border-radius: 6px;
            }
            QTabBar::tab:selected {
                background: #334455;
            }
            QScrollArea {
                background-color: #000c18;
                border: none;
            }
        """
        )

        outer_frame = QFrame(self)
        outer_frame.setObjectName("OuterFrame")
        outer_layout = QVBoxLayout(outer_frame)
        main_layout = outer_layout
        layout = QVBoxLayout(self)
        layout.addWidget(outer_frame)

        icon = QLabel()
        icon_pixmap = QPixmap(icon_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon.setPixmap(icon_pixmap)
        main_layout.addWidget(icon)

        self.tabs = QTabWidget()
        self.general_tab = QWidget()
        self.model_tab = QWidget()
        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.model_tab, "Models")
        main_layout.addWidget(self.tabs)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #334455; margin-top: 8px; margin-bottom: 6px;")
        main_layout.addWidget(divider)

        # Add bottom-right aligned Save/Apply/Cancel buttons to entire window
        button_container = QHBoxLayout()
        button_container.addStretch(2)  # Push buttons to the right

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: (self.save_settings(), self.hide()))

        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.save_settings)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.hide)

        button_container.addWidget(save_button)
        button_container.addWidget(apply_button)
        button_container.addWidget(cancel_button)
        main_layout.addLayout(button_container)

        # General Tab
        general_layout = QVBoxLayout()

        general_layout.addWidget(QLabel("Text Speed"))
        self.speed_dropdown = QComboBox()
        self.speed_dropdown.addItems(["Slow (20)", "Medium (12)", "Fast (6)", "Instant (0)"])
        speed_to_index = {20: 0, 12: 1, 6: 2, 0: 3}
        index = speed_to_index.get(self.config.get("text_speed", 20), 0)
        self.speed_dropdown.setCurrentIndex(index)
        general_layout.addWidget(self.speed_dropdown)

        general_layout.addWidget(QLabel("Default Model"))
        self.model_dropdown = QComboBox()
        self.available_models = [
            "gpt-3.5-turbo", "gpt-4o", "gemini-pro", "deepseek-chat",
            "mixtral", "llama3", "phind", "isou", "pollinations"
        ]
        enabled_models = self.config.get("enabled_models", {})
        if enabled_models.get("ollama", False) and self.ollama_installed:
            self.available_models.append("llama3-local")

        for model in self.available_models:
            provider = self.get_provider_from_model(model)
            if enabled_models.get(provider, False):
                self.model_dropdown.addItem(model)

        current_model = self.config.get("selected_model", "phind")
        idx = self.model_dropdown.findText(current_model)
        if idx != -1:
            self.model_dropdown.setCurrentIndex(idx)
        general_layout.addWidget(self.model_dropdown)

        general_layout.addWidget(QLabel("TTS Voice"))
        self.voice_dropdown = QComboBox()
        voices = [
            "en-GB-RyanNeural", "en-US-JennyNeural", "en-US-GuyNeural",
            "en-AU-NatashaNeural", "en-IN-PrabhatNeural"
        ]
        self.voice_dropdown.addItems(voices)
        self.voice_dropdown.setCurrentText(self.config.get("tts_voice", "en-GB-RyanNeural"))

        voice_row = QHBoxLayout()
        voice_row.addWidget(self.voice_dropdown)

        preview_button = QPushButton("Preview Voice")
        preview_button.clicked.connect(lambda _, v=self.voice_dropdown: self.preview_voice(v.currentText()))
        voice_row.addWidget(preview_button)
        general_layout.addLayout(voice_row)

        self.startup_checkbox = QCheckBox("Run on Windows Startup")
        self.startup_checkbox.setChecked(self.is_startup_enabled())
        general_layout.addWidget(self._divider())

        # Shortcut keys
        general_layout.addWidget(QLabel("Shortcut: Open Chat Window"))
        from PyQt5.QtGui import QKeySequence
        from PyQt5.QtWidgets import QKeySequenceEdit

        self.shortcut_open_chat = QKeySequenceEdit()
        self.shortcut_open_chat.setKeySequence(QKeySequence(self.config.get("shortcut_open_chat", "Ctrl+L")))
        general_layout.addWidget(self.shortcut_open_chat)

        general_layout.addWidget(QLabel("Shortcut: Open Chat + Voice Recognition"))
        self.shortcut_open_chat_voice = QKeySequenceEdit()
        self.shortcut_open_chat_voice.setKeySequence(QKeySequence(self.config.get("shortcut_open_chat_voice", "Ctrl+Shift+L")))
        general_layout.addWidget(self.shortcut_open_chat_voice)
        general_layout.addWidget(self.startup_checkbox)

        self.general_tab.setLayout(general_layout)

        # Models Tab
        self.fields = {}
        self.checkboxes = {}

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: #000c18;")
        model_layout = QVBoxLayout(scroll_content)

        # Section: Text Generation - Free Models
        free_header = QLabel("Text Generation: Free Models")
        free_header.setStyleSheet("font-weight: bold; color: #aaccff; margin-top: 10px;")
        model_layout.addWidget(free_header)

        for provider in ["Phind", "Pollinations"]:
            provider_key = provider.lower()
            row_layout = QHBoxLayout()
            checkbox = QCheckBox()
            checked = bool(self.config.get("enabled_models", {}).get(provider_key, True))
            checkbox.setChecked(checked)
            self.checkboxes[provider_key] = checkbox

            label = QLabel(f"{provider}")
            label.setFixedWidth(150)
            label.setStyleSheet("color: #6688cc;" if checked else "color: #444;")
            row_layout.addWidget(label)
            row_layout.addStretch()
            row_layout.addWidget(checkbox)
            model_layout.addLayout(row_layout)

        model_layout.addWidget(self._divider())

        # Section: Text Generation - Paid Models
        paid_header = QLabel("Text Generation: Paid Models")
        paid_header.setStyleSheet("font-weight: bold; color: #aaccff; margin-top: 10px;")
        model_layout.addWidget(paid_header)

        for provider in ["OpenAI", "Gemini", "Groq", "DeepSeek"]:
            provider_key = provider.lower()
            row_layout = QHBoxLayout()
            checkbox = QCheckBox()
            checked = bool(self.config.get("enabled_models", {}).get(provider_key, False))
            checkbox.setChecked(checked)
            self.checkboxes[provider_key] = checkbox

            label = QLabel(f"{provider}")
            label.setFixedWidth(150)
            label.setStyleSheet("color: #6688cc;" if checked else "color: #444;")
            row_layout.addWidget(label)
            row_layout.addStretch()
            row_layout.addWidget(checkbox)
            model_layout.addLayout(row_layout)

            input_field = QLineEdit()
            input_field.setPlaceholderText(f"Enter {provider} API key")
            input_field.setEchoMode(QLineEdit.Password)
            input_field.setText(self.config["api_keys"].get(provider_key, ""))
            input_field.setEnabled(checkbox.isChecked())
            self.fields[provider_key] = input_field
            model_layout.addWidget(input_field)
            checkbox.stateChanged.connect(lambda state, pk=provider_key, lbl=label: self.toggle_input(pk, state, lbl))

            if provider_key == "openai":
                self.openai_url_field = QLineEdit()
                self.openai_url_field.setPlaceholderText("Enter OpenAI API base URL")
                self.openai_url_field.setText(self.config.get("openai_api_base", "https://api.openai.com/v1"))
                self.openai_url_field.setEnabled(checkbox.isChecked())
                model_layout.addWidget(self.openai_url_field)

        model_layout.addWidget(self._divider())

        # Section: Image Generation
        image_header = QLabel("Image Generation")
        image_header.setStyleSheet("font-weight: bold; color: #aaccff; margin-top: 10px;")
        model_layout.addWidget(image_header)

        provider = "Pollinations"
        provider_key = provider.lower()
        row_layout = QHBoxLayout()
        checkbox = QCheckBox()
        checked = bool(self.config.get("enabled_models", {}).get(provider_key, True))
        checkbox.setChecked(checked)
        self.checkboxes[provider_key] = checkbox

        label = QLabel(f"{provider}")
        label.setFixedWidth(150)
        label.setStyleSheet("color: #6688cc;" if checked else "color: #444;")
        row_layout.addWidget(label)
        row_layout.addStretch()
        row_layout.addWidget(checkbox)
        model_layout.addLayout(row_layout)

        scroll_area.setWidget(scroll_content)
        tab_layout = QVBoxLayout()
        tab_layout.addWidget(scroll_area)
        tab_layout.addStretch()

        button_row = QHBoxLayout()

        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: (self.save_settings(), self.hide()))

        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.save_settings)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.hide)

        button_row.addWidget(save_button)
        button_row.addWidget(apply_button)
        button_row.addWidget(cancel_button)

        # Removed duplicate buttons to centralize control at bottom of window
        # tab_layout.addLayout(button_row)

        self.model_tab.setLayout(tab_layout)

        # Add this helper method to the class:
        def _divider(self):
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setStyleSheet("background-color: #334455; margin-top: 10px; margin-bottom: 10px;")
            return line


    def get_provider_from_model(self, model):
        mapping = {
            "gpt-3.5-turbo": "openai", "gpt-4o": "openai",
            "gemini-pro": "gemini", "deepseek-chat": "deepseek",
            "mixtral": "groq", "llama3": "groq",
            "phind": "phind", "isou": "isou", "pollinations": "pollinations",
            "llama3-local": "ollama"
        }
        return mapping.get(model, "phind")

    def get_installed_ollama_models(self):
        try:
            result = subprocess.run(["ollama", "list", "--json"], capture_output=True, text=True, timeout=5)
            models = json.loads(result.stdout)
            return [m.get("name") for m in models if "name" in m]
        except Exception as e:
            print("[Ollama Model Detection Error]:", e)
            return []
            
    # Add this method inside your SettingsWindow class
    def _divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #334455; margin-top: 10px; margin-bottom: 10px;")
        return line

    def toggle_input(self, provider_key, state, label=None):
        if provider_key in self.fields and self.fields[provider_key]:
            enabled = state == Qt.Checked
            self.fields[provider_key].setEnabled(enabled)
        if provider_key == "openai" and self.openai_url_field:
            self.openai_url_field.setEnabled(enabled)
        if label:
            label.setStyleSheet("color: #6688cc;" if state == Qt.Checked else "color: #444;")

    def save_settings(self):
        global ENABLED_MODELS
        ENABLED_MODELS = []

        speed_map = {
            "Slow (20)": 20, "Medium (12)": 12, "Fast (6)": 6, "Instant (0)": 0
        }

        if "enabled_models" not in self.config:
            self.config["enabled_models"] = {}

        for provider, field in self.fields.items():
            enabled = self.checkboxes[provider].isChecked()
            self.config["enabled_models"][provider] = enabled
            if enabled:
                self.config["api_keys"][provider] = field.text() if field else "enabled"
                ENABLED_MODELS.append(provider)
            else:
                self.config["api_keys"][provider] = ""

        if self.openai_url_field:
            self.config["openai_api_base"] = self.openai_url_field.text()
        self.config["shortcut_open_chat"] = self.shortcut_open_chat.keySequence().toString()
        self.config["shortcut_open_chat_voice"] = self.shortcut_open_chat_voice.keySequence().toString()

        if self.ollama_model_dropdown:
            self.config["selected_ollama_model"] = self.ollama_model_dropdown.currentText()

        self.config["run_on_startup"] = self.startup_checkbox.isChecked()
        self.config["text_speed"] = speed_map.get(self.speed_dropdown.currentText(), 20)
        self.config["selected_model"] = self.model_dropdown.currentText()
        self.config["tts_voice"] = self.voice_dropdown.currentText()
        self.config["openai_api_base"] = self.openai_url_field.text()
        self.set_startup(self.startup_checkbox.isChecked())

        save_config(self.config)
        self.chat_window_ref.apply_config(self.config)
        self.hide()

        if hasattr(self.chat_window_ref.tray_ref, "hotkey_manager"):
            self.chat_window_ref.tray_ref.hotkey_manager.config = self.config
            self.chat_window_ref.tray_ref.hotkey_manager.register()


    def preview_voice(self, voice_name):
        async def run():
            try:
                communicate = Communicate("You are using Lucid AI; how can I assist you.", voice=voice_name)
                await communicate.save("preview.mp3")
                playsound("preview.mp3")
            except Exception as e:
                print("[TTS Preview Error]:", e)
        threading.Thread(target=lambda: asyncio.run(run())).start()

    def set_startup(self, enabled):
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_ALL_ACCESS) as reg_key:
                if enabled:
                    exe_path = os.path.realpath(sys.argv[0])
                    winreg.SetValueEx(reg_key, "Lucid", 0, winreg.REG_SZ, exe_path)
                else:
                    try:
                        winreg.DeleteValue(reg_key, "Lucid")
                    except FileNotFoundError:
                        pass
        except Exception as e:
            print("[Startup Setting Error]:", e)

    def is_startup_enabled(self):
        key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key, 0, winreg.KEY_READ) as reg_key:
                value, _ = winreg.QueryValueEx(reg_key, "Lucid")
                return bool(value)
        except FileNotFoundError:
            return False
        except Exception as e:
            print("[Startup Check Error]:", e)
            return False
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and hasattr(self, "drag_pos"):
            self.move(event.globalPos() - self.drag_pos)
            event.accept()