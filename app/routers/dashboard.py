import json
import logging
import os
import pandas as pd
from pathlib import Path
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse

logger = logging.getLogger("dashboard")
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

CONFIG_FILE = "config.json"
DATA_DIR = Path("d:/university_counselor/data")
LOGS_FILE = DATA_DIR / "conversation_logs.csv"
LEADS_FILE = DATA_DIR / "leads.xlsx"

def read_config():
    config = {}
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)

    def get_val(key, env_key, default=""):
        return config.get(key) if config.get(key) else os.getenv(env_key, default)

    return {
        "first_line": get_val("first_line", "FIRST_LINE", "Namaste! Welcome to TMU Admission Cell. How may I assist you with your admission journey?"),
        "agent_instructions": get_val("agent_instructions", "AGENT_INSTRUCTIONS", ""),
        "stt_min_endpointing_delay": float(get_val("stt_min_endpointing_delay", "STT_MIN_ENDPOINTING_DELAY", 0.6)),
        "llm_model": get_val("llm_model", "LLM_MODEL", "gpt-4o-mini"),
        "tts_voice": get_val("tts_voice", "TTS_VOICE", "kavya"),
        "tts_language": get_val("tts_language", "TTS_LANGUAGE", "hi-IN"),
        **config
    }

def write_config(data):
    config = read_config()
    config.update(data)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


# ── API Endpoints ──────────────────────────────────────────────────────────────

@router.get("/api/config")
async def api_get_config():
    return read_config()

@router.post("/api/config")
async def api_post_config(request: Request):
    data = await request.json()
    write_config(data)
    logger.info("Configuration updated via UI.")
    return {"status": "success"}

@router.get("/api/logs")
async def api_get_logs():
    if not LOGS_FILE.exists():
        return []
    try:
        df = pd.read_csv(LOGS_FILE)
        # Assuming CSV has Date, Phone, Duration, Status, Summary, Transcript
        # Sort desc
        df = df.iloc[::-1].head(50)
        logs = []
        for i, row in df.iterrows():
            logs.append({
                "id": str(i),
                "created_at": row.get("Date", datetime.now().isoformat()),
                "phone_number": row.get("Phone", "Unknown"),
                "duration_seconds": row.get("Duration", 0),
                "summary": row.get("Summary", ""),
                "transcript": row.get("Transcript", "")
            })
        return logs
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return []

@router.get("/api/logs/{log_id}/transcript")
async def api_get_transcript(log_id: str):
    if not LOGS_FILE.exists():
        return PlainTextResponse("No logs found.")
    try:
        df = pd.read_csv(LOGS_FILE)
        row = df.iloc[int(log_id)]
        text = f"Call Log — {row.get('Date', '')}\n"
        text += f"Phone: {row.get('Phone', 'Unknown')}\n"
        text += f"Duration: {row.get('Duration', 0)}s\n"
        text += f"Summary: {row.get('Summary', '')}\n\n"
        text += "--- TRANSCRIPT ---\n"
        text += str(row.get("Transcript", "No transcript available."))
        return PlainTextResponse(content=text, media_type="text/plain",
                                 headers={"Content-Disposition": f"attachment; filename=transcript_{log_id}.txt"})
    except Exception as e:
        return PlainTextResponse(content=f"Error: {e}", status_code=500)

@router.get("/api/bookings")
async def api_get_bookings():
    # Treat Leads found in Excel as Bookings/Leads
    if not LEADS_FILE.exists():
        return []
    try:
        df = pd.read_excel(LEADS_FILE)
        bookings = []
        for i, row in df.iterrows():
            date_str = str(row.get("Date", ""))
            bookings.append({
                "id": str(i),
                "phone_number": str(row.get("Mobile Number", "")),
                "summary": str(row.get("Interested Course", "")) + " - " + str(row.get("City", "")),
                "created_at": date_str if date_str else datetime.now().isoformat(),
                "caller_name": str(row.get("Name", ""))
            })
        # sort desc
        bookings.sort(key=lambda x: x["created_at"], reverse=True)
        return bookings
    except Exception as e:
        logger.error(f"Error fetching bookings: {e}")
        return []

