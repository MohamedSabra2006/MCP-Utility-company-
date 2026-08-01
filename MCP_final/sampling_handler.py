"""
MCP Sampling Handler: Formats `sampling/createMessage` requests and parses
the host LLM's response.

IMPORTANT — what this module is and is not:
This module does NOT call any LLM API (Gemini, OpenAI, Anthropic, etc.) directly.
Per the MCP spec, sampling is the server asking the CLIENT to run a completion
through whatever model the connected host application has configured — the
server never holds an API key or picks the model itself. That request/response
actually crosses the wire via `ctx.session.create_message(...)` in tools.py.

This module only builds the message payload (`build_sampling_messages`) and
interprets the text the host model sends back (`parse_medical_analysis`).
"""
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("NCEDC_SamplingHandler")

SYSTEM_PROMPT = (
    "You are a compliance classifier for an Egyptian electricity utility (NCEDC), "
    "operating under EgyptERA Law 87 of 2015. You will be given a field inspector's "
    "freeform note (often in Egyptian Arabic) about a customer account flagged for "
    "possible disconnection. Decide whether the account shows signs of an active "
    "medical exemption (e.g. dialysis, ventilator, oxygen concentrator, life-support "
    "equipment) or another protection trigger (e.g. an illegal/unmetered connection "
    "worth flagging separately). "
    "Respond with ONLY a JSON object, no prose, no markdown fences, matching this shape: "
    '{"has_active_life_support": bool, "other_flags": [string], '
    '"decision": "PROTECTED - DO NOT DISCONNECT" | "NO EXEMPTION - PROCEED", '
    '"confidence": number between 0 and 1, "reasoning": string}'
)

# Fallback used only when the host model's reply cannot be parsed as the
# expected JSON shape — this is a parsing failure, not a silent approval.
_PARSE_FAILURE_RESULT = {
    "has_active_life_support": None,
    "other_flags": [],
    "decision": "PARSE_ERROR - MANUAL REVIEW REQUIRED",
    "confidence": 0.0,
    "reasoning": "Host LLM response could not be parsed as the expected JSON shape.",
}


def build_sampling_messages(document_text: str) -> list[dict]:
    """
    Builds the `messages` list for a `sampling/createMessage` request.
    The caller (a tool in tools.py) is responsible for actually sending this
    through `ctx.session.create_message(...)` — this function only shapes the
    payload.
    """
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"Inspector's note:\n\"\"\"\n{document_text}\n\"\"\"",
            },
        }
    ]


def parse_medical_analysis(raw_model_text: str) -> dict:
    """
    Parses the text the host LLM returned for `sampling/createMessage` into
    the structured evaluation dict the tool layer stores. If the model didn't
    return valid JSON, this returns an explicit PARSE_ERROR result rather than
    guessing — a wrong classification here is a safety-relevant failure mode,
    so it must be visible, not swallowed.
    """
    cleaned = raw_model_text.strip()
    # Host models sometimes wrap JSON in markdown fences despite instructions.
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Could not parse host LLM sampling response as JSON: %r", raw_model_text)
        return dict(_PARSE_FAILURE_RESULT)

    required_keys = {"has_active_life_support", "decision", "confidence", "reasoning"}
    if not required_keys.issubset(parsed.keys()):
        logger.warning("Host LLM sampling response missing required keys: %r", parsed)
        return dict(_PARSE_FAILURE_RESULT)

    parsed.setdefault("other_flags", [])
    return parsed
