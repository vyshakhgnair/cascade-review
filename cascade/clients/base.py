from abc import ABC, abstractmethod
from typing import List, Dict

class BaseClient(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1024) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass
