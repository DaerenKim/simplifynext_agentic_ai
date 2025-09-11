# manager_agent.py
"""
Rule-based Manager (CLI)
- Orchestrates secretary -> scheduler -> advisor without using an LLM for control.
- Reads/writes shared state in secretary_tools; uses scheduler_tools for calendar.
Run:
  python manager_agent.py
"""
from __future__ import annotations
import argparse
from typing import Callable, Dict, Any, List, Optional
from os import listdir
from os.path import isfile, join
from secretary_tools import (
    QUESTION_BANK_BURNOUT, sec_next_question, sec_record_answer, sec_set_interests,
    ensure_state, 
    sec_is_interests_initialized,
    sec_should_ask_open_ended_interest,
    sec_open_ended_interest_prompt,
    sec_record_open_ended_interest
)   
from scheduler_tools import ask_user_consent_and_schedule, cal_insert_event, get_active_email, cal_auth_status
from scheduler_agent import get_agent as get_scheduler_agent  
import uuid
from advisor_agent import advise_and_render
from therapist_agent import therapy_turn
import re, json, time
from typing import Dict, Any, List, Optional, Tuple

# -------------------- Proposal session store --------------------
_PROPOSAL_SESSIONS: Dict[str, Dict[str, Any]] = {}

def _extract_payload(text: str, fallback_email: str) -> dict:
    m = re.search(r"<payload>\s*(\{.*?\})\s*</payload>", text, re.DOTALL)
    if not m:
        return {"email": fallback_email, "proposals": []}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {"email": fallback_email, "proposals": []}

def _out(s: str) -> None:
    print(s)

def _in(p: str) -> str:
    return input(p)

class Manager:
    def __init__(self, input_fn=_in, output_fn=_out) -> None:
        self.input = input_fn
        self.output = output_fn

    def _ask_binary(self, prompt: str) -> int:
        while True:
            s = self.input(f"{prompt} ").strip().lower()
            if s in ("1","y","yes","true"): return 1
            if s in ("0","n","no","false"): return 0
            self.output("Please type 1/0 or y/n.")
    def _ask_likert(self, prompt: str, k: int) -> int:
        while True:
            s = self.input(f"{prompt} ").strip()
            if s.isdigit() and 1 <= int(s) <= k: return int(s)
            self.output(f"Please enter an integer 1..{k}.")

    #############################################################################################################################################################
    #############################################################################################################################################################
    '''def maybe_collect_interests(self) -> None:
        state = ensure_state()
        if sec_is_interests_initialized():
            return
        self.output("Let me learn your wellbeing preferences (answer 1/0).")
        prefs = {}
        for q in QUESTION_BANK_INTERESTS:
            prefs[q["id"]] = self._ask_binary(q["text"])
        sec_set_interests(prefs)
        self.output("Saved preferences.\n")'''
    #############################################################################################################################################################
    #############################################################################################################################################################

    
    def ask_burnout(self, questions: int = 3) -> None:
        self.output("Quick check-in. Answer as prompted.")
        turns = 0
        while turns < questions:
            # ********************
            # NEW: 5% chance to ask an open-ended interest question instead of a burnout item
            if sec_should_ask_open_ended_interest(prob=0.05):
                prompt = sec_open_ended_interest_prompt()
                note = self.input(f"{prompt}\n> ").strip()
                sec_record_open_ended_interest(note)
                self.output("Thanks — noted your interest.\n")
                turns += 1
                continue
            # ********************
            q = sec_next_question()
            qid, text = q["qid"], q["text"]
            scale = next(item["scale"] for item in QUESTION_BANK_BURNOUT if item["id"] == qid)
            val = self._ask_binary(text) if scale == "binary" else self._ask_likert(text, int(scale))
            result = sec_record_answer(qid=qid, answer_value=float(val))
            self.output(f"Recorded. BS={result['bs']:.2f}. Next check ~{result['next_interval_min']} min.\n")
            turns += 1

    def schedule_and_apply(self, user: str, days: int = 7) -> None:
        self.output("Analyzing upcoming days for schedule improvements...")
        # Get the authorized email the same way you do today
        email = [f for f in listdir("tokens") if isfile(join("tokens", f))][0].replace(".json", "")
        interests = ensure_state().get("interests", {})

        # Ask the scheduler LLM for proposals
        prompt = (
            f"Plan my next {days} days and suggest 1-2 activities per day; "
            f"email={email}; user={user}; interest={interests}"
        )
        agent_response = get_agent()(prompt)
        ask_user_consent_and_schedule(agent_response, email)
        '''text = getattr(agent_response, "output_text", str(agent_response))

        # Extract machine-usable payload
        payload = _extract_payload(text, email)
        proposals = payload.get("proposals", [])

        if not proposals:
            self.output("No additive proposals returned this time.\n")
            return

        self.output("\nProposals (review one by one):\n")

        added = []
        for idx, p in enumerate(proposals, start=1):
            summary = p.get("summary", "Untitled")
            start_iso = p.get("start")
            end_iso = p.get("end")
            reason = p.get("reason", "")

            # Show a compact preview
            self.output(
                f"{idx}. {summary}\n"
                f"   When: {start_iso} → {end_iso}\n"
                f"   Why:  {reason}\n"
            )

            # Ask for consent per item
            accept = self._ask_binary("Add this to your calendar? (y/n)")
            if accept:
                try:
                    cal_insert_event(
                        email=email,
                        summary=summary,
                        start_iso=start_iso,
                        end_iso=end_iso,
                        description=reason,
                    )
                    added.append(summary)
                    self.output("✓ Added.\n")
                except Exception as e:
                    self.output(f"× Failed to add: {e}\n")
            else:
                self.output("Skipped.\n")

        # Final summary
        if added:
            self.output(f"Done. Added {len(added)} event(s): {', '.join(added)}\n")
        else:
            self.output("No events were added.\n")'''


