import sys
import os
import json
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.router import plan_request, build_catalog_context
from app.db_mysql import get_mysql_conn
from app.catalog_store import CatalogStore

def debug():
    # Fetch run ID
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT run_id FROM ai_agent_catalog.catalog_runs ORDER BY created_at DESC LIMIT 1;")
    run_id = cur.fetchone()["run_id"]
    cur.close()
    conn.close()

    store = CatalogStore()
    cat = store.get_catalog(run_id)

    q = "How many patients we have today?"
    print(f"Testing Question: {q}")
    
    ctx = build_catalog_context(run_id, cat, q)
    print("\nCONTEXT SENT TO LLM:")
    # Pretty print just the table names and columns to ensure created_at is there
    for cand in ctx["candidates"]:
        print(f"Table: {cand['table']}")
        for hit in cand["hits"]:
            print(f"  - {hit['column']} ({hit['data_type']}) - sem: {hit['semantic']}")

    print("\nExecuting Plan Request...")
    plan = plan_request(question=q, catalog_ctx=ctx)
    print(f"\nProvider: {plan.provider_used}")
    print(f"Confidence: {plan.confidence}")
    print(f"Action: {plan.action}")
    print(f"SQL: {plan.sql}")
    print(f"Debug: {json.dumps(plan.debug, indent=2)}")

if __name__ == "__main__":
    debug()
