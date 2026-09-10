from sqlalchemy import Text, String
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.models.employee import Base

EMBEDDING_DIMESNION = 2048

class DocumentChunk(Base):
  __tablename__ = "document_chunks"

  id: Mapped[int] = mapped_column(
    primary_key = True
  )

  content: Mapped[str] = mapped_column(
    Text,
    nullable=False
  )

  embedding = mapped_column(
    Vector(EMBEDDING_DIMESNION),
    nullable=False
  )

  source: Mapped[str] = mapped_column(
    String(255),
    nullable=False
  )

  document_type: Mapped[str | None] = mapped_column(
    String(100)
  )

  department: Mapped[str | None] = mapped_column(
    String(100)
  )

  section: Mapped[str|None] = mapped_column(
    String(255)
  )

  chunk_index: Mapped[int] = mapped_column(
    nullable=False
  )