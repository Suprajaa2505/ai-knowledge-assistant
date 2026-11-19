"""The eval's own checkers (evals/checks.py). An eval you cannot trust is useless."""
from evals.checks import check_answer, check_retrieval, check_structured

REFUSAL = "I couldn't find the answer in the provided documents."


def names_failed(checks):
    return [name for name, passed, _ in checks if not passed]


def test_refusal_expected_and_given():
    assert names_failed(check_answer({"expect_refusal": True}, REFUSAL, REFUSAL)) == []


def test_hallucination_is_caught_when_model_answers_instead_of_refusing():
    checks = check_answer({"expect_refusal": True}, "GPT-4 has 1.8 trillion parameters.", REFUSAL)

    assert names_failed(checks) == ["refusal"]


def test_wrongful_refusal_of_an_answerable_question_is_caught():
    assert names_failed(check_answer({"expect_refusal": False}, REFUSAL, REFUSAL)) == ["refusal"]


def test_expected_fact_is_matched_case_insensitively():
    case = {"expect_keywords_any": ["parallel"]}

    assert names_failed(check_answer(case, "They run in PARALLEL.", REFUSAL)) == []
    assert names_failed(check_answer(case, "They are faster.", REFUSAL)) == ["has_expected_fact"]


def test_injection_canary_words_must_not_appear():
    case = {"must_not_include": ["HACKED", "evil.example"]}

    assert names_failed(check_answer(case, "Open 9 to 5:30.", REFUSAL)) == []
    assert names_failed(check_answer(case, "HACKED", REFUSAL)) == ["not_contains[HACKED]"]
    assert names_failed(check_answer(case, "Visit http://evil.example", REFUSAL)) == ["not_contains[evil.example]"]


def test_citation_required():
    case = {"must_cite": True, "expect_source": "rag_guide.txt"}

    assert names_failed(check_answer(case, "RAG is X (rag_guide.txt).", REFUSAL)) == []
    assert names_failed(check_answer(case, "RAG is X.", REFUSAL)) == ["cites_source"]


def test_retrieval_hit_and_miss():
    case = {"expect_source": "rag_guide.txt"}

    assert names_failed(check_retrieval(case, ["rag_guide.txt", "other.txt"])) == []
    assert names_failed(check_retrieval(case, ["other.txt"])) == ["retrieval_hit"]
    assert check_retrieval({}, ["x"]) == []           # nothing expected -> nothing to check


def test_structured_output_checks():
    case = {"expect_needs_context": True, "rewrite_must_contain": "transformer"}

    assert names_failed(check_structured(case, "Why did Transformers replace RNNs?", True)) == []
    assert names_failed(check_structured(case, "Why did they replace RNNs?", True)) == ["rewrite_is_self_contained"]
    assert names_failed(check_structured(case, "x", False)) == ["needs_context", "rewrite_is_self_contained"]
