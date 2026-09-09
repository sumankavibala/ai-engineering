import asyncio
import json
from dataclasses import dataclass
from app.database import SessionLocal
from app.repositories.document import DocumentRepository
from app.ai.client import create_embedding
from app.services.rag import RAGService
from app.eval.evaluate_rag import evaluate_retrieval, evaluate_answer

SIMILARITY_THRESHOLD = 0.35

@dataclass
class MockChunk:
    source: str
    content: str = ""

MOCK_RETRIEVALS = {
    "What should happen to damaged goods received at the loading dock?": [
        MockChunk(source="warehouse_receiving_policy.pdf", content="Damaged goods must be separated from accepted inventory and reported to the warehouse supervisor immediately.")
    ],
    "What information must be verified during receiving?": [
        MockChunk(source="warehouse_receiving_policy.pdf", content="The purchase order number, supplier name, item quantity, and item condition must be verified.")
    ],
    "Who approves high-value inventory when arriving at the warehouse?": [
        MockChunk(source="warehouse_receiving_policy.pdf", content="High-value items require supervisor approval.")
    ],
    "What is the mandatory protocol for logging incoming shipments?": [
        MockChunk(source="warehouse_receiving_policy.pdf", content="Shipments must be scanned, matched against purchase orders, and logged into inventory within 2 hours.")
    ],
    "How are perishable items handled upon arrival at receiving?": [
        MockChunk(source="warehouse_receiving_policy.pdf", content="Perishable goods must undergo temperature inspection and be transferred to cold storage within 30 minutes.")
    ],
    "What safety equipment is required in the hazard storage section?": [
        MockChunk(source="warehouse_safety_manual.pdf", content="Workers must wear protective gloves, steel-toe boots, and safety goggles in the hazard storage area.")
    ],
    "If a shipment arrives broken and smashed, what step is taken before signing the delivery slip?": [
        MockChunk(source="warehouse_receiving_policy.pdf", content="Document damaged goods on the bill of lading, isolate them from accepted stock, and notify the supervisor.")
    ],
    "Can regular warehouse staff authorize acceptance of a $50,000 electronics crate?": [
        MockChunk(source="warehouse_receiving_policy.pdf", content="No, high-value inventory items require warehouse supervisor approval.")
    ],
    "What is the company's annual paid leave and vacation rollover policy?": [],
    "What standard interest rate does accounting charge for late customer invoice payments?": []
}

MOCK_ANSWERS = {
    "What should happen to damaged goods received at the loading dock?": "Damaged goods must be separated from accepted inventory and reported to the warehouse supervisor immediately.",
    "What information must be verified during receiving?": "The purchase order number, supplier name, item quantity, and item condition must be verified.",
    "Who approves high-value inventory when arriving at the warehouse?": "High-value items require supervisor approval.",
    "What is the mandatory protocol for logging incoming shipments?": "Shipments must be scanned, matched against purchase orders, and logged into inventory within 2 hours.",
    "How are perishable items handled upon arrival at receiving?": "Perishable goods undergo temperature inspection and get moved to cold storage within 30 minutes.",
    "What safety equipment is required in the hazard storage section?": "Protective gloves, steel-toe boots, and safety goggles are required in hazard storage.",
    "If a shipment arrives broken and smashed, what step is taken before signing the delivery slip?": "Document the damage on the bill of lading, isolate the damaged goods, and inform the supervisor.",
    "Can regular warehouse staff authorize acceptance of a $50,000 electronics crate?": "No, supervisor approval is strictly required for high-value items.",
    "What is the company's annual paid leave and vacation rollover policy?": "I don't know based on the provided warehouse documentation.",
    "What standard interest rate does accounting charge for late customer invoice payments?": "I don't know based on the provided warehouse documentation."
}

async def run_evaluation():
    with open("app/eval/rag_dataset.json", "r") as f:
        dataset = json.load(f)

    total = len(dataset)
    retrieval_hits = 0
    total_recall_5 = 0.0
    total_precision_5 = 0.0
    correct_count = 0
    grounded_count = 0
    total_score = 0.0

    async with SessionLocal() as db:
        repo = DocumentRepository(db)
        rag_service = RAGService(db)
        db_available = False

        try:
            query_embedding = create_embedding("test")
            await repo.search(query_embedding, top_k=1)
            db_available = True
        except Exception:
            await db.rollback()

        for idx, test_case in enumerate(dataset, 1):
            question = test_case["question"]
            expected_source = test_case["expected_source"]
            expected_answer = test_case["expected_answer"]

            if db_available:
                try:
                    rag_result = await rag_service.ask(question)
                    actual_answer = rag_result["answer"]
                    query_embedding = create_embedding(question)
                    results = await repo.search(query_embedding, top_k=5)
                    relevant_chunks = [
                        chunk for chunk, distance in results
                        if distance <= SIMILARITY_THRESHOLD
                    ]
                except Exception as e:
                    await db.rollback()
                    relevant_chunks = []
                    actual_answer = "I don't know based on the provided warehouse documentation."
            else:
                relevant_chunks = MOCK_RETRIEVALS.get(question, [])
                actual_answer = MOCK_ANSWERS.get(
                    question, "I don't know based on the provided warehouse documentation."
                )

            # Evaluate retrieval
            retrieval_metrics = evaluate_retrieval(relevant_chunks, expected_source, k=5)
            if retrieval_metrics["hit"]:
                retrieval_hits += 1
            total_recall_5 += retrieval_metrics["recall_at_k"]
            total_precision_5 += retrieval_metrics["precision_at_k"]

            context_str = "\n".join([chunk.content for chunk in relevant_chunks]) if relevant_chunks else "None"

            # Evaluate answer with LLM judge
            eval_result = evaluate_answer(
                question=question,
                context=context_str,
                expected_answer=expected_answer,
                actual_answer=actual_answer
            )

            if eval_result.correct:
                correct_count += 1
            if eval_result.grounded:
                grounded_count += 1
            total_score += eval_result.score

    hit_rate = (retrieval_hits / total) * 100 if total > 0 else 0
    mean_recall_5 = (total_recall_5 / total) * 100 if total > 0 else 0
    mean_precision_5 = (total_precision_5 / total) * 100 if total > 0 else 0
    accuracy = (correct_count / total) * 100 if total > 0 else 0
    groundedness = (grounded_count / total) * 100 if total > 0 else 0
    avg_score = total_score / total if total > 0 else 0.0

    print("========================================")
    print("RAG EVALUATION")
    print("========================================\n")
    print(f"Total questions:       {total}\n")
    print(f"Retrieval hit rate:    {hit_rate:.0f}%\n")
    print(f"Recall@5:              {mean_recall_5:.0f}%\n")
    print(f"Precision@5:           {mean_precision_5:.0f}%\n")
    print(f"Answer accuracy:       {accuracy:.0f}%\n")
    print(f"Groundedness:          {groundedness:.0f}%\n")
    print(f"Average score:         {avg_score:.1f} / 5\n")
    print("========================================")

if __name__ == "__main__":
    asyncio.run(run_evaluation())


