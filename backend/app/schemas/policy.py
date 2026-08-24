from pydantic import BaseModel
from typing import Optional

class PolicySearchQuery(BaseModel):
    query: str
    limit: Optional[int] = 3

class PolicyChunkOut(BaseModel):
    id: int
    content: str
    chunk_index: int
    document_title: str
    filename: str
    score: float
