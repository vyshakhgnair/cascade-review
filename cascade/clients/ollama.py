import requests
from typing import List, Dict
from cascade.clients.base import BaseClient

class OllamaClient(BaseClient):
    def __init__(self, model: str, api_key: str = None, base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1024) -> str:
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False,
                  "options": {"num_predict": max_tokens, "temperature": 0}},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def is_available(self) -> bool:
        try:
            return requests.get(f"{self.base_url}/api/tags", timeout=3).status_code == 200
        except Exception:
            return False
