# 데이터 계약 `earlysignal-data-v1`

파이프라인(`pipeline/es/export.py`)과 정적 웹(`web/`) 사이의 현재 JSON 계약이다. 2026-10-09 공개 산출물·스키마·웹 타입과 대조했다. 오래된 예시를 바로잡은 문서 정리이며 필드·스키마·타입·탐지 규칙은 변경하지 않는다. [수정 전 문서](../history/data-contract-v1-before-current-state-2026-10-09.md)는 역사 기록으로 보존한다.

계약 변경 시 이 문서 → [JSON Schema](../../pipeline/es/contracts/) → [TypeScript 타입](../../web/lib/types.ts) → 테스트를 함께 수정한다. 호환이 깨지면 `-v2`로 올리고 ADR을 추가한다. 아래는 필드 요약이며 전체 필드·필수 여부·허용값은 스키마로 확인한다. 실행 가능한 현재 예시는 [공개 JSON](../../web/public/data/)이다.

## 공통 규칙

- 모든 공개 JSON의 `contract`는 `earlysignal-data-v1`이다. 날짜는 `YYYY-MM-DD`, 월은 그달 1일이다.
- `grp`는 대문자 `MAKE|MODEL`, 증상은 ADR-004의 16개 enum이다. 콘솔은 그중 9개를 표시한다.
- 어떤 깊이에서도 `vin`, `city`, `state`, `dealer_name`, `dealer_tel`, `dealer_city`, `dealer_state`, `dealer_zip`, `vehicle_operator`를 공개하지 않는다. 원문 발췌·요약도 알려진 식별값과 패턴을 검사한다. 완전한 익명화 보장은 아니다.
- `null`은 미측정 또는 값 없음이다. 정확도 0%나 비용 0원으로 해석하지 않는다.
- LLM은 현재 입력·모델·프롬프트·스키마에 연결된 전체 캐시가 완성되어야 공개한다. 부분 캐시를 전체 결과로 표시하지 않는다(ADR-013).
- 공개 파일은 미리 계산한 과거 자료다. `sources[].status="connected"`는 이 자료에 포함됐다는 뜻이며 실시간 API 연결이 아니다.

## 파일과 평가 범위

| 파일 | 내용·출처 |
|---|---|
| `meta.json` | 고정 탐지 규칙, **키워드** 38사례·36대조 주 결과와 검토량, LLM 분류 상태, 한계 |
| `console.json` | **LLM** 라벨을 사용하는 현대·기아 9개 차종의 조사 준비 화면 |
| `cases.json`, `cases/*.json` | 키워드 기준선의 등록 사례 결과·사후 시계열 |
| `cases_llm/*.json` | 대표 3사례의 제한된 LLM 관측창 결과. 전체 등록 창의 38사례 LLM 평가가 아님 |
| `completion.json` | 공개 파일 목록·해시·콘솔 건수·완성 상태. 자기 자신을 제외한 파일 해시 보관 |

현재 공개 JSON 45개, 콘솔 신고 2,142건·근거 칸 421개·대표 요약 16개다. 전체 분류 모집단 7,502건과 화면의 2018-03~10 신고 수는 다르다. 18개 대상 경보 중 요약 2개는 검사 실패로 공개하지 않았다. 근거는 [completion.json](../../web/public/data/completion.json), [brief_completed.json](../../data/results/brief_completed.json)이다.

## `meta.json`

[스키마](../../pipeline/es/contracts/meta.schema.json) · [현재 파일](../../web/public/data/meta.json)

