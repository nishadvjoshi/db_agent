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


def crawl_mysql(include_schemas: Optional[Sequence[str]] = None, exclude_schemas: Optional[Sequence[str]] = None) -> str:
    """Crawl MySQL metadata and persist a catalog via CatalogStore.

    This function always aliases columns in SQL to **lowercase** names (schema_name, table_name, ...)
    so downstream code never breaks due to driver-dependent casing.
    """

    from app.catalog_store import CatalogStore  # local import to avoid circular deps

    run_id = str(uuid.uuid4())
    filters = CrawlFilters.from_args(include_schemas, exclude_schemas)

    conn = get_mysql_conn()
    cur = conn.cursor(dictionary=True)

    # 1) Schemas
    cur.execute(
        """
        SELECT schema_name AS schema_name
        FROM information_schema.schemata
        ORDER BY schema_name
        """.strip()
    )
    schema_rows = _fetchall_dict(cur)
    schemas = [r.get("schema_name") for r in schema_rows if isinstance(r.get("schema_name"), str)]
    schemas = [s for s in schemas if filters.allow_schema(s)]

    # 2) Tables
    table_rows: List[Dict[str, Any]] = []
    if schemas:
        ph = ",".join(["%s"] * len(schemas))
        cur.execute(
            f"""
            SELECT table_schema AS schema_name, table_name AS table_name
            FROM information_schema.tables
            WHERE table_type = 'BASE TABLE'
              AND table_schema IN ({ph})
            ORDER BY table_schema, table_name
            """.strip(),
            schemas,
        )
        table_rows = _fetchall_dict(cur)

    # 3) Columns
    column_rows: List[Dict[str, Any]] = []
    if schemas:
        ph = ",".join(["%s"] * len(schemas))
        cur.execute(
            f"""
            SELECT
              table_schema AS schema_name,
              table_name AS table_name,
              column_name AS column_name,
              data_type AS data_type,
              column_type AS column_type,
              is_nullable AS is_nullable,
              column_key AS column_key,
              extra AS extra,
              column_default AS column_default,
              column_comment AS column_comment,
              ordinal_position AS ordinal_position
            FROM information_schema.columns
            WHERE table_schema IN ({ph})
            ORDER BY table_schema, table_name, ordinal_position
            """.strip(),
            schemas,
        )
        column_rows = _fetchall_dict(cur)

    # 4) Foreign keys -> edges
    edge_rows: List[Dict[str, Any]] = []
    if schemas:
        ph = ",".join(["%s"] * len(schemas))
        cur.execute(
            f"""
            SELECT
              kcu.table_schema AS from_schema,
              kcu.table_name AS from_table,
              kcu.column_name AS from_column,
              kcu.referenced_table_schema AS to_schema,
              kcu.referenced_table_name AS to_table,
              kcu.referenced_column_name AS to_column,
              kcu.constraint_name AS constraint_name
            FROM information_schema.key_column_usage kcu
            WHERE kcu.referenced_table_name IS NOT NULL
              AND kcu.table_schema IN ({ph})
              AND kcu.referenced_table_schema IN ({ph})
            ORDER BY kcu.table_schema, kcu.table_name, kcu.constraint_name, kcu.ordinal_position
            """.strip(),
            schemas + schemas,
        )
        edge_rows = _fetchall_dict(cur)

    cur.close()
    conn.close()

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
    for s in schemas:
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
