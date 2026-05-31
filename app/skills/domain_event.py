import json
from typing import Any, Dict
from .base import BaseSkill

class DomainEventSkill(BaseSkill):
    """
    Skill: Domain Event Identification
    Phase: A (Strategic DDD)
    Goal: List domain events (e.g. ClaimSubmitted) to seed fact tables and CDC design.
    """

    def execute(self, aggregates: list = None, **kwargs) -> Dict[str, Any]:
        catalog = self.get_catalog()
        
        system_prompt = (
            "You are an expert Data Architect practicing Domain-Driven Design (DDD). "
            "Your task is Domain Event Identification. Using the provided schemas and aggregate models, "
            "infer the key Domain Events that occur within the system (e.g., 'OrderPlaced', 'UserRegistered'). "
            "Look for tables with temporal or status data."
        )
        
        user_prompt = json.dumps({
            "schemas": {s.get("name"): [t.get("name") for t in s.get("tables", [])] for s in catalog.get("schemas", [])},
            "aggregates": aggregates or []
        })
        
        output_schema = {
            "type": "object",
            "properties": {
                "domain_events": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "event_name": {"type": "string"},
                            "triggered_by_aggregate": {"type": "string"},
                            "description": {"type": "string"}
                        },
                        "required": ["event_name", "triggered_by_aggregate", "description"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["domain_events"],
            "additionalProperties": False
        }
        
        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            provider="openai"
        )