# NEW: free-form support request (routes via Advisor; may hand off to Therapist)
    def support_router(self, user: str, user_freeform: Optional[str]) -> None:
        if not user_freeform:
            return  # nothing to do

        pretty, intent, handoff = advise_and_render(user_freeform)
        # Print a clean, human-friendly block (no XML)
        print("\n-- Advisor --\n" + pretty)

        if handoff == "yes":
            print("\n-- Therapist session (type /exit to end) --")
            seed = "Thanks for opening up. What feels most urgent for you right now?"
            print(seed)
            while True:
                try:
                    line = self.input("> ").strip()
                except EOFError:
                    break
                if not line:
                    continue
                if line.lower() in ("/exit", "exit", "quit", ":q"):
                    print("Take care. I'm here when you want to continue.")
                    break
                # Therapist returns plain text; we print it once
                reply = therapy_turn(user_name=user, user_msg=line)
                print(reply)

    def run_once(self, user: str, numeric_answer: Optional[float], support_text: Optional[str],
                 schedule_days: int = 7, auto_approve: bool = False, checkin_questions: int = 5) -> None:
        #self.maybe_collect_interests()
        self.ask_burnout(questions=checkin_questions)
        self.schedule_and_apply(user=user, days=schedule_days)
        self.support_router(user=user, user_freeform=support_text)
        self.output("\nDone. Take care! 💙")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True, help="Logical user/session name (e.g., Dae)")
    ap.add_argument("--email", default=None, help="Authorized Google account email (Calendar)")
    ap.add_argument("--answer", type=float, default=None, help="Optional numeric answer to the current burnout item")
    ap.add_argument("--support", type=str, default="", help="Free-form request for Advisor (can trigger Therapist handoff)")
    ap.add_argument("--days", type=int, default=7, help="Scheduler planning window (days)")
    ap.add_argument("--auto-approve", type=str, default="false", help="Apply schedule changes without terminal prompt (true/false)")
    ap.add_argument("--checkin-questions", type=int, default=5, help="Number of burnout questions in the interactive check-in")
    args = ap.parse_args()

    auto = args.auto_approve.lower() in ("true", "1", "yes", "y")

    mgr = Manager()
    mgr.run_once(
        user=args.user,
        numeric_answer=args.answer,
        support_text=args.support or None,
        schedule_days=args.days,
        auto_approve=auto,
        checkin_questions=args.checkin_questions,
    )
    
if __name__ == "__main__":
    print("=== Rule-based Manager ===")
    print("Tip: authorize Google first via oauth_webserver.py → https://localhost:8080/login")
    main()


