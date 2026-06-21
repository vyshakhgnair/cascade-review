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

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json={"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": 0},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def is_available(self) -> bool:
        return bool(self.api_key)
