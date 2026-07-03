"""
Shared Postgres connection helper.
All managers import get_conn() from here.
"""
import os
import psycopg2
import psycopg2.extras


def get_conn():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    # Neon gives a postgres:// URL; psycopg2 needs postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    conn = psycopg2.connect(db_url, sslmode="require")
    conn.autocommit = False
    return conn


def dict_row(cursor, row):
    """Convert a row tuple into a dict using cursor description."""
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def fetch_all(cursor):
    rows = cursor.fetchall()
    return [dict_row(cursor, r) for r in rows]


def fetch_one(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    return dict_row(cursor, row)
