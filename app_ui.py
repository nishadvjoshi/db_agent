import streamlit as st
import pandas as pd
from app.agent import propose_sql
from app.db_mysql import get_mysql_conn, get_databases
from app.crawler import crawl_database
from app.profiler import profile_run
from app.catalog_store import CatalogStore
from app.llm.catalog_describer import CatalogDescriber
from scripts.embed_catalog import build_vector_index
from app.modeling import kpi_to_model

st.set_page_config(page_title="MySQL AI Agent", page_icon="🤖", layout="wide")

# Initialize session state for multi-screen navigation
if "current_screen" not in st.session_state:
    st.session_state.current_screen = "connections"
if "selected_db" not in st.session_state:
    st.session_state.selected_db = None
if "active_run_id" not in st.session_state:
    st.session_state.active_run_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

def fetch_runs():
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT run_id, created_at FROM ai_agent_catalog.catalog_runs ORDER BY created_at DESC;")
        runs = cur.fetchall()
        return runs
    except Exception:
        return []
    finally:
        cur.close()
        conn.close()

def fetch_runs_for_db(db_name: str):
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT r.run_id, r.created_at 
            FROM ai_agent_catalog.catalog_runs r
            JOIN ai_agent_catalog.catalog_schemas s ON r.run_id = s.run_id
            WHERE s.schema_name = %s
            ORDER BY r.created_at DESC
            """, (db_name,)
        )
        runs = cur.fetchall()
        return runs
    except Exception:
        return []
    finally:
        cur.close()
        conn.close()

def fetch_phi_columns(run_id: str) -> pd.DataFrame:
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """
            SELECT schema_name as Database_Name, table_name as Table_Name, 
                   column_name as Column_Name, inferred_semantic_type as PHI_Type
            FROM ai_agent_catalog.catalog_profiles
            WHERE run_id = %s AND inferred_semantic_type LIKE 'PHI_%'
            ORDER BY schema_name, table_name, column_name
            """, (run_id,)
        )
        rows = cur.fetchall()
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()
    finally:
        cur.close()
        conn.close()

def execute_query(sql: str) -> pd.DataFrame:
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(sql)
        rows = cur.fetchall()
        return pd.DataFrame(rows)
    finally:
        cur.close()
        conn.close()

# Sidebar Navigation
st.sidebar.title("Navigation")
if st.sidebar.button("🔌 Connections"):
    st.session_state.current_screen = "connections"
    st.rerun()
if st.sidebar.button("💬 Agent Chat"):
    st.session_state.current_screen = "chat"
    st.rerun()
if st.sidebar.button("📊 Data Modeler"):
    st.session_state.current_screen = "modeler"
    st.rerun()
if st.sidebar.button("🛡️ PHI Dashboard"):
    st.session_state.current_screen = "phi_dashboard"
    st.rerun()

runs = fetch_runs()
if runs:
    run_options = {f"{r['created_at']} ({r['run_id'][:8]}...)": r["run_id"] for r in runs}
    selected_label = st.sidebar.selectbox("Active Catalog Version", list(run_options.keys()))
    st.session_state.active_run_id = run_options[selected_label]
else:
    st.sidebar.warning("No catalog runs found. Please connect and crawl a database.")

st.sidebar.markdown("---")
st.sidebar.info("This agent uses an offline catalog with Semantic Vector Embeddings.")

# Screen 1: Connections
def render_connections_screen():
    st.title("🔌 Database Connections")
    st.markdown("Select a database connection to analyze and build its AI Data Catalog.")
    
    try:
        dbs = get_databases()
    except Exception as e:
        st.error(f"Could not fetch databases: {e}")
        return

    if not dbs:
        st.warning("No databases found on the configured MySQL server.")
        return
    
    cols = st.columns(3)
    for idx, db_info in enumerate(dbs):
        with cols[idx % 3]:
            st.markdown(f"### 🗄️ {db_info['name']}")
            st.markdown(f"**Tables**: {db_info['table_count']}")
            if st.button("Connect & Analyze", key=f"btn_{db_info['name']}"):
                st.session_state.selected_db = db_info['name']
                st.session_state.current_screen = "connection_details"
                st.rerun()

# Screen 1.5: Connection Details / Run History
def render_connection_details_screen():
    db_name = st.session_state.selected_db
    st.title(f"🗄️ Database: {db_name}")
    st.markdown("View previous catalog runs or start a new analysis.")
    
    if st.button("🚀 Start New Analysis", type="primary"):
        st.session_state.current_screen = "crawling"
        st.rerun()
        
    st.markdown("### Previous Runs")
    runs = fetch_runs_for_db(db_name)
    if not runs:
        st.info("No previous analysis runs found for this database.")
    else:
        for r in runs:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**Run ID**: `{r['run_id']}`")
                st.write(f"**Created At**: {r['created_at']}")
            with col2:
                if st.button("Activate Run", key=f"act_{r['run_id']}"):
                    st.session_state.active_run_id = r['run_id']
                    st.session_state.current_screen = "chat"
                    st.success(f"Activated run {r['run_id'][:8]}")
                    st.rerun()
            st.markdown("---")

# Screen 2: Crawling Progress
def render_crawling_screen():
    db_name = st.session_state.selected_db
    st.title(f"🔍 Analyzing Database: {db_name}")
    st.markdown("Please wait while the system extracts metadata, profiles data for PHI, generates AI descriptions, and builds the semantic vector index.")
    
    # We use st.status for interactive progress
    with st.status("Building AI Data Catalog...", expanded=True) as status:
        try:
            st.write("1️⃣ Crawling database schema...")
            run_id = crawl_database(include_schemas=[db_name])
            st.session_state.active_run_id = run_id
            
            st.write(f"2️⃣ Profiling sensitive data and PHI for run {run_id}...")
            profile_run(run_id, schemas=[db_name])
            
            st.write("3️⃣ Generating AI descriptions for tables and columns...")
            store = CatalogStore()
            catalog = store.get_catalog(run_id)
            describer = CatalogDescriber()
            schemas = catalog.get("schemas", [])
            for s in schemas:
                s_name = s.get("name")
                for t in s.get("tables", []):
                    t_name = t.get("name")
                    st.write(f"  - Describing table {s_name}.{t_name}...")
                    desc, llm_name = describer.generate_table_description(s_name, t_name, t.get("columns", []))
                    store.upsert_catalog_description(run_id, s_name, t_name, "", desc, llm_name)
                    
                    for c in t.get("columns", []):
                        c_name = c.get("name")
                        c_desc, c_llm = describer.generate_column_description(s_name, t_name, c_name, c.get("data_type"))
                        store.upsert_catalog_description(run_id, s_name, t_name, c_name, c_desc, c_llm)
            
            st.write("4️⃣ Embedding catalog into Vector Database (ChromaDB)...")
            build_vector_index(run_id)
            
            status.update(label="Catalog built successfully!", state="complete", expanded=False)
            st.success("✅ Analysis Complete! You can now chat with the database or use the Data Modeler.")
            
            if st.button("Go to Chat"):
                st.session_state.current_screen = "chat"
                st.rerun()
                
        except Exception as e:
            status.update(label="Error during analysis", state="error")
            st.error(f"Analysis failed: {str(e)}")

# Screen 3: Chat Interface
def render_chat_screen():
    st.title("💬 Agent Chat")
    st.markdown("Ask natural language questions to query the database cleanly and safely.")
    
    if not st.session_state.active_run_id:
        st.warning("Please select an active catalog run from the sidebar or connect to a database first.")
        return

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("data") is not None and not msg["data"].empty:
                st.dataframe(msg["data"], use_container_width=True)
            if msg.get("chart_fig"):
                st.plotly_chart(msg["chart_fig"], use_container_width=True)
            if "sql" in msg and msg["sql"]:
                with st.expander("View Agent Reasoning"):
                    st.write(f"**Provider**: {msg.get('provider')}")
                    st.write(f"**Confidence**: {msg.get('confidence')}")
                    st.code(msg["sql"], language="sql")

    if prompt := st.chat_input("Ex: How many active patients do we have?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing request and building execution plan..."):
                try:
                    response = propose_sql(st.session_state.active_run_id, prompt)
                    sql_generated = response.get("sql")
                    reply_text = "Here are the results:"
                    
                    if response.get("action") == "CLARIFY":
                        reply_text = response.get("clarification_question") or "I need more information to safely run this."
                    elif response.get("action") == "ANSWER":
                        reply_text = response.get("answer") or "I processed your request but no SQL was generated."
                    
                    st.markdown(reply_text)
                    
                    df_results = None
                    fig = None
                    chart_code = None
                    
                    if sql_generated:
                        df_results = execute_query(sql_generated)
                        if not df_results.empty:
                            st.dataframe(df_results, use_container_width=True)
                            
                            from app.visualization import generate_chart_code
                            chart_code = generate_chart_code(df_results, prompt, provider=response.get("provider_used", "local"))
                            if chart_code:
                                try:
                                    import plotly.express as px
                                    import plotly.graph_objects as go
                                    local_vars = {"df": df_results, "px": px, "go": go, "fig": None}
                                    exec(chart_code, {}, local_vars)
                                    fig = local_vars.get("fig")
                                    if fig:
                                        st.plotly_chart(fig, use_container_width=True)
                                except Exception as e:
                                    st.error(f"Chart code failed to execute visually: {e}\n\nCode:\n{chart_code}")

                    with st.expander("View Agent Reasoning"):
                        st.write(f"**Provider**: {response.get('provider_used')}")
                        st.write(f"**Confidence**: {response.get('confidence')}")
                        if response.get("chain_of_thought"):
                            st.write(f"**Chain of Thought**:\n{response.get('chain_of_thought')}")
                        if sql_generated:
                            st.code(sql_generated, language="sql")
                        if chart_code:
                            st.code(chart_code, language="python")
                        if response.get("execution_errors"):
                            for i, err in enumerate(response["execution_errors"]):
                                st.warning(f"Self-Correction Loop #{i+1}:\n{err}")
                        if response.get("debug") and response["debug"].get("error"):
                            st.error(f"Error Log: {response['debug']['error']}")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": reply_text,
                        "data": df_results,
                        "chart_fig": fig,
                        "sql": sql_generated,
                        "provider": response.get("provider_used"),
                        "confidence": response.get("confidence")
                    })
                except Exception as e:
                    st.error(f"Error invoking agent: {str(e)}")


# Screen 4: Data Modeler
def render_modeler_screen():
    st.title("📊 Data Modeler")
    st.markdown("Generate semantic data models and visualize entity relationships based on captured metadata.")
    
    if not st.session_state.active_run_id:
        st.warning("Please select an active catalog run from the sidebar first.")
        return
        
    kpi_text = st.text_input("Enter a Reporting Requirement or KPI (e.g., 'monthly patient appointments'):")
    if st.button("Generate Data Model"):
        if kpi_text:
            with st.spinner("Analyzing metadata and proposing star schema..."):
                try:
                    model_res = kpi_to_model(st.session_state.active_run_id, kpi_text)
                    
                    st.subheader("Model Generation Results")
                    
                    tab1, tab2, tab3 = st.tabs(["🏗️ Architecture Diagram", "🗂️ Proposed Entities", "📝 Cube.js Semantic Layer"])
                    
                    with tab1:
                        # Build Mermaid Diagram
                        mermaid_code = "erDiagram\n"
                        facts = model_res.get("proposed_facts", [])
                        dims = model_res.get("proposed_dimensions", [])
                        
                        for f in facts:
                            f_name = f['table']
                            mermaid_code += f"    {f_name} {{\n        int id PK\n        string role \"FACT\"\n    }}\n"
                            for d in dims:
                                d_name = d['table']
                                mermaid_code += f"    {f_name} ||--o{{ {d_name} : references\n"
                                
                        for d in dims:
                            d_name = d['table']
                            mermaid_code += f"    {d_name} {{\n        int id PK\n        string role \"DIM\"\n    }}\n"
                        
                        # Render visually using an HTML component with Mermaid JS
                        import streamlit.components.v1 as components
                        mermaid_html = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <script type="module">
                            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
                            mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
                            </script>
                        </head>
                        <body>
                            <pre class="mermaid" style="display: flex; justify-content: center; margin-top: 20px;">
{mermaid_code}
                            </pre>
                        </body>
                        </html>
                        """
                        components.html(mermaid_html, height=450, scrolling=True)
                    
                    with tab2:
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("### 📈 Proposed Facts")
                            if facts:
                                st.dataframe([{"Schema": f["schema"], "Table": f["table"], "Score": f["scores"]["fact"]} for f in facts], use_container_width=True)
                            else:
                                st.write("No fact tables identified.")
                        
                        with col2:
                            st.markdown("### 🧩 Proposed Dimensions")
                            if dims:
                                st.dataframe([{"Schema": d["schema"], "Table": d["table"], "Score": d["scores"]["dim"]} for d in dims], use_container_width=True)
                            else:
                                st.write("No dimension tables identified.")
                    
                    with tab3:
                        st.code(model_res.get("semantic_layer_model", ""), language="yaml")
                    
                except Exception as e:
                    st.error(f"Error generating model: {str(e)}")
        else:
            st.warning("Please enter a reporting requirement first.")

