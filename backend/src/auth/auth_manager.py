import re
import hashlib
import secrets
from datetime import datetime
from src.db import get_conn


class AuthManager:

    @staticmethod
    def _hash_password(password: str, salt: str = None) -> str:
        if salt is None:
            salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000)
        return f"{salt}${digest.hex()}"

    @classmethod
    def _verify_password(cls, password: str, stored_hash: str) -> bool:
        try:
            salt, _ = stored_hash.split("$", 1)
        except ValueError:
            return False
        return secrets.compare_digest(cls._hash_password(password, salt), stored_hash)

    @staticmethod
    def _valid_email(email: str) -> bool:
        return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email or ""))

    def signup(self, username: str, email: str, password: str) -> dict:
        username = (username or "").strip()
        email = (email or "").strip().lower()
        password = password or ""

        if len(username) < 3:
            return {"status": "error", "message": "Username must be at least 3 characters."}
        if not self._valid_email(email):
            return {"status": "error", "message": "Please enter a valid email address."}
        if len(password) < 6:
            return {"status": "error", "message": "Password must be at least 6 characters."}

        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return {"status": "error", "message": "That username is already taken."}
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return {"status": "error", "message": "An account with that email already exists."}

            pw_hash = self._hash_password(password)
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO users (username, email, password_hash, created_at) VALUES (%s, %s, %s, %s) RETURNING id",
                (username, email, pw_hash, created_at)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            return {"status": "success", "message": "Account created.",
                    "data": {"id": user_id, "username": username, "email": email}}
        except Exception as e:
            conn.rollback()
            return {"status": "error", "message": f"Signup failed: {str(e)}"}
        finally:
            conn.close()

    def login(self, identifier: str, password: str) -> dict:
        identifier = (identifier or "").strip().lower()
        if not identifier or not password:
            return {"status": "error", "message": "Username/email and password are required."}

        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, username, email, password_hash FROM users WHERE lower(username) = %s OR email = %s",
                (identifier, identifier)
            )
            row = cur.fetchone()
            if not row or not self._verify_password(password, row[3]):
                return {"status": "error", "message": "Invalid username/email or password."}
            return {"status": "success", "message": "Logged in.",
                    "data": {"id": row[0], "username": row[1], "email": row[2]}}
        except Exception as e:
            return {"status": "error", "message": f"Login failed: {str(e)}"}
        finally:
            conn.close()

    def get_user_by_id(self, user_id: int) -> dict:
        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, username, email FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            if not row:
                return {"status": "error", "message": "User not found."}
            return {"status": "success", "data": {"id": row[0], "username": row[1], "email": row[2]}}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            conn.close()
