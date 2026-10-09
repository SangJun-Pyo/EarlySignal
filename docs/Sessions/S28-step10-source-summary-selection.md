# S28 — Step 10 기존 신고별 AI 요약 선택·인용

- 시각: 2026-10-09 구현·오프라인·PR CI 검증 완료
- 관련: SPEC Step 10, ADR-015, ADR-023, ADR-024, 이슈 #12

## 목표
새로운 상황 종합을 생성하지 않고 제공된 신고별 AI 요약을 그대로 번호에 연결한다. 모든 주장에 실제 같은 칸 근거를 연결하고 수량·개인정보·단정·미래 정보 검증을 유지한다.

## 완료 기준
- [x] selected_ids 1~3개, 제공된 최대 10개 번호 enum, 중복·범위 밖 선택 거부
- [x] 기존 summary_ko 문자열·마침표를 그대로 줄별 인용하며 복수 문장·숫자 등을 고치지 않고 실패 처리
- [x] 자유 서술 캐시 무효화 및 선택 ID로 재구성한 캐시 문자열 정확 일치 검사
- [x] 관련·전체 Python 테스트, §1 프롬프트 불변 확인
- [x] Step 커밋·Draft PR·attach·실제 CI, 후속 문서 커밋 최대 1회
- [x] 독립 검수·실제 API 실행은 총괄에 전달 (실제 실행 결과는 후속 통합 기록)

## Codex에 맡긴 일
기존 managed worktree를 재사용해 `e4d7c38`에서 `codex/brief-source-selection` 브랜치를 만들었다. `brief.py`, 관련 Python 테스트, LLM_PROMPTS §2, ADR-024, S28을 담당한다. 웹 표시명은 별도 에이전트 S29 담당, CODEX_LOG는 총괄 담당이다. API·작업 DB·키·분류 캐시에 접근하지 않는다.

## 결과
- 관련 검사: `PYTHONPATH=pipeline /Users/sangjpyo/EarlySignal/.venv/bin/python -m pytest pipeline/tests/test_brief_generation.py pipeline/tests/test_request.py pipeline/tests/test_contract.py pipeline/tests/test_import_llm.py -q` → 116 passed.
- 전체 Python: 같은 런타임으로 `-m pytest -q` → 213 passed. 원 checkout 런타임과 이 worktree의 모듈, 주입 클라이언트·임시 합성 자료만 사용했다.
- `git diff --check` 통과. §1 라벨 프롬프트와 §3 요청서 구조 문자열 동일, `validate_brief`·`narrative_sentences`·`statistics_sentence` AST 동일 확인. `compose_brief`는 통계와 인용 줄 사이 구분자만 공백에서 줄바꿈으로 변경했다.
- 회귀: 선택 0/4개·중복·미제공·다른 칸 번호·추가 자유 서술·이전 응답 형식 거부, 원본 마침표/따옴표 보존, 숫자·단정·복문·공백 등 실패 후 원본 불변, 선택 ID/인용 문자열 캐시 변조·이전 자유 서술 캐시 거부, 재시도·사용량·개인정보 입력 경계 유지.
- 코드 커밋 `34ec51a`, [Draft PR #18](https://github.com/SangJun-Pyo/EarlySignal/pull/18), base `codex/llm-evidence-validation`. [실제 CI run 37880327725](https://github.com/SangJun-Pyo/EarlySignal/actions/runs/37880327725): Python 3.10·3.13 전체 테스트, 웹 테스트·타입 검사·정적 빌드 성공. Cloudflare Pages check 성공. 이번 세션은 실제 API·브라우저 원문 의미 검수를 수행하지 않았다.
- 종단 export 테스트의 주입 응답 생성 한 줄을 `selected_ids` 형식으로 맞췄다. 분류 로직·라벨 캐시는 변경하지 않았다.
- 기존 개인정보 정규식은 이메일 뒤 한국어가 바로 붙는 합성 경계 사례를 놓쳤다. 이번 범위의 privacy 함수는 변경하지 않고 별도 문제로 총괄에게 전달했다. 공백·문자열 끝의 이메일과 알려진 식별값 차단 회귀는 유지했다.

사용자 선택: '신고별 AI 요약을 그대로 인용하고 번호 연결 (추천)'. 기존 구조화 첫 실제 1응답은 형식 통과했으나 제공 요약 대조에서 복합 주장 과장이 확인됐으며 $0.0004956 사용, 공개하지 않고 남은 17개 경보 생성을 보류했다. 이 세션은 합성 테스트만 사용한다.

## 문제와 해결
| 문제 | 원인 | 해결 | 누가 |
|---|---|---|---|
| 인용 형식 통과 뒤 서로 다른 신고의 상황을 합침 | 모델 자유 서술의 복합 주장 | 모델은 ID만 선택, 코드는 기존 신고별 요약 그대로 인용 | Codex |

## 사람이 검토하며 고친 것
- 사용자가 신고별 기존 AI 요약 인용을 명시 선택했다. 원문 정답 검수·분류 정확도 측정은 수행하지 않았다.

## 다음 세션으로 넘길 것
- 총괄의 독립 검수·실제 동일 경보 범위 실행과 공개 확인. 기존 AI 라벨 요약의 의미 정확도는 별도 원문 대조가 필요하다.
