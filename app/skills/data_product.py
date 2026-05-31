import json
from typing import Any, Dict
from .base import BaseSkill

class DataProductSkill(BaseSkill):
    """
    Skill: Data Product Definition (Data Mesh)
    Phase: A (Strategic DDD)
    Goal: Define per-domain data products (output ports, ownership, SLAs).
    """

    def execute(self, domains: list = None, **kwargs) -> Dict[str, Any]:
        catalog = self.get_catalog()
        
        system_prompt = (
            "You are an expert Data Architect practicing Data Mesh principles. "
            "Your task is Data Product Definition. Using the provided domains and catalog schemas, "
            "define the analytical Data Products for each domain, including their output ports and purpose."
        )
        
        user_prompt = json.dumps({
            "discovered_domains": domains or [],
        })
        
        output_schema = {
            "type": "object",
            "properties": {
                "data_products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "domain": {"type": "string"},
                            "product_name": {"type": "string"},
                            "description": {"type": "string"},
                            "recommended_sla": {"type": "string"}
                        },
                        "required": ["domain", "product_name", "description", "recommended_sla"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["data_products"],
            "additionalProperties": False
        }
        
        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            provider="openai"
        )
