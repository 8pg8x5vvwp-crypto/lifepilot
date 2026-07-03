"""
One-time helper: your existing tasks/notes/reminders/etc. from before
auth was added have no owner (user_id is NULL), so they won't show up
under any account.

Run this ONCE after creating your account to claim all of that old
data for yourself:

    cd backend
    python data/claim_legacy_data.py your_username

If you don't want the old test data, just skip this — it'll stay
invisible and harmless in the database.
"""
import sqlite3
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "life_pilot.db")


def claim_legacy_data(username: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT id, username FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    if not row:
        print(f"No user found with username '{username}'. Sign up first, then run this script.")
        conn.close()
        return

    user_id = row[0]
    total = 0
    for table in ("tasks", "transactions", "reminders", "schedule", "notes"):
        cur.execute(f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL", (user_id,))
        total += cur.rowcount
        print(f"  {table}: claimed {cur.rowcount} row(s)")

    conn.commit()
    conn.close()
    print(f"\nDone — {total} old record(s) now belong to '{username}' (id {user_id}).")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python data/claim_legacy_data.py <your_username>")
        sys.exit(1)
    claim_legacy_data(sys.argv[1])
