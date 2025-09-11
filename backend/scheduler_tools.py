# scheduler_tools.py
"""
Google Calendar tools + OAuth blueprint for the Scheduler Agent.
- Per-user OAuth tokens under ./tokens/<email>.json (offline refresh).
- Exposes Flask blueprint for /oauth2/login and /oauth2callback (mount in oauth_webserver.py).
- Tools available to the Scheduler Agent:
    cal_auth_status(email?)
    cal_freebusy(email, start_iso, end_iso)
    cal_list_events(email, start_iso, end_iso)
    cal_insert_event(email, summary, start_iso, end_iso, description)
    policy_constants()
    get_bs(user_name?)
    get_interests(user_name?)
"""
from __future__ import annotations
import os
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from flask import Blueprint, Flask, request, redirect, jsonify

from strands import tool

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# ----------------- Config -----------------
USER_TZ = os.environ.get("USER_TIMEZONE", "Asia/Singapore")
CREDENTIALS_PATH = os.environ.get("GOOGLE_CREDENTIALS_PATH", "./credentials.json")
TOKENS_DIR = os.environ.get("TOKENS_DIR", "./tokens")
REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URI", "https://localhost:8080/oauth2callback")
SCOPES = ["https://www.googleapis.com/auth/calendar"]

MAX_CONTIGUOUS_WORK_MIN = int(os.environ.get("MAX_CONTIGUOUS_WORK_MIN", "240"))
RECOMMENDED_BREAK_MIN = int(os.environ.get("RECOMMENDED_BREAK_MIN", "15"))

STATE_PATH = "./agent_state.json"  # legacy fallback; we prefer user_session when available

os.makedirs(TOKENS_DIR, exist_ok=True)

# ----------------- Helpers -----------------
def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()

def _normalize_iso_z(s: str | None) -> str | None:
    return s.replace("Z", "+00:00") if s else s

def _event_times(e: dict) -> tuple[str | None, str | None]:
    """
    Return (start_iso, end_iso) handling timed and all-day events.
    For all-day events (date), Google uses end-exclusive date.
    """
    s = e.get("start", {})
    t = e.get("end", {})
    s_dt = s.get("dateTime")
    t_dt = t.get("dateTime")
    if s_dt and t_dt:
        return _normalize_iso_z(s_dt), _normalize_iso_z(t_dt)
    s_d = s.get("date")
    t_d = t.get("date")
    if s_d and t_d:
        # Represent all-day as midnight UTC for clarity
        return f"{s_d}T00:00:00+00:00", f"{t_d}T00:00:00+00:00"
    return _normalize_iso_z(s_dt or s_d), _normalize_iso_z(t_dt or t_d)

def _service_from_creds(creds: Credentials):
    return build("calendar", "v3", credentials=creds, cache_discovery=False)

