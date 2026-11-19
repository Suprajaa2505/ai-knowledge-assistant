"""Pure checking functions: no API, no app imports, so they are easy to unit test.

Every check returns (name, passed, detail).
Design rule: only DETERMINISTIC checks (exact text / keywords / yes-no flags).
You can explain exactly why each one passed or failed.
"""


def check_answer(case, answer, refusal_text):
    results = []
    lowered = answer.lower()

    if "expect_refusal" in case:
        refused = refusal_text in answer
        results.append((
            "refusal",
            refused == case["expect_refusal"],
            "refused" if refused else "answered",
        ))

    keywords = case.get("expect_keywords_any")
    if keywords:
        found = [k for k in keywords if k.lower() in lowered]
        results.append(("has_expected_fact", bool(found), f"looked for any of {keywords}"))

    for banned in case.get("must_not_include", []):
        present = banned.lower() in lowered
        results.append((f"not_contains[{banned}]", not present,
                        "FOUND in answer" if present else "absent"))

    if case.get("must_cite"):
        source = case.get("expect_source", "")
        cited = source.lower() in lowered
        results.append(("cites_source", cited, f"expected '{source}' in answer"))

    return results


def check_retrieval(case, retrieved_sources):
    """Did the right document appear in the top-k retrieved chunks?"""
    expected = case.get("expect_source")
    if not expected:
        return []
    hit = expected in retrieved_sources
    return [("retrieval_hit", hit, f"expected {expected}, got {sorted(set(retrieved_sources))}")]


def check_structured(case, rewritten_query, needs_context):
    """Checks the contextualizer's NO / YES+rewrite output."""
    results = [(
        "needs_context",
        needs_context == case["expect_needs_context"],
        f"expected {case['expect_needs_context']}, got {needs_context}",
    )]

    fragment = case.get("rewrite_must_contain")
    if fragment:
        results.append((
            "rewrite_is_self_contained",
            fragment.lower() in rewritten_query.lower(),
            f"rewrite was: {rewritten_query!r}",
        ))

    return results
