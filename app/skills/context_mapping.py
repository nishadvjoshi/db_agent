import json
from typing import Any, Dict
from .base import BaseSkill

class ContextMappingSkill(BaseSkill):
    """
    Skill: Context Mapping
    Phase: A (Strategic DDD)
    Goal: Define the relationship graph between contexts (upstream/downstream).
    """

    def execute(self, bounded_contexts: list = None, **kwargs) -> Dict[str, Any]:
        catalog = self.get_catalog()
        
        system_prompt = (
            "You are an expert Data Architect practicing Domain-Driven Design (DDD). "
            "Your task is Context Mapping. Using the defined bounded contexts and foreign key relationships (edges), "
            "determine the upstream/downstream relationships between these contexts. "
            "Identify integration patterns (e.g., Conformist, Anti-Corruption Layer, Shared Kernel)."
        )
        
        user_prompt = json.dumps({
            "bounded_contexts": bounded_contexts or [],
            "edges": catalog.get("edges", [])
        })
        
        output_schema = {
            "type": "object",
            "properties": {
                "context_map": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "upstream_context": {"type": "string"},
                            "downstream_context": {"type": "string"},
                            "relationship_type": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["upstream_context", "downstream_context", "relationship_type", "description"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["context_map"],
            "additionalProperties": False
        }
        
        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            provider="openai"
        )
