import logging
import os
import tempfile
from contextlib import asynccontextmanager

import chromadb
import whisper
from fastapi import FastAPI, File, HTTPException, UploadFile
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
    whisper_model = whisper.load_model("base")

    chroma = chromadb.Client()
    collection = chroma.get_or_create_collection("care_resources")
    load_knowledge_base(collection, embedder)

    ollama = OllamaClient(
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.environ.get("OLLAMA_MODEL", "aisingapore/Llama-SEA-LION-v3.5-8B-R"),
    )

    api_key = os.environ.get("LLM_API_KEY")
    api_base = os.environ.get("LLM_API_BASE_URL")
    if api_key and api_base:
        api = AIAPIClient(
            base_url=api_base,
            api_key=api_key,
            model=os.environ.get("LLM_MODEL", "Llama-SEA-LION-v3.5-8B-R"),
        )
        llm = FallbackLLMClient(primary=api, fallback=ollama)
    else:
        logging.warning("LLM_API_KEY not set — using Ollama only (no fallback)")
        llm = ollama

    retriever = Retriever(collection=collection, embedder=embedder)
    state["pipeline"] = RAGPipeline(retriever=retriever, llm=llm)
    state["whisper_model"] = whisper_model
    yield
    state.clear()


app = FastAPI(title="Dilly-Dell-E ML Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "pipeline_ready": "pipeline" in state}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Query with text message"""
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    result = await state["pipeline"].query(request.message)
    return QueryResponse(**result)


@app.post("/query-audio", response_model=QueryResponse)
async def query_audio(file: UploadFile = File(...)):
    """Query with audio file (mp3, wav, m4a, ogg, flac, etc.)"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if not ext:
        raise HTTPException(status_code=400, detail="File must have an extension")

    tmp_path = None
    try:
        # Write uploaded file to a temp location
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            contents = await file.read()
            if not contents:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            tmp.write(contents)
            tmp_path = tmp.name

        # Transcribe audio to text
        logging.info("Transcribing audio file: %s", file.filename)
        transcription = state["whisper_model"].transcribe(tmp_path, language="en")
        message = transcription.get("text", "").strip()
        print(message,"<<<<")

        if not message:
            raise HTTPException(status_code=400, detail="Transcription resulted in empty text")

        logging.info("Transcribed text: %s", message)

        # Pass transcribed text to RAG pipeline
        result = await state["pipeline"].query(message)
        return QueryResponse(**result)

    except HTTPException:
        raise
    except Exception as exc:
        logging.error("Error processing audio: %s", exc)
        raise HTTPException(status_code=500, detail=f"Failed to process audio: {str(exc)}")
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)