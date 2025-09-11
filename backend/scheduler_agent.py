# scheduler_agent.py
"""
Scheduler Agent:
- Tools from scheduler_tools are free/busy-aware and interests-aware.
- Provides a CLI interaction: prints proposals, seeks consent, writes calendar.

Env:
  AWS_REGION
  BEDROCK_MODEL_SCHEDULER  (only used if you call through LLM; CLI uses tools directly)
"""
from __future__ import annotations
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from strands import Agent
from strands.models import BedrockModel
import re
import json
from typing import Dict, Any, List, Optional

from scheduler_tools import (
    cal_auth_status, policy_constants, cal_freebusy, cal_list_events, cal_insert_event, get_active_email
)
from secretary_tools import sec_get_bs

load_dotenv()

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID_SCHEDULER = (
    os.getenv("BEDROCK_MODEL_SCHEDULER")
    or os.getenv("BEDROCK_MODEL_ID")
    or "us.anthropic.claude-sonnet-4-20250514-v1:0"  
)

assert MODEL_ID_SCHEDULER, "BEDROCK model id not set"

def _model():
    return BedrockModel(
        model_id=MODEL_ID_SCHEDULER,
        region=AWS_REGION,
        streaming=True, 
        generation_config={"max_tokens": 800, "temperature": 0.3, "top_p": 0.9}
    )

# -------------------- PROMPT ENGINEERING --------------------
TASK_CONTEXT = """
You are the Scheduler Agent. Your purpose is to reduce burnout through calendar hygiene:
- Propose additive adjustments (no deletions) such as brief breaks, restorative activities, and small goal blocks.
- Obtain consent before applying changes via calendar inserts.
"""

TONE_CONTEXT = """
Be concise, concrete, and respectful. Give small, high-impact suggestions first (1–3 items).
"""

TASK_DESCRIPTION = """
Rules & Capabilities:
- Use policy_constants() to read thresholds:
  * MAX_CONTIGUOUS_WORK_MIN (default 240)
  * RECOMMENDED_BREAK_MIN (default 15)
  * USER_TZ (default Asia/Singapore)
- Use get_bs(user_name?) to incorporate Burnout Score (BS).
- Use get_interests(user_name?) to fetch the user’s preferences.
  * Only suggest activities where the interest flag is 1 (e.g. likes_exercise=1).
- If BS ≥ 0.60, prioritize 20–30 min restorative blocks aligned with interests.
- Use cal_auth_status(email?) to check if authorized; if not, return the login_url and stop.
- To analyze schedule: use cal_list_events(...) and cal_freebusy(...) for next 7 days.
- To apply changes after consent: call cal_insert_event(email, summary, start_iso, end_iso, description).
- Never delete or modify existing events. Add only.
"""


EXAMPLES = """
<example>
User: "Plan my week; email=alex@example.com; user=Dae"
Assistant:
1) Call get_bs("Dae") → 0.72; get_interests("Dae") → {"likes_exercise":1,"likes_meditation":1}
2) Call cal_auth_status("alex@example.com") → {"authorized": true}
3) Call policy_constants()
4) Call cal_list_events(...) and cal_freebusy(...) for next 7 days
5) If a 5h block exists, propose a mid-block 15-min break.
6) Propose a 30-min "Wellbeing: 20-min light exercise" in a free afternoon slot.
7) Return:
<response>
<proposal>
- Insert a 15-min recovery break to split a long meeting block on Fri.
- Add one 30-min wellbeing slot on Sat 12:30 for light exercise.
- Add one 30-min "Personal Goals Focus" block mid-week 20:00.
</proposal>
<payload>
{"email":"alex@example.com","proposals":[
 {"type":"break","summary":"Recovery break (15 min)","start":"2025-09-05T15:45:00+08:00","end":"2025-09-05T16:00:00+08:00","reason":"Split a 5h block to reduce strain"},
 {"type":"wellbeing","summary":"Wellbeing: 20-min light exercise","start":"2025-09-06T12:30:00+08:00","end":"2025-09-06T13:00:00+08:00","reason":"BS elevated; restorative slot suggested"},
 {"type":"goals","summary":"Personal Goals Focus","start":"2025-09-10T20:00:00+08:00","end":"2025-09-10T20:30:00+08:00","reason":"Maintain momentum without overload"}
]}
</payload>
<consent>Approve these inserts?</consent>
</response>
</example>

<example>
User: "Plan next few days; email=mina@example.com; user=Mina"
Assistant:
- If cal_auth_status says {"authorized": false, "login_url": "..."},
  return the login_url and stop with a short friendly message.
</example>
"""

