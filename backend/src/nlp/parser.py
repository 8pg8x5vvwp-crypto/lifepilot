import json
import os
import re
import string
from datetime import datetime
from difflib import get_close_matches

import dateparser
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env"))

try:
    from groq import Groq
except Exception as e:
    print(f"[NLP DEBUG] groq import failed: {e}")
    Groq = None


class NLPParser:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.client = None

        if not self.api_key or Groq is None:
            print("[NLP WARNING] Groq unavailable. Using local fallback parser.")
            return

        try:
            self.client = Groq(api_key=self.api_key)
        except Exception as e:
            print("[NLP ERROR] Failed to initialize Groq client:", e)
            self.client = None

    def clean_task_title(self, title: str) -> str:
        title = title.lower()
        for word in ["the ", "my ", "a "]:
            if title.startswith(word):
                title = title[len(word):]
        title = title.translate(str.maketrans("", "", string.punctuation))
        return title.strip()

    def normalize_task_title(self, title: str, existing_titles: list) -> str:
        if not title:
            return ""
        clean_input = self.clean_task_title(title)
        clean_existing = {self.clean_task_title(t): t for t in existing_titles}
        matches = get_close_matches(clean_input, list(clean_existing.keys()), cutoff=0.5)
        if matches:
            return clean_existing[matches[0]]
        return title.strip().title()

    def parse_datetime(self, value: str, default_hour: int = 18) -> str:
        parsed = dateparser.parse(value or "")
        if not parsed:
            parsed = datetime.now()
        if parsed.hour == 0 and parsed.minute == 0:
            parsed = parsed.replace(hour=default_hour, minute=0, second=0)
        return parsed.strftime("%Y-%m-%d %H:%M:%S")

    def parse(self, text: str, existing_task_titles: list = None) -> dict:
        existing_task_titles = existing_task_titles or []

        if not text:
            return {"intent": "unknown", "data": {}}

        if not self.client:
            return self._fallback_parse(text)

        prompt = f"""You are LifePilot, an assistant inside a productivity app.

Convert the user input into STRICT JSON for app actions.

Allowed intents ONLY:
create_task
list_tasks
complete_task
create_reminder
list_reminders
complete_reminder
create_schedule
list_schedule
add_transaction
get_transactions
get_summary
unknown

Rules:
- Use create_reminder for "remind me", alerts, reminders, or notifications.
- Use create_schedule for calendar events, meetings, classes, plans, appointments, or time blocks.
- Use create_task for assignments, todos, homework, chores, or work items.
- Use add_transaction for spending, buying, paid, income, earned, or received money.
- Extract useful title, description, due_date, remind_at, event_time, priority, amount, category, type, and date.
- Transaction type must be "expense" or "income".
- If the user is chatting, asking for advice, or asking about their app data, return unknown.
- Always return valid JSON only. No extra text, no markdown.

JSON Format:
{{
  "intent": "intent_name",
  "data": {{
    "title": "",
    "description": "",
    "due_date": "",
    "remind_at": "",
    "event_time": "",
    "priority": "",
    "amount": 0,
    "category": "",
    "type": "",
    "date": ""
  }}
}}

Input: "{text}"
"""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0,
            )

            text_response = response.choices[0].message.content.strip()
            match = re.search(r"\{.*\}", text_response, re.DOTALL)
            parsed_json = json.loads(match.group(0) if match else text_response)

            intent = parsed_json.get("intent", "unknown")

            allowed_intents = {
                "create_task", "list_tasks", "complete_task",
                "create_reminder", "list_reminders", "complete_reminder",
                "create_schedule", "list_schedule",
                "add_transaction", "get_transactions", "get_summary",
                "unknown",
            }

            if intent not in allowed_intents:
                return {"intent": "unknown", "data": {}}

            parsed_json.setdefault("data", {})

            if parsed_json["data"].get("title"):
                parsed_json["data"]["title"] = self.normalize_task_title(
                    parsed_json["data"]["title"], existing_task_titles
                )

            for field in ["due_date", "remind_at", "event_time", "date"]:
                if parsed_json["data"].get(field):
                    parsed_json["data"][field] = self.parse_datetime(parsed_json["data"][field])

            return parsed_json

        except Exception as e:
            print("[NLP ERROR] Groq parsing failed:", e)
            return self._fallback_parse(text)

    def answer(self, message: str, context: dict) -> str:
        if not self.client:
            return self._fallback_answer(message, context)

        prompt = f"""You are LifePilot, a helpful AI assistant inside a personal productivity app.

Use the live app data below to answer naturally and helpfully.
You can discuss tasks, reminders, schedule, spending, priorities, planning, and general questions.
Keep answers concise and practical.

Live app data:
{json.dumps(context, ensure_ascii=False, default=str)}

User says: "{message}"
"""

        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
            )
            return response.choices[0].message.content.strip() or self._fallback_answer(message, context)

        except Exception as e:
            print("[NLP ERROR] Groq assistant failed:", e)
            return self._fallback_answer(message, context)

    def _fallback_answer(self, message: str, context: dict) -> str:
        tasks = context.get("tasks", [])
        reminders = context.get("reminders", [])
        schedule = context.get("schedule", [])
        spending = context.get("spending", [])

        pending_tasks = [t for t in tasks if not t.get("completed")]
        pending_reminders = [r for r in reminders if not r.get("completed")]
        total_spending = sum(float(i.get("amount") or 0) for i in spending if i.get("type") != "income")

        if "summary" in message.lower() or "overview" in message.lower():
            return (
                f"You have {len(pending_tasks)} pending tasks, "
                f"{len(pending_reminders)} pending reminders, "
                f"{len(schedule)} scheduled events, and "
                f"${total_spending:.2f} in recorded spending."
            )

        if pending_tasks:
            next_task = pending_tasks[0]
            return (
                f"I can help with that. Right now your next focus is "
                f"'{next_task.get('title')}'. You also have "
                f"{len(pending_reminders)} reminders and "
                f"{len(schedule)} schedule items in LifePilot."
            )

        return (
            "I can help you plan tasks, reminders, schedules, and spending. "
            "Try asking for a summary, or say something like "
            "'remind me to study tomorrow at 6'."
        )

    def _fallback_parse(self, text: str) -> dict:
        lower = text.lower().strip()

        if any(p in lower for p in ["list tasks", "show tasks", "my tasks"]):
            return {"intent": "list_tasks", "data": {}}
        if any(p in lower for p in ["list reminders", "show reminders", "my reminders"]):
            return {"intent": "list_reminders", "data": {}}
        if any(p in lower for p in ["list schedule", "show schedule", "my schedule", "calendar"]):
            return {"intent": "list_schedule", "data": {}}

        if lower.startswith("complete "):
            title = re.sub(r"^complete\s+(task|reminder)?\s*", "", text, flags=re.I).strip()
            if "reminder" in lower:
                return {"intent": "complete_reminder", "data": {"title": title}}
            return {"intent": "complete_task", "data": {"title": title}}

        amount_match = re.search(r"(\d+(?:\.\d+)?)", text)
        amount = float(amount_match.group(1)) if amount_match else 0

        if any(w in lower for w in ["spent", "bought", "paid", "expense"]):
            category = self._extract_after_keyword(text, ["on", "for"]) or "General"
            return {"intent": "add_transaction", "data": {
                "type": "expense", "amount": amount, "category": category,
                "date": self.parse_datetime("now"), "description": text,
            }}

        if any(w in lower for w in ["earned", "received", "income"]):
            category = self._extract_after_keyword(text, ["from", "for"]) or "Income"
            return {"intent": "add_transaction", "data": {
                "type": "income", "amount": amount, "category": category,
                "date": self.parse_datetime("now"), "description": text,
            }}

        if any(w in lower for w in ["transaction", "history"]):
            return {"intent": "get_transactions", "data": {}}
        if "summary" in lower and any(w in lower for w in ["finance", "spending", "money"]):
            return {"intent": "get_summary", "data": {}}

        if lower.startswith("remind me") or lower.startswith("reminder") or " remind me " in f" {lower} ":
            title = re.sub(r"^(please\s+)?remind me to\s+", "", text, flags=re.I).strip()
            remind_at = self._extract_datetime_text(text)
            title = self._remove_datetime_text(title, remind_at)
            return {"intent": "create_reminder", "data": {
                "title": title,
                "remind_at": self.parse_datetime(remind_at) if remind_at else ""
            }}

        if any(w in lower for w in ["schedule", "meeting", "appointment", "class", "event", "plan"]):
            title = re.sub(r"^(schedule|plan|add an event|add event)\s+", "", text, flags=re.I).strip()
            event_time = self._extract_datetime_text(text)
            title = self._remove_datetime_text(title, event_time)
            return {"intent": "create_schedule", "data": {
                "title": title or text,
                "event_time": self.parse_datetime(event_time) if event_time else ""
            }}

        if any(w in lower for w in ["task", "todo", "homework", "assignment", "study", "finish", "do "]):
            due_date = self._extract_datetime_text(text)
            return {"intent": "create_task", "data": {
                "title": text.strip(),
                "due_date": self.parse_datetime(due_date) if due_date else "",
                "priority": "medium",
            }}

        return {"intent": "unknown", "data": {}}

    def _extract_after_keyword(self, text: str, keywords: list) -> str:
        for keyword in keywords:
            match = re.search(rf"\b{keyword}\b\s+(.+)", text, re.I)
            if match:
                value = re.sub(r"\b\d+(?:\.\d+)?\b", "", match.group(1)).strip()
                return value or match.group(1).strip()
        return ""

    def _extract_datetime_text(self, text: str) -> str:
        match = re.search(
            r"\b(today|tomorrow|tonight|next\s+\w+|on\s+\w+|at\s+\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b.*",
            text, re.I,
        )
        return match.group(0) if match else ""

    def _remove_datetime_text(self, title: str, datetime_text: str) -> str:
        if not datetime_text:
            return title.strip()
        return title.replace(datetime_text, "").strip(" ,.-") or title.strip()
