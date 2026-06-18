import logging
from typing import Optional, Dict, Any

from .models import TurnType, TurnResponse
from .service import TurnOrchestratorService

logger = logging.getLogger(__name__)


class VoiceOrchestrator:
    """
    Orchestrates conversation flow between:
    - Turn Orchestrator (session management)
    - Profile Builder (patient context)
    - RAG Pipeline (response generation)
    """

    def __init__(
        self,
        turn_service: TurnOrchestratorService,
        profile_service,  # ProfileService
        rag_pipeline  # RAGPipeline
    ):
        self.turn_service = turn_service
        self.profile_service = profile_service
        self.rag_pipeline = rag_pipeline

    async def process_user_input(
        self,
        session_id: str,
        patient_id: str,
        user_input: str
    ) -> TurnResponse:
        """
        Process user input in a conversation session.

        Flow:
        1. Get/create session
        2. Fetch patient context from Profile Builder
        3. Send to RAG pipeline with context
        4. Store conversation in session
        5. Return response

        Args:
            session_id: Existing session or create new
            patient_id: Patient ID
            user_input: User's spoken/typed input

        Returns:
            TurnResponse with assistant's response
        """
        try:
            # Get or create session
            session = await self.turn_service.get_session(session_id)
            if not session:
                logger.info(f"Creating new session {session_id}")
                session_id = await self.turn_service.create_session(patient_id)
                session = await self.turn_service.get_session(session_id)

            # Fetch patient context if not cached
            if not session.patient_context:
                logger.info(f"Fetching patient context for {patient_id}")
                profile = await self.profile_service.get_profile(patient_id)
                if profile:
                    session.patient_context = profile.dict()

            # Add user turn to history
            await self.turn_service.add_turn(
                session_id=session_id,
                turn_type=TurnType.USER,
                content=user_input
            )

            # Build context prompt for RAG
            context_prompt = self._build_context_prompt(session, user_input)

            # Query RAG pipeline with context
            rag_result = await self.rag_pipeline.query(context_prompt)

            assistant_response = rag_result.get("answer", "")
            confidence = rag_result.get("confidence", 0.7)
            sources = rag_result.get("sources", [])

            # Add assistant turn to history
            await self.turn_service.add_turn(
                session_id=session_id,
                turn_type=TurnType.ASSISTANT,
                content=assistant_response,
                confidence=confidence
            )

            logger.info(f"Processed turn in session {session_id}, confidence: {confidence}")

            return TurnResponse(
                session_id=session_id,
                user_input=user_input,
                assistant_response=assistant_response,
                confidence=confidence,
                retrieved_sources=sources,
                turn_count=len(session.turns) + 2  # user + assistant just added
            )

        except Exception as e:
            logger.error(f"Error processing user input: {e}")
            raise

    def _build_context_prompt(self, session, user_input: str) -> str:
        """
        Build an augmented prompt with patient context.

        This helps the RAG pipeline give personalized responses.
        """
        prompt_parts = []

        # Patient context
        if session.patient_context:
            context = session.patient_context
            patient_info = f"Patient: {context.get('name')}, Age: {context.get('age')}"
            if context.get("problem_classes"):
                patient_info += f", Conditions: {', '.join(context['problem_classes'])}"
            prompt_parts.append(patient_info)

        # Recent conversation history (last 2 turns for context)
        recent_turns = session.turns[-4:] if len(session.turns) >= 2 else session.turns
        if recent_turns:
            history_lines = []
            for turn in recent_turns:
                prefix = "User" if turn.type == "user" else "Assistant"
                history_lines.append(f"{prefix}: {turn.content}")
            if history_lines:
                prompt_parts.append("Recent conversation:\n" + "\n".join(history_lines))

        # Current user input
        prompt_parts.append(f"User: {user_input}")

        return "\n".join(prompt_parts)

    async def start_session(self, patient_id: str) -> str:
        """Start a new conversation session."""
        return await self.turn_service.create_session(patient_id)

    async def end_session(self, session_id: str) -> bool:
        """End a conversation session."""
        return await self.turn_service.close_session(session_id)

    def health_check(self) -> Dict[str, bool]:
        """Check health of all dependent services."""
        return {
            "turn_service": self.turn_service.health_check(),
            "profile_service": self.profile_service.health_check(),
        }
