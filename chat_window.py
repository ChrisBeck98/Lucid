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

if sys.platform.startswith("win") and isinstance(asyncio.get_event_loop(), asyncio.ProactorEventLoop):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel,
    QScrollArea, QToolButton, QApplication, QFrame
)
from PyQt5.QtCore import Qt, QTimerEvent, QTimer
from PyQt5.QtGui import QPixmap, QIcon, QClipboard
from edge_tts import Communicate
from playsound3 import playsound
from widgets.enter_send_textedit import EnterSendTextEdit
from config.config_manager import load_config


class ChatWindow(QWidget):
    def __init__(self, icon_path, config, tray_ref = None):
        super().__init__()
        self.setWindowTitle("Lucid")
        self.tray_ref = tray_ref
        self.setFixedSize(420, 520)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setFocusPolicy(Qt.StrongFocus)
        self.model = Model(model_path="config/models/vosk-model-small-en-us-0.15")  # Use correct path
        self.setObjectName("ChatWindow")
        outer_frame = QFrame(self)
        outer_frame.setObjectName("OuterFrame")
        outer_layout = QVBoxLayout(outer_frame)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(outer_frame)
        layout = outer_layout  # Use this for the rest of the content


        self.config = load_config()
        self.typing_speed = self.config.get("text_speed", 20)
        self.tts_voice = self.config.get("tts_voice", "en-GB-RyanNeural")

        self.setStyleSheet("""
            QFrame#OuterFrame {
                border: 1px solid #334455;
                border-radius: 12px;
            }
            QWidget#ChatWindow {
                background-color: #000c18;
                color: #6688cc;
                border-radius: 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12pt;
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

        collapse_row = QHBoxLayout()
        self.collapse_button = QPushButton("\u25BC")
        self.collapse_button.setFixedWidth(30)
        self.collapse_button.clicked.connect(self.tray_ref.animate_hide)

        self.voice_recognition_button = QPushButton()
        mic_icon_path = os.path.join("assets", "microphone_icon.png")
        self.voice_recognition_button.setIcon(QIcon(mic_icon_path))
        self.voice_recognition_button.setFixedWidth(30)
        self.voice_recognition_button.clicked.connect(self.start_voice_recognition)

        icon = QLabel()
        icon_pixmap = QPixmap(icon_path).scaled(30, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon.setPixmap(icon_pixmap)
        collapse_row.addWidget(icon)
        collapse_row.addStretch()
        collapse_row.addWidget(self.voice_recognition_button)
        collapse_row.addWidget(self.collapse_button)
        layout.addLayout(collapse_row)

        self.chat_area = QScrollArea()
        self.chat_area.setWidgetResizable(True)
        self.chat_area.setStyleSheet("background-color: transparent; border: none;")
        self.chat_content = QVBoxLayout()
        self.chat_content.setAlignment(Qt.AlignTop)

        container = QWidget()
        container.setLayout(self.chat_content)
        self.chat_area.setWidget(container)
        layout.addWidget(self.chat_area)

        self.input_box = EnterSendTextEdit(self.send_prompt)
        self.input_box.setPlaceholderText("Ask something...")
        self.input_box.setFixedHeight(80)
        layout.addWidget(self.input_box)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_prompt)
        layout.addWidget(self.send_button)

        self.typing_timer = None
        self.typing_label = None
        self.typing_text = ""
        self.typing_index = 0

    def apply_config(self, config):
        self.config = config
        self.typing_speed = config.get("text_speed", 20)
        self.tts_voice = config.get("tts_voice", "en-GB-RyanNeural")

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

    def send_prompt(self):
        prompt = self.input_box.toPlainText().strip()
        if not prompt:
            return
        self.add_message("You", prompt, selectable=True)
        self.input_box.clear()
        self.get_ai_response(prompt)

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
            cmd += f' "{prompt}"'

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

