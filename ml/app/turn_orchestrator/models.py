from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class TurnType(str, Enum):
    """Type of turn in conversation."""
    USER = "user"
    ASSISTANT = "assistant"


class Turn(BaseModel):
    """Single turn in a conversation."""
    type: TurnType
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: Optional[float] = None  # For assistant responses


class Session(BaseModel):
    """Conversation session between user and voice assistant."""
    session_id: str = Field(..., description="Unique session ID")
    patient_id: str = Field(..., description="Patient ID from profiles")

    # Conversation history
    turns: List[Turn] = Field(default_factory=list)

    # Context
    patient_context: Optional[Dict[str, Any]] = None  # Cached patient profile

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    status: str = "active"  # active, paused, closed

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "sess_abc123",
                "patient_id": "pat_001",
                "turns": [
                    {
                        "type": "user",
                        "content": "I have a headache",
                        "timestamp": "2026-06-18T12:00:00Z"
                    },
                    {
                        "type": "assistant",
                        "content": "I understand. Have you taken any medication?",
                        "confidence": 0.95,
                        "timestamp": "2026-06-18T12:00:01Z"
                    }
                ],
                "patient_context": {
                    "name": "John Doe",
                    "age": 75,
                    "problem_classes": ["Dementia", "Hypertension"]
                },
                "created_at": "2026-06-18T12:00:00Z",
                "last_activity": "2026-06-18T12:00:01Z",
                "status": "active"
            }
        }


class TurnRequest(BaseModel):
    """Request to process a turn."""
    session_id: str
    patient_id: str
    user_input: str


class TurnResponse(BaseModel):
    """Response from processing a turn."""
    session_id: str
    user_input: str
    assistant_response: str
    confidence: float
    retrieved_sources: Optional[List[str]] = None
    turn_count: int
