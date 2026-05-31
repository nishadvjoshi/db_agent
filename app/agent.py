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
        
        target_params = {
            "host": settings.target_db_host,
            "port": settings.target_db_port,
            "user": settings.target_db_user,
            "password": settings.target_db_password,
            "database": settings.target_db_name,
        }
        target_params = {k: v for k, v in target_params.items() if v}
        from app.adapters.factory import get_adapter
        adapter = get_adapter(settings.target_db_type, target_params)

        max_retries = 3
        previous_errors = []
        plan = None
        
        history_records = store.get_chat_history(run_id)
        chat_history = [{"role": r["role"], "content": r["content"]} for r in history_records[-6:]] if history_records else []
        
        for attempt in range(max_retries):
            plan = plan_request(
                question=question, 
                catalog_ctx=catalog_ctx, 
                glossary_ctx=glossary,
                previous_errors=previous_errors,
                chat_history=chat_history
            )
            
            if plan.action == "SQL" and plan.sql:
                try:
                    # Dry-run validation
                    if settings.target_db_type != "sqlserver":
                        adapter.execute_query(f"EXPLAIN {plan.sql}")
                    break # SQL is valid!
                except Exception as db_err:
                    err_msg = str(db_err)
                    previous_errors.append(f"Attempt {attempt+1} generated invalid SQL: {plan.sql}\nDatabase Error: {err_msg}")
                    continue
            else:
                if previous_errors and attempt > 0:
                    if not plan.debug:
                        plan.debug = {}
                    plan.debug["error"] = f"Failed to auto-correct SQL. Internal error: {plan.debug.get('error', '')}"
                break # Non-SQL action or empty SQL, just break

        if not plan:
            raise ValueError("All planner retries failed.")

        return {
            "question": question,
            "provider_used": plan.provider_used,
            "confidence": plan.confidence,
            "detected_intent": plan.intent,
            "action": plan.action,
            "candidate_tables": catalog_ctx.get("candidates", []),
            "chain_of_thought": plan.chain_of_thought,
            "sql": plan.sql,
            "answer": plan.answer,
            "used_tables": plan.used_tables or [],
            "needs_clarification": plan.needs_clarification,
            "clarification_question": plan.clarification_question,
            "debug": plan.debug or {},
            "execution_errors": previous_errors,
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