@router.get("/api/stats")
async def api_get_stats():
    total_calls, total_bookings, avg_duration, booking_rate = 0, 0, 0, 0
    try:
        if LOGS_FILE.exists():
            df = pd.read_csv(LOGS_FILE)
            total_calls = len(df)
            durations = pd.to_numeric(df.get("Duration", []), errors='coerce').dropna()
            if len(durations) > 0:
                avg_duration = int(durations.mean())
                
        if LEADS_FILE.exists():
            df_leads = pd.read_excel(LEADS_FILE)
            total_bookings = len(df_leads)
            
        if total_calls > 0:
            booking_rate = int((total_bookings / total_calls) * 100)
            
        return {"total_calls": total_calls, "total_bookings": total_bookings, "avg_duration": avg_duration, "booking_rate": booking_rate}
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return {"total_calls": 0, "total_bookings": 0, "avg_duration": 0, "booking_rate": 0}

@router.get("/api/contacts")
async def api_get_contacts():
    # Merge logs and leads
    contacts = {}
    try:
        if LEADS_FILE.exists():
            df_leads = pd.read_excel(LEADS_FILE)
            for i, row in df_leads.iterrows():
                phone = str(row.get("Mobile Number", "unknown"))
                if phone not in contacts:
                    contacts[phone] = {
                        "phone_number": phone,
                        "caller_name": str(row.get("Name", "")),
                        "total_calls": 1,
                        "last_seen": str(row.get("Date", "")),
                        "is_booked": True,
                    }
    except Exception as e:
        pass
        
    try:
        if LOGS_FILE.exists():
            df_logs = pd.read_csv(LOGS_FILE)
            for i, row in df_logs.iterrows():
                phone = str(row.get("Phone", "unknown"))
                date_val = str(row.get("Date", ""))
                if phone not in contacts:
                    contacts[phone] = {
                        "phone_number": phone,
                        "caller_name": "Unknown",
                        "total_calls": 1,
                        "last_seen": date_val,
                        "is_booked": False,
                    }
                else:
                    contacts[phone]["total_calls"] += 1
                    # Update last seen if newer
                    if date_val > contacts[phone]["last_seen"]:
                        contacts[phone]["last_seen"] = date_val
    except Exception as e:
        pass
        
    return sorted(contacts.values(), key=lambda x: x["last_seen"] or "", reverse=True)

