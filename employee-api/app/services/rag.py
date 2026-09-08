import re


def split_sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", text.strip())


# def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:

# chunks = []
# start = 0
# while start < len(text):
#     end = start + chunk_size

#     chunks.append(text[start:end])

#     start += chunk_size - overlap

# return chunks


def chunk_text(
    text: str, max_chars: int = 800, overlap_sentences: int = 1
) -> list[str]:

    sentences = split_sentences(text)

    chunks = []
    current = []

    for sentence in sentences:

        candidate = " ".join(current + [sentence])

        if len(candidate) <= max_chars or not current:
            current.append(sentence)

        else:
            chunks.append(" ".join(current))

            overlap = current[-overlap_sentences:]

            current = overlap + [sentence]

    if current:
        chunks.append(" ".join(current))

    return chunks


from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.client import create_embedding, client
from app.repositories.document import DocumentRepository


class RAGService:
    def __init__(self, db: AsyncSession):
        self.repository = DocumentRepository(db)

    async def ingest_document(
        self,
        text: str,
        source: str,
        document_type: str | None = None,
        department: str | None = None,
    ):
        chunks = chunk_text(text)

        for chunk in chunks:
            embedding = create_embedding(chunk)

            await self.repository.create(
                content=chunk,
                embedding=embedding,
                source=source,
                document_type=document_type,
                department=department,
            )

        await self.repository.db.commit()
        return {"chunks_created": len(chunks)}

    async def ask(self, question: str, top_k: int = 5, department: str | None = None):

        SIMILARITY_THRESHOLD = 0.35
        # 1. Embed question
        query_embedding = create_embedding(question)

        # 2. Retrieve relevant chunks
        results = await self.repository.search(query_embedding, top_k, department)

        relevant_results = [
            (chunk, distance)
            for chunk, distance in results
            if distance <= SIMILARITY_THRESHOLD
        ]

        if not relevant_results:
            return {
                "answer": (
                    "I don't know based on the " "provided warehouse documentation."
                ),
                "sources": [],
            }

        context_parts = []

        for chunk, distance in relevant_results:
            context_parts.append(f"""
          Source: {chunk.source}
          Chunk ID: {chunk.id}
          distance: {distance}

          {chunk.content}
          """)

        # 3. Build context
        context = "\n\n".join(context_parts)

        prompt = f"""
          You are a warehouse assistant.

          Answer the user's question using ONLY
          the provided warehouse documentation.

          Do not invent information.

          If the documentation does not contain
          the answer, say that you don't know.

          Documentation:

          {context}

          Question:

          {question}
          """

        response = client.responses.create(model="openai/gpt-oss-120b", input=prompt)

        return {
            "answer": response.output_text,
            "sources": [
                {"chunk_id": chunk.id, "source": chunk.source, "distance": distance}
                for chunk, distance in relevant_results
            ],
        }
