from abc import ABC, abstractmethod
from typing import Dict, Any

class LLMClient(ABC):
    @abstractmethod
    def generate_json(self, system: str, user: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Return a JSON object that matches `schema`."""
        raise NotImplementedError

    @abstractmethod
    def generate_text(self, system: str, user: str) -> str:
        """Return raw generated text."""
        raise NotImplementedError
