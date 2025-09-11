# secretary_agent.py
"""
Secretary Agent (LLM wrapper) for asking questions & recording answers.
Env:
  AWS_REGION
  BEDROCK_MODEL_SECRETARY           (Inference Profile ARN recommended)
"""
from __future__ import annotations
import os
from strands import Agent, tool
from strands.models import BedrockModel
from secretary_tools import (
    sec_next_question, sec_record_answer, sec_set_interests, sec_get_bs
)

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
MODEL_ID_SECRETARY = os.environ.get(
    "BEDROCK_MODEL_SECRETARY",
    "arn:aws:bedrock:us-east-1:337852209640:inference-profile/global.anthropic.claude-sonnet-4-20250514-v1:0"
)

def _model():
    return BedrockModel(model_id=MODEL_ID_SECRETARY, region_name=AWS_REGION, streaming=True)

# -------------------- PROMPT ENGINEERING --------------------
TASK_CONTEXT = """
You are the Secretary Agent for a burnout-support application.
Your mission is to:
(a) conduct burnout check-in questions with the user, one at a time,
(b) update Burnout Score (BS ∈ [0,1]) using the calculator tool based on the user's responses,
(c) return the next notification interval based on the updated BS,
(d) record optional user interests for restorative activities via set_interests when explicitly provided.
"""

TONE_CONTEXT = """
Be concise, clear, and supportive. Act like a respectful check-in assistant, not a therapist.
"""

TASK_DESCRIPTION = """
Rules:
- Always ask exactly ONE burnout evaluation question at a time (via sec_next_question).
- When the user responds with a numeric value, call sec_record_answer:
  * update state
  * next_interval_minutes
- NEVER invent math; always use the other tool to support.
- On request, store interests via sec_set_interests to store preferences.
- You may fetch the latest BS via sec_get_bs when needed.
- Output only the structured fields requested:
  * <question_to_ask qid="...">text</question_to_ask> (when you are asking a question)
  * <user_response qid="...">numeric</user_response> (echo)
  * <updated_BS>0..1</updated_BS>
  * <next_interval>minutes</next_interval>
"""

EXAMPLES = """
<example>
User: "Answer to q1 is 3. Current BS=0.40, user=Dae"
Secretary (calls calculator with current_bs=0.40, qid=q1, answer_value=3, user_name="Dae"):
<response>
<user_response qid="q1">3</user_response>
<updated_BS>0.43</updated_BS>
<next_interval>120</next_interval>
</response>
</example>

<example>
User: "Next question after q1. user=Dae"
Secretary:
<response>
<question_to_ask qid="q2">Rate your ability to focus (1=excellent, 5=very poor).</question_to_ask>
</response>
</example>

<example>
User: "Set interests to likes_exercise=1, likes_meditation=1 for user=Dae"
Secretary (calls set_interests):
<response>
<updated_BS>0.40</updated_BS>
<next_interval>180</next_interval>
</response>
</example>
"""

IMMEDIATE_TASK = """
Decide whether to (a) ask the next question, (b) update BS from a provided numeric answer, or (c) store interests when asked.
Return only the necessary structured fields.
"""

PRECOGNITION = """
Think through: Do I need to fetch a question (get_question), compute an update (calculator), or store interests (set_interests)?
Use the minimal number of tool calls.
"""

OUTPUT_FORMATTING = """
Wrap your answer in <response></response> tags.
"""

SECRETARY_SYSTEM_PROMPT = f"""
{TASK_CONTEXT}
{TONE_CONTEXT}
{TASK_DESCRIPTION}
{EXAMPLES}
{IMMEDIATE_TASK}
{PRECOGNITION}
{OUTPUT_FORMATTING}
"""

# ---- Lazy singleton ----
_SECRETARY = None
def get_agent() -> Agent:
    global _SECRETARY
    if _SECRETARY is None:
        _SECRETARY = Agent(
            name="Secretary Agent",
            system_prompt=SECRETARY_SYSTEM_PROMPT,
            tools=[sec_next_question, sec_record_answer, sec_set_interests, sec_get_bs],
            model=_model(),
        )
    return _SECRETARY

secretary_agent: Agent = get_agent()

# convenience pass-throughs if you want to call them via LLM agent:
def ask() -> str:
    return str(get_agent("Ask next question."))

def answer(qid: str, value: float) -> str:
    return str(get_agent(f"Record answer {value} for {qid}"))

# *****************************************************************************
# *****************************  API ENDPOINTS  ********************************
# *****************************************************************************
try:
    from flask import Blueprint, request, jsonify
    secretary_api_bp = Blueprint("secretary_api", __name__, url_prefix="/api/secretary")

    @secretary_api_bp.route("/checkin/next", methods=["GET"])
    def api_next():
        return jsonify(sec_next_question())

    @secretary_api_bp.route("/checkin/answer", methods=["POST"])
    def api_answer():
        data = request.get_json(force=True) or {}
        return jsonify(sec_record_answer(qid=data["qid"], answer_value=float(data["value"])))

    @secretary_api_bp.route("/bs", methods=["GET"])
    def api_bs():
        return jsonify({"bs": float(sec_get_bs())})

    @secretary_api_bp.route("/health", methods=["GET"])
    def api_health():
        return jsonify({"ok": True})
except Exception:
    secretary_api_bp = None