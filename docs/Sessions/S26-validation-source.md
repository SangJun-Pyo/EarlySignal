# S26 — Step 9 검증 결과의 키워드 출처 유지

- 시각: 2026-10-09
- 관련: 이슈 #11, SPEC Step 8·9, ADR-013, data-contract-v1

## 목표
콘솔이 LLM이어도 등록 사례·대조의 주 백테스트 출처를 키워드 기준선으로 표시한다. 라벨링 건수와 사람 정답 정확도를 구분한다.

## 완료 기준
- [x] 검증 화면과 관련 출처 표시가 console.labeler를 백테스트 출처로 사용하지 않음
- [x] LLM 분류 건수와 미측정 사람 정확도 구분, 렌더 회귀 검사
- [x] 웹 테스트·타입 검사·정적 빌드 및 draft PR CI 성공

## Codex에 맡긴 일
별도 `codex/validation-source` worktree에서 검증 화면의 표시만 작게 수정한다. 데이터 계약·탐지 규칙·공개 데이터·파이프라인은 변경하지 않는다. API·DB·사람 정답 파일을 사용하지 않는다.

## 결과
- `Validation`의 불필요한 console prop을 제거했다. 소개와 사례 표의 출처는 기존 계약대로 키워드 기준선으로 고정했다. 검증 화면 footer도 백테스트 출처를 표시하며 다른 화면 footer는 실제 console 분류 출처를 유지한다.
- 분류 건수·사람 정답 검수 건수는 기존 meta 값을 그대로 표시한다. 사람 정답 분모가 0이거나 판정 수가 null이면 분류 정확도를 미측정으로 표시한다. 사람 검수 기능을 재개하거나 정답을 작성하지 않았다.
- 다른 `data.labeler` 표시를 확인했다. 신고 더미·근거 검토·요청서는 console 모집단을 사용하므로 해당 출처를 유지한다. 데이터·메타 수치·cases 표·계약·탐지 규칙은 변경하지 않았다.
- 실제 컴포넌트 SSR 회귀 4건을 추가했다: keyword/llm 콘솔 모두 주 백테스트는 keyword, 라벨 건수와 미측정 정확도 분리, 0건 정답을 0% 성적으로 계산하지 않음, 요청서 footer의 실제 콘솔 출처 유지. 합성 모델 메타와 커밋된 공개 cases/meta를 사용했다.
- Node 26.3.0에서 `npm ci` 성공, `npm test` **23 passed**, `npm run typecheck` 및 `npm run build` 성공(정적 3/3 페이지 생성). `git diff --check` 통과. API·DB·사람 정답 CSV·비밀값을 사용하지 않았다.
- [Draft PR #14](https://github.com/SangJun-Pyo/EarlySignal/pull/14)를 부모 `codex/llm-evidence-validation` 대상으로 제출하고 작업에 연결했다. commit `3735f80`의 [실제 Actions run 37878692430](https://github.com/SangJun-Pyo/EarlySignal/actions/runs/37878692430)에서 Python 3.10·3.13 전체 테스트 및 웹 23개/타입/빌드의 **3/3 jobs가 성공**했다. 이 결과 기록 후 최신 head의 CI도 확인해 총괄에 전달하며, 동일 성공을 다시 기록하는 문서 커밋을 반복하지 않는다.

## 문제와 해결
| 문제 | 원인 | 해결 | 누가 |
|---|---|---|---|
| 38사례 키워드 결과를 LLM으로 표시 | 콘솔 labeler를 주 검증에 재사용 | 계약에 고정된 키워드 출처와 콘솔 분류 출처 분리 | Codex |

## 사람이 검토하며 고친 것
- 총괄 사전 점검에서 전체 LLM 콘솔 전환 시 출처 오류 발견, 이슈 #11로 추적.

## 다음 세션으로 넘길 것
- 독립 검수와 부모 PR #4 통합·배포는 root가 진행한다.
