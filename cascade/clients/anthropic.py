import sys
import time
import requests
from typing import List, Dict
from cascade.clients.base import BaseClient

class AnthropicClient(BaseClient):
    def __init__(self, model: str, api_key: str = None, base_url: str = "https://api.anthropic.com"):
        self.model = model
        self.api_key = api_key or ""
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1024) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_messages = [m for m in messages if m["role"] != "system"]

        payload = {"model": self.model, "max_tokens": max_tokens, "messages": user_messages}
        if system:
            payload["system"] = system

        last_err = None
        for attempt in range(3):
            try:
                response = requests.post(
                    f"{self.base_url}/v1/messages",
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json=payload,
                    timeout=60,
                )
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    print(f"\033[2m  ⏳ Rate limited, retrying in {retry_after}s (attempt {attempt + 1}/3)…\033[0m", file=sys.stderr, flush=True)
                    time.sleep(retry_after)
                    continue
                response.raise_for_status()
                return response.json()["content"][0]["text"]
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
