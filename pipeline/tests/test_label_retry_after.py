"""Fixed authorized cohorts and server cooldowns; all API responses are mocked."""
import asyncio
from datetime import datetime, timezone
from email.utils import format_datetime
import json
from types import SimpleNamespace

from openai import RateLimitError
import pytest

from es.label_llm import (
    MODEL, cooldown_path, digest, label_rows, parse_retry_after, read_cache,
)

TEXT = "Smoke appeared while driving the vehicle on the road."

def root_setup(root):
    (root / "docs").mkdir()
    (root / "docs/LLM_PROMPTS.md").write_text("### system\n```\nLabel the complaint.\n```\n")

def limited(retry_after):
    response = SimpleNamespace(status_code=429, request=SimpleNamespace(), headers={"retry-after": retry_after})
    return RateLimitError("private response message", response=response, body={"type": "rate_limit_exceeded"})

def success():
    label = {"primary_category": "fire_thermal", "secondary_categories": [],
             "hazards": {key: key in {"smoke", "while_driving"} for key in
                         ("fire", "smoke", "crash", "injury", "while_driving", "while_parked_or_charging")},
             "severity": 2, "evidence_quote": TEXT, "summary_ko": "주행 중 연기 발생"}
    return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10, completion_tokens=10, prompt_tokens_details=None),
                           choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(refusal=None, content=json.dumps(label)))])

def client_for(create, key="synthetic-key-DO-NOT-LOG"):
    return SimpleNamespace(api_key=key, chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

@pytest.mark.parametrize("value, expected", [("1728", 1728), ("0", 0), ("-1", 0), ("2.5", 2.5),
                                             ("not-a-delay", None), ("nan", None), ("inf", None), (None, None)])
def test_retry_after_seconds_and_invalid_values(value, expected):
    assert parse_retry_after(value, now=100) == expected

def test_retry_after_http_date():
    now = datetime(2026, 10, 9, 1, 0, tzinfo=timezone.utc).timestamp()
    header = format_datetime(datetime.fromtimestamp(now + 1728, timezone.utc), usegmt=True)
    assert parse_retry_after(header, now=now) == 1728
    assert parse_retry_after(header, now=now + 1800) == 0

def test_partial_cohort_resume_never_spills_past_original_limit(tmp_path):
    root_setup(tmp_path)
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise limited(None)
        return success()
    rows = [{"odino": str(i), "text": TEXT} for i in range(7)]
    client = client_for(create)
    first = asyncio.run(label_rows(rows, root=tmp_path, client=client, limit=3, concurrency=1, max_attempts=1))
    assert first["completed"] == 2 and first["cohort_pending"] == 1
    assert first["estimated_population_usd"] is None and first["estimated_remaining_seconds"] is None
    assert first["cost_per_1k_usd"] is None
    second = asyncio.run(label_rows(rows, root=tmp_path, client=client, limit=3, concurrency=1))
    expected_ids = {row["odino"] for row in sorted(rows, key=lambda row: digest("seed42:" + row["odino"]))[:3]}
    cached = read_cache(tmp_path / "data/labels/labels_llm.jsonl")
    assert {record["odino"] for record in cached} == expected_ids
    assert len(calls) == 4 and second["completed"] == 1 and second["cache_reused"] == 2
    assert second["cohort_complete"] and second["cohort_completed"] == 3
    # Cached records outside a smaller requested cohort cannot inflate reuse counts.
    third = asyncio.run(label_rows(rows, root=tmp_path, client=client, limit=1))
    assert third["cache_reused"] == third["cohort_completed"] == 1 and len(calls) == 4

def test_long_delay_stops_pending_and_blocks_same_key_until_expiry(tmp_path, monkeypatch):
    root_setup(tmp_path)
    clock = [1000.0]
    monkeypatch.setattr("es.label_llm.time.time", lambda: clock[0])
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        raise limited("1728")
    client = client_for(create)
    rows = [{"odino": str(i), "text": TEXT} for i in range(50)]
    first = asyncio.run(label_rows(rows, root=tmp_path, client=client, concurrency=1))
    assert len(calls) == 1 and first["not_started"] == 49
    assert first["defer_reason"] == "server_retry_after_exceeds_60s" and first["retry_attempts"] == 0
    assert first["cohort_pending"] == 50 and first["estimated_population_usd"] is None
    state_path = cooldown_path(tmp_path, client.api_key, MODEL)
    state = json.loads(state_path.read_text())
    assert state["not_before_epoch"] == 2728.0
    assert state_path.stat().st_mode & 0o777 == 0o600
    all_files = "\n".join(path.read_text() for path in tmp_path.rglob("*") if path.is_file())
    assert client.api_key not in all_files and "private response message" not in all_files
    second = asyncio.run(label_rows(rows, root=tmp_path, client=client, concurrency=1))
    assert len(calls) == 1 and second["not_started"] == 50
    assert second["defer_reason"] == "local_server_cooldown" and second["failed"] == 0
    async def create_ok(**kwargs):
        calls.append(kwargs)
        return success()
    other = asyncio.run(label_rows(rows, root=tmp_path, client=client_for(create_ok, key="different-synthetic-key"), limit=1, concurrency=1))
    assert other["completed"] == 1 and len(calls) == 2
    assert cooldown_path(tmp_path, client.api_key, MODEL) != cooldown_path(tmp_path, client.api_key, "other-model")
    # Same identity resumes only after the recorded server deadline.
    clock[0] = 2728.0
    third = asyncio.run(label_rows(rows, root=tmp_path, client=client_for(create_ok), limit=2, concurrency=1))
    assert third["completed"] == 1 and third["cache_reused"] == 1 and len(calls) == 3

def test_long_delay_preserves_in_flight_results_but_stops_queue(tmp_path):
    root_setup(tmp_path)
    calls = []
    async def run():
        started = asyncio.Event()
        rejected = asyncio.Event()
        async def create(**kwargs):
            calls.append(kwargs)
            nth = len(calls)
            if nth == 3:
                started.set()
            await started.wait()
            if nth == 1:
                rejected.set()
                raise limited("1728")
            await rejected.wait()
            return success()
        return await label_rows([{"odino": str(i), "text": TEXT} for i in range(50)],
                                root=tmp_path, client=client_for(create), concurrency=3)
    result = asyncio.run(run())
    assert len(calls) == 3 and result["completed"] == 2 and result["failed"] == 1
    assert result["not_started"] == 47 and result["cohort_pending"] == 48
    assert result["estimated_population_usd"] is None

@pytest.mark.parametrize("delay", [2.0, 60.0])
def test_short_server_delay_is_shared_with_queued_work(tmp_path, monkeypatch, delay):
    root_setup(tmp_path)
    clock, sleeps, calls = [100.0], [], []
    monkeypatch.setattr("es.label_llm.time.monotonic", lambda: clock[0])
    async def fake_sleep(seconds):
        sleeps.append(seconds)
        clock[0] += seconds
    monkeypatch.setattr("es.label_llm.asyncio.sleep", fake_sleep)
    async def create(**kwargs):
        calls.append(clock[0])
        if len(calls) == 1:
            raise limited(str(delay))
        return success()
    # First record has no retries left; the next queued record still waits.
    result = asyncio.run(label_rows([{"odino": "1", "text": TEXT}, {"odino": "2", "text": TEXT}],
                                    root=tmp_path, client=client_for(create), concurrency=1, max_attempts=1))
    assert calls == [100.0, 100.0 + delay] and sleeps == [delay]
    assert result["completed"] == 1 and result["failed"] == 1 and not result["stopped_for_api_error"]
    assert not (tmp_path / "data/private").exists()
