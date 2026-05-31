import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import mysql.connector
from app.config import settings


class CatalogStore:
    """
    MySQL-backed catalog store.

    Expected schema (created by init_schema in settings.catalog_schema):
      - runs(run_id PK, created_at)
      - schemas(run_id, schema_name)
      - tables(run_id, schema_name, table_name, row_count)
      - columns(run_id, schema_name, table_name, column_name, data_type, is_nullable, column_key, extra, column_default)
      - foreign_keys(run_id, schema_name, table_name, column_name, ref_schema_name, ref_table_name, ref_column_name, constraint_name)
      - profiles(...)
      - docs(...)
      - catalog_descriptions(run_id, schema_name, table_name, column_name, description, generated_by, generated_at)
      - learned_concepts(...)
    """

    def __init__(self):
        self.schema = settings.catalog_schema
        self.init_schema()

    def _conn(self, include_schema=True) -> mysql.connector.MySQLConnection:
        db = self.schema if include_schema else None
        return mysql.connector.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=db,
            autocommit=True,
        )

    def init_schema(self) -> None:
        con = self._conn(include_schema=False)
        cur = con.cursor()
        try:
            cur.execute(f"CREATE DATABASE IF NOT EXISTS `{self.schema}`")
            cur.execute(f"USE `{self.schema}`")
            
            tables_ddl = [
                """
                CREATE TABLE IF NOT EXISTS `catalog_runs` (
                    run_id VARCHAR(255) PRIMARY KEY,
                    created_at VARCHAR(255)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_schemas` (
                    run_id VARCHAR(64),
                    schema_name VARCHAR(64),
                    PRIMARY KEY (run_id, schema_name)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_tables` (
                    run_id VARCHAR(64),
                    schema_name VARCHAR(64),
                    table_name VARCHAR(64),
                    row_count BIGINT,
                    ai_description TEXT,
                    ai_generated_by VARCHAR(64),
                    ai_generated_at VARCHAR(64),
                    PRIMARY KEY (run_id, schema_name, table_name)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_columns` (
                    run_id VARCHAR(64),
                    schema_name VARCHAR(64),
                    table_name VARCHAR(64),
                    column_name VARCHAR(64),
                    data_type VARCHAR(64),
                    is_nullable VARCHAR(64),
                    column_key VARCHAR(64),
                    extra VARCHAR(64),
                    column_default TEXT,
                    ai_description TEXT,
                    ai_generated_by VARCHAR(64),
                    ai_generated_at VARCHAR(64),
                    PRIMARY KEY (run_id, schema_name, table_name, column_name)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_foreign_keys` (
                    run_id VARCHAR(64),
                    schema_name VARCHAR(64),
                    table_name VARCHAR(64),
                    column_name VARCHAR(64),
                    ref_schema_name VARCHAR(64),
                    ref_table_name VARCHAR(64),
                    ref_column_name VARCHAR(64),
                    constraint_name VARCHAR(64),
                    PRIMARY KEY (run_id, schema_name, table_name, column_name, ref_schema_name, ref_table_name, ref_column_name)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_profiles` (
                    run_id VARCHAR(64),
                    schema_name VARCHAR(64),
                    table_name VARCHAR(64),
                    column_name VARCHAR(64),
                    inferred_semantic_type VARCHAR(64),
                    sample_values_json TEXT,
                    notes TEXT,
                    PRIMARY KEY (run_id, schema_name, table_name, column_name)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_docs` (
                    doc_id VARCHAR(64) PRIMARY KEY,
                    run_id VARCHAR(64),
                    doc_type VARCHAR(64),
                    payload_json TEXT,
                    created_at VARCHAR(64)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_learned_concepts` (
                    concept_name VARCHAR(64) PRIMARY KEY,
                    description TEXT,
                    synonyms_json TEXT,
                    table_hints_json TEXT,
                    column_hints_json TEXT,
                    learned_at VARCHAR(64)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_edw_configs` (
                    run_id VARCHAR(64),
                    table_name VARCHAR(255),
                    is_included BOOLEAN DEFAULT TRUE,
                    table_role VARCHAR(64),
                    scd_type VARCHAR(64),
                    type_3_columns TEXT,
                    PRIMARY KEY (run_id, table_name)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_connections` (
                    connection_id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255),
                    db_type VARCHAR(64),
                    host VARCHAR(255),
                    port INT,
                    username VARCHAR(255),
                    password VARCHAR(255),
                    database_name VARCHAR(255),
                    created_at VARCHAR(64)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_run_logs` (
                    log_id INT AUTO_INCREMENT PRIMARY KEY,
                    run_id VARCHAR(64),
                    timestamp VARCHAR(64),
                    level VARCHAR(32),
                    message TEXT,
                    INDEX (run_id)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_chat_messages` (
                    msg_id INT AUTO_INCREMENT PRIMARY KEY,
                    run_id VARCHAR(64),
                    role VARCHAR(32),
                    content TEXT,
                    sql_query TEXT,
                    data_json LONGTEXT,
                    provider VARCHAR(64),
                    confidence VARCHAR(64),
                    created_at VARCHAR(64),
                    INDEX (run_id)
                )
                """,
                """
                CREATE TABLE IF NOT EXISTS `catalog_ddd_artifacts` (
                    run_id VARCHAR(64),
                    artifact_type VARCHAR(64),
                    payload_json LONGTEXT,
                    created_at VARCHAR(64),
                    PRIMARY KEY (run_id, artifact_type)
                )
                """
            ]
            for ddl in tables_ddl:
                cur.execute(ddl)
        finally:
            cur.close()
            con.close()

    # ----------------------------
    # Low-level upserts
    # ----------------------------

    def upsert_run(self, run_id: str, created_at: Optional[str] = None) -> None:
        created_at = created_at or datetime.utcnow().isoformat()
        con = self._conn()
        cur = con.cursor()
        try:
            cur.execute(
                """
                INSERT INTO `catalog_runs`(run_id, created_at) VALUES(%s, %s)
                ON DUPLICATE KEY UPDATE created_at=VALUES(created_at)
                """,
                (run_id, created_at),
            )
        finally:
            cur.close()
            con.close()

    def upsert_schema(self, run_id: str, schema_name: str) -> None:
        con = self._conn()
        cur = con.cursor()
        try:
            cur.execute(
                """
                INSERT IGNORE INTO `catalog_schemas`(run_id, schema_name) VALUES(%s, %s)
                """,
                (run_id, schema_name),
            )
        finally:
            cur.close()
            con.close()

    def upsert_table(
        self, run_id: str, schema_name: str, table_name: str, row_count: Optional[int] = None
    ) -> None:
        con = self._conn()
        cur = con.cursor()
        try:
            cur.execute(
                """
                INSERT INTO `catalog_tables`(run_id, schema_name, table_name, row_count)
                VALUES(%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE row_count=COALESCE(VALUES(row_count), `catalog_tables`.row_count)
                """,
                (run_id, schema_name, table_name, row_count),
            )
        finally:
            cur.close()
            con.close()

    def upsert_column(
        self,
        run_id: str,
        schema_name: str,
        table_name: str,
        column_name: str,
        data_type: str,
        is_nullable: Optional[str] = None,
        column_key: Optional[str] = None,
        extra: Optional[str] = None,
        column_default: Optional[str] = None,
    ) -> None:
        # Handle dict column_default cases or weird values causing MySQL issues
        if isinstance(column_default, dict):
            column_default = json.dumps(column_default)
            
        con = self._conn()
        cur = con.cursor()
        try:
            cur.execute(
                """
                INSERT INTO `catalog_columns`(
                    run_id, schema_name, table_name, column_name,
                    data_type, is_nullable, column_key, extra, column_default
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  data_type=VALUES(data_type),
                  is_nullable=VALUES(is_nullable),
                  column_key=VALUES(column_key),
                  extra=VALUES(extra),
                  column_default=VALUES(column_default)
                """,
                (
                    run_id,
                    schema_name,
                    table_name,
                    column_name,
                    data_type,
                    is_nullable,
                    column_key,
                    extra,
                    column_default,
                ),
            )
        finally:
            cur.close()
            con.close()

    def upsert_foreign_key(
        self,
        run_id: str,
        schema_name: str,
        table_name: str,
        column_name: str,
        ref_schema_name: str,
        ref_table_name: str,
        ref_column_name: str,
        constraint_name: Optional[str] = None,
    ) -> None:
        con = self._conn()
        cur = con.cursor()
        try:
            cur.execute(
                """
                INSERT INTO `catalog_foreign_keys`(
                    run_id, schema_name, table_name, column_name,
                    ref_schema_name, ref_table_name, ref_column_name, constraint_name
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE constraint_name=COALESCE(VALUES(constraint_name), `catalog_foreign_keys`.constraint_name)
                """,
                (
                    run_id,
                    schema_name,
                    table_name,
                    column_name,
                    ref_schema_name,
                    ref_table_name,
                    ref_column_name,
                    constraint_name,
                ),
            )
        finally:
            cur.close()
            con.close()

    def upsert_profile(
        self,
        run_id: str,
        schema_name: str,
        table_name: str,
        column_name: str,
        inferred_semantic_type: Optional[str],
        distinct_count: Optional[int],
        null_count: Optional[int],
        sample_vals: List[Any],
    ) -> None:
        con = self._conn()
        cur = con.cursor()
        try:
            notes = json.dumps({"distinct_count": distinct_count, "null_count": null_count})
            sample_values_json = json.dumps(sample_vals, default=str) if sample_vals else "[]"
            cur.execute(
                """
                INSERT INTO `catalog_profiles`(
                    run_id, schema_name, table_name, column_name,
                    inferred_semantic_type, sample_values_json, notes
                )
                VALUES(%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  inferred_semantic_type=VALUES(inferred_semantic_type),
                  sample_values_json=VALUES(sample_values_json),
                  notes=VALUES(notes)
                """,
                (
                    run_id,
                    schema_name,
                    table_name,
                    column_name,
                    inferred_semantic_type,
                    sample_values_json,
                    notes,
                ),
            )
        finally:
            cur.close()
            con.close()

    # ----------------------------
    # Catalog Descriptions (AI Glossary)
    # ----------------------------
    
    def upsert_catalog_description(
        self,
        run_id: str,
        schema_name: str,
        table_name: str,
        column_name: str,
        description: str,
        generated_by: str,
    ) -> None:
        """Upsert an AI-generated description directly into catalog_tables or catalog_columns."""
        con = self._conn()
        cur = con.cursor()
        try:
            now = datetime.utcnow().isoformat()
            if column_name:
                cur.execute(
                    """
                    UPDATE `catalog_columns` 
                    SET ai_description=%s, ai_generated_by=%s, ai_generated_at=%s 
                    WHERE run_id=%s AND schema_name=%s AND table_name=%s AND column_name=%s
                    """,
                    (description, generated_by, now, run_id, schema_name, table_name, column_name),
                )
            else:
                cur.execute(
                    """
                    UPDATE `catalog_tables` 
                    SET ai_description=%s, ai_generated_by=%s, ai_generated_at=%s 
                    WHERE run_id=%s AND schema_name=%s AND table_name=%s
                    """,
                    (description, generated_by, now, run_id, schema_name, table_name),
                )
        finally:
            cur.close()
            con.close()

    def get_catalog_descriptions(self, run_id: str) -> Dict[Tuple[str, str, str], Dict[str, str]]:
        con = self._conn()
        cur = con.cursor(dictionary=True)
        try:
            out = {}
            
            # 1. Fetch table descriptions
            cur.execute(
                "SELECT schema_name, table_name, ai_description, ai_generated_by, ai_generated_at FROM `catalog_tables` WHERE run_id=%s AND ai_description IS NOT NULL",
                (run_id,)
            )
            for r in cur.fetchall():
                key = (r["schema_name"], r["table_name"], "")
                out[key] = {
                    "description": r["ai_description"],
                    "generated_by": r["ai_generated_by"],
                    "generated_at": r["ai_generated_at"]
                }
                
            # 2. Fetch column descriptions
            cur.execute(
                "SELECT schema_name, table_name, column_name, ai_description, ai_generated_by, ai_generated_at FROM `catalog_columns` WHERE run_id=%s AND ai_description IS NOT NULL",
                (run_id,)
            )
            for r in cur.fetchall():
                key = (r["schema_name"], r["table_name"], r["column_name"])
                out[key] = {
                    "description": r["ai_description"],
                    "generated_by": r["ai_generated_by"],
                    "generated_at": r["ai_generated_at"]
                }
            return out
        finally:
            cur.close()
            con.close()

    # ----------------------------
    # Learned Concepts (Dynamic Glossary Cache)
    # ----------------------------
    
    def get_learned_concept(self, concept_name: str) -> Optional[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT * FROM `catalog_learned_concepts` WHERE concept_name=%s", 
                (concept_name.lower(),)
            )
            row = cur.fetchone()
            if row:
                return {
                    "concept": row["concept_name"],
                    "description": row["description"],
                    "synonyms": json.loads(row["synonyms_json"] or "[]"),
                    "table_hints": json.loads(row["table_hints_json"] or "[]"),
                    "column_hints": json.loads(row["column_hints_json"] or "{}"),
                    "learned_at": row["learned_at"]
                }
            return None
        finally:
            cur.close()
            con.close()

    def save_learned_concept(self, concept_name: str, payload: Dict[str, Any]) -> None:
        con = self._conn()
        cur = con.cursor()
        try:
            desc = payload.get("description", "")
            syns = json.dumps(payload.get("synonyms", []))
            thints = json.dumps(payload.get("table_hints", []))
            chints = json.dumps(payload.get("column_hints", {}))
            now = datetime.utcnow().isoformat()
            
            cur.execute(
                """
                INSERT INTO `catalog_learned_concepts`(concept_name, description, synonyms_json, table_hints_json, column_hints_json, learned_at)
                VALUES(%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                  description=VALUES(description),
                  synonyms_json=VALUES(synonyms_json),
                  table_hints_json=VALUES(table_hints_json),
                  column_hints_json=VALUES(column_hints_json),
                  learned_at=VALUES(learned_at)
                """,
                (concept_name.lower(), desc, syns, thints, chints, now)
            )
        finally:
            cur.close()
            con.close()
            
    def get_all_learned_concepts(self) -> Dict[str, Any]:
        """Returns all cached concepts for natural language matching."""
        con = self._conn()
        cur = con.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM `catalog_learned_concepts`")
            rows = cur.fetchall()
            out = {}
            for r in rows:
                out[r["concept_name"]] = {
                    "description": r["description"],
                    "synonyms": json.loads(r["synonyms_json"] or "[]"),
                    "table_hints": json.loads(r["table_hints_json"] or "[]"),
                    "column_hints": json.loads(r["column_hints_json"] or "{}")
                }
            return out
        finally:
            cur.close()
            con.close()

    # ----------------------------
    # Backward-compatible wrappers
    # ----------------------------

    def save_run(self, run_id: str, created_at: Optional[str] = None) -> None:
        """Older code expects save_run(). Alias to upsert_run()."""
        self.upsert_run(run_id, created_at)

    def save_catalog(self, run_id: str, catalog: Dict[str, Any]) -> None:
        created_at = catalog.get("created_at") or datetime.utcnow().isoformat()
        self.save_run(run_id, created_at)

        schemas = catalog.get("schemas") or []
        for s in schemas:
            schema_name = s.get("name") or s.get("schema_name")
            if not schema_name:
                continue
            self.upsert_schema(run_id, schema_name)

            for t in (s.get("tables") or []):
                table_name = t.get("name") or t.get("table_name")
                if not table_name:
                    continue
                self.upsert_table(run_id, schema_name, table_name, t.get("row_count"))

                for c in (t.get("columns") or []):
                    col_name = c.get("name") or c.get("column_name")
                    if not col_name:
                        continue
                    self.upsert_column(
                        run_id=run_id,
                        schema_name=schema_name,
                        table_name=table_name,
                        column_name=col_name,
                        data_type=c.get("data_type") or c.get("type") or "",
                        is_nullable=c.get("is_nullable"),
                        column_key=c.get("column_key"),
                        extra=c.get("extra"),
                        column_default=c.get("column_default"),
                    )

        # Save FK edges (crawler uses "edges")
        for e in (catalog.get("edges") or []):
            from_tbl = e.get("from_table") or ""
            to_tbl = e.get("to_table") or ""
            if "." not in from_tbl or "." not in to_tbl:
                continue
            from_schema, from_table = from_tbl.split(".", 1)
            to_schema, to_table = to_tbl.split(".", 1)

            self.upsert_foreign_key(
                run_id=run_id,
                schema_name=from_schema,
                table_name=from_table,
                column_name=e.get("from_column") or "",
                ref_schema_name=to_schema,
                ref_table_name=to_table,
                ref_column_name=e.get("to_column") or "",
                constraint_name=e.get("constraint_name"),
            )

    def get_catalog(self, run_id: str) -> Dict[str, Any]:
        """Reconstruct nested catalog for a run_id (enough for router/planning)."""
        con = self._conn()
        cur = con.cursor(dictionary=True)
        try:
            cur.execute("SELECT run_id, created_at FROM `catalog_runs` WHERE run_id=%s", (run_id,))
            run = cur.fetchone()
            if not run:
                raise KeyError(f"run_id not found: {run_id}")

            cur.execute(
                "SELECT schema_name FROM `catalog_schemas` WHERE run_id=%s ORDER BY schema_name",
                (run_id,),
            )
            schema_rows = cur.fetchall()

            cur.execute(
                "SELECT schema_name, table_name, row_count, ai_description FROM `catalog_tables` WHERE run_id=%s ORDER BY schema_name, table_name",
                (run_id,),
            )
            tables_rows = cur.fetchall()

            cur.execute(
                """
                SELECT 
                    c.schema_name, 
                    c.table_name, 
                    c.column_name, 
                    c.data_type, 
                    c.is_nullable, 
                    c.column_key, 
                    c.extra, 
                    c.column_default,
                    c.ai_description AS catalog_description,
                    p.inferred_semantic_type
                FROM `catalog_columns` c
                LEFT JOIN `catalog_profiles` p 
                  ON c.run_id = p.run_id 
                 AND c.schema_name = p.schema_name
                 AND c.table_name = p.table_name
                 AND c.column_name = p.column_name
                WHERE c.run_id=%s
                ORDER BY c.schema_name, c.table_name, c.column_name
                """,
                (run_id,),
            )
            cols_rows = cur.fetchall()

            cur.execute(
                """
                SELECT schema_name, table_name, column_name, ref_schema_name, ref_table_name, ref_column_name, constraint_name
                FROM `catalog_foreign_keys`
                WHERE run_id=%s
                """,
                (run_id,),
            )
            fk_rows = cur.fetchall()

            # Build maps
            cols_map: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
            for r in cols_rows:
                key = (r["schema_name"], r["table_name"])
                cols_map.setdefault(key, []).append(
                    {
                        "name": r["column_name"],
                        "data_type": r["data_type"],
                        "is_nullable": r["is_nullable"],
                        "column_key": r["column_key"],
                        "extra": r["extra"],
                        "column_default": r["column_default"],
                        "inferred_semantic_type": r["inferred_semantic_type"],
                        "catalog_description": r.get("catalog_description"),
                    }
                )

            table_desc_map: Dict[Tuple[str, str], str] = {}
            for r in tables_rows:
                if r.get("ai_description"):
                    table_desc_map[(r["schema_name"], r["table_name"])] = r["ai_description"]

            tables_map: Dict[str, List[Dict[str, Any]]] = {}
            for r in tables_rows:
                key = r["schema_name"]
                tname = r["table_name"]
                tables_map.setdefault(key, []).append(
                    {
                        "name": tname,
                        "row_count": r["row_count"],
                        "columns": cols_map.get((key, tname), []),
                        "catalog_description": table_desc_map.get((key, tname)),
                    }
                )

            schemas = []
            for s in schema_rows:
                sn = s["schema_name"]
                schemas.append({"name": sn, "tables": tables_map.get(sn, [])})

            edges = []
            for r in fk_rows:
                edges.append(
                    {
                        "from_table": f"{r['schema_name']}.{r['table_name']}",
                        "from_column": r["column_name"],
                        "to_table": f"{r['ref_schema_name']}.{r['ref_table_name']}",
                        "to_column": r["ref_column_name"],
                        "constraint_name": r["constraint_name"],
                    }
                )

            return {"run_id": run["run_id"], "created_at": run["created_at"], "schemas": schemas, "edges": edges}
        finally:
            cur.close()
            con.close()

    def save_edw_config(self, run_id: str, table_configs: List[Dict[str, Any]]):
        """Saves EDW table configurations to catalog_edw_configs."""
        con = self._conn()
        cur = con.cursor()
        try:
            # Delete existing configs for this run
            cur.execute("DELETE FROM `catalog_edw_configs` WHERE run_id=%s", (run_id,))
            
            # Insert new configs
            for config in table_configs:
                cur.execute(
                    """
                    INSERT INTO `catalog_edw_configs` 
                    (run_id, table_name, is_included, table_role, scd_type, type_3_columns)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run_id,
                        config.get("table_name"),
                        config.get("is_included", True),
                        config.get("table_role", "Dimension"),
                        config.get("scd_type", "Type 2"),
                        config.get("type_3_columns", "")
                    )
                )
            con.commit()
        finally:
            cur.close()
            con.close()

    def load_edw_config(self, run_id: str) -> List[Dict[str, Any]]:
        """Loads EDW table configurations for a given run."""
        con = self._conn()
        cur = con.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM `catalog_edw_configs` WHERE run_id=%s", (run_id,))
            return cur.fetchall()
        finally:
            cur.close()
            con.close()

    # ----------------------------
    # Run Logs
    # ----------------------------

    def log_run_event(self, run_id: str, level: str, message: str) -> None:
        con = self._conn()
        cur = con.cursor()
        try:
            now = datetime.utcnow().isoformat()
            cur.execute(
                """
                INSERT INTO `catalog_run_logs` (run_id, timestamp, level, message)
                VALUES (%s, %s, %s, %s)
                """,
                (run_id, now, level, message)
            )
            con.commit()
        finally:
            cur.close()
            con.close()

    def get_run_logs(self, run_id: str) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT * FROM `catalog_run_logs` WHERE run_id=%s ORDER BY log_id ASC",
                (run_id,)
            )
            return cur.fetchall()
        finally:
            cur.close()
            con.close()

    # ----------------------------
    # Connections
    # ----------------------------

    def save_connection(self, conn_id: str, payload: Dict[str, Any]) -> None:
        con = self._conn()
        cur = con.cursor()
        try:
            now = datetime.utcnow().isoformat()
            cur.execute(
                """
                INSERT INTO `catalog_connections` (connection_id, name, db_type, host, port, username, password, database_name, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name=VALUES(name), db_type=VALUES(db_type), host=VALUES(host), port=VALUES(port),
                    username=VALUES(username), password=VALUES(password), database_name=VALUES(database_name)
                """,
                (
                    conn_id, payload.get("name"), payload.get("db_type"), payload.get("host"),
                    payload.get("port"), payload.get("username"), payload.get("password"),
                    payload.get("database_name"), now
                )
            )
            con.commit()
        finally:
            cur.close()
            con.close()

    def get_connections(self) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor(dictionary=True)
        try:
            cur.execute("SELECT connection_id, name, db_type, host, port, username, database_name, created_at FROM `catalog_connections` ORDER BY created_at DESC")
            return cur.fetchall()
        finally:
            cur.close()
            con.close()
            
    def get_connection(self, conn_id: str) -> Optional[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor(dictionary=True)
        try:
            cur.execute("SELECT * FROM `catalog_connections` WHERE connection_id=%s", (conn_id,))
            return cur.fetchone()
        finally:
            cur.close()
            con.close()

    # ----------------------------
    # Chat History
    # ----------------------------

    def append_chat_message(
        self,
        run_id: str,
        role: str,
        content: str,
        sql_query: Optional[str] = None,
        data_json: Optional[str] = None,
        provider: Optional[str] = None,
        confidence: Optional[str] = None
    ) -> None:
        con = self._conn()
        cur = con.cursor()
        try:
            now = datetime.utcnow().isoformat()
            cur.execute(
                """
                INSERT INTO `catalog_chat_messages`
                (run_id, role, content, sql_query, data_json, provider, confidence, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (run_id, role, content, sql_query, data_json, provider, confidence, now)
            )
            con.commit()
        finally:
            cur.close()
            con.close()

    def get_chat_history(self, run_id: str) -> List[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT * FROM `catalog_chat_messages` WHERE run_id=%s ORDER BY msg_id ASC",
                (run_id,)
            )
            return cur.fetchall()
        finally:
            cur.close()
            con.close()

    # ----------------------------
    # DDD Artifacts (Phase A)
    # ----------------------------

    def save_ddd_artifact(self, run_id: str, artifact_type: str, payload: Dict[str, Any]) -> None:
        con = self._conn()
        cur = con.cursor()
        try:
            now = datetime.utcnow().isoformat()
            payload_json = json.dumps(payload)
            cur.execute(
                """
                INSERT INTO `catalog_ddd_artifacts` (run_id, artifact_type, payload_json, created_at)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE payload_json=VALUES(payload_json), created_at=VALUES(created_at)
                """,
                (run_id, artifact_type, payload_json, now)
            )
            con.commit()
        finally:
            cur.close()
            con.close()

    def get_ddd_artifact(self, run_id: str, artifact_type: str) -> Optional[Dict[str, Any]]:
        con = self._conn()
        cur = con.cursor(dictionary=True)
        try:
            cur.execute(
                "SELECT payload_json FROM `catalog_ddd_artifacts` WHERE run_id=%s AND artifact_type=%s",
                (run_id, artifact_type)
            )
            row = cur.fetchone()
            if row and row.get("payload_json"):
                return json.loads(row["payload_json"])
            return None
        finally:
            cur.close()
            con.close()