from email.mime import message
import logging
import os
import tempfile
from contextlib import asynccontextmanager

import chromadb
import whisper
from fastapi import FastAPI, File, HTTPException, UploadFile
from sentence_transformers import SentenceTransformer
# from transformers import pipeline

from .llm.api_client import AIAPIClient
from .llm.fallback_client import FallbackLLMClient
from .llm.ollama_client import OllamaClient
from .model import predict as run_predict
from .rag.loader import load_knowledge_base
from .rag.pipeline import RAGPipeline
from .rag.retriever import Retriever
from .adapters.mapper import AdapterMapper
from .schemas import PredictRequest, PredictResponse, QueryRequest, QueryResponse

logging.basicConfig(level=logging.INFO)
state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    whisper_model = whisper.load_model("base")

    # sentiment_analyzer = pipeline("sentiment-analysis", model="distilbert-base-uncased-finetuned-sst-2-english")
    # state["sentiment_analyzer"] = sentiment_analyzer

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
    state["adapter_mapper"] = AdapterMapper(llm_client=llm)
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
    # sentiment = state["sentiment_analyzer"](request.message)[0]
    # result["sentiment"] = sentiment
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
        print(message, "message!")

        if not message:
            raise HTTPException(status_code=400, detail="Transcription resulted in empty text")

        logging.info("Transcribed text: %s", message)

        # Pass transcribed text to RAG pipeline
        # sentiment = state["sentiment_analyzer"](message)[0]
        result = await state["pipeline"].query(message)
        # result["sentiment"] = sentiment
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


@app.post("/adapter/import")
async def import_agency_form(
    file: UploadFile = File(...),
    agency_name: str = "",
) -> dict:
    """Import and normalize agency form data using LLM field mapping."""
    if not agency_name or not agency_name.strip():
        raise HTTPException(status_code=400, detail="agency_name required")

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    tmp_path = None
    try:
        # Get file extension to determine format
        ext = file.filename.rsplit(".", 1)[-1].lower()
        if not ext:
            raise HTTPException(status_code=400, detail="File must have an extension")

        if ext not in ["csv", "xlsx", "xls", "json", "pdf"]:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {ext}. Supported: csv, xlsx, xls, json, pdf",
            )

        # Write uploaded file to temp location
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            contents = await file.read()
            if not contents:
                raise HTTPException(status_code=400, detail="Uploaded file is empty")
            tmp.write(contents)
            tmp_path = tmp.name

        # Use adapter mapper to import and normalize
        mapper = state["adapter_mapper"]
        result = await mapper.import_agency_data(
            file_path=tmp_path,
            agency_name=agency_name,
            file_format=ext,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Import failed"))

        return {
            "success": True,
            "agency": result["agency"],
            "records_imported": result["records_normalized"],
            "mapping_confidence": result["mapping_confidence"],
            "unmapped_fields": result.get("unmapped_fields", []),
            "sample_record": result["records"][0] if result["records"] else None,
            "records": result["records"],
            "mapping_metadata": result.get("mapping_metadata", {}),
        }

    except HTTPException:
        raise
    except Exception as exc:
        logging.error("Error importing agency data: %s", exc)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(exc)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest) -> PredictResponse:
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="text cannot be empty")
    result = await run_predict(request.text, request.session_id)
    return PredictResponse(**result)