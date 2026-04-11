import os
import sys
from pprint import pprint

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.agent import propose_sql
from app.db_mysql import get_mysql_conn

def test_agent():
    # Fetch the latest run_id dynamically
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT run_id FROM ai_agent_catalog.catalog_runs ORDER BY created_at DESC LIMIT 1;")
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        print("No run_id found in catalog_runs!")
        return
    
    run_id = row["run_id"]
    print(f"Using Run ID: {run_id}")

    test_queries = [
        "How many total users are there?",
        "Show me all the cancelled appointments",
        "Who is the patient with ID 10?"
    ]

    for q in test_queries:
        print(f"\n======================================")
        print(f"QUESTION: {q}")
        print(f"======================================")
        result = propose_sql(run_id, q)
        print(f"PROVIDER: {result.get('provider_used')}")
        print(f"CONFIDENCE: {result.get('confidence')}")
        print(f"SQL GENERATED: {result.get('sql')}")
        if result.get('debug', {}).get('error'):
            print(f"ERROR: {result['debug']['error']}")

if __name__ == "__main__":
    test_agent()
