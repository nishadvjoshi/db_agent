import sqlalchemy
from sqlalchemy import create_engine, inspect, text
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class DatabaseConnector(ABC):
    def __init__(self, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.engine = self._create_engine()

    @abstractmethod
    def _create_engine(self):
        pass

    def get_databases(self) -> List[str]:
        # Usually implemented specifically, or return default
        return [self.database] if self.database else []

    def get_tables(self, schema_name: Optional[str] = None) -> List[str]:
        inspector = inspect(self.engine)
        return inspector.get_table_names(schema=schema_name)

    def get_columns(self, table_name: str, schema_name: Optional[str] = None) -> List[Dict[str, Any]]:
        inspector = inspect(self.engine)
        cols = inspector.get_columns(table_name, schema=schema_name)
        # return standardized format
        results = []
        for c in cols:
            results.append({
                "name": c["name"],
                "type": str(c["type"])
            })
        return results

    def execute_query(self, sql: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        with self.engine.connect() as conn:
            result = conn.execute(text(sql), parameters=params)
            keys = result.keys()
            return [dict(zip(keys, row)) for row in result.fetchall()]


class MySQLConnector(DatabaseConnector):
    def _create_engine(self):
        # Fallback to empty string for database if not provided, though typically we connect to a default
        db_part = f"/{self.database}" if self.database else ""
        url = f"mysql+mysqlconnector://{self.user}:{self.password}@{self.host}:{self.port}{db_part}"
        return create_engine(url)
        
    def get_databases(self) -> List[str]:
        with self.engine.connect() as conn:
            res = conn.execute(text("SHOW DATABASES"))
            dbs = [row[0] for row in res]
            return [db for db in dbs if db not in ('information_schema', 'mysql', 'performance_schema', 'sys')]

class SQLServerConnector(DatabaseConnector):
    def _create_engine(self):
        db_part = f"/{self.database}" if self.database else ""
        url = f"mssql+pymssql://{self.user}:{self.password}@{self.host}:{self.port}{db_part}"
        return create_engine(url)

class RedshiftConnector(DatabaseConnector):
    def _create_engine(self):
        db_part = f"/{self.database}" if self.database else ""
        # Redshift can use postgres driver
        url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}{db_part}"
        return create_engine(url)

def get_connector(db_type: str, host: str, port: int, user: str, password: str, database: str = "") -> DatabaseConnector:
    db_type = db_type.lower()
    if db_type == "mysql":
        return MySQLConnector(host, port, user, password, database)
    elif db_type == "sqlserver":
        return SQLServerConnector(host, port, user, password, database)
    elif db_type in ["redshift", "postgres", "postgresql"]:
        return RedshiftConnector(host, port, user, password, database)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
