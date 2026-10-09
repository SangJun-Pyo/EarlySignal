import { availableDate, evidenceKey, getAsOf } from "./asof";
import type { Category, ConsoleData, Decision, DecisionKind, Flag } from "./types";

export const BRIEF_TITLE = "대표 신고 요약";
export const BRIEF_REVIEW_NOTE = "AI 요약 인용·담당자 검토";
export const BRIEF_UNAVAILABLE = "이 경보의 대표 신고 요약은 없습니다. 아래 원문에서 근거를 직접 확인해 주세요.";

export const CATEGORY_NAMES: Record<Category, string> = {
  fire_thermal: "화재·과열", electrical_failure: "전기 계통", loss_of_power: "동력 상실", engine_stall: "주행 중 멈춤",
  engine_failure: "엔진 손상", airbag: "에어백", brakes: "브레이크", steering: "조향", seat_belt: "안전벨트",
  fuel_leak: "연료 누출", transmission: "변속기", lighting: "등화 장치", suspension: "현가 장치", structure_body: "차체", tires_wheels: "타이어·휠", other: "기타",
};
const FLAG_NAMES: Record<Flag, string> = { fire: "화재 기록", smoke: "연기 언급", driving: "주행 중 언급", parked: "주차·충전 중 언급", crash: "충돌 기록", injury: "부상 기록", severe: "심각도 높음" };
export interface RequestInput { data: ConsoleData; month: string; grp: string; category: Category; cited: string[]; excluded: string[]; decision?: DecisionKind; actions?: string[]; memo?: string; savedAt?: string }

