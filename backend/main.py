import sys
import os
import secrets as secrets_module
from dotenv import load_dotenv
from groq import Groq
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel
from typing import Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, ".env")
load_dotenv(env_path)
sys.path.append(os.path.join(BASE_DIR, "src"))

from nlp.parser import NLPParser
from tasks.task_manager import TaskManager
from tasks.reminder_manager import ReminderManager
from tasks.schedule_manager import ScheduleManager
from tasks.notes_manager import NotesManager
from finance.finance_manager import FinanceManager
from audio.speech_recognizer import SpeechRecognizer
from auth.auth_manager import AuthManager

sys.path.append(os.path.join(BASE_DIR, "data"))
from migrations import run_migrations

# ── Database migration (runs on every startup, idempotent) ────────────────────
run_migrations()

# ── App setup ────────────────────────────────────────────────────────────────────
app = FastAPI()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    # Falls back to a random key (sessions won't survive a restart) and warns loudly.
    SECRET_KEY = secrets_module.token_hex(32)
    print("[WARNING] SECRET_KEY not set in .env — using a temporary one. "
          "Everyone will be logged out on restart. Add SECRET_KEY to backend/.env to fix this.")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, same_site="lax", max_age=60 * 60 * 24 * 14)

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("GROQ_API_KEY not found in environment variables")
groq_client = Groq(api_key=groq_api_key)

auth_manager = AuthManager()

# ── Auth dependency ──────────────────────────────────────────────────────────────
def get_current_user_id(request: Request) -> int:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id

# ── Request models ─────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

class ReminderRequest(BaseModel):
    text: str
    remind_at: str = ""

class ScheduleRequest(BaseModel):
    title: str
    date: str = ""
    time: str = ""
    duration: str = ""
    notes: str = ""

class NoteRequest(BaseModel):
    title: Optional[str] = "Untitled Note"
    content: Optional[str] = ""
    pinned: Optional[bool] = False

class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    identifier: str
    password: str

# ── Context builder ────────────────────────────────────────────────────────────
def build_context(user_id, task_mgr, finance_mgr, reminder_mgr, schedule_mgr, notes_mgr) -> str:
    tasks     = task_mgr.list_tasks(user_id).get("data", [])
    spending  = finance_mgr.get_transactions(user_id).get("data", [])
    summary   = finance_mgr.get_summary(user_id).get("data", {})
    reminders = reminder_mgr.list_reminders(user_id).get("data", [])
    events    = schedule_mgr.list_events(user_id).get("data", [])
    notes     = notes_mgr.list_notes(user_id).get("data", [])

    pending   = [t for t in tasks if not t.get("completed")]
    completed = [t for t in tasks if t.get("completed")]

    lines = [f"=== LifePilot User Data ({datetime.now().strftime('%A %B %d %Y, %H:%M')}) ==="]

    lines.append("\nTASKS (Pending):")
    if pending:
        for t in pending:
            due = f" | due: {t['due_date']}" if t.get("due_date") else ""
            pri = f" [{t.get('priority','').upper()}]" if t.get("priority") else ""
            lines.append(f"  • {t['title']}{pri}{due}")
    else:
        lines.append("  No pending tasks.")

    lines.append("\nTASKS (Completed):")
    lines.extend([f"  ✓ {t['title']}" for t in completed] or ["  No completed tasks yet."])

    lines.append("\nREMINDERS:")
    if reminders:
        for r in reminders:
            at = f" (remind at: {r['remind_at']})" if r.get("remind_at") else ""
            lines.append(f"  • {r.get('title') or r.get('text','')}{at}")
    else:
        lines.append("  No reminders.")

    lines.append("\nSCHEDULE/EVENTS:")
    if events:
        for e in events:
            when = ""
            if e.get("date"):     when += f" on {e['date']}"
            if e.get("time"):     when += f" at {e['time']}"
            if e.get("duration"): when += f" ({e['duration']})"
            notes_txt = f" — {e['notes']}" if e.get("notes") else ""
            lines.append(f"  • {e['title']}{when}{notes_txt}")
    else:
        lines.append("  No scheduled events.")

    lines.append("\nNOTES:")
    if notes:
        for n in notes:
            pin = " 📌" if n.get("pinned") else ""
            preview = (n.get("content") or "")[:80].replace("\n", " ")
            lines.append(f"  • {n['title']}{pin}: {preview}")
    else:
        lines.append("  No notes.")

    lines.append("\nSPENDING:")
    if spending:
        for s in spending:
            amt = float(s.get('amount', 0))
            cat = s.get('category', 'Other')
            date_str = str(s.get('date', ''))[:10]
            lines.append(f"  • {cat}: ${amt:.2f} — {date_str}")
        lines.append(f"\n  ── SUMMARY ──")
        lines.append(f"  Total expenses: ${float(summary.get('total_expenses', 0)):.2f}")
        lines.append(f"  Total income:   ${float(summary.get('total_income', 0)):.2f}")
        lines.append(f"  Balance:        ${float(summary.get('balance', 0)):.2f}")
    else:
        lines.append("  No spending records.")

    return "\n".join(lines)