def _load_creds_for_email(email: str) -> Optional[Credentials]:
    path = os.path.join(TOKENS_DIR, f"{email}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        info = json.load(f)
    creds = Credentials.from_authorized_user_info(info, SCOPES)
    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(path, "w") as f:
                f.write(creds.to_json())
        else:
            return None
    return creds

def _save_creds_for_email(email: str, creds: Credentials) -> None:
    path = os.path.join(TOKENS_DIR, f"{email}.json")
    with open(path, "w") as f:
        f.write(creds.to_json())

def _get_primary_email(service) -> str:
    resp = service.calendarList().list().execute()
    for item in resp.get("items", []):
        if item.get("primary"):
            return item.get("id") or item.get("summary", "primary")
    items = resp.get("items", [])
    return (items[0].get("id") if items else "primary")

def _read_state_legacy() -> Dict[str, Any]:
    if not os.path.exists(STATE_PATH):
        return {}
    with open(STATE_PATH, "r") as f:
        return json.load(f)

def _try_user_session():
    try:
        import user_session
        return user_session
    except Exception:
        return None
    
def handle_user_consent(consent_response: str, proposals: list) -> str:
    """
    Handle user's yes/no consent for proposed calendar inserts.
    Args:
        consent_response: 'yes' or 'no' (case-insensitive)
        proposals: list of proposals returned by scheduler_agent
    Returns:
        str: reply message for the user
    """
    consent_response = consent_response.strip().lower()
    if consent_response in ["yes", "y"]:
        # Here you could call cal_insert_event for each proposal if you want
        return f"Great! I've scheduled the following: {', '.join(p['summary'] for p in proposals)}"
    elif consent_response in ["no", "n"]:
        return "No problem! Nothing has been added to your calendar. Let me know if you want to try something else."
    else:
        return "I didn't understand that. Please reply 'yes' ply 'yes' or 'no'."

# ----------------- Interactive User Consent -----------------
import json
import re

def ask_user_consent_and_schedule(agent_result, email):
    """
    Ask for user consent for each proposed event individually and insert if approved.
    """
    if hasattr(agent_result, "output_text"):
        agent_response = agent_result.output_text
    else:
        agent_response = str(agent_result)

    # Extract payload JSON
    payload_match = re.search(r"<payload>\s*(\{.*?\})\s*</payload>", agent_response, re.DOTALL)
    if payload_match:
        payload_json = payload_match.group(1)
        payload = json.loads(payload_json)
        proposals = payload.get("proposals", [])
    else:
        proposals = []

    if not proposals:
        print("No proposals found in the agent response.")
        return

    scheduled = []
    for p in proposals:
        print(f"\nProposed event:\n- {p['summary']} ({p['type']}) [{p['start']} → {p['end']}]")
        user_reply = input("Do you approve this event? (yes/no): ").strip().lower()
        if user_reply in ["yes", "y"]:
            try:
                cal_insert_event(
                    email=email,
                    summary=p["summary"],
                    start_iso=p["start"],
                    end_iso=p["end"],
                    description=p.get("reason", "")
                )
                scheduled.append(p["summary"])
                print(f"✅ Scheduled: {p['summary']}")
            except Exception as e:
                print(f"Failed to insert event '{p['summary']}': {e}")
        else:
            print(f"❌ Skipped: {p['summary']}")

    if scheduled:
        print(f"\nFinished scheduling. Events added: {', '.join(scheduled)}")
    else:
        print("\nNo events were added to your calendar.")




# ----------------- OAuth Blueprint -----------------
scheduler_oauth_bp = Blueprint("scheduler_oauth", __name__)

@scheduler_oauth_bp.route("/oauth2/login")
def oauth_login():
    flow = Flow.from_client_secrets_file(CREDENTIALS_PATH, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    return redirect(auth_url, code=302)

@scheduler_oauth_bp.route("/oauth2callback")
def oauth_callback():
    flow = Flow.from_client_secrets_file(CREDENTIALS_PATH, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    flow.fetch_token(authorization_response=request.url)
    creds: Credentials = flow.credentials
    service = _service_from_creds(creds)
    email = _get_primary_email(service)
    _save_creds_for_email(email, creds)
    return jsonify({"status": "ok", "email": email, "message": "Authorized. You can close this tab."})

# Optional standalone for local dev
app = Flask(__name__)
app.register_blueprint(scheduler_oauth_bp)

# ----------------- Tools -----------------
@tool
def cal_auth_status(email: str = "") -> dict:
    """
    Check whether we have valid credentials for 'email'.
    If not authorized, returns a login_url to start OAuth.
    """
    if email:
        creds = _load_creds_for_email(email)
        if creds:
            return {"authorized": True}
    flow = Flow.from_client_secrets_file(CREDENTIALS_PATH, scopes=SCOPES, redirect_uri=REDIRECT_URI)
    auth_url, _state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    return {"authorized": False, "login_url": auth_url}

def _service_or_raise(email: str):
    creds = _load_creds_for_email(email)
    if not creds:
        raise RuntimeError(f"No valid credentials for {email}. Ask user to open /oauth2/login.")
    return _service_from_creds(creds)

@tool
def cal_freebusy(email: str, start_iso: str, end_iso: str) -> dict:
    """
    Return busy intervals for [start_iso, end_iso] in user's primary calendar.
    Output: {"busy":[{"start": iso, "end": iso}, ...]}
    """
    svc = _service_or_raise(email)
    body = {"timeMin": start_iso, "timeMax": end_iso, "timeZone": USER_TZ, "items": [{"id": "primary"}]}
    resp = svc.freebusy().query(body=body).execute()
    busy = resp.get("calendars", {}).get("primary", {}).get("busy", [])
    return {"busy": busy}

@tool
def cal_list_events(email: str, start_iso: str, end_iso: str) -> list:
    """
    Return Google-shaped events (id, summary, start{dateTime|date}, end{...}, location, attendees, description)
    across ALL calendars visible to the user. Handles recurring, all-day, pagination.
    """
    svc = _service_or_raise(email)

    def _fetch_for_calendar(cid: str) -> List[dict]:
        items, token = [], None
        while True:
            resp = svc.events().list(
                calendarId=cid,
                timeMin=_normalize_iso_z(start_iso),
                timeMax=_normalize_iso_z(end_iso),
                singleEvents=True,          # expand recurring
                showDeleted=False,
                orderBy="startTime",
                pageToken=token
            ).execute()
            for e in resp.get("items", []):
                # keep Google structure but prune
                items.append({
                    "id": e.get("id"),
                    "summary": e.get("summary", "(no title)"),
                    "start": e.get("start", {}),  # may contain dateTime OR date
                    "end":   e.get("end",   {}),
                    "location": e.get("location"),
                    "attendees": e.get("attendees", []),
                    "description": e.get("description"),
                    "htmlLink": e.get("htmlLink"),
                    "calendarId": cid,
                })
            token = resp.get("nextPageToken")
            if not token: break
        return items

    # iterate all calendars (primary + secondary)
    out = []
    for cal in svc.calendarList().list().execute().get("items", []):
        out.extend(_fetch_for_calendar(cal["id"]))
    return out

@tool
def cal_insert_event(email: str, summary: str, start_iso: str, end_iso: str, description: str = "") -> dict:
    """
    Insert an event into the user's primary calendar.
    """
    svc = _service_or_raise(email)
    body = {
        "summary": summary,
        "start": {"dateTime": start_iso, "timeZone": USER_TZ},
        "end":   {"dateTime": end_iso,   "timeZone": USER_TZ},
        "description": description,
    }
    return svc.events().insert(calendarId="primary", body=body).execute()

@tool
def policy_constants() -> dict:
    """
    Provide policy thresholds for the Agent's reasoning.
    """
    return {
        "MAX_CONTIGUOUS_WORK_MIN": MAX_CONTIGUOUS_WORK_MIN,
        "RECOMMENDED_BREAK_MIN": RECOMMENDED_BREAK_MIN,
        "USER_TZ": USER_TZ,
        "now": _now_iso(),
    }

@tool
def get_bs(user_name: str | None = None) -> float:
    """
    Fetch current BS from user_session (fallback to 0.35 or legacy state).
    """
    us = _try_user_session()
    if us:
        try:
            return float(us.get_bs(user_name))
        except Exception:
            pass
    legacy = _read_state_legacy()
    return float(legacy.get("bs", 0.35))

@tool
def get_interests(user_name: str | None = None) -> dict:
    """
    Fetch interests from user_session (fallback to {} or legacy state).
    """
    us = _try_user_session()
    if us:
        try:
            return us.get_interests(user_name) or {}
        except Exception:
            pass
    legacy = _read_state_legacy()
    return legacy.get("interests", {})


# *****************************************************************************
# *********************  NEW HELPERS + API ENDPOINTS  *************************
# *****************************************************************************

def get_active_email() -> Optional[str]:
    """
    Return the first token email we have on disk, or None if none.
    """
    if not os.path.isdir(TOKENS_DIR): return None
    for f in os.listdir(TOKENS_DIR):
        if f.endswith(".json"): return f[:-5]
    return None

try:
    scheduler_tools_api_bp = Blueprint("scheduler_tools_api", __name__, url_prefix="/api/scheduler-tools")

    @scheduler_tools_api_bp.route("/auth/status", methods=["GET"])
    def api_auth_status():
        email = get_active_email()
        info = cal_auth_status(email or "")
        return jsonify({"email": info.get("email", email), **info})

    @scheduler_tools_api_bp.route("/whoami", methods=["GET"])
    def api_whoami():
        return jsonify({"email": get_active_email()})

    @scheduler_tools_api_bp.route("/events", methods=["POST"])
    def api_list_events():
        data = request.get_json(force=True) or {}
        email = data.get("email") or get_active_email()
        calendar_id = data.get("calendarId") 
        return jsonify(cal_list_events(email, data["start_iso"], data["end_iso"]))

    @scheduler_tools_api_bp.route("/freebusy", methods=["POST"])
    def api_freebusy():
        data = request.get_json(force=True) or {}
        email = data.get("email") or get_active_email()
        return jsonify(cal_freebusy(email, data["start_iso"], data["end_iso"]))

    @scheduler_tools_api_bp.route("/insert", methods=["POST"])
    def api_insert():
        data = request.get_json(force=True) or {}
        email = data.get("email") or get_active_email()
        resp = cal_insert_event(email, data["summary"], data["start_iso"], data["end_iso"], data.get("description",""))
        return jsonify(resp)

    @scheduler_tools_api_bp.route("/list-calendars", methods=["GET"])
    def api_list_calendars():
        email = request.args.get("email") or get_active_email()
        if not email:
            return jsonify({"error": "No authorized email"}), 400
        svc = _service_or_raise(email)
        data = svc.calendarList().list().execute().get("items", [])
        slim = [{"id": c["id"], "summary": c.get("summary"), "primary": c.get("primary", False), "accessRole": c.get("accessRole")} for c in data]
        return jsonify({"email": email, "calendars": slim})

    # Register for standalone dev server too
    app.register_blueprint(scheduler_tools_api_bp)
except Exception:
    scheduler_tools_api_bp = None