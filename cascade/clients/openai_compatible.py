import time
import requests
from typing import List, Dict
from cascade.clients.base import BaseClient

class OpenAICompatibleClient(BaseClient):
    def __init__(self, model: str, api_key: str = None, base_url: str = "https://api.openai.com/v1"):
        self.model = model
        self.api_key = api_key or ""
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1024) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        if "openrouter" in self.base_url:
            headers["HTTP-Referer"] = "https://github.com/vyshakhgnair/cascade-review"
            headers["X-Title"] = "Cascade Review"

        last_err = None
        for attempt in range(3):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json={"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": 0},
                    timeout=60,
                )
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    import sys
                    print(f"\033[2m  ⏳ Rate limited, retrying in {retry_after}s (attempt {attempt + 1}/3)…\033[0m", file=sys.stderr, flush=True)
                    time.sleep(retry_after)
                    continue
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except requests.exceptions.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    last_err = e
                    time.sleep(2 ** attempt)
                    continue
                raise
            except requests.exceptions.Timeout:
                last_err = TimeoutError("Request timed out")
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                raise last_err

        raise last_err or RuntimeError("Max retries exceeded")

    def is_available(self) -> bool:
        return bool(self.api_key)
