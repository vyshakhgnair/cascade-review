import requests
from typing import List, Dict
from cascade.clients.base import BaseClient

class GeminiClient(BaseClient):
    def __init__(self, model: str, api_key: str = None, base_url: str = "https://generativelanguage.googleapis.com"):
        self.model = model
        self.api_key = api_key or ""
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1024) -> str:
        contents = []
        for m in messages:
            if m["role"] == "system":
                contents.append({"role": "user", "parts": [{"text": m["content"]}]})
                contents.append({"role": "model", "parts": [{"text": "Understood."}]})
            else:
                role = "model" if m["role"] == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": m["content"]}]})

        response = requests.post(
            f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}",
            json={"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0}},
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]

    def is_available(self) -> bool:
        return bool(self.api_key)
