import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from .schemas import PredictRequest, PredictResponse
from .model import load_model, run_inference

ml_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_path = os.getenv("MODEL_PATH", "/app/models/model.onnx")
    ml_state["model"] = load_model(model_path)
    yield
    ml_state.clear()


app = FastAPI(title="Dilly-Dell-E ML Service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "model_loaded": ml_state.get("model") is not None}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    result = run_inference(ml_state["model"], request)
    return PredictResponse(result=result)
