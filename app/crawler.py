from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from app.db_mysql import get_mysql_conn


SYSTEM_SCHEMAS: Set[str] = {
    "information_schema",
    "mysql",
    "performance_schema",
    "sys",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _as_list(x: Optional[Sequence[str]]) -> List[str]:
    if not x:
        return []
    return [str(s).strip() for s in x if str(s).strip()]


@dataclass(frozen=True)
class CrawlFilters:
    include_schemas: Set[str]
    exclude_schemas: Set[str]

    @staticmethod
    def from_args(include: Optional[Sequence[str]], exclude: Optional[Sequence[str]]) -> "CrawlFilters":
        return CrawlFilters(set(_as_list(include)), set(_as_list(exclude)))

    def allow_schema(self, schema: str) -> bool:
        if schema in SYSTEM_SCHEMAS:
            return False
        if schema in self.exclude_schemas:
            return False
        if self.include_schemas and schema not in self.include_schemas:
            return False
        return True


def _fetchall_dict(cur) -> List[Dict[str, Any]]:
    rows = cur.fetchall() or []
    out: List[Dict[str, Any]] = []
    for r in rows:
        if isinstance(r, dict):
            out.append(r)
        else:
            cols = [d[0] for d in (cur.description or [])]
            out.append({cols[i]: r[i] for i in range(min(len(cols), len(r)))})
    return out


def crawl_database(include_schemas: Optional[Sequence[str]] = None, exclude_schemas: Optional[Sequence[str]] = None, run_id: Optional[str] = None, conn_id: Optional[str] = None) -> str:
    """Crawl Target Database metadata and persist a catalog via CatalogStore."""

    from app.catalog_store import CatalogStore  # local import to avoid circular deps
    from app.config import settings
    from app.adapters.factory import get_adapter

    run_id = run_id or str(uuid.uuid4())
    filters = CrawlFilters.from_args(include_schemas, exclude_schemas)

    target_params = {
        "host": settings.target_db_host,
        "port": settings.target_db_port,
        "user": settings.target_db_user,
        "password": settings.target_db_password,
        "database": settings.target_db_name,
    }
    db_type = settings.target_db_type

    if conn_id:
        store = CatalogStore()
        conn = store.get_connection(conn_id)
        if conn:
            db_type = conn.get("db_type", "mysql").lower()
            target_params = {
                "host": conn.get("host"),
                "port": conn.get("port"),
                "user": conn.get("username"),
                "password": conn.get("password"),
                "database": conn.get("database_name"),
            }

    # For demo simplicity we remove empty properties that pyodbc/psycopg2 might complain about
    target_params = {k: v for k, v in target_params.items() if v}
    
    adapter = get_adapter(db_type, target_params)

    # 1) Schemas
    all_schemas = adapter.get_schemas(filters.include_schemas, filters.exclude_schemas)

    # 2) Tables
    table_rows = adapter.get_tables(all_schemas)

    # 3) Columns
    column_rows = adapter.get_columns(all_schemas)

    # 4) Foreign keys -> edges
    edge_rows = adapter.get_foreign_keys(all_schemas)

    # Build canonical catalog JSON
    tables_by_schema: Dict[str, List[str]] = {}
    for r in table_rows:
        s = r.get("schema_name")
        t = r.get("table_name")
        if isinstance(s, str) and isinstance(t, str):
            tables_by_schema.setdefault(s, []).append(t)

    cols_by_table: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for r in column_rows:
        s = r.get("schema_name")
        t = r.get("table_name")
        c = r.get("column_name")
        if not (isinstance(s, str) and isinstance(t, str) and isinstance(c, str)):
            continue
        cols_by_table.setdefault((s, t), []).append(
            {
                "name": c,
                "data_type": r.get("data_type"),
                "column_type": r.get("column_type"),
                "is_nullable": r.get("is_nullable"),
                "column_key": r.get("column_key"),
                "extra": r.get("extra"),
                "default": r.get("column_default"),
                "comment": r.get("column_comment"),
                "ordinal_position": r.get("ordinal_position"),
            }
        )

    catalog_schemas: List[Dict[str, Any]] = []
    for s in all_schemas:
        schema_tables: List[Dict[str, Any]] = []
        for t in tables_by_schema.get(s, []):
            schema_tables.append({"name": t, "columns": cols_by_table.get((s, t), [])})
        catalog_schemas.append({"name": s, "tables": schema_tables})

    catalog_edges: List[Dict[str, Any]] = []
    for r in edge_rows:
        fs, ft, fc = r.get("from_schema"), r.get("from_table"), r.get("from_column")
        ts, tt, tc = r.get("to_schema"), r.get("to_table"), r.get("to_column")
        if not all(isinstance(x, str) and x for x in [fs, ft, fc, ts, tt, tc]):
            continue
        catalog_edges.append(
            {
                "from_table": f"{fs}.{ft}",
                "from_column": fc,
                "to_table": f"{ts}.{tt}",
                "to_column": tc,
                "constraint": r.get("constraint_name"),
            }
        )

    catalog: Dict[str, Any] = {
        "run_id": run_id,
        "generated_at": _utc_now_iso(),
        "schemas": catalog_schemas,
        "edges": catalog_edges,
    }

    CatalogStore().save_catalog(run_id, catalog)
    return run_id
