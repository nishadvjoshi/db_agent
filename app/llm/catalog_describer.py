from typing import Dict, Any, List, Optional
import logging
from app.config import settings
from app.llm.ollama_client import OllamaClient
from app.llm.gemini_client import GeminiClient
from app.llm.openai_client import OpenAIClient

logger = logging.getLogger(__name__)

class CatalogDescriber:
    """Uses LLMs defined in config.yml with fallbacks to generate summaries for catalog tables and columns."""
    
    def __init__(self):
        self.clients = {
            "ollama": OllamaClient(),
            "gemini": GeminiClient(),
            "openai": OpenAIClient(),
        }
        self.prefer = getattr(settings, "llm_prefer", "local")
        if self.prefer == "local":
            self.prefer = getattr(settings, "llm_local", {}).get("provider", "ollama")
            
        fallback_list = getattr(settings, "llm_fallback_order", ["openai", "gemini"])
        
        self.order = []
        if self.prefer in self.clients:
            self.order.append(self.prefer)
            
        for f in fallback_list:
            if f in self.clients and f not in self.order:
                self.order.append(f)
                
        self.failed_counts = {p: 0 for p in self.order}

    def generate_table_description(self, schema_name: str, table_name: str, columns: List[Dict[str, Any]]) -> tuple[str, str]:
        """
        Returns a tuple of (description_text, generated_by_llm_name).
        """
        system_prompt = (
            "You are an expert AI Data Architect."
            "\nYour task is to generate a concise, human-readable business description for a database table."
        )
        
        col_summary = "\n".join([f"- {c['name']} ({c['data_type']})" for c in columns])
        
        user_prompt = (
            f"Please describe the purpose of the table '{schema_name}.{table_name}'.\n"
            f"Here are its columns:\n{col_summary}\n\n"
            "Keep the description under 3 sentences and focus on its business value."
        )
        
        schema = {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "The concise business description of the table"
                }
            },
            "required": ["description"],
            "additionalProperties": False
        }

        for provider in self.order:
            if self.failed_counts[provider] >= 3:
                continue
                
            client = self.clients[provider]
            try:
                logger.info(f"Attempting to generate description for table {table_name} using {provider}")
                result = client.generate_json(system_prompt, user_prompt, schema)
                desc = result.get("description", "").strip()
                if desc:
                    self.failed_counts[provider] = 0 # reset on success
                    return desc, provider
            except Exception as e:
                self.failed_counts[provider] += 1
                logger.warning(f"Provider {provider} failed for table {table_name}: {e}")

        return "Could not generate description.", "none"

    def generate_column_description(self, schema_name: str, table_name: str, column_name: str, data_type: str) -> tuple[str, str]:
        """
        Returns a tuple of (description_text, generated_by_llm_name).
        """
        system_prompt = (
            "You are an expert AI Data Architect."
            "\nYour task is to generate a concise 1-sentence business description for a database column."
        )
        
        user_prompt = (
            f"Please describe the column '{column_name}' of type '{data_type}' "
            f"in the table '{schema_name}.{table_name}'.\n"
            "Keep the description to exactly 1 sentence focusing on what data it likely holds."
        )
        
        schema = {
            "type": "object",
            "properties": {
                "description": {"type": "string"}
            },
            "required": ["description"],
            "additionalProperties": False
        }

        for provider in self.order:
            if self.failed_counts[provider] >= 3:
                continue
                
            client = self.clients[provider]
            try:
                result = client.generate_json(system_prompt, user_prompt, schema)
                desc = result.get("description", "").strip()
                if desc:
                    self.failed_counts[provider] = 0 # reset on success
                    return desc, provider
            except Exception as e:
                self.failed_counts[provider] += 1
                pass

        return "Could not generate description.", "none"
