import logging
from .base import LLMClient

logger = logging.getLogger(__name__)


class FallbackLLMClient(LLMClient):
    def __init__(self, primary: LLMClient, fallback: LLMClient):
        self.primary = primary
        self.fallback = fallback

    async def chat(self, messages: list[dict]) -> str:
        try:
            return await self.primary.chat(messages)
        except Exception as exc:
            logger.warning("Primary LLM failed (%s), falling back to Ollama", exc)
            return await self.fallback.chat(messages)
