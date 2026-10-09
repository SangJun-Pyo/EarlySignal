"""Offline safety tests. Synthetic data is not a quality or accuracy measure."""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
try:
    import httpx2 as httpx
except ImportError:
    import httpx
from openai import RateLimitError
import pytest
from es.brief import (alert_cells, generate_briefs, load_validated_briefs, load_public_console,
                      compose_brief, prepare_cell, CACHE_VERSION)
from es.config import DEMO_GROUPS, Config
from es.export import MONTHS, FLAGS


@pytest.fixture
def root(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/LLM_PROMPTS.md").write_text(
        "## 2. 경보 브리프\n### system\n```\n제공 근거만 사용한다.\n```\n## 3. 요청서\n")
    return tmp_path


def console(n=12, extra_cell=True):
    grp = "HYUNDAI|SONATA"
    complaints = {str(1000 + i): {"grp": grp, "month": "2018-08-01", "ldate": "2018-08-10",
        "categories": ["fire_thermal"], "flags": ["smoke"] if i < n - 1 else ["fire", "severe"],
        "summary_ko": "연기가 발생했다고 신고", "label_source": "llm", "year": "2013",
        "severity": 3 if i == n - 1 else 2, "injured": 0, "text": "PRIVATE RAW TEXT NEVER SEND"} for i in range(n)}
    ids = list(complaints)
    ev = {"n": n, "ids": ids, "agg": {f: sum(f in c["flags"] for c in complaints.values()) for f in FLAGS}, "co": [], "years": [["2013", n]]}
    alert = {"grp": grp, "category": "fire_thermal", "n": n, "baseline": 1.0,
             "ratio": float(n), "streak": 1, "p_value": 1e-8, "is_new": True, "comove": []}
    snapshots = {m: {"alerts": [], "kpi": {k: 0 for k in ("complaints", "complaints_prev", "alerts", "alerts_prev", "fire_alert_models")}} for m in MONTHS}
    snapshots["2018-08-01"]["alerts"] = [alert]
    evidence = {f"{grp}:fire_thermal:2018-08-01": ev}
    if extra_cell:
        for i in (2000, 2001, 2002):
            complaints[str(i)] = {**complaints["1000"], "grp": "KIA|SOUL"}
        snapshots["2018-08-01"]["alerts"].append({**alert, "grp": "KIA|SOUL", "n": 3, "ratio": 3.0})
        evidence["KIA|SOUL:fire_thermal:2018-08-01"] = {**ev, "n": 3, "ids": ["2000", "2001", "2002"]}
    return {"contract": "earlysignal-data-v1", "labeler": "llm", "labeling_note": "Synthetic test",
        "flag_sources": {f: "LLM" for f in FLAGS}, "complaints": complaints, "evidence": evidence,
        "asof_months": MONTHS, "snapshots": snapshots, "demo_signal": {"grp": grp, "category": "fire_thermal", "month": "2018-08-01"},
        "default_asof": "2018-08-01", "groups": list(DEMO_GROUPS), "categories": ["fire_thermal"],
        "series": {}, "reveal": {"cases": [], "series_after": {}}, "pile": {}, "briefs": {}, "sources": [], "assumptions": []}


class Client:
    def __init__(self, outputs):
        self.outputs = iter(outputs)
        self.calls = []
        self.chat = SimpleNamespace(completions=self)

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        value = next(self.outputs)
        if isinstance(value, Exception):
            raise value
        content = value if isinstance(value, str) else json.dumps(value)
        return SimpleNamespace(usage=SimpleNamespace(prompt_tokens=100, completion_tokens=20, prompt_tokens_details=None),
            choices=[SimpleNamespace(finish_reason="stop", message=SimpleNamespace(content=content, refusal=None))])


def invoke(c, root, client, **kwargs):
    return asyncio.run(generate_briefs(c, root=root, client=client, **kwargs))


def test_payload_is_whitelisted_ten_same_cell_reports_and_cache_is_fixed_cohort(root, monkeypatch):
    monkeypatch.setattr("es.brief.os.getenv", lambda *args: (_ for _ in ()).throw(AssertionError("No env read with injected client")))
    c = console()
    client = Client([{"narrative": "연기가 발생했다는 신고가 있습니다(#1000)."}])
    result = invoke(c, root, client, limit=1)
    payload = json.loads(client.calls[0]["messages"][1]["content"])
    assert set(payload) == {"statistics", "evidence"}
    assert len(payload["evidence"]) == 10 and payload["evidence"][0]["odino"] == "1011"
    assert all(set(e) == {"odino", "summary_ko", "flags"} for e in payload["evidence"])
    assert "PRIVATE" not in json.dumps(client.calls) and "2000" not in json.dumps(payload)
    assert client.calls[0]["response_format"]["json_schema"]["strict"] is True
    assert result["completed"] == 1 and result["population"] == 2
    # Repeating the same limit cannot reach the second cell after a cache hit.
    second = Client([])
    resumed = invoke(c, root, second, limit=1)
    assert second.calls == [] and resumed["cache_reused"] == 1 and resumed["selected"] == 0
    assert result["estimated_usd"] > 0 and result["extrapolation_eligible"] is False
    assert result["estimated_population_usd"] is None and result["cost_per_1k_usd"] is None


