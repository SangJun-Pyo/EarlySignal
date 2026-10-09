import type { Category, Flag } from "./types";
import { CATEGORY_NAMES } from "./request";
export const categories = CATEGORY_NAMES;
export const flags: Record<Flag, string> = {
  fire: "화재 기록",
  smoke: "연기 언급",
  driving: "주행 중",
  parked: "주차 중",
  crash: "충돌 기록",
  injury: "부상 기록",
  severe: "높은 심각도",
};
export const flagSourceLabel = (source: string) => {
  if (source.startsWith("NHTSA") && source.includes("LLM")) return "NHTSA 기록 또는 AI 분류";
  if (source.startsWith("NHTSA")) return "NHTSA 신고 기록";
  if (source === "keyword") return "키워드 규칙";
  if (source === "LLM severity >= 3") return "AI 심각도 분류";
  if (source === "LLM") return "AI 원문 분류";
  if (source === "unmeasured") return "미측정";
  return "출처 확인 필요";
};
export const model = (grp: string) => grp.split("|").slice(1).join("|");
export const make = (grp: string) =>
  grp.split("|")[0] === "HYUNDAI"
    ? "현대"
    : grp.split("|")[0] === "KIA"
      ? "기아"
      : grp.split("|")[0];
export const monthLabel = (month: string) =>
  `${month.slice(0, 4)}년 ${Number(month.slice(5, 7))}월`;
export const dateLabel = (date: string) =>
  date.slice(0, 10).replaceAll("-", ".");
export const formatNumber = (n: number) =>
  new Intl.NumberFormat("ko-KR").format(n);