# Screen 5: PHI Dashboard
def render_phi_screen():
    st.title("🛡️ PHI Dashboard")
    st.markdown("Review all Protected Health Information (PHI) columns identified by the Presidio NLP profiler.")
    
    if not st.session_state.active_run_id:
        st.warning("Please select an active catalog run from the sidebar first.")
        return
        
    df = fetch_phi_columns(st.session_state.active_run_id)
    if df.empty:
        st.info("No PHI columns found in this catalog run.")
        return
        
    col1, col2, col3 = st.columns(3)
    with col1:
        db_search = st.text_input("Search Database", value="")
    with col2:
        table_search = st.text_input("Search Table", value="")
    with col3:
        col_search = st.text_input("Search Column", value="")
        
    filtered_df = df.copy()
    if db_search:
        filtered_df = filtered_df[filtered_df['Database_Name'].str.contains(db_search, case=False, na=False)]
    if table_search:
        filtered_df = filtered_df[filtered_df['Table_Name'].str.contains(table_search, case=False, na=False)]
    if col_search:
        filtered_df = filtered_df[filtered_df['Column_Name'].str.contains(col_search, case=False, na=False)]
        
    st.markdown(f"**Found {len(filtered_df)} PHI Columns**")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

# Main Router
if st.session_state.current_screen == "connections":
    render_connections_screen()
elif st.session_state.current_screen == "connection_details":
    render_connection_details_screen()
elif st.session_state.current_screen == "crawling":
    render_crawling_screen()
elif st.session_state.current_screen == "chat":
    render_chat_screen()
elif st.session_state.current_screen == "modeler":
    render_modeler_screen()
elif st.session_state.current_screen == "phi_dashboard":
    render_phi_screen()
