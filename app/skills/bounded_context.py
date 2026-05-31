import json
from typing import Any, Dict
from .base import BaseSkill

class BoundedContextSkill(BaseSkill):
    """
    Skill: Bounded Context Identification
    Phase: A (Strategic DDD)
    Goal: Map out bounded contexts with explicit boundaries, preventing model corruption.
    """

    def execute(self, domains: list = None, **kwargs) -> Dict[str, Any]:
        catalog = self.get_catalog()
        
        schema_summary = {}
        for schema in catalog.get("schemas", []):
            schema_name = schema.get("name")
            tables = [t.get("name") for t in schema.get("tables", [])]
            schema_summary[schema_name] = tables
            
        system_prompt = (
            "You are an expert Data Architect practicing Domain-Driven Design (DDD). "
            "Your task is Bounded Context Identification. Using the provided schema and domains, "
            "define the Bounded Contexts. For each context, list the entities (tables) that belong strictly within its boundary."
        )
        
        user_prompt = json.dumps({
            "schemas": schema_summary,
            "discovered_domains": domains or []
        })
        
        output_schema = {
            "type": "object",
            "properties": {
                "bounded_contexts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "tables_included": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["name", "description", "tables_included"],
                        "additionalProperties": False
                    }
                },
                "integration_events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "event_name": {"type": "string"},
                            "from_context": {"type": "string"},
                            "to_context": {"type": "string"}
                        },
                        "required": ["event_name", "from_context", "to_context"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["bounded_contexts", "integration_events"],
            "additionalProperties": False
        }
        
        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            provider="openai"
        )
