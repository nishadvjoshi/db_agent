import mysql.connector
from app.config import settings

def get_mysql_conn():
    return mysql.connector.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database if settings.mysql_database else None,
        autocommit=True,
    )

def get_databases():
    conn = get_mysql_conn()
    cur = conn.cursor()
    try:
        cur.execute("SHOW DATABASES")
        dbs = [row[0] for row in cur.fetchall() if row[0] not in ('information_schema', 'mysql', 'performance_schema', 'sys', settings.catalog_schema)]
        
        results = []
        for db in dbs:
            cur.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{db}'")
            cnt = cur.fetchone()[0]
            results.append({"name": db, "table_count": cnt})
        return results
    finally:
        cur.close()
        conn.close()
