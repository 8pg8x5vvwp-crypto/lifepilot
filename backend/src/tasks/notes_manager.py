from datetime import datetime
from src.db import get_conn, fetch_all, fetch_one


class NotesManager:

    def create_note(self, user_id: int, data: dict) -> dict:
        try:
            title = (data.get("title") or "Untitled Note").strip()
            content = (data.get("content") or "").strip()
            pinned = int(data.get("pinned", 0))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO notes (title, content, pinned, created_at, updated_at, user_id) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (title, content, pinned, now, now, user_id)
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Note saved.",
                    "data": {"id": new_id, "title": title, "content": content, "pinned": bool(pinned), "created_at": now, "updated_at": now}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def update_note(self, user_id: int, note_id: int, data: dict) -> dict:
        try:
            title = (data.get("title") or "Untitled Note").strip()
            content = (data.get("content") or "").strip()
            pinned = int(data.get("pinned", 0))
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "UPDATE notes SET title=%s, content=%s, pinned=%s, updated_at=%s WHERE id=%s AND user_id=%s",
                (title, content, pinned, now, note_id, user_id)
            )
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Note updated.",
                    "data": {"id": note_id, "title": title, "content": content, "pinned": bool(pinned), "updated_at": now}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_notes(self, user_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, content, pinned, created_at, updated_at FROM notes "
                "WHERE user_id = %s ORDER BY pinned DESC, updated_at DESC",
                (user_id,)
            )
            rows = fetch_all(cur)
            conn.close()
            for r in rows:
                r["pinned"] = bool(r["pinned"])
            return {"status": "success", "data": rows}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_note(self, user_id: int, note_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM notes WHERE id=%s AND user_id=%s", (note_id, user_id))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Note deleted."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def toggle_pin(self, user_id: int, note_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT pinned FROM notes WHERE id=%s AND user_id=%s", (note_id, user_id))
            row = cur.fetchone()
            if not row:
                conn.close()
                return {"status": "error", "message": "Note not found."}
            new_pin = 0 if row[0] else 1
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("UPDATE notes SET pinned=%s, updated_at=%s WHERE id=%s AND user_id=%s", (new_pin, now, note_id, user_id))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Pin toggled.", "data": {"pinned": bool(new_pin)}}
        except Exception as e:
            return {"status": "error", "message": str(e)}
