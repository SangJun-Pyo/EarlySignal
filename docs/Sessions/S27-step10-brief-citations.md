# S27 — Step 10 상황 요약의 문장별 인용 실패 수정

- 시각: 2026-10-09 구현·오프라인·PR CI 검증 완료
- 관련: SPEC Step 10, ADR-015, ADR-023, 이슈 #12

## 목표
제공된 신고 밖의 사실 금지, 모든 주장에 같은 칸 #ODINO 인용, 원인·결함 단정 금지라는 Step 10 기준을 유지하면서 실제 상황 요약 인용 실패를 수정한다.

## 완료 기준
- [x] 인용 없는 문장과 제공되지 않은 번호를 거부하는 오프라인 회귀 검사
- [x] 관련 상황 요약·요청서·계약 테스트 및 전체 Python 테스트
- [x] §1 라벨링 프롬프트 변경 없음 확인
- [x] Step 커밋·Draft PR·실제 CI 결과 확인
- [x] 독립 검수 및 동일 18개 경보 실제 재실행은 총괄에 전달 (실행 결과는 후속 통합 기록)

## Codex에 맡긴 일
Astra 총괄이 이슈 #12를 구현 에이전트에 배정했다. 별도 managed worktree와 `codex/brief-citations` 브랜치에서 `brief.py`, `test_brief_generation.py`, `LLM_PROMPTS.md` §2, ADR-023, 이 세션만 수정한다. 전체 검사에서 종단 export 테스트의 주입 mock 1곳이 이전 narrative 응답을 반환해 실패했다. 총괄 동의를 받아 `test_import_llm.py`의 응답 생성 한 줄을 새 내부 형식으로 바꿨으며 다른 라벨 검사는 그대로다. CODEX_LOG 색인은 총괄 담당이다. DB·키·실제 API에는 접근하지 않는다.

## 결과
- 관련 검사: `PYTHONPATH=pipeline .venv/bin/python -m pytest pipeline/tests/test_brief_generation.py pipeline/tests/test_request.py pipeline/tests/test_contract.py pipeline/tests/test_import_llm.py -q` → 96 passed.
- 전체 Python 검사: `PYTHONPATH=pipeline .venv/bin/python -m pytest -q` → 193 passed. Python 런타임은 원 checkout의 `.venv/bin/python`을 사용하고 모듈은 이 worktree의 `pipeline`을 사용했다. 주입 클라이언트와 임시 합성 자료만 사용한다.
- `git diff --check` 통과. 변경 전후 §1 라벨링 프롬프트와 §3 요청서 구조의 문자열 동일 확인.
- 기존 `validate_brief()`·`compose_brief()`·재시도 상한·사용량 로깅 코드 변경 없음. 새 회귀는 첫 문장 무인용/둘째 문장 정상 인용, 빈 인용, 존재하지 않는 번호와 같은 칸이지만 미제공 번호, 복수 문장, text 인용 표식, 빈 응답, 이전 응답 형식과 성공 문장별 인용 렌더를 검사한다.
- 코드 커밋 `5a828b8`, [Draft PR #15](https://github.com/SangJun-Pyo/EarlySignal/pull/15), base `codex/llm-evidence-validation`. [실제 CI run 37879078169](https://github.com/SangJun-Pyo/EarlySignal/actions/runs/37879078169): Python 3.10·3.13 전체 테스트, 웹 테스트·타입 검사·정적 빌드 성공. Cloudflare Pages check도 성공하나 이번 세션은 브라우저 의미 검수·실제 API 실행을 하지 않았다. 총괄은 구현자 외 에이전트 `brief_finish`에 독립 검수를 배정했다.

실제 실패 18경보/54응답 및 추가 진단 1응답은 이슈 #12·ADR-023에 보존한다. 구현 세션은 합성 테스트만 사용한다.

## 문제와 해결
| 문제 | 원인 | 해결 | 누가 |
|---|---|---|---|
| 문장 인용 누락과 제공되지 않은 번호 | 상충하는 프롬프트와 자유 인용 문자열 | 문장별 text/citation_ids, 호출별 enum, 코드 인용 렌더 및 기존 검증 유지 | Codex |

## 사람이 검토하며 고친 것
- 도메인 지식·시간 제약으로 사람 정답 검수 취소. 분류 정확도 미측정이며 합성 테스트를 정확도 결과로 표시하지 않는다.

## 다음 세션으로 넘길 것
- 독립 검수 후 총괄이 동일 18개 경보의 첫 1건을 실제 확인하고 나머지를 실행한다. 통과한 요약만 공개한다.
