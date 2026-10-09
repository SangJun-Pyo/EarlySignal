# ADR 목록

설계 결정 기록. 10/8 사전 조사에서 정한 결정은 '사전 작업'이고, ADR-001~009는 사전 결정이며 당일 새 결정은 ADR-010부터 추가한다(기존 ADR을 고칠 때는 '변경 이력'을 덧붙인다).

| 번호 | 제목 |
|---|---|
| [ADR-001](ADR-001-monitoring-unit.md) | 감시 단위는 브랜드+모델(연식 통합) |
| [ADR-002](ADR-002-time-basis.md) | 시간 기준은 NHTSA 접수일(LDATE), 판단 시점 이후 정보는 쓰지 않는다 |
| [ADR-003](ADR-003-detection-rule.md) | 탐지 규칙: 직전 12개월 포아송 기준선, p<0.001 그리고 3건 이상 |
| [ADR-004](ADR-004-ai-roles.md) | AI 역할 분담: LLM=측정, 통계=판단, 사람=결정 |
| [ADR-005](ADR-005-validation-design.md) | 검증 설계: 기계적 사례 선정, dev/holdout, 대조군, 12개월 선행 창 |
| [ADR-006](ADR-006-static-delivery.md) | 배포: 미리 계산한 JSON + Next.js 정적 사이트 |
| [ADR-007](ADR-007-dashboard-encoding.md) | 대시보드 표현: 히트맵 색=평소 대비 배수, 기준일 이후는 두 개의 전망 띠, 데이터 연결 현황은 사실대로 |
| [ADR-008](ADR-008-privacy-and-sources.md) | 개인정보 제외와 출처 명시 |
| [ADR-009](ADR-009-demo-goal-investigation-request.md) | 데모 목표 = 조사 준비 끝내기, 주인공 = 조사 요청서 |
| [ADR-010](ADR-010-parallel-work-and-evidence.md) | 병렬 개발·독립 검수·발표 근거 통합 |
| [ADR-011](ADR-011-retrospective-time-boundaries.md) | 접수일 기준 회고 분석과 완성월 경계 |
| [ADR-012](ADR-012-text-privacy-and-label-provenance.md) | 자유서술 식별정보 제거와 라벨 출처 |
| [ADR-013](ADR-013-complete-llm-cache-and-scope.md) | 완전한 LLM 캐시만 연결하고 주 검증 기준선을 보존 |
| [ADR-014](ADR-014-fixed-pilot-and-rate-deferral.md) | 승인 표본 고정과 서버 대기 시간 준수 |
| [ADR-015](ADR-015-bounded-evidence-brief-generation.md) | 근거 범위를 제한한 상황 요약과 캐시 재검증 |
| [ADR-016](ADR-016-retrieval-for-evidence-review.md) | 분류 검증 후 유사 근거 검색 보완 설계 |
| [ADR-017](ADR-017-submitted-proposal-and-delivery-scope.md) | 제출 기획과 실제 구현의 차이·판단 이유 |
| [ADR-018](ADR-018-label-quote-diagnostics.md) | 인용 실패 진단과 실제 원문 후보 선택 |
| [ADR-019](ADR-019-investigation-hypotheses-design-only.md) | 조사 가설과 확인 절차는 후속 설계로 구분 |
| [ADR-020](ADR-020-independent-blind-human-review.md) | 개발 표본과 분리한 예측 비공개 사람 정답 검수 |
| [ADR-021](ADR-021-approved-full-labeling.md) | 승인된 전체 분류와 고정 시험 결과 분리 |
| [ADR-022](ADR-022-issue-branch-pr-review.md) | 이슈·브랜치·PR·독립 검수 연결 |
| [ADR-023](ADR-023-structured-brief-citations.md) | 문장별 상황 서술 실험 — ADR-024로 대체 |
| [ADR-024](ADR-024-source-summary-selection.md) | 대표 ID 선택과 기존 신고별 AI 요약 그대로 인용 |
| [ADR-025](ADR-025-designated-pe-comparison-context.md) | 선행 기간은 지정 예비조사(PE) 개시일과 비교 |

## 기록을 읽는 기준

ADR은 결정 당시의 근거를 보존한다. 승인 한도·작업 진행 상태·자유 서술·전망 띠처럼 달라진 항목은 각 문서 상단의 후속 상태를 우선한다. 최신 제품·미구현 범위는 [현재 명세](../SPEC.md), 실행 결과는 [현재 상태](../Development/STATUS.md)와 [작업 색인](../CODEX_LOG.md)에 있다. 역사 기록의 과거 수치를 현재 성능으로 인용하지 않는다.

## 새 ADR 양식
```
# ADR-0NN: 제목
- 상태: 제안/채택/대체(ADR-0XX)
- 날짜:
## 배경
## 결정
## 결과와 트레이드오프
```
