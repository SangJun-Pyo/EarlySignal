import type { Category, Complaint, ConsoleData, Evidence } from "../lib/types";
import type { RequestInput } from "../lib/request";

// Synthetic fixtures exercise invariants; these are never exported as product data.
export const MONTH = "2018-08-01";
export const GROUP = "TEST|MODEL";
export const IDS = ["11111001", "11111002", "11111003"];
export const KEY = `${GROUP}:fire_thermal:${MONTH}`;

export function fixture(): ConsoleData {
  const complaints: Record<string, Complaint> = Object.fromEntries(IDS.map((id, i) => [id, {
    grp: GROUP, month: MONTH, ldate: `2018-08-0${i + 1}`, year: "2013",
    flags: ["smoke"], categories: ["fire_thermal"], severity: 2, injured: 0,
    summary_ko: null, text: `Smoke appeared in synthetic complaint ${i + 1}.`, label_source: "keyword",
  } satisfies Complaint]));
  const evidence: Evidence = { n: 3, agg: { fire: 0, smoke: 3, driving: 0, parked: 0, crash: 0, injury: 0, severe: 0 }, co: [], years: [["2013", 3]], ids: [...IDS] };
  return {
    contract: "earlysignal-data-v1", labeler: "keyword", labeling_note: "Synthetic keyword fixture",
    flag_sources: { fire: "NHTSA FIRE", crash: "NHTSA CRASH", injury: "NHTSA INJURED", smoke: "keyword", driving: "keyword", parked: "keyword", severe: "unmeasured" },
    asof_months: [MONTH, "2018-09-01"], default_asof: MONTH,
    demo_signal: { grp: GROUP, category: "fire_thermal", month: MONTH }, groups: [GROUP], categories: ["fire_thermal"],
    series: { [GROUP]: { months: ["2018-07-01", MONTH, "2018-09-01"], total: [1, 3, 999], categories: {
      fire_thermal: { n: [1, 3, 999], baseline: [0.5, 0.5, 0.5], alert: [false, true, true] },
    } } },
    snapshots: {
      [MONTH]: { kpi: { complaints: 3, complaints_prev: 1, alerts: 1, alerts_prev: 0, fire_alert_models: 1 }, alerts: [
        { grp: GROUP, category: "fire_thermal", n: 3, baseline: 0.5, ratio: 6, p_value: 0.00001, streak: 1, is_new: true, comove: [] },
      ] },
      "2018-09-01": { kpi: { complaints: 999, complaints_prev: 3, alerts: 0, alerts_prev: 1, fire_alert_models: 0 }, alerts: [] },
    },
    complaints, pile: { [MONTH]: [...IDS], "2018-09-01": [] }, evidence: { [KEY]: evidence }, briefs: {},
    reveal: { cases: [], series_after: {} }, sources: [{ name: "Test", status: "connected", count: 3 }], assumptions: [],
  };
}

export function input(data = fixture(), overrides: Partial<RequestInput> = {}): RequestInput {
  return { data, month: MONTH, grp: GROUP, category: "fire_thermal", cited: [], excluded: [], ...overrides };
}

export function addAlert(data: ConsoleData, category: Category): void {
  data.categories.push(category);
  data.snapshots[MONTH].alerts.push({ ...data.snapshots[MONTH].alerts[0], category });
  data.evidence[`${GROUP}:${category}:${MONTH}`] = structuredClone(data.evidence[KEY]);
  data.series[GROUP].categories[category] = structuredClone(data.series[GROUP].categories.fire_thermal!);
  for (const row of Object.values(data.complaints)) row.categories.push(category);
}
