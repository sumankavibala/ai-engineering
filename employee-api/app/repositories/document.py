import math
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag import DocumentChunk


def compute_cosine_distance(vec1: list[float], vec2: list[float]) -> float:
    if not vec1 or not vec2:
        return 1.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if not norm1 or not norm2:
        return 1.0
    return 1.0 - (dot / (norm1 * norm2))


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        content: str,
        embedding: list[float],
        source: str | None = None,
        document_type: str | None = None,
        department: str | None = None,
        chunk_index: int = 0,
    ):
        document = DocumentChunk(
            content=content,
            embedding=embedding,
            source=source,
            document_type=document_type,
            department=department,
            chunk_index=chunk_index,
        )

        self.db.add(document)
        return document

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        department: str | None = None,
    ):
        try:
            distance = DocumentChunk.embedding.cosine_distance(
                query_embedding
            ).label("distance")
            statement = select(DocumentChunk, distance)
            if department:
                statement = statement.where(DocumentChunk.department == department)
            statement = statement.order_by(distance).limit(top_k)
            result = await self.db.execute(statement)
            return result.all()
        except Exception:
            statement = select(DocumentChunk)
            if department:
                statement = statement.where(DocumentChunk.department == department)
            result = await self.db.execute(statement)
            chunks = result.scalars().all()
            scored = []
            for chunk in chunks:
                emb = chunk.embedding
                if isinstance(emb, str):
                    import json
                    emb = json.loads(emb)
                dist = compute_cosine_distance(emb, query_embedding)
                scored.append((chunk, dist))
            scored.sort(key=lambda x: x[1])
            return scored[:top_k]

    async def get_neighbours(
        self, chunk: DocumentChunk, window: int = 1
    ):
        statement = (
            select(DocumentChunk)
            .where(
                DocumentChunk.source == chunk.source,
                DocumentChunk.chunk_index >= chunk.chunk_index - window,
                DocumentChunk.chunk_index <= chunk.chunk_index + window,
            )
            .order_by(DocumentChunk.chunk_index)
        )

        result = await self.db.execute(statement)
        return result.scalars().all()