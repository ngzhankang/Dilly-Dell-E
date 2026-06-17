import os
import logging
import httpx
from ..llm.ollama_client import OllamaClient
from ..llm.api_client import AIAPIClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a compassionate care navigator helping seniors and caregivers in Singapore "
    "find community care resources and social services. Respond with empathy, clarity, "
    "and practical guidance. Keep responses concise (2-4 sentences). "
    "Answer in the same language as the user. "
    "Do not mention any organisation or product names. "
    "If the input contains placeholder tokens like [PERSON_1] or [NRIC_1], treat them as real values."
)

async def _is_ollama_reachable(base_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as c:
            r = await c.get(f"{base_url.rstrip('/')}/api/tags")
            return r.status_code == 200
    except Exception:
        return False

async def call_llm(text: str, system_prompt_addon: str = "") -> str:
    system = SYSTEM_PROMPT + system_prompt_addon
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": text},
    ]

    ollama_url = os.environ.get("OLLAMA_BASE_URL", "")
    if ollama_url and await _is_ollama_reachable(ollama_url):
        client = OllamaClient(
            base_url=ollama_url,
            model=os.environ.get("OLLAMA_MODEL", "aisingapore/llama3.1-8b-cpt-sea-lionv3-instruct"),
        )
        try:
            return await client.chat(messages)
        except Exception as e:
            logger.warning("Ollama call failed (%s), trying API fallback", e)

    api_key = os.environ.get("LLM_API_KEY", "")
    api_base = os.environ.get("LLM_API_BASE_URL", "")
    if api_key and api_base:
        client = AIAPIClient(
            base_url=api_base,
            api_key=api_key,
            model=os.environ.get("LLM_MODEL", "sea-lion-v3-instruct"),
        )
        return await client.chat(messages)

    raise RuntimeError("No LLM available: OLLAMA_BASE_URL unreachable and LLM_API_KEY not set")
