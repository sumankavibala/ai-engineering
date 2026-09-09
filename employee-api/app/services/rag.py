import logging
import re
import time
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.client import create_embedding, client
from app.ai.logging_utils import log_token_usage
from app.repositories.document import DocumentRepository

logger = logging.getLogger(__name__)


def split_sentences(text: str) -> list[str]:
    return re.split(r"(?<=[.!?])\s+", text.strip())


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
        # 1. Embed question and 2. Retrieve relevant chunks
        retrieval_start = time.perf_counter()
        query_embedding = create_embedding(question)
        results = await self.repository.search(query_embedding, top_k, department)
        rag_retrieval_latency = time.perf_counter() - retrieval_start

        logger.info(
            "rag_retrieval",
            extra={"rag_retrieval_latency": rag_retrieval_latency, "latency_seconds": rag_retrieval_latency}
        )

        relevant_results = [
            (chunk, distance)
            for chunk, distance in results
            if distance <= SIMILARITY_THRESHOLD
        ]

        if not relevant_results:
            return {
                "answer": (
                    "I don't know based on the provided warehouse documentation."
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
        start = time.perf_counter()

        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
            )
            raw_answer = response.choices[0].message.content or ""
            if getattr(response, "usage", None):
                log_token_usage(response.usage)
        except Exception:
            response = client.responses.create(model="openai/gpt-oss-120b", input=prompt)
            raw_answer = getattr(response, "output_text", "") or ""
            if getattr(response, "usage", None):
                log_token_usage(response.usage)

        elapsed = time.perf_counter() - start

        logger.info(
            "llm_call",
            extra={
                "llm_latency": elapsed,
                "latency_seconds": elapsed
            }
        )
        clean_answer = re.sub(r"<think>.*?</think>", "", raw_answer, flags=re.DOTALL).strip()

        return {
            "answer": clean_answer,
            "sources": [
                {"chunk_id": chunk.id, "source": chunk.source, "distance": distance}
                for chunk, distance in relevant_results
            ],
        }

    async def ask_stream(self, question: str, top_k: int = 5, department: str | None = None):
        SIMILARITY_THRESHOLD = 0.35
        retrieval_start = time.perf_counter()
        query_embedding = create_embedding(question)
        results = await self.repository.search(query_embedding, top_k, department)
        rag_retrieval_latency = time.perf_counter() - retrieval_start

        logger.info(
            "rag_retrieval",
            extra={"rag_retrieval_latency": rag_retrieval_latency, "latency_seconds": rag_retrieval_latency}
        )

        relevant_results = [
            (chunk, distance)
            for chunk, distance in results
            if distance <= SIMILARITY_THRESHOLD
        ]

        if not relevant_results:
            yield "I don't know based on the provided warehouse documentation."
            return

        context_parts = []
        for chunk, distance in relevant_results:
            context_parts.append(f"""
          Source: {chunk.source}
          Chunk ID: {chunk.id}
          distance: {distance}

          {chunk.content}
          """)

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

        start = time.perf_counter()
        stream_response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            stream_options={"include_usage": True},
        )

        in_think_block = False
        buffer = ""

        for chunk in stream_response:
            if getattr(chunk, "usage", None):
                log_token_usage(chunk.usage)
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta.content or ""
            if not delta:
                continue

            buffer += delta

            while buffer:
                if not in_think_block:
                    think_start = buffer.find("<think>")
                    if think_start != -1:
                        if think_start > 0:
                            yield buffer[:think_start]
                        buffer = buffer[think_start + 7 :]
                        in_think_block = True
                    else:
                        if any("<think>"[:i] == buffer[-i:] for i in range(1, len("<think>"))):
                            break
                        yield buffer
                        buffer = ""
                else:
                    think_end = buffer.find("</think>")
                    if think_end != -1:
                        buffer = buffer[think_end + 8 :]
                        in_think_block = False
                    else:
                        buffer = ""
                        break

        if buffer and not in_think_block:
            yield buffer

        elapsed = time.perf_counter() - start
        logger.info("llm_call", extra={"llm_latency": elapsed, "latency_seconds": elapsed})

