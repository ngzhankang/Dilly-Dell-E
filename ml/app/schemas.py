from typing import Optional
from pydantic import BaseModel


# --- Existing (keep) ---
class QueryRequest(BaseModel):
    message: str


class Source(BaseModel):
    title: str
    url: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]


# --- New: /predict endpoint ---
class PredictRequest(BaseModel):
    text: str
    session_id: str


class EmotionOut(BaseModel):
    label: str   # exactly one of: "Happy", "Neutral", "Worried", "Confused"
    score: float


class IntentFlags(BaseModel):
    begin_schemes_workflow: bool
    display_schemes: bool


class PredictResponse(BaseModel):
    text: str
    emotion: EmotionOut
    escalated: bool
    escalation_severity: Optional[str]
    strike_count: int
    intent: IntentFlags
    problem_classes: list[str]
    special_case: Optional[str]
