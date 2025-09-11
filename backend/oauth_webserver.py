# oauth_webserver.py
"""
Lightweight local OAuth server for Google Calendar access.

- Mounts the OAuth blueprint from scheduler_tools.py:
    • GET /oauth2/login        -> starts OAuth
    • GET /oauth2callback      -> handles callback, saves ./tokens/<email>.json

- Adds a few convenience endpoints for dev/testing:
    • GET /                    -> simple HTML with links + token listing
    • GET /oauth2/status       -> JSON auth status (use ?email=<addr> to check a specific user)
    • POST /oauth2/logout      -> delete saved token for ?email=<addr>

Env vars (optional):
    PORT=8080
    HOST=localhost
    OAUTH_REDIRECT_URI=http://localhost:8080/oauth2callback
    GOOGLE_CREDENTIALS_PATH=./credentials.json
"""

from __future__ import annotations

import glob
import json
import os
from typing import List

from flask import Flask, jsonify, redirect, request
from datetime import datetime, timedelta, timezone
from scheduler_tools import cal_list_events, cal_freebusy, scheduler_tools_api_bp  
from scheduler_agent import scheduler_api_bp

# Import the OAuth blueprint and helpers from your tools module
from scheduler_tools import (
    scheduler_oauth_bp,
    cal_auth_status,  
    TOKENS_DIR,
    CREDENTIALS_PATH,
    REDIRECT_URI,
)

# -------------------- App setup --------------------
app = Flask(__name__)
app.register_blueprint(scheduler_oauth_bp)

if scheduler_tools_api_bp:
    app.register_blueprint(scheduler_tools_api_bp)   # /api/scheduler-tools/*
if scheduler_api_bp:
    app.register_blueprint(scheduler_api_bp)         # /api/scheduler/*

# -------------------- Helpers --------------------
def _token_emails() -> List[str]:
    """List emails for which we have saved tokens."""
    if not os.path.isdir(TOKENS_DIR):
        return []
    paths = glob.glob(os.path.join(TOKENS_DIR, "*.json"))
    return [os.path.splitext(os.path.basename(p))[0] for p in paths]

def _env(val: str, default: str) -> str:
    return os.environ.get(val, default)

