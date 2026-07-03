from datetime import datetime
from src.db import get_conn, fetch_all


class ReminderManager:

    def add_reminder(self, user_id: int, data: dict) -> dict:
        try:
            title = (data.get("title") or data.get("text") or "").strip()
            if not title:
                return {"status": "error", "message": "Reminder title is required."}
            remind_at = data.get("remind_at", "") or ""
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO reminders (title, remind_at, created_at, user_id) VALUES (%s, %s, %s, %s) RETURNING id",
                (title, remind_at, created_at, user_id)
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            conn.close()
            return {"status": "success", "message": f"Reminder added: {title}",
                    "data": {"id": new_id, "title": title, "text": title, "remind_at": remind_at, "created_at": created_at}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_reminders(self, user_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, remind_at, created_at FROM reminders WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            rows = fetch_all(cur)
            conn.close()
            for r in rows:
                r["text"] = r["title"]
            return {"status": "success", "data": rows}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_reminder(self, user_id: int, reminder_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM reminders WHERE id = %s AND user_id = %s", (reminder_id, user_id))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Reminder deleted."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
