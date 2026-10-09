"""Source-span selection never rewrites label facts and obeys existing API limits."""
import asyncio
import json
from types import SimpleNamespace

from openai import APITimeoutError, RateLimitError
import pytest

from es.label_llm import HAZARDS, label_rows, read_cache, source_spans

TEXT = "The engine emitted smoke while driving. The vehicle then stopped on the road."
INVALID_QUOTE = "Unvalidated invented quotation never stored"

def label():
    return {"primary_category": "fire_thermal", "secondary_categories": ["engine_stall"],
            "hazards": {h: h in {"smoke", "while_driving"} for h in HAZARDS},
            "severity": 2, "evidence_quote": INVALID_QUOTE, "summary_ko": "주행 중 연기 발생 후 차량 정지"}

def response(content, *, refusal=None):
    return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20, prompt_tokens_details=None),
        choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(refusal=refusal, content=json.dumps(content)))])

def setup(root, create):
    (root / "docs").mkdir()
    (root / "docs/LLM_PROMPTS.md").write_text("### system\n```\nLabel the complaint.\n```", encoding="utf-8")
    return SimpleNamespace(api_key="synthetic-quote-key", chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

def run(root, client, **kwargs):
    return asyncio.run(label_rows([{"odino": str(i), "text": TEXT} for i in range(3)], root=root,
        client=client, limit=2, concurrency=1, max_attempts=kwargs.pop("max_attempts", 1),
        quote_selection_fallback=True, **kwargs))

def test_selection_preserves_label_and_records_independent_provenance(tmp_path):
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        if len(calls) % 2:
            return response(label())
        return response({"span_id": 0})
    client = setup(tmp_path, create)
    report = run(tmp_path, client, max_new_rows=1)
    assert len(calls) == 2 and report["completed"] == 1 and report["cohort_pending"] == 1
    assert report["quote_selection_completed"] == report["quote_selection_responses"] == 1
    assert report["quote_mismatch_attempts"] == 1 and report["retry_attempts"] == 0
    cached = read_cache(tmp_path / "data/labels/labels_llm.jsonl")[0]
    chosen = source_spans(TEXT)[0]
    assert cached["label"] == {**label(), "evidence_quote": TEXT[chosen["start"]:chosen["end"]]}
    assert cached["quote_selection"]["source_start"] == chosen["start"]
    assert cached["quote_selection"]["source_end"] == chosen["end"]
    usage = read_cache(tmp_path / "data/labels/llm_usage.jsonl")
    assert [u["stage"] for u in usage] == ["label", "quote_selection"]
    assert usage[0]["cache_key"] == usage[1]["cache_key"] == cached["cache_key"]
    assert usage[0]["prompt_hash"] == cached["prompt_hash"] != usage[1]["prompt_hash"]
    assert usage[0]["input_hash"] != usage[1]["input_hash"] == cached["quote_selection"]["input_hash"]
    assert report["estimated_usd"] == pytest.approx(sum(u["estimated_usd"] for u in usage))
    assert INVALID_QUOTE not in calls[1]["messages"][1]["content"]
    assert all(INVALID_QUOTE not in p.read_text() for p in tmp_path.rglob("*.json*"))
    # Enabling selection later cannot invalidate a previously strict-valid cache.
    resumed = run(tmp_path, client)
    assert resumed["cache_reused"] == 1 and resumed["cohort_complete"] and len(calls) == 4

def test_sentence_and_long_window_candidates_are_exact_and_overlap():
    short = source_spans(TEXT)
    assert len(short) == 2
    source = " ".join(["long complaint wording"] * 35)
    spans = source_spans(source)
    assert len(spans) > 2
    assert all(0 < len(s["text"]) <= 200 and s["text"] == source[s["start"]:s["end"]] for s in spans)
    assert all(a["start"] < b["start"] < a["end"] for a, b in zip(spans, spans[1:]))
    covered = {i for s in spans for i in range(s["start"], s["end"])}
    assert all(i in covered for i, c in enumerate(source) if not c.isspace())
    assert source_spans("") == source_spans("  ") == []

@pytest.mark.parametrize("picked", [{"span_id": -1}, {"span_id": 99}, {"span_id": True},
                                     {"span_id": 0, "summary_ko": "changed"}, {}, []])
def test_invalid_selection_never_enters_success_cache(tmp_path, picked):
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        return response(label() if len(calls) == 1 else picked)
    report = run(tmp_path, setup(tmp_path, create), max_new_rows=1)
    assert report["failed"] == 1 and report["completed"] == 0 and len(calls) == 2
    failure = read_cache(tmp_path / "data/labels/llm_failures.jsonl")[0]
    assert failure["errors"] == ["quote_mismatch", "invalid_quote_selection"]
    assert failure["attempts"] == 1
    assert not (tmp_path / "data/labels/labels_llm.jsonl").exists()

def test_selection_runs_only_once_even_when_primary_retries(tmp_path, monkeypatch):
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        return response({"span_id": -1} if len(calls) == 2 else label())
    async def no_sleep(_):
        pass
    monkeypatch.setattr("es.label_llm.asyncio.sleep", no_sleep)
    report = run(tmp_path, setup(tmp_path, create), max_attempts=3, max_new_rows=1)
    assert len(calls) == 4 and report["quote_selection_responses"] == 1
    assert report["quote_mismatch_attempts"] == 3 and report["retry_attempts"] == 2

def test_enabling_fallback_preserves_prior_direct_success(tmp_path):
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        return response({**label(), "evidence_quote": TEXT})
    client = setup(tmp_path, create)
    rows = [{"odino": "1", "text": TEXT}]
    first = asyncio.run(label_rows(rows, root=tmp_path, client=client, quote_selection_fallback=False))
    before = (tmp_path / "data/labels/labels_llm.jsonl").read_bytes()
    second = asyncio.run(label_rows(rows, root=tmp_path, client=client, quote_selection_fallback=True))
    assert first["completed"] == 1 and second["cache_reused"] == 1 and len(calls) == 1
    assert (tmp_path / "data/labels/labels_llm.jsonl").read_bytes() == before

def test_selection_short_retry_after_delays_next_record(tmp_path, monkeypatch):
    now, calls = [100.0], []
    monkeypatch.setattr("es.label_llm.time.monotonic", lambda: now[0])
    async def sleep(seconds):
        now[0] += seconds
    monkeypatch.setattr("es.label_llm.asyncio.sleep", sleep)
    async def create(**kwargs):
        calls.append(now[0])
        if len(calls) == 1:
            return response(label())
        if len(calls) == 2:
            raise RateLimitError("private", response=SimpleNamespace(status_code=429, headers={"retry-after": "2"}, request=SimpleNamespace()), body={})
        return response({**label(), "evidence_quote": TEXT})
    report = run(tmp_path, setup(tmp_path, create))
    assert calls == [100.0, 100.0, 102.0]
    assert report["failed"] == 1 and report["completed"] == 1

@pytest.mark.parametrize("problem", ["no_candidates", "summary_length"])
def test_invalid_nonquote_fields_or_no_candidates_avoid_extra_call(tmp_path, monkeypatch, problem):
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        result = label()
        if problem == "summary_length":
            result["summary_ko"] = "a" * 41
        return response(result)
    if problem == "no_candidates":
        monkeypatch.setattr("es.label_llm.source_spans", lambda _: [])
    report = run(tmp_path, setup(tmp_path, create), max_new_rows=1)
    assert len(calls) == 1 and report["failed"] == 1

def test_selected_span_is_privacy_checked_again(tmp_path, monkeypatch):
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        return response(label() if len(calls) == 1 else {"span_id": 1})
    monkeypatch.setattr("es.label_llm.privacy_matches", lambda value, denied: "then stopped" in value)
    report = run(tmp_path, setup(tmp_path, create), max_new_rows=1)
    assert report["failed"] == 1 and len(calls) == 2
    assert read_cache(tmp_path / "data/labels/llm_failures.jsonl")[0]["errors"][-1] == "sensitive_output"

@pytest.mark.parametrize("problem", ["quota", "long_delay", "timeout", "refusal"])
def test_selection_errors_preserve_api_safety_boundaries(tmp_path, problem):
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            return response(label())
        if problem == "refusal":
            return response({}, refusal="private refusal detail")
        if problem == "timeout":
            raise APITimeoutError(request=SimpleNamespace())
        headers = {"retry-after": "1728"} if problem == "long_delay" else {}
        body = {"code": "insufficient_quota"} if problem == "quota" else {"type": "rate_limit_exceeded"}
        raise RateLimitError("private API detail", response=SimpleNamespace(status_code=429, headers=headers, request=SimpleNamespace()), body=body)
    client = setup(tmp_path, create)
    report = run(tmp_path, client, **({} if problem in {"quota", "long_delay"} else {"max_new_rows": 1}))
    assert len(calls) == 2 and report["completed"] == 0 and report["failed"] == 1
    assert report["cohort_pending"] == 2
    assert report["stopped_for_api_error"] == (problem in {"quota", "long_delay"})
    usage = read_cache(tmp_path / "data/labels/llm_usage.jsonl")
    assert len(usage) == (2 if problem == "refusal" else 1)
    assert all("private API detail" not in p.read_text() and "private refusal detail" not in p.read_text()
               and client.api_key not in p.read_text() for p in tmp_path.rglob("*.json*"))
    if problem == "long_delay":
        second = run(tmp_path, client)
        assert second["defer_reason"] == "local_server_cooldown" and len(calls) == 2
