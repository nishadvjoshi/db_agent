import json
import requests
from typing import Dict, Any
from app.config import settings
from app.llm.base import LLMClient

class OpenAIClient(LLMClient):
    def __init__(self):
        cfg = getattr(settings, "llm_openai", None) or {}
        self.api_key = cfg.get("api_key", "")
        self.model = cfg.get("model", "gpt-4o-mini")

    def _make_strict(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(schema, dict):
            new_schema = {}
            for k, v in schema.items():
                new_schema[k] = self._make_strict(v)
            if new_schema.get("type") == "object":
                new_schema["additionalProperties"] = False
            return new_schema
        elif isinstance(schema, list):
            return [self._make_strict(item) for item in schema]
        else:
            return schema

    def generate_json(self, system: str, user: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key or self.api_key == "PUT_KEY_HERE":
            raise ValueError("OpenAI API key missing in config.yml")

        strict_schema = self._make_strict(schema)

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema", 
                "json_schema": {
                    "name": "result", 
                    "schema": strict_schema,
                    "strict": True
                }
            }
        }

        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()

        text = data["choices"][0]["message"]["content"]
        return json.loads(text)

    def generate_text(self, system: str, user: str) -> str:
        if not self.api_key or self.api_key == "PUT_KEY_HERE":
            raise ValueError("OpenAI API key missing in config.yml")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ]
        }

        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()

        return data["choices"][0]["message"]["content"].strip()
