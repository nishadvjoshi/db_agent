from app.llm.ollama_client import OllamaClient
from app.llm.openai_client import OpenAIClient
from app.llm.gemini_client import GeminiClient

def get_client(provider: str):
    provider = (provider or "").lower()
    if provider == "local" or provider == "ollama":
        return OllamaClient()
    if provider == "openai":
        return OpenAIClient()
    if provider == "gemini":
        return GeminiClient()
    raise ValueError(f"Unknown LLM provider: {provider}")
