"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { availableDate, evidenceKey, getAsOf } from "@/lib/asof";
import { BRIEF_TITLE, BRIEF_REVIEW_NOTE, BRIEF_UNAVAILABLE, createRequest } from "@/lib/request";
import {
  categories as categoryNames,
  flags as flagNames,
  flagSourceLabel,
  model,
  make,
  monthLabel,
  dateLabel,
  formatNumber,
} from "@/lib/display";
import type {
  Alert,
  CasesData,
  Category,
  Complaint,
  ConsoleData,
  Decision,
  DecisionKind,
  Flag,
  MetaData,
  RevealCase,
} from "@/lib/types";

type View = "pile" | "signals" | "request" | "validation";
type Selection = { grp: string; category: Category };
const storageKey = "earlysignal.decisions.v1";
const nextActions = [
  "원문 정밀 검토",
  "수리·보증 기록 조회",
  "생산 기록 대조",
  "부품 공급사 확인",
  "다음 달 재검토",
];
const stepNames: Record<View, string> = {
  pile: "신고 원문",
  signals: "신호와 근거",
  request: "조사 요청서",
  validation: "검증 결과",
};
const displayedFlags: Flag[] = [
  "fire",
  "smoke",
  "driving",
  "parked",
  "crash",
  "injury",
  "severe",
];
const expressions = [
  { name: "FIRE / FLAMES", regex: /\b(fire|fires|flames?)\b/i },
  { name: "SMOKE", regex: /\bsmok(e|ing)\b/i },
  { name: "BURN / BURNING", regex: /\bburn(ed|ing|s)?\b/i },
  { name: "MELTED", regex: /\bmelt(ed|ing|s)?\b/i },
  { name: "STALLED", regex: /\bstall(ed|ing|s)?\b/i },
  { name: "LOSS OF POWER", regex: /loss of power|lost power|power loss/i },
];

