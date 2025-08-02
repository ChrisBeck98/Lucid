import sys, os, yaml

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "Lucid")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yaml")

DEFAULT_CONFIG = {
    "api_keys": {
        "openai": "",
        "gemini": "",
        "groq": "",
        "deepseek": ""
    },
    "text_speed": 20,
    "selected_model": "phind"
}

def update_config(model_flags, api_key):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    enabled = model_flags.split(',')
    for i, key in enumerate(["openai", "gemini", "groq", "deepseek"]):
        if enabled[i].lower() == "true":
            DEFAULT_CONFIG["api_keys"][key] = api_key

    with open(CONFIG_PATH, "w") as f:
        yaml.dump(DEFAULT_CONFIG, f)

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        update_config(sys.argv[1], sys.argv[2])
