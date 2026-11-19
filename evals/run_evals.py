"""Evaluate the REAL app end to end with the REAL Gemini API.

Run from the project root (needs GEMINI_API_KEY in your .env):

    python -m evals.run_evals                  # all cases
    python -m evals.run_evals --pause 8        # slower, if you hit rate limits
    python -m evals.run_evals --only hallucination injection

What it does
  1. Starts the app in-process with a TEMPORARY database + vector store
     (your own documents and chats are never touched).
  2. Uploads the small documents in evals/docs/ through the real /upload endpoint.
  3. Asks every question in evals/cases.json through the real /chat endpoint.
  4. Applies simple, deterministic checks (evals/checks.py).
  5. Prints a summary and saves evals/results/latest.json + latest.md.

It also measures latency, token usage and rate-limit hits (429s) for free,
by wrapping the Gemini client.
"""
import argparse
import json
import os
import statistics
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

from evals.checks import check_answer, check_retrieval, check_structured  # noqa: E402

# Fill these in from the Gemini pricing page for the model you use.
# Left as None on purpose: prices change, so no number is hard-coded here.
PRICE_PER_1M_INPUT_TOKENS_USD = None
PRICE_PER_1M_OUTPUT_TOKENS_USD = None


class Recorder:
    """Wraps a Gemini client and records time, tokens and errors of every call."""

    def __init__(self, inner, log, kind):
        self.inner = inner
        self.log = log
        self.kind = kind

    @property
    def models(self):
        return self

    def _call(self, method_name, **kwargs):
        started = time.perf_counter()
        try:
            response = getattr(self.inner.models, method_name)(**kwargs)
        except Exception as error:
            self.log.append({"kind": self.kind, "seconds": time.perf_counter() - started,
                             "error_code": getattr(error, "code", None),
                             "input_tokens": None, "output_tokens": None})
            raise

        usage = getattr(response, "usage_metadata", None)
        output = (getattr(usage, "candidates_token_count", None) or 0) + \
                 (getattr(usage, "thoughts_token_count", None) or 0)
        self.log.append({"kind": self.kind, "seconds": time.perf_counter() - started,
                         "error_code": None,
                         "input_tokens": getattr(usage, "prompt_token_count", None),
                         "output_tokens": output if usage else None})
        return response

    def generate_content(self, **kwargs):
        return self._call("generate_content", **kwargs)

    def embed_content(self, **kwargs):
        return self._call("embed_content", **kwargs)


def _result(case, checks, answer="", seconds=None, top_distance=None, error=None):
    return {
        "id": case["id"], "category": case["category"], "question": case.get("question", ""),
        "checks": [{"name": n, "passed": bool(p), "detail": d} for n, p, d in checks],
        "passed": bool(checks) and all(p for _, p, _ in checks),
        "answer": answer, "seconds": seconds, "top_distance": top_distance, "error": error,
    }


def run(cases, docs_dir, top_k=3, pause=4.0):
    """Runs all cases and returns {"results": [...], "report": {...}}.

    Imports of `app` happen here (not at the top of the file) so that main()
    can switch to a temporary folder first.
    """
    from fastapi.testclient import TestClient
    from app import main as app_main
    from app.embeddings import embedder
    from app.generation import generator
    from app.generation.generator import REFUSAL_TEXT
    from app.retrieval import contextualizer

    log = []
    saved = (generator.client, contextualizer.client, embedder.client)
    generator.client = Recorder(saved[0], log, "generate")
    contextualizer.client = Recorder(saved[1], log, "generate")
    embedder.client = Recorder(saved[2], log, "embed")

    client = TestClient(app_main.app, raise_server_exceptions=False)
    results = []

    try:
        for path in sorted(Path(docs_dir).glob("*.txt")):
            response = client.post("/upload", files={"file": (path.name, path.read_bytes(), "text/plain")})
            if response.status_code != 200:
                raise RuntimeError(f"Could not upload {path.name}: {response.status_code} {response.text}")
            time.sleep(pause)

        for index, case in enumerate(cases):
            print(f"[{index + 1}/{len(cases)}] {case['id']}: {case.get('question') or case.get('turns')}")
            try:
                results.append(_run_case(case, client, contextualizer, REFUSAL_TEXT, top_k))
            except Exception as error:  # an eval run should never crash half-way
                results.append(_result(case, [("no_crash", False, repr(error))], error=repr(error)))
            time.sleep(pause)
    finally:
        generator.client, contextualizer.client, embedder.client = saved

    return {"results": results, "report": summarize(results, log)}


