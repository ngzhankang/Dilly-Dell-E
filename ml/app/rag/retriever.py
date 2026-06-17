import chromadb
from sentence_transformers import SentenceTransformer


class Retriever:
    def __init__(self, collection: chromadb.Collection, embedder: SentenceTransformer, top_k: int = 5):
        self.collection = collection
        self.embedder = embedder
        self.top_k = top_k

    def retrieve(self, query: str) -> list[dict]:
        embedding = self.embedder.encode([query])[0].tolist()
        results = self.collection.query(query_embeddings=[embedding], n_results=self.top_k)

        sources = []
        for i in range(len(results["ids"][0])):
            sources.append({
                "title": results["metadatas"][0][i].get("title", ""),
                "url": results["metadatas"][0][i].get("url", ""),
                "content": results["documents"][0][i],
            })
        return sources
