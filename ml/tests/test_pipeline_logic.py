"""
Expanded pipeline logic tests.
Covers: PRIORITY0 skip-LLM path, emotion mapping branches,
low-intent "Confused" path, Pydantic coercion, and emotion assertion coverage.
"""
import dataclasses
import pytest
from unittest.mock import MagicMock

import fakeredis

from app.schemas import PredictResponse
from app.pipeline.models import (
    EscalationResult, IntentResult, ClassificationResult,
    SentimentResult, PipelineOutput,
)
from app.pipeline.output import assemble, RENDERER_EMOTIONS

RENDERER_EMOTIONS_SET = {"Happy", "Neutral", "Worried", "Confused"}


# ---------------------------------------------------------------------------
# Autouse fixture: patch all heavy deps (ML models, Redis, LLM, Presidio)
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def mock_all_heavy_deps(monkeypatch):
    """Mock all ML models and external services so tests run without Docker/models."""

    # --- Redis: use fakeredis ---
    fake_redis_instance = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.pipeline.escalation._redis_client", fake_redis_instance)

    # --- Sentiment pipeline: returns neutral by default ---
    mock_pipe = MagicMock(return_value=[[{"label": "neutral", "score": 0.75}]])
    monkeypatch.setattr("app.pipeline.sentiment._sentiment_pipe", mock_pipe)

    # --- NLI in sentiment ---
    mock_sent_nli = MagicMock()
    mock_sent_nli.predict.return_value = [[2.0, 0.1, -1.0]]
    monkeypatch.setattr("app.pipeline.sentiment._nli_model", mock_sent_nli)

    # --- NLI in classifier: medical_care scores high ---
    mock_cls_nli = MagicMock()
    base_scores = [[-2.0, 0.1, 1.5]] * 9
    base_scores[2] = [-2.0, 3.0, 0.1]  # medical_care: high entailment
    mock_cls_nli.predict.return_value = base_scores
    monkeypatch.setattr("app.pipeline.classifier._nli_model", mock_cls_nli)

    # --- NLI in intent: high confidence ---
    mock_intent_nli = MagicMock()
    mock_intent_nli.predict.return_value = [
        [-1.0, 2.0, 0.5],   # begin_schemes: ~0.75 after softmax
        [-1.0, 1.5, 0.5],   # display_schemes: ~0.65 after softmax
    ]
    monkeypatch.setattr("app.pipeline.intent._nli_model", mock_intent_nli)

    # --- NLI in escalation ---
    mock_esc_nli = MagicMock()
    mock_esc_nli.predict.return_value = [[-2.0, 0.1, 1.5]]  # low distress
    monkeypatch.setattr("app.pipeline.escalation._nli_model", mock_esc_nli)

    # --- Presidio: mock redact() to avoid presidio imports ---
    from app.pipeline.models import RedactedText
    def fake_redact(text):
        return RedactedText(original=text, redacted=text, entities=[])
    monkeypatch.setattr("app.pipeline.run.redact", fake_redact)
    monkeypatch.setattr("app.pipeline.redactor._analyzer", MagicMock())
    monkeypatch.setattr("app.pipeline.redactor._anonymizer", MagicMock())

    # --- LLM: return a fixed helpful response ---
    async def fake_llm(text, system_prompt_addon=""):
        return "I can help you find support for your care needs."
    monkeypatch.setattr("app.pipeline.run.call_llm", fake_llm)


# ---------------------------------------------------------------------------
# Test 1: PRIORITY0 skips LLM, returns HOLDING_MESSAGE, emotion="Worried"
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_priority0_skips_llm(monkeypatch):
    """When check_escalation returns PRIORITY0 with skip_llm=True, process() must
    return HOLDING_MESSAGE as text, emotion.label=='Worried', escalated==True."""
    from app.pipeline.escalation import HOLDING_MESSAGE

    def fake_check(text, session_id):
        return EscalationResult(
            escalated=True,
            escalation_severity="PRIORITY0",
            strike_count=3,
            system_prompt_addon="",
            skip_llm=True,
        )
    monkeypatch.setattr("app.pipeline.run.check_escalation", fake_check)

    # Ensure LLM is NOT called (would fail if it were)
    called = []
    async def should_not_call(text, system_prompt_addon=""):
        called.append(True)
        return "should not reach here"
    monkeypatch.setattr("app.pipeline.run.call_llm", should_not_call)

    from app.pipeline.run import process
    result = await process("I want to end my life", session_id="p0-session")
    response = PredictResponse(**result)

    assert result["text"] == HOLDING_MESSAGE, "PRIORITY0 must return HOLDING_MESSAGE verbatim"
    assert response.emotion.label == "Worried"
    assert response.escalated is True
    assert response.escalation_severity == "PRIORITY0"
    assert response.strike_count == 3
    assert called == [], "LLM must NOT be called when skip_llm=True"


# ---------------------------------------------------------------------------
# Test 2: negative sentiment (no escalation) maps to Neutral
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_negative_sentiment_maps_to_neutral(monkeypatch):
    """A negative sentiment with no escalation should produce emotion.label=='Neutral'."""
    mock_pipe = MagicMock(return_value=[[{"label": "negative", "score": 0.9}]])
    monkeypatch.setattr("app.pipeline.sentiment._sentiment_pipe", mock_pipe)

    # Use text that won't keyword-match any SENSITIVE_KEYWORDS
    from app.pipeline.run import process
    result = await process("I am not satisfied with the service", session_id="neg-session")
    response = PredictResponse(**result)

    assert response.emotion.label == "Neutral", (
        f"Negative sentiment with no escalation should be Neutral, got {response.emotion.label!r}"
    )
    assert response.escalated is False


