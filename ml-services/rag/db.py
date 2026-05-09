import psycopg2

DB_CONFIG = {
    "dbname": "liquidity",
    "user": "admin",
    "password": "secret",
    "host": "localhost",
    "port": 5432
}

conn = psycopg2.connect(**DB_CONFIG)

def get_connection():
    """Возвращает текущее соединение"""
    global conn
    if conn.closed:
        conn = psycopg2.connect(**DB_CONFIG)
    return conn

def get_cursor():
    """Возвращает новый курсор от текущего соединения."""
    return get_connection().cursor()