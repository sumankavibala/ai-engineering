import logging
import re
from sqlalchemy.ext.asyncio import AsyncSession
from app.ai.client import create_embedding, client
from app.ai.logging_utils import log_token_usage
from app.ai.retry import call_with_retry
from app.ai.timer import Timer
from app.ai.telemetry import TelemetryMetrics
from app.ai.cache import policy_cache
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


def rerank_chunks(query: str, results: list, max_keep: int = 5) -> list:
    """Rerank retrieved chunks by combined similarity distance and query term overlap score.
    Returns top 3 to 5 highest quality chunks.
    """
    if not results:
        return []

    query_words = set(re.findall(r"\w+", query.lower()))
    scored_results = []

    for chunk, distance in results:
        chunk_words = set(re.findall(r"\w+", chunk.content.lower()))
        overlap_score = len(query_words.intersection(chunk_words)) / max(len(query_words), 1)
        # Higher relevance score = lower distance + high term overlap
        combined_score = (1.0 - distance) + (overlap_score * 0.5)
        scored_results.append((combined_score, chunk, distance))

    scored_results.sort(key=lambda x: x[0], reverse=True)
    top_results = [(chunk, dist) for score, chunk, dist in scored_results[:max_keep]]
    return top_results


class RAGService:
    def __init__(self, db: AsyncSession):
        self.repository = DocumentRepository(db)

    async def search_warehouse_policy(self, query: str):
        """Search warehouse policies and procedures."""
        return await self.ask(question=query)

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
        policy_cache.clear()
        return {"chunks_created": len(chunks)}

    async def ask(
        self,
        question: str,
        top_k: int = 5,
        department: str | None = None,
        telemetry: TelemetryMetrics | None = None,
    ):
        cached_res = policy_cache.get(question, department)
        if cached_res:
            logger.info("policy_cache_hit", extra={"question": question})
            return cached_res

        SIMILARITY_THRESHOLD = 0.35
        # Retrieve candidate chunks (e.g. 10) then rerank to top 3-5 chunks
        candidate_k = max(top_k, 10)
        with Timer() as timer:
            query_embedding = create_embedding(question)
            results = await self.repository.search(query_embedding, candidate_k, department)

        if telemetry:
            telemetry.add_retrieval_call(timer.elapsed_ms)

        logger.info(
            "rag_retrieval",
            extra={"rag_retrieval_latency": timer.elapsed_ms / 1000.0, "latency_seconds": timer.elapsed_ms / 1000.0},
        )

        relevant_results = [
            (chunk, distance) for chunk, distance in results if distance <= SIMILARITY_THRESHOLD
        ]

        # Rerank and select top 3 to 5 chunks
        reranked_results = rerank_chunks(question, relevant_results, max_keep=min(top_k, 5))

        if not reranked_results:
            no_info_res = {
                "answer": "I don't know based on the provided warehouse documentation.",
                "sources": [],
            }
            policy_cache.set(question, no_info_res, department)
            return no_info_res

        context_parts = []
        for chunk, distance in reranked_results:
            context_parts.append(
                f"Source: {chunk.source}\nChunk ID: {chunk.id}\ndistance: {distance}\n\n{chunk.content}"
            )

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

        with Timer() as llm_timer:
            try:
                response = call_with_retry(
                    lambda: client.chat.completions.create(
                        model="openai/gpt-oss-120b",
                        messages=[{"role": "user", "content": prompt}],
                    )
                )
                raw_answer = response.choices[0].message.content or ""
                usage = getattr(response, "usage", None)
            except Exception:
                response = call_with_retry(
                    lambda: client.responses.create(model="openai/gpt-oss-120b", input=prompt)
                )
                raw_answer = getattr(response, "output_text", "") or ""
                usage = getattr(response, "usage", None)

        if usage:
            log_token_usage(usage)
        if telemetry:
            telemetry.add_llm_call("openai/gpt-oss-120b", usage.__dict__ if hasattr(usage, "__dict__") else None, llm_timer.elapsed_ms)

        logger.info("llm_call", extra={"llm_latency": llm_timer.elapsed_ms / 1000.0, "latency_seconds": llm_timer.elapsed_ms / 1000.0})
        clean_answer = re.sub(r"<think>.*?</think>", "", raw_answer, flags=re.DOTALL).strip()

        result_payload = {
            "answer": clean_answer,
            "sources": [
                {"chunk_id": chunk.id, "source": chunk.source, "distance": distance}
                for chunk, distance in reranked_results
            ],
        }

        policy_cache.set(question, result_payload, department)
        return result_payload

    async def ask_stream(
        self,
        question: str,
        top_k: int = 5,
        department: str | None = None,
        telemetry: TelemetryMetrics | None = None,
    ):
        SIMILARITY_THRESHOLD = 0.35
        candidate_k = max(top_k, 10)
        with Timer() as timer:
            query_embedding = create_embedding(question)
            results = await self.repository.search(query_embedding, candidate_k, department)

        if telemetry:
            telemetry.add_retrieval_call(timer.elapsed_ms)

        logger.info(
            "rag_retrieval",
            extra={"rag_retrieval_latency": timer.elapsed_ms / 1000.0, "latency_seconds": timer.elapsed_ms / 1000.0},
        )

        relevant_results = [
            (chunk, distance) for chunk, distance in results if distance <= SIMILARITY_THRESHOLD
        ]

        reranked_results = rerank_chunks(question, relevant_results, max_keep=min(top_k, 5))

        if not reranked_results:
            yield "I don't know based on the provided warehouse documentation."
            return

        context_parts = []
        for chunk, distance in reranked_results:
            context_parts.append(
                f"Source: {chunk.source}\nChunk ID: {chunk.id}\ndistance: {distance}\n\n{chunk.content}"
            )

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

        with Timer() as llm_timer:
            stream_response = call_with_retry(
                lambda: client.chat.completions.create(
                    model="openai/gpt-oss-120b",
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    stream_options={"include_usage": True},
                )
            )

            in_think_block = False
            buffer = ""

            for chunk in stream_response:
                usage = getattr(chunk, "usage", None)
                if usage:
                    log_token_usage(usage)
                    if telemetry:
                        telemetry.add_llm_call("openai/gpt-oss-120b", usage.__dict__ if hasattr(usage, "__dict__") else None, llm_timer.elapsed_ms)
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

        logger.info("llm_call", extra={"llm_latency": llm_timer.elapsed_ms / 1000.0, "latency_seconds": llm_timer.elapsed_ms / 1000.0})
