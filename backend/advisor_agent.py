# advisor_agent.py
"""
Advisor Agent (Bedrock, via Strands)
- Produces short, supportive guidance and ready-to-use phrasing.
- Infers intent from free-form user input and (optionally) signals a therapist handoff.

Env:
  AWS_REGION                         (default: us-east-1)
  BEDROCK_MODEL_ADVISOR              (optional; you can point to an inference profile ARN instead of model_id)
"""

from __future__ import annotations
import os
import re
from typing import Optional, Tuple, Dict
from strands import Agent
from strands.models import BedrockModel

# Pull state + interest helpers from your secretary tools
from secretary_tools import (
    ensure_state,
    sec_get_structured_interests,
    sec_get_open_interests,
    sec_open_ended_interest_prompt,
)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# If you prefer an Inference Profile ARN, set BEDROCK_MODEL_ADVISOR and replace model_id below with that ARN.
# MODEL_ID_ADVISOR = os.environ.get(
#     "BEDROCK_MODEL_ADVISOR",
#     "arn:aws:bedrock:us-east-1:337852209640:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0"
# )

def _model():
    return BedrockModel(
        model_id="us.anthropic.claude-sonnet-4-20250514-v1:0",  # or MODEL_ID_ADVISOR
        temperature=0.2,
        top_p=0.9,
        max_tokens=1500,
        region_name=AWS_REGION,
    )

# -------------------- PROMPT ENGINEERING --------------------
TASK_CONTEXT = """
You are the Advisor Agent, designed to help users reduce burnout and feel supported.

Your behavior adapts to the user's burnout score (BS):
1. High Burnout (BS > 0.7):
   - Act professionally, like an experienced workplace coach or psychology practitioner.
   - Provide structured, practical strategies (boundary-setting, stress relief, scheduling breaks).
   - Keep tone supportive but formal, with clear actionable advice.

2. Normal Burnout (BS ≤ 0.7):
   - Act more like a caring friend or peer.
   - Be warm, conversational, and empathetic.
   - Focus on encouragement, light suggestions, and emotional support.
   - Use casual, uplifting language without sounding clinical.

Always ensure responses are stigma-free, supportive, and tailored to the user’s situation.
"""

TONE_CONTEXT = """
Maintain a gentle, supportive, and stigma-free tone at all times.

- When BS > 0.7 → Be professional, structured, and reassuring. Speak like a trusted workplace advisor or coach.
- When BS ≤ 0.7 → Be warm, casual, and conversational. Speak like a caring friend who listens and encourages.

Regardless of style, always be empathetic, respectful, and empowering.
"""

# NEW: intent inference + therapist handoff routing
INTENT_AND_OUTPUT_POLICY = """
Intent inference and routing:
- Parse the user's message and infer exactly ONE primary intent:
  • "professional_email" → a complete email template.
  • "suggested_phrases"  → short bullet phrases for workplace communication.
  • "suggested_activities" → short list tailored to preferences.
  • "chat_support" → the user wants a back-and-forth supportive conversation (therapist-style). In this case, set <handoff target="therapist">yes</handoff>.
- If none of the above is clear AND there is a user message, output only a <supportive_message> plus a short starter <advisor_chat> (no info dump), and set:
  <intent>chat_support</intent> and <handoff target="therapist">yes</handoff>.

Strict output rule:
- Output only the ONE requested artifact. Do not include other sections.
- Always include a brief <supportive_message> tailored to the BS (keep it short if handing off).
"""

TASK_DESCRIPTION = """
Here are the key rules for your interaction:

1. Always provide a supportive_message → brief encouragement tailored to the user’s Burnout Score (BS).

2. Adapt tone based on Burnout Score (BS):
   * High BS (>0.70): act as a professional advisor or coach. Prioritize boundary-setting, stress relief, and simple restorative activities. Keep language structured, direct, and reassuring.
   * Mid BS (0.40–0.70): act as a supportive peer. Provide encouragement, recognition of effort, and practical balance tips. Blend professionalism with warmth.
   * Low BS (<0.40): act more like a caring friend. Focus on positive reinforcement, proactive resilience-building, and light wellbeing prompts. Keep the style casual, friendly, and uplifting.

3. Response mode:
   * If the user provides a message → infer intent and respond with only that artifact (plus supportive_message).
   * If there is no user message (system-triggered/proactive mode) → in addition to supportive_message, include:
       - suggested_phrases
       - professional_email
       - suggested_activities (music links are allowed if helpful)
"""

# Your existing examples retained (abridged here for brevity) + the new intent/handoff spec
EXAMPLES = """
<example>
User: "Can I get an email template to express my burnout condition due to my workload?"
-> intent=professional_email, handoff=no
</example>

<example>
User: "I can’t keep up with all these deadlines anymore. Could you please talk with me to make me feel better?"
-> intent=chat_support, handoff=yes
When handoff=yes, add user's name and at least 2 appropriate emojis such as purple heart, smiling or sad emoji to sound friendlier.   
DO NOT include <supportive_message>

</example>
"""

OUTPUT_FORMATTING = """
Store the response generated as:

<response>
<intent>one_of[professional_email|suggested_phrases|suggested_activities|chat_support]</intent>
<handoff target="therapist">yes|no</handoff>
<supportive_message>...</supportive_message>

<!-- EXACTLY ONE of the following blocks, matching the intent -->
<professional_email>...</professional_email>
<!-- OR -->
<suggested_phrases>
- ...
- ...
</suggested_phrases>
<!-- OR -->
<suggested_activities>
- ...
- ...
</suggested_activities>
<!-- OR -->
<advisor_chat>short seed message to start the chat</advisor_chat>
</response>

But do no output your response. Manager Agent will perform the output.
"""

