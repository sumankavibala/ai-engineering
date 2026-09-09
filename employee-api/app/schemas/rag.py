from pydantic import BaseModel


class DocumentIngestRequest(BaseModel):
    text: str
    source: str
    document_type: str | None = None
    department: str | None = None


class Source(BaseModel):
    chunk_id: int
    source: str
    distance: float


class DocumentIngestResponse(BaseModel):
    chunks_created: int


class QuestionRequest(BaseModel):
    question: str
    top_k: int = 5
    department: str | None = None
    stream: bool = False


class QuestionResponse(BaseModel):
    answer: str
    sources: list[Source]
