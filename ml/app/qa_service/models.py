from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ReviewStatus(str, Enum):
    """Status of review item."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"


class ConfidenceLevel(str, Enum):
    """Confidence level classification."""
    HIGH = "high"  # >= 0.8
    MEDIUM = "medium"  # 0.6 - 0.79
    LOW = "low"  # < 0.6


class HallucinationCheck(BaseModel):
    """Result of hallucination check."""
    is_hallucination: bool
    score: float  # 0.0-1.0, higher = more likely hallucination
    reason: str
    matched_sources: List[str] = Field(default_factory=list)
    unmatched_claims: List[str] = Field(default_factory=list)


class QACheckResult(BaseModel):
    """Result of complete QA check on response."""
    response: str
    confidence: float
    hallucination_check: HallucinationCheck
    confidence_level: ConfidenceLevel
    needs_review: bool  # True if confidence < 0.7 or hallucination detected
    reason_for_review: Optional[str] = None


class ReviewQueueItem(BaseModel):
    """Item in human review queue."""
    review_id: str = Field(..., description="Unique review ID")
    session_id: str
    patient_id: str
    user_input: str
    llm_response: str
    confidence: float
    hallucination_score: float

    status: ReviewStatus = ReviewStatus.PENDING
    reviewer_notes: Optional[str] = None
    approved_response: Optional[str] = None  # Modified response if rejected/modified

    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "review_id": "rev_abc123",
                "session_id": "sess_xyz",
                "patient_id": "pat_001",
                "user_input": "What medications can I take?",
                "llm_response": "You can take ibuprofen and paracetamol...",
                "confidence": 0.65,
                "hallucination_score": 0.2,
                "status": "pending",
                "created_at": "2026-06-18T12:00:00Z"
            }
        }


class ReviewAction(BaseModel):
    """Action taken during review."""
    review_id: str
    action: ReviewStatus
    reviewer_id: str
    notes: Optional[str] = None
    approved_response: Optional[str] = None


class AuditLog(BaseModel):
    """Audit log entry for all interactions."""
    audit_id: str
    session_id: str
    patient_id: str
    turn_count: int
    user_input: str
    llm_response: str
    confidence: float
    hallucination_score: float
    was_reviewed: bool
    review_action: Optional[str] = None  # approved, rejected, modified

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
