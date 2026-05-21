"""KPI -> reporting model (very pragmatic MVP)
This module proposes fact/dim candidates using heuristics:
- likely FACT: tables with datetime columns + numeric columns + many rows (if known)
- likely DIM: tables with mostly text + identifiers
- reference DIM: code sets like ICD9
"""
from app.config import settings
from app.catalog_store import CatalogStore
from app.retrieval import retrieve_candidates
from app.glossary import Glossary
from app.llm.factory import get_client
import json

def classify_table(run_id: str, schema: str, table: str) -> dict:
    store = CatalogStore()
    con = store._conn()
    cur = con.cursor()
    try:
        cur.execute(
            """SELECT data_type, column_name FROM `catalog_columns`
               WHERE run_id=%s AND schema_name=%s AND table_name=%s""",
            (run_id, schema, table),
        )
        cols = cur.fetchall()
        cur.execute(
            """SELECT row_count FROM `catalog_tables`
               WHERE run_id=%s AND schema_name=%s AND table_name=%s""",
            (run_id, schema, table),
        )
        row = cur.fetchone()
        row_count = row[0] if row else None
    finally:
        cur.close()
        con.close()

    dt_types = {"date", "datetime", "timestamp", "time", "year"}
    num_types = {"int", "bigint", "smallint", "tinyint", "decimal", "numeric", "float", "double"}
    text_types = {"varchar", "text", "char", "longtext", "mediumtext"}

    has_dt = any((t or "").lower() in dt_types for t, _ in cols)
    num_cnt = sum(1 for t, _ in cols if (t or "").lower() in num_types)
    text_cnt = sum(1 for t, _ in cols if (t or "").lower() in text_types)
    id_cnt = sum(1 for _, c in cols if c.lower().endswith("_id") or c.lower() in ("id","key"))

    # Heuristic scoring
    fact_score = (2 if has_dt else 0) + (2 if num_cnt >= 2 else 0) + (1 if (row_count or 0) > 10000 else 0)
    dim_score = (2 if text_cnt >= 3 else 0) + (1 if id_cnt >= 1 else 0) + (1 if not has_dt else 0)

    role = "UNKNOWN"
    if "icd" in table.lower():
        role = "DIM_REFERENCE"
    elif fact_score >= 3:
        role = "FACT_CANDIDATE"
    elif dim_score >= 3:
        role = "DIM_CANDIDATE"

    return {
        "schema": schema,
        "table": table,
        "row_count": row_count,
        "has_datetime": has_dt,
        "numeric_columns": num_cnt,
        "text_columns": text_cnt,
        "id_columns": id_cnt,
        "role": role,
        "scores": {"fact": fact_score, "dim": dim_score},
    }

def generate_semantic_model(kpi_text: str, facts: list, dims: list) -> str:
    """Uses the LLM to generate a minimal Cube.js YAML model based on the extracted tables."""
    try:
        preferred_llm = getattr(settings, "llm_prefer", "openai")
        order = [preferred_llm]
        for fallback in getattr(settings, "llm_fallback_order", ["gemini", "openai"]):
            if fallback not in order:
                order.append(fallback)
                
        system = (
            "You are a Data Engineering assistant. Your task is to generate a minimal Semantic Layer definition "
            "in Cube.js YAML format for the requested KPI using the provided Fact and Dimension tables. "
            "Return the valid YAML definition as a string inside the JSON object."
        )
        payload = {
            "requested_kpi": kpi_text,
            "fact_tables": [f["schema"] + "." + f["table"] for f in facts],
            "dimension_tables": [d["schema"] + "." + d["table"] for d in dims]
        }
        
        import time
        last_error = ""
        for provider in order:
            for attempt in range(3):
                try:
                    client = get_client(provider)
                    resp = client.generate_text(
                        system=system,
                        user=json.dumps(payload, ensure_ascii=False)
                    )
                    
                    # Strip potential markdown blocks if the LLM couldn't follow instructions perfectly
                    if resp.startswith("```yaml"):
                        resp = resp.replace("```yaml", "", 1)
                    elif resp.startswith("```"):
                        resp = resp.replace("```", "", 1)
                        
                    if resp.endswith("```"):
                        resp = resp[:-3]
                        
                    return resp.strip()
                except Exception as e:
                    last_error = str(e)
                    if "429" in str(e) and attempt < 2:
                        print(f"Provider {provider} rate limited. Waiting 10s...")
                        time.sleep(10)
                        continue
                    print(f"Provider {provider} failed in generate_semantic_model: {e}")
                    break
                
        return f"# Error generating semantic model:\n# All providers failed. Last error: {last_error}"
    except Exception as e:
        return f"# Error generating semantic model:\n# {str(e)}"

def kpi_to_model(run_id: str, kpi_text: str) -> dict:
    gl = Glossary(run_id)
    concept_hits = gl.find_concepts(kpi_text)
    
    if not concept_hits:
        # Autolearn the core KPI concept and use it
        learned = gl.auto_learn_concept(kpi_text)
        if learned.get("description"):
            concept_hits = [(kpi_text, learned)]
    
    candidates = retrieve_candidates(run_id, kpi_text, max_tables=10)

    chosen = []
    for c in candidates[:5]:
        s, t = c["table"].split(".", 1)
        chosen.append(classify_table(run_id, s, t))

    # propose a tiny star based on concept cues
    dims = []
    facts = []
    for x in chosen:
        if x["role"].startswith("FACT"):
            facts.append(x)
        elif x["role"].startswith("DIM"):
            dims.append(x)

    # If no fact detected but concept implies one (appointment/caremap), promote best candidate
    if not facts and candidates:
        s, t = candidates[0]["table"].split(".", 1)
        promoted = classify_table(run_id, s, t)
        promoted["role"] = "FACT_CANDIDATE"
        facts.append(promoted)

    yaml_model = generate_semantic_model(kpi_text, facts[:2], dims[:6])

    return {
        "kpi": kpi_text,
        "concept_hits": [{"concept": n, "description": p.get("description","")} for n, p in concept_hits],
        "candidate_tables": candidates[:5],
        "proposed_facts": facts[:2],
        "proposed_dimensions": dims[:6],
        "semantic_layer_model": yaml_model,
        "notes": [
            "MVP heuristics: improve by adding org-specific docs + synonyms.",
            "Next step: detect grain/measures/time columns and generate full fact/dim DDL."
        ],
        "confidence": 0.6 if facts else 0.35,
    }
