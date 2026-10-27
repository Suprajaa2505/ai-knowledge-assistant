import time

from app.evaluation.dataset import EVALUATION_DATASET
from app.retrieval.retriever import retrieve_documents
from app.retrieval.context_builder import build_context
from app.generation.generator import generate_answer, GeminiServiceError


REFUSAL_TEXT = "I couldn't find the answer in the provided documents."


def evaluate_refusal(answer, answerable):
    if answerable:
        return {
            "expected": False,
            "actual": REFUSAL_TEXT in answer,
            "passed": REFUSAL_TEXT not in answer
        }

    return {
        "expected": True,
        "actual": REFUSAL_TEXT in answer,
        "passed": REFUSAL_TEXT in answer
    }

def evaluate_citations(answer, metadatas, answerable):
    # A correctly refused unanswerable question does not need a citation.
    if not answerable:
        return {
            "expected": False,
            "actual": False,
            "passed": True
        }

    if not metadatas:
        return {
            "expected": True,
            "actual": False,
            "passed": False
        }

    answer_lower = answer.lower()

    citation_found = False

    for metadata in metadatas:
        source = metadata["source"].lower()
        page = metadata.get("page")

        if source not in answer_lower:
            continue

        # For PDFs, require the page number as well.
        if page is not None:
            page_text = str(page)

            if (
                f"page {page_text}" in answer_lower
                or f"page {page_text}" in answer_lower.replace(" ", "")
            ):
                citation_found = True
                break

        # For documents without page metadata,
        # the source name itself is enough.
        else:
            citation_found = True
            break

    return {
        "expected": True,
        "actual": citation_found,
        "passed": citation_found
    }

def evaluate_generation_result(
    answer,
    metadatas,
    expected_behavior,
    answerable
):
    refusal_result = evaluate_refusal(
        answer=answer,
        answerable=answerable
    )

    citation_result = evaluate_citations(
    answer=answer,
    metadatas=metadatas,
    answerable=answerable
)

    return {
        "expected_behavior": expected_behavior,
        "refusal_check": refusal_result,
        "citation_check": citation_result,
        "answer": answer
    }


def evaluate_generation(top_k=3):
    evaluation_results = []

    for index, item in enumerate(EVALUATION_DATASET):
        query = item["query"]
        answerable = item["answerable"]

        print(f"\nEvaluating: {query}")

        try:
            documents, metadatas = retrieve_documents(
                query=query,
                top_k=top_k
            )

            context = build_context(
                documents,
                metadatas
            )

            answer = generate_answer(
                query=query,
                context=context
            )

        except GeminiServiceError as error:
            print(
                f"Evaluation stopped because Gemini API failed: "
                f"{error}"
            )
            break

        evaluation = evaluate_generation_result(
            answer=answer,
            metadatas=metadatas,
            expected_behavior=item["expected_behavior"],
            answerable=answerable
        )

        evaluation_results.append({
            "query": query,
            "answerable": answerable,
            "retrieved_chunks": [
                (
                    metadata["document_id"],
                    metadata["chunk_index"]
                )
                for metadata in metadatas
            ],
            "answer": answer,
            "evaluation": evaluation
        })

        if index < len(EVALUATION_DATASET) - 1:
            time.sleep(2)

    return evaluation_results


if __name__ == "__main__":
    results = evaluate_generation(top_k=3)

    print("\n" + "=" * 80)
    print("GENERATION EVALUATION RESULTS")
    print("=" * 80)

    for result in results:
        print("\n" + "-" * 80)
        print("Query:", result["query"])
        print("Answerable:", result["answerable"])

        print("\nRetrieved chunks:")
        print(result["retrieved_chunks"])

        print("\nGenerated answer:")
        print(result["answer"])

        print("\nEvaluation:")
        print(result["evaluation"])