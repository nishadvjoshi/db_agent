import abc
import json
from typing import Any, Dict, Optional

from app.llm.factory import get_client
from app.catalog_store import CatalogStore

class BaseSkill(abc.ABC):
    """
    Abstract base class for all Agent Skills.
    Each skill encapsulates a localized LLM task within the DDD to EDW pipeline.
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.store = CatalogStore()

    @abc.abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the skill and return a structured JSON response."""
        pass

    def get_catalog(self) -> Dict[str, Any]:
        return self.store.get_catalog(self.run_id)

    def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        output_schema: Dict[str, Any],
        provider: str = "openai"
    ) -> Dict[str, Any]:
        """Helper to invoke the LLM and enforce JSON output."""
        client = get_client(provider)
        try:
            resp = client.generate_json(
                system=system_prompt,
                user=user_prompt,
                schema=output_schema
            )
            if isinstance(resp, dict):
                return resp
            if isinstance(resp, str):
                return json.loads(self._extract_json(resp))
            raise ValueError(f"Unexpected LLM response type: {type(resp)}")
        except Exception as e:
            raise RuntimeError(f"Skill LLM Call Failed: {e}")

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        if text.startswith("{") and text.endswith("}"):
            return text
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON found")
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        raise ValueError("Unbalanced JSON")
