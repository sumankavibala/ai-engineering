from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag import DocumentChunk

class DocumentRepository:
  def __init__(self, db: AsyncSession):
    self.db = db
  
  async def create(
    self,
    content: str,
    embedding: list[float],
    source: str | None = None,
    document_type: str | None = None,
    department: str | None = None
  ):

    document = DocumentChunk(
      content=content,
      embedding=embedding,
      source=source,
      document_type=document_type,
      department=department
    )

    self.db.add(document)

    return document

  async def search(
    self,
    query_embedding: list[float],
    top_k: int = 5,
    department: str | None = None
  ):
    distance = DocumentChunk.embedding.cosine_distance(
      query_embedding
    ).label("distance")

    statement = select(
        DocumentChunk,
        distance
    )

    if department:
      statement = statement.where(
        DocumentChunk.department == department
      )

    statement = (
      statement
      .order_by(distance)
      .limit(top_k)
    )

    result = await self.db.execute(statement)
    return result.all()

  async def get_neighbours(
    self, chunk: DocumentChunk, window: int = 1
  ):
    statement = (
      select(DocumentChunk)
      .where(
        DocumentChunk.source == chunk.source,
        DocumentChunk.chunk_index >= chunk.chunk_index - window,
        DocumentChunk.chunk_index <= chunk.chunk_index + window
      )
      .order_by(
        DocumentChunk.chunk_index
      )
    )

    result = await self.db.execute(statement)
    return result.scalars().all()