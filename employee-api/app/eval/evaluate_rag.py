import json
import re
from pydantic import BaseModel
from app.ai.client import client


class EvaluationResult(BaseModel):
    correct: bool
    grounded: bool
    score: int
    reason: str


def evaluate_retrieval(
    retrieved_chunks: list,
    expected_source: str | None,
    k: int = 5
) -> dict:
    top_k_chunks = retrieved_chunks[:k]
    
    if expected_source is None:
        hit = len(retrieved_chunks) == 0
        precision = 1.0 if hit else 0.0
        recall = 1.0 if hit else 0.0
        return {
            "hit": hit,
            "precision_at_k": precision,
            "recall_at_k": recall
        }
    
    relevant_retrieved = sum(1 for c in top_k_chunks if getattr(c, 'source', None) == expected_source)
    hit = relevant_retrieved > 0
    precision = relevant_retrieved / k if k > 0 else 0.0
    recall = 1.0 if hit else 0.0

    return {
        "hit": hit,
        "precision_at_k": precision,
        "recall_at_k": recall
    }



def evaluate_answer(
    question: str,
    context: str,
    expected_answer: str | None,
    actual_answer: str
) -> EvaluationResult:
    prompt = f"""
Evaluate the answer produced by a warehouse AI assistant.

Question:
{question}

Retrieved context:
{context}

Expected answer:
{expected_answer}

Actual answer:
{actual_answer}

Evaluate:

1. Is the actual answer correct?
2. Is the actual answer supported by the retrieved context?
3. Give a score from 1 to 5.
4. Explain briefly.

Return JSON with:

correct
grounded
score
reason
"""

    response = client.responses.create(
        model="openai/gpt-oss-120b",
        input=prompt,
    )

    raw_text = response.output_text or ""
    clean_text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

    try:
        data = json.loads(clean_text)
        return EvaluationResult(**data)
    except Exception:
        json_match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            return EvaluationResult(**data)
        raise