@pytest.mark.parametrize("mutation,error", [("keyword", "complete_llm_console"), ("mixed", "complete_llm_complaints"),
    ("missing_summary", "complete_llm_complaints"), ("future", "future_evidence"),
    ("other_group", "scope_mismatch"), ("counts", "count_mismatch"), ("ratio", "invalid_statistics")])
def test_invalid_input_refuses_before_any_api_or_output(root, mutation, error):
    c = console()
    if mutation == "keyword": c["labeler"] = "keyword"
    elif mutation == "mixed": c["complaints"]["1000"]["label_source"] = "keyword"
    elif mutation == "missing_summary": c["complaints"]["1000"]["summary_ko"] = None
    elif mutation == "future": c["complaints"]["1000"]["ldate"] = "2018-09-01"
    elif mutation == "other_group": c["complaints"]["1000"]["grp"] = "KIA|SOUL"
    elif mutation == "counts": c["evidence"][next(iter(c["evidence"]))]["n"] += 1
    else: c["snapshots"]["2018-08-01"]["alerts"][0]["ratio"] = 99
    client = Client([])
    with pytest.raises(ValueError, match=error): invoke(c, root, client)
    assert client.calls == [] and not (root / "data").exists()


@pytest.mark.parametrize("bad", ["연기가 발생했습니다(#9999).", "연기가 발생했습니다(#1010).", "부상 2명(#1000).",
    "연기가 발생했습니다(#1000). 화재가 반복됐습니다.", "결함이 확정됐습니다(#1000).",
    "연기가 발생했습니다(#1000). Contact a@example.com(#1000)."])
def test_invalid_narrative_regenerates_twice_then_leaves_no_public_brief(root, monkeypatch, bad):
    monkeypatch.setattr("es.brief.asyncio.sleep", lambda _: async_noop())
    c = console()
    client = Client([{"narrative": bad}] * 3)
    result = invoke(c, root, client)
    assert len(client.calls) == 3 and result["failed"] == 1 and result["completed"] == 0
    assert load_validated_briefs(c, root=root) == {}
    assert result["api_responses"] == 3 and result["prompt_tokens"] == 300
    assert result["estimated_population_usd"] is None and result["cohort_complete"] is False
    failure = json.loads((root / "data/labels/brief_failures.jsonl").read_text())
    assert failure["attempts"] == 3 and bad not in (root / "data/labels/brief_failures.jsonl").read_text()


async def async_noop(): pass


def test_invalid_then_valid_success_keeps_usage_of_failed_attempt(root, monkeypatch):
    monkeypatch.setattr("es.brief.asyncio.sleep", lambda _: async_noop())
    client = Client([{"narrative": "연기가 발생했습니다(#9999)."}, {"narrative": "연기가 발생했습니다(#1000)."}])
    c = console(); result = invoke(c, root, client)
    assert result["completed"] == 1 and result["api_responses"] == 2
    assert len(load_validated_briefs(c, root=root)) == 1
    records = json.loads((root / "data/labels/briefs.json").read_text())["records"]
    assert next(iter(records.values()))["prior_errors"] == ["outside_evidence_citation"]
    c["complaints"]["1000"]["summary_ko"] = "주차 중 연기 발생"
    assert load_validated_briefs(c, root=root) == {}


def rate_error(code="rate_limit_exceeded", retry_after=None):
    headers = {"Retry-After": retry_after} if retry_after is not None else {}
    response = httpx.Response(429, request=httpx.Request("POST", "https://example.invalid"), headers=headers)
    return RateLimitError("DO NOT LOG API BODY", response=response, body={"error": {"code": code}})


def test_quota_stops_remaining_cells_and_does_not_extrapolate(root):
    client = Client([rate_error("insufficient_quota")])
    result = invoke(console(), root, client, limit=2)
    assert len(client.calls) == 1 and result["defer_reason"] == "quota_exhausted"
    assert result["not_started"] == 1 and result["api_responses"] == 0 and result["estimated_usd"] is None
    assert result["extrapolation_eligible"] is False
    assert "DO NOT LOG" not in (root / "data/labels/brief_failures.jsonl").read_text()


