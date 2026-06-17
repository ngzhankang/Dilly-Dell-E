from ..llm.base import LLMClient
from .retriever import Retriever

SYSTEM_PROMPT = (
    "You are a care navigator helping seniors and caregivers in Singapore find community care resources. "
    "Answer in the same language as the user — English, Mandarin, Malay, Tamil, or local dialect (Singlish, Hokkien, Cantonese). "
    "Be concise, warm, and practical. When you mention a service, include its name and contact if available."
)


class RAGPipeline:
    def __init__(self, retriever: Retriever, llm: LLMClient):
        self.retriever = retriever
        self.llm = llm

    async def query(self, message: str) -> dict:
        sources = self.retriever.retrieve(message)

        context = "\n\n".join(
            f"[{s['title']}]\n{s['content']}" for s in sources
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Relevant care resources:\n{context}\n\nUser question: {message}",
            },
        ]

        answer = await self.llm.chat(messages)
        return {
            "answer": answer,
            "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
        }
