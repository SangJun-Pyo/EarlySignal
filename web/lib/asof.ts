import type { Category, ConsoleData, Series } from "./types";

export function availableDate(month: string): string {
  if (!/^\d{4}-(0[1-9]|1[0-2])-01$/.test(month)) throw new Error("올바른 기준 월을 선택해 주세요.");
  const date = new Date(`${month}T00:00:00Z`);
  date.setUTCMonth(date.getUTCMonth() + 1);
  return date.toISOString().slice(0, 10);
}
export function evidenceKey(grp: string, category: Category, month: string) {
  return `${grp}:${category}:${month}`;
}
export function getAsOf(data: ConsoleData, month: string) {
  if (!data.asof_months.includes(month) || !data.snapshots[month]) throw new Error("데이터에 없는 기준 월입니다.");
  const series: Record<string, Series> = {};
  for (const [grp, original] of Object.entries(data.series)) {
    const indices = original.months.map((value, i) => value <= month ? i : -1).filter(i => i >= 0);
    series[grp] = {
      months: indices.map(i => original.months[i]), total: indices.map(i => original.total[i]),
      categories: Object.fromEntries(Object.entries(original.categories).map(([category, values]) => [category, {
        n: indices.map(i => values!.n[i]), baseline: indices.map(i => values!.baseline[i]), alert: indices.map(i => values!.alert[i]),
      }])),
    };
  }
  const complaints = (data.pile[month] ?? []).map(odino => ({ odino, ...data.complaints[odino] }))
    .filter(row => row.month === month && row.ldate >= month && row.ldate < availableDate(month));
  return { snapshot: data.snapshots[month], complaints, series };
}
