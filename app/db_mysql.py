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
