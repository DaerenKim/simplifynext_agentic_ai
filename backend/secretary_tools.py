# secretary_tools.py
"""
Secretary tools: state, burnout score, Q&A, interests.
State is persisted in STATE_PATH (JSON).
Env:
  STATE_PATH                          (default: ./agent_state.json)
  USER_TIMEZONE                       (default: Asia/Singapore)
"""
from __future__ import annotations
import os, json, math
from dataclasses import dataclass
from datetime import datetime, timezone
import random
from typing import Dict, Any, List, Optional 
from dateutil import tz
from strands import tool

STATE_PATH = os.environ.get("STATE_PATH", "./agent_state.json")
USER_TIMEZONE = os.environ.get("USER_TIMEZONE", "Asia/Singapore")

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def to_user_tz(dt: datetime, tz_name: str = USER_TIMEZONE) -> datetime:
    return dt.astimezone(tz.gettz(tz_name))

# ---------- Question banks ----------
QUESTION_BANK_BURNOUT = [
    {"id": "q1",  "text": "I dread going to work each day. (1=Disagree, 5=Agree)",                                          "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q2",  "text": "I often don’t really care what happens to my colleagues or customers. (1=Disagree, 5=Agree)",   "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q3",  "text": "I feel dissatisfied with my job more often than not. (1=Disagree, 5=Agree)",                    "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q4",  "text": "Starting a new project often feels pointless. (1=Disagree, 5=Agree)",                             "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q5",  "text": "No matter how hard I work, I don’t feel appreciated. (1=Disagree, 5=Agree)",                     "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q6",  "text": "Having to interact with people at my job just feels like a burden. (1=Disagree, 5=Agree)",        "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q7",  "text": "The work I do makes a real difference in the world. (1=Disagree, 5=Agree)",                     "scale": 5, "weight": 0.05, "direction": -1},
    {"id": "q8",  "text": "Even 'normal' workdays leave me feeling completely mentally drained. (1=Disagree, 5=Agree)",     "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q9",  "text": "I’m proud of what I’ve accomplished over the course of my career. (1=Disagree, 5=Agree)",        "scale": 5, "weight": 0.05, "direction": -1},
    {"id": "q10", "text": "Even when work is tough, I’m able to stay upbeat. (1=Disagree, 5=Agree)",                        "scale": 5, "weight": 0.05, "direction": -1},
    {"id": "q11", "text": "I often feel incapable of handling the tasks required by my job. (1=Disagree, 5=Agree)",          "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q12", "text": "It's hard to be there for my loved ones because I’m so drained by work. (1=Disagree, 5=Agree)",   "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q13", "text": "I’m often dissatisfied with the quality of my work but don’t have the energy to improve it. (1=Disagree, 5=Agree)", "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q14", "text": "The frustrations of my job have turned me into a cynical person. (1=Disagree, 5=Agree)",          "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q15", "text": "Whenever anyone asks me about my job, all I can do is complain. (1=Disagree, 5=Agree)",           "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q16", "text": "Being asked to take on a new task fills me with dread. (1=Disagree, 5=Agree)",                    "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q17", "text": "The pressures of my job feel impossible to manage. (1=Disagree, 5=Agree)",                        "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q18", "text": "I often feel like a robot, doing my job without thought. (1=Disagree, 5=Agree)",                  "scale": 5, "weight": 0.05, "direction": +1},
    {"id": "q19", "text": "I have control over how I spend my time at work. (1=Disagree, 5=Agree)",                         "scale": 5, "weight": 0.05, "direction": -1},
    {"id": "q20", "text": "I quickly feel overwhelmed when a new problem comes up at work. (1=Disagree, 5=Agree)",          "scale": 5, "weight": 0.05, "direction": +1},
]

def ensure_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_PATH):
        s = {
            "bs": 0.35,
            "last_eval": None,
            "eval_queue": [],
            "answers": {},
            "interests": {},
            "interests_initialized": False,  
            "interests_open": [],
            "history": [],
        }
        with open(STATE_PATH, "w") as f: json.dump(s, f, indent=2)
        return s
    with open(STATE_PATH, "r") as f: return json.load(f)

def save_state(s: Dict[str, Any]) -> None:
    with open(STATE_PATH, "w") as f: json.dump(s, f, indent=2)

