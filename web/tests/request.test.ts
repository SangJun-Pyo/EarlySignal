import assert from "node:assert/strict";
import test from "node:test";
import { createRequest } from "../lib/request";
import { addAlert, fixture, GROUP, IDS, input, KEY, MONTH } from "./fixtures";

test("draft has seven sections, traceable selected-month facts and no future series", () => {
  const data = fixture();
  const original = structuredClone(data);
  const result = createRequest(input(data));
  assert.equal((result.markdown.match(/^## [1-7]\. /gm) ?? []).length, 7);
  assert.match(result.markdown, /이번 달 3건/);
  assert.match(result.markdown, /2018-09-01/);
  assert.doesNotMatch(result.markdown, /999건/);
  assert.match(result.markdown, /키워드 분류/);
  assert.doesNotMatch(result.markdown, /AI 라벨|AI 작성/);
  assert.match(result.markdown, /## 3\. 대표 신고 요약\n이 경보의 대표 신고 요약은 없습니다/);
  assert.match(result.markdown, /알려진 식별정보를 가린 발췌/);
  assert.doesNotMatch(result.markdown, /AI 요약 인용·담당자 검토/);
  assert.equal(result.record, null);
  assert.match(result.markdown, /\(초안\)/);
  assert.deepEqual(data, original);
});

test("automatic suggestions are labeled and exclude rejected evidence", () => {
  const result = createRequest(input(undefined, { excluded: [IDS[0]] }));
  assert.equal(result.autoSuggested, true);
  assert.deepEqual(result.cited, IDS.slice(1));
  assert.match(result.markdown, /자동 제안/);
  assert.doesNotMatch(result.markdown, new RegExp(`#${IDS[0]}\\b`));
  assert.match(result.markdown, /통계·상황 집계는 최초 분류된 전체 근거 기준/);
});

test("explicit multiple citations deduplicate without becoming automatic suggestions", () => {
  const result = createRequest(input(undefined, { cited: [IDS[2], IDS[0], IDS[2]] }));
  assert.deepEqual(result.cited, [IDS[2], IDS[0]]);
  assert.equal(result.autoSuggested, false);
  assert.match(result.markdown, /담당자 인용/);
  assert.doesNotMatch(result.markdown, /자동 제안/);
});

test("invalid, contradictory and all-excluded selections cannot create a request", () => {
  for (const options of [
    { cited: ["99999999"] }, { excluded: ["99999999"] },
    { cited: [IDS[0]], excluded: [IDS[0]] }, { excluded: [...IDS] },
  ]) assert.throws(() => createRequest(input(undefined, options)));
  assert.throws(() => createRequest(input(undefined, { month: "2018-09-01" })));
  assert.throws(() => createRequest(input(undefined, { grp: "TEST|OTHER" })));
});

test("valid brief references are retained once alongside human citations", () => {
  const data = fixture();
  data.labeler = "llm";
  for (const row of Object.values(data.complaints)) {
    row.label_source = "llm";
    row.summary_ko = "연기가 발생했다는 신고";
  }
  data.briefs[KEY] = `(#${IDS[1]}, #${IDS[1]}) ${data.complaints[IDS[1]].summary_ko}`;
  const result = createRequest(input(data, { cited: [IDS[0]] }));
  assert.deepEqual(result.briefCited, [IDS[1]]);
  assert.equal(result.briefSuppressed, false);
  assert.match(result.markdown, /## 3\. 대표 신고 요약 \(AI 요약 인용·담당자 검토\)/);
  assert.ok(result.markdown.includes(data.briefs[KEY]));
  assert.match(result.markdown, /기존 신고별 AI 요약을 그대로 인용합니다\. 원문과의 의미 일치는 담당자가 확인해야 합니다/);
  assert.match(result.markdown, /대표 요약 인용/);
  assert.match(result.markdown, /AI 라벨/);
  assert.doesNotMatch(result.markdown, /AI 작성|종합/);
});

test("one excluded or unknown brief citation suppresses the entire brief", () => {
  for (const text of [`연기(#${IDS[0]}, #${IDS[1]}).`, `연기(#${IDS[0]}, #99999999).`, "번호 없는 상황 설명"]) {
    const data = fixture();
    data.briefs[KEY] = text;
    const result = createRequest(input(data, { cited: [IDS[2]], excluded: [IDS[1]] }));
    assert.equal(result.briefSuppressed, true);
    assert.deepEqual(result.briefCited, []);
    assert.doesNotMatch(result.markdown, /AI 작성/);
    assert.doesNotMatch(result.markdown, /AI 요약 인용·담당자 검토/);
    assert.match(result.markdown, /대표 신고 요약을 사용하지 않았습니다/);
    assert.ok(!result.markdown.includes(text));
  }
});

test("malformed short citation cannot hide beside a valid brief reference", () => {
  const data = fixture();
  data.briefs[KEY] = `연기(#${IDS[0]}, #12).`;
  assert.equal(createRequest(input(data)).briefSuppressed, true);
});

test("evidence must match the selected group, category and actual receipt month", () => {
  for (const change of [
    { grp: "TEST|OTHER" }, { categories: ["brakes" as const] }, { month: "2018-09-01" },
    { ldate: "2018-09-01" }, { ldate: "2018-07-31" },
  ]) {
    const data = fixture();
    Object.assign(data.complaints[IDS[0]], change);
    assert.throws(() => createRequest(input(data)));
  }
});

test("duplicate or inconsistent evidence cannot become authoritative request counts", () => {
  for (const mutate of [
    (data: ReturnType<typeof fixture>) => { data.evidence[KEY].ids.push(IDS[0]); },
    (data: ReturnType<typeof fixture>) => { data.evidence[KEY].n = 99; },
    (data: ReturnType<typeof fixture>) => { data.snapshots[MONTH].alerts[0].n = 99; },
  ]) {
    const data = fixture(); mutate(data);
    assert.throws(() => createRequest(input(data)));
  }
});

test("saving keeps actual timestamp separate from historical availability and requires a decision", () => {
  const savedAt = "2026-10-09T04:30:00.000Z";
  const result = createRequest(input(undefined, { cited: [IDS[0]], decision: "보류", actions: ["다음 달 재검토", "다음 달 재검토"], savedAt }));
  assert.equal(result.record?.made, savedAt);
  assert.equal(result.record?.analysis_available, "2018-09-01");
  assert.deepEqual(result.record?.actions, ["다음 달 재검토"]);
  assert.match(result.markdown, /실제 저장 시각: 2026-10-09T04:30:00.000Z/);
  assert.match(result.markdown, /\(확정\)/);
  assert.throws(() => createRequest(input(undefined, { savedAt })));
  assert.throws(() => createRequest(input(undefined, { savedAt: "invalid", decision: "보류" })));
});

test("operator memo cannot cite nonexistent or excluded evidence", () => {
  assert.throws(() => createRequest(input(undefined, { memo: "재검토 #99999999" })));
  assert.throws(() => createRequest(input(undefined, { memo: `재검토 #${IDS[0]}`, excluded: [IDS[0]] })));
});

test("separate engine symptom selections get distinct document identifiers", () => {
  const data = fixture();
  addAlert(data, "engine_stall"); addAlert(data, "engine_failure");
  const stalled = createRequest(input(data, { category: "engine_stall" }));
  const failure = createRequest(input(data, { category: "engine_failure" }));
  assert.notEqual(stalled.docNo, failure.docNo);
  assert.equal(stalled.available, failure.available);
});

test("LLM summary supplements the cited original and retains its own provenance", () => {
  const data = fixture();
  data.labeler = "llm";
  data.complaints[IDS[0]].label_source = "llm";
  data.complaints[IDS[0]].summary_ko = "연기가 발생했다는 신고";
  const result = createRequest(input(data, { cited: [IDS[0]] }));
  assert.ok(result.markdown.includes(`원문 발췌: ${data.complaints[IDS[0]].text} [담당자 인용]`));
  assert.match(result.markdown, /AI 요약\(담당자 검토 필요\): 연기가 발생했다는 신고/);
  assert.doesNotMatch(result.markdown, /원문 발췌: 연기가 발생했다는 신고/);
  assert.match(result.markdown, /화재·충돌·부상은 NHTSA 기록 또는 AI 분류/);
});
