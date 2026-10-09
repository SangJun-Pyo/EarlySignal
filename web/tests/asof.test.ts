import assert from "node:assert/strict";
import test from "node:test";
import { availableDate, getAsOf } from "../lib/asof";
import { fixture, GROUP, IDS, MONTH } from "./fixtures";

test("availability crosses December and leap February using UTC calendar months", () => {
  assert.equal(availableDate("2019-12-01"), "2020-01-01");
  assert.equal(availableDate("2020-02-01"), "2020-03-01");
  for (const value of ["2018-08-02", "2018-13-01", "2018-00-01", "2018-8-01", "invalid"]) {
    assert.throws(() => availableDate(value));
  }
});

test("selected month removes future values from every parallel series array", () => {
  const data = fixture();
  const original = structuredClone(data);
  const selected = getAsOf(data, MONTH);
  assert.deepEqual(selected.series[GROUP].months, ["2018-07-01", MONTH]);
  assert.deepEqual(selected.series[GROUP].total, [1, 3]);
  assert.deepEqual(selected.series[GROUP].categories.fire_thermal, { n: [1, 3], baseline: [0.5, 0.5], alert: [false, true] });
  assert.equal(selected.snapshot.kpi.complaints, 3);
  assert.deepEqual(selected.complaints.map(row => row.odino), IDS);
  assert.deepEqual(data, original);
});

test("unregistered months and missing snapshots cannot be selected", () => {
  const data = fixture();
  assert.throws(() => getAsOf(data, "2018-10-01"));
  delete data.snapshots[MONTH];
  assert.throws(() => getAsOf(data, MONTH));
});

test("pile does not expose missing IDs or next-month receipts even if its index is corrupt", () => {
  const data = fixture();
  data.pile[MONTH].push("99999999");
  data.complaints[IDS[0]].ldate = "2018-09-01";
  assert.deepEqual(getAsOf(data, MONTH).complaints.map(row => row.odino), IDS.slice(1));
});

test("pile cannot relabel an earlier receipt as a current-month complaint", () => {
  const data = fixture();
  data.complaints[IDS[0]].ldate = "2018-07-31";
  assert.equal(getAsOf(data, MONTH).complaints.some(row => row.odino === IDS[0]), false);
});
