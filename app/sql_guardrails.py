import sqlparse

BLOCKLIST = [
    "drop ", "truncate ", "delete ", "update ", "insert ",
    "alter ", "create ", "grant ", "revoke ", " into ",
    "information_schema", "mysql.", "performance_schema", "sys."
]

def is_safe_sql(sql: str) -> tuple[bool, str]:
    if not sql or not sql.strip():
        return False, "Empty SQL"
    statements = [s for s in sqlparse.split(sql) if s.strip()]
    if len(statements) != 1:
        return False, "Multiple statements not allowed"
    low = sql.lower()
    for b in BLOCKLIST:
        if b in low:
            return False, f"Blocked token: {b.strip()}"
    import re
    cleaned = re.sub(r'/\*.*?\*/', '', low, flags=re.DOTALL)
    cleaned = re.sub(r'--.*?\n', '\n', cleaned)
    cleaned = re.sub(r'^--.*$', '', cleaned) # If comment is the very last line with no newline
    cleaned = cleaned.strip()

    if not (cleaned.startswith("select") or cleaned.startswith("with")):
        return False, f"Only SELECT or CTE (WITH) statements are allowed. Got: '{cleaned[:30]}...'"
    return True, "OK"

def enforce_limit(sql: str, limit: int) -> str:
    low = sql.lower()
    if " limit " in low:
        return sql
    return sql.rstrip().rstrip(";") + f" LIMIT {limit};"

def check_phi_safety(sql: str, catalog_ctx: dict) -> tuple[bool, str]:
    """
    Check if the LLM's generated SQL queries any column tagged with 'PHI_'.
    """
    if "schemas" not in catalog_ctx or "candidates" not in catalog_ctx:
        return True, "No catalog context provided"

    sql_lower = sql.lower()
    
    # Iterate through candidates provided to the LLM
    for candidate in catalog_ctx["candidates"]:
        table_name = candidate.get("table", "")
        # Remove schema prefix if it exists
        bare_table = table_name.split(".")[-1] if "." in table_name else table_name
        
        # Check if table is used in the query
        if bare_table.lower() not in sql_lower and table_name.lower() not in sql_lower:
            continue
            
        # Check if the query selects a PHI column or selects all (*) from a table with PHI
        for hit in candidate.get("hits", []):
            semantic_type = hit.get("semantic", "")
            if semantic_type and isinstance(semantic_type, str) and semantic_type.startswith("PHI_"):
                col_name = hit.get("column", "").lower()
                
                # If the query uses "SELECT *" on a table with PHI columns
                if "select *" in sql_lower:
                    return False, f"Unsafe query: 'SELECT *' exposes sensitive column '{col_name}' ({semantic_type})"
                
                # If the specific PHI column is queried directly in the SELECT clause
                import re
                select_match = re.search(r"select\s+(.*?)\s+from", sql, re.IGNORECASE | re.DOTALL)
                if select_match:
                    select_clause = select_match.group(1).lower()
                    if col_name in select_clause:
                        return False, f"Unsafe query: Cannot select sensitive PHI column '{col_name}' ({semantic_type})"

    return True, "OK"