def _html_escape(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

# -------------------- Routes --------------------
@app.get("/")
def index():
    emails = _token_emails()
    creds_exists = os.path.exists(CREDENTIALS_PATH)
    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Local OAuth Server</title>
  <style>
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 2rem; line-height: 1.5; }}
    code, pre {{ background: #f6f8fa; padding: 0.2rem 0.4rem; border-radius: 4px; }}
    .box {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-top: 1rem; }}
    a.button {{ display: inline-block; padding: 0.5rem 0.9rem; border: 1px solid #2563eb; color: #2563eb; text-decoration: none; border-radius: 6px; }}
    a.button:hover {{ background:#eff6ff; }}
  </style>
</head>
<body>
  <h1>Google Calendar OAuth (Local)</h1>

  <div class="box">
    <h3>Status</h3>
    <p><strong>Credentials file:</strong> <code>{_html_escape(CREDENTIALS_PATH)}</code> — {"✅ found" if creds_exists else "❌ missing"}</p>
    <p><strong>Redirect URI:</strong> <code>{_html_escape(REDIRECT_URI)}</code></p>
    <p><strong>Tokens dir:</strong> <code>{_html_escape(TOKENS_DIR)}</code></p>
    <p><strong>Authorized emails ({len(emails)}):</strong> {", ".join(map(_html_escape, emails)) or "(none yet)"}</p>
  </div>

  <div class="box">
    <h3>Actions</h3>
    <p><a class="button" href="/oauth2/login">Start OAuth (sign in)</a></p>
    <p>Check status for an email (JSON): <code>GET /oauth2/status?email=you@example.com</code></p>
    <p>Logout an email (delete token): <code>POST /oauth2/logout?email=you@example.com</code></p>
  </div>

  <div class="box">
    <h3>Notes</h3>
    <ul>
      <li>Ensure your Google Cloud Console OAuth client has the redirect URI above authorized.</li>
      <li>Each developer runs this locally; tokens are saved under <code>{_html_escape(TOKENS_DIR)}</code> as <code>&lt;email&gt;.json</code>.</li>
    </ul>
  </div>
</body>
</html>
"""
    return html, 200, {"Content-Type": "text/html; charset=utf-8"}

@app.get("/oauth2/status")
def oauth_status():
    """
    Check whether an email is authorized.
    - If ?email is provided, return its status.
    - If not, return the list of authorized emails.
    """
    email = request.args.get("email", "").strip()
    if email:
        try:
            # cal_auth_status returns {"authorized": bool, ...}
            status = cal_auth_status(email=email)  # type: ignore
            return jsonify({"email": email, **status})
        except Exception as e:
            return jsonify({"email": email, "authorized": False, "error": str(e)}), 400
    else:
        return jsonify({"authorized_emails": _token_emails()})

@app.post("/oauth2/logout")
def oauth_logout():
    """
    Delete the saved token for an email.
    Usage: POST /oauth2/logout?email=you@example.com
    """
    email = request.args.get("email", "").strip()
    if not email:
        return jsonify({"error": "email query parameter required"}), 400
    path = os.path.join(TOKENS_DIR, f"{email}.json")
    if os.path.exists(path):
        try:
            os.remove(path)
            return jsonify({"email": email, "deleted": True})
        except Exception as e:
            return jsonify({"email": email, "deleted": False, "error": str(e)}), 500
    return jsonify({"email": email, "deleted": False, "error": "no token file found"}), 404


# ---------- Calendar Data API ----------
def _iso_now():
    return datetime.now(timezone.utc).astimezone().isoformat()

@app.get("/api/calendar/events")
def api_calendar_events():
    """
    Returns events for an authorized email within [start,end].
    Query params:
      - email: optional; if omitted and exactly one token exists, it will be used
      - start: ISO datetime (default: now)
      - end:   ISO datetime (default: now + 7 days)
    """
    email = request.args.get("email", "").strip()
    if not email:
        emails = _token_emails()
        if len(emails) == 1:
            email = emails[0]
        else:
            return jsonify({"error": "email query parameter required", "authorized_emails": emails}), 400

    start = request.args.get("start") or _iso_now()
    end = request.args.get("end")
    if not end:
        end_ts = datetime.now(timezone.utc).astimezone() + timedelta(days=90)
        end = end_ts.isoformat()

    try:
        events = cal_list_events(email=email, start_iso=start, end_iso=end)
        return jsonify({"email": email, "start": start, "end": end, "events": events})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.get("/api/calendar/freebusy")
def api_calendar_freebusy():
    """
    Free/busy helper (optional).
    Query: email (optional), start (default now), end (default +7d)
    """
    email = request.args.get("email", "").strip()
    if not email:
        emails = _token_emails()
        if len(emails) == 1:
            email = emails[0]
        else:
            return jsonify({"error": "email query parameter required", "authorized_emails": emails}), 400

    start = request.args.get("start") or _iso_now()
    end   = request.args.get("end") or (datetime.now(timezone.utc).astimezone() + timedelta(days=7)).isoformat()

    try:
        data = cal_freebusy(email=email, start_iso=start, end_iso=end)
        return jsonify({"email": email, "start": start, "end": end, **data})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# -------------------- Main --------------------
if __name__ == "__main__":
    host = _env("HOST", "localhost")
    port = int(_env("PORT", "8000"))
    debug = _env("DEBUG", "false").lower() in ("1", "true", "yes", "y")

    # Friendly console hints
    print("== Local OAuth Server ==")
    print(f"Credentials: {CREDENTIALS_PATH} ({'OK' if os.path.exists(CREDENTIALS_PATH) else 'MISSING'})")
    print(f"Redirect URI: {REDIRECT_URI}")
    print(f"Tokens dir:   {TOKENS_DIR}")
    print(f"Open:         http://{host}:{port}/")
    app.run(host="localhost", port=8080, debug=True, ssl_context="adhoc")

