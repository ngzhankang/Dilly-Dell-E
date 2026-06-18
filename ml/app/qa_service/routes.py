import logging
from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel

from .models import ReviewQueueItem, ReviewStatus, ReviewAction
from .qa_service import QAService
from .review_service import ReviewQueueService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/qa", tags=["qa-service"])

_qa_service: QAService = None
_review_service: ReviewQueueService = None


def init_qa_services(qa_service: QAService, review_service: ReviewQueueService):
    """Initialize QA services."""
    global _qa_service, _review_service
    _qa_service = qa_service
    _review_service = review_service
    logger.info("QA routes initialized")


def get_qa_service() -> QAService:
    if _qa_service is None:
        raise RuntimeError("QA service not initialized")
    return _qa_service


def get_review_service() -> ReviewQueueService:
    if _review_service is None:
        raise RuntimeError("Review service not initialized")
    return _review_service


# ============ QA Endpoints ============


class CheckResponseRequest(BaseModel):
    """Request to check response quality."""
    response: str
    confidence: float
    retrieved_sources: List[str] = []


@router.post("/check-response")
async def check_response(request: CheckResponseRequest) -> dict:
    """
    Perform QA check on a response.

    Checks:
    - Confidence level classification
    - Hallucination detection
    - Escalation to review if needed

    Returns:
        QACheckResult with confidence level and review decision
    """
    try:
        qa_service = get_qa_service()
        result = await qa_service.check_response(
            response=request.response,
            confidence=request.confidence,
            retrieved_sources=request.retrieved_sources
        )
        return result.dict()
    except Exception as e:
        logger.error(f"Error checking response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class EscalateRequest(BaseModel):
    """Request to escalate to review."""
    session_id: str
    patient_id: str
    user_input: str
    response: str
    confidence: float
    hallucination_score: float


@router.post("/escalate")
async def escalate_response(request: EscalateRequest) -> dict:
    """
    Escalate a response to human review queue.

    Used when:
    - Confidence score < 0.7
    - Hallucination detected
    - LLM uncertainty requires verification

    Returns:
        review_id for tracking
    """
    try:
        qa_service = get_qa_service()
        review_id = await qa_service.escalate_to_review(
            session_id=request.session_id,
            patient_id=request.patient_id,
            user_input=request.user_input,
            response=request.response,
            confidence=request.confidence,
            hallucination_score=request.hallucination_score
        )
        return {"review_id": review_id, "status": "escalated"}
    except Exception as e:
        logger.error(f"Error escalating: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LogInteractionRequest(BaseModel):
    """Request to log interaction."""
    session_id: str
    patient_id: str
    turn_count: int
    user_input: str
    llm_response: str
    confidence: float
    hallucination_score: float
    was_reviewed: bool = False
    review_action: str = None


@router.post("/log-interaction")
async def log_interaction(request: LogInteractionRequest) -> dict:
    """Log interaction for audit trail."""
    try:
        qa_service = get_qa_service()
        audit_id = await qa_service.log_interaction(
            session_id=request.session_id,
            patient_id=request.patient_id,
            turn_count=request.turn_count,
            user_input=request.user_input,
            llm_response=request.llm_response,
            confidence=request.confidence,
            hallucination_score=request.hallucination_score,
            was_reviewed=request.was_reviewed,
            review_action=request.review_action
        )
        return {"audit_id": audit_id}
    except Exception as e:
        logger.error(f"Error logging interaction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ Review Queue Endpoints ============


@router.get("/reviews/pending")
async def get_pending_reviews(limit: int = 50) -> dict:
    """
    Get pending reviews for human reviewer dashboard.

    Returns:
        List of pending ReviewQueueItems
    """
    try:
        review_service = get_review_service()
        items = await review_service.get_pending_reviews(limit=limit)
        return {
            "pending_count": len(items),
            "items": [item.dict() for item in items]
        }
    except Exception as e:
        logger.error(f"Error getting pending reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reviews/{review_id}")
async def get_review(review_id: str) -> dict:
    """Get a specific review item."""
    try:
        review_service = get_review_service()
        item = await review_service.get_review(review_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Review not found: {review_id}")
        return item.dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ApproveReviewRequest(BaseModel):
    """Request to approve a review."""
    reviewer_id: str
    notes: str = None


@router.post("/reviews/{review_id}/approve")
async def approve_review(review_id: str, request: ApproveReviewRequest) -> dict:
    """Approve a review (accept LLM response)."""
    try:
        review_service = get_review_service()
        success = await review_service.approve_review(
            review_id=review_id,
            reviewer_id=request.reviewer_id,
            notes=request.notes
        )
        if not success:
            raise HTTPException(status_code=404, detail=f"Review not found: {review_id}")
        return {"review_id": review_id, "status": "approved"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error approving review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class RejectReviewRequest(BaseModel):
    """Request to reject a review."""
    reviewer_id: str
    notes: str = None


@router.post("/reviews/{review_id}/reject")
async def reject_review(review_id: str, request: RejectReviewRequest) -> dict:
    """Reject a review (reject LLM response)."""
    try:
        review_service = get_review_service()
        success = await review_service.reject_review(
            review_id=review_id,
            reviewer_id=request.reviewer_id,
            notes=request.notes
        )
        if not success:
            raise HTTPException(status_code=404, detail=f"Review not found: {review_id}")
        return {"review_id": review_id, "status": "rejected"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rejecting review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ModifyReviewRequest(BaseModel):
    """Request to modify and approve a review."""
    reviewer_id: str
    approved_response: str
    notes: str = None


@router.post("/reviews/{review_id}/modify")
async def modify_and_approve(review_id: str, request: ModifyReviewRequest) -> dict:
    """Modify and approve a review (provide corrected response)."""
    try:
        review_service = get_review_service()
        success = await review_service.modify_and_approve(
            review_id=review_id,
            reviewer_id=request.reviewer_id,
            approved_response=request.approved_response,
            notes=request.notes
        )
        if not success:
            raise HTTPException(status_code=404, detail=f"Review not found: {review_id}")
        return {"review_id": review_id, "status": "modified"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error modifying review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reviews/stats")
async def get_review_stats() -> dict:
    """Get review queue statistics."""
    try:
        review_service = get_review_service()
        stats = await review_service.get_review_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/ready", tags=["health"])
async def health_check() -> dict:
    """Check if QA service is ready."""
    try:
        qa_service = get_qa_service()
        review_service = get_review_service()
        return {
            "status": "ready",
            "qa_service": qa_service.health_check(),
            "review_service": review_service.health_check()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))
