import os
import yaml
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG = {
    "models": {
        "local": {
            "provider": "ollama",
            "model": "qwen2.5-coder:3b",
            "base_url": "http://localhost:11434",
        },
        "mid": {
            "provider": "groq",
            "model": "llama-3.3-70b-versatile",
            "api_key_env": "GROQ_API_KEY",
        },
        "frontier": {
            "provider": "openrouter",
            "model": "deepseek/deepseek-chat-v3-0324:free",
            "api_key_env": "OPENROUTER_API_KEY",
        },
    },
    "routing": {
        "local_max_lines": 50,
        "mid_max_lines": 200,
        "force_tier": "auto",
        "fallback": "mid",
    },
    "review": {
        "severity_threshold": "warning",
        "exclude": ["migrations/", "vendor/", "node_modules/"],
        "explain": False,
    },
    "output": {
        "format": "terminal",
    },
}

def find_config() -> Optional[Path]:
    search = Path.cwd()
    for _ in range(5):
        candidate = search / ".cascade.yml"
        if candidate.exists():
            return candidate
        search = search.parent
    return None

def load_config() -> dict:
    config = {k: dict(v) for k, v in DEFAULT_CONFIG.items()}
    config_path = find_config()
    if config_path:
        with open(config_path) as f:
            user_config = yaml.safe_load(f) or {}
        for section, values in user_config.items():
            if isinstance(values, dict) and section in config:
                config[section].update(values)
            else:
                config[section] = values
    return config

def resolve_api_key(tier_config: dict) -> str:
    env_var = tier_config.get("api_key_env", "")
    direct = tier_config.get("api_key", "")
    return direct or os.environ.get(env_var, "")
