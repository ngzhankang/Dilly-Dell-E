from scipy.special import softmax
from .models import IntentResult

_nli_model = None

def _get_nli_model():
    global _nli_model
    if _nli_model is None:
        from sentence_transformers import CrossEncoder
        _nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-small")
    return _nli_model

def evaluate_intent(text: str, problem_classes: list[str]) -> IntentResult:
    nli = _get_nli_model()
    context = text
    if problem_classes:
        context = f"{text} (concerns: {', '.join(problem_classes)})"

    pairs = [
        (context, "The person wants to find or apply for a social care service or grant."),
        (context, "The person is asking to see a list of available schemes or services."),
    ]
    scores = nli.predict(pairs)

    begin_probs = softmax(scores[0])
    display_probs = softmax(scores[1])

    # index [1] is entailment (label order: contradiction=0, entailment=1, neutral=2)
    begin_score = float(begin_probs[1])
    display_score = float(display_probs[1])

    begin_schemes_workflow = begin_score > 0.60
    display_schemes = display_score > 0.65

    intent_confidence = max(begin_score, display_score)
    if begin_score < 0.4 and display_score < 0.4:
        intent_confidence = (begin_score + display_score) / 2.0

    return IntentResult(
        begin_schemes_workflow=begin_schemes_workflow,
        display_schemes=display_schemes,
        intent_confidence=intent_confidence,
    )
