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

def _find_configs() -> list:
    configs = []
    search = Path.cwd()
    for _ in range(10):
        candidate = search / ".cascade.yml"
        if candidate.exists():
            configs.append(candidate)
        if (search / ".git").exists():
            break
        search = search.parent
    configs.reverse()
    return configs


def _deep_merge(base: dict, overlay: dict) -> dict:
    result = base.copy()
    for key, value in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def find_config() -> Optional[Path]:
    configs = _find_configs()
    return configs[0] if configs else None


def load_config() -> dict:
    config = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT_CONFIG.items()}
    for config_path in _find_configs():
        with open(config_path) as f:
            layer = yaml.safe_load(f) or {}
        config = _deep_merge(config, layer)
    return config

def resolve_api_key(tier_config: dict) -> str:
    env_var = tier_config.get("api_key_env", "")
    direct = tier_config.get("api_key", "")
    return direct or os.environ.get(env_var, "")
