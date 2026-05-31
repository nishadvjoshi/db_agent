import json
from typing import Any, Dict
from .base import BaseSkill

class AggregateModelingSkill(BaseSkill):
    """
    Skill: Aggregate & Entity Modeling
    Phase: A (Strategic DDD)
    Goal: Define per-context aggregates, entities, and value objects.
    """

    def execute(self, bounded_contexts: list = None, **kwargs) -> Dict[str, Any]:
        catalog = self.get_catalog()
        
        system_prompt = (
            "You are an expert Data Architect practicing Domain-Driven Design (DDD). "
            "Your task is Aggregate Modeling. Using the bounded contexts, group the tables into Aggregate Roots, "
            "Entities, and Value Objects for each context."
        )
        
        user_prompt = json.dumps({
            "bounded_contexts": bounded_contexts or [],
        })
        
        output_schema = {
            "type": "object",
            "properties": {
                "aggregates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "context": {"type": "string"},
                            "aggregate_roots": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "entities": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        },
                                        "value_objects": {
                                            "type": "array",
                                            "items": {"type": "string"}
                                        }
                                    },
                                    "required": ["name", "entities", "value_objects"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["context", "aggregate_roots"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["aggregates"],
            "additionalProperties": False
        }
        
        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            provider="openai"
        )
