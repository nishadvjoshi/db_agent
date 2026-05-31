import json
from typing import Any, Dict
from .base import BaseSkill

class DomainDiscoverySkill(BaseSkill):
    """
    Skill: Domain Discovery
    Phase: A (Strategic DDD)
    Goal: Scan the raw schema and identify the high-level business domains and source systems.
    """

    def execute(self, **kwargs) -> Dict[str, Any]:
        catalog = self.get_catalog()
        
        # Prepare a lightweight summary of the schema to send to the LLM
        schema_summary = {}
        for schema in catalog.get("schemas", []):
            schema_name = schema.get("name")
            tables = [t.get("name") for t in schema.get("tables", [])]
            schema_summary[schema_name] = tables
            
        system_prompt = (
            "You are an expert Data Architect practicing Domain-Driven Design (DDD). "
            "Your task is Domain Discovery. Analyze the provided database schemas and tables. "
            "Output a JSON object identifying the core business domains and the source systems they likely originated from."
        )
        
        user_prompt = json.dumps({
            "schemas": schema_summary,
        })
        
        output_schema = {
            "type": "object",
            "properties": {
                "domains": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "tables_included": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "description": {"type": "string"}
                        },
                        "required": ["name", "tables_included", "description"],
                        "additionalProperties": False
                    }
                },
                "source_systems": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "type": {"type": "string"},
                            "confidence": {"type": "string"}
                        },
                        "required": ["name", "type", "confidence"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["domains", "source_systems"],
            "additionalProperties": False
        }
        
        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            provider="openai"  # We can configure this via settings later
        )
