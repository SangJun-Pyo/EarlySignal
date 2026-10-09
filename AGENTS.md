# AGENTS.md — EarlySignal (Codex 작업 지침)

이 저장소에서 작업하는 Codex는 이 문서를 항상 먼저 따른다.

## 하네스 구조 (세 층)
| 층 | 위치 | 역할 |
|---|---|---|
| 1. 작업 틀 | `AGENTS.md`, `docs/Development/WORKFLOW.md`, `docs/SPEC.md` | 무엇을 어떤 순서·절차로 만드는가 |
| 2. 기록과 근거 | `docs/ADR/`, `docs/Sessions/`, `docs/Knowledge/LessonsLearned.md`, `docs/Contracts/` + 테스트 | 왜 그렇게 했고, 무엇을 확인했고, 무엇을 배웠는가 |
| 3. 기능 | `pipeline/`, `web/` | 실제 코드 |

현재 제품·실측은 `README.md`, `docs/Development/STATUS.md`, 현재 구현 명세는 `docs/SPEC.md`를 따른다. ADR·세션·사전 조사·history는 해당 시점의 기록이며 최신 기능 목록이 아니다.

기타 참고: 사전 조사 `docs/RESEARCH.md`, LLM 프롬프트 `docs/LLM_PROMPTS.md`, 발표 `docs/PRESENTATION.md`.
**작업 전 반드시 읽을 것**: 이 문서 → WORKFLOW → 해당 Step의 SPEC → 관련 ADR → 데이터 계약(웹·export 작업 시).

## 프로젝트 한 줄
미국 NHTSA 소비자 결함 신고(자유서술)를 LLM이 증상 라벨로 바꾸고, 차종×증상별 월간 신고 건수를 통계로 감시해 **조사해야 할 안전 신호를 더 일찍 찾는** 도구. 데모와 제품의 끝은 **조사 요청서**다: 담당자가 신호를 고르고, 원문을 검토해 인용·제외하고, 근거가 연결된 요청서를 확정·저장한다(ADR-009). 검증 결과는 그 접근이 맞았는지 보여주는 보조 화면이다.

- 리콜을 예측하거나 결함을 판정하는 시스템이 **아니다**. 화면·문서·커밋 메시지 어디에서도 "리콜 예측", "결함 확정", "원인 규명" 같은 표현을 쓰지 않는다.
- 역할 분담: **LLM = 측정**(원문 → 라벨, 요약), **통계 = 판단**(경보 여부), **사람 = 결정**(조사 착수/보류/기각).

## 절대 규칙
1. **미래 정보 차단.** 어떤 시점 t의 판단에는 `ldate`(NHTSA 접수일) ≤ t인 신고만 쓴다. `faildate`(사고일)로 집계하지 않는다. `COMPDESC`(부품 분류)는 사후 수정되므로 탐지 입력에 쓰지 않는다. 조사 파일의 `SUMMARY`, `CDATE`, `CAMPNO`는 정답지이므로 탐지 코드가 읽지 않는다. 이 규칙은 `pipeline/tests/test_lookahead.py`로 검증한다.
2. **소비자 신고만.** `CMPL_TYPE` ∈ {IVOQ, VOQ, EVOQ, MIVQ, MAVQ, MVOQ, SVOQ, LETR, CAG, CON, INS}, `PROD_TYPE`='V'. 건수는 `ODINO` 고유값으로 센다(한 신고가 부품별로 여러 행).
3. **파라미터는 dev 사례로만 조정**한다. holdout 결과를 보고 규칙을 바꾸지 않는다. 바꿨다면 그 사실과 이유를 `docs/CODEX_LOG.md`와 README에 적는다.
4. **실패를 숨기지 않는다.** 놓친 사례, 늦은 사례는 결과표와 화면에 그대로 남긴다.
5. **비밀값 금지.** `OPENAI_API_KEY`는 `.env`에만. `.env`, `data/raw/`, `*.duckdb`는 커밋하지 않는다. 화면·JSON에 VIN, 도시, 딜러, 운전자 이름 등 개인정보 필드를 넣지 않는다.
6. **숫자를 지어내지 않는다.** 화면과 문서의 모든 수치는 파이프라인 출력에서 나와야 한다. 데모용 가정(우선순위 가중치 등)은 화면에 "가정"이라고 표시한다. 디자인 시안의 숫자·차종명(GRANDEUR, AVANTE 등)은 자리 표시일 뿐이니 쓰지 않는다.
7. 경로를 하드코딩하지 않는다(맥·윈도우 모두 동작). 설정은 `pipeline/es/config.py`와 CLI 인자로.
8. **운영 대시보드는 기준일까지의 실제 값만** 그린다. 기준일 이후 실제 값은 검증 결과(사후 확인)에서만 보여준다. 전망 띠(평소 범위, 추세 연장=가정)는 P2이며, 넣는다면 기준일까지의 데이터로만 계산한다(ADR-002, ADR-007).
9. **요청서·대표 신고 요약의 모든 숫자와 #신고번호는 실제 근거에 연결**된다. ADR-024에 따라 모델은 제공된 근거에서 대표 신고 번호 1~3개만 선택하며 새 종합 문장을 쓰지 않는다. 첫 통계문은 실제 경보 값으로 만들고, 그 뒤는 선택한 기존 `summary_ko`를 `(#번호) 기존 요약`으로 그대로 인용한다. 번호는 해당 칸 `evidence.ids`와 실제 제공된 번호 안에 있어야 한다(`tests/test_request.py`, `web/tests/request.test.ts`). 수량·개인정보·원인·결함 단정 검사를 유지하며 기존 AI 요약의 의미는 담당자가 원문과 대조한다.
10. **범위 고정**: "경보 선택 → 근거 검토 → 요청서 저장" 흐름은 배포 완료했다. SPEC §1의 미구현·후속 항목은 현재 기능으로 설명하지 않으며, 추가 요청에 따라 별도 이슈·검증 범위로 진행한다.