SYSTEM_PROMPT = """You are LifePilot, a smart personal productivity AI assistant.

Your job:
- Answer questions about the user's tasks, reminders, schedule, notes, and spending
- Give practical advice on productivity, time management, and budgeting
- When asked to plan a day/week, build a detailed schedule using their existing data
- Be encouraging, friendly, and concise (2-4 sentences) unless they ask for details
- Never make up data — only refer to what you see in the context below

When building schedules: format clearly with times, durations, and helpful notes."""

class LifePilotApp:
    def __init__(self):
        self.parser           = NLPParser()
        self.task_manager     = TaskManager()
        self.reminder_manager = ReminderManager()
        self.schedule_manager = ScheduleManager()
        self.finance_manager  = FinanceManager()
        self.notes_manager    = NotesManager()
        self.speech_recognizer = SpeechRecognizer()
        # chat history is per-user, since this app instance is shared by everyone
        self.chat_history_by_user = {}

    def ai_chat(self, user_id: int, user_message: str) -> str:
        context = build_context(
            user_id, self.task_manager, self.finance_manager,
            self.reminder_manager, self.schedule_manager, self.notes_manager
        )
        system_with_context = SYSTEM_PROMPT + "\n\n" + context

        history = self.chat_history_by_user.setdefault(user_id, [])
        history.append({"role": "user", "content": user_message})

        messages = [{"role": "system", "content": system_with_context}]
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        try:
            response = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                max_tokens=1024,
            )
            reply = response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[BACKEND] Groq chat error: {e}")
            reply = "Sorry, I'm having trouble connecting right now."
        history.append({"role": "assistant", "content": reply})
        return reply

    def handle_nlp(self, user_id: int, text: str) -> dict:
        print(f"[BACKEND] NLP: {text}")
        lower = text.lower().strip()
        if lower in ["summary", "finance summary"]:
            return self.finance_manager.get_summary(user_id)
        if lower in ["tasks", "list tasks"]:
            return self.task_manager.list_tasks(user_id)
        if lower == "clear all":
            self.task_manager.clear_all_tasks(user_id)
            self.finance_manager.clear_all_transactions(user_id)
            return {"status": "success", "message": "All tasks and expenses cleared.", "data": {}}
        existing_titles = [t["title"] for t in self.task_manager.list_tasks(user_id).get("data", [])]
        parsed = self.parser.parse(text, existing_task_titles=existing_titles)
        print(f"[BACKEND] Parsed: {parsed}")
        intent = parsed.get("intent", "unknown")
        data   = parsed.get("data", {})
        if intent == "create_task":
            return self.task_manager.create_task(user_id, data)
        if intent == "add_transaction":
            data["type"] = data.get("type") or "expense"
            return self.finance_manager.add_transaction(user_id, data)
        if intent == "add_reminder":
            return self.reminder_manager.add_reminder(user_id, data)
        if intent == "list_reminders":
            return self.reminder_manager.list_reminders(user_id)
        if intent == "add_schedule":
            return self.schedule_manager.add_event(user_id, data)
        if intent == "list_schedule":
            return self.schedule_manager.list_events(user_id)
        return {"status": "error", "message": "I didn't understand that. Try being more specific."}

pilot = LifePilotApp()

