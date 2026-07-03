"""
Startup migration for Postgres.
Creates all tables and columns if they don't exist.
Safe to run on every startup — fully idempotent.
"""
import os
import psycopg2


def _get_conn():
    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    return psycopg2.connect(db_url, sslmode="require")


def run_migrations(db_path: str = None) -> None:
    """db_path param kept for backwards compatibility, ignored for Postgres."""
    conn = _get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            due_date TEXT,
            priority TEXT,
            completed INTEGER DEFAULT 0,
            created_at TEXT,
            user_id INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            amount REAL NOT NULL,
            category TEXT,
            type TEXT,
            date TEXT,
            description TEXT,
            user_id INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            remind_at TEXT,
            created_at TEXT,
            user_id INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS schedule (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            date TEXT,
            time TEXT,
            duration TEXT,
            notes TEXT,
            created_at TEXT,
            user_id INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL DEFAULT 'Untitled Note',
            content TEXT DEFAULT '',
            pinned INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            user_id INTEGER
        )
    """)

    # Add user_id column to any table that might exist without it (safety net)
    for table in ("tasks", "transactions", "reminders", "schedule", "notes"):
        cur.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = %s AND column_name = 'user_id'
        """, (table,))
        if not cur.fetchone():
            cur.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER")
            print(f"[MIGRATION] Added user_id to '{table}'")

    conn.commit()
    cur.close()
    conn.close()
    print("[MIGRATION] Postgres schema is up to date.")
