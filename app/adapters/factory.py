from typing import Dict, Any
from .base import BaseDatabaseAdapter
from .mysql import MySQLAdapter
from .sqlserver import SqlServerAdapter
from .redshift import RedshiftAdapter

def get_adapter(db_type: str, connection_params: Dict[str, Any]) -> BaseDatabaseAdapter:
    db_type = db_type.lower()
    if db_type == "mysql":
        return MySQLAdapter(connection_params)
    elif db_type == "sqlserver":
        return SqlServerAdapter(connection_params)
    elif db_type == "redshift":
        return RedshiftAdapter(connection_params)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
