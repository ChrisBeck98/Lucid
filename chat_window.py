import subprocess
import sys
import shlex
import asyncio
import threading
import os
import queue
import json
from vosk import Model, KaldiRecognizer
import sounddevice as sd
from config.config_manager import load_config, save_config

if sys.platform.startswith("win") and isinstance(asyncio.get_event_loop(), asyncio.ProactorEventLoop):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel,
    QScrollArea, QToolButton, QApplication, QFrame, QComboBox
)
from PyQt5.QtCore import Qt, QTimerEvent, QTimer, QPoint
from PyQt5.QtGui import QPixmap, QIcon, QClipboard
from edge_tts import Communicate
from playsound3 import playsound
from widgets.enter_send_textedit import EnterSendTextEdit
import uuid


class ChatWindow(QWidget):
    def __init__(self, icon_path, config, tray_ref=None):
        super().__init__()
        self.chat_id = str(uuid.uuid4())
        self.custom_name = f"Chat {len(tray_ref.chat_windows) + 1}" if tray_ref else "Chat"
        self.message_history = []

        self.setWindowTitle("Lucid")
        self.tray_ref = tray_ref
        self.docked = True
        self.setFixedSize(420, 520)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)  # Enables transparency
        self.setFocusPolicy(Qt.StrongFocus)
        self.model = Model(model_path="config/models/vosk-model-small-en-us-0.15")
        self.setObjectName("ChatWindow")
        self.setProperty("docked", True)
        self.drag_pos = None
        self.is_maximized = False
        self.config = load_config()
        self.model_name = self.config.get("selected_model", "phind")
        self.typing_speed = self.config.get("text_speed", 20)
        self.tts_voice = self.config.get("tts_voice", "en-GB-RyanNeural")

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)

        self.outer_container = QFrame(self)
        self.outer_container.setObjectName("OuterFrame")
        self.outer_container.setAttribute(Qt.WA_StyledBackground, True)
        main_layout.addWidget(self.outer_container)

        outer_layout = QVBoxLayout(self.outer_container)
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(10)

        # --- Header Buttons ---
        collapse_row = QHBoxLayout()
        icon = QLabel()
        icon_pixmap = QPixmap(icon_path).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon.setPixmap(icon_pixmap)
        collapse_row.addWidget(icon)
        collapse_row.addStretch()

        # Model selector dropdown
        self.model_dropdown = QComboBox()
        self.model_dropdown.setFixedHeight(30)
        self.model_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #001626;
                color: #aaccff;
                border-radius: 6px;
                padding: 4px;
            }
        """)

        # Populate from enabled models
        available_models = [
            "gpt-3.5-turbo", "gpt-4o", "gemini-pro", "deepseek-chat",
            "mixtral", "llama3", "phind", "isou", "pollinations"
        ]
        enabled_models = self.config.get("enabled_models", {})
        for model in available_models:
            provider = self.get_provider_from_model(model)
            if enabled_models.get(provider, False):
                self.model_dropdown.addItem(model)

        # Set current model
        current_model = self.config.get("selected_model", "phind")
        index = self.model_dropdown.findText(current_model)
        if index != -1:
            self.model_dropdown.setCurrentIndex(index)

        # Update config on change
        self.model_dropdown.currentIndexChanged.connect(self.update_model_selection)
        collapse_row.addWidget(self.model_dropdown)


        self.voice_recognition_button = QPushButton()
        mic_icon_path = os.path.join("assets", "microphone_icon.png")
        self.voice_recognition_button.setIcon(QIcon(mic_icon_path))
        self.voice_recognition_button.setToolTip("Voice Recognition")
        self.voice_recognition_button.setFixedSize(30, 30)
        self.voice_recognition_button.clicked.connect(self.start_voice_recognition)
        collapse_row.addWidget(self.voice_recognition_button)

        self.dock_button = QPushButton("🗗")
        self.dock_button.setFixedSize(30, 30)
        self.dock_button.setToolTip("Undock Chat")
        self.dock_button.clicked.connect(self.toggle_popout)
        collapse_row.addWidget(self.dock_button)

        self.collapse_button = QPushButton("▼")
        self.collapse_button.setToolTip("Minimize to Tray")
        self.collapse_button.setFixedSize(30, 30)
        self.collapse_button.clicked.connect(lambda: self.tray_ref.animate_hide(self))
        collapse_row.addWidget(self.collapse_button)

        outer_layout.addLayout(collapse_row)

        # --- Chat Area ---
        self.chat_area = QScrollArea()
        self.chat_area.setWidgetResizable(True)
        self.chat_area.setStyleSheet("background-color: transparent; border: none;")
        self.chat_content = QVBoxLayout()
        self.chat_content.setAlignment(Qt.AlignTop)

        container = QWidget()
        container.setLayout(self.chat_content)
        self.chat_area.setWidget(container)
        outer_layout.addWidget(self.chat_area)

        # --- Input + Send ---
        self.input_box = EnterSendTextEdit(self.send_prompt)
        self.input_box.setPlaceholderText("Ask something...")
        self.input_box.setFixedHeight(80)
        outer_layout.addWidget(self.input_box)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_prompt)
        outer_layout.addWidget(self.send_button)

        self.typing_timer = None
        self.typing_label = None
        self.typing_text = ""
        self.typing_index = 0

        # --- Stylesheet ---
        self.setStyleSheet("""
            QWidget#ChatWindow {
                background-color: transparent;
            }

            QFrame#OuterFrame {
                background-color: #000c18;
                border-radius: 10px;
                border: 2px solid #334455;
            }

            QTextEdit {
                background-color: #001626;
                color: #aaccff;
                border: 1px solid #334455;
                border-radius: 6px;
                padding: 5px;
            }

            QPushButton {
                background-color: #223344;
                color: #6688cc;
                border: none;
                border-radius: 6px;
                padding: 6px;
            }

            QPushButton:hover {
                background-color: #334455;
            }

            QLabel {
                padding: 6px;
                border-radius: 6px;
                color: #6688cc;
            }
        """)

           # --- Popout / Restore ---


    def toggle_popout(self):
        if self.docked:
            self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setFixedSize(640, 480)
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.center().x() - self.width() // 2
            y = screen.center().y() - self.height() // 2
            self.move(x, y)
            self.docked = False
            self.setProperty("docked", False)
            self.dock_button.setToolTip("Dock to tray")
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
            self.setFixedSize(420, 520)
            self.tray_ref.position_chat_window(self)
            self.docked = True
            self.setProperty("docked", True)
            self.dock_button.setToolTip("Pop out window")

        self.style().unpolish(self)
        self.style().polish(self)

        if self.tray_ref is not None:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
            self.docked = False
            self.setProperty("docked", False)
        else:
            self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
            self.docked = True
            self.setProperty("docked", True)

        self.tray_ref.save_all_chats()
        self.show()  # Must call show() again after changing flags

    # --- Drag to Move ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drag_pos:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def apply_config(self, config):
        self.config = config
        self.typing_speed = config.get("text_speed", 20)
        self.tts_voice = config.get("tts_voice", "en-GB-RyanNeural")

    def get_provider_from_model(self, model):
        mapping = {
            "gpt-3.5-turbo": "openai", "gpt-4o": "openai",
            "gemini-pro": "gemini", "deepseek-chat": "deepseek",
            "mixtral": "groq", "llama3": "groq",
            "phind": "phind", "isou": "isou", "pollinations": "pollinations"
        }
        return mapping.get(model, "phind")
    
    def update_model_selection(self):
        selected_model = self.model_dropdown.currentText()
        self.config["selected_model"] = selected_model
        save_config(self.config)



    def add_message(self, sender, message, selectable=False):
        bubble_widget = QWidget()
        bubble_layout = QVBoxLayout(bubble_widget)
        bubble_layout.setContentsMargins(8, 6, 8, 6)
        bubble_layout.setSpacing(4)

        message_label = QLabel(f"<b>{sender}:</b> {message}")
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(Qt.TextSelectableByMouse if selectable else Qt.NoTextInteraction)

        message_color = "#001e33" if sender == "AI" else "#002b4d"
        message_label.setStyleSheet(f"""
            background-color: {message_color};
            color: #6688cc;
            border-radius: 6px;
            padding: 6px;
        """)

        bubble_layout.addWidget(message_label)

        # Store reference if typing effect is needed
        if sender == "AI":
            self.typing_label = message_label

            controls = QWidget()
            controls_layout = QHBoxLayout(controls)
            controls_layout.setContentsMargins(0, 0, 0, 0)
            controls_layout.setSpacing(6)
            controls_layout.addStretch()

            # Speaker icon
            speaker_button = QPushButton()
            speaker_button.setCursor(Qt.PointingHandCursor)
            speaker_button.setToolTip("Read aloud")
            icon_path = os.path.join("assets", "speaker_icon.png")
            if os.path.exists(icon_path):
                speaker_button.setIcon(QIcon(icon_path))
            else:
                speaker_button.setText("🔊")

            speaker_button.setFixedSize(24, 24)
            speaker_button.setStyleSheet("QPushButton { background-color: transparent; border: none; }"
                                         "QPushButton:hover { background-color: #334455; border-radius: 4px; }")
            speaker_button.clicked.connect(lambda: self.speak_text(message))
            controls_layout.addWidget(speaker_button)

            # Copy button
            copy_button = QPushButton()
            copy_button.setToolTip("Copy to clipboard")
            copy_icon_path = os.path.join("assets", "copy_icon.png")
            if os.path.exists(copy_icon_path):
                copy_button.setIcon(QIcon(copy_icon_path))
            else:
                copy_button.setText("📋")  # fallback emoji

            copy_button.setFixedSize(24, 24)
            copy_button.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #334455;
                    border-radius: 4px;
                }
            """)
            copy_button.setCursor(Qt.PointingHandCursor)
            copy_button.clicked.connect(lambda: QApplication.clipboard().setText(message))
            controls_layout.addWidget(copy_button)

            bubble_layout.addWidget(controls)

        self.chat_content.addWidget(bubble_widget)
        if sender != "You":
            self.message_history.append((sender, message))



    def send_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if not prompt:
            return
        self.add_message("You", prompt, selectable=True)
        self.input_box.clear()
        self.get_ai_response(prompt)
        if self.tray_ref:
            self.tray_ref.save_all_chats()

    def get_ai_response(self, prompt):
        try:
            selected_model = self.config.get("selected_model", "phind")
            enabled_models = self.config.get("enabled_models", {})
            model_provider_map = {
                "gpt-3.5-turbo": "openai",
                "gpt-4o": "openai",
                "gemini-pro": "gemini",
                "deepseek-chat": "deepseek",
                "mixtral": "groq",
                "llama3": "groq",
                "phind": "phind",
                "isou": "isou",
                "pollinations": "pollinations"
            }
            provider = model_provider_map.get(selected_model, "phind")
            api_key = self.config.get("api_keys", {}).get(provider, "")


            cmd = f"tgpt -q --provider {provider}"

            if api_key and api_key != "enabled":
                cmd += f" --key {api_key} --model {selected_model}"
                if provider == "openai":
                    openai_url = self.config.get("openai_api_base", "https://api.openai.com/v1")
                    cmd += f" --url {openai_url}"

            # Append the original user message (preserve line breaks)
            self.message_history.append(("You", prompt))

            # Sanitize for tgpt prompt
            sanitized_history = []
            for sender, msg in self.message_history:
                cleaned = msg.replace("\n", " | ").replace("\r", " ").strip()
                sanitized_history.append(f"{sender}: {cleaned}")

            # Use double-pipe to separate message blocks
            full_prompt = " || ".join(sanitized_history)

            cmd += f' "{full_prompt.strip()}"'
            print("[DEBUG] Running command:", cmd)


            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            response = result.stdout.strip() if result.returncode == 0 else f"[Error]: {result.stderr}"
        except Exception as e:
            response = f"[Exception]: {e}"

        self.typing_text = response
        self.typing_index = 0


        self.add_message("AI", response, selectable=True)

        if self.typing_speed == 0:
            formatted_text = self.typing_text.replace('\n', '<br>')
            self.typing_label.setText(f"<b>AI:</b> {formatted_text}")
        else:
            if self.typing_timer:
                self.killTimer(self.typing_timer)
            self.typing_timer = self.startTimer(self.typing_speed)

    def timerEvent(self, event: QTimerEvent):
        if self.typing_index < len(self.typing_text):
            safe_text = self.typing_text[:self.typing_index + 1].replace("\n", "<br>")
            self.typing_label.setText(f"<b>AI:</b> {safe_text}")
            self.typing_index += 1
        else:
            self.killTimer(self.typing_timer)
            self.typing_timer = None

    def speak_text(self, text: str):
        async def run():
            
            if os.path.exists("response.mp3"):
                os.remove("response.mp3")
            communicate = Communicate(text, voice=self.tts_voice)
            await communicate.save("response.mp3")
            playsound("response.mp3")

        threading.Thread(target=lambda: asyncio.run(run())).start()


    def start_voice_recognition(self):
        async def startSound():
            playsound("assets/Listening-start.mp3")
        threading.Thread(target=lambda: asyncio.run(startSound())).start()


        print("[Voice] Listening for speech...")
        q = queue.Queue()

        def callback(indata, frames, time, status):
            if status:
                print("[Audio Status]:", status)
            q.put(bytes(indata))

        try:
            rec = KaldiRecognizer(self.model, 16000)
            with sd.RawInputStream(samplerate=16000, blocksize=8000, dtype='int16',
                                channels=1, callback=callback):
                result_text = ""
                import time
                silence_threshold = 2  # 500ms
                last_speech_time = time.time()

                # Create and add an updating message bubble
                temp_bubble = QLabel("<b>You:</b> <i>listening...</i>")
                temp_bubble.setWordWrap(True)
                temp_bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
                temp_bubble.setStyleSheet("background-color: #002b4d; color: #6688cc; border-radius: 6px; padding: 6px;")
                self.chat_content.addWidget(temp_bubble)
                QApplication.processEvents()

                while True:
                    data = q.get()
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        if result.get("text"):
                            result_text += result["text"] + " "
                            temp_bubble.setText(f"<b>You:</b> {result_text.strip()}")
                            last_speech_time = time.time()
                    else:
                        partial = json.loads(rec.PartialResult()).get("partial", "")
                        if partial.strip():
                            temp_bubble.setText(f"<b>You:</b> {result_text.strip()} {partial}")
                            last_speech_time = time.time()

                    QApplication.processEvents()
                    if time.time() - last_speech_time > silence_threshold:
                        break

                final_result = json.loads(rec.FinalResult())
                if final_result.get("text"):
                    result_text += final_result["text"]

                prompt = result_text.strip()
                if prompt:
                    print("[Voice] Recognized:", prompt)
                    temp_bubble.setText(f"<b>You:</b> {prompt}")
                    self.get_ai_response(prompt)
                else:
                    print("[Voice] No prompt recognized.")
                    temp_bubble.deleteLater()

                async def endSound():
                    playsound("assets/Listening-end.mp3")
                threading.Thread(target=lambda: asyncio.run(endSound())).start()

        except Exception as e:
            print(f"[Voice Error]: {e}")

    def to_dict(self):
        return {
            "id": self.chat_id,
            "name": getattr(self, "custom_name", "Chat"),
            "model": self.model_name,
            "history": self.message_history
        }
    