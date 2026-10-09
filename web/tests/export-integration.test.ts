import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { availableDate, evidenceKey, getAsOf } from "../lib/asof";
import { createRequest } from "../lib/request";
import type { ConsoleData } from "../lib/types";

// Check the actual exported product boundary, independently of the synthetic fixtures.
const data = JSON.parse(readFileSync(new URL("../public/data/console.json", import.meta.url), "utf8")) as ConsoleData;

test("all exported alert cells produce a traceable request without excluded evidence", () => {
  const documentIds = new Set<string>();
  let count = 0;
  for (const month of data.asof_months) {
    const asof = getAsOf(data, month);
    assert.ok(Object.values(asof.series).every(series => series.months.every(value => value <= month)));
    assert.ok(asof.complaints.every(row => row.ldate >= month && row.ldate < availableDate(month)));
    for (const alert of asof.snapshot.alerts) {
      const evidence = data.evidence[evidenceKey(alert.grp, alert.category, month)];
      const excluded = [evidence.ids[evidence.ids.length - 1]];
      const request = createRequest({ data, month, grp: alert.grp, category: alert.category, cited: [], excluded,
        decision: "보류", savedAt: "2026-10-09T04:30:00.000Z" });
      assert.equal((request.markdown.match(/^## [1-7]\. /gm) ?? []).length, 7);
      assert.ok(request.markdown.includes(`이번 달 ${evidence.ids.length}건`));
      assert.ok(request.markdown.includes(`평소 ${alert.baseline.toFixed(2)}건`));
      assert.equal(request.record?.analysis_available, availableDate(month));
      assert.equal(request.record?.made, "2026-10-09T04:30:00.000Z");
      const citations = [...request.markdown.matchAll(/#(\d+)\b/g)].map(match => match[1]);
      assert.ok(citations.length > 0);
      assert.ok(citations.every(id => evidence.ids.includes(id) && !excluded.includes(id)));
      assert.ok(!documentIds.has(request.docNo), `Duplicate document identifier: ${request.docNo}`);
      documentIds.add(request.docNo);
      count += 1;
    }
  }
  assert.ok(count > 0, "The exported dataset must contain at least one reviewable alert");
});
