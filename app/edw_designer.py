"""
Enterprise Data Warehouse (EDW) Designer
Orchestrates the LLM workflow to understand the domain catalog, suggest data warehouse themes, 
chat with the user, and generate full Star Schema DDLs.
"""

import json
from typing import Dict, Any, List

from app.config import settings
from app.catalog_store import CatalogStore
from app.llm.factory import get_client

def get_domain_context(run_id: str) -> str:
    """Aggregates all tables and descriptions from the catalog into a dense JSON string."""
    store = CatalogStore()
    con = store._conn()
    cur = con.cursor(dictionary=True)
    
    try:
        # Fetch tables
        cur.execute(
            """SELECT schema_name, table_name, row_count, ai_description 
               FROM `catalog_tables` 
               WHERE run_id=%s""",
            (run_id,)
        )
        tables = cur.fetchall()
        
        # For simplicity in the prompt, we'll format this nicely
        context = []
        for t in tables:
            context.append({
                "table": f"{t['schema_name']}.{t['table_name']}",
                "description": t.get('ai_description', 'No description'),
                "row_count": t.get('row_count', 0)
            })
            
        return json.dumps(context, ensure_ascii=False)
    finally:
        cur.close()
        con.close()

def propose_edw_themes(run_id: str) -> List[Dict[str, str]]:
    """Proposes 3-4 data warehouse architectures based on the domain context."""
    domain_context = get_domain_context(run_id)
    
    system_prompt = (
        "You are an expert Data Architect. Review the following database catalog context. "
        "Propose 3 distinct, valuable Data Warehouse reporting themes (Star Schemas) that could be built from this data. "
        "Return a JSON array of objects, each with 'theme_name' and 'description'."
    )
    
    schema = {
        "type": "object",
        "properties": {
            "themes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "theme_name": {"type": "string"},
                        "description": {"type": "string"}
                    },
                    "required": ["theme_name", "description"]
                }
            }
        },
        "required": ["themes"]
    }
    
    preferred_llm = getattr(settings, "llm_prefer", "openai")
    client = get_client(preferred_llm)
    
    try:
        resp = client.generate_json(system=system_prompt, user=domain_context, schema=schema)
        return resp.get("themes", [])
    except Exception as e:
        print(f"Failed to propose themes: {e}")
        return []

def generate_edw_blueprint(run_id: str, user_prompt: str) -> Dict[str, Any]:
    """Generates a complete EDW Star Schema blueprint based on user instructions."""
    domain_context = get_domain_context(run_id)
    
    system_prompt = (
        "You are an expert Data Architect. Based on the provided database context and the user's reporting requirement, "
        "design a comprehensive Enterprise Data Warehouse Star Schema that strictly follows SCD (Slowly Changing Dimension) principles.\n"
        "You must return a JSON object containing:\n"
        "- 'blueprint_name': A short name for the EDW.\n"
        "- 'description': A brief explanation of the design.\n"
        "- 'fact_tables': A list of fact table objects. Each object must have 'name' (the new fact table name), "
        "'source_tables' (list of original tables it draws from), and 'columns' (list of objects with 'name', 'type', and 'source_column'). "
        "Fact tables should link to dimensions using the dimension's surrogate key.\n"
        "- 'dimension_tables': A list of dimension table objects formatted exactly like the fact_tables. "
        "Every dimension MUST include the following standard SCD metadata columns: "
        "'meta_surr_key' (PK), 'meta_hash_key', 'meta_eff_date', 'meta_end_date', 'meta_iud_flag', plus any necessary business columns.\n"
        "Ensure all data types are valid MySQL types."
    )
    
    table_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "source_tables": {"type": "array", "items": {"type": "string"}},
            "columns": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "source_column": {"type": "string"}
                    },
                    "required": ["name", "type", "source_column"]
                }
            }
        },
        "required": ["name", "source_tables", "columns"]
    }
    
    schema = {
        "type": "object",
        "properties": {
            "blueprint_name": {"type": "string"},
            "description": {"type": "string"},
            "fact_tables": {"type": "array", "items": table_schema},
            "dimension_tables": {"type": "array", "items": table_schema}
        },
        "required": ["blueprint_name", "description", "fact_tables", "dimension_tables"]
    }
    
    preferred_llm = getattr(settings, "llm_prefer", "openai")
    client = get_client(preferred_llm)
    
    try:
        blueprint = client.generate_json(system=system_prompt, user=f"Context: {domain_context}\n\nUser Requirement: {user_prompt}", schema=schema)
        return blueprint
    except Exception as e:
        print(f"Failed to generate blueprint: {e}")
        return {}

def generate_edw_ddl(blueprint: Dict[str, Any], target_schema: str = "analytics_dwh") -> str:
    """Converts a JSON blueprint into physical MySQL CREATE TABLE and INSERT statements."""
    if not blueprint:
        return "-- No blueprint provided."
        
    ddl = [
        f"-- ==========================================",
        f"-- EDW Blueprint: {blueprint.get('blueprint_name', 'Custom DWH')}",
        f"-- {blueprint.get('description', '')}",
        f"-- ==========================================\n",
        f"CREATE DATABASE IF NOT EXISTS `{target_schema}`;",
        f"USE `{target_schema}`;\n"
    ]
    
    # Generate Dimensions
    for dim in blueprint.get("dimension_tables", []):
        table_name = dim.get("name")
        cols = []
        for c in dim.get("columns", []):
            cols.append(f"  `{c['name']}` {c.get('type', 'VARCHAR(255)')}")
            
        ddl.append(f"DROP TABLE IF EXISTS `{table_name}`;")
        ddl.append(f"CREATE TABLE `{table_name}` (\n" + ",\n".join(cols) + "\n);\n")
    
    # Generate Facts
    for fact in blueprint.get("fact_tables", []):
        table_name = fact.get("name")
        cols = []
        for c in fact.get("columns", []):
            cols.append(f"  `{c['name']}` {c.get('type', 'INT')}")
            
        ddl.append(f"DROP TABLE IF EXISTS `{table_name}`;")
        ddl.append(f"CREATE TABLE `{table_name}` (\n" + ",\n".join(cols) + "\n);\n")
            
    return "\n".join(ddl)
