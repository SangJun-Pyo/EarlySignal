import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from es.label_llm import MODEL, QuoteMismatch, cache_key, label_rows, quote_diagnostics, read_cache, usage_cost, validate_label

TEXT = "The engine emitted smoke while driving down the road and stopped abruptly."

def label():
    return {"primary_category": "fire_thermal", "secondary_categories": ["fire_thermal", "engine_stall", "engine_stall"],
            "hazards": {k: k in {"smoke", "while_driving"} for k in ("fire", "smoke", "crash", "injury", "while_driving", "while_parked_or_charging")},
            "severity": 2, "evidence_quote": TEXT, "summary_ko": "주행 중 연기가 발생하고 엔진이 멈춤"}

def test_quote_and_secondary_validation():
    assert validate_label(label(), TEXT)["secondary_categories"] == ["engine_stall"]
    wrong = label(); wrong["evidence_quote"] = "The battery exploded"
    with pytest.raises(ValueError, match="quote_mismatch"):
        validate_label(wrong, TEXT)

def test_cache_invalidates_changed_source_prompt_or_model():
    original = cache_key("1", TEXT, MODEL, "a")
    assert all(original != key for key in (cache_key("1", TEXT+"new", MODEL, "a"), cache_key("1", TEXT, "other", "a"), cache_key("1", TEXT, MODEL, "b")))

def test_known_identifier_with_korean_particle_is_rejected_before_cache():
    result = label()
    result["summary_ko"] = "Exampleville에서 주행 중 연기 발생"
    with pytest.raises(ValueError, match="sensitive_output"):
        validate_label(result, TEXT, denied=["Exampleville"])

def test_interrupted_cache_tail_is_repaired(tmp_path):
    path = tmp_path / "cache.jsonl"
    path.write_text('{"status":"ok"}\n{"broken":', encoding="utf-8")
    assert read_cache(path) == [{"status":"ok"}]
    assert path.read_text() == '{"status":"ok"}\n'

def test_cost_accounts_for_cached_tokens():
    assert usage_cost({"prompt_tokens": 1_000_000, "cached_tokens": 500_000, "completion_tokens": 1_000_000}, MODEL) == pytest.approx(1.85)
    assert usage_cost({}, "unpriced-model") is None

def test_pilot_bounds_calls_and_resume_without_network(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/LLM_PROMPTS.md").write_text("### system\n```\nLabel the complaint.\n```", encoding="utf-8")
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50, prompt_tokens_details=None),
                               choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(refusal=None, content=json.dumps(label())))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    rows = [{"odino": str(i), "text": TEXT} for i in range(3)]
    first = asyncio.run(label_rows(rows, root=tmp_path, limit=2, client=client))
    assert first["completed"] == 2 and len(calls) == 2
    second = asyncio.run(label_rows(rows, root=tmp_path, limit=2, client=client))
    assert second["completed"] == 0 and second["cache_reused"] == 2 and len(calls) == 2
    assert second["cohort_complete"] and second["cohort_size"] == 2
    assert second["cohort_pending"] == 0 and second["resume_odinos"] == []
    assert second["selected"] == 0 and second["cache_scope"] == "within_fixed_cohort"
    assert second["estimated_population_usd"] is None  # This run contains no new usage.
    usage = read_cache(tmp_path / "data/labels/llm_usage.jsonl")
    cached = read_cache(tmp_path / "data/labels/labels_llm.jsonl")
    assert {entry["cache_key"] for entry in usage} == {entry["cache_key"] for entry in cached}
    assert all(entry["input_hash"] and entry["prompt_hash"] for entry in usage)
    assert calls[0]["response_format"]["json_schema"]["strict"] is True

def test_successful_retry_keeps_quote_failure_in_metrics(tmp_path, monkeypatch):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/LLM_PROMPTS.md").write_text("### system\n```\nLabel the complaint.\n```", encoding="utf-8")
    counter = [0]
    async def create(**kwargs):
        counter[0] += 1
        result = label()
        if counter[0] == 1:
            result["evidence_quote"] = "invented quote"
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50, prompt_tokens_details=None),
            choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(refusal=None, content=json.dumps(result)))])
    async def no_sleep(_):
        pass
    monkeypatch.setattr("es.label_llm.asyncio.sleep", no_sleep)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    report = asyncio.run(label_rows([{"odino":"1", "text":TEXT}], root=tmp_path, client=client))
    assert report["completed"] == 1
    assert report["quote_mismatch_attempts"] == 1
    assert report["retry_attempts"] == 1
    assert report["api_responses"] == 2
    assert report["quote_diagnostics"]["observed_attempts"] == 1
    diagnostics = read_cache(tmp_path / "data/labels/llm_quote_diagnostics.jsonl")
    assert len(diagnostics) == 1 and diagnostics[0]["attempt"] == 1
    assert diagnostics[0]["verbatim_in_source"] is False
    assert "invented quote" not in json.dumps(diagnostics)

