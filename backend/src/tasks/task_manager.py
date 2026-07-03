import dateparser
from datetime import datetime
from src.db import get_conn, fetch_all, fetch_one


class TaskManager:

    def create_task(self, user_id: int, data: dict) -> dict:
        try:
            title = data.get("title")
            if not title:
                return {"status": "error", "message": "Title is required."}
            due_date = None
            if data.get("due_date"):
                parsed = dateparser.parse(data["due_date"])
                if not parsed:
                    return {"status": "error", "message": "Invalid due date format."}
                if parsed.hour == 0 and parsed.minute == 0:
                    parsed = parsed.replace(hour=18, minute=0, second=0)
                due_date = parsed.strftime("%Y-%m-%d %H:%M:%S")
            priority = data.get("priority", "medium")
            description = data.get("description", "")
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO tasks (title, description, due_date, priority, completed, created_at, user_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (title, description, due_date, priority, 0, created_at, user_id)
            )
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Task created.",
                    "data": {"title": title, "due_date": due_date, "priority": priority}}
        except Exception as e:
            return {"status": "error", "message": f"Failed to create task: {str(e)}"}

    def list_tasks(self, user_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, description, due_date, priority, completed, created_at "
                "FROM tasks WHERE user_id = %s ORDER BY completed ASC, created_at DESC",
                (user_id,)
            )
            rows = fetch_all(cur)
            conn.close()
            for r in rows:
                r["completed"] = bool(r["completed"])
            return {"status": "success", "data": rows}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def complete_task(self, user_id: int, task_identifier) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            if isinstance(task_identifier, int):
                cur.execute("SELECT id FROM tasks WHERE id = %s AND user_id = %s", (task_identifier, user_id))
            else:
                cur.execute(
                    "SELECT id FROM tasks WHERE title ILIKE %s AND completed = 0 AND user_id = %s "
                    "ORDER BY created_at DESC LIMIT 1",
                    (f"%{task_identifier}%", user_id)
                )
            task = cur.fetchone()
            if not task:
                conn.close()
                return {"status": "error", "message": f"Task not found for '{task_identifier}'."}
            task_id = task[0]
            cur.execute("UPDATE tasks SET completed = 1 WHERE id = %s AND user_id = %s", (task_id, user_id))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Task completed."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_task(self, user_id: int, task_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, user_id))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Task deleted."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def clear_all_tasks(self, user_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM tasks WHERE user_id = %s", (user_id,))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "All tasks cleared."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
