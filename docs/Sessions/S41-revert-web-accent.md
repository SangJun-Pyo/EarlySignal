# S41 — Step9 마지막 웹 시각 보완 되돌림

- 시각: 2026-10-09 (Asia/Seoul)
- 관련: SPEC Step9, ADR-022·028, 이슈 #40, PR #38

## 목표
사용자 요청에 따라 마지막 웹 디자인 merge만 되돌리고 직전 발표·PDF·데이터·기존 기능을 보존한다.

## 완료 기준
- [x] 코드 전 ADR028·세션 작성
- [x] 정확한 merge a9ffba8을 revert -m 1
- [x] web 전체 tree=39e6e07, PDF/data 변경0
- [x] 웹 tests/typecheck/build·diff 검사 통과
- [x] 이슈 연결·PR 및 독립 검수 준비

## Codex에 맡긴 일
별도 작업트리에서 정확한 revert와 후행 기록만 작성한다. 원본·API·DB·키·PDF 생성은 실행하지 않는다. ZIP은 별도 담당자 소유다.

## 결과
fetch 후 main HEAD가 정확히 `a9ffba8e92eb93ff9bd872317254ba4c0a1c8ecf`임을 확인했다. 이슈 #40과 ADR028·세션을 코드 전에 작성했다. `git revert -m 1 a9ffba8e92eb93ff9bd872317254ba4c0a1c8ecf --no-edit`로 정상 revert 커밋 `d0b0d086f313d2c9053d6c81a80e9341c77e57a1`을 만들었다. 원래 merge의 첫 부모는 발표 PR36 통합 `39e6e0739a428c6245030a22462f8ce1ff388fab`이다.

revert 직후 tracked 전체 tree가39e6e07과 동일했다. web tree SHA는 양쪽 모두 `42b587136d027500b8f654fcc587e2e5edfb6f57`이다. 후행 변경은 이번 이유·검수 기록과 색인뿐이며 PDF·data·pipeline·README 등은 그대로 보존한다. 장식 WebP와 제목·버튼의 추가 청록 강조가 제거됐고 기존 웹 기능은 이전 코드로 돌아갔다.

원래 [ADR027](https://github.com/SangJun-Pyo/EarlySignal/blob/a9ffba8e92eb93ff9bd872317254ba4c0a1c8ecf/docs/ADR/ADR-027-compact-web-pdf-accent.md)과 [S40](https://github.com/SangJun-Pyo/EarlySignal/blob/a9ffba8e92eb93ff9bd872317254ba4c0a1c8ecf/docs/Sessions/S40-web-pdf-accent.md)은 정확한 revert로 현재 파일에서 삭제됐지만 Git 역사와 [PR38](https://github.com/SangJun-Pyo/EarlySignal/pull/38)에 보존된다. 파일을 다시 복원하거나 이전 사용자 승인·검수 이력을 지우지 않았다.

root의 기존 node_modules를 APFS 복사로 재사용했고 심볼릭 링크는 만들지 않았다. 웹26 tests·typecheck·정적 build 통과, build prebuild hook의 기존26 tests도 통과했다. `git diff --check` 통과. API·원본자료·DB·키 접근과 PDF 생성은 하지 않았다. 실제 공개 배포 및 최신 ZIP은 총괄·별도 담당자의 후속 작업이며 여기서 완료했다고 주장하지 않는다.

## 문제와 해결
| 문제 | 원인 | 해결 | 누가 |
|---|---|---|---|
| 새 웹 시각 보완을 사용자가 원하지 않음 | 사용자 선호와 구현 결과가 맞지 않음 | 마지막 merge만 정확히 revert, 직전 웹 tree 대조 | Codex |

## 사람이 검토하며 고친 것
- 사용자가 최종 커밋만 되돌리고 최신 로그 ZIP을 요청했다. 이전 발표·PDF나 다른 기능을 되돌리라는 요청이 아니다.

## 다음 세션으로 넘길 것
- 독립 검수·병합·공개 배포 확인은 총괄, ZIP은 별도 담당자가 진행한다.