# *****************************************************************************
# *****************************  API ENDPOINTS  ********************************
# *****************************************************************************
from flask import Blueprint, request, jsonify
manager_api_bp = Blueprint("manager_api", __name__, url_prefix="/api/manager")

    # In-memory session store (restart-safe persistence is optional)
_PROPOSAL_SESSIONS: Dict[str, Dict[str, Any]] = {}

# -------- helpers --------
def get_active_email() -> Optional[str]:
    try:
        files = [f for f in listdir("tokens") if isfile(join("tokens", f)) and f.endswith(".json")]
        return files[0].replace(".json", "") if files else None
    except Exception:
        return None

_PAYLOAD_RE = re.compile(r"<payload>\s*(\{.*?\})\s*</payload>", re.DOTALL)

def _extract_payload(text: str, fallback_email: str) -> dict:
    m = _PAYLOAD_RE.search(text or "")
    if not m:
        return {"email": fallback_email, "proposals": []}
    try:
        return json.loads(m.group(1))
    except Exception:
        return {"email": fallback_email, "proposals": []}

def _session_summary(sess: Dict[str, Any]) -> dict:
    return {
        "finished": sess.get("cursor", 0) >= len(sess.get("queue", [])),
        "email": sess.get("email"),
        "accepted": sess.get("accepted", []),
        "remaining": max(0, len(sess.get("queue", [])) - sess.get("cursor", 0)),
        "index": min(sess.get("cursor", 0), max(0, len(sess.get("queue", [])) - 1)),
    }

@manager_api_bp.route("/checkin/next", methods=["GET"])
def api_checkin_next():
    q = sec_next_question()
    return jsonify(q)

@manager_api_bp.route("/checkin/answer", methods=["POST"])
def api_checkin_answer():
    data = request.get_json(force=True) or {}
    qid = data.get("qid"); value = float(data.get("value", 3))
    result = sec_record_answer(qid=qid, answer_value=value)
    return jsonify(result)

@manager_api_bp.route("/support", methods=["POST"])
def api_support():
    data = request.get_json(force=True) or {}
    user = data.get("user") or "default"
    msg = data.get("message") or ""
    pretty, intent, handoff = advise_and_render(msg)
    return jsonify({"text": pretty, "intent": intent, "handoff": handoff})

@manager_api_bp.route("/reset", methods=["POST"])
def api_reset():
    # wipe the lightweight state the same way your CLI fresh-run does
    from secretary_tools import ensure_state
    st = ensure_state()
    st["answers"] = {}
    st["interests"] = st.get("interests", {})
    return jsonify({"ok": True})

@manager_api_bp.route("/therapist/turn", methods=["POST"])
def api_therapist_turn():
    data = request.get_json(force=True) or {}
    return jsonify({"text": therapy_turn(data.get("user") or "", data.get("message") or "")})

# -------- endpoints --------

# Replace the existing schedule endpoints in manager_agent.py with these fixed versions:

@manager_api_bp.route("/schedule/start", methods=["POST"])
def api_schedule_start():
    """
    Body:  { "user": "krlee", "email": "krlee7001@gmail.com"?, "days": 7 }
    Resp:  { finished, session_id?, email, proposal?, index?, remaining, login_url? }
    """
    data = request.get_json(force=True) or {}
    user = (data.get("user") or "default").strip()
    days = int(data.get("days") or 7)
    email = (data.get("email") or get_active_email() or "").strip()

    if not email:
        return jsonify({"error": "No authorized email; start OAuth at /oauth2/login"}), 400

    # Check authorization
    auth = cal_auth_status(email=email)
    if not auth.get("authorized"):
        return jsonify({"finished": True, "email": email, "login_url": auth.get("login_url")})

    # Get interests from state for the user
    interests = ensure_state().get("interests", {})

    # Ask the scheduler agent for proposals
    prompt = (
        f"Plan my next {days} days and suggest 1-2 activities per day; "
        f"email={email}; user={user}; interest={interests}"
    )
    agent_res = get_scheduler_agent()(prompt)
    text = getattr(agent_res, "output_text", str(agent_res))
    payload = _extract_payload(text, fallback_email=email)

    queue = payload.get("proposals") or []
    session_id = uuid.uuid4().hex
    _PROPOSAL_SESSIONS[session_id] = {
        "email": email,
        "user": user,
        "queue": queue,
        "cursor": 0,
        "accepted": [],
        "created_at": time.time(),
        "raw_text": text,
    }

    if not queue:
        return jsonify({
            "finished": True,
            "email": email,
            "accepted": [],
            "remaining": 0,
            "message": "No suggestions at this time.",
            "raw_text": text  
        })

    first = queue[0]
    return jsonify({
        "finished": False,
        "session_id": session_id,
        "email": email,
        "proposal": first,
        "index": 0,
        "remaining": max(0, len(queue) - 1),
        "raw_text": text  
    })


