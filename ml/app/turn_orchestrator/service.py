import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pymongo import MongoClient

from .models import Session, Turn, TurnType, TurnResponse

logger = logging.getLogger(__name__)


class TurnOrchestratorService:
    """Manages conversation sessions and turn orchestration."""

    def __init__(self, mongo_uri: str = "mongodb://localhost:27017", db_name: str = "dilly_dell_e"):
        """Initialize with MongoDB connection."""
        self.client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        self.sessions = self.db.conversation_sessions
        self._create_indexes()
        logger.info("Turn Orchestrator initialized")

    def _create_indexes(self):
        """Create MongoDB indexes."""
        try:
            self.sessions.create_index("session_id", unique=True)
            self.sessions.create_index("patient_id")
            self.sessions.create_index("created_at")
            logger.info("Session indexes created")
        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")

    async def create_session(self, patient_id: str, patient_context: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new conversation session.

        Args:
            patient_id: Patient ID
            patient_context: Cached patient profile data

        Returns:
            session_id
        """
        try:
            session_id = f"sess_{uuid.uuid4().hex[:12]}"

            session = {
                "session_id": session_id,
                "patient_id": patient_id,
                "turns": [],
                "patient_context": patient_context or {},
                "created_at": datetime.utcnow(),
                "last_activity": datetime.utcnow(),
                "status": "active"
            }

            self.sessions.insert_one(session)
            logger.info(f"Created session {session_id} for patient {patient_id}")
            return session_id

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise

    async def add_turn(
        self,
        session_id: str,
        turn_type: TurnType,
        content: str,
        confidence: Optional[float] = None
    ) -> bool:
        """
        Add a turn to conversation history.

        Args:
            session_id: Session ID
            turn_type: "user" or "assistant"
            content: Turn content
            confidence: Confidence score (for assistant turns)

        Returns:
            Success boolean
        """
        try:
            turn = {
                "type": turn_type.value,
                "content": content,
                "timestamp": datetime.utcnow(),
                "confidence": confidence
            }

            result = self.sessions.update_one(
                {"session_id": session_id},
                {
                    "$push": {"turns": turn},
                    "$set": {"last_activity": datetime.utcnow()}
                }
            )

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error adding turn to session {session_id}: {e}")
            return False

    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        try:
            doc = self.sessions.find_one({"session_id": session_id})
            if not doc:
                return None

            doc.pop("_id", None)
            return Session(**doc)

        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None

    async def get_conversation_history(self, session_id: str, limit: int = 10) -> list:
        """Get recent turns from conversation."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return []

            # Return last N turns
            return session.turns[-limit:]

        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    async def close_session(self, session_id: str) -> bool:
        """Close a session."""
        try:
            result = self.sessions.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "status": "closed",
                        "last_activity": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error closing session: {e}")
            return False

    def health_check(self) -> bool:
        """Check MongoDB connection."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
