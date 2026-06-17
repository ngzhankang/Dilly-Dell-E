from .models import SentimentResult, EscalationResult, ClassificationResult, IntentResult, PipelineOutput

RENDERER_EMOTIONS = {"Happy", "Neutral", "Worried", "Confused"}

def assemble(
    llm_text: str,
    sentiment: SentimentResult,
    escalation: EscalationResult,
    classification: ClassificationResult,
    intent: IntentResult,
) -> PipelineOutput:
    # Emotion mapping — apply rules in order
    if escalation.escalated:
        emotion_label = "Worried"
        emotion_score = sentiment.score
    elif intent.intent_confidence < 0.5:
        emotion_label = "Confused"
        emotion_score = intent.intent_confidence
    elif sentiment.label == "positive":
        emotion_label = "Happy"
        emotion_score = sentiment.score
    elif sentiment.label == "negative":
        # block negative from renderer — Unity has no negative state
        emotion_label = "Neutral"
        emotion_score = 0.5
    else:
        emotion_label = "Neutral"
        emotion_score = sentiment.score

    assert emotion_label in RENDERER_EMOTIONS, f"Invalid emotion: {emotion_label}"

    return PipelineOutput(
        text=llm_text,
        emotion={"label": emotion_label, "score": round(emotion_score, 3)},
        escalated=escalation.escalated,
        escalation_severity=escalation.escalation_severity,
        strike_count=escalation.strike_count,
        intent={
            "begin_schemes_workflow": intent.begin_schemes_workflow,
            "display_schemes": intent.display_schemes,
        },
        problem_classes=classification.problem_classes,
        special_case=classification.special_case,
    )
