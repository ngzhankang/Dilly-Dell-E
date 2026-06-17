import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# fakeredis for Redis without a real server
import fakeredis

from app.schemas import PredictResponse

RENDERER_EMOTIONS = {"Happy", "Neutral", "Worried", "Confused"}


@pytest.fixture(autouse=True)
def mock_all_heavy_deps(monkeypatch):
    """Mock all ML models and external services so tests run without Docker/models."""

    # --- Redis: use fakeredis ---
    fake_redis_instance = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr("app.pipeline.escalation._redis_client", fake_redis_instance)

    # --- Sentiment pipeline: returns neutral ---
    mock_pipe = MagicMock(return_value=[[{"label": "neutral", "score": 0.75}]])
    monkeypatch.setattr("app.pipeline.sentiment._sentiment_pipe", mock_pipe)

    # --- NLI in sentiment (Tier 2 escalation check) ---
    mock_sent_nli = MagicMock()
    mock_sent_nli.predict.return_value = [[2.0, 0.1, -1.0]]  # low entailment after softmax
    monkeypatch.setattr("app.pipeline.sentiment._nli_model", mock_sent_nli)

    # --- NLI in classifier: medical_care scores high, others low ---
    mock_cls_nli = MagicMock()
    base_scores = [[-2.0, 0.1, 1.5]] * 9
    base_scores[2] = [-2.0, 3.0, 0.1]  # medical_care: high entailment
    mock_cls_nli.predict.return_value = base_scores
    monkeypatch.setattr("app.pipeline.classifier._nli_model", mock_cls_nli)

    # --- NLI in intent: moderate begin_schemes score ---
    mock_intent_nli = MagicMock()
    mock_intent_nli.predict.return_value = [
        [-1.0, 2.0, 0.5],   # begin_schemes: entailment prob ~0.75
        [-1.0, 1.5, 0.5],   # display_schemes: entailment prob ~0.65
    ]
    monkeypatch.setattr("app.pipeline.intent._nli_model", mock_intent_nli)

    # --- NLI in escalation ---
    mock_esc_nli = MagicMock()
    mock_esc_nli.predict.return_value = [[-2.0, 0.1, 1.5]]  # low distress
    monkeypatch.setattr("app.pipeline.escalation._nli_model", mock_esc_nli)

    # --- Presidio: mock redact() entirely to avoid presidio imports ---
    from app.pipeline.models import RedactedText
    def fake_redact(text):
        return RedactedText(original=text, redacted=text, entities=[])
    monkeypatch.setattr("app.pipeline.run.redact", fake_redact)
    monkeypatch.setattr("app.pipeline.redactor._analyzer", MagicMock())
    monkeypatch.setattr("app.pipeline.redactor._anonymizer", MagicMock())

    # --- LLM: return a fixed helpful response ---
    async def fake_llm(text, system_prompt_addon=""):
        return "I can help you find support for your medication and care needs."

    monkeypatch.setattr("app.pipeline.run.call_llm", fake_llm)


@pytest.mark.asyncio
async def test_normal_response_schema():
    """Normal input produces valid PredictResponse with allowed emotion."""
    from app.pipeline.run import process
    result = await process("I need help with my medication costs", session_id="test-session-1")
    response = PredictResponse(**result)

    assert response.emotion.label in RENDERER_EMOTIONS
    assert 0.0 <= response.emotion.score <= 1.0
    assert response.escalated is False
    assert response.escalation_severity is None
    assert response.strike_count == 0
    assert isinstance(response.problem_classes, list)
    assert isinstance(response.intent.begin_schemes_workflow, bool)
    assert isinstance(response.intent.display_schemes, bool)


@pytest.mark.asyncio
async def test_escalated_response_schema(monkeypatch):
    """Input with a Tier 1 keyword escalates to sensitive_mode with Worried emotion."""
    # Make escalation return strike 1 / sensitive_mode
    from app.pipeline.escalation import EscalationResult
    def fake_check(text, session_id):
        return EscalationResult(
            escalated=True,
            escalation_severity="sensitive_mode",
            strike_count=1,
            system_prompt_addon="Be careful.",
            skip_llm=False,
        )
    monkeypatch.setattr("app.pipeline.run.check_escalation", fake_check)

    from app.pipeline.run import process
    result = await process("I feel hopeless and nobody cares", session_id="test-session-2")
    response = PredictResponse(**result)

    assert response.emotion.label in RENDERER_EMOTIONS
    assert response.emotion.label == "Worried"
    assert response.escalated is True
    assert response.escalation_severity == "sensitive_mode"
    assert response.strike_count == 1


@pytest.mark.asyncio
async def test_special_case_schema(monkeypatch):
    """Input with no matching bucket returns special_case populated."""
    from app.pipeline.classifier import ClassificationResult
    def fake_classify(text):
        return ClassificationResult(
            problem_classes=[],
            special_case="Person is experiencing neighbour harassment and does not know which agency to contact.",
            confidence=0.1,
        )
    monkeypatch.setattr("app.pipeline.run.classify", fake_classify)

    from app.pipeline.run import process
    result = await process("My neighbour keeps stealing my mail", session_id="test-session-3")
    response = PredictResponse(**result)

    assert response.emotion.label in RENDERER_EMOTIONS
    assert response.problem_classes == []
    assert response.special_case is not None
    assert len(response.special_case) > 10
