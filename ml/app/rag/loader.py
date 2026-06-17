import json
import logging
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"


def load_knowledge_base(collection: chromadb.Collection, embedder: SentenceTransformer) -> int:
    documents, metadatas, ids = [], [], []

    for jsonl_file in sorted(DATA_DIR.glob("*.jsonl")):
        with open(jsonl_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                doc = json.loads(line)
                documents.append(doc["content"])
                metadatas.append({"title": doc.get("title", ""), "url": doc.get("url", "")})
                ids.append(str(doc["id"]))

    if not documents:
        logger.warning("No documents found in %s — knowledge base is empty", DATA_DIR)
        return 0

    embeddings = embedder.encode(documents, show_progress_bar=False).tolist()
    collection.upsert(documents=documents, embeddings=embeddings, metadatas=metadatas, ids=ids)
    logger.info("Loaded %d documents into ChromaDB", len(documents))
    return len(documents)
