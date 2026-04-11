import streamlit as st
import pandas as pd
from app.agent import propose_sql
from app.db_mysql import get_mysql_conn

st.set_page_config(page_title="MySQL AI Agent", page_icon="🤖", layout="wide")

# Initialize session state for chat
if "messages" not in st.session_state:
    st.session_state.messages = []

def fetch_runs():
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT run_id, created_at FROM ai_agent_catalog.catalog_runs ORDER BY created_at DESC;")
    runs = cur.fetchall()
    cur.close()
    conn.close()
    return runs

def execute_query(sql: str) -> pd.DataFrame:
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        # Convert rows (list of dicts) into a DataFrame
        return pd.DataFrame(rows)
    finally:
        cur.close()
        conn.close()

# Sidebar: Run ID Selection
st.sidebar.title("Configuration")
runs = fetch_runs()
if not runs:
    st.sidebar.error("No catalog runs found. Please run the crawler and glossary builder first.")
    st.stop()

run_options = {f"{r['created_at']} ({r['run_id'][:8]}...)": r["run_id"] for r in runs}
selected_label = st.sidebar.selectbox("Active Catalog Version", list(run_options.keys()))
active_run_id = run_options[selected_label]

st.sidebar.markdown("---")
st.sidebar.info("This agent uses an offline catalog with Semantic Vector Embeddings.")

# Main Interface
st.title("🤖 MySQL Context AI Agent")
st.markdown("Ask natural language questions to query the `physician_portal` database cleanly and safely.")

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("data") is not None:
            st.dataframe(msg["data"], use_container_width=True)
        if "sql" in msg and msg["sql"]:
            with st.expander("View Agent Reasoning"):
                st.write(f"**Provider**: {msg.get('provider')}")
                st.write(f"**Confidence**: {msg.get('confidence')}")
                st.code(msg["sql"], language="sql")

# Chat Input
if prompt := st.chat_input("Ex: How many active patients do we have?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Analyzing request and building execution plan..."):
            try:
                # 1. Propose SQL
                response = propose_sql(active_run_id, prompt)
                
                sql_generated = response.get("sql")
                reply_text = "Here are the results:"
                
                if response.get("action") == "CLARIFY":
                    reply_text = response.get("clarification_question") or "I need more information to safely run this."
                elif response.get("action") == "ANSWER":
                    reply_text = response.get("answer") or "I processed your request but no SQL was generated."
                
                st.markdown(reply_text)
                
                df_results = None
                # 2. Execute SQL safely
                if sql_generated:
                    df_results = execute_query(sql_generated)
                    st.dataframe(df_results, use_container_width=True)
                
                # Render reasoning expander
                with st.expander("View Agent Reasoning"):
                    st.write(f"**Provider**: {response.get('provider_used')}")
                    st.write(f"**Confidence**: {response.get('confidence')}")
                    if sql_generated:
                        st.code(sql_generated, language="sql")
                    if response.get("debug") and response["debug"].get("error"):
                        st.error(f"Error Log: {response['debug']['error']}")

                # 3. Store in memory
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply_text,
                    "data": df_results,
                    "sql": sql_generated,
                    "provider": response.get("provider_used"),
                    "confidence": response.get("confidence")
                })
            except Exception as e:
                st.error(f"Error invoking agent: {str(e)}")