| 필드 | 의미 |
|---|---|
| `generated_at` | 실제 내보내기 시각 ISO8601, 과거 분석 기준일과 구분 |
| `data_source.downloaded_at` | 제공 ZIP의 실제 다운로드일을 알 수 없으면 `null` |
| `data_source.observed_local_date` | 로컬에서 원본 파일을 확인한 날짜 |
| `params` | 직전 12개월 평균·최소 6개월·하한 0.5, 포아송 상측 p<0.001·월 3건 이상. 평가창 기준은 `alert_month` |
| `validation` | dev/holdout 각각 case/control의 hits·n. 키워드 경보 비율이며 일반 정확도·오탐률이 아님 |
| `burden` | 등록 평가창의 차종-월당 증상 경보 관측량. 실제 조직 업무량은 미검증 |
| `labels.llm_model`, `llm_labeled` | 실제 모델과 출력 검사 완료 신고 수 |
| `labels.sample_agreement` | 기존 개발 비교 표본 60건의 주 라벨 일치. 전체 7,502건 비교는 별도 결과 파일 |
| `labels.human_check` | 현재 사람 정답 n=0, kw_correct·llm_correct는 `null` |
| `labels.cost_per_1k_usd` | 입력·사용량이 연결된 완료 배치 단가. 현재 미측정(`null`) |
| `validation_notes` | 회고 재현·시제품과의 차이·평가 한계의 표시용 설명 |

현재 dev 사례 9/19·대조 0/19, holdout 사례 7/19·대조 1/17이다. `sample_agreement` 27/60과 전체 모집단 3,793/7,502를 혼동하지 않는다. 전체 비교는 [llm_demo_comparison.json](../../data/results/llm_demo_comparison.json)이 출처다. 두 방식의 일치는 사람 정답 정확도가 아니다.

## `console.json`

[스키마](../../pipeline/es/contracts/console.schema.json) · [현재 파일](../../web/public/data/console.json)

| 필드 | 현재 구조·의미 |
|---|---|
| `labeler`, `labeling_note`, `flag_sources` | keyword 또는 llm 출처, 설명, 상황 플래그별 출처 |
| `asof_months`, `default_asof`, `demo_signal` | 선택 월 2018-03~10, 기본 2018-08, SONATA 화재·과열 2018-08 |
| `groups`, `categories` | 현대·기아 9개 차종, 표시 증상 9개 |
| `series` | 차종별 months·total, 증상별 n/baseline/alert 배열. 2018-10 이후 실제 값 없음 |
| `snapshots[month]` | 해당 월 kpi·alerts. 선택 월까지의 신고로 계산 |
| `complaints[id]` | 차종·접수월·접수일·연식·플래그·증상·심각도·부상 수·AI 요약·정제 원문 발췌·라벨 출처 |
| `pile[month]` | 해당 월 접수 신고 ID 목록 |
| `evidence[cell]` | 3건 이상 칸의 n·상황 집계 agg·동반 증상 co·연식 years·실제 근거 ids. 키는 grp:category:month |
| `briefs[cell]` | 같은 칸의 대표 신고 요약 인용 문자열. 생성·검사 실패 칸은 없음 |
| `reveal.cases`, `reveal.series_after` | 지정 PE와의 사후 비교·이후 실제 시계열. 운영 화면의 미래 값으로 사용하지 않음 |
| `sources`, `assumptions` | 포함·미연결 자료와 해석상 가정 |

웹은 `web/lib/asof.ts`에서 선택 월까지 시계열을 잘라 표시한다. 접수일 `ldate`를 쓰며 사고일로 바꾸지 않는다. 현재 `forecast` 필드는 없고 전망 띠·우선순위 점수·사례 재생 화면은 후속 범위다. 추가하려면 별도 계약 변경과 미래 정보 차단 검사가 필요하다.

경보는 해당 월의 표시 증상 중 조건을 통과한 칸이며 배수 내림차순이다. n·baseline·ratio·p_value·streak·is_new·comove를 제공한다. 현재 SONATA 2018-08 LLM 화재·과열은 17건, 기준선 4.916666666666667, 배수 3.4576271186440675, p=0.000016130219673942316이다. 키워드 기준선 6.8333과 섞지 않는다.

신고 `text`는 정제 원문 최대 520자 발췌다. `label_source`는 각 신고의 출처다. flags는 fire/smoke/driving/parked/crash/injury/severe다. LLM fire/crash/injury는 NHTSA 기록 OR LLM hazard이고 severe는 LLM severity≥3이다. 키워드 심각도는 `null`이다. 근거 ID는 화재 > 부상 > 충돌 > 심각도 순이다.

