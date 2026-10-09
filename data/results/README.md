# 실행 결과를 읽는 순서

결과 JSON은 해당 실행·검수 시점의 기록이다. 초기 실패·대기 상태를 최신 상태로 덮어쓰지 않는다. 현재 제품은 전체 7,502건 LLM 분류와 대표 신고 요약 인용을 사용하는 정적 공개 사이트다.

| 확인할 내용 | 현재 근거 | 함께 읽을 한계 |
|---|---|---|
| 전체 분류·출처 검사 | `llm_full_completed.json`, `llm_batch.json` | 출력 검사 완료이며 사람 정답 정확도는 미측정 |
| 같은 모집단의 키워드/LLM 비교 | `llm_demo_comparison.json` | 3,793/7,502 일치는 정확도가 아님. 제한된 LLM 관측창 |
| 대표 요약·최종 누적 비용 | `brief_completed.json` | 16/18 공개, 실패 2개 유지. 반환 사용량 추정이며 청구액 아님 |
| 현재 문구·저장 동작 확인 | `deployment_copy_verification.json` | 웹 커밋1db76f7, 새 제목·45JSON 일치·실제 저장·다운로드·재접속5기록 |
| 전체 LLM 공개 제품 최초 검증 | `deployment_llm_verification.json` | 기록된8b50a75 커밋·시각의 검수. 후속 문구 배포 확인은 위 기록 |
| 38사례 주 평가 | `../backtest_kw.json`, `lookahead_kw.json` | 키워드 기준선. 실제 예방 효과·기관 최초 인지 비교가 아님 |
| 원본 출처 | `source_manifest.json` | 관측일과 실제 다운로드일을 구분 |

`llm_pilot*.json`은 고정 50건 시험·당시 추정 기록이다. 이후 전체 실행 승인은 ADR-021, 실제 전체 실행 결과는 위 파일을 따른다. `llm_full_completed.json`의 brief pending은 라벨 검수 당시 범위이며 요약의 최신 상태는 `brief_completed.json`이다. `brief_semantic_review.json`의 rejected 상태는 실제 폐기한 과장 요약을 기록한 것이므로 유지한다. `deployment_verification.json`은 초기 키워드 배포, `deployment_llm_preview.json`은 LLM 미리보기 검수다.

현재 공개 데이터 파일과 해시 목록은 [completion.json](../../web/public/data/completion.json), 전체 문서·화면 최신화 결과는 [S37](../../docs/Sessions/S37-current-copy-audit.md)에 연결한다.
