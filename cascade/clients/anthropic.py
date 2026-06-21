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
        response.raise_for_status()
        return response.json()["content"][0]["text"]

    def is_available(self) -> bool:
        return bool(self.api_key)
