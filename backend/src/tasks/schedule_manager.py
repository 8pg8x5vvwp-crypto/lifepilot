from datetime import datetime
from src.db import get_conn, fetch_all


class ScheduleManager:

    def add_event(self, user_id: int, data: dict) -> dict:
        try:
            title = data.get("title", "").strip()
            if not title:
                return {"status": "error", "message": "Event title is required."}
            date = data.get("date", "") or ""
            time = data.get("time", "") or ""
            duration = data.get("duration", "") or ""
            notes = data.get("notes", "") or ""
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO schedule (title, date, time, duration, notes, created_at, user_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (title, date, time, duration, notes, created_at, user_id)
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            conn.close()
            return {"status": "success", "message": f"Event scheduled: {title}",
                    "data": {"id": new_id, "title": title, "date": date, "time": time, "duration": duration, "notes": notes}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def list_events(self, user_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, date, time, duration, notes, created_at FROM schedule "
                "WHERE user_id = %s ORDER BY date ASC, time ASC",
                (user_id,)
            )
            rows = fetch_all(cur)
            conn.close()
            return {"status": "success", "data": rows}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_event(self, user_id: int, event_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM schedule WHERE id = %s AND user_id = %s", (event_id, user_id))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Event deleted."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