# ── Main Dashboard HTML ────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def get_dashboard():
    config = read_config()

    def sel(key, val):
        return "selected" if config.get(key) == val else ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>TMU Admission Agent — Dashboard</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    :root {{
      --bg: #0f1117;
      --sidebar: #161b27;
      --card: #1c2333;
      --border: #2a3448;
      --accent: #2563eb;
      --accent-glow: rgba(37,99,235,0.18);
      --text: #e2e8f0;
      --muted: #8892a4;
      --green: #22c55e;
      --red: #ef4444;
      --yellow: #f59e0b;
      --sidebar-w: 240px;
    }}
    body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); display: flex; height: 100vh; overflow: hidden; }}

    /* ── Sidebar ── */
    #sidebar {{
      width: var(--sidebar-w); min-width: var(--sidebar-w);
      background: var(--sidebar); border-right: 1px solid var(--border);
      display: flex; flex-direction: column; padding: 24px 0;
      position: relative; z-index: 10;
    }}
    .sidebar-brand {{
      padding: 0 20px 24px;
      border-bottom: 1px solid var(--border);
      display: flex; align-items: center; gap: 10px;
    }}
    .sidebar-brand .logo {{
      width: 32px; height: 32px; background: var(--accent);
      border-radius: 8px; display: flex; align-items: center; justify-content: center;
      font-size: 16px;
    }}
    .sidebar-brand .brand-text {{ font-weight: 700; font-size: 14px; line-height: 1.2; }}
    .sidebar-brand .brand-sub {{ font-size: 10px; color: var(--muted); }}
    .sidebar-nav {{ padding: 16px 0; flex: 1; }}
    .nav-section {{ padding: 8px 16px 4px; font-size: 10px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }}
    .nav-item {{
      display: flex; align-items: center; gap: 10px;
      padding: 10px 20px; cursor: pointer; font-size: 13.5px; font-weight: 500;
      color: var(--muted); border-left: 3px solid transparent;
      transition: all 0.15s; user-select: none;
    }}
    .nav-item:hover {{ color: var(--text); background: rgba(255,255,255,0.04); }}
    .nav-item.active {{ color: var(--accent); border-left-color: var(--accent); background: var(--accent-glow); }}
    .nav-item .icon {{ font-size: 16px; width: 20px; text-align: center; }}
    .sidebar-footer {{
      padding: 16px 20px;
      border-top: 1px solid var(--border);
      font-size: 11px; color: var(--muted);
    }}
    .status-dot {{
      display: inline-block; width: 7px; height: 7px; border-radius: 50%;
      background: var(--green); margin-right: 6px; box-shadow: 0 0 6px var(--green);
    }}

    /* ── Main ── */
    #main {{ flex: 1; overflow-y: auto; background: var(--bg); }}
    .page {{ display: none; padding: 32px 36px; min-height: 100%; }}
    .page.active {{ display: block; }}
    .page-header {{ margin-bottom: 28px; }}
    .page-title {{ font-size: 22px; font-weight: 700; }}
    .page-sub {{ font-size: 13px; color: var(--muted); margin-top: 4px; }}

    /* ── Cards ── */
    .card {{
      background: var(--card); border: 1px solid var(--border);
      border-radius: 12px; padding: 20px;
    }}
    .stat-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 28px; }}
    .stat-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }}
    .stat-label {{ font-size: 11px; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }}
    .stat-value {{ font-size: 28px; font-weight: 700; margin-top: 8px; }}
    .stat-sub {{ font-size: 12px; color: var(--muted); margin-top: 4px; }}

    /* ── Table ── */
    .table-wrap {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    thead th {{ padding: 12px 16px; text-align: left; font-size: 11px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; background: rgba(255,255,255,0.03); border-bottom: 1px solid var(--border); }}
    tbody td {{ padding: 13px 16px; border-bottom: 1px solid rgba(255,255,255,0.04); vertical-align: middle; }}
    tbody tr:last-child td {{ border-bottom: none; }}
    tbody tr:hover {{ background: rgba(255,255,255,0.025); }}
    .badge {{ display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }}
    .badge-green {{ background: rgba(34,197,94,0.12); color: var(--green); }}
    .badge-gray {{ background: rgba(255,255,255,0.07); color: var(--muted); }}
    .badge-yellow {{ background: rgba(245,158,11,0.12); color: var(--yellow); }}

    /* ── Forms ── */
    label {{ display: block; font-size: 12px; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }}
    input[type=text], input[type=password], input[type=number], select, textarea {{
      width: 100%; background: var(--bg); border: 1px solid var(--border);
      border-radius: 8px; padding: 10px 12px; color: var(--text); font-family: inherit;
      font-size: 13.5px; outline: none; transition: border-color 0.15s;
    }}
    input:focus, select:focus, textarea:focus {{ border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-glow); }}
    textarea {{ font-family: 'JetBrains Mono', 'Fira Code', monospace; resize: vertical; }}
    .form-group {{ margin-bottom: 20px; }}
    .form-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .hint {{ font-size: 11.5px; color: var(--muted); margin-top: 5px; }}
    .section-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 24px; margin-bottom: 20px; }}
    .section-title {{ font-size: 14px; font-weight: 600; margin-bottom: 18px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }}

    /* ── Buttons ── */
    .btn {{ display: inline-flex; align-items: center; gap: 6px; padding: 9px 18px; border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer; border: none; transition: all 0.15s; }}
    .btn-primary {{ background: var(--accent); color: #fff; }}
    .btn-primary:hover {{ background: #1d4ed8; box-shadow: 0 0 16px var(--accent-glow); }}
    .btn-ghost {{ background: transparent; border: 1px solid var(--border); color: var(--muted); }}
    .btn-ghost:hover {{ border-color: var(--accent); color: var(--accent); }}
    .btn-sm {{ padding: 5px 12px; font-size: 12px; }}
    .save-bar {{
      position: sticky; bottom: 0; left: 0; right: 0;
      background: rgba(22,27,39,0.95); backdrop-filter: blur(12px);
      border-top: 1px solid var(--border);
      padding: 14px 36px; display: flex; align-items: center; justify-content: space-between; z-index: 20;
    }}
    .save-status {{ font-size: 13px; font-weight: 500; color: var(--green); opacity: 0; transition: opacity 0.3s; }}

    /* ── Premium extras ── */
    .stat-card {{ transition: transform 0.15s, box-shadow 0.15s; }}
    .stat-card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 30px rgba(37,99,235,0.12); }}
    .stat-accent {{ color: var(--accent); }}
    .pulse {{ animation: pulse 2s infinite; }}
    @keyframes pulse {{ 0%,100% {{ box-shadow: 0 0 6px var(--green); }} 50% {{ box-shadow: 0 0 14px var(--green); }} }}
  </style>
</head>
<body>

<!-- ── Sidebar ── -->
<nav id="sidebar">
  <div class="sidebar-brand">
    <div class="logo">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="12" cy="12" r="10" fill="rgba(255,255,255,0.12)"/>
        <path d="M8 12c0-2.21 1.79-4 4-4s4 1.79 4 4" stroke="white" stroke-width="1.8" stroke-linecap="round"/>
        <circle cx="12" cy="15" r="2" fill="white"/>
      </svg>
    </div>
    <div>
      <div class="brand-text">TMU Counselor</div>
      <div class="brand-sub">Admissions AI</div>
    </div>
  </div>
  <div class="sidebar-nav">
    <div class="nav-section">Overview</div>
    <div class="nav-item active" onclick="goTo('dashboard', this)"><span class="icon">📊</span> Dashboard</div>
    <div class="nav-section" style="margin-top:12px;">Configuration</div>
    <div class="nav-item" onclick="goTo('agent', this)"><span class="icon">🤖</span> Agent Settings</div>
    <div class="nav-item" onclick="goTo('models', this)"><span class="icon">🎙️</span> Models & Voice</div>
    <div class="nav-section" style="margin-top:12px;">Data</div>
    <div class="nav-item" onclick="goTo('logs', this); loadLogs();"><span class="icon">📞</span> Call Logs</div>
    <div class="nav-item" onclick="goTo('crm', this); loadCRM();"><span class="icon">👥</span> CRM Leads</div>
  </div>
  <div class="sidebar-footer">
    <span class="status-dot pulse"></span>System Online
  </div>
</nav>

<!-- ── Main Content ── -->
<div id="main">

  <!-- ── Dashboard ── -->
  <div id="page-dashboard" class="page active">
    <div class="page-header">
      <div class="page-title">TMU Admissions Dashboard</div>
      <div class="page-sub">Real-time overview of your AI Admission Counselor performance</div>
    </div>
    <div class="stat-grid" id="stat-grid">
      <div class="stat-card"><div class="stat-label">Total Calls</div><div class="stat-value" id="stat-calls">—</div><div class="stat-sub">All time interactions</div></div>
      <div class="stat-card"><div class="stat-label">Leads Captured</div><div class="stat-value" id="stat-bookings">—</div><div class="stat-sub">Processed profiles</div></div>
      <div class="stat-card"><div class="stat-label">Avg Duration</div><div class="stat-value" id="stat-duration">—</div><div class="stat-sub">Seconds per call</div></div>
      <div class="stat-card"><div class="stat-label">Capture Rate</div><div class="stat-value" id="stat-rate">—</div><div class="stat-sub">Calls converted to leads</div></div>
    </div>
    <div class="section-card">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px;">
        <div class="section-title" style="border:none;padding:0;margin:0;">Recent Interactions</div>
        <button class="btn btn-ghost btn-sm" onclick="loadDashboard()">↻ Refresh</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Date</th><th>Phone</th><th>Duration</th><th>Status</th><th>Actions</th></tr></thead>
          <tbody id="dash-table-body"><tr><td colspan="5" style="text-align:center;padding:24px;color:var(--muted);">Loading...</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- ── Agent Settings ── -->
  <div id="page-agent" class="page">
    <div class="page-header">
      <div class="page-title">Agent Settings</div>
      <div class="page-sub">Configure AI personality, opening line, and instructions</div>
    </div>
    <div class="section-card">
      <div class="section-title">Opening Greeting</div>
      <div class="form-group">
        <label>First Line (What the agent says when a call connects)</label>
        <input type="text" id="first_line" value="{config.get('first_line', '')}" placeholder="Namaste! Welcome to TMU. Main aapki kaise madad kar sakti hoon?">
      </div>
    </div>
    <div class="section-card">
      <div class="section-title">System Prompt & Context</div>
      <div class="form-group">
        <label>Agent Instructions</label>
        <textarea id="agent_instructions" rows="12" placeholder="Enter the AI's core instructions...">{config.get('agent_instructions', '')}</textarea>
      </div>
    </div>
    <div class="save-bar">
      <span class="save-status" id="save-status-agent">✅ Saved!</span>
      <button class="btn btn-primary" onclick="saveConfig('agent')">💾 Save Agent Settings</button>
    </div>
  </div>
  
  <!-- ── Models & Voice ── -->
  <div id="page-models" class="page">
    <div class="page-header">
      <div class="page-title">Models & Voice</div>
      <div class="page-sub">Select the AI brain and preferred TTS voice</div>
    </div>
    <div class="section-card">
      <div class="section-title">Language Model (LLM)</div>
      <div class="form-group" style="max-width:360px;">
        <label>Model</label>
        <select id="llm_model">
          <option value="gpt-4o-mini" {sel('llm_model','gpt-4o-mini')}>gpt-4o-mini</option>
          <option value="gpt-4o" {sel('llm_model','gpt-4o')}>gpt-4o</option>
          <option value="o1-mini" {sel('llm_model','o1-mini')}>o1-mini</option>
        </select>
      </div>
    </div>
    <div class="section-card">
      <div class="section-title">Voice Configuration</div>
      <div class="form-row" style="max-width:720px;">
        <div class="form-group">
          <label>Voice Persona</label>
          <select id="tts_voice">
            <option value="kavya" {sel('tts_voice','kavya')}>Kavya (Female, Default)</option>
            <option value="rohan" {sel('tts_voice','rohan')}>Rohan (Male)</option>
          </select>
        </div>
      </div>
    </div>
    <div class="save-bar">
      <span class="save-status" id="save-status-models">✅ Saved!</span>
      <button class="btn btn-primary" onclick="saveConfig('models')">💾 Save Voice Settings</button>
    </div>
  </div>

  <!-- ── Call Logs ── -->
  <div id="page-logs" class="page">
    <div class="page-header">
      <div style="display:flex;align-items:center;justify-content:space-between;">
        <div>
          <div class="page-title">Call Logs</div>
          <div class="page-sub">Full history of all incoming calls and transcripts</div>
        </div>
        <button class="btn btn-ghost" onclick="loadLogs()">↻ Refresh</button>
      </div>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Date & Time</th>
            <th>Phone</th>
            <th>Duration</th>
            <th>Summary</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody id="logs-table-body"><tr><td colspan="5" style="text-align:center;padding:32px;color:var(--muted);">Loading logs...</td></tr></tbody>
      </table>
    </div>
  </div>
  
  <!-- ── CRM Leads ── -->
  <div id="page-crm" class="page">
    <div class="page-header">
      <div class="page-title">👥 CRM Leads</div>
      <div class="page-sub">Consolidated list of interested applicants</div>
    </div>
    <div class="section-card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
        <div class="section-title" style="margin:0;">Captured Leads</div>
        <button class="btn btn-ghost btn-sm" onclick="loadCRM()">↻ Refresh</button>
      </div>
      <div style="overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
          <thead>
            <tr style="border-bottom:1px solid var(--border);">
              <th style="padding:10px 12px;text-align:left;color:var(--muted);font-weight:500;">Name</th>
              <th style="padding:10px 12px;text-align:left;color:var(--muted);font-weight:500;">Phone</th>
              <th style="padding:10px 12px;text-align:left;color:var(--muted);font-weight:500;">Total Calls</th>
              <th style="padding:10px 12px;text-align:left;color:var(--muted);font-weight:500;">Lead Captured</th>
            </tr>
          </thead>
          <tbody id="crm-tbody">
            <tr><td colspan="4" style="text-align:center;padding:32px;color:var(--muted);">Loading leads...</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>

</div><!-- /main -->

<script>
// ── Navigation ──────────────────────────────────────────────────────────────
function goTo(pageId, el) {{
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + pageId).classList.add('active');
  el.classList.add('active');
}}

// ── Stats & Dashboard ───────────────────────────────────────────────────────
async function loadDashboard() {{
  try {{
    const [stats, logs] = await Promise.all([
      fetch('/dashboard/api/stats').then(r => r.json()),
      fetch('/dashboard/api/logs').then(r => r.json())
    ]);
    document.getElementById('stat-calls').textContent = stats.total_calls ?? '—';
    document.getElementById('stat-bookings').textContent = stats.total_bookings ?? '—';
    document.getElementById('stat-duration').textContent = stats.avg_duration ? stats.avg_duration + 's' : '—';
    document.getElementById('stat-rate').textContent = stats.booking_rate ? stats.booking_rate + '%' : '—';

    const tbody = document.getElementById('dash-table-body');
    if (!logs || logs.length === 0) {{
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--muted);">No calls yet.</td></tr>';
      return;
    }}
    tbody.innerHTML = logs.slice(0, 10).map(log => `
      <tr>
        <td style="color:var(--muted)">${{new Date(log.created_at).toLocaleString()}}</td>
        <td style="font-weight:600">${{log.phone_number || 'Unknown'}}</td>
        <td>${{log.duration_seconds || 0}}s</td>
        <td><span class="badge badge-gray">Logged</span></td>
        <td>
          ${{log.id ? `<a style="color:var(--accent);font-size:12px;text-decoration:none;" href="/dashboard/api/logs/${{log.id}}/transcript" download="transcript_${{log.id}}.txt">⬇ Transcript</a>` : ''}}
        </td>
      </tr>`).join('');
  }} catch(e) {{
    document.getElementById('dash-table-body').innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:red;">Error loading data.</td></tr>';
  }}
}}

