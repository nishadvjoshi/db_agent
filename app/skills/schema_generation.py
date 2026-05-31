import json
from typing import Any, Dict
from .base import BaseSkill

class SchemaGenerationSkill(BaseSkill):
    """
    Skill: Physical Schema Generation
    Phase: C (Technology)
    Goal: Generates physical MySQL DDL scripts from the logical schema.
    """

    def execute(self, logical_schema: list = None, **kwargs) -> Dict[str, Any]:
        catalog = self.get_catalog()
        
        system_prompt = (
            "You are an expert Data Engineer. Your task is Physical Schema Generation. "
            "Using the provided Logical Schema (Tables, Columns, Keys), generate the exact physical "
            "MySQL DDL script to create this Data Warehouse schema. Ensure you use IF NOT EXISTS "
            "and appropriate MySQL data types."
        )
        
        user_prompt = json.dumps({
            "logical_schema": logical_schema or [],
        })
        
        output_schema = {
            "type": "object",
            "properties": {
                "ddl": {"type": "string"},
                "dialect": {"type": "string"}
            },
            "required": ["ddl", "dialect"],
            "additionalProperties": False
        }
        
        return self._call_llm(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
            provider="openai"
        )
