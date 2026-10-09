export type Category = "fire_thermal" | "electrical_failure" | "loss_of_power" | "engine_stall" | "engine_failure" | "airbag" | "brakes" | "steering" | "seat_belt" | "fuel_leak" | "transmission" | "lighting" | "suspension" | "structure_body" | "tires_wheels" | "other";
export type LabelSource = "keyword" | "llm";
export type Flag = "fire" | "smoke" | "driving" | "parked" | "crash" | "injury" | "severe";
export interface Complaint { grp: string; month: string; ldate: string; year: string; flags: Flag[]; categories: Category[]; severity: number | null; injured: number; summary_ko: string | null; text: string; label_source: LabelSource }
export interface Alert { grp: string; category: Category; n: number; baseline: number; ratio: number; p_value: number; streak: number; is_new: boolean; comove: string[] }
export interface Series { months: string[]; total: number[]; categories: Partial<Record<Category, { n: number[]; baseline: (number | null)[]; alert: boolean[] }>> }
export interface Evidence { n: number; agg: Record<Flag, number>; co: [Category, number][]; years: [string, number][]; ids: string[] }
export interface RevealCase { case_id: string; make: string; title: string; odate: string; first_alert_month: string | null; first_alert_grp: string | null; first_alert_category: Category | null; available: string | null; lead_days: number | null; groups?: string[] }
export interface ConsoleData {
  contract: "earlysignal-data-v1"; labeler: LabelSource; labeling_note: string; flag_sources: Record<Flag, string>;
  asof_months: string[]; default_asof: string; demo_signal: { grp: string; category: Category; month: string };
  groups: string[]; categories: Category[]; series: Record<string, Series>;
  snapshots: Record<string, { kpi: { complaints: number; complaints_prev: number; alerts: number; alerts_prev: number; fire_alert_models: number }; alerts: Alert[] }>;
  complaints: Record<string, Complaint>; pile: Record<string, string[]>; evidence: Record<string, Evidence>; briefs: Record<string, string>;
  reveal: { cases: RevealCase[]; series_after: Record<string, unknown> };
  sources: { name: string; status: "connected" | "not_connected"; count?: number }[]; assumptions: string[];
}
export interface Metric { hits: number; n: number }
export interface MetaData { contract: "earlysignal-data-v1"; generated_at: string; data_source: { name: string; downloaded_at: string | null; observed_local_date: string; license: string }; params: Record<string, string | number>; validation: Record<"dev" | "holdout", Record<"case" | "control", Metric>>; burden: { case_alerts_per_group_month: number | null; control_alerts_per_group_month: number | null }; labels: { llm_model: string | null; llm_labeled: number; sample_agreement: { agree: number; n: number }; human_check: { n: number; kw_correct: number | null; llm_correct: number | null }; cost_per_1k_usd: number | null }; validation_notes: string[] }
export interface CaseResult { case_id: string; split: "dev" | "holdout"; investigation: string; note: string; groups: string[]; target_categories: Category[]; odate: string; result: "early" | "late" | "missed"; lead_days: number | null; first_alert_month: string | null; first_alert_group: string | null; first_alert_category: Category | null; has_llm: boolean }
export interface CasesData { contract: "earlysignal-data-v1"; cases: CaseResult[]; controls: { group: string; ref_date: string; matched_to: string }[] }
export type DecisionKind = "조사 착수" | "보류" | "기각";
export interface Decision { doc_no: string; made: string; analysis_available: string; grp: string; category: Category; decision: DecisionKind; actions: string[]; memo: string; cited: string[]; excluded: string[]; brief_cited: string[] }

export interface CaseDetail { contract: "earlysignal-data-v1"; case_id: string; labeler: LabelSource; odate: string; target_categories: Category[]; groups: Record<string, Series>; alerts: { id: string; grp: string; category: Category; month: string; observed: number; baseline: number; p_value: number; is_target: boolean; available: string; brief: string | null; evidence: { odino: string; ldate: string; fire: boolean; crash: boolean; injured: number; summary_ko: string | null; snippet: string }[] }[]; coverage?: { source: "demo"; start: string; end_exclusive: string; registered_window_complete: boolean } }
