import json
import requests
from typing import Dict, Any
from app.config import settings
from app.llm.base import LLMClient

class GeminiClient(LLMClient):
    def __init__(self):
        cfg = getattr(settings, "llm_gemini", None) or {}
        self.api_key = cfg.get("api_key", "")
        self.model = cfg.get("model", "gemini-1.5-flash")

    def generate_json(self, system: str, user: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Gemini API key missing in config.yml")

        # Gemini expects a single prompt; keep it simple
        prompt = (
            f"{system}\n\n"
            f"Return ONLY valid JSON matching this JSON schema:\n{json.dumps(schema)}\n\n"
            f"USER:\n{user}\n"
        )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        r = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=120)
        r.raise_for_status()
        data = r.json()

        text = data["candidates"][0]["content"]["parts"][0]["text"]
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start:end+1])

    def generate_text(self, system: str, user: str) -> str:
        if not self.api_key:
            raise ValueError("Gemini API key missing in config.yml")
            
        prompt = f"{system}\n\nUSER:\n{user}\n"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        r = requests.post(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=120)
        r.raise_for_status()
        data = r.json()
        
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
