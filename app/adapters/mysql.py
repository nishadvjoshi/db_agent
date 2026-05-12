import mysql.connector
from typing import List, Dict, Any, Set
from .base import BaseDatabaseAdapter

def _fetchall_dict(cur) -> List[Dict[str, Any]]:
    rows = cur.fetchall() or []
    out = []
    for r in rows:
        if isinstance(r, dict):
            out.append(r)
        else:
            cols = [d[0] for d in (cur.description or [])]
            out.append({cols[i]: r[i] for i in range(min(len(cols), len(r)))})
    return out

class MySQLAdapter(BaseDatabaseAdapter):
    def __init__(self, connection_params: Dict[str, Any]):
        self.params = connection_params

    def _conn(self):
        return mysql.connector.connect(**self.params)

    def get_schemas(self, include_schemas: Set[str], exclude_schemas: Set[str]) -> List[str]:
        with self._conn() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute("SELECT schema_name AS schema_name FROM information_schema.schemata ORDER BY schema_name")
                rows = _fetchall_dict(cur)
                
        schemas = [r.get("schema_name") for r in rows if isinstance(r.get("schema_name"), str)]
        
        system_schemas = {"information_schema", "mysql", "performance_schema", "sys"}
        allowed = []
        for s in schemas:
            if s in system_schemas or s in exclude_schemas:
                continue
            if include_schemas and s not in include_schemas:
                continue
            allowed.append(s)
        return allowed

    def get_tables(self, schemas: List[str]) -> List[Dict[str, Any]]:
        if not schemas: return []
        ph = ",".join(["%s"] * len(schemas))
        sql = f"SELECT table_schema AS schema_name, table_name AS table_name FROM information_schema.tables WHERE table_type = 'BASE TABLE' AND table_schema IN ({ph}) ORDER BY table_schema, table_name"
        with self._conn() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql, schemas)
                return _fetchall_dict(cur)

    def get_columns(self, schemas: List[str]) -> List[Dict[str, Any]]:
        if not schemas: return []
        ph = ",".join(["%s"] * len(schemas))
        sql = f"SELECT table_schema AS schema_name, table_name AS table_name, column_name AS column_name, data_type AS data_type, column_type AS column_type, is_nullable AS is_nullable, column_key AS column_key, extra AS extra, column_default AS column_default, column_comment AS column_comment, ordinal_position AS ordinal_position FROM information_schema.columns WHERE table_schema IN ({ph}) ORDER BY table_schema, table_name, ordinal_position"
        with self._conn() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql, schemas)
                return _fetchall_dict(cur)

    def get_foreign_keys(self, schemas: List[str]) -> List[Dict[str, Any]]:
        if not schemas: return []
        ph = ",".join(["%s"] * len(schemas))
        sql = f"SELECT kcu.table_schema AS from_schema, kcu.table_name AS from_table, kcu.column_name AS from_column, kcu.referenced_table_schema AS to_schema, kcu.referenced_table_name AS to_table, kcu.referenced_column_name AS to_column, kcu.constraint_name AS constraint_name FROM information_schema.key_column_usage kcu WHERE kcu.referenced_table_name IS NOT NULL AND kcu.table_schema IN ({ph}) AND kcu.referenced_table_schema IN ({ph}) ORDER BY kcu.table_schema, kcu.table_name, kcu.constraint_name, kcu.ordinal_position"
        with self._conn() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql, schemas + schemas)
                return _fetchall_dict(cur)

    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(sql, params)
                if cur.description:
                    return _fetchall_dict(cur)
                return []
