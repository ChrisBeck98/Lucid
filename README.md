# 🛠 Lucid – Technical Overview

**Lucid** is a taskbar-based AI assistant designed for simplicity, speed, and accessibility. Built with PyQt5, it provides a seamless user experience for interacting with large language models (LLMs) through a clean, floating chat window.

## ⚙️ Core Technologies

- **Python / PyQt5** – GUI and tray system
- **tgpt** – Command-line interface to multiple LLM providers
- **Vosk** – Offline voice-to-text engine for speech recognition
- **Edge-TTS + playsound3** – Local text-to-speech output
- **YAML** – Lightweight configuration and state persistence
- **Inno Setup** – Branded installer with API onboarding and model selection

## 🔑 Key Features

### 🎤 Voice Recognition
- Powered by Vosk with full offline support
- Real-time transcription appears in a live-updating chat bubble
- Final voice prompt is auto-submitted to the selected AI model

### 🔊 Text-to-Speech (TTS)
- AI responses can be spoken aloud with a single click
- User selects from multiple neural voices (e.g. Ryan, Jenny, Guy)
- Preview voice feature in Settings

### 🖥 Chat Window
- Always-on-top by default, with pop-out/dock toggle
- Custom typing speed animations (slow to instant)
- Clean UI with color-coded bubbles for user and AI
- Copy and speak buttons on AI responses

### 💬 Language Model Integration
- Supports OpenAI, Gemini, Groq, Phind, DeepSeek, and more
- Provider API keys configured via GUI
- Each model dynamically enabled/disabled
- Uses `tgpt` CLI as backend, launching subprocess calls for responses

### 🪟 System Tray Integration
- Left-click to toggle chat window
- Right-click menu with **Settings** and **Quit**
- Smooth show/hide animations with customizable positioning
- Global shortcuts:  
  - `Ctrl+L` → Open chat  
  - `Ctrl+Shift+L` → Open chat + Start voice capture

### 🧠 Settings Panel
- Tabs for **General** and **Models**
- Adjustable typing speed, default model, and voice
- Toggle “Run on Windows Startup”
- Enable/disable model providers with secure API key entry

## 📂 Configuration & Persistence

All settings are stored in `config/config.yaml`, including:

```yaml
enabled_models:
  openai: true
  groq: true
api_keys:
  openai: "sk-..."
text_speed: 12
selected_model: "gpt-4o"
tts_voice: "en-US-JennyNeural"
run_on_startup: true