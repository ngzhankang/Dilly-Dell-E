import re
from .models import SentimentResult

# NOTE: raw "negative" label is used for escalation detection only.
# It is remapped to "Neutral" in output.py before reaching the renderer.
# Do not change this — the Unity animation rig has no negative state.

_sentiment_pipe = None
_nli_model = None

EMOTION_MAP = {
    "hopeless": "distressed",
    "no point": "distressed",
    "alone": "distressed",
    "scared": "anxious",
    "worried": "anxious",
    "angry": "frustrated",
    "unfair": "frustrated",
    "thank": "grateful",
    "hope": "hopeful",
    "better": "hopeful",
}

_LABEL_MAP = {
    "positive": "positive",
    "neutral": "neutral",
    "negative": "negative",
    "label_0": "negative",
    "label_1": "neutral",
    "label_2": "positive",
}

def _get_sentiment_pipe():
    global _sentiment_pipe
    if _sentiment_pipe is None:
        from transformers import pipeline as hf_pipeline
        _sentiment_pipe = hf_pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment-latest",
            top_k=1,
        )
    return _sentiment_pipe

def _get_nli_model():
    global _nli_model
    if _nli_model is None:
        from sentence_transformers import CrossEncoder
        _nli_model = CrossEncoder("cross-encoder/nli-deberta-v3-small")
    return _nli_model

def _normalise_label(raw: str) -> str:
    return _LABEL_MAP.get(raw.lower(), raw.lower())

def _detect_emotion(text: str) -> str:
    lower = text.lower()
    for keyword, emotion in EMOTION_MAP.items():
        if keyword in lower:
            return emotion
    return "neutral"

def analyse(text: str) -> SentimentResult:
    pipe = _get_sentiment_pipe()
    raw = pipe(text)
    while isinstance(raw, list):
        raw = raw[0]
    label = _normalise_label(raw["label"])
    score = float(raw["score"])
    emotion = _detect_emotion(text)
    return SentimentResult(label=label, score=score, emotion=emotion)