def _run_case(case, client, contextualizer, refusal_text, top_k):
    if case["category"] == "structured_output":
        started = time.perf_counter()
        rewritten, needs_context = contextualizer.contextualize_query(case["question"], case["history"])
        return _result(case, check_structured(case, rewritten, needs_context),
                       answer=rewritten, seconds=time.perf_counter() - started)

    conversation_id = client.post("/conversations", json={}).json()["conversation_id"]
    turns = case.get("turns") or [case["question"]]

    for turn in turns:
        started = time.perf_counter()
        response = client.post(f"/conversations/{conversation_id}/chat", json={"query": turn, "top_k": top_k})
        seconds = time.perf_counter() - started
        if response.status_code != 200:
            detail = response.json().get("detail", response.text)
            return _result(case, [("api_call", False, f"HTTP {response.status_code}: {detail}")],
                           error=detail)

    answer = response.json()["answer"]
    checks = check_answer(case, answer, refusal_text)
    top_distance = None

    if "turns" not in case:
        # Retrieval is checked separately, so a wrong refusal cannot hide it.
        probe = client.post("/evaluate/retrieval", json={"query": case["question"], "top_k": top_k})
        if probe.status_code == 200:
            rows = probe.json()["results"]
            checks += check_retrieval(case, [row["metadata"]["source"] for row in rows])
            top_distance = rows[0]["distance"] if rows else None

    return _result(case, checks, answer=answer, seconds=seconds, top_distance=top_distance)


def summarize(results, log):
    categories = defaultdict(lambda: {"passed": 0, "total": 0})
    for result in results:
        categories[result["category"]]["total"] += 1
        categories[result["category"]]["passed"] += int(result["passed"])

    seconds = [r["seconds"] for r in results if r["seconds"] is not None and r["category"] != "structured_output"]
    ok_generate = [c for c in log if c["kind"] == "generate" and c["error_code"] is None]
    input_tokens = sum(c["input_tokens"] or 0 for c in ok_generate)
    output_tokens = sum(c["output_tokens"] or 0 for c in ok_generate)

    cost = None
    if PRICE_PER_1M_INPUT_TOKENS_USD is not None and PRICE_PER_1M_OUTPUT_TOKENS_USD is not None:
        cost = (input_tokens * PRICE_PER_1M_INPUT_TOKENS_USD + output_tokens * PRICE_PER_1M_OUTPUT_TOKENS_USD) / 1_000_000

    def avg_distance(wanted_answerable):
        values = [r["top_distance"] for r in results
                  if r["top_distance"] is not None and (r["category"] == "answerable") == wanted_answerable]
        return round(statistics.mean(values), 3) if values else None

    return {
        "categories": dict(categories),
        "passed": sum(r["passed"] for r in results), "total": len(results),
        "latency_seconds": {"median": round(statistics.median(seconds), 2) if seconds else None,
                            "max": round(max(seconds), 2) if seconds else None},
        "tokens": {"generate_calls": len(ok_generate), "input_total": input_tokens, "output_total": output_tokens,
                   "input_avg_per_call": round(input_tokens / len(ok_generate)) if ok_generate else None,
                   "output_avg_per_call": round(output_tokens / len(ok_generate)) if ok_generate else None},
        "rate_limit_hits_429": sum(1 for c in log if c["error_code"] == 429),
        "estimated_cost_usd": cost,
        "avg_top_distance": {"answerable": avg_distance(True), "not_answerable": avg_distance(False)},
    }


def to_markdown(report):
    lines = ["| Category | Passed |", "|---|---:|"]
    for name, counts in report["categories"].items():
        lines.append(f"| {name} | {counts['passed']}/{counts['total']} |")
    lines.append(f"| **Total** | **{report['passed']}/{report['total']}** |")
    lat, tok = report["latency_seconds"], report["tokens"]
    lines += ["",
              f"- Latency per chat request: median {lat['median']}s, max {lat['max']}s",
              f"- Tokens: {tok['input_total']} in / {tok['output_total']} out over {tok['generate_calls']} generate calls "
              f"(avg {tok['input_avg_per_call']} in / {tok['output_avg_per_call']} out)",
              f"- Rate-limit (429) errors seen: {report['rate_limit_hits_429']}"]
    if report["estimated_cost_usd"] is not None:
        lines.append(f"- Estimated cost of this run: ${report['estimated_cost_usd']:.4f}")
    return "\n".join(lines)


def print_report(output):
    print("\n" + "=" * 70 + "\nEVAL RESULTS\n" + "=" * 70)
    for result in output["results"]:
        mark = "PASS" if result["passed"] else "FAIL"
        print(f"{mark}  {result['id']:<10} {result['category']}")
        if not result["passed"]:
            for check in result["checks"]:
                if not check["passed"]:
                    print(f"        x {check['name']}: {check['detail']}")
            print(f"        answer: {result['answer'][:200]!r}")
    print("\n" + to_markdown(output["report"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pause", type=float, default=4.0, help="seconds to wait between API calls (default 4)")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--only", nargs="*", help="run only these categories")
    args = parser.parse_args()

    sys.path.insert(0, str(ROOT))
    os.chdir(tempfile.mkdtemp(prefix="rag-evals-"))   # temp db + vector store, before importing app

    cases = json.loads((HERE / "cases.json").read_text(encoding="utf-8"))
    if args.only:
        cases = [c for c in cases if c["category"] in args.only]

    output = run(cases, HERE / "docs", top_k=args.top_k, pause=args.pause)
    print_report(output)

    results_dir = HERE / "results"
    results_dir.mkdir(exist_ok=True)
    (results_dir / "latest.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    (results_dir / "latest.md").write_text(to_markdown(output["report"]) + "\n", encoding="utf-8")
    print(f"\nSaved to {results_dir}")


if __name__ == "__main__":
    main()
