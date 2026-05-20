import psycopg

DB_URL = "postgresql://postgres:postgres@localhost:5433/postgres"

conn = psycopg.connect(DB_URL, autocommit=True)
cur = conn.cursor()
cur.execute(
    """
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE datname = 'sena_guias_db'
      AND pid <> pg_backend_pid()
    """,
)
cur.execute("DROP DATABASE IF EXISTS sena_guias_db")
cur.execute("CREATE DATABASE sena_guias_db")
print("DB recreated")
conn.close()