// ── Call Logs ───────────────────────────────────────────────────────────────
async function loadLogs() {{
  const tbody = document.getElementById('logs-table-body');
  try {{
    const logs = await fetch('/dashboard/api/logs').then(r => r.json());
    if (!logs || logs.length === 0) {{
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:var(--muted);">No call logs found.</td></tr>';
      return;
    }}
    tbody.innerHTML = logs.map(log => `
      <tr>
        <td style="color:var(--muted);white-space:nowrap">${{new Date(log.created_at).toLocaleString()}}</td>
        <td style="font-weight:600">${{log.phone_number || 'Unknown'}}</td>
        <td>${{log.duration_seconds || 0}}s</td>
        <td style="color:var(--muted);font-size:12px;max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${{log.summary || ''}}">${{log.summary || '—'}}</td>
        <td>
          ${{log.id ? `<a class="btn btn-ghost btn-sm" style="text-decoration:none;" href="/dashboard/api/logs/${{log.id}}/transcript" download="transcript_${{log.id}}.txt">⬇ Download</a>` : '—'}}
        </td>
      </tr>`).join('');
  }} catch(e) {{
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:24px;color:#ef4444;">Error loading logs.</td></tr>';
  }}
}}

// ── CRM ─────────────────────────────────────────────────────────────────────
async function loadCRM() {{
  const tbody = document.getElementById('crm-tbody');
  try {{
    const contacts = await fetch('/dashboard/api/contacts').then(r => r.json());
    if (!contacts.length) {{
      tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:40px;color:var(--muted);">No leads captured yet.</td></tr>';
      return;
    }}
    tbody.innerHTML = contacts.map(c => `
      <tr style="border-bottom:1px solid var(--border); transition:background 0.12s;">
        <td style="padding:14px 16px;font-weight:600;">${{c.caller_name || '<span style="color:var(--muted);font-weight:400;">Unknown</span>'}}</td>
        <td style="padding:14px 16px;font-family:monospace;font-size:13px;">${{c.phone_number || '—'}}</td>
        <td style="padding:14px 16px;">${{c.total_calls}} interactions</td>
        <td style="padding:14px 16px;">${{c.is_booked ? '<span class="badge badge-green">Lead Captured</span>' : '<span class="badge badge-gray">Pending</span>'}}</td>
      </tr>`).join('');
  }} catch(e) {{
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;padding:24px;color:#ef4444;">Error loading CRM contacts.</td></tr>';
  }}
}}

// ── Save Config ─────────────────────────────────────────────────────────────
async function saveConfig(section) {{
  const get = id => {{ const el = document.getElementById(id); return el ? el.value : null; }};
  const payload = {{}};
  if (section === 'agent') {{
    Object.assign(payload, {{ first_line: get('first_line'), agent_instructions: get('agent_instructions') }});
  }} else if (section === 'models') {{
    Object.assign(payload, {{ llm_model: get('llm_model'), tts_voice: get('tts_voice') }});
  }}
  const res = await fetch('/dashboard/api/config', {{
    method: 'POST', headers: {{'Content-Type': 'application/json'}}, body: JSON.stringify(payload)
  }});
  const statusEl = document.getElementById('save-status-' + section);
  if (res.ok) {{
    statusEl.style.opacity = '1';
    setTimeout(() => {{ statusEl.style.opacity = '0'; }}, 2500);
  }}
}}

// ── Boot ────────────────────────────────────────────────────────────────────
loadDashboard();
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