def test_long_server_wait_is_persisted_and_followup_makes_no_call(root):
    client = Client([rate_error(retry_after="1728")])
    result = invoke(console(), root, client, limit=2)
    assert len(client.calls) == 1 and result["defer_reason"] == "server_retry_after_exceeds_60s"
    second = Client([])
    resume = invoke(console(), root, second, limit=2)
    assert second.calls == [] and resume["defer_reason"] == "local_server_cooldown"
    assert resume["not_started"] == 2 and resume["retry_not_before"]


def test_short_server_wait_is_honored(root, monkeypatch):
    waits = []
    async def sleep(seconds): waits.append(seconds)
    monkeypatch.setattr("es.brief.asyncio.sleep", sleep)
    client = Client([rate_error(retry_after="2"), {"narrative": "연기가 발생했습니다(#1000)."}])
    assert invoke(console(), root, client)["completed"] == 1
    assert waits == [2.0] and len(client.calls) == 2


def test_known_private_values_are_checked_in_input_output_and_cache(root, monkeypatch):
    c = console(); denied = {"1000": ["Exampleville"]}
    client = Client([{"narrative": "Exampleville에서 연기가 발생했습니다(#1000)."}])
    result = invoke(c, root, client, denied_by_id=denied, max_retries=0)
    assert result["failed"] == 1
    assert "Exampleville" not in (root / "data/labels/brief_failures.jsonl").read_text()
    c["complaints"]["1000"]["summary_ko"] = "Exampleville에서 연기 발생"
    with pytest.raises(ValueError, match="sensitive_brief_input"):
        invoke(c, root, Client([]), denied_by_id=denied)


def test_cache_model_prompt_statistics_and_tampering_invalidate(root):
    c = console(); invoke(c, root, Client([{"narrative": "연기가 발생했습니다(#1000)."}]))
    assert len(load_validated_briefs(c, root=root)) == 1
    assert load_validated_briefs(c, root=root, model="different-model") == {}
    changed = copy.deepcopy(c); changed["snapshots"]["2018-08-01"]["alerts"][0]["streak"] = 2
    assert load_validated_briefs(changed, root=root) == {}
    path = root / "data/labels/briefs.json"; cache = json.loads(path.read_text())
    next(iter(cache["records"].values()))["brief"] += " 부상 2명(#1000)."
    path.write_text(json.dumps(cache))
    assert load_validated_briefs(c, root=root) == {}


def write_export(root, c):
    path = root / "console.json"; path.write_text(json.dumps(c))
    other = root / "meta.json"; other.write_text('{}')
    manifest = {"contract": "earlysignal-data-v1", "status": "complete", "labeler": "llm",
        "files": ["console.json", "meta.json"], "file_sha256": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (path, other)},
        "complaints": len(c["complaints"]), "evidence_cells": len(c["evidence"]), "briefs": 0,
        "console_months": len(MONTHS), "console_groups": len(DEMO_GROUPS), "cases": 0}
    (root / "completion.json").write_text(json.dumps(manifest))
    return path, manifest


