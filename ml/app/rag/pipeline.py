from ..llm.base import LLMClient
from .retriever import Retriever
import json

SYSTEM_PROMPT = (
    # "You are a care navigator helping seniors and caregivers in Singapore find community care resources. "
    # "Answer in the same language as the user — English, Mandarin, Malay, Tamil, or local dialect (Singlish, Hokkien, Cantonese). "
    # "Be concise, warm, and practical. When you mention a service, include its name and contact if available."
    "You are a care navigator for seniors in Singapore. "
      "Respond in the user's language. "
      "\n\nIMPORTANT: Always respond in this JSON format:\n"
      "{\n"
      '  "answer": "Your care navigation response...",\n'
      '  "sentiment": "worried"|"confused"|"neutral"|"happy",\n'
      '  "confidence": 0.0 to 1.0\n'
      "}\n"
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
        # return {
        #     "answer": answer,
        #     "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
        # }
        try:
            response_json = json.loads(answer)
            return {
                "answer": response_json.get("answer", answer),
                "sentiment": response_json.get("sentiment", "neutral"),
                "confidence": response_json.get("confidence", 0.0),
                "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
            }
        except json.JSONDecodeError:
            # If the LLM response is not valid JSON, return the raw answer with default sentiment and confidence
            return {
                "answer": answer,
                "sentiment": "neutral",
                "confidence": 0.0,
                "sources": [{"title": s["title"], "url": s["url"]} for s in sources],
            }