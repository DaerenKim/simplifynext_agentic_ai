# therapist_agent.py
from __future__ import annotations
import os
from strands import Agent
from strands.models import BedrockModel
import re

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Light, fast model for back-and-forth chat
def _model():
    return BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",  # or use a lighter Haiku if you prefer
        temperature=0.3,
        top_p=0.95,
        max_tokens=800,
        region_name=AWS_REGION,
    )

THERAPIST_SYSTEM_PROMPT = """
You are a supportive, empathetic, non-judgmental therapist-style companion focused on burnout, stress, and work overwhelm.

Goals:
- Listen actively; reflect feelings and needs.
- Ask one gentle, concrete question at a time.
- Offer 1–2 tiny, optional coping steps.
- Encourage boundaries and self-kindness.
- Avoid diagnosis/medical claims; avoid pathologizing language.
- If user expresses imminent self-harm or danger, encourage contacting local emergency services or a trusted person.

Style:
- Warm, concise, de-stigmatizing.
- Validate emotions; normalize difficulty.
- Keep suggestions optional and small.
- Sound human and empathetic.
- Add emojis (limited to purple hearts and face emojis) to sound friendlier.   
- End with one kind, open-ended question to continue.

Output format: plain text only.
"""

_THERAPIST = None
def _agent() -> Agent:
    global _THERAPIST
    if _THERAPIST is None:
        _THERAPIST = Agent(model=_model(), system_prompt=THERAPIST_SYSTEM_PROMPT)
    return _THERAPIST

# --------- Sanitization helpers to remove accidental repetition ---------
_SENT_SPLIT = re.compile(r"(?<=[\.\?\!])\s+")
_PARA_SPLIT = re.compile(r"\n\s*\n+")

def _dedupe(text: str) -> str:
    s = text.strip()

    # Case 1: entire reply duplicated once (AB == AB)
    n = len(s)
    if n % 2 == 0 and s[: n // 2] == s[n // 2 :]:
        s = s[: n // 2].strip()

    # Case 2: drop consecutive duplicate paragraphs
    paras = [p.strip() for p in _PARA_SPLIT.split(s) if p.strip()]
    out_paras = []
    for p in paras:
        if not out_paras or _norm(out_paras[-1]) != _norm(p):
            out_paras.append(p)
    s = "\n\n".join(out_paras)

    # Case 3: drop duplicate consecutive sentences & global exact dupes
    sentences = [t.strip() for t in _SENT_SPLIT.split(s) if t.strip()]
    out_sents, seen = [], set()
    for sent in sentences:
        key = _norm(sent).lower()
        if (not out_sents or _norm(out_sents[-1]).lower() != key) and key not in seen:
            out_sents.append(sent)
            seen.add(key)

    s = " ".join(out_sents).strip()

    # Length guardrail
    if len(s) > 1200:
        s = s[:1200].rsplit(" ", 1)[0] + "…"

    return s

def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", t).strip()

# --------- Public API ---------
def therapy_turn(user_name: str | None, user_msg: str) -> str:
    """
    One therapist-style turn. Returns plain text (sanitized).
    """
    user_name = user_name or ""
    prompt = f'User "{user_name}" says: {user_msg}'
    res = _agent()(prompt)
    raw = getattr(res, "output_text", str(res)).strip()
    return _dedupe(raw)

# *****************************************************************************
# *****************************  API ENDPOINTS  ********************************
# *****************************************************************************
try:
    from flask import Blueprint, request, jsonify
    therapist_api_bp = Blueprint("therapist_api", __name__, url_prefix="/api/therapist")

    @therapist_api_bp.route("/turn", methods=["POST"])
    def api_turn():
        data = request.get_json(force=True) or {}
        return jsonify({"text": therapy_turn(data.get("user") or "", data.get("message") or "")})

    @therapist_api_bp.route("/health", methods=["GET"])
    def api_health():
        return jsonify({"ok": True})
except Exception:
    therapist_api_bp = None