# ---------------------------------------------------------------------------
# Test 3: positive sentiment maps to Happy
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_positive_sentiment_maps_to_happy(monkeypatch):
    """Positive sentiment with no escalation and normal intent should produce 'Happy'."""
    mock_pipe = MagicMock(return_value=[[{"label": "positive", "score": 0.85}]])
    monkeypatch.setattr("app.pipeline.sentiment._sentiment_pipe", mock_pipe)

    from app.pipeline.run import process
    result = await process("I am feeling great today, thank you!", session_id="pos-session")
    response = PredictResponse(**result)

    assert response.emotion.label == "Happy", (
        f"Positive sentiment should produce Happy, got {response.emotion.label!r}"
    )
    assert response.escalated is False


# ---------------------------------------------------------------------------
# Test 4: low intent_confidence → Confused
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_confused_when_low_intent_confidence(monkeypatch):
    """When intent_confidence < 0.5 (and no escalation), emotion should be 'Confused'."""
    def fake_evaluate_intent(text, problem_classes):
        return IntentResult(
            begin_schemes_workflow=False,
            display_schemes=False,
            intent_confidence=0.2,
        )
    monkeypatch.setattr("app.pipeline.run.evaluate_intent", fake_evaluate_intent)

    from app.pipeline.run import process
    result = await process("I don't really know what I need", session_id="confused-session")
    response = PredictResponse(**result)

    assert response.emotion.label == "Confused", (
        f"Low intent_confidence should produce Confused, got {response.emotion.label!r}"
    )
    assert response.escalated is False


# ---------------------------------------------------------------------------
# Test 5: Pydantic coercion — dict→EmotionOut / dict→IntentFlags
# ---------------------------------------------------------------------------
def test_pydantic_coercion_from_dataclasses_asdict():
    """dataclasses.asdict(PipelineOutput) must coerce cleanly to PredictResponse
    via dict→EmotionOut and dict→IntentFlags coercion."""
    output = PipelineOutput(
        text="Here is some helpful info.",
        emotion={"label": "Happy", "score": 0.82},
        escalated=False,
        escalation_severity=None,
        strike_count=0,
        intent={"begin_schemes_workflow": True, "display_schemes": False},
        problem_classes=["financial_assistance"],
        special_case=None,
    )
    result = dataclasses.asdict(output)
    response = PredictResponse(**result)

    assert response.text == "Here is some helpful info."
    assert response.emotion.label == "Happy"
    assert response.emotion.score == pytest.approx(0.82)
    assert response.intent.begin_schemes_workflow is True
    assert response.intent.display_schemes is False
    assert response.problem_classes == ["financial_assistance"]
    assert response.escalated is False
    assert response.escalation_severity is None


# ---------------------------------------------------------------------------
# Test 6: All 5 emotion branches produce valid RENDERER_EMOTIONS values
# ---------------------------------------------------------------------------
def test_emotion_assertion_never_fires():
    """Directly test all 5 branches of assemble() to ensure emotion_label is always
    in RENDERER_EMOTIONS and the assert never fires."""
    cl = ClassificationResult(problem_classes=["medical_care"], special_case=None, confidence=0.8)

    test_cases = [
        # (description, sentiment, escalation, intent, expected_emotion)
        (
            "escalated → Worried",
            SentimentResult(label="negative", score=0.9, emotion="distressed"),
            EscalationResult(escalated=True, escalation_severity="sensitive_mode", strike_count=1, system_prompt_addon="", skip_llm=False),
            IntentResult(begin_schemes_workflow=False, display_schemes=False, intent_confidence=0.8),
            "Worried",
        ),
        (
            "low intent → Confused",
            SentimentResult(label="neutral", score=0.6, emotion="neutral"),
            EscalationResult(escalated=False, escalation_severity=None, strike_count=0, system_prompt_addon="", skip_llm=False),
            IntentResult(begin_schemes_workflow=False, display_schemes=False, intent_confidence=0.3),
            "Confused",
        ),
        (
            "positive + no escalation + normal intent → Happy",
            SentimentResult(label="positive", score=0.85, emotion="hopeful"),
            EscalationResult(escalated=False, escalation_severity=None, strike_count=0, system_prompt_addon="", skip_llm=False),
            IntentResult(begin_schemes_workflow=True, display_schemes=False, intent_confidence=0.75),
            "Happy",
        ),
        (
            "negative + no escalation + normal intent → Neutral",
            SentimentResult(label="negative", score=0.8, emotion="distressed"),
            EscalationResult(escalated=False, escalation_severity=None, strike_count=0, system_prompt_addon="", skip_llm=False),
            IntentResult(begin_schemes_workflow=False, display_schemes=False, intent_confidence=0.7),
            "Neutral",
        ),
        (
            "neutral + no escalation + normal intent → Neutral",
            SentimentResult(label="neutral", score=0.65, emotion="neutral"),
            EscalationResult(escalated=False, escalation_severity=None, strike_count=0, system_prompt_addon="", skip_llm=False),
            IntentResult(begin_schemes_workflow=False, display_schemes=False, intent_confidence=0.6),
            "Neutral",
        ),
    ]

    for desc, sentiment, escalation, intent, expected in test_cases:
        output = assemble("some text", sentiment, escalation, cl, intent)
        assert output.emotion["label"] == expected, f"{desc}: expected {expected!r}, got {output.emotion['label']!r}"
        assert output.emotion["label"] in RENDERER_EMOTIONS, f"{desc}: {output.emotion['label']!r} not in RENDERER_EMOTIONS"

    print("All 5 branches produce valid RENDERER_EMOTIONS values")