@dataclass
class BurnoutScore:
    alpha: float = 0.2

    @staticmethod
    def _normalize(q: Dict[str, Any], v: int) -> float:
        if q["scale"] == "binary": return float(v)
        if isinstance(q["scale"], int) and q["scale"] > 1:
            return (float(v) - 1.0) / (q["scale"] - 1.0)
        raise ValueError("Unsupported scale")
    
    def update_one(self, current_bs: float, qid: str, value: float, bank: List[Dict[str, Any]]) -> float:        
        q = next(q for q in bank if q["id"] == qid)
        norm = self._normalize(q, value)        
        inst = norm if q["direction"] > 0 else 1 - norm
        updated = current_bs * (1 - self.alpha * q["weight"]) + inst * (self.alpha * q["weight"])        
        return max(0.0, min(1.0, updated))

    '''
    def update_one(self, current_bs: float, qid: str, value: float, bank: List[Dict[str, Any]]) -> float:
        q = next(q for q in bank if q["id"] == qid)
        norm = self._normalize(q, value)
        contrib = 0.7 * (norm if q["direction"] > 0 else -1.0 * norm)
        updated = self.alpha * contrib + (1.0 - self.alpha) * current_bs
        return updated
    '''

    @staticmethod
    def next_interval_minutes(bs: float) -> int:
        MIN_INTERVAL_MIN, MAX_INTERVAL_MIN, LOGISTIC_STEEPNESS = 30, 4*60, 10.0
        ratio = 1.0 / (1.0 + math.exp(-LOGISTIC_STEEPNESS * (bs - 0.5)))
        minutes = MIN_INTERVAL_MIN + (MAX_INTERVAL_MIN - MIN_INTERVAL_MIN) * (1.0 - ratio)
        return int(round(minutes))

_bs_model = BurnoutScore()

# ---------- Tools ----------
@tool
def sec_next_question() -> dict:
    state = ensure_state()
    queue = state.get("eval_queue") or []
    if not queue:
        queue = [q["id"] for q in QUESTION_BANK_BURNOUT]
    qid = queue.pop(0)
    state["eval_queue"] = queue
    save_state(state)
    qtext = next(q["text"] for q in QUESTION_BANK_BURNOUT if q["id"] == qid)
    return {"qid": qid, "text": qtext}

@tool
def sec_record_answer(qid: str, answer_value: float) -> dict:
    state = ensure_state()
    answers = state.get("answers", {})
    answers[qid] = answer_value
    state["answers"] = answers
    new_bs = _bs_model.update_one(state["bs"], qid, float(answer_value), QUESTION_BANK_BURNOUT)
    state["bs"] = new_bs
    state["last_eval"] = now_utc().isoformat()
    state["history"].append({"ts": now_utc().isoformat(), "bs": new_bs})
    save_state(state)
    return {"bs": new_bs, "next_interval_min": _bs_model.next_interval_minutes(new_bs)}

@tool
def sec_set_interests(preferences: dict) -> dict:
    state = ensure_state()
    interests = state.get("interests", {})
    interests.update({k: 1 if v else 0 for k, v in preferences.items()})
    state["interests"] = interests
    state["interests_initialized"] = True
    save_state(state)
    return interests

@tool
def sec_get_bs() -> float:
    return ensure_state().get("bs", 0.35)

@tool
def sec_is_interests_initialized() -> bool:
    return bool(ensure_state().get("interests_initialized"))

@tool
def sec_get_structured_interests() -> Dict[str, int]:
    return ensure_state().get("interests", {}) or {}

@tool
def sec_get_open_interests() -> List[str]:
    return ensure_state().get("interests_open", []) or []

@tool
def sec_open_ended_interest_prompt() -> str:
    # A gentle, reusable question
    return ("What’s an interest or activity you genuinely enjoy that helps you recharge "
            "(e.g., music, cycling, cooking, gaming, photography)? Feel free to add details.")

@tool
def sec_record_open_ended_interest(note: str) -> List[str]:
    state = ensure_state()
    lst = state.get("interests_open", []) or []
    note = (note or "").strip()
    if note:
        lst.append(note)
        state["interests_open"] = lst
        save_state(state)
    return lst

@tool
def sec_should_ask_open_ended_interest(prob: float = 0.05) -> bool:
    # 5% chance each check-in turn
    try:
        return random.random() < prob
    except Exception:
        return False

# We now support a GUI "multi-select" for interests. The catalog provides the buttons to render.
# Users can pick multiple. We expose tools to (a) return the catalog, (b) REPLACE interests
# with the chosen set (typical for a multi-select "Next" action), (c) UPSERT/merge interests,
# (d) CLEAR interests.

# Canonical catalog (ids are stable; labels can be shown in UI)
_INTEREST_CATALOG: List[Dict[str, Any]] = [
    {"id": "exercise",    "label": "Exercise",                    "aliases": ["workout", "run", "jog", "walk", "walking", "yoga", "stretch"]},
    {"id": "sleep",       "label": "Sleep all day",               "aliases": ["nap", "rest"]},
    {"id": "eat",         "label": "Eat",                         "aliases": ["food", "dining", "meal", "cook", "cooking"]},
    {"id": "meditate",    "label": "Meditate",                    "aliases": ["mindfulness", "breathing", "breathwork"]},
    {"id": "travel",      "label": "Travel",                      "aliases": ["trip", "vacation", "getaway"]},
    {"id": "social",      "label": "Spend time with friends",     "aliases": ["friends", "socialize", "hangout", "meet", "call"]},
    {"id": "read",        "label": "Read",                        "aliases": ["reading", "books", "book"]},
    {"id": "movies",      "label": "Watch movies",                "aliases": ["movie", "film", "tv", "netflix"]},
    {"id": "create_art",  "label": "Create art",                  "aliases": ["draw", "painting", "paint", "sketch", "craft", "creative", "art"]},
]

