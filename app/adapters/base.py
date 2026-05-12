import abc
from typing import List, Dict, Any, Set, Optional

class BaseDatabaseAdapter(abc.ABC):
    """
    Abstract interface for connecting to different target databases.
    Implements schema crawling and query execution.
    """

    @abc.abstractmethod
    def get_schemas(self, include_schemas: Set[str], exclude_schemas: Set[str]) -> List[str]:
        pass

    @abc.abstractmethod
    def get_tables(self, schemas: List[str]) -> List[Dict[str, Any]]:
        """Returns list of dicts with: schema_name, table_name"""
        pass

    @abc.abstractmethod
    def get_columns(self, schemas: List[str]) -> List[Dict[str, Any]]:
        """
        Returns list of dicts with:
        schema_name, table_name, column_name, data_type, column_type,
        is_nullable, column_key, extra, default, comment, ordinal_position
        """
        pass

    @abc.abstractmethod
    def get_foreign_keys(self, schemas: List[str]) -> List[Dict[str, Any]]:
        """
        Returns list of dicts with:
        from_schema, from_table, from_column,
        to_schema, to_table, to_column, constraint_name
        """
        pass

    @abc.abstractmethod
    def execute_query(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        pass
