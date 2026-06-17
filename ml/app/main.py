import logging
import os
from contextlib import asynccontextmanager

import chromadb
from fastapi import FastAPI
from sentence_transformers import SentenceTransformer

from .llm.api_client import AIAPIClient
from .llm.fallback_client import FallbackLLMClient
from .llm.ollama_client import OllamaClient
from .rag.loader import load_knowledge_base
from .rag.pipeline import RAGPipeline
from .rag.retriever import Retriever
from .schemas import QueryRequest, QueryResponse

logging.basicConfig(level=logging.INFO)
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

    chroma = chromadb.Client()
    collection = chroma.get_or_create_collection("care_resources")
    load_knowledge_base(collection, embedder)

    ollama = OllamaClient(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.environ.get("OLLAMA_MODEL", "aisingapore/llama3.1-8b-cpt-sea-lionv3-instruct"),
    )

    api_key = os.environ.get("LLM_API_KEY")
    api_base = os.environ.get("LLM_API_BASE_URL")
    if api_key and api_base:
        api = AIAPIClient(
            base_url=api_base,
            api_key=api_key,
            model=os.environ.get("LLM_MODEL", "sea-lion-v3-instruct"),
        )
        llm = FallbackLLMClient(primary=api, fallback=ollama)
    else:
        logging.warning("LLM_API_KEY not set — using Ollama only (no fallback)")
        llm = ollama

    retriever = Retriever(collection=collection, embedder=embedder)
    state["pipeline"] = RAGPipeline(retriever=retriever, llm=llm)
    yield
    state.clear()


app = FastAPI(title="Dilly-Dell-E ML Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "pipeline_ready": "pipeline" in state}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    result = await state["pipeline"].query(request.message)
    return QueryResponse(**result)