@pytest.mark.parametrize("quote, source, expected", [
    ("", TEXT, {"empty": True, "verbatim_in_source": False, "normalized_match": False, "too_long": False}),
    ("Smoke " * 40, "Smoke " * 40, {"empty": False, "verbatim_in_source": True, "normalized_match": True, "too_long": True}),
    ("The driver’s\nengine stopped", "The driver's engine stopped", {"empty": False, "verbatim_in_source": False, "normalized_match": True, "too_long": False}),
    ("The engine stopped", "The engine never stopped", {"empty": False, "verbatim_in_source": False, "normalized_match": False, "too_long": False}),
    ("SMOKE", "Smoke", {"empty": False, "verbatim_in_source": False, "normalized_match": False, "too_long": False}),
])
def test_quote_diagnostics_do_not_relax_validation(quote, source, expected):
    actual = quote_diagnostics(quote, source)
    assert {key: actual[key] for key in expected} == expected
    assert actual["length"] == len(quote)
    result = label()
    result["evidence_quote"] = quote
    with pytest.raises(QuoteMismatch, match="^quote_mismatch$") as failure:
        validate_label(result, source)
    assert failure.value.diagnostics == actual

@pytest.mark.parametrize("quote, source, folded_match, normalized_folded_match, longest_ratio", [
    ("SMOKE", "Smoke", True, True, 1.0),
    ("DRIVER’S\nENGINE STOPPED", "The driver's engine stopped yesterday", False, True, 1.0),
    ("ENGINE STOPPED", "ENGINE NEVER STOPPED", False, False, 8 / 14),
    ("", TEXT, False, False, 0.0),
])
def test_casefold_and_longest_match_diagnostics_are_nontext(quote, source, folded_match, normalized_folded_match, longest_ratio):
    diagnostic = quote_diagnostics(quote, source)
    assert diagnostic["casefold_match"] == folded_match
    assert diagnostic["normalized_casefold_match"] == normalized_folded_match
    assert diagnostic["longest_normalized_casefold_match_ratio"] == round(longest_ratio, 4)
    assert all(type(value) in (bool, int, float) for value in diagnostic.values())
    assert 0 <= diagnostic["longest_exact_match_ratio"] <= 1
    assert diagnostic["longest_exact_match_length"] <= len(quote)

def test_exact_quote_at_length_limit_remains_valid():
    result = label()
    result["evidence_quote"] = "Smoke" * 40
    assert validate_label(result, result["evidence_quote"])["evidence_quote"] == result["evidence_quote"]

def test_diagnostic_run_cap_preserves_cohort_resume_and_usage(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/LLM_PROMPTS.md").write_text("### system\n```\nLabel the complaint.\n```", encoding="utf-8")
    calls = []
    rejected = "Unvalidated private invented quotation"
    async def create(**kwargs):
        calls.append(kwargs)
        result = label()
        if len(calls) == 1:
            result["evidence_quote"] = rejected
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=100, completion_tokens=50, prompt_tokens_details=None),
            choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(refusal=None, content=json.dumps(result)))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    rows = [{"odino": str(i), "text": TEXT} for i in range(7)]
    first = asyncio.run(label_rows(rows, root=tmp_path, client=client, limit=3, max_attempts=1, max_new_rows=1))
    assert len(calls) == 1 and first["cohort_size"] == first["cohort_pending"] == 3
    assert first["selected"] == 3 and first["not_started"] == 2 and first["failed"] == 1
    assert not first["cohort_complete"] and first["estimated_population_usd"] is None
    failures = read_cache(tmp_path / "data/labels/llm_failures.jsonl")
    diagnostic = failures[0]["quote_diagnostics"][0]
    usage = read_cache(tmp_path / "data/labels/llm_usage.jsonl")
    assert diagnostic["cache_key"] == usage[0]["cache_key"]
    assert diagnostic["run_id"] == usage[0]["run_id"] and diagnostic["length"] == len(rejected)
    assert all(rejected not in path.read_text() for path in tmp_path.rglob("*.json*"))
    second = asyncio.run(label_rows(rows, root=tmp_path, client=client, limit=3, max_attempts=1, max_new_rows=1))
    assert len(calls) == 2 and second["completed"] == 1 and second["cohort_pending"] == 2
    third = asyncio.run(label_rows(rows, root=tmp_path, client=client, limit=3, max_attempts=1))
    assert third["cache_reused"] == 1 and third["completed"] == 2 and third["cohort_complete"]
    assert third["cohort_completed"] == 3 and len(calls) == 4
    cached = read_cache(tmp_path / "data/labels/labels_llm.jsonl")
    assert {r["odino"] for r in cached} == set(first["resume_odinos"])
    assert len(read_cache(tmp_path / "data/labels/llm_usage.jsonl")) == 4

def test_diagnostic_run_cap_rejects_zero_before_api(tmp_path):
    with pytest.raises(ValueError, match="max_new_rows"):
        asyncio.run(label_rows([], root=tmp_path, max_new_rows=0))
