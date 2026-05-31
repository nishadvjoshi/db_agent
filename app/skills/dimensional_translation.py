import json
from typing import Any, Dict
from .base import BaseSkill

class DimensionalTranslationSkill(BaseSkill):
    """
    Skill: Dimensional Translation
    Phase: B (Bridge - Domain -> Analytical)
    Goal: Maps the DDD aggregates and grains into Kimball Facts and Conformed Dimensions.
    """

    def execute(self, processes: list = None, aggregates: list = None, **kwargs) -> Dict[str, Any]:
        catalog = self.get_catalog()
        
        system_prompt = (
            "You are an expert Data Warehouse Architect practicing Kimball Dimensional Modeling. "
            "Your task is Dimensional Translation. Using the provided DDD aggregates and analytical grains, "
            "translate these business concepts into a list of proposed Fact tables and Conformed Dimension tables."
        )
        
        user_prompt = json.dumps({
            "aggregates": aggregates or [],
            "processes_and_grains": processes or [],
        })
        
        output_schema = {
            "type": "object",
            "properties": {
                "facts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "grain": {"type": "string"},
                            "associated_dimensions": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "metrics": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["name", "grain", "associated_dimensions", "metrics"],
                        "additionalProperties": False
                    }
                },
                "dimensions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "is_conformed": {"type": "boolean"}
                        },
                        "required": ["name", "description", "is_conformed"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["facts", "dimensions"],
            "additionalProperties": False
        }
        
        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            provider="openai"
        )
