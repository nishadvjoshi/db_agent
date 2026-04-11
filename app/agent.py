from app.catalog_store import CatalogStore
from app.retrieval import retrieve_candidates
from app.graph import build_graph, shortest_join_path
from app.sql_guardrails import is_safe_sql, enforce_limit
from app.config import settings
from app.router import build_catalog_context, plan_request
from app.glossary import Glossary

def _pick_datetime_column(hits: list[dict]) -> str | None:
    # Prefer columns that look like appointment/scheduled/start datetime
    prefs = ("appt", "appoint", "schedule", "scheduled", "start", "visit", "encounter", "time", "dt", "date")
    datetime_hits = [h for h in hits if (h.get("semantic") == "date" or (h.get("data_type") or "").lower() in ("date","datetime","timestamp"))]
    if not datetime_hits:
        return None
    datetime_hits.sort(key=lambda h: sum(1 for p in prefs if p in h["column"].lower()), reverse=True)
    return datetime_hits[0]["column"]

def _pick_status_column(hits: list[dict]) -> str | None:
    status_hits = [h for h in hits if (h.get("semantic") == "status" or "status" in h["column"].lower() or "state" in h["column"].lower())]
    return status_hits[0]["column"] if status_hits else None

def explain_concept(run_id: str, concept: str):
    gl = Glossary(run_id)
    payload = gl.get_concept(concept)
    if not payload:
        # try to match by synonyms
        hits = gl.find_concepts(concept)
        if hits:
            payload = hits[0][1]
        else:
            # Auto-Learn unknown concepts on the fly using the multi-LLM pipeline
            payload = gl.auto_learn_concept(concept)
    candidates = retrieve_candidates(run_id, concept, max_tables=10)

    return {
        "concept": concept,
        "glossary": payload,
        "candidate_tables": candidates[:7],
        "notes": [
            "Glossary gives domain meaning; candidates are matched against actual schema.",
            "Add your data dictionary and refine hints for higher accuracy."
        ],
    }

def propose_sql(run_id: str, question: str, context: dict | None = None):
    """LLM-first planner for the /ask endpoint.

    The local LLM (Ollama) is always attempted first.
    If it cannot produce a safe/high-confidence plan, we fall back to a
    heuristic plan (and optionally OpenAI/Gemini via the router).
    """

    context = context or {}
    store = CatalogStore()
    catalog = store.get_catalog(run_id)
    glossary = context.get("glossary")

    # --- LLM-first ---
    try:
        catalog_ctx = build_catalog_context(run_id, catalog, question, top_k=6)
        plan = plan_request(question=question, catalog_ctx=catalog_ctx, glossary_ctx=glossary)
        return {
            "question": question,
            "provider_used": plan.provider_used,
            "confidence": plan.confidence,
            "detected_intent": plan.intent,
            "action": plan.action,
            "candidate_tables": catalog_ctx.get("candidates", []),
            "sql": plan.sql,
            "answer": plan.answer,
            "used_tables": plan.used_tables or [],
            "needs_clarification": plan.needs_clarification,
            "clarification_question": plan.clarification_question,
            "debug": plan.debug or {},
        }
    except Exception as e:
        # --- Safe fallback: legacy heuristic ---
        candidates = retrieve_candidates(run_id, question)
        chosen_tables = [c["table"] for c in candidates[:1]]
        sql = None
        if chosen_tables:
            sch, tbl = chosen_tables[0].split(".", 1)
            sql = enforce_limit(f"SELECT * FROM `{sch}`.`{tbl}`", settings.force_limit)

        return {
            "question": question,
            "provider_used": "heuristic",
            "confidence": 0.25,
            "detected_intent": "UNKNOWN",
            "action": "SQL" if sql else "CLARIFY",
            "candidate_tables": candidates[:5],
            "sql": sql or "SELECT 1;",
            "answer": None,
            "used_tables": chosen_tables,
            "needs_clarification": sql is None,
            "clarification_question": "Which schema/table should I use?" if sql is None else None,
            "debug": {"error": str(e)},
        }
