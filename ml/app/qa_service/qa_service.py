import logging
import uuid
from datetime import datetime
from typing import List, Optional
from pymongo import MongoClient

from .models import (
    QACheckResult,
    ConfidenceLevel,
    HallucinationCheck,
    ReviewQueueItem,
    ReviewStatus,
    AuditLog,
)

logger = logging.getLogger(__name__)


class QAService:
    """
    Quality Assurance service that:
    1. Scores response confidence
    2. Checks for hallucinations
    3. Escalates low-confidence/hallucinated responses
    4. Logs all interactions for audit
    """

    def __init__(self, mongo_uri: str = "mongodb://localhost:27017", db_name: str = "dilly_dell_e"):
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.review_queue = self.db.review_queue
        self.audit_logs = self.db.audit_logs
        self._create_indexes()
        logger.info("QA Service initialized")

    def _create_indexes(self):
        """Create MongoDB indexes."""
        try:
            self.review_queue.create_index("review_id", unique=True)
            self.review_queue.create_index([("status", 1), ("created_at", -1)])
            self.review_queue.create_index("patient_id")
            self.audit_logs.create_index("audit_id", unique=True)
            self.audit_logs.create_index([("patient_id", 1), ("timestamp", -1)])
            logger.info("QA indexes created")
        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")

    async def check_response(
        self,
        response: str,
        confidence: float,
        retrieved_sources: List[str]
    ) -> QACheckResult:
        """
        Perform complete QA check on response.

        1. Classify confidence level
        2. Check for hallucinations
        3. Determine if needs review

        Args:
            response: The LLM response
            confidence: Confidence score from RAG (0.0-1.0)
            retrieved_sources: Sources used to generate response

        Returns:
            QACheckResult with checks and review decision
        """
        try:
            # Check for hallucinations
            hallucination_check = self._check_hallucinations(response, retrieved_sources)

            # Classify confidence level
            conf_level = self._classify_confidence(confidence)

            # Determine if needs review
            needs_review = confidence < 0.7 or hallucination_check.is_hallucination
            reason = None
            if confidence < 0.7:
                reason = f"Low confidence score: {confidence:.2f}"
            elif hallucination_check.is_hallucination:
                reason = f"Potential hallucination detected: {hallucination_check.reason}"

            return QACheckResult(
                response=response,
                confidence=confidence,
                hallucination_check=hallucination_check,
                confidence_level=conf_level,
                needs_review=needs_review,
                reason_for_review=reason
            )

        except Exception as e:
            logger.error(f"Error checking response: {e}")
            # Default to escalate on error
            return QACheckResult(
                response=response,
                confidence=0.0,
                hallucination_check=HallucinationCheck(
                    is_hallucination=True,
                    score=1.0,
                    reason="QA check failed"
                ),
                confidence_level=ConfidenceLevel.LOW,
                needs_review=True,
                reason_for_review="QA check encountered an error"
            )

    def _classify_confidence(self, confidence: float) -> ConfidenceLevel:
        """Classify confidence into buckets."""
        if confidence >= 0.8:
            return ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    def _check_hallucinations(self, response: str, sources: List[str]) -> HallucinationCheck:
        """
        Check if response contains hallucinations.

        Simple approach: check if key claims from response appear in sources.
        """
        try:
            if not sources:
                return HallucinationCheck(
                    is_hallucination=True,
                    score=0.9,
                    reason="No sources provided"
                )

            # Combine sources into single text
            sources_text = " ".join(sources).lower()
            response_lower = response.lower()

            # Extract key phrases from response (naive approach: split by sentences)
            sentences = [s.strip() for s in response.split('.') if s.strip()]

            unmatched = []
            matched = []

            for sentence in sentences:
                # Very simple matching: check if significant words from sentence appear in sources
                words = [w for w in sentence.split() if len(w) > 4]  # Filter short words
                if not words:
                    continue

                # Check how many key words appear in sources
                matches = sum(1 for w in words if w.lower() in sources_text)
                match_ratio = matches / len(words) if words else 0

                if match_ratio < 0.3:  # Less than 30% of key words matched
                    unmatched.append(sentence[:100])
                else:
                    matched.append(sentence[:100])

            # Calculate hallucination score
            if not unmatched:
                score = 0.0  # No unmatched claims
            else:
                score = min(len(unmatched) / (len(unmatched) + len(matched) + 1), 1.0)

            is_hallucination = score > 0.3  # > 30% unmatched = hallucination

            return HallucinationCheck(
                is_hallucination=is_hallucination,
                score=score,
                reason=f"{len(unmatched)} unmatched claims found" if unmatched else "Response matches sources",
                matched_sources=matched[:3],
                unmatched_claims=unmatched[:3]
            )

        except Exception as e:
            logger.error(f"Error checking hallucinations: {e}")
            return HallucinationCheck(
                is_hallucination=True,
                score=0.5,
                reason=f"Hallucination check error: {str(e)}"
            )

    async def escalate_to_review(
        self,
        session_id: str,
        patient_id: str,
        user_input: str,
        response: str,
        confidence: float,
        hallucination_score: float
    ) -> str:
        """
        Escalate response to human review queue.

        Returns:
            review_id
        """
        try:
            review_id = f"rev_{uuid.uuid4().hex[:12]}"

            review_item = {
                "review_id": review_id,
                "session_id": session_id,
                "patient_id": patient_id,
                "user_input": user_input,
                "llm_response": response,
                "confidence": confidence,
                "hallucination_score": hallucination_score,
                "status": ReviewStatus.PENDING.value,
                "created_at": datetime.utcnow()
            }

            self.review_queue.insert_one(review_item)
            logger.info(f"Escalated to review: {review_id}")
            return review_id

        except Exception as e:
            logger.error(f"Error escalating to review: {e}")
            raise

    async def log_interaction(
        self,
        session_id: str,
        patient_id: str,
        turn_count: int,
        user_input: str,
        llm_response: str,
        confidence: float,
        hallucination_score: float,
        was_reviewed: bool = False,
        review_action: Optional[str] = None
    ) -> str:
        """
        Log interaction for audit trail.

        Returns:
            audit_id
        """
        try:
            audit_id = f"audit_{uuid.uuid4().hex[:12]}"

            log_entry = {
                "audit_id": audit_id,
                "session_id": session_id,
                "patient_id": patient_id,
                "turn_count": turn_count,
                "user_input": user_input,
                "llm_response": llm_response,
                "confidence": confidence,
                "hallucination_score": hallucination_score,
                "was_reviewed": was_reviewed,
                "review_action": review_action,
                "timestamp": datetime.utcnow()
            }

            self.audit_logs.insert_one(log_entry)
            return audit_id

        except Exception as e:
            logger.error(f"Error logging interaction: {e}")
            raise

    def health_check(self) -> bool:
        """Check MongoDB connection."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
