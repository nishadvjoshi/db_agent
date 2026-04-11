import json
import requests
from typing import Dict, Any
from app.config import settings
from app.llm.base import LLMClient

class OllamaClient(LLMClient):
    def __init__(self):
        cfg = getattr(settings, "llm_local", None) or {}
        self.base_url = cfg.get("base_url", "http://localhost:11434")
        self.model = cfg.get("model", "llama3.1:8b")

    def generate_json(self, system: str, user: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        prompt = (
            f"{system}\n\n"
            f"Return ONLY valid JSON matching this JSON schema:\n{json.dumps(schema)}\n\n"
            f"USER:\n{user}\n"
        )

        r = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "format": "json", "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        text = r.json().get("response", "").strip()

        # Be strict: extract first JSON object
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise ValueError(f"Ollama returned non-JSON: {text[:500]}")
        return json.loads(text[start:end+1], strict=False)

    def generate_text(self, system: str, user: str) -> str:
        prompt = f"{system}\n\nUSER:\n{user}\n"
        r = requests.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()
