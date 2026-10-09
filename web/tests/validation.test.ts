import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { InvestigationComparison, SourceAttribution, Validation } from "../components/workspace";
import type { CasesData, LabelSource, MetaData, RevealCase } from "../lib/types";

const meta = JSON.parse(readFileSync(new URL("../public/data/meta.json", import.meta.url), "utf8")) as MetaData;
const cases = JSON.parse(readFileSync(new URL("../public/data/cases.json", import.meta.url), "utf8")) as CasesData;

function renderValidation(labeler: LabelSource, value: MetaData) {
  return renderToStaticMarkup(createElement("main", null,
    createElement(Validation, { meta: value, cases }),
    createElement(SourceAttribution, { view: "validation", labeler }),
  ));
}

for (const labeler of ["keyword", "llm"] as const) {
  test(`registered case/control results retain keyword attribution with ${labeler} console`, () => {
    const value = structuredClone(meta);
    // Synthetic model metadata; never exported as product data.
    value.labels = { ...value.labels, llm_model: "synthetic-model", llm_labeled: 7502,
      human_check: { n: 0, kw_correct: null, llm_correct: null } };
    const html = renderValidation(labeler, value);
    assert.match(html, /사례·대조의 백테스트와.*키워드 기준선 결과입니다/);
    assert.match(html, /지정 예비조사\(PE\) 사례/);
    assert.match(html, /지정 PE 개시 대비/);
    assert.match(html, /PE19003·PE19004: 이전 청원·리콜 조사가 있었으며 최초 발견 시점과의 비교는 아닙니다/);
    assert.match(html, /백테스트 출처: 키워드 기준선/);
    assert.doesNotMatch(html, /LLM 분류 기준|백테스트 출처:.*LLM|콘솔 분류 출처:/);
    assert.match(html, /7,502/);
    assert.match(html, /사람 정답 기준 분류 정확도:.*미측정/);
    for (const item of cases.cases) assert.ok(html.includes(item.case_id));
    for (const split of ["dev", "holdout"] as const) {
      for (const kind of ["case", "control"] as const) {
        const metric = value.validation[split][kind];
        assert.ok(html.includes(`${metric.hits}<small> / ${metric.n}</small>`));
      }
    }
  });
}

test("unrun LLM and absent human gold remain unmeasured rather than a zero accuracy", () => {
  const value = structuredClone(meta);
  value.labels = { ...value.labels, llm_model: null, llm_labeled: 0,
    human_check: { n: 0, kw_correct: 0, llm_correct: 0 }, cost_per_1k_usd: null };
  const html = renderValidation("keyword", value);
  assert.match(html, /모델: 미실행/);
  assert.match(html, /사람 정답 검수: 0건/);
  assert.match(html, /사람 정답 기준 분류 정확도:.*미측정/);
  assert.match(html, /1,000건 라벨 비용:.*미측정/);
  assert.doesNotMatch(html, /0 \/ 0건 일치/);
});

test("request workflow footer continues to describe its actual console classification", () => {
  const llm = renderToStaticMarkup(createElement(SourceAttribution, { view: "request", labeler: "llm" }));
  const keyword = renderToStaticMarkup(createElement(SourceAttribution, { view: "signals", labeler: "keyword" }));
  assert.equal(llm, "콘솔 분류 출처: 사전 실행 LLM");
  assert.equal(keyword, "콘솔 분류 출처: 키워드 규칙");
});

for (const [caseId, available, days] of [
  ["PE19003", "2018-09-01", 209],
  ["PE19004", "2018-08-01", 240],
] as const) {
  test(`${caseId} comparison identifies the designated PE rather than first discovery`, () => {
    // Only the saved comparison needs this synthetic, non-exported investigation.
    const investigation: RevealCase = {
      case_id: caseId, make: "synthetic", title: "synthetic",
      odate: "2019-03-29", first_alert_month: null, first_alert_grp: null,
      first_alert_category: null, available: null, lead_days: null,
    };
    const html = renderToStaticMarkup(createElement(InvestigationComparison, { available, investigation }));
    assert.match(html, new RegExp(`지정 예비조사\\(PE\\) 개시 · ${caseId}`));
    assert.ok(html.includes(`<b>${days}</b>`));
    assert.match(html, /지정 PE 개시 이전/);
    assert.match(html, /이전 청원·리콜 조사가 있었으며 최초 발견 시점과의 비교는 아닙니다/);
    assert.doesNotMatch(html, /NHTSA 공식 조사 개시|최초 발견보다|최초 조사보다/);

    const lateHtml = renderToStaticMarkup(createElement(InvestigationComparison, {
      available: "2019-04-01", investigation,
    }));
    assert.ok(lateHtml.includes("<b>3</b>"));
    assert.match(lateHtml, /지정 PE 개시 이후/);
  });
}

test("no linked PE means no lead claim and known context is not generalized to other PEs", () => {
  const missing = renderToStaticMarkup(createElement(InvestigationComparison, {
    available: "2018-09-01", investigation: undefined,
  }));
  assert.match(missing, /이 신호에 연결된 예비조사 사례가 없습니다/);
  assert.doesNotMatch(missing, /lead-result|지정 PE 개시 이전|이전 청원·리콜 조사/);
  const other: RevealCase = {
    case_id: "PE20016", make: "synthetic", title: "synthetic", odate: "2020-10-09",
    first_alert_month: null, first_alert_grp: null, first_alert_category: null,
    available: null, lead_days: null,
  };
  const html = renderToStaticMarkup(createElement(InvestigationComparison, {
    available: "2020-10-01", investigation: other,
  }));
  assert.match(html, /지정 예비조사\(PE\) 개시 · PE20016/);
  assert.doesNotMatch(html, /이전 청원·리콜 조사/);
});
