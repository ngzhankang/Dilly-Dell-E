from dataclasses import dataclass
from typing import Optional

@dataclass
class PiiEntity:
    entity_type: str
    original: str
    placeholder: str
    start: int
    end: int

@dataclass
class RedactedText:
    original: str
    redacted: str
    entities: list[PiiEntity]

@dataclass
class SentimentResult:
    # NOTE: raw "negative" label is used for escalation detection only.
    # It is remapped to "Neutral" in output.py before reaching the renderer.
    # Do not change this — the Unity animation rig has no negative state.
    label: str       # "positive" | "neutral" | "negative" (RAW — never sent to renderer)
    score: float
    emotion: str     # raw keyword-based emotion (for internal use)

@dataclass
class EscalationResult:
    escalated: bool
    escalation_severity: Optional[str]   # None | "sensitive_mode" | "PRIORITY0"
    strike_count: int                    # 0, 1, 2, or 3
    system_prompt_addon: str             # extra text injected into LLM system prompt
    skip_llm: bool                       # True only for PRIORITY0

@dataclass
class IntentResult:
    begin_schemes_workflow: bool
    display_schemes: bool
    intent_confidence: float             # max score; < 0.5 triggers "Confused" emotion

@dataclass
class ClassificationResult:
    problem_classes: list[str]
    special_case: Optional[str]
    confidence: float

@dataclass
class PipelineOutput:
    text: str
    emotion: dict                        # {"label": str, "score": float} — renderer-safe
    escalated: bool
    escalation_severity: Optional[str]
    strike_count: int
    intent: dict                         # {"begin_schemes_workflow": bool, "display_schemes": bool}
    problem_classes: list[str]
    special_case: Optional[str]
