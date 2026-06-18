import logging
from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from .models import TurnRequest, TurnResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/voice", tags=["voice-gateway"])

# Global orchestrator instance
_orchestrator = None


def init_orchestrator(orchestrator):
    """Initialize the global orchestrator."""
    global _orchestrator
    _orchestrator = orchestrator
    logger.info("Voice Gateway orchestrator initialized")


def get_orchestrator():
    """Get the orchestrator instance."""
    if _orchestrator is None:
        raise RuntimeError("Voice Gateway orchestrator not initialized")
    return _orchestrator


class StartSessionRequest(BaseModel):
    """Request to start a new voice session."""
    patient_id: str


class StartSessionResponse(BaseModel):
    """Response when starting a session."""
    session_id: str
    patient_id: str


class VoiceInputRequest(BaseModel):
    """Voice input as text."""
    session_id: str
    patient_id: str
    text: str


@router.post("/sessions/start", response_model=StartSessionResponse)
async def start_session(request: StartSessionRequest) -> dict:
    """
    Start a new voice conversation session.

    Args:
        patient_id: Patient ID to start session with

    Returns:
        session_id: Unique session ID for this conversation
    """
    try:
        orchestrator = get_orchestrator()
        session_id = await orchestrator.start_session(request.patient_id)
        return {
            "session_id": session_id,
            "patient_id": request.patient_id
        }
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/turn", response_model=TurnResponse)
async def process_voice_turn(request: VoiceInputRequest) -> dict:
    """
    Process a voice turn (user input → assistant response).

    This is the main endpoint for voice interactions:
    1. Takes user's transcribed speech (or typed text)
    2. Fetches patient context from Profile Builder
    3. Queries RAG pipeline for response
    4. Stores conversation in session
    5. Returns response (for voice synthesis)

    Args:
        session_id: Conversation session ID
        patient_id: Patient ID
        text: User's input text (transcribed from audio)

    Returns:
        TurnResponse with assistant's response + confidence
    """
    try:
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Text cannot be empty")

        orchestrator = get_orchestrator()
        result = await orchestrator.process_user_input(
            session_id=request.session_id,
            patient_id=request.patient_id,
            user_input=request.text
        )
        return result.dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing voice turn: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sessions/{session_id}/end")
async def end_session(session_id: str) -> dict:
    """End a voice session."""
    try:
        orchestrator = get_orchestrator()
        success = await orchestrator.end_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
        return {"session_id": session_id, "status": "closed"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ending session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/ready", tags=["health"])
async def health_check() -> dict:
    """Check if voice gateway is ready."""
    try:
        orchestrator = get_orchestrator()
        health = orchestrator.health_check()
        if all(health.values()):
            return {"status": "ready", "services": health}
        else:
            raise HTTPException(status_code=503, detail="Some services unhealthy")
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=str(e))
