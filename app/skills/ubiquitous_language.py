import json
from typing import Any, Dict
from .base import BaseSkill

class UbiquitousLanguageSkill(BaseSkill):
    """
    Skill: Ubiquitous Language Extraction
    Phase: A (Strategic DDD)
    Goal: Define the per-context business glossary (entities, terms, canonical definitions).
    """

    def execute(self, bounded_contexts: list = None, **kwargs) -> Dict[str, Any]:
        catalog = self.get_catalog()
        
        system_prompt = (
            "You are an expert Data Architect practicing Domain-Driven Design (DDD). "
            "Your task is Ubiquitous Language Extraction. Given the schemas and defined bounded contexts, "
            "create a canonical business glossary for each context. Define the entities and key business terms."
        )
        
        user_prompt = json.dumps({
            "bounded_contexts": bounded_contexts or [],
            "catalog_overview": {
                s.get("name"): [t.get("name") for t in s.get("tables", [])]
                for s in catalog.get("schemas", [])
            }
        })
        
        output_schema = {
            "type": "object",
            "properties": {
                "glossary": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "context": {"type": "string"},
                            "terms": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "term": {"type": "string"},
                                        "definition": {"type": "string"},
                                        "synonyms": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    },
                                    "required": ["term", "definition", "synonyms"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["context", "terms"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["glossary"],
            "additionalProperties": False
        }
        
        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            provider="openai"
        )
