import logging
from datetime import datetime
from typing import List, Optional
from pymongo import MongoClient

from .models import ReviewQueueItem, ReviewStatus, ReviewAction

logger = logging.getLogger(__name__)


class ReviewQueueService:
    """Manages the human-in-the-loop review queue."""

    def __init__(self, mongo_uri: str = "mongodb://localhost:27017", db_name: str = "dilly_dell_e"):
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.review_queue = self.db.review_queue
        self._create_indexes()
        logger.info("Review Queue Service initialized")

    def _create_indexes(self):
        """Create MongoDB indexes."""
        try:
            self.review_queue.create_index("review_id", unique=True)
            self.review_queue.create_index([("status", 1), ("created_at", -1)])
            self.review_queue.create_index("patient_id")
            self.review_queue.create_index("session_id")
            logger.info("Review queue indexes created")
        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")

    async def get_pending_reviews(self, limit: int = 50) -> List[ReviewQueueItem]:
        """
        Get pending reviews for human reviewer.

        Args:
            limit: Maximum number to return

        Returns:
            List of ReviewQueueItem objects
        """
        try:
            cursor = self.review_queue.find(
                {"status": ReviewStatus.PENDING.value}
            ).sort("created_at", -1).limit(limit)

            items = []
            for doc in cursor:
                doc.pop("_id", None)
                items.append(ReviewQueueItem(**doc))

            return items

        except Exception as e:
            logger.error(f"Error getting pending reviews: {e}")
            return []

    async def get_review(self, review_id: str) -> Optional[ReviewQueueItem]:
        """Get a specific review item."""
        try:
            doc = self.review_queue.find_one({"review_id": review_id})
            if not doc:
                return None

            doc.pop("_id", None)
            return ReviewQueueItem(**doc)

        except Exception as e:
            logger.error(f"Error getting review {review_id}: {e}")
            return None

    async def approve_review(
        self,
        review_id: str,
        reviewer_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Approve a review (accept LLM response as-is).

        Args:
            review_id: Review ID
            reviewer_id: ID of reviewer
            notes: Optional reviewer notes

        Returns:
            Success boolean
        """
        try:
            result = self.review_queue.update_one(
                {"review_id": review_id},
                {
                    "$set": {
                        "status": ReviewStatus.APPROVED.value,
                        "reviewer_id": reviewer_id,
                        "reviewer_notes": notes,
                        "reviewed_at": datetime.utcnow()
                    }
                }
            )

            logger.info(f"Approved review {review_id}")
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error approving review: {e}")
            return False

    async def reject_review(
        self,
        review_id: str,
        reviewer_id: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Reject a review (reject LLM response).

        Args:
            review_id: Review ID
            reviewer_id: ID of reviewer
            notes: Reason for rejection

        Returns:
            Success boolean
        """
        try:
            result = self.review_queue.update_one(
                {"review_id": review_id},
                {
                    "$set": {
                        "status": ReviewStatus.REJECTED.value,
                        "reviewer_id": reviewer_id,
                        "reviewer_notes": notes,
                        "reviewed_at": datetime.utcnow()
                    }
                }
            )

            logger.info(f"Rejected review {review_id}")
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error rejecting review: {e}")
            return False

    async def modify_and_approve(
        self,
        review_id: str,
        reviewer_id: str,
        approved_response: str,
        notes: Optional[str] = None
    ) -> bool:
        """
        Modify and approve a review (reject LLM response, provide corrected one).

        Args:
            review_id: Review ID
            reviewer_id: ID of reviewer
            approved_response: Corrected response
            notes: Optional notes on what was changed

        Returns:
            Success boolean
        """
        try:
            result = self.review_queue.update_one(
                {"review_id": review_id},
                {
                    "$set": {
                        "status": ReviewStatus.MODIFIED.value,
                        "reviewer_id": reviewer_id,
                        "approved_response": approved_response,
                        "reviewer_notes": notes,
                        "reviewed_at": datetime.utcnow()
                    }
                }
            )

            logger.info(f"Modified and approved review {review_id}")
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error modifying review: {e}")
            return False

    async def get_review_stats(self) -> dict:
        """Get statistics on review queue."""
        try:
            total = self.review_queue.count_documents({})
            pending = self.review_queue.count_documents({"status": ReviewStatus.PENDING.value})
            approved = self.review_queue.count_documents({"status": ReviewStatus.APPROVED.value})
            rejected = self.review_queue.count_documents({"status": ReviewStatus.REJECTED.value})
            modified = self.review_queue.count_documents({"status": ReviewStatus.MODIFIED.value})

            return {
                "total": total,
                "pending": pending,
                "approved": approved,
                "rejected": rejected,
                "modified": modified
            }

        except Exception as e:
            logger.error(f"Error getting review stats: {e}")
            return {}

    def health_check(self) -> bool:
        """Check MongoDB connection."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
