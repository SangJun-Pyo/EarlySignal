# S18 — Step 7 독립 사람 검수 30건 준비

- 시각: 2026-10-09 (오프라인)
- 관련: SPEC Step 7, ADR-020

## 목표
개발 시험 50건과 분리한 사람 검수 30건을 준비하고, 예측 가림·실제 송신 원문 일치·정답 보존을 검증한다.

## 완료 기준
- [x] seed42 개발 50건 제외, 새 seed의 독립 30건 고정 및 입력·모델·정책 잠금
- [x] private blind CSV·별도 대응표, 검수 지침, 정답·메모 재실행 보존
- [x] 유료 호출 없는 표본 누수·원문 일치·보존 테스트 및 실제 로컬 준비

## Codex에 맡긴 일
별도 준비 CLI·모듈과 최소 회귀 테스트를 구현한다. 기존 export 비교 CSV는 개발용으로 표시하고 덮어쓰지 않는다. 키·`.env` 읽기, API 호출, 정확도 계산·자동 사람 정답 생성은 하지 않는다.

## 결과
- ADR-020을 코드보다 먼저 기록했다. `pipeline/es/human_review.py` 전용 진입점으로 준비하며 공용 CLI의 `.env` 기반 설정 동작은 변경하지 않았다.
- 실제 demo 7,502건에서 seed42 개발 50건을 제외하고 `human-review-v1` 해시 순서의 30건을 고정했다. `data/private/human_review_independent30/blind.csv`에는 익명 검수 번호·실제 송신과 같은 비식별 원문 최대 1,500자·빈 정답 항목만 있다. ODI 대응표와 입력 해시·모델·프롬프트/스키마·인용 정책·지침 잠금은 별도 비공개 파일에 있다.
- `.venv/bin/python -m es.human_review --root <저장소> --quote-policy source-span-v1`: 첫 실행 `created=true`, 두 번째 실행 `created=false`, 두 번 모두 독립 30건·제외 50건·정답 작성 0건·`accuracy=null`·`api_calls=0`. 비공개 세 파일의 Git ignore도 확인했다. 키와 `.env`는 읽지 않았다.
- `.venv/bin/python -m pytest pipeline/tests/test_human_review.py pipeline/tests/test_import_llm.py -q`: **27 passed (5.08s)**. 표본 누수, 예측 가림, 정확한 송신 원문/해시, 변경 잠금, 사람이 작성한 정답·메모/행 정렬 보존, 개발 비교 CSV 보존을 확인했다. 모의 테스트에서는 API 클라이언트와 dotenv 호출 시 실패하도록 차단했다.
- `.venv/bin/python -m pytest pipeline/tests -q`: **174 passed (26.43s)**. 소유 파일의 `git diff --check` 통과.
- `sample60_compare.csv`는 개발 비교용으로 표시하는 sidecar를 추가하고 기존 파일을 덮어쓰지 않는다. 사람 정답은 독립 `blind.csv`만 권위 원본으로 삼는다. CSV 요청에 맞춰 별도 Excel 변환·AI 번역/요약은 만들지 않았다.

## 문제와 해결
| 문제 | 원인 | 해결 | 누가 |
|---|---|---|---|
| 기존 첫60건은 개발50건 포함 | 동일 seed42 순서 | 독립 seed와 개발 표본 제외 | Codex |
| 예측·AI요약이 정답 판단을 유도 | 비교 CSV를 검수 CSV로 사용 | 별도 blind 입력 | Codex |
| export가 정답 빈 칸으로 덮어씀 | 매번 새 CSV 작성 | 기존 개발 CSV 보존, 독립 정답 경로 | Codex |

## 사람이 검토하며 고친 것
- 사용자 선택: 독립 사람 검수 준비를 구현. 실제 정답은 사람이 작성하며 현재 미측정.

## 다음 세션으로 넘길 것
- 사람이 모델 예측을 보지 않고 주 라벨과 근거·애매함을 작성한 뒤, 고정 버전의 예측과 대조한다.
- 독립 검수에서 누락/추가 셀을 정상으로 받는 CSV 행 형식 검사 누락을 확인했다. 기존 정답을 덮어쓰지는 않는다. GitHub 이슈 #3으로 등록하고 별도 하위 브랜치에서 수정·재검수한다.
- 사용자가 30건을 직접 검수하겠다고 답해 실제 blind CSV와 판정 지침을 전달했다.
