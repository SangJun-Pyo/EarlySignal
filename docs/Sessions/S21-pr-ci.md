# S21 — PR 자동 검증

- 시각: 2026-10-09
- 관련: 이슈 #2, SPEC Step 6·8·9 검증, ADR-006

## 목표
PR에서 재현 가능한 Python·웹 검증을 실행하고 자동 검사와 수동 검수의 역할을 구분한다.

## 완료 기준
- [x] PR과 main push에 전체 Python 테스트·웹 테스트·타입 검사·정적 빌드 실행 구성
- [x] 원본 데이터·작업 DB·API 키 없이 최소 권한으로 실행
- [x] 로컬 검사와 실제 draft PR의 CI 성공 확인

## Codex에 맡긴 일
이슈 #2의 별도 managed worktree와 codex/pr-checks 브랜치에서 GitHub Actions를 추가하고 draft PR을 제출한다. 배포와 병합은 root가 맡는다.

## 결과
- 별도 `codex/pr-checks` worktree에서만 수정했다. 로컬 Git 작성자 설정은 `Sangjun Pyo`와 GitHub noreply 주소로 확인했다.
- `.github/workflows/pr-checks.yml`: PR 대상 `main` 및 `main` push, Python 3.10·3.13 전체 테스트와 Node `web/.node-version` 기반 웹 검사. `contents: read`, checkout 인증 비보존, PR/브랜치별 오래된 실행 취소, job별 15분 제한.
- 공식 actions 저장소의 v7 tag를 GitHub API로 조회하고 해당 commit SHA로 고정했다. ADR-006에 공식 출처를 기록했다.
- 깨끗한 worktree에 Python 3.12.14 전용 venv를 만들고 `python -m pip install -e '.[test]'` 후 **78 passed (31.53s)**. 원본 데이터·작업 DB·`.env`가 없는 checkout에서 전체 검사했다.
- Node 26.3.0에서 `npm ci` 성공, **웹 19 tests passed**, `npm run typecheck` 및 `npm run build` 성공. 기존 prebuild가 웹 테스트를 한 번 더 실행하는 동작도 유지했다.
- `git diff --check` 통과. [Draft PR #5](https://github.com/SangJun-Pyo/EarlySignal/pull/5) 제출·작업에 연결 완료.
- 실제 GitHub Actions [run 37876506109](https://github.com/SangJun-Pyo/EarlySignal/actions/runs/37876506109)는 commit `5889d00`에서 **3/3 jobs success**: Python 3.10 전체 검사·Python 3.13 전체 검사·웹 테스트/타입/정적 빌드. 테스트 제외·실패 무시·API 호출 없이 통과했다.

## 문제와 해결
| 문제 | 원인 | 해결 | 누가 |
|---|---|---|---|
| PR에 자동 검사 결과 없음 | 로컬 검사만 실행 | GitHub Actions 전체 검사 | Codex |

## 사람이 검토하며 고친 것
- 사용자 요청: 이슈·기능 브랜치·PR·별도 검수 방식으로 작업한다.

## 다음 세션으로 넘길 것
- 독립 검수 및 root의 병합 결정. CI는 원문 의미나 사람 정답 정확도, 공개 배포 동작을 보증하지 않는다.
