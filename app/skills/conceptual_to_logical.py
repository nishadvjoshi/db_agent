import json
from typing import Any, Dict
from .base import BaseSkill

class ConceptualToLogicalSkill(BaseSkill):
    """
    Skill: Conceptual to Logical Model
    Phase: B (Bridge - Domain -> Analytical)
    Goal: Generates the exact source-agnostic schema with surrogate keys and relationships.
    """

    def execute(self, facts: list = None, dimensions: list = None, **kwargs) -> Dict[str, Any]:
        catalog = self.get_catalog()
        
        system_prompt = (
            "You are an expert Data Warehouse Architect. Your task is Conceptual to Logical Modeling. "
            "Using the provided Facts and Dimensions, define the logical schema (e.g. Star Schema). "
            "For each table, specify the exact columns, including surrogate keys, business keys, and foreign keys."
        )
        
        user_prompt = json.dumps({
            "facts": facts or [],
            "dimensions": dimensions or [],
        })
        
        output_schema = {
            "type": "object",
            "properties": {
                "logical_schema": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "table_name": {"type": "string"},
                            "type": {"type": "string"},
                            "columns": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "type": {"type": "string"},
                                        "is_primary_key": {"type": "boolean"},
                                        "foreign_key_target": {"type": ["string", "null"]}
                                    },
                                    "required": ["name", "type", "is_primary_key", "foreign_key_target"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["table_name", "type", "columns"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["logical_schema"],
            "additionalProperties": False
        }
        
        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            provider="openai"
        )
