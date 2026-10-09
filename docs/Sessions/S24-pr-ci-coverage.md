# S24 — PR 자동 검증 대상 확장

- 시각: 2026-10-09, 구현·실제 CI·독립 검수 완료
- 관련: ADR-022, GitHub 이슈 #8, S21의 CI 구성 후속

## 목표
기능 브랜치를 대상으로 한 하위 PR에도 기존 Python·웹 검사를 실행한다. PR #6에서 `main` 대상 필터 때문에 검사가 실행되지 않은 문제를 해결한다.

## 완료 기준
- [x] `pull_request`의 브랜치 제한만 제거한다.
- [x] `main` push·읽기 권한·작업 구성·기존 보안 경계가 유지되는지 확인한다.
- [x] `main` 이외 브랜치를 대상으로 한 실제 PR의 Python·웹 CI가 모두 통과한다.
- [x] 구현자 외 독립 검수 결과를 확인한다.

## Codex에 맡긴 일
기존 clean managed worktree에서 상위 기능 브랜치를 기준으로 `codex/ci-all-pr-bases`를 만든다. 모델·API·제품 데이터·원본·실제 비공개 파일·키는 건드리지 않는다. 작은 커밋과 draft PR로 검토한다.

## 결과
- ADR-022 변경 이력을 구현 전에 기록했다.
- 기준 커밋: `205f5aa` (`origin/codex/llm-evidence-validation`, PR #6 병합).
- 로컬 YAML 구조 비교: PR 필터만 제거됐고 `main` push·권한·동시 실행·모든 작업이 기존과 같음을 확인했다. `pull_request_target`은 없다. `git diff --check` 통과.
- [하위 PR #9](https://github.com/SangJun-Pyo/EarlySignal/pull/9)의 기준 브랜치는 `codex/llm-evidence-validation`이다. 구현 커밋 `61e58c1`에서 `pull_request` 이벤트 [Actions 실행 37877178594](https://github.com/SangJun-Pyo/EarlySignal/actions/runs/37877178594)가 실제 실행됐으며 **3/3 jobs 성공**했다.
- Python 3.10: **181 passed** (12.60초). Python 3.13: **181 passed** (14.18초). 웹 테스트·타입 검사·정적 빌드 작업 성공. CI 로그를 확인한 결과이며 로컬 테스트로 대신한 수치가 아니다.
- 구현자 외 독립 검수자가 구현 커밋 `61e58c1`의 한 줄 변경과 `main` push·권한·credentials·고정 SHA·작업·동시 실행·timeout 불변을 대조했다. 실제 하위 PR Actions 이벤트와 세 작업의 성공·로그 수치도 별도로 확인했으며 차단 사항은 없었다. Cloudflare Pages 검사도 통과했다.

## 문제와 해결
| 문제 | 원인 | 해결 | 누가 |
|---|---|---|---|
| 하위 PR 검사 누락 | pull_request.branches가 main만 포함 | PR 대상 브랜치 필터 제거 | Codex |

## 사람이 검토하며 고친 것
- 사용자가 선택한 이슈·하위 브랜치·PR·독립 검수 방식에 맞춰 자동 검사 범위도 적용한다.

## 다음 세션으로 넘길 것
- 실제 Actions 통과와 독립 검수 후 주 작업에서 merge commit으로 통합한다.