function unique(values: string[]) { return [...new Set(values)]; }
function citations(text: string) { return unique([...text.matchAll(/#(\d+)\b/g)].map(m => m[1])); }
function plain(value: string) { return value.replace(/[\r\n]+/g, " ").trim(); }

export function createRequest(input: RequestInput) {
  const { data, month, grp, category, decision, savedAt } = input;
  const { snapshot, series } = getAsOf(data, month);
  const key = evidenceKey(grp, category, month);
  const evidence = data.evidence[key];
  const alert = snapshot.alerts.find(a => a.grp === grp && a.category === category);
  if (!evidence || !alert) throw new Error("경보를 선택한 뒤 조사 요청서를 만들어 주세요.");
  const allowed = new Set(evidence.ids);
  if (allowed.size !== evidence.ids.length || evidence.n !== evidence.ids.length || alert.n !== evidence.n || !Number.isFinite(alert.baseline) || alert.baseline <= 0) {
    throw new Error("경보 건수와 근거 신고 목록이 일치하지 않습니다.");
  }
  for (const id of evidence.ids) {
    const row = data.complaints[id];
    if (!row || row.grp !== grp || row.month !== month || row.ldate < month || row.ldate >= availableDate(month) || !row.categories.includes(category)) {
      throw new Error("근거 데이터의 차종·증상·시점이 일치하지 않습니다.");
    }
  }
  const excluded = unique(input.excluded);
  const explicit = unique(input.cited);
  for (const id of [...excluded, ...explicit]) if (!allowed.has(id)) throw new Error("선택한 경보에 없는 신고를 인용하거나 제외할 수 없습니다.");
  if (explicit.some(id => excluded.includes(id))) throw new Error("같은 신고를 인용하고 제외할 수 없습니다.");
  const remaining = evidence.ids.filter(id => !excluded.includes(id));
  if (!remaining.length) throw new Error("근거 신고가 모두 제외됐습니다. 인용할 신고를 다시 검토해 주세요.");
  const autoSuggested = explicit.length === 0;
  const cited = autoSuggested ? remaining.slice(0, 3) : explicit;
  const rawBrief = data.briefs[key] ?? "";
  const rawCitations = citations(rawBrief);
  const briefSuppressed = Boolean(rawBrief) && (rawCitations.length === 0 || rawCitations.some(id => !allowed.has(id) || excluded.includes(id)));
  const brief = briefSuppressed ? "제외한 신고 또는 확인되지 않은 인용이 포함되어 대표 신고 요약을 사용하지 않았습니다." : rawBrief || BRIEF_UNAVAILABLE;
  const briefCited = briefSuppressed ? [] : rawCitations;
  const memo = plain(input.memo ?? "");
  if (citations(memo).some(id => !allowed.has(id) || excluded.includes(id))) throw new Error("메모에 근거 밖의 신고 번호가 있습니다.");
  if (decision && !["조사 착수", "보류", "기각"].includes(decision)) throw new Error("담당자 판단을 선택해 주세요.");
  if (savedAt && (!decision || Number.isNaN(Date.parse(savedAt)))) throw new Error("저장하려면 판단과 실제 저장 시각이 필요합니다.");
  const available = availableDate(month);
  const model = grp.split("|")[1] ?? grp;
  const docNo = `ES-${available.replaceAll("-", "")}-${grp.replace(/[^A-Z0-9-]/g, "-")}-${category.toUpperCase()}`;
  const recent = series[grp];
  const categorySeries = recent?.categories[category];
  const history = recent && categorySeries ? recent.months.slice(-6).map((m, i) => `${m.slice(0, 7)} ${categorySeries.n[Math.max(0, recent.months.length - 6) + i]}건`).join(" · ") : "이력 없음";
  const sourceName = data.labeler === "llm" ? "AI 라벨" : "키워드 분류";
  const flagSourceNote = data.labeler === "llm"
    ? "화재·충돌·부상은 NHTSA 기록 또는 AI 분류에 해당한 신고입니다. 연기·주행·주차와 심각도는 AI 분류입니다."
    : "화재·충돌·부상은 NHTSA 기록입니다. 연기·주행·주차는 키워드 규칙이며 심각도는 미측정입니다.";
  const citedAll = unique([...cited, ...briefCited]);
  const actions = unique((input.actions ?? []).map(plain).filter(Boolean));
  const quoteLines = citedAll.map(id => {
    const row = data.complaints[id];
    const note = cited.includes(id) ? autoSuggested ? "자동 제안" : "담당자 인용" : "대표 요약 인용";
    const original = `- #${id} · ${row.ldate} · 원문 발췌: ${plain(row.text)} [${note}]`;
    return row.summary_ko ? `${original}\nAI 요약(담당자 검토 필요): ${plain(row.summary_ko)}` : original;
  });
  const parts = [
    `# 조사 요청서 ${docNo} (${savedAt ? "확정" : "초안"})`,
    `- 조사 대상: ${model} (${grp.split("|")[0]}) · ${CATEGORY_NAMES[category]}\n- 분석 기준: ${month.slice(0, 7)} 접수분까지 · 월 집계 확인 가능일 ${available}\n- 데이터: NHTSA 소비자 신고 · ${sourceName} · 통계 경보\n${savedAt ? `- 실제 저장 시각: ${savedAt}\n` : ""}- 분석 방식: 현재 공개 파일의 접수일을 기준으로 한 과거 재현`,
    `## 1. 신고 증가와 경보 근거\n이번 달 ${alert.n}건, 평소 ${alert.baseline.toFixed(2)}건, ${(alert.n / alert.baseline).toFixed(2)}배 (p=${alert.p_value.toExponential(3)}). 연속 경보 ${alert.streak}개월.\n경보 기준: 이전 12개월 평균 대비 p<0.001, 3건 이상(최소 이력 6개월).\n같은 시기 같은 증상 경보 차종: ${alert.comove.map(g => g.replace("|", " ")).join(", ") || "없음"}.\n최근 6개월: ${history}`,
    `## 2. 반복되는 발생 상황 (${sourceName}, ${evidence.n}건 기준)\n${Object.entries(evidence.agg).filter(([, n]) => n > 0).sort((a, b) => b[1] - a[1]).map(([flag, n]) => `${FLAG_NAMES[flag as Flag]} ${n}건`).join(" · ") || "집계된 발생 상황 없음"}\n${flagSourceNote}\n함께 언급: ${evidence.co.map(([c, n]) => `${CATEGORY_NAMES[c]} ${n}건`).join(" · ") || "없음"}\n신고 차량 연식: ${evidence.years.map(([year, n]) => `${year}년 ${n}건`).join(" · ") || "미상"}\n통계·상황 집계는 최초 분류된 전체 근거 기준입니다. 담당자 제외는 요청서 인용에 반영됩니다.`,
    `## 3. ${BRIEF_TITLE}${rawBrief && !briefSuppressed ? ` (${BRIEF_REVIEW_NOTE})\n기존 신고별 AI 요약을 그대로 인용합니다. 원문과의 의미 일치는 담당자가 확인해야 합니다.` : ""}\n${brief}`,
    `## 4. 인용 신고\n${quoteLines.join("\n")}\n검토 후 제외 ${excluded.length}건${excluded.length ? ` (${excluded.map(id => `신고 ${id}`).join(", ")})` : ""}.\nNHTSA ODI 신고 번호로 근거를 식별할 수 있습니다. 원문은 알려진 식별정보를 가린 발췌입니다.`,
    "## 5. 아직 확인되지 않은 사항\n- 원인과 결함 여부\n- 판매·운행 대수 대비 신고 비율\n- 동일인·중복 신고 여부\n- 정비·수리 이력과 미국 외 시장에서의 발생 여부",
    `## 6. 내부 데이터로 확인할 항목\n- 고객 상담·보증 수리 기록: 신고 차량의 연식과 증상 대조\n- 생산 기록: 같은 시기·공장에서 생산한 차량에 반복되는지 확인\n- 부품 공급사와 부품 변경 이력 확인`,
    `## 7. 담당자 판단과 다음 조치\n판단: ${decision ?? "미선택"}\n다음 조치: ${actions.join(" · ") || "미선택"}\n메모: ${memo || "없음"}`,
    "> 결함·원인 판정이 아니라 조사 착수 여부를 정하기 위한 자료입니다.",
  ];
  const record: Decision | null = savedAt && decision ? { doc_no: docNo, made: savedAt, analysis_available: available, grp, category, decision, actions, memo, cited, excluded, brief_cited: briefCited } : null;
  return { docNo, markdown: parts.join("\n\n") + "\n", cited, excluded, briefCited, briefSuppressed, autoSuggested, available, record };
}
