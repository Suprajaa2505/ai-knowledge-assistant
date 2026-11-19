"""Your existing evaluation code (app/evaluation) - checking the maths and the
refusal / citation checkers themselves. An eval you cannot trust is worse than none."""
import pytest

from app.evaluation.generation import REFUSAL_TEXT, evaluate_citations, evaluate_refusal
from app.evaluation.retrieval import calculate_mrr, calculate_precision_at_k, calculate_recall_at_k

RELEVANT = {("d", 1), ("d", 2)}


def test_precision_recall_mrr_known_values():
    retrieved = [("d", 9), ("d", 1), ("d", 2)]

    assert calculate_precision_at_k(retrieved, RELEVANT, 3) == pytest.approx(2 / 3)
    assert calculate_recall_at_k(retrieved, RELEVANT, 3) == 1.0
    assert calculate_mrr(retrieved, RELEVANT) == 0.5      # first hit at rank 2


def test_nothing_relevant_retrieved_scores_zero():
    retrieved = [("d", 7), ("d", 8), ("d", 9)]

    assert calculate_precision_at_k(retrieved, RELEVANT, 3) == 0.0
    assert calculate_recall_at_k(retrieved, RELEVANT, 3) == 0.0
    assert calculate_mrr(retrieved, RELEVANT) == 0.0


def test_precision_at_3_is_capped_when_only_one_chunk_is_relevant():
    """Why your Precision@3 = 0.58 is NOT a problem: with 1 relevant chunk the
    best possible Precision@3 is 0.33, so this metric punishes good retrieval."""
    best_possible = calculate_precision_at_k([("d", 1), ("d", 8), ("d", 9)], {("d", 1)}, 3)

    assert best_possible == pytest.approx(1 / 3)


def test_refusal_checker():
    assert evaluate_refusal(REFUSAL_TEXT, answerable=False)["passed"]
    assert not evaluate_refusal("Quantum computers use qubits.", answerable=False)["passed"]
    assert evaluate_refusal("RAG retrieves chunks.", answerable=True)["passed"]
    assert not evaluate_refusal(REFUSAL_TEXT, answerable=True)["passed"]


def test_citation_checker_needs_source_and_page_for_pdfs():
    metadatas = [{"source": "guide.pdf", "page": 2}]

    assert evaluate_citations("Yes (guide.pdf, Page 2).", metadatas, True)["passed"]
    assert not evaluate_citations("Yes (guide.pdf).", metadatas, True)["passed"]
    assert not evaluate_citations("Yes, no citation.", metadatas, True)["passed"]


def test_citation_checker_for_txt_only_needs_the_filename():
    assert evaluate_citations("See notes.txt", [{"source": "notes.txt"}], True)["passed"]
