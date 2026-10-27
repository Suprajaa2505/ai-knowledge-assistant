
import time

from app.evaluation.dataset import EVALUATION_DATASET
from app.evaluation.retrieval import (
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_mrr
)
from app.retrieval.retriever import retrieve_documents
from app.gemini_service import GeminiServiceError


def evaluate_retrieval(k=3):
    evaluation_results = []

    for index, item in enumerate(EVALUATION_DATASET):
        query = item["query"]
        relevant_chunks = item["relevant_chunks"]
        answerable = item["answerable"]

        print(f"\nEvaluating: {query}")

        try:
            documents, metadatas = retrieve_documents(
                query=query,
                top_k=k
            )

        except GeminiServiceError as error:
            print(f"Evaluation stopped because Gemini API failed: {error}")
            break

        retrieved_chunks = [
            (
                metadata["document_id"],
                metadata["chunk_index"]
            )
            for metadata in metadatas
        ]

        # Metrics are meaningful for answerable queries.
        if answerable:
            precision = calculate_precision_at_k(
                retrieved_chunks,
                relevant_chunks,
                k
            )

            recall = calculate_recall_at_k(
                retrieved_chunks,
                relevant_chunks,
                k
            )

            mrr = calculate_mrr(
                retrieved_chunks,
                relevant_chunks
            )

        else:
            precision = None
            recall = None
            mrr = None

        evaluation_results.append({
            "query": query,
            "answerable": answerable,
            "precision_at_k": precision,
            "recall_at_k": recall,
            "mrr": mrr,
            "retrieved_chunks": retrieved_chunks
        })

        # Avoid sending embedding requests back-to-back.
        if index < len(EVALUATION_DATASET) - 1:
            time.sleep(2)

    return evaluation_results


if __name__ == "__main__":
    results = evaluate_retrieval(k=3)

    print("\n" + "=" * 60)
    print("RETRIEVAL EVALUATION RESULTS")
    print("=" * 60)

    answerable_results = []

    for result in results:
        print("\nQuery:", result["query"])
        print("Answerable:", result["answerable"])
        print("Precision@3:", result["precision_at_k"])
        print("Recall@3:", result["recall_at_k"])
        print("MRR:", result["mrr"])
        print("Retrieved:", result["retrieved_chunks"])

        if result["answerable"]:
            answerable_results.append(result)

    if answerable_results:
        average_precision = sum(
            result["precision_at_k"]
            for result in answerable_results
        ) / len(answerable_results)

        average_recall = sum(
            result["recall_at_k"]
            for result in answerable_results
        ) / len(answerable_results)

        average_mrr = sum(
            result["mrr"]
            for result in answerable_results
        ) / len(answerable_results)

        print("\n" + "-" * 60)
        print("AVERAGE METRICS — ANSWERABLE QUERIES ONLY")
        print("-" * 60)
        print("Average Precision@3:", round(average_precision, 4))
        print("Average Recall@3:", round(average_recall, 4))
        print("Average MRR:", round(average_mrr, 4))