@manager_api_bp.route("/schedule/decision", methods=["POST"])
def api_schedule_decision():
    """
    Body: { "session_id": "...", "accept": true/false }
    If accepted, insert event immediately.
    Returns next proposal or finished summary.
    """
    data = request.get_json(force=True) or {}
    sid = (data.get("session_id") or "").strip()
    accept = bool(data.get("accept"))

    sess = _PROPOSAL_SESSIONS.get(sid)
    if not sess:
        return jsonify({"error": "Invalid or expired session"}), 400

    queue = sess["queue"]
    i = sess["cursor"]
    if i >= len(queue):
        # Already finished
        return jsonify({**_session_summary(sess), "message": "No more proposals."})

    proposal = queue[i]
    email = sess["email"]

    # If user accepts, insert event now
    if accept:
        try:
            cal_insert_event(
                email=email,
                summary=proposal.get("summary", "Untitled"),
                start_iso=proposal.get("start"),
                end_iso=proposal.get("end"),
                description=proposal.get("reason", ""),
            )
            sess["accepted"].append(proposal)
            result = {"status": "scheduled"}
        except Exception as e:
            result = {"status": "error", "error": str(e)}
    else:
        result = {"status": "skipped"}

    # Advance cursor and return next (or finished)
    sess["cursor"] = i + 1
    if sess["cursor"] >= len(queue):
        resp = {
            "finished": True,
            "email": email,
            "accepted": sess["accepted"],
            "remaining": 0,
            "result": result,
        }
        # Optional: close session
        # _PROPOSAL_SESSIONS.pop(sid, None)
        return jsonify(resp)

    next_prop = queue[sess["cursor"]]
    return jsonify({
        "finished": False,
        "session_id": sid,
        "email": email,
        "proposal": next_prop,
        "index": sess["cursor"],
        "remaining": max(0, len(queue) - (sess["cursor"] + 1)),
        "result": result,
    })


@manager_api_bp.route("/schedule/status", methods=["GET"])
def api_schedule_status():
    """Query current session state (for page reloads)."""
    sid = (request.args.get("session_id") or "").strip()
    sess = _PROPOSAL_SESSIONS.get(sid)
    if not sess:
        return jsonify({"error": "Invalid or expired session"}), 400

    i = sess["cursor"]
    payload = _session_summary(sess)
    if not payload["finished"]:
        payload.update({"session_id": sid, "proposal": sess["queue"][i]})
    return jsonify(payload)


@manager_api_bp.route("/schedule/cancel", methods=["POST"])
def api_schedule_cancel():
    """Cancel and delete the pending proposal session."""
    data = request.get_json(force=True) or {}
    sid = (data.get("session_id") or "").strip()
    sess = _PROPOSAL_SESSIONS.pop(sid, None)
    if not sess:
        return jsonify({"error": "Invalid or expired session"}), 400
    return jsonify({"ok": True, "email": sess.get("email"), "accepted": sess.get("accepted", [])})


@manager_api_bp.route("/health", methods=["GET"])
def api_health():
    return jsonify({"ok": True})

@manager_api_bp.route("/debug/user-context", methods=["POST"])
def debug_user_context():
    """Debug endpoint to check what user context is being received"""
    data = request.get_json(force=True) or {}
    user = data.get("user")
    email = data.get("email") or get_active_email()
    
    # Check current state
    state = ensure_state()
    interests = state.get("interests", {})
    bs = state.get("bs", 0.35)
    
    return jsonify({
        "received_user": user,
        "received_email": email,
        "active_email": get_active_email(),
        "state_interests": interests,
        "state_bs": bs,
        "state_keys": list(state.keys())
    })
