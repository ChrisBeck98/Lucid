# common_imports.py

import os
import yaml
import sys
import json
import shlex
import queue
import threading
import asyncio
import subprocess

from PyQt5.QtCore import Qt, QTimer, QTimerEvent, QPropertyAnimation, QPoint, QEventLoop
from PyQt5.QtGui import QIcon, QPixmap, QCursor, QMouseEvent, QClipboard
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QLineEdit, QComboBox, QCheckBox, QTabWidget, QFrame, QToolButton
)

from edge_tts import Communicate
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from playsound3 import playsound
