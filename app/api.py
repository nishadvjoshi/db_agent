from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.crawler import crawl_database
from app.agent import propose_sql, explain_concept
from app.modeling import kpi_to_model, classify_table
from app.db_mysql import get_databases, get_mysql_conn
from app.catalog_store import CatalogStore
from app.llm.catalog_describer import CatalogDescriber
from scripts.embed_catalog import build_vector_index
from app.edw_designer import propose_edw_themes, generate_edw_blueprint, generate_edw_ddl

from app.api_ddd import router as ddd_router

app = FastAPI(title="MySQL Context Agent (MVP)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ddd_router)

class CrawlRequest(BaseModel):
    conn_id: Optional[str] = None
    include_schemas: Optional[List[str]] = None
    exclude_schemas: Optional[List[str]] = None
    run_profiler: bool = False
    run_describer: bool = False

class ConnectionRequest(BaseModel):
    name: str
    db_type: str
    host: str
    port: int
    username: str
    password: str
    database_name: str

class AskRequest(BaseModel):
    run_id: str
    question: str
    context: Optional[Dict] = None

class QueryRequest(BaseModel):
    sql: str

class ExplainConceptRequest(BaseModel):
    run_id: str
    concept: str

class KPIModelRequest(BaseModel):
    run_id: str
    kpi: str
    
class BlueprintRequest(BaseModel):
    run_id: str
    user_req: str
    user_config: List[Dict[str, Any]]

class DDLDeployRequest(BaseModel):
    ddl: str
    conn_id: str
    warehouse_name: str

class ChatMessage(BaseModel):
    run_id: str
    role: str
    content: str
    sql_query: Optional[str] = None
    data_json: Optional[str] = None
    provider: Optional[str] = None
    confidence: Optional[str] = None

@app.get("/api/databases")
def get_all_databases():
    return {"databases": get_databases()}

@app.get("/api/connections")
def get_connections():
    store = CatalogStore()
    return {"connections": store.get_connections()}

@app.post("/api/connections")
def create_connection(req: ConnectionRequest):
    import uuid
    store = CatalogStore()
    conn_id = str(uuid.uuid4())
    store.save_connection(conn_id, req.dict())
    return {"connection_id": conn_id, "status": "success"}

@app.get("/api/runs/{run_id}/logs")
def get_logs(run_id: str):
    store = CatalogStore()
    return {"logs": store.get_run_logs(run_id)}

@app.get("/api/runs")
def get_all_runs():
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT run_id, created_at FROM ai_agent_catalog.catalog_runs ORDER BY created_at DESC;")
        return {"runs": cur.fetchall()}
    finally:
        cur.close()
        conn.close()

@app.get("/api/runs/{db_name}")
def get_runs_for_db(db_name: str):
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
        return {"runs": cur.fetchall()}
    finally:
        cur.close()
        conn.close()

@app.post("/api/analyze")
def analyze(req: CrawlRequest):
    from app.background_runner import start_background_analysis
    run_id = start_background_analysis(req.conn_id, req.include_schemas)
    return {"run_id": run_id, "status": "started"}

@app.get("/api/runs/{run_id}/phi")
def get_phi_columns(run_id: str):
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
        return {"phi_columns": cur.fetchall()}
    finally:
        cur.close()
        conn.close()

@app.post("/api/query/execute")
def execute_sql(req: QueryRequest):
    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(req.sql)
        rows = cur.fetchall()
        return {"rows": rows}
    except Exception as e:
        return {"error": str(e)}
    finally:
        cur.close()
        conn.close()

@app.post("/api/ask")
def ask(req: AskRequest):
    return propose_sql(req.run_id, req.question, context=req.context or {})

@app.post("/api/explain-concept")
def explain(req: ExplainConceptRequest):
    return explain_concept(req.run_id, req.concept)

@app.post("/api/kpi-to-model")
def model(req: KPIModelRequest):
    return kpi_to_model(req.run_id, req.kpi)

@app.get("/api/edw/themes/{run_id}")
def get_edw_themes(run_id: str):
    return {"themes": propose_edw_themes(run_id)}

@app.get("/api/edw/config/{run_id}")
def get_edw_config(run_id: str):
    store = CatalogStore()
    config = store.load_edw_config(run_id)
    
    con = store._conn()
    cur = con.cursor(dictionary=True)
    try:
        if not config:
            cur.execute("SELECT schema_name, table_name FROM catalog_tables WHERE run_id=%s", (run_id,))
            tables = cur.fetchall()
            config = []
            for t in tables:
                classification = classify_table(run_id, t["schema_name"], t["table_name"])
                guessed_role = "Fact" if "FACT" in classification.get("role", "") else "Dimension"
                config.append({
                    "table_name": t["table_name"],
                    "is_included": True,
                    "table_role": guessed_role,
                    "scd_type": "Type 2",
                    "type_3_columns": ""
                })
        
        cur.execute("SELECT table_name, column_name FROM catalog_columns WHERE run_id=%s", (run_id,))
        cols = cur.fetchall()
        col_map = {}
        for c in cols:
            col_map.setdefault(c["table_name"], []).append(c["column_name"])
            
        return {"config": config, "table_columns": col_map}
    finally:
        cur.close()
        con.close()

@app.post("/api/edw/blueprint")
def generate_blueprint(req: BlueprintRequest):
    store = CatalogStore()
    store.save_edw_config(req.run_id, req.user_config)
    bp = generate_edw_blueprint(req.run_id, req.user_req, user_config=req.user_config)
    if bp:
        ddl = generate_edw_ddl(bp)
        return {"blueprint": bp, "ddl": ddl}
    return {"error": "Failed to generate blueprint"}

@app.post("/api/edw/ddl/deploy")
def deploy_ddl(req: DDLDeployRequest):
    from app.catalog_store import CatalogStore
    from app.adapters.factory import get_adapter
    
    store = CatalogStore()
    conn_data = store.get_connection(req.conn_id)
    if not conn_data:
        return {"success": False, "error": "Connection not found"}
        
    db_type = conn_data.get("db_type", "mysql").lower()
    target_params = {
        "host": conn_data.get("host"),
        "port": conn_data.get("port"),
        "user": conn_data.get("username"),
        "password": conn_data.get("password"),
        "database": conn_data.get("database_name"),
    }
    target_params = {k: v for k, v in target_params.items() if v}
    adapter = get_adapter(db_type, target_params)
    
    try:
        statements = [s.strip() for s in req.ddl.split(';') if s.strip()]
        
        if db_type == "mysql":
            import mysql.connector
            conn = mysql.connector.connect(**target_params)
            cur = conn.cursor()
            try:
                cur.execute(f"CREATE DATABASE IF NOT EXISTS `{req.warehouse_name}`")
                cur.execute(f"USE `{req.warehouse_name}`")
                for stmt in statements:
                    if stmt:
                        cur.execute(stmt)
                conn.commit()
            finally:
                cur.close()
                conn.close()
        else:
            # Basic fallback for Redshift / SQL Server
            statements = [s.strip() for s in req.ddl.split(';') if s.strip()]
            if db_type == "sqlserver":
                import pymssql
                conn = pymssql.connect(**target_params)
            else:
                import psycopg2
                conn = psycopg2.connect(**target_params)
            
            cur = conn.cursor()
            try:
                if db_type == "redshift":
                    try:
                        cur.execute(f"CREATE SCHEMA IF NOT EXISTS {req.warehouse_name}")
                    except Exception:
                        pass
                    cur.execute(f"SET search_path TO {req.warehouse_name}")
                    
                for stmt in statements:
                    if stmt:
                        cur.execute(stmt)
                conn.commit()
            finally:
                cur.close()
                conn.close()
                
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/chat/messages/{run_id}")
def get_chat_history(run_id: str):
    store = CatalogStore()
    return {"messages": store.get_chat_history(run_id)}

@app.post("/api/chat/messages")
def save_chat_message(req: ChatMessage):
    store = CatalogStore()
    store.append_chat_message(
        run_id=req.run_id,
        role=req.role,
        content=req.content,
        sql_query=req.sql_query,
        data_json=req.data_json,
        provider=req.provider,
        confidence=req.confidence
    )
    return {"status": "success"}
