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

def get_domain_context(run_id: str, included_tables: List[str] = None) -> str:
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
        
        # Fetch columns
        cur.execute(
            """SELECT schema_name, table_name, column_name 
               FROM `catalog_columns` 
               WHERE run_id=%s""",
            (run_id,)
        )
        columns = cur.fetchall()
        
        # Group columns by table
        cols_by_table = {}
        for c in columns:
            key = f"{c['schema_name']}.{c['table_name']}"
            if key not in cols_by_table:
                cols_by_table[key] = []
            cols_by_table[key].append(c['column_name'])
        
        # For simplicity in the prompt, we'll format this nicely
        context = []
        for t in tables:
            if included_tables is not None and t['table_name'] not in included_tables:
                continue
                
            key = f"{t['schema_name']}.{t['table_name']}"
            context.append({
                "table": key,
                "description": t.get('ai_description', 'No description'),
                "columns": cols_by_table.get(key, []),
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
    if preferred_llm == "local":
        preferred_llm = getattr(settings, "llm_local", {}).get("provider", "ollama")
    
    fallback_list = getattr(settings, "llm_fallback_order", ["openai", "gemini"])
    order = []
    if preferred_llm not in order: order.append(preferred_llm)
    for f in fallback_list:
        if f not in order: order.append(f)
    
    for provider in order:
        try:
            client = get_client(provider)
            resp = client.generate_json(system=system_prompt, user=domain_context, schema=schema)
            if resp and "themes" in resp:
                return resp.get("themes", [])
        except Exception as e:
            print(f"Provider {provider} failed to propose themes: {e}")
            
    return []

def generate_edw_blueprint(run_id: str, user_prompt: str, user_config: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generates a complete EDW Star Schema blueprint based on user instructions and explicit config grid."""
    
    # --- PERFORMANCE OPTIMIZATION ---
    # Filter the domain context to ONLY include tables marked as `is_included=True`.
    # This shrinks the context window by up to 90%, preventing local LLMs from hanging!
    included_tables = None
    if user_config:
        included_tables = [c['table_name'] for c in user_config if c.get('is_included')]
        
    domain_context = get_domain_context(run_id, included_tables)
    
    system_prompt = (
        "You are an expert Data Architect. Based on the provided database context and the user's reporting requirement, "
        "design a comprehensive Enterprise Data Warehouse Star Schema.\n"
        "You must return a JSON object containing:\n"
        "- 'blueprint_name': A short name for the EDW.\n"
        "- 'description': A brief explanation of the design.\n"
        "- 'fact_tables': A list of fact table objects. Each object must have 'name' (the new fact table name), "
        "'source_tables' (list of original tables it draws from), and 'columns' (list of objects with 'name', 'type', and 'source_column'). "
        "Fact tables should link to dimensions using the dimension's surrogate key.\n"
        "- 'dimension_tables': A list of dimension table objects formatted exactly like the fact_tables. "
        "IT IS CRITICAL that every dimension ALSO includes the actual business attributes (at least 3-5 columns) from the source tables (e.g., patient names, diagnoses, statuses, etc.).\n"
        "IMPORTANT STRICT CONSTRAINTS: You MUST strictly adhere to the USER'S EXPLICIT TABLE CONFIGURATION if provided in the prompt. "
        "Only include tables the user marked as included. "
        "Assign the exact table roles (Fact or Dimension) as requested. "
        "For Dimensions, you MUST generate the EXACT SCD metadata columns based on the requested SCD Type:\n"
        " - If 'SCD Type 1' or 'None': generate normal business columns.\n"
        " - If 'SCD Type 2': YOU MUST EXPLICITLY generate exactly these 5 columns in the dimension: 'meta_surr_key' (PK), 'meta_hash_key', 'meta_eff_date', 'meta_end_date', 'meta_iud_flag'.\n"
        " - If 'SCD Type 3': YOU MUST EXPLICITLY generate 'meta_surr_key' (PK), and for every specific column listed in 'Tracked Columns', you MUST generate a 'prev_<column_name>' and 'curr_<column_name>'.\n"
        "DO NOT just output the ID and metadata columns! You must include the standard business columns as well.\n"
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
    if preferred_llm == "local":
        preferred_llm = getattr(settings, "llm_local", {}).get("provider", "ollama")
    
    fallback_list = getattr(settings, "llm_fallback_order", ["openai", "gemini"])
    order = []
    if preferred_llm not in order: order.append(preferred_llm)
    for f in fallback_list:
        if f not in order: order.append(f)
    
    user_payload = f"Context: {domain_context}\n\nUser Requirement: {user_prompt}"
    if user_config:
        config_str = json.dumps([c for c in user_config if c.get('is_included')], indent=2)
        user_payload += f"\n\nUSER'S EXPLICIT TABLE CONFIGURATION (ONLY INCLUDE THESE):\n{config_str}"
        
    for provider in order:
        try:
            client = get_client(provider)
            blueprint = client.generate_json(system=system_prompt, user=user_payload, schema=schema)
            if blueprint:
                return blueprint
        except Exception as e:
            print(f"Provider {provider} failed to generate blueprint: {e}")
            
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
