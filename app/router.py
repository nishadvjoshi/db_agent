"""LLM-first planning router.

Goal
----
The *local* LLM (Ollama) should do the heavy lifting for every request.

Flow
----
1) Build a compact "catalog context" from the crawled DB metadata.
2) Ask the LOCAL LLM to produce a **JSON plan**.
3) Validate/guardrail the plan (SQL safety, table existence, etc.).
4) If local plan is low-confidence or invalid, fall back to OpenAI/Gemini.

This file intentionally keeps routing/planning concerns separate from execution.
Execution (running SQL, returning results) remains in app/agent.py and app/api.py.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.config import settings
from app.llm.factory import get_client
from app.retrieval import retrieve_candidates
from app.sql_guardrails import is_safe_sql, check_phi_safety


@dataclass
class Plan:
    """Normalized plan used by the agent."""

    ok: bool
    provider_used: str
    confidence: float
    intent: str
    action: str
    chain_of_thought: Optional[str] = None
    sql: Optional[str] = None
    answer: Optional[str] = None
    used_tables: Optional[List[str]] = None
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    debug: Optional[Dict[str, Any]] = None


def build_catalog_context(run_id: str, catalog: Dict[str, Any], question: str, *, top_k: int = 6) -> Dict[str, Any]:
    """Compact context: schema list + top-K relevant tables/columns + edges.

    In this project, candidate retrieval is backed by the centralized MySQL catalog store,
    so we need the run_id.
    """

    candidates = retrieve_candidates(run_id, question, max_tables=top_k)
    schema_names = [s.get("name") for s in (catalog.get("schemas") or []) if s.get("name")]
    
    # Inject few-shot complex SQL examples to guide the LLM
    from app.few_shot import get_few_shot_examples
    examples = get_few_shot_examples()

    return {
        "schemas": schema_names,
        "candidates": candidates,
        "edges": catalog.get("edges") or [],
        "few_shot_examples": examples,
    }


def plan_request(
    *,
    question: str,
    catalog_ctx: Dict[str, Any],
    glossary_ctx: Optional[Dict[str, Any]] = None,
    previous_errors: Optional[List[str]] = None,
) -> Plan:
    """LLM-first planner.

    Always tries local first. If local fails (invalid JSON / unsafe SQL / low confidence),
    falls back to OpenAI/Gemini **only if** corresponding API keys are configured.
    """

    providers = _provider_order()
    last_err: Optional[str] = None

    for provider in providers:
        try:
            raw = _call_planner_llm(
                provider=provider,
                question=question,
                catalog_ctx=catalog_ctx,
                glossary_ctx=glossary_ctx,
                previous_errors=previous_errors,
            )
            plan = _normalize_plan(raw, provider_used=provider)

            # Guardrails for any SQL plans
            if plan.sql:
                ok, reason = is_safe_sql(plan.sql)
                if not ok:
                    raise ValueError(f"SQL rejected: {reason}")
                
                # Check for sensitive PHI columns
                phi_ok, phi_reason = check_phi_safety(plan.sql, catalog_ctx)
                if not phi_ok:
                    raise ValueError(phi_reason)
                    
                bad_tables = _unknown_tables(plan.sql, catalog_ctx)
                if bad_tables:
                    raise ValueError(f"Unknown tables referenced: {bad_tables}")

            # Confidence threshold
            threshold = 0.50
            if plan.needs_clarification or plan.confidence >= threshold:
                return plan

            raise ValueError(f"Low confidence plan ({plan.confidence:.2f})")

        except Exception as e:
            last_err = str(e)
            continue

    return Plan(
        ok=False,
        provider_used="none",
        confidence=0.0,
        intent="UNKNOWN",
        action="CLARIFY",
        needs_clarification=True,
        clarification_question="I couldn't confidently plan this. Can you mention a table/column or rephrase?",
        debug={"error": last_err},
    )


def _provider_order() -> List[str]:
    preferred_llm = getattr(settings, "llm_prefer", "openai")
    order = [preferred_llm]
    for fallback in getattr(settings, "llm_fallback_order", ["gemini", "openai"]):
        if fallback not in order:
            order.append(fallback)
    return order


def _call_planner_llm(
    *,
    provider: str,
    question: str,
    catalog_ctx: Dict[str, Any],
    glossary_ctx: Optional[Dict[str, Any]],
    previous_errors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    client = get_client(provider)

    from datetime import datetime
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    system = (
        f"You are a backend PLANNING agent for Augmented BI. Today's Date is {current_date} and current time is {current_time}. "
        "You must output ONLY valid JSON. "
        "Use database metadata (schemas/tables/columns/relationships) and healthcare glossary when helpful. "
        "CRITICAL: Produce a 'chain_of_thought' mapping out the steps (Joins, CTEs) needed BEFORE drafting the SQL. "
        "CRITICAL PRIVACY RULE: Do NOT `SELECT` any columns in your SQL queries where the 'inferred_semantic_type' starts with 'PHI_'. You may use them in `WHERE` clauses for filtering context (e.g. filtering by date), but you cannot return their values. "
        "If the user explicitly asks to view 'PHI_' columns, you MUST refuse and set action='CLARIFY' with an explanation. "
        "If SQL is needed, output a READ-ONLY SELECT query with LIMIT 50. "
        "If previous SQL executions failed, review the 'previous_errors' and fix the syntax or table references."
        "If the question is about metadata, answer directly without SQL. "
        "If unsure, set needs_clarification=true and ask ONE short clarification question."
    )

    payload = {
        "question": question,
        "catalog": catalog_ctx,
        "glossary": glossary_ctx or {},
        "previous_errors": previous_errors or [],
        "rules": {
            "sql": {
                "read_only": True,
                "limit": 50,
                "no_ddl_dml": True,
                "use_backticks_for_identifiers": True,
            }
        },
        "output_schema": {
            "ok": "boolean",
            "confidence": "number 0..1",
            "intent": "string",
            "action": "SQL|ANSWER|CLARIFY",
            "chain_of_thought": "string|null",
            "sql": "string|null",
            "answer": "string|null",
            "used_tables": "array[string]",
            "needs_clarification": "boolean",
            "clarification_question": "string|null",
        },
    }

    import time
    for attempt in range(3):
        try:
            resp = client.generate_json(
                system=system,
                user=json.dumps(payload, ensure_ascii=False),
                schema=payload["output_schema"]
            )
            if isinstance(resp, dict):
                return resp
            if isinstance(resp, str):
                return json.loads(_extract_json(resp))
            raise ValueError(f"Unexpected LLM response type: {type(resp)}")
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                print(f"Provider {provider} rate limited in Agent Chat. Waiting 10s...")
                time.sleep(10)
                continue
            raise


def _normalize_plan(raw: Dict[str, Any], *, provider_used: str) -> Plan:
    ok = bool(raw.get("ok", True))
    confidence = float(raw.get("confidence", 0.5) or 0.5)
    intent = str(raw.get("intent") or "UNKNOWN")
    action = str(raw.get("action") or "ANSWER").upper()
    chain_of_thought = raw.get("chain_of_thought")

    sql = raw.get("sql")
    answer = raw.get("answer")
    used_tables = raw.get("used_tables") or []

    needs_clarification = bool(raw.get("needs_clarification", False))
    clarification_question = raw.get("clarification_question")

    if sql is not None:
        sql = str(sql).strip()
        if sql.startswith("```"):
            lines = sql.split("\n")
            if len(lines) > 1:
                sql = "\n".join(lines[1:])
        sql = sql.replace("```", "").strip() or None
    if answer is not None:
        answer = str(answer).strip() or None

    # Ignore hallucinated SQL if the action isn't executing a query
    if action != "SQL":
        sql = None

    # Enforce LIMIT if missing.
    if sql and re.search(r"\blimit\b", sql, flags=re.IGNORECASE) is None:
        sql = sql.rstrip("; ") + " LIMIT 50;"

    debug = {k: v for k, v in raw.items() if k not in {"ok", "confidence", "intent", "action", "sql", "answer", "used_tables", "needs_clarification", "clarification_question"}}

    return Plan(
        ok=ok,
        provider_used=provider_used,
        confidence=max(0.0, min(1.0, confidence)),
        intent=intent,
        action=action,
        chain_of_thought=chain_of_thought,
        sql=sql,
        answer=answer,
        used_tables=used_tables,
        needs_clarification=needs_clarification,
        clarification_question=clarification_question,
        debug=debug or None,
    )


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON found")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    raise ValueError("Unbalanced JSON")


def _unknown_tables(sql: str, catalog_ctx: Dict[str, Any]) -> List[str]:
    known = set()
    for c in (catalog_ctx.get("candidates") or []):
        t = c.get("table")
        if t:
            known.add(str(t).lower())

    schemas = set([s.lower() for s in (catalog_ctx.get("schemas") or []) if s])

    # heuristic parsing: FROM `schema`.`table` and JOIN `schema`.`table`
    refs = re.findall(r"\b(?:from|join)\s+`?([\w]+)`?\.`?([\w]+)`?", sql, flags=re.IGNORECASE)
    bad: List[str] = []
    for schema, table in refs:
        full = f"{schema}.{table}".lower()
        if schema.lower() in schemas and full not in known:
            bad.append(full)
    return bad