function Icon({ name, size = 20 }: { name: string; size?: number }) {
  const paths: Record<string, React.ReactNode> = {
    signal: (
      <>
        <path d="M3 15h4l3-9 4 13 3-8h4" />
        <path d="M3 4v16h18" />
      </>
    ),
    pile: (
      <>
        <rect x="5" y="3" width="14" height="18" rx="2" />
        <path d="M9 8h6M9 12h6M9 16h4" />
      </>
    ),
    request: (
      <>
        <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" />
        <path d="M14 3v6h6M8 13h8M8 17h5" />
      </>
    ),
    validation: (
      <>
        <path d="M12 3l8 4v6c0 4-8 8-8 8s-8-4-8-8V7z" />
        <path d="m8 12 3 3 5-6" />
      </>
    ),
    arrow: (
      <>
        <path d="M4 12h16m-6-6 6 6-6 6" />
      </>
    ),
    download: (
      <>
        <path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5" />
      </>
    ),
    check: <path d="m5 12 4 4L19 6" />,
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    close: <path d="m6 6 12 12M6 18 18 6" />,
  };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] || paths.signal}
    </svg>
  );
}
function download(name: string, text: string, type: string) {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function isDecision(value: unknown): value is Decision {
  if (!value || typeof value !== "object") return false;
  const d = value as Partial<Decision>;
  return (
    typeof d.doc_no === "string" &&
    typeof d.made === "string" &&
    typeof d.analysis_available === "string" &&
    typeof d.grp === "string" &&
    typeof d.category === "string" &&
    ["조사 착수", "보류", "기각"].includes(d.decision || "") &&
    Array.isArray(d.actions) &&
    d.actions.every((x) => typeof x === "string") &&
    typeof d.memo === "string" &&
    Array.isArray(d.cited) &&
    d.cited.every((x) => typeof x === "string") &&
    Array.isArray(d.excluded) &&
    d.excluded.every((x) => typeof x === "string") &&
    Array.isArray(d.brief_cited) &&
    d.brief_cited.every((x) => typeof x === "string")
  );
}

export default function Workspace() {
  const [data, setData] = useState<ConsoleData | null>(null);
  const [meta, setMeta] = useState<MetaData | null>(null);
  const [cases, setCases] = useState<CasesData | null>(null);
  const [loadError, setLoadError] = useState("");
  const [view, setView] = useState<View>("signals");
  const [month, setMonth] = useState("");
  const [selected, setSelected] = useState<Selection | null>(null);
  const [detailTab, setDetailTab] = useState<"evidence" | "trend">("evidence");
  const [flagFilter, setFlagFilter] = useState<Flag | null>(null);
  const [cited, setCited] = useState<string[]>([]);
  const [excluded, setExcluded] = useState<string[]>([]);
  const [decision, setDecision] = useState<DecisionKind | undefined>();
  const [actions, setActions] = useState<string[]>([]);
  const [memo, setMemo] = useState("");
  const [saved, setSaved] = useState<ReturnType<typeof createRequest> | null>(
    null,
  );
  const [records, setRecords] = useState<Decision[]>([]);
  const [notice, setNotice] = useState("");
  const [storageWarning, setStorageWarning] = useState("");

  useEffect(() => {
    const abort = new AbortController();
    Promise.all(
      ["console", "meta", "cases"].map(async (name) => {
        const response = await fetch(`./data/${name}.json`, {
          signal: abort.signal,
        });
        if (!response.ok)
          throw new Error(`자료를 읽지 못했습니다 (${response.status}).`);
        const value = await response.json();
        if (value.contract !== "earlysignal-data-v1")
          throw new Error("데이터 계약 버전이 맞지 않습니다.");
        return value;
      }),
    )
      .then(([consoleData, metaData, casesData]) => {
        setData(consoleData);
        setMeta(metaData);
        setCases(casesData);
        setMonth(consoleData.default_asof);
      })
      .catch((error) => {
        if (error.name !== "AbortError") setLoadError(error.message);
      });
    try {
      const parsed = JSON.parse(
        localStorage.getItem(storageKey) || '{"decisions":[]}',
      );
      if (
        parsed.contract === "earlysignal-data-v1" &&
        Array.isArray(parsed.decisions)
      )
        setRecords(parsed.decisions.filter(isDecision));
    } catch {
      setStorageWarning(
        "이 브라우저의 저장 기록을 읽지 못했습니다. 새 요청서는 파일로 내려받을 수 있습니다.",
      );
    }
    return () => abort.abort();
  }, []);

  const asof = useMemo(
    () => (data && month ? getAsOf(data, month) : null),
    [data, month],
  );
  const key =
    data && selected ? evidenceKey(selected.grp, selected.category, month) : "";
  const evidence = data?.evidence[key];
  const alert = asof?.snapshot.alerts.find(
    (a) => a.grp === selected?.grp && a.category === selected?.category,
  );
  const draftState = useMemo(() => {
    if (!data || !selected || !evidence?.ids.length)
      return { request: null, error: "" };
    try {
      return {
        request: createRequest({
          data,
          month,
          ...selected,
          cited,
          excluded,
          decision,
          actions,
          memo,
        }),
        error: "",
      };
    } catch (error) {
      return {
        request: null,
        error:
          error instanceof Error
            ? error.message
            : "요청서 생성에 실패했습니다.",
      };
    }
  }, [
    data,
    month,
    selected,
    evidence,
    cited,
    excluded,
    decision,
    actions,
    memo,
  ]);
  const draft = draftState.request;
  const renderedRequest = saved || draft;

  function resetReview() {
    setCited([]);
    setExcluded([]);
    setFlagFilter(null);
    setDecision(undefined);
    setActions([]);
    setMemo("");
    setSaved(null);
    setNotice("");
    setDetailTab("evidence");
  }
  function selectSignal(grp: string, category: Category) {
    resetReview();
    setSelected({ grp, category });
    setView("signals");
  }
  function changeMonth(value: string) {
    resetReview();
    setSelected(null);
    setMonth(value);
    if (view === "request") setView("signals");
  }
  function mark(id: string, kind: "cite" | "exclude") {
    setSaved(null);
    setNotice("");
    if (kind === "cite") {
      setCited((old) =>
        old.includes(id) ? old.filter((v) => v !== id) : [...old, id],
      );
      setExcluded((old) => old.filter((v) => v !== id));
    } else {
      setExcluded((old) =>
        old.includes(id) ? old.filter((v) => v !== id) : [...old, id],
      );
      setCited((old) => old.filter((v) => v !== id));
    }
  }
  function saveRequest() {
    if (!data || !selected || !decision) return;
    try {
      const result = createRequest({
        data,
        month,
        ...selected,
        cited,
        excluded,
        decision,
        actions,
        memo,
        savedAt: new Date().toISOString(),
      });
      if (!result.record) throw new Error("판단 기록을 생성하지 못했습니다.");
      const updated = [result.record, ...records];
      setRecords(updated);
      setSaved(result);
      download(
        `${result.docNo}.md`,
        result.markdown,
        "text/markdown;charset=utf-8",
      );
      try {
        localStorage.setItem(
          storageKey,
          JSON.stringify({
            contract: "earlysignal-data-v1",
            decisions: updated,
          }),
        );
        setStorageWarning("");
        setNotice("요청서를 확정하고 이 브라우저에 저장했습니다.");
      } catch {
        setStorageWarning(
          "브라우저 저장 공간을 사용할 수 없습니다. 현재 요청서와 판단 기록을 내려받아 보관하세요.",
        );
        setNotice("요청서를 확정했습니다. 파일 다운로드로 보관해주세요.");
      }
    } catch (error) {
      setNotice(
        error instanceof Error
          ? error.message
          : "요청서를 저장하지 못했습니다.",
      );
    }
  }

  if (loadError)
    return (
      <main className="loading">
        <Icon name="validation" size={36} />
        <h1>공개 자료를 불러오지 못했습니다</h1>
        <p>{loadError}</p>
        <button className="primary" onClick={() => location.reload()}>
          다시 불러오기
        </button>
      </main>
    );
  if (!data || !asof || !meta || !cases)
    return (
      <main className="loading">
        <span className="loading-mark">ES</span>
        <h1>공개 신고 자료를 불러옵니다</h1>
        <p>NHTSA 공개 파일의 신고와 검증 결과를 불러오는 중입니다.</p>
      </main>
    );
  const currentComplaints = asof.complaints.map((c) => ({ ...c, id: c.odino }));
  const currentPile = currentComplaints.map((c) => c.id);
  const filteredIds = (evidence?.ids || []).filter((id) => {
    const c = data.complaints[id];
    return (
      c &&
      c.grp === selected?.grp &&
      c.month === month &&
      c.categories.includes(selected!.category) &&
      c.ldate >= month &&
      c.ldate < availableDate(month) &&
      (!flagFilter || c.flags.includes(flagFilter))
    );
  });
  const currentSeries = selected ? asof.series[selected.grp] : null;
  const trend =
    currentSeries?.months.slice(-18).map((m, i) => {
      const offset =
        currentSeries.months.length -
        Math.min(18, currentSeries.months.length) +
        i;
      const cat = currentSeries.categories[selected!.category];
      return {
        month: m,
        n: cat?.n[offset] || 0,
        baseline: cat?.baseline[offset] ?? null,
        alert: cat?.alert[offset] || false,
      };
    }) || [];
  const postCase =
    saved && selected
      ? data.reveal.cases.find(
          (c) =>
            c.groups?.includes(selected.grp) &&
            c.first_alert_category === selected.category,
        )
      : undefined;

  return (
    <div className="shell">
      <a href="#main" className="skip-link">
        본문으로 이동
      </a>
      <aside className="rail" aria-label="작업 공간 메뉴">
        <a className="brand-mark" href="./" aria-label="EarlySignal 홈">
          <Icon name="signal" size={26} />
        </a>
        <div className="rail-divider" />
        {(["pile", "signals", "request"] as View[]).map((v, i) => (
          <button
            key={v}
            className={`rail-button ${view === v ? "active" : ""}`}
            title={stepNames[v]}
            aria-label={stepNames[v]}
            onClick={() => setView(v)}
          >
            <Icon name={v === "signals" ? "signal" : v} />
            <span>0{i + 1}</span>
          </button>
        ))}
        <button
          className={`rail-button rail-bottom ${view === "validation" ? "active" : ""}`}
          title="검증 결과"
          aria-label="검증 결과"
          onClick={() => setView("validation")}
        >
          <Icon name="validation" />
          <span>검증</span>
        </button>
        <span className="avatar" title="고객 안전 담당자">
          안전
        </span>
      </aside>
      <div className="app">
        <header className="topbar">
          <div className="brand">
            <b>
              Early<span>Signal</span>
            </b>
            <span className="brand-divider" />
            <span className="team">고객 안전팀 작업 공간</span>
          </div>
          <div className="top-badges">
            <span className="live-dot" aria-hidden="true" /> NHTSA 공개 파일 기반{" "}
            <span className="historical-badge">접수일 기준 과거 재현</span>
          </div>
        </header>
        <div className="page-heading">
          <div className="page-heading-copy">
            <p className="eyebrow">COMPLAINTS TO INVESTIGATION</p>
            <h1>
              {view === "validation"
                ? "검증 결과와 남은 질문"
                : "고객의 목소리를, 조사의 근거로."}
            </h1>
            <p className="page-intro">
              {view === "validation"
                ? "확인한 결과와 아직 확인하지 못한 가정을 함께 공개합니다."
                : "신호를 고르고 원문을 검토하면, 근거가 연결된 조사 요청서가 완성됩니다."}
            </p>
          </div>
          {view !== "validation" && (
            <div className="heading-art" aria-hidden="true">
              <img
                src="/images/vehicle-concept.webp"
                alt=""
                width={960}
                height={540}
                decoding="async"
              />
            </div>
          )}
          <button
            className="subtle-button demo-button"
            onClick={() => {
              changeMonth(data.demo_signal.month);
              selectSignal(data.demo_signal.grp, data.demo_signal.category);
            }}
          >
            데모 신호 열기 <Icon name="arrow" size={17} />
          </button>
        </div>
        <nav className="workflow-nav" aria-label="조사 준비 단계">
          {(["pile", "signals", "request"] as View[]).map((v, i) => (
            <button
              key={v}
              className={view === v ? "active" : ""}
              aria-current={view === v ? "step" : undefined}
              onClick={() => setView(v)}
            >
              <span className="step-index">0{i + 1}</span>
              {stepNames[v]}
              {v === "request" && (
                <span className={`status-dot ${saved ? "saved" : ""}`}>
                  {saved ? "확정" : "초안"}
                </span>
              )}
            </button>
          ))}
          <button
            className={`validation-nav ${view === "validation" ? "active" : ""}`}
            onClick={() => setView("validation")}
          >
            <Icon name="validation" size={17} />
            검증 결과
          </button>
        </nav>
        <main id="main">
          {view !== "validation" && (
            <section className="asof-bar" aria-label="분석 기준 월">
              <div className="asof-title">
                <Icon name="clock" size={18} />
                <b>분석 시점</b>
              </div>
              <div className="month-buttons">
                {data.asof_months.map((m) => (
                  <button
                    key={m}
                    className={m === month ? "active" : ""}
                    aria-pressed={m === month}
                    onClick={() => changeMonth(m)}
                  >
                    {Number(m.slice(5, 7))}월
                  </button>
                ))}
              </div>
              <div className="asof-caption">
                <b>{monthLabel(month)} 접수분까지</b>
                <span>
                  월 집계 확인 가능일 {dateLabel(availableDate(month))}
                </span>
              </div>
            </section>
          )}
          {view === "pile" && (
            <div className="pile-layout">
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">01 · SOURCE MATERIAL</p>
                    <h2>{monthLabel(month)} 접수 신고</h2>
                  </div>
                  <span className="count-badge">
                    {formatNumber(currentPile.length)}건
                  </span>
                </div>
                <p className="small muted">
                  감시 대상 {data.groups.length}개 차종 · 접수일 기준 · 알려진
                  식별정보를 가린 원문 발췌
                </p>
                <div className="pile-list">
                  {currentComplaints.slice(0, 40).map((c) => (
                    <div className="pile-row" key={c.id}>
                      <div className="pile-meta">
                        <span className="mono">{c.ldate.slice(5)}</span>
                        <b>{model(c.grp)}</b>
                        <span>{c.year}년식</span>
                        <span className="mono complaint-id">#{c.id}</span>
                      </div>
                      <p>{c.text}</p>
                    </div>
                  ))}
                </div>
                {currentPile.length > 40 && (
                  <p className="remaining">
                    외 {formatNumber(currentPile.length - 40)}건 · 신호 화면에서
                    증상별 근거를 검토합니다
                  </p>
                )}
              </section>
              <aside className="expression-panel panel">
                <p className="eyebrow">THE SAME SYMPTOM, DIFFERENT WORDS</p>
                <h2>
                  같은 현상이
                  <br />
                  제각각의 말로 들어옵니다.
                </h2>
                <p className="muted">
                  문장을 읽어야 상황이 보입니다. 표현만으로는 다른 부위의 신고가
                  함께 묶일 수 있습니다.
                </p>
                <div className="expression-list">
                  {expressions.map((e) => (
                    <div key={e.name}>
                      <span className="mono">{e.name}</span>
                      <b>
                        {
                          currentComplaints.filter((c) => e.regex.test(c.text))
                            .length
                        }
                        <small>건</small>
                      </b>
                    </div>
                  ))}
                </div>
                <p className="small muted">
                  원문 발췌에 해당 표현이 있는 신고 수입니다. 증상 라벨 집계와
                  다릅니다.
                </p>
                <button
                  className="primary full"
                  onClick={() => setView("signals")}
                >
                  {data.labeler === "llm" ? "AI 분류" : "키워드 분류"}{" "}
                  · 통계 경보 보기 <Icon name="arrow" />
                </button>
              </aside>
            </div>
          )}
          {view === "signals" && (
            <div className="signals-layout">
              <section className="signals-left">
                <div className="panel heatmap-panel">
                  <div className="panel-heading">
                    <div>
                      <p className="eyebrow">02 · SIGNAL MONITORING</p>
                      <h2>어디부터 살펴볼까요?</h2>
                    </div>
                    <span className="small muted">차종 × 증상</span>
                  </div>
                  <div className="heatmap-scroll">
                    <table className="heatmap">
                      <thead>
                        <tr>
                          <th scope="col">차종</th>
                          {data.categories.map((c) => (
                            <th key={c} scope="col">
                              {categoryNames[c]}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {data.groups.map((g) => (
                          <tr key={g}>
                            <th scope="row">
                              <span>{make(g)}</span>
                              {model(g)}
                            </th>
                            {data.categories.map((c) => {
                              const s = asof.series[g];
                              const idx = s?.months.indexOf(month) ?? -1;
                              const cat = s?.categories[c];
                              const n = cat?.n[idx] ?? 0;
                              const baseline = cat?.baseline[idx];
                              const ratio = baseline
                                ? Math.min(n / baseline, 5)
                                : 0;
                              const isAlert = cat?.alert[idx] || false;
                              const active =
                                selected?.grp === g && selected?.category === c;
                              return (
                                <td key={c}>
                                  <button
                                    className={`heat-cell ${isAlert ? "alert" : ""} ${active ? "selected" : ""}`}
                                    style={
                                      {
                                        "--heat":
                                          ratio > 0
                                            ? Math.min(
                                                0.12 + ratio * 0.12,
                                                0.68,
                                              )
                                            : 0,
                                      } as React.CSSProperties
                                    }
                                    title={`${model(g)} ${categoryNames[c]}: ${n}건, 평소 ${baseline == null ? "산출 전" : baseline.toFixed(1) + "건"}${isAlert ? ", 통계 경보" : ""}`}
                                    aria-label={`${model(g)} ${categoryNames[c]} ${n}건${isAlert ? " 통계 경보" : ""}`}
                                    aria-pressed={active}
                                    onClick={() => selectSignal(g, c)}
                                  >
                                    {n || "·"}
                                  </button>
                                </td>
                              );
                            })}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="heatmap-legend">
                    <span>색 = 평소 대비 증가</span>
                    <span className="legend-swatches">
                      <i />
                      <i />
                      <i />
                      <i />
                    </span>
                    <span>
                      <i className="alert-swatch" /> 통계 경보
                    </span>
                  </div>
                </div>
                <div className="panel alerts-panel">
                  <div className="panel-heading">
                    <h2>
                      이 시점의 경보{" "}
                      <span className="teal">
                        {asof.snapshot.alerts.length}
                      </span>
                    </h2>
                    <span className="small muted">증가 배수 순</span>
                  </div>
                  <div className="alert-list">
                    {asof.snapshot.alerts.length ? (
                      asof.snapshot.alerts.map((a) => (
                        <AlertRow
                          key={`${a.grp}:${a.category}`}
                          alert={a}
                          active={
                            selected?.grp === a.grp &&
                            selected.category === a.category
                          }
                          onClick={() => selectSignal(a.grp, a.category)}
                        />
                      ))
                    ) : (
                      <div className="empty-small">
                        이 달에는 설정한 통계 규칙을 넘은 신호가 없습니다.
                      </div>
                    )}
                  </div>
                </div>
              </section>
              <section className="panel evidence-panel">
                {!selected ? (
                  <div className="selection-empty">
                    <div className="empty-icon">
                      <Icon name="signal" size={38} />
                    </div>
                    <p className="eyebrow">START WITH ONE SIGNAL</p>
                    <h2>관심 신호를 선택하세요.</h2>
                    <p>
                      왼쪽의 경보 또는 차종·증상 칸을 선택하면
                      <br />
                      증상별로 분류된 신고 원문과 통계 경보를 확인할 수 있습니다.
                    </p>
                    <div className="empty-steps">
                      <span>경보 선택</span>
                      <Icon name="arrow" size={16} />
                      <span>원문 검토</span>
                      <Icon name="arrow" size={16} />
                      <span>요청서 저장</span>
                    </div>
                    <button
                      className="subtle-button"
                      onClick={() => {
                        changeMonth(data.demo_signal.month);
                        selectSignal(
                          data.demo_signal.grp,
                          data.demo_signal.category,
                        );
                      }}
                    >
                      {model(data.demo_signal.grp)} ·{" "}
                      {categoryNames[data.demo_signal.category]} 살펴보기{" "}
                      <Icon name="arrow" size={17} />
                    </button>
                  </div>
                ) : (
                  <>
                    <div className="panel-heading selected-heading">
                      <div>
                        <p className="eyebrow">
                          {make(selected.grp)} · {monthLabel(month)}
                        </p>
                        <h2>
                          {model(selected.grp)}{" "}
                          <span>· {categoryNames[selected.category]}</span>
                        </h2>
                      </div>
                      <span className={alert ? "alert-badge" : "neutral-badge"}>
                        {alert ? "통계 경보" : "경보 없음"}
                      </span>
                    </div>
                    <div className="signal-stats">
                      <div>
                        <span>이번 달 신고</span>
                        <b>
                          {evidence?.n ??
                            getSelectedN(
                              asof.series[selected.grp],
                              month,
                              selected.category,
                            )}
                          <small>건</small>
                        </b>
                      </div>
                      <div>
                        <span>평소 월평균</span>
                        <b>
                          {getBaseline(
                            asof.series[selected.grp],
                            month,
                            selected.category,
                          )}
                          <small>건</small>
                        </b>
                      </div>
                      <div>
                        <span>평소 대비</span>
                        <b className="amber">
                          {alert ? alert.ratio.toFixed(1) + "배" : "—"}
                        </b>
                      </div>
                      {alert && (
                        <div>
                          <span>연속 경보</span>
                          <b>
                            {alert.streak}
                            <small>개월</small>
                          </b>
                        </div>
                      )}
                    </div>
                    <p className="small muted baseline-note">
                      평소 = 직전 {meta.params.baseline_months}개월 평균
                      {alert?.comove.length
                        ? ` · 같은 증상 경보: ${alert.comove.map(model).join(", ")}`
                        : ""}
                    </p>
                    <div className="detail-tabs">
                      <button
                        className={detailTab === "evidence" ? "active" : ""}
                        onClick={() => setDetailTab("evidence")}
                      >
                        근거 검토 <span>{evidence?.n ?? 0}</span>
                      </button>
                      <button
                        className={detailTab === "trend" ? "active" : ""}
                        onClick={() => setDetailTab("trend")}
                      >
                        월별 추이
                      </button>
                    </div>
                    {detailTab === "trend" ? (
                      <div className="trend-area">
                        <h3>언제부터 신고가 늘었을까요?</h3>
                        <p className="small muted">
                          {monthLabel(month)}까지의 실제 접수 건수 · 주황색
                          막대는 경보 발생 월
                        </p>
                        <div className="chart">
                          <ResponsiveContainer width="100%" height={290}>
                            <ComposedChart
                              data={trend}
                              margin={{
                                top: 20,
                                right: 15,
                                left: -18,
                                bottom: 15,
                              }}
                            >
                              <CartesianGrid
                                stroke="#22374b"
                                vertical={false}
                              />
                              <XAxis
                                dataKey="month"
                                tickFormatter={(m: string) =>
                                  m.slice(2, 7).replace("-", ".")
                                }
                                stroke="#90a4b8"
                                fontSize={12}
                              />
                              <YAxis
                                stroke="#90a4b8"
                                allowDecimals={false}
                                fontSize={12}
                              />
                              <Tooltip
                                contentStyle={{
                                  background: "#102237",
                                  border: "1px solid #35506a",
                                  borderRadius: 8,
                                  color: "#e9f0f6",
                                }}
                                labelFormatter={(v) => monthLabel(String(v))}
                                formatter={(v, n) => [
                                  v == null
                                    ? "산출 전"
                                    : Number(v).toFixed(
                                        n === "평소 월평균" ? 1 : 0,
                                      ) + "건",
                                  n,
                                ]}
                              />
                              <Bar
                                dataKey="n"
                                name="접수 신고"
                                fill="#42b6ba"
                                radius={[3, 3, 0, 0]}
                                shape={(props) => {
                                  const p = props as {
                                    x: number;
                                    y: number;
                                    width: number;
                                    height: number;
                                    payload: { alert: boolean };
                                  };
                                  return (
                                    <rect
                                      x={p.x}
                                      y={p.y}
                                      width={p.width}
                                      height={p.height}
                                      fill={
                                        p.payload.alert ? "#f1aa52" : "#42b6ba"
                                      }
                                      rx={3}
                                    />
                                  );
                                }}
                              />
                              <Line
                                dataKey="baseline"
                                name="평소 월평균"
                                stroke="#d3dce6"
                                strokeDasharray="5 5"
                                dot={false}
                                strokeWidth={2}
                              />
                            </ComposedChart>
                          </ResponsiveContainer>
                        </div>
                        <div className="chart-legend">
                          <span>
                            <i className="teal-swatch" /> 신고 건수
                          </span>
                          <span>
                            <i className="alert-swatch" /> 경보 발생
                          </span>
                          <span>┄ 평소 월평균</span>
                        </div>
                      </div>
                    ) : !evidence ? (
                      <div className="empty-small">
                        이 칸은 신고가 3건 미만으로 검토 근거 묶음이 생성되지
                        않았습니다. 다른 신호를 선택하세요.
                      </div>
                    ) : (
                      <>
                        <div className="evidence-overview">
                          <div className="section-label">
                            <h3>
                              {data.labeler === "llm"
                                ? "AI 라벨"
                                : "키워드 분류"}
                              로 묶인 신고 <b>{evidence.n}건</b>
                            </h3>
                            <span className="small muted">
                              집계를 눌러 원문 좁히기
                            </span>
                          </div>
                          <div className="flag-filters">
                            <button
                              className={!flagFilter ? "active" : ""}
                              onClick={() => setFlagFilter(null)}
                            >
                              전체 <b>{evidence.n}</b>
                            </button>
                            {displayedFlags
                              .filter((f) => evidence.agg[f] > 0)
                              .map((f) => (
                                <button
                                  key={f}
                                  className={flagFilter === f ? "active" : ""}
                                  onClick={() =>
                                    setFlagFilter(flagFilter === f ? null : f)
                                  }
                                >
                                  {flagNames[f]} <b>{evidence.agg[f]}</b>
                                </button>
                              ))}
                          </div>
                          <p className="small muted">
                            발생 상황 출처:{" "}
                            {displayedFlags.map((flag) =>
                              `${flagNames[flag]}: ${flagSourceLabel(data.flag_sources[flag])}`
                            ).join(" · ")}
                          </p>
                          <div className="co-years">
                            <span>
                              함께 분류:{" "}
                              {evidence.co.length
                                ? evidence.co
                                    .map(
                                      ([c, n]) => `${categoryNames[c]} ${n}건`,
                                    )
                                    .join(" · ")
                                : "없음"}
                            </span>
                            <span>
                              연식:{" "}
                              {evidence.years
                                .slice(0, 4)
                                .map(([y, n]) => `${y} (${n}건)`)
                                .join(" · ")}
                            </span>
                          </div>
                          {data.briefs[key] ? (
                            <div className="brief-box">
                              <span className="eyebrow">
                                {BRIEF_TITLE} ({BRIEF_REVIEW_NOTE})
                              </span>
                              <p className="whitespace-pre-line">{data.briefs[key]}</p>
                              <p>기존 신고별 AI 요약을 그대로 인용합니다. 원문과의 의미 일치는 담당자가 확인해야 합니다.</p>
                            </div>
                          ) : (
                            <div className="brief-empty">
                              <Icon name="pile" size={17} />
                              <span>
                                {BRIEF_UNAVAILABLE}
                              </span>
                            </div>
                          )}
                        </div>
                        <div className="evidence-list-heading">
                          <h3>
                            원문 검토{" "}
                            <span>
                              {filteredIds.length}건
                              {flagFilter ? ` · ${flagNames[flagFilter]}` : ""}
                            </span>
                          </h3>
                          <p>
                            <span className="teal">인용 {cited.length}</span>
                            <span>제외 {excluded.length}</span>
                            <span>
                              미검토{" "}
                              {evidence.ids.length -
                                cited.length -
                                excluded.length}
                            </span>
                          </p>
                        </div>
                        <div className="complaint-list">
                          {filteredIds.map((id) => (
                            <ComplaintCard
                              key={id}
                              id={id}
                              complaint={data.complaints[id]}
                              cited={cited.includes(id)}
                              excluded={excluded.includes(id)}
                              onMark={(kind) => mark(id, kind)}
                            />
                          ))}
                        </div>
                        <div className="request-cta">
                          <p className="small muted">
                            {cited.length
                              ? `직접 선택한 ${cited.length}건을 요청서에 인용합니다.`
                              : "인용이 없으면 근거에서 최대 3건을 자동 제안합니다."}
                            <br />
                            제외는 담당자 검토 기록이며 원본 통계 집계를 바꾸지
                            않습니다.
                          </p>
                          {draftState.error && (
                            <p className="storage-warning" role="alert">
                              {draftState.error}
                            </p>
                          )}
                          <button
                            className="primary full"
                            disabled={!draft}
                            onClick={() => {
                              setView("request");
                              window.scrollTo({ top: 0, behavior: "smooth" });
                            }}
                          >
                            조사 요청서 초안 만들기 <Icon name="arrow" />
                          </button>
                        </div>
                      </>
                    )}
                  </>
                )}
              </section>
            </div>
          )}
          {view === "request" &&
            (!selected || (!renderedRequest && !draftState.error) ? (
              <section className="panel request-empty">
                <Icon name="request" size={42} />
                <h2>조사할 근거부터 선택해주세요.</h2>
                <p className="muted">
                  신호 화면에서 원문을 확인하고 인용·제외한 뒤 요청서를 만들 수
                  있습니다.
                </p>
                <button className="primary" onClick={() => setView("signals")}>
                  신호와 근거로 돌아가기 <Icon name="arrow" />
                </button>
              </section>
            ) : (
              <div className="request-layout">
                <article className="paper">
                  {renderedRequest ? (
                    <>
                  <div className="paper-top">
                    <span className="mono">{renderedRequest.docNo}</span>
                    <span
                      className={`document-stamp ${saved ? "confirmed" : ""}`}
                    >
                      {saved ? "확정됨" : "검토 초안"}
                    </span>
                  </div>
                  <div className="paper-body">
                    <MarkdownDocument markdown={renderedRequest.markdown} />
                  </div>
                  {renderedRequest.autoSuggested && !saved && (
                    <p className="paper-note">
                      인용 신고는 자동 제안입니다. 원문 검토 단계에서
                      인용·제외를 바꿀 수 있습니다.
                    </p>
                  )}
                  {renderedRequest.briefSuppressed && (
                    <p className="paper-note">
                      제외한 신고나 확인되지 않은 인용이 있어 대표 신고 요약을 요청서에 넣지 않았습니다.
                    </p>
                  )}
                    </>
                  ) : (
                    <div className="paper-body" role="alert">
                      <h2>요청서 내용을 확인해주세요.</h2>
                      <p>{draftState.error}</p>
                      <p>담당자 메모를 수정하거나 신호 화면에서 근거를 다시 검토해주세요.</p>
                    </div>
                  )}
                </article>
                <aside className="decision-sidebar">
                  <section className="panel decision-panel">
                    <p className="eyebrow">03 · HUMAN DECISION</p>
                    <h2>담당자 판단</h2>
                    <p className="muted small">
                      근거를 확인한 뒤 다음 조치를 정하세요.
                    </p>
                    <div className="decision-buttons">
                      {(["조사 착수", "보류", "기각"] as DecisionKind[]).map(
                        (d) => (
                          <button
                            key={d}
                            className={decision === d ? "active" : ""}
                            aria-pressed={decision === d}
                            onClick={() => {
                              setDecision(d);
                              setSaved(null);
                              setNotice("");
                            }}
                          >
                            {d}
                          </button>
                        ),
                      )}
                    </div>
                    <h3>
                      다음 조치 <span className="muted small">복수 선택</span>
                    </h3>
                    <div className="action-options">
                      {nextActions.map((a) => (
                        <label key={a}>
                          <input
                            type="checkbox"
                            checked={actions.includes(a)}
                            onChange={() => {
                              setActions((old) =>
                                old.includes(a)
                                  ? old.filter((x) => x !== a)
                                  : [...old, a],
                              );
                              setSaved(null);
                            }}
                          />
                          <span>{a}</span>
                        </label>
                      ))}
                    </div>
                    <label className="memo-label" htmlFor="decision-memo">
                      담당자 메모
                    </label>
                    <textarea
                      id="decision-memo"
                      rows={4}
                      value={memo}
                      placeholder="추가로 확인할 점과 판단 이유를 남겨주세요."
                      onChange={(e) => {
                        setMemo(e.target.value);
                        setSaved(null);
                      }}
                    />
                    <button
                      className="primary full save-button"
                      disabled={!decision || !draft || !!draftState.error}
                      onClick={saveRequest}
                    >
                      <Icon name={saved ? "check" : "request"} />
                      {saved ? "다시 확정하고 저장" : "확정하고 저장"}
                    </button>
                    <p className="small muted">
                      저장 시각은 현재 시각으로 기록됩니다.
                    </p>
                    <p className="notice" role="status">
                      {notice}
                    </p>
                    {storageWarning && (
                      <p className="storage-warning" role="alert">
                        {storageWarning}
                      </p>
                    )}
                  </section>
                  {saved && (
                    <>
                      <section className="panel saved-panel">
                        <div className="saved-heading">
                          <Icon name="check" />
                          <h3>저장된 요청서</h3>
                        </div>
                        <p className="small muted">
                          실제 저장:{" "}
                          {saved.record?.made
                            ? new Date(saved.record.made).toLocaleString(
                                "ko-KR",
                              )
                            : ""}
                        </p>
                        <button
                          className="subtle-button full"
                          onClick={() =>
                            download(
                              `${saved.docNo}.md`,
                              saved.markdown,
                              "text/markdown;charset=utf-8",
                            )
                          }
                        >
                          <Icon name="download" />
                          요청서 Markdown 내려받기
                        </button>
                        <button
                          className="text-button"
                          onClick={() =>
                            download(
                              "earlysignal-decisions.json",
                              JSON.stringify(
                                {
                                  contract: "earlysignal-data-v1",
                                  decisions: records,
                                },
                                null,
                                2,
                              ),
                              "application/json",
                            )
                          }
                        >
                          판단 기록 JSON 내려받기{" "}
                          <Icon name="download" size={16} />
                        </button>
                      </section>
                      <section className="panel reveal-panel">
                        <p className="eyebrow">
                          AFTER-SAVE VERIFICATION · 사후 확인
                        </p>
                        <h3>접수일 기준으로 과거를 재현하면</h3>
                        <InvestigationComparison
                          available={saved.available}
                          investigation={postCase}
                        />
                        <button
                          className="text-button"
                          onClick={() => setView("validation")}
                        >
                          전체 사례와 놓친 사례 보기{" "}
                          <Icon name="arrow" size={16} />
                        </button>
                      </section>
                    </>
                  )}
                  {records.length > 0 && (
                    <section className="panel history-panel">
                      <h3>
                        이 브라우저의 판단 기록{" "}
                        <span className="teal">{records.length}</span>
                      </h3>
                      {records.slice(0, 5).map((r) => (
                        <div
                          className="history-row"
                          key={`${r.doc_no}:${r.made}`}
                        >
                          <b>
                            {model(r.grp)} · {categoryNames[r.category]}
                          </b>
                          <span>
                            {r.decision} ·{" "}
                            {new Date(r.made).toLocaleDateString("ko-KR")}
                          </span>
                        </div>
                      ))}
                    </section>
                  )}
                </aside>
              </div>
            ))}
          {view === "validation" && (
            <Validation meta={meta} cases={cases} />
          )}
        </main>
        <footer className="footer">
          <div>
            <span className="live-dot" aria-hidden="true" />
            <b>NHTSA 공개 파일 기반</b>
            <span>수리 기록 · 생산 기록 · 부품 이력은 미연동</span>
          </div>
          <p>
            현재 공개 파일의 접수일로 과거 재현 · 경보는 조사 후보 ·{" "}
            <SourceAttribution view={view} labeler={data.labeler} />
            <br />
            {meta.data_source.downloaded_at
              ? `원본 다운로드일 ${meta.data_source.downloaded_at}`
              : "원본 다운로드일 미확인"}
            {meta.data_source.observed_local_date &&
              ` · 로컬 파일 확인일 ${meta.data_source.observed_local_date}`}
          </p>
        </footer>
      </div>
    </div>
  );
}
function getSelectedN(
  series: ConsoleData["series"][string] | undefined,
  month: string,
  category: Category,
) {
  return series?.categories[category]?.n[series.months.indexOf(month)] ?? 0;
}
function getBaseline(
  series: ConsoleData["series"][string] | undefined,
  month: string,
  category: Category,
) {
  const v =
    series?.categories[category]?.baseline[series.months.indexOf(month)];
  return v == null ? "—" : v.toFixed(1);
}
function AlertRow({
  alert: a,
  active,
  onClick,
}: {
  alert: Alert;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button className={`alert-row ${active ? "active" : ""}`} onClick={onClick}>
      <span className="alert-indicator" />
      <div>
        <b>
          {model(a.grp)} <span>· {categoryNames[a.category]}</span>
        </b>
        <p>
          {a.n}건 / 평소 {a.baseline.toFixed(1)}건{" "}
          <span className="alert-status">
            {a.is_new ? "신규" : `연속 ${a.streak}개월`}
          </span>
        </p>
      </div>
      <strong>
        {a.ratio.toFixed(1)}
        <small>배</small>
      </strong>
      <Icon name="arrow" size={16} />
    </button>
  );
}
function ComplaintCard({
  id,
  complaint: c,
  cited,
  excluded,
  onMark,
}: {
  id: string;
  complaint: Complaint;
  cited: boolean;
  excluded: boolean;
  onMark: (kind: "cite" | "exclude") => void;
}) {
  const [expanded, setExpanded] = useState(false);
  if (!c) return null;
  return (
    <article
      className={`complaint-card ${cited ? "cited" : ""} ${excluded ? "excluded" : ""}`}
      id={`complaint-${id}`}
    >
      <div className="complaint-top">
        <span className="mono">#{id}</span>
        <span>
          접수 {dateLabel(c.ldate)} · {c.year}년식
        </span>
        {cited && <span className="review-badge">인용됨</span>}
        {excluded && <span className="review-badge">제외됨</span>}
      </div>
      <div className="complaint-flags">
        {c.flags.map((f) => (
          <span key={f}>{flagNames[f]}</span>
        ))}
      </div>
      {c.summary_ko && <p className="complaint-summary">{c.summary_ko}</p>}
      <p className={`original-text ${expanded ? "expanded" : ""}`}>
        <HighlightedText text={c.text} />
      </p>
      <div className="complaint-actions">
        <button
          className="text-button"
          aria-expanded={expanded}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "발췌 접기" : "원문 발췌 펼치기"}{" "}
          <span>{expanded ? "−" : "+"}</span>
        </button>
        <div>
          <button
            className={`cite-button ${cited ? "active" : ""}`}
            aria-pressed={cited}
            onClick={() => onMark("cite")}
          >
            <Icon name="check" size={15} />
            인용
          </button>
          <button
            className={`exclude-button ${excluded ? "active" : ""}`}
            aria-pressed={excluded}
            onClick={() => onMark("exclude")}
          >
            <Icon name="close" size={15} />
            제외
          </button>
        </div>
      </div>
    </article>
  );
}
function HighlightedText({ text }: { text: string }) {
  return (
    <>
      {text
        .split(
          /(\b(?:fire|smoke|flames?|burn(?:ed|ing)?|melt(?:ed|ing)?|while driving|stalled|lost power)\b)/gi,
        )
        .map((part, i) => (i % 2 ? <mark key={i}>{part}</mark> : part))}
    </>
  );
}
function MarkdownDocument({ markdown }: { markdown: string }) {
  return (
    <>
      {markdown.split("\n").map((line, i) => {
        if (!line.trim()) return null;
        if (line.startsWith("# "))
          return (
            <h2 key={i} className="paper-title">
              {line.slice(2)}
            </h2>
          );
        if (line.startsWith("## ")) return <h3 key={i}>{line.slice(3)}</h3>;
        if (line.startsWith("### ")) return <h4 key={i}>{line.slice(4)}</h4>;
        if (line === "---") return <hr key={i} />;
        const content = line.replace(/^[-*] /, "").replace(/\*\*/g, "");
        if (line.startsWith("|"))
          return (
            <p key={i} className="paper-table-row mono">
              {content}
            </p>
          );
        return (
          <p key={i} className={line.startsWith("- ") ? "paper-list" : ""}>
            {content}
          </p>
        );
      })}
    </>
  );
}
const priorInvestigationNote =
  "이전 청원·리콜 조사가 있었으며 최초 발견 시점과의 비교는 아닙니다.";

export function InvestigationComparison({
  available,
  investigation,
}: {
  available: string;
  investigation: RevealCase | undefined;
}) {
  return (
    <>
      <div className="date-comparison">
        <div>
          <span>월 집계 확인 가능일</span>
          <b>{dateLabel(available)}</b>
        </div>
        {investigation ? (
          <div>
            <span>지정 예비조사(PE) 개시 · {investigation.case_id}</span>
            <b>{dateLabel(investigation.odate)}</b>
          </div>
        ) : (
          <p className="muted small">이 신호에 연결된 예비조사 사례가 없습니다.</p>
        )}
      </div>
      {investigation && (
        <>
          <p className="lead-result">
            <b>
              {Math.abs(
                Math.round(
                  (Date.parse(investigation.odate) - Date.parse(available)) /
                    86400000,
                ),
              )}
            </b>
            <span>
              일<br />
              지정 PE 개시 {investigation.odate >= available ? "이전" : "이후"}
            </span>
          </p>
          {["PE19003", "PE19004"].includes(investigation.case_id) && (
            <p className="small muted">{priorInvestigationNote}</p>
          )}
        </>
      )}
    </>
  );
}

export function SourceAttribution({ view, labeler }: { view: View; labeler: ConsoleData["labeler"] }) {
  return view === "validation" ? (
    <>백테스트 출처: 키워드 기준선</>
  ) : (
    <>콘솔 분류 출처: {labeler === "keyword" ? "키워드 규칙" : "완료된 LLM 분류"}</>
  );
}

export function Validation({
  meta,
  cases,
}: {
  meta: MetaData;
  cases: CasesData;
}) {
  const [split, setSplit] = useState<"all" | "dev" | "holdout">("all");
  const visible = cases.cases.filter(
    (c) => split === "all" || c.split === split,
  );
  return (
    <div className="validation-content">
      <div className="validation-intro panel">
        <div>
          <p className="eyebrow">EVIDENCE, LIMITATIONS, NEXT STEPS</p>
          <h2>한 사례의 성공으로 끝내지 않았습니다.</h2>
          <p className="muted">
            지정 예비조사(PE) 사례와 대조 차종을 나눠 확인했습니다. 사례·대조의 백테스트와
            아래 사례 표는 키워드 기준선 결과입니다. 콘솔의 LLM 분류와 구분합니다.
          </p>
        </div>
        <span className="verification-tag">사후 검증 화면</span>
      </div>
      <div className="validation-cards">
        {(["dev", "holdout"] as const).map((s) => (
          <section key={s} className="panel validation-card">
            <p className="eyebrow">
              {s === "dev" ? "DEVELOPMENT SET" : "HOLDOUT SET"}
            </p>
            <h3>{s === "dev" ? "개발 사례" : "별도로 남겨둔 사례"}</h3>
            <div className="metric-pair">
              <div>
                <span>조사 사례에서 경보</span>
                <b>
                  {meta.validation[s].case.hits}
                  <small> / {meta.validation[s].case.n}</small>
                </b>
                <div className="metric-track">
                  <i
                    style={{
                      width: `${meta.validation[s].case.n ? (meta.validation[s].case.hits / meta.validation[s].case.n) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
              <div>
                <span>대조 차종에서 경보</span>
                <b>
                  {meta.validation[s].control.hits}
                  <small> / {meta.validation[s].control.n}</small>
                </b>
                <div className="metric-track control">
                  <i
                    style={{
                      width: `${meta.validation[s].control.n ? (meta.validation[s].control.hits / meta.validation[s].control.n) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          </section>
        ))}
        <section className="panel validation-card model-status">
          <p className="eyebrow">MODEL VALIDATION</p>
          <h3>LLM 분류 및 사람 검수</h3>
          <b className="model-number">
            {formatNumber(meta.labels.llm_labeled)}
            <small>건 분류·출력 검사</small>
          </b>
          <p className="muted small">
            모델: {meta.labels.llm_model || "미실행"}
            <br />
            사람 정답 검수: {meta.labels.human_check.n}건<br />
            사람 정답 기준 분류 정확도:{" "}
            {meta.labels.human_check.n > 0 && meta.labels.human_check.llm_correct != null
              ? `${meta.labels.human_check.llm_correct} / ${meta.labels.human_check.n}건 일치`
              : "미측정"}
            <br />
            1,000건 라벨 비용:{" "}
            {meta.labels.cost_per_1k_usd == null
              ? "미측정"
              : `$${meta.labels.cost_per_1k_usd.toFixed(2)}`}
          </p>
          <p className="model-note">
            미측정 값은 정확도 0% 또는 비용 0원을 의미하지 않습니다.
          </p>
        </section>
      </div>
      <section className="panel validation-table-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">ALL CASES · INCLUDING MISSES</p>
            <h2>놓친 사례도 함께 남깁니다.</h2>
          </div>
          <div className="split-filter">
            {(["all", "dev", "holdout"] as const).map((s) => (
              <button
                key={s}
                className={split === s ? "active" : ""}
                onClick={() => setSplit(s)}
              >
                {s === "all" ? "전체" : s === "dev" ? "개발" : "홀드아웃"}
              </button>
            ))}
          </div>
        </div>
        <p className="muted small">
          PE19003·PE19004: {priorInvestigationNote}
        </p>
        <div className="validation-table-scroll">
          <table className="validation-table">
            <thead>
              <tr>
                <th>조사 번호</th>
                <th>사례 · 대상 차종</th>
                <th>구분</th>
                <th>검증 결과</th>
                <th>지정 PE 개시 대비</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((c) => (
                <tr key={c.case_id}>
                  <td className="mono">{c.case_id}</td>
                  <td>
                    <b>{c.note}</b>
                    <p>{c.groups.map(model).join(", ")}</p>
                  </td>
                  <td>{c.split === "dev" ? "개발" : "홀드아웃"}</td>
                  <td>
                    <span className={`result-badge ${c.result}`}>
                      {c.result === "early"
                        ? "먼저 경보"
                        : c.result === "late"
                          ? "늦은 경보"
                          : "놓침"}
                    </span>
                  </td>
                  <td>
                    {c.lead_days == null
                      ? "경보 없음"
                      : `${Math.abs(c.lead_days)}일 ${c.lead_days >= 0 ? "이전" : "이후"}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <div className="validation-notes">
        <section className="panel">
          <p className="eyebrow">WHAT WE CHECKED</p>
          <h3>검증 방법과 한계</h3>
          <ul>
            {meta.validation_notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
          <p className="small muted">
            통계 규칙: {String(meta.params.rule)} · 유의수준{" "}
            {String(meta.params.alpha)} · 최소 {String(meta.params.min_count)}건
          </p>
        </section>
        <section className="panel">
          <p className="eyebrow">ADOPTION · NEXT VALIDATION</p>
          <h3>실제 도입에서 확인할 것</h3>
          <ul>
            <li>고객 안전 담당자의 월별 원문 검토·요청서 작성 업무에 연결</li>
            <li>수리 기록·생산 기록·부품 이력과 대조해 조사 착수 판단</li>
            <li>차량 운행 대수와 중복 신고를 확인해 신고 건수의 편향 검토</li>
            <li>
              실제 담당자의 검토 시간·누락 감소·반복 사용 의향은 아직 미검증
            </li>
          </ul>
          <p className="small muted">
            대조 차종 월평균 경보:{" "}
            {meta.burden.control_alerts_per_group_month == null
              ? "미측정"
              : meta.burden.control_alerts_per_group_month.toFixed(2) +
                "건"}{" "}
            · 도입 가치·구매 의향은 가정
          </p>
        </section>
      </div>
      <p className="small muted data-generated">
        데이터 생성: {new Date(meta.generated_at).toLocaleString("ko-KR")} ·{" "}
        {meta.data_source.name}
      </p>
    </div>
  );
}
