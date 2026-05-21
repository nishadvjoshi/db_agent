import json
import re
from typing import Any, Dict, List, Tuple
from app.catalog_store import CatalogStore
from app.llm.factory import get_client
from app.config import settings

class Glossary:
    def __init__(self, run_id: str | None = None):
        self.run_id = run_id
        self.store = CatalogStore()

    def get_concept(self, concept: str) -> Dict[str, Any] | None:
        c = (concept or "").strip().lower()
        return self.store.get_learned_concept(c)

    def find_concepts(self, text: str) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Extracts known concepts from natural language text using local memory.
        If a new concept is explicitly asked via the UI, use `auto_learn_concept` separately.
        """
        text_l = (text or "").lower()
        hits = []
        all_concepts = self.store.get_all_learned_concepts()
        
        for name, payload in all_concepts.items():
            synonyms = [name] + list(payload.get("synonyms", []))
            if any(s.lower() in text_l for s in synonyms):
                hits.append((name, payload))
        return hits

    def auto_learn_concept(self, concept: str) -> Dict[str, Any]:
        """
        Uses configured LLM to learn the domain definition of a term and map it
        to the physical database schemas currently in `catalog.db`.
        """
        c = (concept or "").strip().lower()
        
        # 1. Check Memory
        existing = self.store.get_learned_concept(c)
        if existing:
            return existing
            
        # 2. Extract context
        if not self.run_id:
            raise ValueError("Glossary needs a run_id to map new concepts to the database schema.")
            
        catalog = self.store.get_catalog(self.run_id)
        
        available_tables = []
        for schema in catalog.get("schemas", []):
            s_name = schema["name"]
            for table in schema.get("tables", []):
                t_name = table["name"]
                columns = [col["name"] for col in table.get("columns", [])]
                available_tables.append(f"{s_name}.{t_name} (Cols: {', '.join(columns[:5])}...)")
                
        tables_str = "\n".join(available_tables)
        
        preferred_llm = getattr(settings, "llm_prefer", "openai")
        order = [preferred_llm]
        for fallback in getattr(settings, "llm_fallback_order", ["gemini", "openai"]):
            if fallback not in order:
                order.append(fallback)
        
        system = (
            "You are a Senior Data Architect AI. Your job is to learn the definition of the user's business concept, "
            "provide synonyms, and suggest which of our physical database tables and columns best represent it.\n"
            "Here are the available tables in our catalog:\n"
            f"{tables_str}\n\n"
            "Return valid JSON matching the requested schema. If you don't know the concept at all, make your best guess "
            "based on the table names, or return an empty mapping."
        )
        
        schema = {
            "description": "A clear, 1-2 sentence business definition of the concept.",
            "synonyms": ["list", "of", "similar", "terms"],
            "table_hints": ["table_name_1", "table_name_2"],
            "column_hints": {
                "logical_field_1": ["physical_col_1", "physical_col_2"],
                "logical_field_2": ["physical_col_3"]
            }
        }
        
        import time
        last_error = ""
        for provider in order:
            for attempt in range(3):
                try:
                    client = get_client(provider)
                    resp = client.generate_json(system=system, user=f"Learn concept: {concept}", schema=schema)
                    
                    # 4. Save to Memory
                    self.store.save_learned_concept(c, resp)
                    
                    # Return uniform payload
                    return {
                        "concept": c,
                        "description": resp.get("description", ""),
                        "synonyms": resp.get("synonyms", []),
                        "table_hints": resp.get("table_hints", []),
                        "column_hints": resp.get("column_hints", {}),
                        "learned_at": "Just now (Auto-Learned)"
                    }
                except Exception as e:
                    last_error = str(e)
                    if "429" in str(e) and attempt < 2:
                        print(f"Provider {provider} rate limited in auto_learn_concept. Waiting 10s...")
                        time.sleep(10)
                        continue
                    break

        # Fallback on LLM failure
        return {
            "concept": c,
            "description": f"Failed to learn using LLM: {last_error}",
            "synonyms": [],
            "table_hints": [],
            "column_hints": {}
        }
