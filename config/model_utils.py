# config/model_utils.py
MODEL_PROVIDER_MAP = {
    "gpt-3.5-turbo": "openai",
    "gpt-4o": "openai",
    "gemini-pro": "gemini",
    "deepseek-chat": "deepseek",
    "mixtral": "groq",
    "llama3": "groq",
    "phind": "phind",
    "isou": "isou",
    "pollinations": "pollinations",
    "llama3-local": "ollama"
}

def get_provider_from_model(model: str) -> str:
    return MODEL_PROVIDER_MAP.get(model, "phind")
