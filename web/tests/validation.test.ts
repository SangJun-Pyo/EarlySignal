import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { SourceAttribution, Validation } from "../components/workspace";
import type { CasesData, LabelSource, MetaData } from "../lib/types";

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