def _norm(s: str) -> str:
    return "".join(ch.lower() for ch in s.strip() if ch.isalnum() or ch in (" ", "_", "-"))

def _to_struct_key(cat_id: str) -> str:
    # stored as likes_<id>: 1/0
    return f"likes_{cat_id}"

def _resolve_catalog_id(value: str) -> Optional[str]:
    """
    Map user-provided label/id/synonym to a catalog id.
    Accepts raw strings from GUI or free text.
    """
    if not value:
        return None
    n = _norm(value)
    # direct id match
    for item in _INTEREST_CATALOG:
        if n == _norm(item["id"]):
            return item["id"]
    # label match
    for item in _INTEREST_CATALOG:
        if n == _norm(item["label"]):
            return item["id"]
    # aliases match
    for item in _INTEREST_CATALOG:
        for a in item.get("aliases", []):
            if n == _norm(a):
                return item["id"]
    return None

@tool
def sec_interest_catalog() -> List[Dict[str, Any]]:
    """
    Return the catalog for GUI rendering.
    Example element: {"id": "exercise", "label": "Exercise"}
    """
    return [{"id": x["id"], "label": x["label"]} for x in _INTEREST_CATALOG]

@tool
def sec_replace_interests(selected: List[str]) -> Dict[str, int]:
    """
    Replace the structured interests with the provided multi-select values.
    - selected: list of ids/labels/synonyms (strings) chosen in the GUI.
    - Unknown items are appended to open-ended interests.
    Returns the resulting structured interests dict.
    """
    state = ensure_state()
    # build fresh map, turning only selected to 1
    interests: Dict[str, int] = { _to_struct_key(x["id"]): 0 for x in _INTEREST_CATALOG }
    open_notes: List[str] = state.get("interests_open", []) or []

    for raw in selected or []:
        cid = _resolve_catalog_id(str(raw))
        if cid:
            interests[_to_struct_key(cid)] = 1
        else:
            # Preserve unknowns as free text prefs
            note = (str(raw) or "").strip()
            if note:
                open_notes.append(note)

    state["interests"] = interests
    state["interests_open"] = open_notes
    state["interests_initialized"] = True
    save_state(state)
    return interests

@tool
def sec_upsert_interests(selected: List[str]) -> Dict[str, int]:
    """
    Merge the provided selections with existing interests (set selected -> 1; keep others).
    Unknown items are appended to open-ended interests.
    """
    state = ensure_state()
    interests: Dict[str, int] = state.get("interests", {}) or {}
    # ensure baseline keys exist
    for item in _INTEREST_CATALOG:
        interests.setdefault(_to_struct_key(item["id"]), 0)
    open_notes: List[str] = state.get("interests_open", []) or []

    for raw in selected or []:
        cid = _resolve_catalog_id(str(raw))
        if cid:
            interests[_to_struct_key(cid)] = 1
        else:
            note = (str(raw) or "").strip()
            if note:
                open_notes.append(note)

    state["interests"] = interests
    state["interests_open"] = open_notes
    state["interests_initialized"] = True
    save_state(state)
    return interests

@tool
def sec_clear_interests() -> Dict[str, int]:
    """
    Clear structured interests (sets all to 0) and keeps open-ended notes unchanged.
    """
    state = ensure_state()
    interests = { _to_struct_key(x["id"]): 0 for x in _INTEREST_CATALOG }
    state["interests"] = interests
    state["interests_initialized"] = False
    save_state(state)
    return interests


'''
How to use from your GUI

Render choices: call sec_interest_catalog() → iterate and display pill buttons for each label.
On submit (multi-select): send the selected labels/ids to sec_replace_interests(selected=[...]).
Optional: if you want additive behavior (progressively adding interests), use sec_upsert_interests([...]) instead.
Compatibility: existing code that reads sec_get_structured_interests() keeps working. Values are still {likes_<id>: 0|1}. Open-ended/free-text goes to interests_open.

'''

# *****************************************************************************
# *****************************  API ENDPOINTS  ********************************
# *****************************************************************************
try:
    from flask import Blueprint, request, jsonify
    secretary_tools_api_bp = Blueprint("secretary_tools_api", __name__, url_prefix="/api/secretary-tools")

    @secretary_tools_api_bp.route("/interest/catalog", methods=["GET"])
    def api_interest_catalog():
        return jsonify(sec_interest_catalog())

    @secretary_tools_api_bp.route("/interest/replace", methods=["POST"])
    def api_interest_replace():
        data = request.get_json(force=True) or {}
        return jsonify(sec_replace_interests(data.get("selected") or []))

    @secretary_tools_api_bp.route("/interest/upsert", methods=["POST"])
    def api_interest_upsert():
        data = request.get_json(force=True) or {}
        return jsonify(sec_upsert_interests(data.get("selected") or []))

    @secretary_tools_api_bp.route("/interest/clear", methods=["POST"])
    def api_interest_clear():
        return jsonify(sec_clear_interests())

    @secretary_tools_api_bp.route("/state/bs", methods=["GET"])
    def api_state_bs():
        return jsonify({"bs": sec_get_bs()})
except Exception:
    secretary_tools_api_bp = None