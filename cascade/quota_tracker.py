import json
import time
from pathlib import Path

QUOTA_FILE = Path.home() / ".cascade" / "quota.json"

PROVIDER_LIMITS = {
    "groq":       30_000,
    "openrouter": 50_000,
}

def _load() -> dict:
    if QUOTA_FILE.exists():
        with open(QUOTA_FILE) as f:
            return json.load(f)
    return {}

def _save(data: dict):
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUOTA_FILE, "w") as f:
        json.dump(data, f)

def record_usage(provider: str, tokens: int):
    data = _load()
    key = f"{provider}:{time.strftime('%Y-%m-%d')}"
    data[key] = data.get(key, 0) + tokens
    _save(data)

def get_today_usage(provider: str) -> int:
    return _load().get(f"{provider}:{time.strftime('%Y-%m-%d')}", 0)

def is_likely_rate_limited(provider: str) -> bool:
    limit = PROVIDER_LIMITS.get(provider, 0)
    if not limit:
        return False
    return get_today_usage(provider) >= limit * 0.9
