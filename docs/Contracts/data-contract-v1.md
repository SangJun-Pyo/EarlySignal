# 데이터 계약 `earlysignal-data-v1`

파이프라인(`export.py`)과 웹(`web/`) 사이의 JSON 형식. 이 문서가 기준이고, Codex는 이 문서로 `pipeline/es/contracts/*.schema.json`(JSON Schema)과 `web/lib/types.ts`(TypeScript 타입)를 만든다. 계약 테스트(`tests/test_contract.py`)는 export 결과 전부를 스키마로 검증하고, **금지 필드**가 어디에도 없는지 검사한다.

변경 규칙: 필드를 바꾸면 이 문서 → 스키마 → 타입 → 테스트 순서로 같이 바꾸고, 호환이 깨지면 `-v2`로 올리고 ADR을 추가한다.

## 공통
- 날짜: `"YYYY-MM-DD"`, 월은 그 달 1일(`"2018-10-01"`)
- 카테고리: ADR-004 enum 16개(`fire_thermal` …)
- `grp`: `"MAKE|MODEL"` 대문자
- **금지 필드(어떤 깊이에도)**: `vin`, `city`, `state`, `dealer_name`, `dealer_tel`, `dealer_city`, `dealer_state`, `dealer_zip`, `vehicle_operator`
- 모든 파일 최상위에 `"contract": "earlysignal-data-v1"`

## `meta.json`
```json
{
  "contract": "earlysignal-data-v1",
  "generated_at": "ISO8601",
  "data_source": {"name": "NHTSA ODI complaints & investigations", "downloaded_at": "YYYY-MM-DD", "license": "public domain"},
  "params": {"rule": "poisson", "alpha": 0.001, "min_count": 3, "baseline_months": 12, "min_history": 6, "lambda_floor": 0.5, "pre_window_months": 12},
  "validation": {
    "dev":     {"case": {"hits": 8, "n": 19}, "control": {"hits": 0, "n": 19}},
    "holdout": {"case": {"hits": 7, "n": 19}, "control": {"hits": 1, "n": 17}}
  },
  "burden": {"case_alerts_per_group_month": 0.24, "control_alerts_per_group_month": 0.08},
  "labels": {"llm_model": "string", "llm_labeled": 7502, "sample_agreement": {"agree": 0, "n": 60},
             "human_check": {"n": 30, "kw_correct": 0, "llm_correct": 0}, "cost_per_1k_usd": 0.0}
}
```

## `console.json` (조사 준비 흐름: 신고 원문 → 신호와 근거 → 조사 요청서)
한 파일에 기준 월 8개(2018-03~2018-10)를 담는다. 화면은 기준 월을 바꿔 가며 `snapshots[기준 월]`과 `series`를 그 달까지만 잘라 쓴다. 요청서는 `complaints`·`evidence`·`briefs`만으로 만들 수 있어야 한다.
```json
{
  "contract": "earlysignal-data-v1",
  "asof_months": ["2018-03-01", "2018-04-01", "2018-05-01", "2018-06-01", "2018-07-01", "2018-08-01", "2018-09-01", "2018-10-01"],
  "default_asof": "2018-08-01",
  "demo_signal": {"grp": "HYUNDAI|SONATA", "category": "fire_thermal", "month": "2018-08-01"},
  "groups": ["HYUNDAI|SONATA", "HYUNDAI|SONATA HYBRID", "HYUNDAI|SANTA FE", "HYUNDAI|SANTA FE SPORT",
             "KIA|OPTIMA", "KIA|OPTIMA HYBRID", "KIA|SORENTO", "KIA|SOUL", "KIA|SOUL EV"],
  "categories": ["fire_thermal", "engine_failure", "engine_stall", "loss_of_power", "electrical_failure", "lighting", "airbag", "steering"],
  "series": {
    "KIA|OPTIMA": {"months": ["2017-03-01", "…", "2018-10-01"], "total": [0],
                   "categories": {"fire_thermal": {"n": [0], "baseline": [null], "alert": [false]}}}
  },
  "snapshots": {
    "2018-10-01": {
      "kpi": {"complaints": 0, "complaints_prev": 0, "alerts": 0, "alerts_prev": 0, "fire_alert_models": 0},
      "alerts": [{"grp": "KIA|OPTIMA", "category": "fire_thermal", "n": 19, "baseline": 2.58, "ratio": 7.36,
                  "p_value": 4.8e-11, "streak": 1, "is_new": true, "comove": ["KIA|SORENTO"]}],
      "forecast": "P2 — {\"grp:cat\": [{month, expected, low, high, trend_expected, trend_low, trend_high}]}"
    }
  },
  "complaints": {
    "11115234": {"grp": "HYUNDAI|SONATA", "month": "2018-08-01", "ldate": "2018-08-01", "year": "2013",
                 "flags": ["fire", "smoke", "driving", "severe"], "categories": ["fire_thermal", "loss_of_power"],
                 "severity": 3, "injured": 0, "summary_ko": "string", "text": "원문 앞부분 최대 520자"}
  },
  "pile": {"2018-08-01": ["11115234", "…"]},
  "evidence": {
    "HYUNDAI|SONATA:fire_thermal:2018-08-01": {
      "n": 16,
      "agg": {"fire": 0, "smoke": 0, "driving": 0, "parked": 0, "crash": 0, "injury": 0, "severe": 0},
      "co": [["engine_stall", 8]],
      "years": [["2013", 6]],
      "ids": ["11115234", "…"]
    }
  },
  "briefs": {"KIA|OPTIMA:fire_thermal:2018-10-01": "string(#신고번호 인용)"},
  "reveal": {
    "cases": [{"case_id": "PE19004", "make": "KIA", "title": "Non-crash Vehicle Fires", "odate": "2019-03-29",
               "first_alert_month": "2018-07-01", "first_alert_grp": "KIA|SORENTO", "first_alert_category": "fire_thermal",
               "available": "2018-08-01", "lead_days": 240}],
    "series_after": {"KIA|OPTIMA": {"months": ["2018-11-01", "…", "2019-06-01"], "categories": {"fire_thermal": {"n": [0], "alert": [false]}}}}
  },
  "sources": [
    {"name": "NHTSA 소비자 신고", "status": "connected", "count": 932837},
    {"name": "AS·보증 수리", "status": "not_connected"},
    {"name": "MES 생산 이력", "status": "not_connected"},
    {"name": "부품 LOT·공급사", "status": "not_connected"}
  ],
  "assumptions": ["추세 연장 띠는 최근 3개월 수준이 이어진다는 단순 가정"]
}
```
- `series`는 `asof_months` 마지막 달까지만. 그 뒤 실제 값은 `reveal.series_after`에만 둔다(계약 테스트로 검사). 화면은 `web/lib/asof.ts` 순수 함수로 선택한 기준 월까지만 잘라 그린다.
- `snapshots[m]`의 모든 값은 m까지의 신고로만 계산한다.
- (P2) `forecast`는 기준 월 다음 1~3개월. 평소 범위: `expected`=기준 월 시점 λ(직전 12개월 평균), `low/high`=Poisson 5%/95% 분위. 추세 연장(가정): `trend_expected`=기준 월 포함 최근 3개월 평균, `trend_low/high`=그 값의 Poisson 5%/95% 분위. 검증된 예측이 아니므로 `assumptions`에 명시.
- `complaints`는 기준 월 범위(9개 차종) 신고 전부. `flags` ∈ {fire, smoke, driving, parked, crash, injury, severe}(LLM hazards + NHTSA FIRE/CRASH/INJURED 필드 + severity≥3). 원문은 520자까지, 금지 필드 없음.
- `evidence`는 기준 월 범위에서 신고 3건 이상인 (grp, category, 월) 칸만. `agg`는 `flags` 집계, `ids`는 그 칸 신고 전부(화재 > 부상 > 충돌 > 심각도 순). 집계를 누르면 `ids` 중 그 플래그가 있는 신고만 보여준다.
- `briefs`의 모든 `#번호`는 같은 키의 `evidence.ids`에 있어야 한다(`tests/test_request.py`).
- `alerts`는 배수(ratio) 내림차순. 우선순위 점수(SPEC §5)는 쓰지 않아도 된다(쓰면 '가정' 표시).

