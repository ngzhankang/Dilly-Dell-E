from typing import Any, Optional
from pydantic import BaseModel


class PredictRequest(BaseModel):
    input: str  # Replace with your actual input fields


class PredictResponse(BaseModel):
    result: Any
    confidence: Optional[float] = None
