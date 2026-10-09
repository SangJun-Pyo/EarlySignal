# S22 — Step 7 사람 검수 CSV 행 무결성

- 시각: 2026-10-09, 구현·합성 검증·독립 검수 완료
- 관련: SPEC Step 7, ADR-020, GitHub 이슈 #3, 상위 PR #4

## 목표
SPEC Step 7의 사람 검수 정답 열을 보존한다. 누락·추가 셀이 있는 기존 CSV는 손상으로 거부하고 정상적인 빈 정답·메모는 그대로 허용한다. 전체 라벨링 완료 기준이나 표집·인용 정책은 이번 수정 범위가 아니다.

## 완료 기준
- [x] `_read_csv`가 모든 행의 키 집합과 문자열 셀을 확인한다.
- [x] 누락·추가 셀 거부와 정상 빈 문자열 허용을 합성 테스트로 확인한다.
- [x] 거부·재개 시 기존 정답·메모·대응표·manifest 바이트 보존을 검증한다.
- [x] 관련 테스트 통과 후 독립 검수가 가능한 변경을 준비한다.

## Codex에 맡긴 일
전용 worktree의 `codex/human-csv-integrity`에서 이슈 #3을 수정한다. 원본 데이터·실제 비공개 검수 파일·키·`.env`를 읽지 않고 합성 데이터로 검증한다. API 호출은 하지 않는다.

## 결과
- 구현 전 ADR-020에 행 무결성 규칙을 기록했다.
- 커밋 작성자는 상속된 저장소 설정 `Sangjun Pyo <87307274+SangJun-Pyo@users.noreply.github.com>`을 사용한다.
- `PYTHONPATH=<worktree>/pipeline <기존 환경>/bin/python -m pytest pipeline/tests/test_human_review.py -q`: **20 passed** (1.70초). blind/mapping 각각의 누락·추가·추가 빈 셀 6개 조합과 정상 빈 셀 재개를 포함한다.
- `git diff --check`: 통과. 테스트는 임시 폴더의 합성 원문·검수 파일·DB만 사용했다. 실제 데이터·비공개 정답·환경 파일 읽기와 API 호출은 0회다.
- 라벨러·프롬프트·인용 정책 파일은 바꾸지 않았으므로 잠긴 manifest를 재생성하지 않는다.
- draft PR 대상: `codex/human-csv-integrity` → `codex/llm-evidence-validation` (상위 PR #4). 구현자 외 독립 검수 후 통합은 주 작업에서 수행한다.
- [PR #6](https://github.com/SangJun-Pyo/EarlySignal/pull/6), 구현 커밋 `8f57b9e`: 독립 검수자가 같은 합성 테스트 **20 passed** (1.59초), 파일 보존·정책 불변·작업 트리 clean을 확인했다. 차단 사항 없음.
- 상위 브랜치 `68861c8`을 rebase 없이 merge commit으로 가져왔다. CODEX_LOG의 유일한 충돌은 상위 S15·S17·S20과 하위 S22를 모두 보존하여 해결했고 R05·S21도 유지했다. 구현 코드는 추가 변경하지 않았다. 병합 상태에서 관련 테스트 **20 passed** (1.50초), diff 검사 통과.

## 문제와 해결
| 문제 | 원인 | 해결 | 누가 |
|---|---|---|---|
| 누락·추가 셀을 손상으로 처리하지 않음 | 헤더만 검사하고 DictReader의 None 값·키를 허용 | 모든 행의 명시된 열 및 문자열 셀 검증 | Codex |

## 사람이 검토하며 고친 것
- 사용자 선택에 따라 이슈 → 기능 브랜치/별도 worktree → PR → 독립 검수 순서를 따른다.

## 다음 세션으로 넘길 것
- 독립 검수 후 상위 브랜치에 merge commit으로 통합한다. 실제 비공개 정답 파일은 이 작업에서 읽거나 변경하지 않는다.