### 대표 신고 요약(ADR-024)

첫 문장은 실제 경보 수치로 코드가 만든다. 모델은 제공된 최대 10개 근거 ID 중 중복 없이 1~3개만 선택한다. 프로그램이 기존 `summary_ko`를 `(#번호) 기존 요약`의 독립 줄로 그대로 복사한다. 새 상황을 종합하거나 기존 요약을 수정하지 않는다.

번호는 같은 칸 evidence.ids와 모델에 제공한 번호 안에 있어야 한다. 기존 수량·개인정보·단정·캐시 모드·입력 해시 검사를 유지하고 실패 결과는 공개하지 않는다. 검사 통과가 원문의 의미 정확성이나 대표성 검증은 아니다. 표시명은 **대표 신고 요약 (AI 요약 인용·담당자 검토)**다.

## 조사 요청서와 결정 기록

화면과 Markdown은 `web/lib/request.ts`의 같은 순수 함수로 만든다. 7개 항목은 `docs/LLM_PROMPTS.md` §3 구조이며 LLM이 문서 전체를 작성하지 않는다.

- 문서번호·파일명은 `ES-{작성가능일 YYYYMMDD}-{MAKE}-{MODEL}-{CATEGORY 전체}.md`다. 범주 첫 단어만 쓰지 않는다.
- decision.made는 **실제 저장 시각 ISO8601**, analysis_available은 분석 접수월 다음 달 1일이다. 과거에 실제 저장한 문서로 표시하지 않는다.
- localStorage 키는 `earlysignal.decisions.v1`이며 해당 브라우저에만 저장한다. JSON 다운로드 최상위는 contract·decisions다.
- 각 기록은 doc_no/made/analysis_available/grp/category/decision/actions/memo/cited/excluded/brief_cited를 보관한다. 판단은 조사 착수·보류·기각이다.
- cited·brief_cited는 해당 근거 칸 안에 있어야 하고 excluded와 겹칠 수 없다. 제외한 번호가 대표 요약에 있으면 요약 전체를 요청서에서 보류하고 표시한다.
- 제외는 담당자의 검토 표시다. 원래 통계 모집단을 다시 계산한 것처럼 표현하지 않는다.
- 저장 후 209·240일 비교는 지정 예비조사(PE) 개시일 대비다. 앞선 청원·조사를 설명하며 최초 발견·사고 예방 효과로 주장하지 않는다(ADR-025).

## 사례와 완료 manifest

[cases 스키마](../../pipeline/es/contracts/cases.schema.json) · [case 스키마](../../pipeline/es/contracts/case.schema.json) · [completion 스키마](../../pipeline/es/contracts/completion.schema.json)

`cases.json`의 사례에는 case_id/split/investigation/note/groups/target_categories/odate/result/lead_days/first_alert_month/first_alert_group/first_alert_category/has_llm이 있다. result는 early/late/missed다. 첫 경보가 없으면 관련 값은 null이며 대조군은 group/ref_date/matched_to로 연결한다.

개별 사례 파일에는 labeler·odate·target_categories·차종별 시계열 groups·경보와 원문 근거 alerts가 있다. 사후 확인용이므로 이후 실제 값도 포함할 수 있다. LLM 파일의 coverage는 실제 시작·종료일과 registered_window_complete=false를 명시한다. 등록 전체 창의 키워드 결과와 직접 성능 우열을 주장하지 않는다.

`completion.json`의 status=complete는 파일 내보내기 완료다. files·file_sha256와 console_months/console_groups/complaints/evidence_cells/briefs/cases를 대조한다. 사람 정답 검수 완료를 뜻하지 않는다.

## 실제 검사

`pipeline/tests/test_contract.py`는 공개 파일을 스키마·금지 필드·미래 시계열 규칙과 대조한다. 인용은 `pipeline/tests/test_request.py`, `web/tests/request.test.ts`에서 검사한다. 완료 manifest와 LLM 출처 검사는 export·brief 검사에 포함한다. 실행 결과는 [현재 상태](../Development/STATUS.md)와 [검수 기록](../Reviews/)에 남긴다.
