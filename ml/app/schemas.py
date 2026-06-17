from typing import Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    message: str


class Source(BaseModel):
    title: str
    url: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
