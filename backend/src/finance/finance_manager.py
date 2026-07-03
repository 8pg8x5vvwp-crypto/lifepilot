import dateparser
from datetime import datetime
from src.db import get_conn, fetch_all


class FinanceManager:

    def add_transaction(self, user_id: int, data: dict) -> dict:
        try:
            amount = float(data.get("amount", 0))
            category = data.get("category") or data.get("title") or "General"
            transaction_type = data.get("type", "expense")
            description = data.get("description", "")
            if transaction_type not in ["expense", "income"]:
                transaction_type = "expense"
            if data.get("date"):
                parsed = dateparser.parse(data["date"])
                date = parsed.strftime("%Y-%m-%d %H:%M:%S") if parsed else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO transactions (amount, category, type, date, description, user_id) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (amount, category, transaction_type, date, description, user_id)
            )
            conn.commit()
            conn.close()
            return {"status": "success", "message": f"{category} added.",
                    "data": {"title": category, "amount": amount, "type": transaction_type}}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def delete_transaction(self, user_id: int, transaction_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM transactions WHERE id = %s AND user_id = %s", (transaction_id, user_id))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "Transaction deleted."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_transactions(self, user_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT id, amount, category, type, date, description FROM transactions "
                "WHERE user_id = %s ORDER BY date DESC",
                (user_id,)
            )
            rows = fetch_all(cur)
            conn.close()
            return {"status": "success", "data": rows}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def get_summary(self, user_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='income' AND user_id = %s", (user_id,))
            total_income = float(cur.fetchone()[0])
            cur.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense' AND user_id = %s", (user_id,))
            total_expenses = float(cur.fetchone()[0])
            balance = total_income - total_expenses
            cur.execute(
                "SELECT category, SUM(amount) FROM transactions WHERE type='expense' AND user_id = %s GROUP BY category",
                (user_id,)
            )
            cat_rows = cur.fetchall()
            conn.close()
            breakdown = {
                c: {"total": float(t), "percentage": round((float(t) / total_expenses) * 100, 2) if total_expenses else 0}
                for c, t in cat_rows
            }
            return {"status": "success", "data": {
                "total_income": total_income, "total_expenses": total_expenses,
                "balance": balance, "category_breakdown": breakdown
            }}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def clear_all_transactions(self, user_id: int) -> dict:
        try:
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("DELETE FROM transactions WHERE user_id = %s", (user_id,))
            conn.commit()
            conn.close()
            return {"status": "success", "message": "All transactions cleared."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
