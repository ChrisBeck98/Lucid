import os
import yaml

CONFIG_PATH = os.path.join("config", "config.yaml")

DEFAULT_CONFIG = {
    "api_keys": {
        "openai": "",
        "gemini": "",
        "groq": "",
        "deepseek": "",
        "ollama": "enabled",
        "phind": "enabled",
        "pollinations": "enabled"
    },
    "enabled_models": {
        "openai": False,
        "gemini": False,
        "groq": False,
        "deepseek": False,
        "ollama": False,
        "phind": True,
        "pollinations": True
    },
    "openai_url": "api.openai.com/v1",
    "selected_model": "phind",
    "text_speed": 20,
    "tts_voice": "en-GB-RyanNeural",
    "run_on_startup": False 
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    with open(CONFIG_PATH, "r") as f:
        try:
            config = yaml.safe_load(f)
            if not isinstance(config, dict):
                raise ValueError("Invalid config format")
        except Exception:
            config = DEFAULT_CONFIG.copy()

    # Ensure all default keys are present
    def deep_update(d, u):
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = deep_update(d.get(k, {}), v)
            else:
                d.setdefault(k, v)
        return d

    return deep_update(config, DEFAULT_CONFIG.copy())


def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f)