## 작업 방식 (WORKFLOW.md의 5단계: 계획 → 구현 → 검증 → 기록 → 커밋)
- 한 번에 `docs/SPEC.md`의 Step 하나만 구현한다. 시작할 때 `docs/Sessions/S{번호}-{step}.md`를 `_TEMPLATE.md`로 만들고, 끝나면 그 Step의 **완료 기준**을 실제로 실행해 결과 숫자를 세션 로그에 적는다.
- 설계 결정이 새로 생기거나 기존 ADR과 다르게 가야 하면 **코드보다 먼저** ADR을 추가/수정한다(009번부터).
- `web/`과 `export.py`는 `docs/Contracts/data-contract-v1.md`를 기준으로 한다. 형식을 바꾸면 계약 문서 → 스키마 → 타입 → 테스트를 함께 바꾼다.
- 다음에도 쓸 교훈은 `docs/Knowledge/LessonsLearned.md`에 L-11부터 한 줄씩.
- 커밋은 Step 단위로 작게: `stepN: <무엇을>` (예: `step5: poisson detector + lookahead test`). 세션 로그를 같은 커밋에 포함. 이력을 rebase/squash로 지우지 않는다.
- 사용자 선택(2026-10-09, ADR-022)에 따라 발견한 문제는 GitHub 이슈로 추적한다. 구현은 `codex/` 기능 브랜치, 병렬 수정은 별도 worktree, 통합은 PR과 구현자 외 독립 검수를 거친다. 기존 이력을 보존하는 merge commit을 사용한다.
- `docs/CODEX_LOG.md`(세션 색인)에 한 줄 추가: 세션 번호, Step, 핵심 결과, 사람이 고친 것.
- 확신이 없는 데이터 사실은 추측하지 말고 실제 데이터로 확인하는 짧은 쿼리를 먼저 실행한다.
- 시간이 부족하면 SPEC의 우선순위(P0 → P1 → P2) 순서를 지킨다. P0이 끝나기 전에 화면을 꾸미지 않는다.

## 기술 스택
- 파이프라인: Python 3.10+, duckdb, pandas, numpy, scipy, pyyaml, python-dotenv, openai, pytest
- 웹: Next.js(App Router, `output: "export"` 정적 사이트) + TypeScript + Tailwind CSS v4 + Recharts
- 배포: 사용자 선택(2026-10-09)에 따라 정적 `web/out`을 Cloudflare Pages에 올린다. 서버 없음. 데이터는 `web/public/data/*.json`.

## 심사 기준과 이 저장소의 대응 (작업 우선순위 판단에 사용)
| 심사 항목 | 저장소에서 보여줄 것 |
|---|---|
| 문제 정의와 필요성 | README 상단, `docs/PRESENTATION.md` |
| AI 판단과 해결 방식 | LLM 라벨러(`label_llm.py`)와 통계 탐지(`detect.py`)의 역할 분리, 근거 신고 표시 |
| 작동하는 결과물 | 배포된 웹(신고 원문 → 신호와 근거 → 조사 요청서, 보조 검증 결과), 재현 명령 |
| 검증과 개선 | dev/holdout·대조군 결과표, 미래 정보 차단 테스트, 키워드 vs LLM 비교, 실패 사례와 당일 개선 내역 |
| 사업성·도입 가능성 | 관측 경보량·누적 실험 비용(현업 업무량·정확한 건당단가는 미측정), 도입 대상과 운영 방식(README) |
| Codex 활용 과정 | 하네스(AGENTS·WORKFLOW·SPEC), 전체 세션 로그, ADR, LessonsLearned, Step 단위 커밋, `docs/CODEX_LOG.md` 색인 |