IMMEDIATE_TASK = """
- Parse user input to extract `email` and optional `user` (user_name).
- If unauthorized: show login_url and brief note.
- Else:
  * Analyze next 7 days.
  * Use cal_freebusy and cal_list_events to find available time.
  * Only propose activities in empty/free slots (never overlap existing events).
  * Build 1–3 focused proposals based on Burnout Score (BS) and interests.
  * Return a readable <proposal>, a machine-usable <payload> JSON, and a <consent> question.
"""


PRECOGNITION = """
Plan your tool calls. Keep them minimal and relevant. Never insert events without consent.
"""

OUTPUT_FORMATTING = """
Wrap your final answer in <response> with children <proposal>, <payload>, and <consent>.
"""

SCHEDULER_SYSTEM_PROMPT = f"""
{TASK_CONTEXT}
{TONE_CONTEXT}
{TASK_DESCRIPTION}
{EXAMPLES}
{IMMEDIATE_TASK}
{PRECOGNITION}
{OUTPUT_FORMATTING}
"""

# ---- Lazy singleton ----
_SCHEDULER = None
def get_agent() -> Agent:
    global _SCHEDULER
    if _SCHEDULER is None:
        _SCHEDULER = Agent(
            name="Scheduler Agent",
            system_prompt=SCHEDULER_SYSTEM_PROMPT,
            tools=[
                cal_insert_event, 
                cal_auth_status, policy_constants, cal_freebusy, cal_list_events
            ],
            model=_model(),
        )
    return _SCHEDULER

# *****************************************************************************
# *****************************  API ENDPOINTS  ********************************
# *****************************************************************************
try:
    from flask import Blueprint, request, jsonify
    scheduler_api_bp = Blueprint("scheduler_api", __name__, url_prefix="/api/scheduler")

    @scheduler_api_bp.route("/plan", methods=["POST"])
    def api_plan():
        data = request.get_json(force=True) or {}
        user = data.get("user") or "default"
        days = int(data.get("days", 7))
        email = data.get("email") or get_active_email() or ""
        if not email:
            return jsonify({"authorized": False, "login_url": cal_auth_status("").get("login_url")}), 401
        prompt = f"Plan my next {days} days and suggest 1-2 activities per day; email={email}; user={user}"
        agent_result = get_agent()(prompt)
        text = getattr(agent_result, "output_text", str(agent_result))
        # pull out payload for FE convenience
        m = re.search(r"<payload>\s*(\{.*?\})\s*</payload>", text, re.DOTALL)
        payload = json.loads(m.group(1)) if m else {"email": email, "proposals": []}
        return jsonify({"text": text, "payload": payload, "email": email})

    @scheduler_api_bp.route("/apply", methods=["POST"])
    def api_apply():
        data = request.get_json(force=True) or {}
        email = data.get("email") or get_active_email()
        proposals: List[Dict[str, Any]] = data.get("proposals") or []
        if not email:
            return jsonify({"error":"No authorized calendar email"}), 400
        added = []
        for p in proposals:
            cal_insert_event(email=email,
                             summary=p["summary"],
                             start_iso=p["start"],
                             end_iso=p["end"],
                             description=p.get("reason",""))
            added.append(p["summary"])
        return jsonify({"added": added, "count": len(added)})

    @scheduler_api_bp.route("/health", methods=["GET"])
    def api_health():
        return jsonify({"ok": True})
except Exception:
    scheduler_api_bp = None


  