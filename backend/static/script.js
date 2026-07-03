// ─────────────────────────────────────────────
//  NAVIGATION
// ─────────────────────────────────────────────
function showSection(sectionId, btnEl) {
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  const target = document.getElementById(sectionId);
  if (target) target.classList.add("active");

  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
  if (btnEl) btnEl.classList.add("active");
}

// ─────────────────────────────────────────────
//  API HELPERS
// ─────────────────────────────────────────────
function handleAuthExpired(res) {
  if (res.status === 401) {
    window.location.href = "/login";
    return true;
  }
  return false;
}

async function apiPost(url, body) {
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (handleAuthExpired(res)) return { status: "error", message: "Session expired." };
    const json = await res.json();
    console.log(`[API] POST ${url}:`, json);
    return json;
  } catch (err) {
    console.error("[API] POST error", url, err);
    return { status: "error", message: "Could not connect to server." };
  }
}

async function apiPut(url, body) {
  try {
    const res = await fetch(url, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    if (handleAuthExpired(res)) return { status: "error", message: "Session expired." };
    const json = await res.json();
    console.log(`[API] PUT ${url}:`, json);
    return json;
  } catch (err) {
    console.error("[API] PUT error", url, err);
    return { status: "error", message: "Could not connect to server." };
  }
}

async function apiDelete(url) {
  try {
    const res = await fetch(url, { method: "DELETE" });
    if (handleAuthExpired(res)) return { status: "error", message: "Session expired." };
    const json = await res.json();
    console.log(`[API] DELETE ${url}:`, json);
    return json;
  } catch (err) {
    console.error("[API] DELETE error", url, err);
    return { status: "error", message: "Could not connect to server." };
  }
}

// ─────────────────────────────────────────────
//  SYNC — load everything from backend
// ─────────────────────────────────────────────
let isSyncing = false;
async function syncData() {
  if (isSyncing) return;
  isSyncing = true;
  try {
    console.log("[SYNC] Starting sync...");
    const response = await fetch("/api/init");
    if (handleAuthExpired(response)) { isSyncing = false; return; }
    const data = await response.json();
    console.log("[SYNC] Data received:", data);

    window.tasks = (data.tasks || []).map(t => ({
      id: t.id, title: t.title || "Untitled", due_date: t.due_date || "",
      priority: t.priority || "", description: t.description || "", completed: !!t.completed
    }));

    window.spending = (data.spending || []).map(s => ({
      id: s.id, title: s.category || s.description || "Expense",
      amount: Number(s.amount) || 0, type: s.type || "expense", date: s.date || ""
    }));

    window.reminders = (data.reminders || []);
    window.schedule  = (data.schedule || []);

    // Don't overwrite notes while the editor is open (avoid clobbering unsaved edits)
    if (!window.noteEditorOpen) {
      window.notes = (data.notes || []);
    }

    renderTasks();
    renderSpending();
    renderReminders();
    renderSchedule();
    renderNotes();
    renderDashNotes();
    updateDashboard();
    console.log("[SYNC] ✅ All data synced and rendered");
  } catch (err) {
    console.error("[SYNC] Failed:", err);
  } finally {
    isSyncing = false;
  }
}

// ─────────────────────────────────────────────
//  RENDER: TASKS
// ─────────────────────────────────────────────
function renderTasks() {
  const container = document.getElementById("taskList");
  if (!container) return;

  if (!window.tasks || window.tasks.length === 0) {
    container.innerHTML = `<p style="color:#999; padding:20px; text-align:center;">No tasks yet. Add one above!</p>`;
    return;
  }

  let html = "";
  window.tasks.forEach(t => {
    html += `
      <div class="task-card">
        <div class="task-info">
          <h3 style="margin:0 0 8px; ${t.completed ? 'text-decoration:line-through;color:#888;' : ''}">${escapeHtml(t.title)}</h3>
          ${t.due_date ? `<p style="margin:4px 0; font-size:12px; color:#999;">📅 Due: ${t.due_date.slice(0,16)}</p>` : ""}
          ${t.priority ? `<p style="margin:4px 0; font-size:12px; color:#999;">Priority: ${t.priority}</p>` : ""}
          <p style="margin:4px 0; font-size:12px; color:#999;">Status: ${t.completed ? "✅ Completed" : "⏳ Pending"}</p>
        </div>
        <div class="task-actions">
          ${t.completed
            ? `<span class="done-badge">Done ✅</span>`
            : `<button onclick="completeTask(${t.id})" style="padding:8px 12px; background:#b91c1c; color:white; border:none; border-radius:8px; cursor:pointer;">Complete</button>`}
          <button class="delete-btn" onclick="deleteTask(${t.id})" style="padding:8px 12px; background:#323232; color:white; border:none; border-radius:8px; cursor:pointer; margin-left:8px;">Delete</button>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

// ─────────────────────────────────────────────
//  RENDER: SPENDING
// ─────────────────────────────────────────────
function renderSpending() {
  const container = document.getElementById("spendingList");
  if (!container) return;

  if (!window.spending || window.spending.length === 0) {
    container.innerHTML = `<p style="color:#999; padding:20px; text-align:center;">No expenses yet. Add one above!</p>`;
    return;
  }

  let html = "";
  window.spending.forEach(s => {
    html += `
      <div class="spending-card">
        <div class="spending-info">
          <h3 style="margin:0 0 8px;">${escapeHtml(s.title)}</h3>
          <p style="margin:4px 0; font-size:12px; color:#999;">💵 $${Number(s.amount).toFixed(2)} | ${s.type} | ${s.date ? s.date.slice(0,10) : 'N/A'}</p>
        </div>
        <div class="spending-actions">
          <button class="delete-btn" onclick="deleteSpending(${s.id})" style="padding:8px 12px; background:#323232; color:white; border:none; border-radius:8px; cursor:pointer;">Delete</button>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

// ─────────────────────────────────────────────
//  RENDER: REMINDERS
// ─────────────────────────────────────────────
function renderReminders() {
  const container = document.getElementById("reminderList");
  if (!container) return;

  if (!window.reminders || window.reminders.length === 0) {
    container.innerHTML = `<p style="color:#999; padding:20px; text-align:center;">No reminders yet. Add one above!</p>`;
    return;
  }

  let html = "";
  window.reminders.forEach(r => {
    const label = r.title || r.text || "Untitled";
    html += `
      <div class="reminder-card">
        <div class="reminder-info">
          <h3 style="margin:0 0 8px;">${escapeHtml(label)}</h3>
          ${r.remind_at ? `<p style="margin:4px 0; font-size:12px; color:#999;">🔔 Remind: ${r.remind_at}</p>` : ""}
        </div>
        <div class="reminder-actions">
          <button class="delete-btn" onclick="deleteReminder(${r.id})" style="padding:8px 12px; background:#323232; color:white; border:none; border-radius:8px; cursor:pointer;">Delete</button>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

// ─────────────────────────────────────────────
//  RENDER: SCHEDULE
// ─────────────────────────────────────────────
function renderSchedule() {
  const container = document.getElementById("scheduleList");
  if (!container) return;

  if (!window.schedule || window.schedule.length === 0) {
    container.innerHTML = `<p style="color:#999; padding:20px; text-align:center;">No events yet. Add one above!</p>`;
    return;
  }

  let html = "";
  window.schedule.forEach(s => {
    html += `
      <div class="schedule-card">
        <div class="schedule-info">
          <h3 style="margin:0 0 8px;">${escapeHtml(s.title)}</h3>
          <div style="margin-top:6px;">
            ${s.date ? `<p style="margin:4px 0; font-size:12px; color:#999;">📅 ${s.date}</p>` : ""}
            ${s.time ? `<p style="margin:4px 0; font-size:12px; color:#999;">🕐 ${s.time}</p>` : ""}
            ${s.duration ? `<p style="margin:4px 0; font-size:12px; color:#999;">⏱️ ${s.duration}</p>` : ""}
            ${s.notes ? `<p style="margin:4px 0; font-size:12px; color:#999;">📝 ${escapeHtml(s.notes)}</p>` : ""}
          </div>
        </div>
        <div class="schedule-actions">
          <button class="delete-btn" onclick="deleteSchedule(${s.id})" style="padding:8px 12px; background:#323232; color:white; border:none; border-radius:8px; cursor:pointer;">Delete</button>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

// ─────────────────────────────────────────────
//  RENDER: NOTES
// ─────────────────────────────────────────────
let currentNoteId = null;
let notesFilterText = "";

function renderNotes() {
  const container = document.getElementById("notesList");
  if (!container) return;

  let notes = window.notes || [];

  if (notesFilterText.trim()) {
    const q = notesFilterText.toLowerCase();
    notes = notes.filter(n =>
      (n.title || "").toLowerCase().includes(q) ||
      (n.content || "").toLowerCase().includes(q)
    );
  }

  if (!notes.length) {
    container.innerHTML = `<p style="color:#999; padding:20px; text-align:center; grid-column: 1/-1;">No notes yet. Tap "+ New Note" to create one!</p>`;
    return;
  }

  let html = "";
  notes.forEach(n => {
    const preview = (n.content || "").slice(0, 120);
    const updated = n.updated_at ? formatNoteDate(n.updated_at) : "";
    html += `
      <div class="note-card ${n.pinned ? 'pinned' : ''}" onclick="openNoteEditor(${n.id})">
        ${n.pinned ? `<div class="note-pin-indicator">📌</div>` : ""}
        <h3 class="note-card-title">${escapeHtml(n.title || "Untitled Note")}</h3>
        <p class="note-card-preview">${escapeHtml(preview)}${(n.content || "").length > 120 ? "…" : ""}</p>
        <div class="note-card-footer">
          <span class="note-card-date">${updated}</span>
          <button class="note-card-delete" onclick="event.stopPropagation(); quickDeleteNote(${n.id})">🗑️</button>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

function renderDashNotes() {
  const container = document.getElementById("dashNotesList");
  if (!container) return;
  const notes = (window.notes || []).slice(0, 3);
  if (!notes.length) {
    container.innerHTML = `<p style="color:#808098;font-size:12px">No notes yet. Create one!</p>`;
    return;
  }
  container.innerHTML = notes.map(n => `
    <div class="dash-note-item" onclick="showSection('notes', document.querySelectorAll('.nav-btn')[5]); setTimeout(()=>openNoteEditor(${n.id}), 150)">
      <div class="dash-note-title">${n.pinned ? '📌 ' : ''}${escapeHtml(n.title || 'Untitled Note')}</div>
      <div class="dash-note-preview">${escapeHtml((n.content || '').slice(0, 50))}</div>
    </div>
  `).join("");
}

function filterNotes(value) {
  notesFilterText = value;
  renderNotes();
}

function formatNoteDate(dateStr) {
  try {
    const d = new Date(dateStr.replace(" ", "T"));
    const now = new Date();
    const diffMs = now - d;
    const diffMin = diffMs / 60000;
    if (diffMin < 1) return "Just now";
    if (diffMin < 60) return `${Math.floor(diffMin)}m ago`;
    if (diffMin < 1440) return `${Math.floor(diffMin / 60)}h ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return dateStr;
  }
}

// ─────────────────────────────────────────────
//  NOTES: EDITOR MODAL
// ─────────────────────────────────────────────
function openNoteEditor(noteId = null) {
  window.noteEditorOpen = true;
  currentNoteId = noteId;
  const modal       = document.getElementById("noteModal");
  const titleInput  = document.getElementById("noteTitle");
  const contentArea = document.getElementById("noteContent");
  const timestampEl = document.getElementById("noteTimestamp");
  const deleteBtn   = document.getElementById("noteDeleteBtn");
  const pinBtn      = document.getElementById("notePinBtn");

  if (noteId) {
    const note = (window.notes || []).find(n => n.id === noteId);
    if (note) {
      titleInput.value  = note.title || "";
      contentArea.value = note.content || "";
      timestampEl.textContent = note.updated_at ? `Last edited ${formatNoteDate(note.updated_at)}` : "";
      deleteBtn.classList.remove("hidden");
      pinBtn.classList.toggle("active", !!note.pinned);
      window.editorPinned = !!note.pinned;
    }
  } else {
    titleInput.value  = "";
    contentArea.value = "";
    timestampEl.textContent = "New note";
    deleteBtn.classList.add("hidden");
    pinBtn.classList.remove("active");
    window.editorPinned = false;
  }

  modal.classList.remove("hidden");
  setTimeout(() => titleInput.focus(), 50);
}

function closeNoteEditor() {
  window.noteEditorOpen = false;
  document.getElementById("noteModal").classList.add("hidden");
  currentNoteId = null;
  syncData();
}

function toggleEditorPin() {
  window.editorPinned = !window.editorPinned;
  document.getElementById("notePinBtn").classList.toggle("active", window.editorPinned);
}

async function saveNote() {
  const title   = document.getElementById("noteTitle").value.trim() || "Untitled Note";
  const content = document.getElementById("noteContent").value;
  const pinned  = !!window.editorPinned;

  window.notes = window.notes || [];

  if (currentNoteId) {
    const res = await apiPut(`/api/notes/${currentNoteId}`, { title, content, pinned });
    if (res.status === "success") {
      const idx = window.notes.findIndex(n => n.id === currentNoteId);
      const updated = { id: currentNoteId, title, content, pinned, updated_at: res.data?.updated_at || new Date().toISOString() };
      if (idx >= 0) window.notes[idx] = { ...window.notes[idx], ...updated };
      else window.notes.unshift(updated);
    }
  } else {
    const res = await apiPost("/api/notes", { title, content, pinned });
    if (res.status === "success" && res.data) {
      currentNoteId = res.data.id;
      window.notes.unshift(res.data);
    }
  }

  // Re-sort: pinned first, then by updated_at
  window.notes.sort((a, b) => (b.pinned - a.pinned) || (new Date(b.updated_at) - new Date(a.updated_at)));

  window.noteEditorOpen = false;
  renderNotes();
  renderDashNotes();
  closeNoteEditorSilent();
  syncData();
}

function closeNoteEditorSilent() {
  document.getElementById("noteModal").classList.add("hidden");
  currentNoteId = null;
}

async function deleteCurrentNote() {
  if (!currentNoteId) return;
  if (!confirm("Delete this note?")) return;
  await apiDelete(`/api/notes/${currentNoteId}`);
  window.noteEditorOpen = false;
  closeNoteEditorSilent();
  await syncData();
}

async function quickDeleteNote(id) {
  if (!confirm("Delete this note?")) return;
  await apiDelete(`/api/notes/${id}`);
  await syncData();
}

// Auto-save on close via Escape key
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    const modal = document.getElementById("noteModal");
    if (modal && !modal.classList.contains("hidden")) {
      saveNote();
    }
  }
});

// ─────────────────────────────────────────────
//  DASHBOARD STATS
// ─────────────────────────────────────────────
function updateDashboard() {
  const total      = (window.tasks || []).length;
  const completed  = (window.tasks || []).filter(t => t.completed).length;
  const pending    = total - completed;
  const totalSpend = (window.spending || []).reduce((s, e) => s + Number(e.amount || 0), 0);
  const remCount   = (window.reminders || []).length;
  const schedCount = (window.schedule || []).length;

  setText("totalTasksCard",     total);
  setText("completedTasksCard", completed);
  setText("remindersCard",      remCount);
  setText("dashboardSpending",  `$${totalSpend.toFixed(2)}`);

  setText("todayCompleted", completed);
  setText("todayPending",   pending);
  setText("todaySpending",  `$${totalSpend.toFixed(2)}`);
  setText("tomorrowEvents", schedCount);

  setText("totalSpending", `$${totalSpend.toFixed(2)}`);

  updateSpendingChart();

  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  setText("productivityPct", `${pct}%`);
  const arc = document.getElementById("productivityArc");
  if (arc) {
    const circumference = 251.2;
    arc.setAttribute("stroke-dashoffset", (circumference - (pct / 100) * circumference).toFixed(1));
  }

  updateUpcomingPanel();
}

// ─────────────────────────────────────────────
//  SPENDING CHART (real data, smooth line chart)
// ─────────────────────────────────────────────
function updateSpendingChart() {
  const dayNames = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
  const range = document.getElementById("spendRangeSelect")?.value || "week";

  const now = new Date();
  const dow = now.getDay() === 0 ? 6 : now.getDay() - 1; // 0=Mon ... 6=Sun
  const monday = new Date(now);
  monday.setDate(now.getDate() - dow);
  monday.setHours(0, 0, 0, 0);

  let totals, labels, txnCounts;

  if (range === "month") {
    // Group by week-of-month (up to 5 buckets)
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
    totals = new Array(5).fill(0);
    txnCounts = new Array(5).fill(0);
    labels = ["W1", "W2", "W3", "W4", "W5"];
    (window.spending || []).forEach(s => {
      if (s.type === "income" || !s.date) return;
      const d = new Date(s.date.replace(" ", "T"));
      if (isNaN(d) || d.getMonth() !== now.getMonth() || d.getFullYear() !== now.getFullYear()) return;
      const week = Math.min(Math.floor((d.getDate() - 1) / 7), 4);
      totals[week] += Number(s.amount) || 0;
      txnCounts[week]++;
    });
  } else {
    totals = new Array(7).fill(0);
    txnCounts = new Array(7).fill(0);
    labels = dayNames;
    (window.spending || []).forEach(s => {
      if (s.type === "income" || !s.date) return;
      const d = new Date(s.date.replace(" ", "T"));
      if (isNaN(d)) return;
      const diffDays = Math.floor((d - monday) / 86400000);
      if (diffDays >= 0 && diffDays < 7) {
        totals[diffDays] += Number(s.amount) || 0;
        txnCounts[diffDays]++;
      }
    });
  }

  const periodTotal = totals.reduce((a, b) => a + b, 0);
  setText("weekSpending", `$${periodTotal.toFixed(2)}`);
  document.querySelector(".spend-week-label").textContent = range === "month" ? "This Month" : "This Week";

  renderLineChart(totals, labels);
  updateSpendStats(totals, labels, txnCounts);
}

function renderLineChart(totals, labels) {
  const svg = document.getElementById("spendLineChart");
  if (!svg) return;

  const W = 700, H = 220;
  const padLeft = 50, padRight = 20, padTop = 40, padBottom = 30;
  const chartW = W - padLeft - padRight;
  const chartH = H - padTop - padBottom;

  const max = Math.max(...totals, 1);
  const niceMax = Math.ceil(max / 100) * 100 || 100;

  const n = totals.length;
  const points = totals.map((val, i) => {
    const x = padLeft + (n === 1 ? chartW / 2 : (i / (n - 1)) * chartW);
    const y = padTop + chartH - (val / niceMax) * chartH;
    return { x, y, val };
  });

  // Grid lines + Y axis labels (4 steps)
  let gridHtml = "";
  const steps = 4;
  for (let s = 0; s <= steps; s++) {
    const val = (niceMax / steps) * s;
    const y = padTop + chartH - (val / niceMax) * chartH;
    gridHtml += `<line x1="${padLeft}" y1="${y}" x2="${W - padRight}" y2="${y}" stroke="#26263a" stroke-width="1" />`;
    gridHtml += `<text x="${padLeft - 10}" y="${y + 4}" text-anchor="end" font-size="11" fill="#7a7a92">$${Math.round(val)}</text>`;
  }

  // Smooth path (catmull-rom-ish via simple bezier between points)
  let pathD = "";
  if (points.length === 1) {
    pathD = `M ${points[0].x} ${points[0].y}`;
  } else {
    pathD = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i], p1 = points[i + 1];
      const midX = (p0.x + p1.x) / 2;
      pathD += ` C ${midX} ${p0.y}, ${midX} ${p1.y}, ${p1.x} ${p1.y}`;
    }
  }

  const areaD = pathD + ` L ${points[points.length - 1].x} ${padTop + chartH} L ${points[0].x} ${padTop + chartH} Z`;

  let dotsHtml = "";
  let valueLabelsHtml = "";
  let xLabelsHtml = "";
  points.forEach((p, i) => {
    dotsHtml += `<circle cx="${p.x}" cy="${p.y}" r="5" fill="#8b7ae8" stroke="#13131a" stroke-width="2" />`;
    if (p.val > 0) {
      valueLabelsHtml += `<text x="${p.x}" y="${p.y - 14}" text-anchor="middle" font-size="12" font-weight="700" fill="#e8e8f0">$${Math.round(p.val)}</text>`;
    }
    xLabelsHtml += `<text x="${p.x}" y="${H - 6}" text-anchor="middle" font-size="11" fill="#9090a8">${labels[i]}</text>`;
  });

  svg.innerHTML = `
    <defs>
      <linearGradient id="spendAreaGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#8b7ae8" stop-opacity="0.35" />
        <stop offset="100%" stop-color="#8b7ae8" stop-opacity="0" />
      </linearGradient>
    </defs>
    ${gridHtml}
    <path d="${areaD}" fill="url(#spendAreaGrad)" stroke="none" />
    <path d="${pathD}" fill="none" stroke="#8b7ae8" stroke-width="2.5" stroke-linecap="round" />
    ${dotsHtml}
    ${valueLabelsHtml}
    ${xLabelsHtml}
  `;
}

function updateSpendStats(totals, labels, txnCounts) {
  const n = totals.length;
  let maxIdx = 0, minIdx = 0;
  for (let i = 1; i < n; i++) {
    if (totals[i] > totals[maxIdx]) maxIdx = i;
    if (totals[i] < totals[minIdx]) minIdx = i;
  }
  const sum = totals.reduce((a, b) => a + b, 0);
  const activeDays = totals.filter(t => t > 0).length || 1;
  const avg = sum / activeDays;
  const totalTxns = (txnCounts || []).reduce((a, b) => a + b, 0);

  setText("highestDayName", labels[maxIdx]);
  setText("highestDayVal", `$${totals[maxIdx].toFixed(2)}`);
  setText("lowestDayName", labels[minIdx]);
  setText("lowestDayVal", `$${totals[minIdx].toFixed(2)}`);
  setText("avgDailyVal", `$${avg.toFixed(2)}`);
  setText("totalTxnVal", totalTxns);
}

function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}

function updateUpcomingPanel() {
  const container = document.getElementById("upcomingTasks");
  if (!container) return;
  const pendingTasks = (window.tasks || []).filter(t => !t.completed).slice(0, 3);
  if (!pendingTasks.length) {
    container.innerHTML = `<p style="color:#808098;font-size:12px">All tasks completed! 🎉</p>`;
    return;
  }
  const colors   = ["#a070e0", "#3878dc", "#34c759", "#ffaa00", "#e05252"];
  const badges   = ["High", "Medium", "Low"];
  const badgeCls = ["high", "med", "low"];
  container.innerHTML = pendingTasks.map((t, i) => `
    <div class="upcoming-item">
      <div class="upcoming-dot" style="background:${colors[i % colors.length]}"></div>
      <div class="upcoming-info">
        <div class="upcoming-name">${escapeHtml(t.title)}</div>
        <div class="upcoming-time">${t.due_date ? t.due_date.slice(0,10) : "No due date"}</div>
      </div>
      <span class="priority-badge ${badgeCls[i % 3]}">${t.priority || badges[i % 3]}</span>
    </div>
  `).join("");
}

// ─────────────────────────────────────────────
//  TASKS
// ─────────────────────────────────────────────
async function addTask() {
  const input = document.getElementById("taskInput");
  const text = input?.value.trim();
  if (!text) { alert("Please enter a task!"); return; }
  setLoading("taskAddBtn", true);
  const res = await apiPost("/api/nlp", { message: text });
  setLoading("taskAddBtn", false);
  if (res.status !== "success") {
    alert(res.message || "Could not add task. Try: 'Finish math by Friday'");
    return;
  }
  input.value = "";
  await syncData();
}

async function completeTask(id) {
  await fetch(`/api/tasks/complete/${id}`, { method: "POST" });
  await syncData();
}

async function deleteTask(id) {
  await apiDelete(`/api/tasks/${id}`);
  await syncData();
}

// ─────────────────────────────────────────────
//  REMINDERS
// ─────────────────────────────────────────────
async function addReminder() {
  const input = document.getElementById("reminderInput");
  const text = input?.value.trim();
  if (!text) { alert("Please enter a reminder!"); return; }
  setLoading("reminderAddBtn", true);
  const res = await apiPost("/api/reminders", { text, remind_at: "" });
  setLoading("reminderAddBtn", false);
  if (res.status !== "success") {
    alert(res.message || "Could not add reminder.");
    return;
  }
  input.value = "";
  await syncData();
}

async function deleteReminder(id) {
  await apiDelete(`/api/reminders/${id}`);
  await syncData();
}

// ─────────────────────────────────────────────
//  SCHEDULE
// ─────────────────────────────────────────────
async function addScheduleItem() {
  const titleInput = document.getElementById("scheduleTitleInput");
  const timeInput  = document.getElementById("scheduleTimeInput");
  const dateInput  = document.getElementById("scheduleDateInput");
  const title = titleInput?.value.trim();
  if (!title) { alert("Please enter an event title!"); return; }
  const time  = timeInput?.value.trim()  || "";
  const date  = dateInput?.value.trim()  || "";
  setLoading("scheduleAddBtn", true);
  const res = await apiPost("/api/schedule", { title, date, time, duration: "", notes: "" });
  setLoading("scheduleAddBtn", false);
  if (res.status !== "success") {
    alert(res.message || "Could not add event.");
    return;
  }
  titleInput.value = "";
  if (timeInput) timeInput.value = "";
  if (dateInput) dateInput.value = "";
  await syncData();
}

async function deleteSchedule(id) {
  await apiDelete(`/api/schedule/${id}`);
  await syncData();
}

// ─────────────────────────────────────────────
//  SPENDING
// ─────────────────────────────────────────────
async function addExpense() {
  const input = document.getElementById("expenseTitleInput");
  const text  = input?.value.trim();
  if (!text) { alert("Please enter an expense!"); return; }
  setLoading("spendingAddBtn", true);
  const res = await apiPost("/api/nlp", { message: text });
  setLoading("spendingAddBtn", false);
  if (res.status !== "success") {
    alert(res.message || "Could not add expense. Try: 'Coffee 5' or 'I spent 20 on food'");
    return;
  }
  input.value = "";
  await syncData();
}

async function deleteSpending(id) {
  await apiDelete(`/api/finance/${id}`);
  await syncData();
}

// ─────────────────────────────────────────────
//  AI CHAT
// ─────────────────────────────────────────────
async function sendMessage() {
  const input    = document.getElementById("user-input");
  const messages = document.getElementById("messages");
  const text     = input?.value.trim();
  if (!text || !messages) return;

  appendMessage(messages, "You", text, "#e8e8f0");
  input.value = "";

  const typingId = "typing-" + Date.now();
  messages.innerHTML += `<p id="${typingId}" style="color:#606078;font-style:italic;margin:6px 0;font-size:13px">LifePilot is thinking...</p>`;
  messages.scrollTop = messages.scrollHeight;

  const res   = await apiPost("/api/chat", { message: text });
  const reply = res?.message || "Sorry, I couldn't get a response.";

  document.getElementById(typingId)?.remove();
  appendMessage(messages, "LifePilot", reply, "#b91c1c");
  messages.scrollTop = messages.scrollHeight;

  await syncData();
}

function appendMessage(container, sender, text, color) {
  const p = document.createElement("p");
  p.style.cssText = "margin:10px 0;line-height:1.5;font-size:13px";
  p.innerHTML = `<strong style="color:${color}">${sender}:</strong> <span style="color:#c0c0d8;white-space:pre-wrap">${escapeHtml(text)}</span>`;
  container.appendChild(p);
}

// ─────────────────────────────────────────────
//  VOICE INPUT
// ─────────────────────────────────────────────
async function startVoiceInput(targetInputId, event) {
  const targetInput = document.getElementById(targetInputId);
  const micBtn      = event?.currentTarget;
  if (!targetInput) return;
  if (micBtn) micBtn.classList.add("recording");
  try {
    const res  = await fetch("/voice/listen", { method: "POST" });
    const data = await res.json();
    if (data.status === "success" && data.text?.trim()) {
      targetInput.value = data.text.trim();
      targetInput.focus();
      if      (targetInputId === "user-input")         await sendMessage();
      else if (targetInputId === "taskInput")           await addTask();
      else if (targetInputId === "reminderInput")       await addReminder();
      else if (targetInputId === "scheduleTitleInput")  await addScheduleItem();
      else if (targetInputId === "expenseTitleInput")   await addExpense();
    } else {
      alert(data.message || "No speech detected.");
    }
  } catch (err) {
    console.error("[VOICE] Error:", err);
    alert("Voice input failed.");
  } finally {
    if (micBtn) micBtn.classList.remove("recording");
  }
}

// ─────────────────────────────────────────────
//  UTILS
// ─────────────────────────────────────────────
function escapeHtml(text) {
  if (!text) return "";
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function setLoading(btnId, loading) {
  const btn = document.getElementById(btnId);
  if (!btn) return;
  btn.disabled = loading;
  if (loading) btn.dataset.orig = btn.textContent, btn.textContent = "...";
  else btn.textContent = btn.dataset.orig || btn.textContent;
}

// ─────────────────────────────────────────────
//  INIT
// ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  console.log("[INIT] LifePilot initializing...");
  window.tasks     = [];
  window.spending  = [];
  window.reminders = [];
  window.schedule  = [];
  window.notes     = [];
  window.noteEditorOpen = false;

  syncData();

  [
    ["taskInput",          addTask],
    ["reminderInput",      addReminder],
    ["scheduleTitleInput", addScheduleItem],
    ["expenseTitleInput",  addExpense],
    ["user-input",         sendMessage],
  ].forEach(([id, fn]) => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("keydown", e => { if (e.key === "Enter") fn(); });
  });

  setInterval(() => { syncData(); }, 5000);

  console.log("[INIT] ✅ LifePilot ready!");
});