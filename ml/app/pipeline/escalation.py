import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Optional
from scipy.special import softmax

from .models import EscalationResult

logger = logging.getLogger(__name__)

_nli_model = None
_redis_client = None

SENSITIVE_KEYWORDS = [
    "want to die", "no point living", "end my life", "kill myself",
    "rather be dead", "don't want to live", "suicide", "take my own life",
    "hits me", "hurts me", "beats me", "afraid to go home",
    "lock me in", "take my money", "threatening me",
    "hopeless", "no one cares", "nobody cares", "give up",
    "can't go on", "cannot go on", "chest pain", "can't breathe",
    "cannot breathe", "collapsed", "unconscious",
]

HOLDING_MESSAGE = (
    "It sounds like you're going through something very difficult. "
    "Please reach out to the helpline at 1800-650-6060, or SOS at 1767 if urgent. "
    "A care advisor will follow up with you shortly."
)

_STRIKE1_PROBE = (
    "\n\nThe user may be experiencing distress. Respond with extra care and warmth. "
    "Gently ask how they are feeling without being alarming."
)
_STRIKE2_PROBE = (
    "\n\nThe user has shown repeated signs of distress. Respond with compassion. "
    "Ask directly but gently if they are okay and if they need to speak to someone."
)

def _get_nli_model():
    global _nli_model
    if _nli_model is None:
        from sentence_transformers import CrossEncoder
        _nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-small")
    return _nli_model

def _get_redis():
    global _redis_client
    if _redis_client is None:
        import redis as redis_lib
        url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        _redis_client = redis_lib.from_url(url, decode_responses=True)
    return _redis_client

def _get_session_state(session_id: str) -> dict:
    try:
        r = _get_redis()
        raw = r.get(f"strikes:{session_id}")
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning("Redis read failed: %s", e)
    return {"strike_count": 0, "mode": "normal", "trigger_texts": []}

def _save_session_state(session_id: str, state: dict) -> None:
    try:
        r = _get_redis()
        r.set(f"strikes:{session_id}", json.dumps(state), ex=86400)
    except Exception as e:
        logger.warning("Redis write failed: %s", e)

def _log_priority0(session_id: str, state: dict) -> None:
    try:
        from pymongo import MongoClient
        url = os.environ.get("MONGODB_URL", os.environ.get("MONGO_URI", "mongodb://mongo:27017/careapp"))
        client = MongoClient(url, serverSelectionTimeoutMS=2000)
        db = client.get_default_database()
        db.priority0_alerts.insert_one({
            "session_id": session_id,
            "trigger_texts": state.get("trigger_texts", []),
            "strike_count": 3,
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception as e:
        logger.error("Failed to log PRIORITY0 alert to MongoDB: %s", e)

def _strip_punctuation(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower())

def _keyword_match(text: str) -> Optional[str]:
    from rapidfuzz import fuzz
    normalized = _strip_punctuation(text)
    for keyword in SENSITIVE_KEYWORDS:
        if keyword in normalized:
            return keyword
        if fuzz.partial_ratio(keyword, normalized) >= 90:
            return keyword
    return None

def _nli_distress_score(text: str) -> float:
    nli = _get_nli_model()
    scores = nli.predict([(text, "The person is expressing distress, fear, or danger.")])
    probs = softmax(scores[0])
    return float(probs[1])  # entailment index

def check_escalation(text: str, session_id: str) -> EscalationResult:
    state = _get_session_state(session_id)
    strike_count = state["strike_count"]
    mode = state["mode"]
    trigger_texts = state.get("trigger_texts", [])

    # Already at PRIORITY0 — stay there
    if mode == "PRIORITY0":
        return EscalationResult(
            escalated=True,
            escalation_severity="PRIORITY0",
            strike_count=3,
            system_prompt_addon="",
            skip_llm=True,
        )

    # Determine if there's a new signal
    keyword = _keyword_match(text)
    is_keyword_signal = keyword is not None

    # Strike 2+ also checks NLI distress
    is_nli_signal = False
    if strike_count >= 1 and not is_keyword_signal:
        is_nli_signal = _nli_distress_score(text) > 0.65

    has_signal = is_keyword_signal or is_nli_signal

    if not has_signal:
        return EscalationResult(
            escalated=False,
            escalation_severity=None,
            strike_count=strike_count,
            system_prompt_addon="",
            skip_llm=False,
        )

    # New signal — increment strike
    trigger_texts.append(text[:200])
    strike_count += 1

    if strike_count >= 3:
        mode = "PRIORITY0"
        new_state = {"strike_count": 3, "mode": "PRIORITY0", "trigger_texts": trigger_texts}
        _save_session_state(session_id, new_state)
        _log_priority0(session_id, new_state)
        return EscalationResult(
            escalated=True,
            escalation_severity="PRIORITY0",
            strike_count=3,
            system_prompt_addon="",
            skip_llm=True,
        )

    mode = "sensitive_mode"
    _save_session_state(session_id, {"strike_count": strike_count, "mode": mode, "trigger_texts": trigger_texts})
    probe = _STRIKE1_PROBE if strike_count == 1 else _STRIKE2_PROBE
    return EscalationResult(
        escalated=True,
        escalation_severity="sensitive_mode",
        strike_count=strike_count,
        system_prompt_addon=probe,
        skip_llm=False,
    )
