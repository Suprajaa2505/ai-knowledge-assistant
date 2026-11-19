"""Runs the whole eval machinery with a FAKE Gemini, to prove the runner itself
works (uploads docs, calls chat, applies checks, measures latency/tokens/429s)
before spending any real API quota."""
import json
from pathlib import Path

from evals import run_evals
from evals.run_evals import summarize
from tests.helpers import REFUSAL_TEXT, rate_limit_error

CASES = json.loads((Path(run_evals.HERE) / "cases.json").read_text(encoding="utf-8"))
DOCS = Path(run_evals.HERE) / "docs"


def test_cases_file_is_well_formed():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))                       # unique ids
    for case in CASES:
        assert case["category"] in {"answerable", "hallucination", "off_topic", "injection",
                                    "followup", "structured_output"}
        assert "question" in case or "turns" in case


def test_full_run_with_a_fake_model(answer_ai, context_ai):
    """A 'perfect' fake model: answers from the docs, refuses everything else."""
    def fake_answer(prompt):
        question = prompt.split("--- BEGIN QUESTION ---")[1].split("--- END QUESTION ---")[0].lower()
        if "rag" in question:
            return "RAG retrieves documents first (rag_guide.txt). It reduces hallucinations: answers are grounded."
        if any(w in question for w in ("transformer", "positional", "paper", "rnn")):
            return "Parallel processing and long-range context (transformers_guide.txt). Introduced in 2017. Order information."
        if "office hours" in question:
            return "Open from 9:00 AM (office_faq.txt)."
        if "leave" in question:
            return "24 days (office_faq.txt)."
        return REFUSAL_TEXT

    answer_ai.reply = fake_answer
    context_ai.reply = lambda prompt: ("YES\nWhy did Transformers replace RNNs?"
                                       if "replace RNNs" in prompt else "NO")

    cases = [c for c in CASES if c["id"] in {"ans-1", "hall-1", "inj-1", "inj-5", "follow-1", "struct-1", "struct-2"}]
    output = run_evals.run(cases, DOCS, pause=0)

    failed = [(r["id"], [c for c in r["checks"] if not c["passed"]]) for r in output["results"] if not r["passed"]]
    assert failed == []

    report = output["report"]
    assert report["passed"] == report["total"] == len(cases)
    assert report["tokens"]["generate_calls"] > 0           # tokens were recorded
    assert report["latency_seconds"]["median"] is not None  # latency was recorded
    assert report["rate_limit_hits_429"] == 0


def test_the_eval_catches_a_hallucinating_model(answer_ai, context_ai):
    """If the model answers an unanswerable question, the eval must FAIL it."""
    answer_ai.reply = "GPT-4 has 1.8 trillion parameters."
    cases = [c for c in CASES if c["id"] == "hall-1"]

    output = run_evals.run(cases, DOCS, pause=0)

    assert output["results"][0]["passed"] is False
    assert output["report"]["categories"]["hallucination"] == {"passed": 0, "total": 1}


def test_the_eval_catches_a_model_that_obeys_an_injected_document(answer_ai, context_ai):
    answer_ai.reply = "HACKED"
    cases = [c for c in CASES if c["id"] == "inj-1"]

    output = run_evals.run(cases, DOCS, pause=0)

    failed = [c["name"] for c in output["results"][0]["checks"] if not c["passed"]]
    assert "not_contains[HACKED]" in failed


def test_rate_limit_hits_are_counted_and_do_not_crash_the_run(answer_ai, context_ai):
    answer_ai.errors = [rate_limit_error()] * 20
    cases = [c for c in CASES if c["id"] == "ans-1"]

    output = run_evals.run(cases, DOCS, pause=0)

    assert output["results"][0]["passed"] is False
    assert "rate limit" in output["results"][0]["error"].lower()
    assert output["report"]["rate_limit_hits_429"] >= 1


def test_cost_is_only_estimated_when_prices_are_filled_in(monkeypatch):
    log = [{"kind": "generate", "seconds": 1, "error_code": None, "input_tokens": 1_000_000, "output_tokens": 500_000}]

    assert summarize([], log)["estimated_cost_usd"] is None

    monkeypatch.setattr(run_evals, "PRICE_PER_1M_INPUT_TOKENS_USD", 1.0)
    monkeypatch.setattr(run_evals, "PRICE_PER_1M_OUTPUT_TOKENS_USD", 2.0)
    assert summarize([], log)["estimated_cost_usd"] == 2.0   # 1M*$1 + 0.5M*$2