# ── Auth pages ───────────────────────────────────────────────────────────────────
@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/")
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def serve_signup(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(url="/")
    return templates.TemplateResponse("signup.html", {"request": request})

# ── Auth API ─────────────────────────────────────────────────────────────────────
@app.post("/api/auth/signup")
async def signup(req: SignupRequest, request: Request):
    result = auth_manager.signup(req.username, req.email, req.password)
    if result.get("status") == "success":
        user = result["data"]
        request.session["user_id"] = user["id"]
        request.session["username"] = user["username"]
    return JSONResponse(result)

@app.post("/api/auth/login")
async def login(req: LoginRequest, request: Request):
    result = auth_manager.login(req.identifier, req.password)
    if result.get("status") == "success":
        user = result["data"]
        request.session["user_id"] = user["id"]
        request.session["username"] = user["username"]
    return JSONResponse(result)

@app.post("/api/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return JSONResponse({"status": "success", "message": "Logged out."})

@app.get("/api/auth/me")
async def me(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return JSONResponse({"status": "error", "message": "Not authenticated"}, status_code=401)
    return JSONResponse({"status": "success", "data": {"id": user_id, "username": request.session.get("username")}})

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("index.html", {
        "request": request,
        "username": request.session.get("username", "")
    })

@app.get("/api/init")
async def get_initial_data(user_id: int = Depends(get_current_user_id)):
    return {
        "tasks":     pilot.task_manager.list_tasks(user_id).get("data", []),
        "spending":  pilot.finance_manager.get_transactions(user_id).get("data", []),
        "reminders": pilot.reminder_manager.list_reminders(user_id).get("data", []),
        "schedule":  pilot.schedule_manager.list_events(user_id).get("data", []),
        "notes":     pilot.notes_manager.list_notes(user_id).get("data", []),
    }

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, user_id: int = Depends(get_current_user_id)):
    reply = pilot.ai_chat(user_id, request.message)
    return JSONResponse({"status": "success", "message": reply})

@app.post("/api/nlp")
async def nlp_endpoint(request: ChatRequest, user_id: int = Depends(get_current_user_id)):
    result = pilot.handle_nlp(user_id, request.message)
    return JSONResponse(result)

# Tasks
@app.post("/api/tasks/complete/{task_id}")
async def complete_task(task_id: int, user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.task_manager.complete_task(user_id, task_id))

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int, user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.task_manager.delete_task(user_id, task_id))

# Finance
@app.delete("/api/finance/{trans_id}")
async def delete_spending(trans_id: int, user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.finance_manager.delete_transaction(user_id, trans_id))

# Reminders
@app.post("/api/reminders")
async def add_reminder(req: ReminderRequest, user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.reminder_manager.add_reminder(user_id, {"text": req.text, "remind_at": req.remind_at}))

@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int, user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.reminder_manager.delete_reminder(user_id, reminder_id))

# Schedule
@app.post("/api/schedule")
async def add_schedule(req: ScheduleRequest, user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.schedule_manager.add_event(user_id, {
        "title": req.title, "date": req.date,
        "time": req.time, "duration": req.duration, "notes": req.notes
    }))

@app.delete("/api/schedule/{event_id}")
async def delete_schedule(event_id: int, user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.schedule_manager.delete_event(user_id, event_id))

# Notes
@app.get("/api/notes")
async def list_notes(user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.notes_manager.list_notes(user_id))

@app.post("/api/notes")
async def create_note(req: NoteRequest, user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.notes_manager.create_note(user_id, {
        "title": req.title, "content": req.content, "pinned": req.pinned
    }))

@app.put("/api/notes/{note_id}")
async def update_note(note_id: int, req: NoteRequest, user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.notes_manager.update_note(user_id, note_id, {
        "title": req.title, "content": req.content, "pinned": req.pinned
    }))

@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: int, user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.notes_manager.delete_note(user_id, note_id))

@app.post("/api/notes/{note_id}/pin")
async def toggle_pin(note_id: int, user_id: int = Depends(get_current_user_id)):
    return JSONResponse(pilot.notes_manager.toggle_pin(user_id, note_id))

# Voice
@app.post("/voice/listen")
async def voice_listen(user_id: int = Depends(get_current_user_id)):
    text = pilot.speech_recognizer.listen()
    if text:
        return JSONResponse({"status": "success", "text": text})
    return JSONResponse({"status": "error", "text": "", "message": "No speech detected."})
