from typing import List, Optional

from pydantic import BaseModel


class Metadata(BaseModel):
    path: str = ""
    description: str = ""


class RetrievalRecord(BaseModel):
    content: str
    title: Optional[str] = None
    source: Optional[str] = None
    type: Optional[str] = None
    score: float
    search_type: Optional[str] = None


class RetrievalResponse(BaseModel):
    records: List[RetrievalRecord]
