"""No real API calls: verify fatal quota stops queued work and retries."""
import asyncio
import json
from types import SimpleNamespace

from openai import RateLimitError
import pytest

from es.label_llm import label_rows

TEXT = "Smoke appeared while driving the vehicle on the road."

def setup_root(root):
    (root / "docs").mkdir()
    (root / "docs/LLM_PROMPTS.md").write_text("### system\n```\nLabel the complaint.\n```\n", encoding="utf-8")

def quota_error(body):
    # Only the error metadata is used; no network transport is constructed.
    response = SimpleNamespace(status_code=429, request=SimpleNamespace(), headers={})
    return RateLimitError("Simulated quota exhausted; private source must not be logged", response=response, body=body)

@pytest.mark.parametrize("body", [
    {"type": "insufficient_quota", "message": "Private source text"},
    {"error": {"code": "insufficient_quota", "message": "Private source text"}},
    {"error": {"code": "credit_balance_exhausted", "message": "Private source text"}},
])
def test_quota_error_stops_before_retry_or_next_complaint(tmp_path, body):
    setup_root(tmp_path)
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        raise quota_error(body)
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    rows = [{"odino": str(i), "text": TEXT} for i in range(50)]
    result = asyncio.run(label_rows(rows, root=tmp_path, client=client, concurrency=1))
    assert len(calls) == 1
    assert result["stopped_for_api_error"] is True
    assert result["completed"] == 0 and result["failed"] == 1
    assert result["retry_attempts"] == 0
    assert result["estimated_usd"] is None
    failures = (tmp_path / "data/labels/llm_failures.jsonl").read_text(encoding="utf-8")
    assert "quota_exhausted" in failures
    assert "Private source" not in failures

def test_quota_with_concurrency_does_not_start_queued_requests(tmp_path):
    setup_root(tmp_path)
    calls = []
    async def run():
        all_started = asyncio.Event()
        async def create(**kwargs):
            calls.append(kwargs)
            if len(calls) == 3:
                all_started.set()
            await all_started.wait()
            raise quota_error({"type": "insufficient_quota"})
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        return await label_rows([{"odino": str(i), "text": TEXT} for i in range(50)], root=tmp_path, client=client, concurrency=3)
    result = asyncio.run(run())
    assert len(calls) == 3  # Already in flight before the first rejection.
    assert result["stopped_for_api_error"] is True
    assert result["failed"] == 3 and result["retry_attempts"] == 0

def test_temporary_rate_limit_is_retried_without_fatal_stop(tmp_path, monkeypatch):
    setup_root(tmp_path)
    calls = []
    async def no_sleep(_):
        pass
    monkeypatch.setattr("es.label_llm.asyncio.sleep", no_sleep)
    async def create(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise quota_error({"type": "rate_limit_exceeded"})
        label = {"primary_category": "fire_thermal", "secondary_categories": [],
                 "hazards": {name: name in {"smoke", "while_driving"} for name in ("fire", "smoke", "crash", "injury", "while_driving", "while_parked_or_charging")},
                 "severity": 2, "evidence_quote": TEXT, "summary_ko": "주행 중 연기 발생"}
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=10, prompt_tokens_details=None),
            choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(refusal=None, content=json.dumps(label)))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    result = asyncio.run(label_rows([{"odino": "1", "text": TEXT}], root=tmp_path, client=client, concurrency=1))
    assert len(calls) == 2
    assert result["stopped_for_api_error"] is False and result["completed"] == 1
    assert result["retry_attempts"] == 1