## 조사 요청서 (브라우저에서 생성 · 저장)
- 화면과 `.md` 파일은 `web/lib/request.ts`의 같은 순수 함수로 만든다. 구조는 `docs/LLM_PROMPTS.md` §3.
- 파일명 `{doc_no}.md`, `doc_no` = `ES-{작성가능일 YYYYMMDD}-{MODEL}-{CATEGORY 앞 단어}` (예: `ES-20180901-SONATA-FIRE`).
- 결정 기록(localStorage 키 `earlysignal.decisions.v1`, 읽기·쓰기 try/catch, JSON 다운로드 가능):
```json
{"contract": "earlysignal-data-v1", "decisions": [
  {"doc_no": "ES-20180901-SONATA-FIRE", "made": "2018-09-01", "grp": "HYUNDAI|SONATA", "category": "fire_thermal",
   "decision": "조사 착수|보류|기각", "actions": ["원문 정밀 검토"], "memo": "string",
   "cited": ["11115234"], "excluded": ["11118964"], "brief_cited": ["11115600"]}
]}
```
- 규칙: `cited`와 `excluded`는 겹치지 않는다. `cited`·`brief_cited`는 모두 해당 칸 `evidence.ids` 안에 있다.

## `cases.json`
```json
{"contract": "earlysignal-data-v1",
 "cases": [{"case_id": "PE19003", "split": "dev", "investigation": "PE19003", "note": "Non-crash Vehicle Fires",
            "groups": ["HYUNDAI|SONATA"], "target_categories": ["fire_thermal", "electrical_failure"],
            "odate": "2019-03-29", "result": "early|late|missed", "lead_days": 209,
            "first_alert_month": "2018-08-01", "first_alert_group": "HYUNDAI|SONATA", "first_alert_category": "fire_thermal",
            "has_llm": true}],
 "controls": [{"group": "HYUNDAI|GENESIS", "ref_date": "2019-03-29", "matched_to": "PE19003"}]}
```

## `cases/{case_id}.json`, `cases_llm/{case_id}.json` (사례 재생, 사후 확인용 — 전체 기간 포함 가능)
```json
{"contract": "earlysignal-data-v1", "case_id": "PE19003", "labeler": "keyword|llm", "odate": "2019-03-29",
 "target_categories": ["fire_thermal"],
 "groups": {"HYUNDAI|SONATA": {"months": [], "total": [], "categories": {"fire_thermal": {"n": [], "baseline": [], "alert": []}}}},
 "alerts": [{"id": "string", "grp": "string", "category": "string", "month": "YYYY-MM-01", "observed": 0, "baseline": 0.0,
             "p_value": 0.0, "is_target": true, "available": "YYYY-MM-01", "brief": "string|null",
             "evidence": [{"odino": "", "ldate": "", "fire": false, "crash": false, "injured": 0, "summary_ko": null, "snippet": ""}]}]}
```