def test_completed_public_export_checks_all_files_counts_and_true_label_sources(root):
    c = console(extra_cell=False); path, manifest = write_export(root, c)
    assert load_public_console(path)["labeler"] == "llm"
    (root / "meta.json").write_text('modified')
    with pytest.raises(ValueError, match="export_hash_mismatch"): load_public_console(path)
    path, manifest = write_export(root, c); manifest["complaints"] += 1
    (root / "completion.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="export_count_mismatch"): load_public_console(path)
    c["complaints"]["1000"]["label_source"] = "keyword"; path, _ = write_export(root, c)
    with pytest.raises(ValueError, match="complete_llm_complaints"): load_public_console(path)


def test_manifest_missing_status_or_path_escape_cannot_be_used(root):
    c = console(extra_cell=False); path, manifest = write_export(root, c)
    manifest["files"].append("../escape.json"); manifest["file_sha256"]["../escape.json"] = "a" * 64
    (root / "completion.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="invalid_manifest_file"): load_public_console(path)


def test_cli_has_conservative_limit_and_routes_without_generating(root, monkeypatch, capsys):
    from es.cli import main
    calls = []
    monkeypatch.setattr("es.cli.load_dotenv", lambda *a: None)
    monkeypatch.setattr("es.brief.run_briefs", lambda config, **kwargs: calls.append(kwargs) or {"completed": 0})
    main(["--root", str(root), "briefs", "--console", str(root / "console.json")])
    assert calls[0]["limit"] == 1 and calls[0]["console_path"] == root / "console.json"
    assert json.loads(capsys.readouterr().out)["completed"] == 0


def test_exhausted_retry_still_waits_before_next_cell(root, monkeypatch):
    waits=[]
    async def sleep(seconds): waits.append(seconds)
    monkeypatch.setattr("es.brief.asyncio.sleep",sleep)
    client=Client([rate_error(retry_after="2"),{"narrative":"연기가 발생했습니다(#2000)."}])
    result=invoke(console(),root,client,limit=2,max_retries=0)
    assert len(client.calls)==2 and waits==[2.0]
    assert result["failed"]==1 and result["completed"]==1 and result["defer_reason"] is None


def test_manifest_cannot_omit_existing_result_file(root):
    path,manifest=write_export(root,console(extra_cell=False))
    manifest["files"].remove("meta.json");manifest["file_sha256"].pop("meta.json")
    (root/"completion.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match="incomplete_export_manifest"):load_public_console(path)


def test_cache_prompt_changes_invalidate(root):
    c=console();invoke(c,root,Client([{"narrative":"연기가 발생했습니다(#1000)."}]))
    (root/"docs/LLM_PROMPTS.md").write_text("## 2. 경보\n### system\n```\nChanged prompt.\n```\n## 3. 요청서\n")
    assert load_validated_briefs(c,root=root)=={}


@pytest.mark.parametrize("limit,retries",[(0,2),(1,3),(True,2),(1,-1)])
def test_call_bounds_reject_bad_limits_and_retry_budgets(root,limit,retries):
    client=Client([])
    with pytest.raises(ValueError,match="limit must"):
        invoke(console(),root,client,limit=limit,max_retries=retries)
    assert client.calls==[]


@pytest.mark.parametrize("stop",[".","!","?","。","！","？","｡"])
def test_every_unspaced_sentence_requires_its_own_citation(root,stop):
    c=console();cell=alert_cells(c)[0]
    bad=f"연기가 발생했습니다(#1000){stop}주차 중 화재가 발생했습니다."
    with pytest.raises(ValueError,match="uncited_narrative"):
        compose_brief(bad,cell["evidence"],c["complaints"],grp=cell["grp"],category=cell["category"],month=cell["month"],expected_counts=cell["counts"])
    client=Client([{"narrative":bad}])
    assert invoke(c,root,client,max_retries=0)["failed"]==1
    assert load_validated_briefs(c,root=root)=={}


@pytest.mark.parametrize("narrative",[
    "연기가 발생했습니다(#1000).주행 중 신고도 있습니다(#1001).",
    "연기가 발생했습니다(#1000)！주행 중 신고도 있습니다(#1001)。",
    "U.S. 신고에 연기가 언급됐습니다(#1000, #1001).",
    "e.g.라는 표현과 연기가 신고에 언급됐습니다(#1000).",
    '“연기가 발생했습니다(#1000).”',
])
def test_sentence_checks_preserve_initialisms_words_and_citation_groups(root,narrative):
    c=console();cell=alert_cells(c)[0]
    text=compose_brief(narrative,cell["evidence"],c["complaints"],grp=cell["grp"],category=cell["category"],month=cell["month"],expected_counts=cell["counts"])
    assert text.endswith(narrative)


@pytest.mark.parametrize("quantity",["열한 명","십 명","한 사람","스물세명","서른 두 사람","삼십 명","백여 명","수십 명","한두 사람"])
def test_korean_compound_and_sino_quantities_are_never_prose_metrics(root,quantity):
    c=console();cell=alert_cells(c)[0]
    bad=f"부상 {quantity}(#1000)."
    with pytest.raises(ValueError,match="unsupported_narrative_number"):
        compose_brief(bad,cell["evidence"],c["complaints"],grp=cell["grp"],category=cell["category"],month=cell["month"],expected_counts=cell["counts"])
    assert invoke(c,root,Client([{"narrative":bad}]),max_retries=0)["failed"]==1


def test_severity_one_and_two_rank_by_value_after_fire_injury_crash(root):
    c=console(extra_cell=False)
    for item in c["complaints"].values():item.update(flags=["smoke"],severity=1)
    c["complaints"]["1011"]["severity"]=2
    payload,_,_=prepare_cell(alert_cells(c)[0],c["complaints"])
    ids=[row["odino"] for row in payload["evidence"]]
    assert len(ids)==10 and ids[0]=="1011" and "1010" not in ids
    c["complaints"]["1000"]["flags"]=["fire"]
    payload,_,_=prepare_cell(alert_cells(c)[0],c["complaints"])
    assert [row["odino"] for row in payload["evidence"]][:2]==["1000","1011"]


def test_invalid_unspaced_or_quantity_cache_is_omitted_by_export_loader(root):
    c=console();invoke(c,root,Client([{"narrative":"연기가 발생했습니다(#1000)."}]))
    path=root/"data/labels/briefs.json";base=json.loads(path.read_text())
    for append in ["주차 중 화재가 발생했습니다.","부상 열한 명(#1000)."]:
        modified=copy.deepcopy(base)
        next(iter(modified["records"].values()))["brief"]+=append
        path.write_text(json.dumps(modified))
        assert load_validated_briefs(c,root=root)=={}
