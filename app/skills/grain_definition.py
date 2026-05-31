import json
from typing import Any, Dict
from .base import BaseSkill

class GrainDefinitionSkill(BaseSkill):
    """
    Skill: Grain & Metric Definition
    Phase: B (Bridge - Domain -> Analytical)
    Goal: Declare the grain per process and catalog KPIs tied to business questions.
    """

    def execute(self, aggregates: list = None, domain_events: list = None, **kwargs) -> Dict[str, Any]:
        catalog = self.get_catalog()
        
        system_prompt = (
            "You are an expert Data Warehouse Architect. Your task is Grain & Metric Definition. "
            "Using the provided DDD Aggregates and Domain Events, define the target grain (what one row represents) "
            "for each potential business process. Also, extract a catalog of likely KPIs/metrics that "
            "would be associated with those grains."
        )
        
        user_prompt = json.dumps({
            "aggregates": aggregates or [],
            "domain_events": domain_events or [],
        })
        
        output_schema = {
            "type": "object",
            "properties": {
                "processes": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "process_name": {"type": "string"},
                            "grain_description": {"type": "string"},
                            "associated_metrics": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "metric_name": {"type": "string"},
                                        "definition": {"type": "string"}
                                    },
                                    "required": ["metric_name", "definition"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["process_name", "grain_description", "associated_metrics"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["processes"],
            "additionalProperties": False
        }
        
        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            provider="openai"
        )