IMMEDIATE_TASK = "Generate the requested artifact based on user input and BS; keep output minimal and empathetic."
PRECOGNITION = "Think step by step about BS and requested format before writing."

ADVISOR_SYSTEM_PROMPT = f"""
{TASK_CONTEXT}
{TONE_CONTEXT}
{INTENT_AND_OUTPUT_POLICY}
{TASK_DESCRIPTION}
{EXAMPLES}
{IMMEDIATE_TASK}
{PRECOGNITION}
{OUTPUT_FORMATTING}
"""

# ---- Lazy singleton ----
_ADVISOR: Optional[Agent] = None
def get_agent() -> Agent:
    global _ADVISOR
    if _ADVISOR is None:
        _ADVISOR = Agent(
            name="Advisor Agent",
            system_prompt=ADVISOR_SYSTEM_PROMPT,
            tools=[],
            model=_model(),
        )
    return _ADVISOR

def _session_bs_and_prefs() -> tuple[float, list[str], str]:
    """Pull current BS and interests from secretary/state for richer context."""
    state = ensure_state()
    bs = float(state.get("bs", 0.35))
    structured = sec_get_structured_interests() or {}
    open_notes = sec_get_open_interests() or []
    active_structured = [k for k, v in structured.items() if v]
    # If no interests captured yet, embed a tiny coach prompt to elicit them next time.
    open_interest_line = ""
    if not active_structured and not open_notes:
        open_q = sec_open_ended_interest_prompt()
        open_interest_line = f"\n[ActionSuggestion] Ask user: {open_q}\n"
    preferences = active_structured + open_notes
    return bs, preferences, open_interest_line

# -------------------- Public API --------------------
def advise(user_msg: Optional[str]) -> str:
    """
    Flexible entrypoint: infer intent from user_msg and produce the single requested output.
    Returns the raw LLM-tagged string (<response>...</response>).
    """
    bs, preferences, interest_hint = _session_bs_and_prefs()
    payload = {
        "user_msg": user_msg if user_msg else "NA",
        "bs": round(bs, 2),
        "preferences": preferences,
        "context": "Advisor invoked by manager",
    }
    prompt = (
        "Consider the following runtime context:\n"
        f"{payload}\n\n"
        f"{interest_hint}"
        "Return the final content in plain text."
    )
    res = get_agent()(prompt)
    return getattr(res, "output_text", str(res))

# Back-compatible wrapper used by older manager code.
def generate_support(context: str = "", user_msg: Optional[str] = None) -> str:
    return advise(user_msg=user_msg or None)

# -------------------- Parsing & Pretty Rendering --------------------
_TAG = lambda t: re.compile(fr"<{t}>(.*?)</{t}>", re.IGNORECASE | re.DOTALL)
_HANDOFF = re.compile(r"<handoff[^>]*>(.*?)</handoff>", re.IGNORECASE | re.DOTALL)

def parse_advisor_response(raw: str) -> Dict[str, str]:
    """Extract fields from Advisor's XML-ish output."""
    def get(tag: str) -> str:
        m = _TAG(tag).search(raw)
        return (m.group(1).strip() if m else "")
    intent = get("intent").lower() or "chat_support"
    handoff = (_HANDOFF.search(raw).group(1).strip().lower()
               if _HANDOFF.search(raw) else "no")
    return {
        "intent": intent,
        "handoff": handoff,
        "supportive_message": get("supportive_message"),
        "professional_email": get("professional_email"),
        "suggested_phrases": get("suggested_phrases"),
        "suggested_activities": get("suggested_activities"),
        "advisor_chat": get("advisor_chat"),
    }

def render_advisor_console(parsed: Dict[str, str]) -> str:
    """Turn parsed fields into a clean CLI-friendly string (no tags)."""
    lines = []
    sm = parsed.get("supportive_message", "").strip()
    if sm:
        lines.append(sm)

    intent = parsed.get("intent", "chat_support")
    if intent == "professional_email":
        body = parsed.get("professional_email", "").strip()
        if body:
            lines += ["", "Email draft:", body]
    elif intent == "suggested_phrases":
        body = parsed.get("suggested_phrases", "").strip()
        if body:
            lines += ["", "Suggested phrases:", body]
    elif intent == "suggested_activities":
        body = parsed.get("suggested_activities", "").strip()
        if body:
            lines += ["", "Suggested activities:", body]
    else:  # chat_support
        seed = parsed.get("advisor_chat", "").strip()
        if seed:
            lines += ["", seed]

    return "\n".join(lines).strip()

# Convenience for manager: returns (pretty_text, intent, handoff)
def advise_and_render(user_msg: str) -> Tuple[str, str, str]:
    raw = advise(user_msg)
    parsed = parse_advisor_response(raw)
    pretty = render_advisor_console(parsed)
    return pretty, parsed["intent"], parsed["handoff"]

# Back-compatible wrapper used by older manager code.
def generate_support(context: str = "", user_msg: Optional[str] = None) -> str:
    pretty, _intent, _handoff = advise_and_render(user_msg or "")
    return pretty

# *****************************************************************************
# *****************************  API ENDPOINTS  ********************************
# *****************************************************************************
try:
    from flask import Blueprint, request, jsonify
    advisor_api_bp = Blueprint("advisor_api", __name__, url_prefix="/api/advisor")

    @advisor_api_bp.route("/advise", methods=["POST"])
    def api_advise():
        data = request.get_json(force=True) or {}
        msg = data.get("user_msg") or ""
        pretty, intent, handoff = advise_and_render(msg)
        return jsonify({"text": pretty, "intent": intent, "handoff": handoff})

    @advisor_api_bp.route("/health", methods=["GET"])
    def api_health():
        return jsonify({"ok": True})
except Exception:  # Flask not installed in some contexts
    advisor_api_bp = None