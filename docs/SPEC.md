# EarlySignal — 구현 명세 v2

> 사전 작성 문서(10/8). 10/8 시제품으로 설계와 수치를 미리 검증했다(결과는 `RESEARCH.md`). 코드는 당일 Codex로 새로 작성한다.
> 작업 절차는 `docs/Development/WORKFLOW.md`(하네스), 설계 결정은 `docs/ADR/`, 데이터 형식은 `docs/Contracts/data-contract-v1.md`를 따른다.

## 0. 무엇을 만드나

**고객의 작은 불만이 큰 사고가 되기 전에.** 자유서술형 소비자 결함 신고를 LLM이 증상 라벨로 바꾸고, 차종×증상별 월간 신고를 통계로 감시해 조사해야 할 이상 신호를 더 일찍 찾는다.

**데모 목표: 경보 보여주기가 아니라 조사 준비 끝내기**(ADR-009). 한 가지 업무를 끝까지 보여준다: *담당자가 반복되는 화재 신고를 발견하고, 원문을 검토한 뒤, 근거가 연결된 조사 요청서를 만들어 저장한다.* 주인공은 대시보드가 아니라 **조사 요청서**이고, 대시보드는 그것을 만드는 작업 공간이다. 원인 분석을 끝냈다고 주장하지 않는다. 조사를 시작하는 데 필요한 자료를 준비했다는 것이 가치다.

웹 화면(상단 단계 내비게이션: 신고 원문 / 신호와 근거 / 조사 요청서 + 검증 결과):
1. **신고 원문**: 선택 월 접수 신고 원문 목록(9개 차종) + 같은 현상의 다양한 표현 수. "사람이 정리해야 할 일"을 보여준다.
2. **신호와 근거**: 분석 시점(월) 선택 → 차종×증상 히트맵과 경보 목록 → 경보 선택 → AI 집계(누르면 해당 원문만) + 대표 신고 요약(기존 AI 요약을 #신고번호와 함께 인용) + 원문 검토(인용/제외) + 월별 추이 탭 → "조사 요청서 초안 생성".
3. **조사 요청서**: 7개 항목 문서 + 담당자 판단·다음 조치·메모 → 확정·저장 → `.md` 다운로드 + 결정 기록 + "이 요청서 작성 가능일 vs NHTSA 조사 개시일".
4. **검증 결과**(보조): 38건 dev/holdout × 사례/대조, 리드 일수, 놓친 사례.

**데모 고정 사례**: HYUNDAI SONATA · 화재·과열 · 2018년 8월 접수분(16건, 평소 6.0건, 2.7배 — 시제품 값). 작성 가능일 2018-09-01 → NHTSA PE19003 개시 2019-03-29 → **209일 먼저**.

## 1. 우선순위

| 등급 | 내용 | 목표 시각 |
|---|---|---|
| P0 | Step 1~6: 적재 → 범위 → 키워드 라벨 → 집계·탐지 → 백테스트 → 미래 정보 차단 테스트 | 11:30 |
| P0 | Step 7: OpenAI 라벨링 (데모 범위 7,502건, hazards·summary_ko 포함, 백그라운드로 먼저 시작) | 시작 10:30, 완료 12:30 |
| P1 | Step 8: console.json(요청서형) export + Step 10: 대표 신고 선택·기존 AI 요약 인용 검사 | 13:30 |
| P1 | Step 9: 웹 — 신고 원문 → 신호와 근거 → 조사 요청서(확정·저장·다운로드·결정 기록) + 검증 결과 요약 + 정적 배포 | 15:30 |
| P2 | 사례 재생 화면(38건), 전망 띠(평소 범위·추세 연장)와 test_forecast, 시간 재생 애니메이션, KPI 카드, 우선순위 점수, 키워드 vs LLM 비교 화면, 최신 데이터 모드 | 남는 시간 |
| — | 발표 PDF, 녹화 데모, README, 제출 | 16:40 제출 완료 |

**범위 고정**: 15:30까지 "경보 하나를 골라, 근거를 확인하고, 조사 요청서를 저장하는 흐름 하나"가 끝까지 동작하는 것이 최우선이다. P2는 이 흐름이 배포된 뒤에만 손댄다.

## 2. 저장소 구조

```
earlysignal/
├─ AGENTS.md  README.md  .gitignore  .env.example
├─ docs/
│  ├─ SPEC.md  RESEARCH.md  LLM_PROMPTS.md  PRESENTATION.md  CODEX_LOG.md(세션 색인)
│  ├─ DESIGN_REF.md  design-ref/*.png   # 화면 참고(글·캡처, 코드 없음)
│  ├─ Development/WORKFLOW.md   # 하네스 작업 절차
│  ├─ ADR/                     # 설계 결정 (001~009 사전, 010~ 당일)
│  ├─ Contracts/data-contract-v1.md
│  ├─ Sessions/                # S00~S12 세션 로그
│  └─ Knowledge/LessonsLearned.md
├─ data/
│  ├─ cases_pool.yaml          # 사전 조사로 정한 백테스트 사례 38건 + 대조군 36개 (커밋)
│  ├─ raw/                     # NHTSA zip (커밋 안 함)
│  └─ labels/                  # labels_llm.jsonl, briefs.json (커밋: 재현용 캐시)
├─ pipeline/
│  ├─ requirements.txt
│  ├─ es/ config.py ingest.py scope.py label_kw.py label_llm.py aggregate.py detect.py
│  │      backtest.py forecast.py brief.py export.py cli.py
│  │      contracts/*.schema.json   # data-contract-v1에서 생성
│  └─ tests/ test_ingest.py test_detect.py test_lookahead.py test_contract.py test_request.py
└─ web/   (Next.js 정적 사이트; public/data/*.json 은 export 결과, 커밋)
   ├─ lib/ types.ts asof.ts request.ts   # request.ts = 요청서 생성 순수 함수(화면·.md 공용)
   └─ tests/request.test.ts
```

## 3. 데이터 (모두 미국 NHTSA ODI 공개 데이터, 퍼블릭 도메인)

| 파일 | URL |
|---|---|
| COMPLAINTS_RECEIVED_2010-2014.zip / 2015-2019 / 2020-2024 | https://static.nhtsa.gov/odi/ffdd/cmpl/ |
| FLAT_INV.zip (조사) | https://static.nhtsa.gov/odi/ffdd/inv/ |
| 필드 정의 CMPL.txt / INV.txt | 같은 폴더 |

**형식(10/8 확인)**: UTF-8, 탭 구분, 헤더 없음. 신고 51컬럼, 조사 11컬럼. 신고문에 `"`가 있으므로 따옴표 해석을 끈다(DuckDB `quote=''`). 일부 깨진 행은 무시(`ignore_errors`). FLAT_INV는 풀면 약 390MB.

**신고 컬럼(1부터)**: 1 CMPLID, 2 ODINO, 3 MFR_NAME, 4 MAKETXT, 5 MODELTXT, 6 YEARTXT, 7 CRASH, 8 FAILDATE, 9 FIRE, 10 INJURED, 11 DEATHS, 12 COMPDESC, 13 CITY, 14 STATE, 15 VIN, 16 DATEA, 17 LDATE, 18 MILES, 19 OCCURENCES, 20 CDESCR, 21 CMPL_TYPE, … 46 PROD_TYPE, … 51 VEHICLE_OPERATOR (전체는 CMPL.txt)

**조사 컬럼**: 1 ACTION_NO(앞 2글자 PE/EA/DP/RQ…), 2 MAKE, 3 MODEL, 4 YEAR, 5 COMPNAME, 6 MFR_NAME, 7 ODATE, 8 CDATE, 9 CAMPNO, 10 SUBJECT, 11 SUMMARY

## 4. 파이프라인 단계

### Step 1. 적재 `ingest.py`
- zip을 풀어 DuckDB(`data/earlysignal.duckdb`)에 `complaints_raw`, `complaints`, `investigations` 생성.
- `complaints`: AGENTS 규칙 2 적용 후 ODINO당 1행. 컬럼: odino, make, model, year(대문자·trim), grp=`MAKE|MODEL`, ldate, datea, month(=ldate 월초), crash, fire, injured, deaths, text(CDESCR), cmpl_type, compdesc_list(평가용).
- **완료 기준(10/8 기준값, 같은 파일이면 일치해야 함)**: 원본 1,301,663행 → 소비자 신고 고유 932,837건, LDATE 파싱 실패 0%, 조사 154,401행 / 고유 조사 5,349건. 샘플 5건 출력.

### Step 2. 범위 `scope.py`
- 감시 단위 = **브랜드+모델(연식 통합)** `grp`.
- (a) 검증 범위: `data/cases_pool.yaml`의 사례·대조군 grp에 대해 [odate−48개월, odate+6개월) 신고 → 테이블 `scoped` (10/8: 123,138건).
- (b) 데모(LLM) 범위: 아래 조건 → 테이블 `demo` (10/8: **7,502건**)
  - 현대 `SANTA FE`, `SANTA FE SPORT`, `SONATA`, `SONATA HYBRID`, 기아 `OPTIMA`, `OPTIMA HYBRID`, `SORENTO`, `SOUL`, `SOUL EV`: ldate 2017-03-01 ~ 2019-06-30
  - `CHEVROLET|BOLT EV`: ldate 2018-10-01 ~ 2021-01-31
- 완료 기준: 범위별 건수 출력.

### Step 3. 키워드 라벨 `label_kw.py` (비교 기준선)
- 카테고리 enum(16개, LLM과 동일): `fire_thermal, electrical_failure, loss_of_power, engine_stall, engine_failure, airbag, brakes, steering, seat_belt, fuel_leak, transmission, lighting, suspension, structure_body, tires_wheels, other`
- 우선순위가 있는 정규식으로 primary 1개 + secondary 최대 2개. 패턴 예: fire_thermal `\bfires?\b|flames?|\bsmok(e|ing|ed)\b|burn(ing|t|ed)?\s+(smell|odor)|melt|overheat`, loss_of_power `los[st]\s+(all\s+)?(motive\s+)?power|loss\s+of\s+(motive\s+)?power|...` (복수형·“loss of” 형태를 빠뜨리지 말 것 — 10/8에 실제로 놓쳤음).
- `scoped`와 `demo` 모두 라벨 → `labels_kw`.

### Step 4. 집계 `aggregate.py`
- 키 grp × category × month(ldate 기준). 값 = 고유 ODINO 수. primary와 secondary 모두 반영. 신고 없는 달은 0으로 채움. grp별 월 전체 건수 total도 함께.
- `as_of` 인자를 받으면 `ldate <= as_of`만 사용(테스트용).

### Step 5. 탐지 `detect.py`
- 각 (grp, category) 월 t: 기준선 λ = 직전 12개월(t 제외) 평균, 이력 6개월 미만이면 판단 안 함, λ < 0.5이면 0.5.
- p = P(X ≥ n_t | Poisson(λ)). **경보 = p < 0.001 그리고 n_t ≥ 3.**
- 출력: grp, category, month, n, total, baseline, p_value, alert, streak(연속 경보 개월).
- 보조 규칙(비교용): 같은 grp 전체 신고 중 비율의 이항 검정. 10/8 dev에서 포아송이 더 나아 포아송 채택(RESEARCH §5).

### Step 6. 백테스트 `backtest.py` + 테스트
- 사례별: 사례 grp들 × target_categories에서 [odate−12개월, odate+6개월] 안의 첫 경보 월 m. 확인 가능일 = m 다음 달 1일. `lead_days = odate − 확인 가능일`. 결과 early(>0) / late / missed.
- **주 지표**: 조사 전 12개월 안(마지막 1개월 제외) target 경보 발생 여부를 사례 vs 대조군, dev vs holdout 2×2로.
- 검토 업무량: grp-월당 경보 수(모든 증상)를 사례/대조 따로.
- `tests/test_lookahead.py`: 여러 cut-off에서 `ldate <= cut-off`로 잘라 다시 탐지한 결과가, 전체 데이터 결과의 해당 기간과 **완전히 같아야** 한다.
- **완료 기준(10/8 기준값)**: dev 사례 8/19, 대조 0/19 / holdout 사례 7/19, 대조 1/17. PE19003 lead 209일, PE19004 240일, PE20016 late. 테스트 통과. 값이 다르면 원인을 찾아 CODEX_LOG에 기록.

### Step 7. LLM 라벨 `label_llm.py` (OpenAI)
- 대상: `demo` 7,502건(원문은 공백 정리 후 1,500자까지).
- OpenAI Chat Completions + **Structured Outputs(JSON Schema strict)**, temperature 0, 소형 모델(당일 쓸 수 있는 가성비 모델). 프롬프트·스키마는 `docs/LLM_PROMPTS.md` §1.
- 동시 요청 8~16, 지수 백오프 재시도, **결과를 `data/labels/labels_llm.jsonl`에 한 줄씩 즉시 저장**, 재실행 시 처리된 odino는 건너뜀.
- 먼저 50건 시험 → 건당 평균 시간·입출력 토큰을 출력하고 전체 비용을 추정한 뒤 본 실행. **본 실행은 백그라운드로 돌리고 다른 Step을 진행.**
- 초기 검증 계획: `data/labels/sample60_compare.csv` 만들기 — 무작위 60건(seed 고정)의 키워드 vs LLM primary 비교, 사람이 30건 검수해 정답 열 추가. 현재 이 비교 파일은 개발용이고 실제 사람 정답은 별도의 독립 검수 자료에서 관리하며 아래 변경에 따라 당일 정답 검수는 미완료다.
- 당일 변경(2026-10-09, ADR-020·S23): 개발 표본과 분리한 독립 30건 자료를 준비했으나, 사용자가 도메인 지식·공모전 시간 제약으로 검수를 완료하지 않기로 했다. 사람 정답 평가를 후속 전문가 검수로 이관하며 이번 제출의 분류 정확도는 미측정으로 보고한다.
- 완료 기준: 7,502건 라벨, 스키마 위반 0, 키워드 vs LLM 일치율 출력(10/8 Claude 라벨 기준 60%).

### Step 8. 내보내기 `export.py` → `web/public/data/`
- `meta.json`: 데이터 출처, 파라미터, 2×2 hit rate, 검토 업무량, 키워드 vs LLM 비교 요약
- `cases.json`: 38건 요약(split, 조사 번호, 제목, grp들, target, odate, result, lead_days, 첫 경보 월·grp·category) + 대조군 목록
- `cases/{case_id}.json` (키워드 라벨): grp별 months, total, categories{cat: n[], baseline[], alert[]}, alerts[{id, grp, category, month, observed, baseline, p_value, is_target, available, evidence[]}]
- `cases_llm/{PE19003|PE19004|PE20016}.json`: 같은 구조, LLM 라벨, evidence에 `summary_ko`, alert에 `brief`
- `console.json`: 대시보드 전체 데이터. 형식은 `docs/Contracts/data-contract-v1.md`. 기준 월 선택 범위 2018-03~2018-10(`asof_months`, 기본 2018-05), 감시 grp = 현대·기아 9개 차종(볼트 EV는 사례 재생에서), LLM 라벨 사용(없으면 키워드). heatmap(차종×주요 9개 증상: 기준 월 건수, λ, 배수, 경보), signals(최근 3개월 경보, (grp,category)별 최신 1건, §5 점수와 high/medium/low), series(**기준 월까지만**), forecast(**P2**, `forecast.py`: 기준 월 다음 1~3개월. 평소 범위 = 기준 월 시점 λ의 Poisson 5~95% 분위, 추세 연장(가정) = 기준 월 포함 최근 3개월 평균의 Poisson 5~95% 분위. 둘 다 기준 월까지 데이터만 사용), complaints(선택 범위 신고 원문 사전: 번호 → 차종·월·접수일·연식·발생 상황 플래그·라벨·요약·원문 520자), pile(월별 신고 번호 목록), evidence(선택 범위의 (grp,category,월)별 신고 3건 이상인 칸: 집계 agg{fire,smoke,driving,parked,crash,injury,severe}, 함께 언급된 증상 상위 3, 연식 분포, 해당 신고 번호 전체를 화재>부상>충돌>심각도 순으로), briefs(경보 칸), reveal(사례별 odate·첫 경보 월·lead_days와 기준 월 이후 실제 series — 5단계 전용), sources(데이터 연결 현황), assumptions.
- 계약 테스트 `tests/test_contract.py`: 모든 export 파일을 스키마로 검증, 금지 필드 없음, console.series에 asof_months 마지막 달 이후 값 없음(이후 실제 값은 reveal에만).
- (P2) `tests/test_forecast.py`: 기준 월 이후 신고를 지우고 다시 계산해도 forecast가 똑같은지(미래 데이터 미사용), low ≤ expected ≤ high, 평소 띠와 추세 띠 값 예시 검산(KIA|OPTIMA 화재: 평소 기대값 약 2.6).
- evidence: 해당 grp·월·category 신고 중 화재>부상>충돌 순 최대 10건. 필드 odino, ldate, fire, crash, injured, summary_ko, snippet(키워드 위치 주변 300자). **VIN·도시·딜러·운전자 이름 제외.**

### Step 9. 웹 `web/` (정적 export)

**디자인 방향 (10/8 사용자 시안 기반)**: 어두운 남색 바탕의 업무용 대시보드. 왼쪽 세로 내비게이션(대시보드 / 사례 재생 / 검증 결과), 상단 제목 "품질 안전 현황" + 기준일 배지 + "과거 데이터 데모" 표시.
- 색(근사값): 바탕 #0b1626, 패널 #10233a, 선 #1e3a57, 글자 #e6eef7, 보조 글자 #8fa3b8, 강조(정보) #22d3ee, **경보 #f5a524**, 높음 #f05252, 조사 개시선 #60a5fa. 히트맵은 남색→청록 단계 + 경보 칸 주황 테두리.
- **발표장 프로젝터 대비**: 본문 글자는 #e6eef7 이상 밝기, 14px 이상, 숫자는 굵게. 빛 번짐·그라데이션 장식은 최소화.
- 폰트 IBM Plex Sans KR(숫자 tabular). 차트 Recharts. 숫자에는 단위와 기준(평소=직전 12개월 평균)을 붙인다.
- **차종 이름과 숫자는 시안 값이 아니라 `console.json` 실제 값**(SONATA, SANTA FE, OPTIMA, SORENTO, SOUL 등 NHTSA 표기).

**① 조사 준비 흐름 (메인, ADR-009 · ADR-007)**

참고 시안: `docs/DESIGN_REF.md`(화면별 명세)와 `docs/design-ref/*.png`(사용자가 캡처해 넣는 화면). **흐름과 배치만 참고하고 코드는 새로 작성**한다. 시안 숫자는 시제품 값이라 당일 파이프라인 값으로 바뀐다.

원칙
- 주인공은 조사 요청서. 모든 화면은 요청서를 채우기 위한 단계다.
- 요청서의 모든 숫자와 문장은 실제 신고에 연결된다. ADR-024에 따라 모델은 대표 신고 번호만 선택하고 새 종합 문장을 쓰지 않는다. "대표 신고 요약"에는 실제 통계문과 선택된 기존 `summary_ko`를 그대로 인용하며, #신고번호는 같은 칸의 근거 목록과 실제 제공된 번호 안에 있어야 한다(`tests/test_request.py`). 원문 의미 대조는 담당자의 몫이다.
- 안내 띠·곳곳의 면책 문구 금지. 면책은 화면 맨 아래 한 줄 + 요청서 꼬리말 한 줄.

화면 1. 신고 원문
- 제목 "2018년 8월 접수 신고 N건". 접수일·차종·연식·원문(2줄 말줄임, 원문 그대로) 목록 40건 + "…외 n건".
- 오른쪽: "같은 현상이 제각각의 말로 들어옵니다" — SMOKE / FIRE·FLAMES / BURN / MELTED / STALLED / LOSS OF POWER 표현이 들어간 신고 수(정규식으로 원문에서 직접 셈). 오타·맥락·다른 부위가 섞인다는 한 줄.
- 버튼 "AI가 정리한 신호 보기 →".

화면 2. 신호와 근거
- 분석 시점 바: 2018년 3~10월 월 버튼, "N월 접수분까지 · 다음 달 1일에 알 수 있었던 것만".
- 왼쪽: 차종×증상 히트맵(칸 숫자 = 건수, 색 = 평소 대비 배수 4단계, 경보 = 주황 채움, 선택 = 흰 테두리) + "이 시점의 경보 n건"(배수 큰 순, 신규/연속 배지).
- 오른쪽(경보 선택 시): 제목·배지, 한 줄 지표(이번 달, 평소, 배수, 연속 경보, 같은 시기 같은 증상 차종). 탭 2개.
  - **근거 검토**(기본): ① "AI가 신고 N건을 묶은 결과" 발생 상황 막대(전체, 화재 언급, 연기, 주행 중, 주차 중, 충돌, 부상, 심각도 높음) — **누르면 해당 원문만 아래에 남음**. 함께 언급된 증상·연식 분포. ② 대표 신고 요약(AI 요약 인용·담당자 검토, #번호별 독립 줄). ③ 원문 검토 목록: 신고 번호, 접수일, 연식, 플래그, 한국어 요약, 원문(3줄 말줄임, 누르면 펼침, 화재·연기·주행 상황 표현 강조), **[인용] [제외] 버튼**. 상단에 "인용 n · 제외 m · 미검토 k". ④ 큰 버튼 "조사 요청서 초안 생성 →"(인용이 없으면 화재 언급 상위 3건을 '자동 제안'으로 표시).
  - **월별 추이**: 최근 18개월 막대(경보 달 주황) + 평소 점선. 기준 월까지만.
- 데모 포인트: 쏘나타 8월 16건 중 후미등·브레이크등 소켓이 녹는 신고가 섞여 있다(AI 라벨은 화재·과열로 묶음). 담당자가 [제외]하는 장면이 "사람이 판단한다"를 보여준다.

화면 3. 조사 요청서 (주인공)
- 왼쪽: 종이 질감의 문서(밝은 바탕). 문서 번호(ES-작성가능일-차종-증상), 상태 도장(초안/확정).
  - 머리: 조사 대상(차종·제조사·증상), 분석 기준(N월 접수분까지 · 작성 가능일), 데이터(NHTSA 소비자 신고 · AI 라벨 · 통계 경보 규칙)
  - 1. 신고 증가와 경보 근거: 이번 달 n, 평소 λ, 배수, p, 연속 경보, 같은 시기 같은 증상 차종, 최근 6개월 건수
  - 2. 반복되는 발생 상황: AI 라벨 집계(건수 큰 순), 함께 언급된 증상, 신고 차량 연식
  - 3. 대표 신고 요약(AI 요약 인용·담당자 검토): 실제 경보 통계문 + 선택한 신고의 기존 AI 요약을 번호별로 그대로 인용 — brief. 미준비·인용 보류 상태도 표시한다.
  - 4. 인용 신고: 담당자가 인용한 신고 + 대표 요약에 포함된 신고(표시 "[대표 요약 인용]"), 제외한 신고 번호, "NHTSA ODI 번호로 원문 조회 가능". 외부 링크는 당일 확인된 경우에만.
  - 5. 아직 확인되지 않은 사항(고정): 원인과 결함 여부, 판매·운행 대수 대비 비율, 동일인·중복 신고, 정비·리콜 수리 이력, 미국 외 시장
  - 6. 내부 데이터로 확인할 항목(고정 + 연식 삽입): AS·보증 수리 이력, MES 생산 기간·공장·엔진 LOT, 부품 공급사·변경 이력
  - 7. 담당자 판단과 다음 조치
  - 꼬리말: "결함·원인 판정이 아니라 조사 착수 여부를 정하기 위한 자료"
- 오른쪽: 판단 버튼 3개(조사 착수/보류/기각), 다음 조치 칩(원문 정밀 검토, AS·보증 수리 이력 조회, 생산 LOT 대조, 부품 공급사 확인, 다음 달 재검토), 메모 입력, "확정하고 저장"(판단 선택 전 비활성).
- 저장 후: 도장 "확정 2018.09.01 · 품질안전팀", **`{문서번호}.md` 다운로드**(Blob, 서버 없음), 결정 기록 목록(localStorage, try/catch, JSON 다운로드 버튼), 그리고 카드 **"이 요청서 작성 가능일 2018.09.01 / NHTSA 공식 조사 개시 2019.03.29 (PE19003) → 209일 먼저"** + "38개 사례 검증과 놓친 사례 보기". 연결된 조사가 없는 신호는 "연결된 조사 없음"으로 정직하게.
- 요청서 생성은 `web/lib/request.ts` 순수 함수(입력: console.json, 선택 칸, 기준 월, 인용·제외 표시, 판단) 하나로 한다. 같은 함수로 화면과 .md를 만든다. 테스트: `web/tests/request.test.ts`(인용 번호가 근거 목록에 있음, 7개 항목 존재, 금지 필드 없음, 제외한 신고는 인용 목록에 없음).

검증 결과(보조 화면 또는 패널): dev/holdout × 사례/대조 숫자, 현대 209일·기아 240일, 놓친 사례(볼트 EV) 문장.

미래 데이터 규칙(ADR-002): 화면 1~3은 선택한 기준 월까지의 신고만 쓴다. 이후 실제 값은 검증 결과에서만.

**② 사례 재생 (P2, 사후 확인)** — 여기서는 기준일 이후 실제 값과 NHTSA 조사 개시선을 보여준다.
- 왼쪽 사례 목록(38건, 결과 점), 가운데: 큰 연월 표시(시점), 상태 문장, 차종·증상 선택, (LLM 데이터 있는 사례) 라벨 방식 전환, 차트(미래 구간 회색, as_of가 조사 개시를 지나면 조사 개시선), 재생 버튼과 슬라이더. 오른쪽: 이 시점까지의 경보 목록 → 펼치면 브리프·근거·결정 버튼.
- 상태 문장 예: "공식 조사까지 7개월 남은 시점, 경보 없음" / "2018.08부터 경보가 이어지고 있음. NHTSA는 아직 조사 전" / "NHTSA 조사 개시보다 209일 먼저 확인 가능" / "놓친 사례".

**③ 검증 결과**
- 2×2 막대(dev/holdout × 사례/대조) + 설명, 검토 업무량 문장, 키워드 vs LLM 비교 섹션, 38건 표(행 클릭 → 재생), 방법과 한계.

배포: 사용자 선택(2026-10-09)에 따라 `next build` → `web/out`을 Cloudflare Pages에 정적 배포한다. 서버 없이 상대 경로로 `data/*.json`을 fetch한다.

### Step 10. 대표 신고 요약 `brief.py` (P1) — 요청서 3번 항목
- 대상: console.json 범위(2018-03~10)의 실제 경보 칸 전부. 데모 고정 사례(SONATA 화재 2018-08)는 반드시 포함.
- 입력: 경보 수치 + 그 칸 근거 신고의 summary_ko·odino·발생 상황 플래그(화재>부상>충돌>심각도 순 최대 10건). 프롬프트 `docs/LLM_PROMPTS.md` §2. **제공된 신고 밖의 사실 금지, 모든 주장에 #ODINO, 원인·결함 단정 금지.** 결과는 `data/labels/briefs.json` 캐시.
- 현재 방식(ADR-024, 사용자 선택): 모델은 제공된 번호 enum에서 중복 없이 `selected_ids` 1~3개만 선택한다. 새 종합 문장을 쓰지 않는다. 프로그램은 실제 경보 값으로 첫 통계문을 만들고 선택된 기존 `summary_ko`를 `(#ODINO) 기존 요약`의 독립 줄로 그대로 연결한다. 기존 요약의 단어·숫자·마침표를 고치지 않는다.
- 검사 `tests/test_request.py`·`test_brief_generation.py`: 모든 brief의 #번호가 해당 칸 evidence ids와 실제 제공된 근거 안에 있다. 같은 칸·접수월·미래 정보·수량·개인정보·단정 검사를 유지하고 그대로 인용할 수 없는 요약은 거부한다. 최초 선택 뒤 재선택은 최대 2회이며 그래도 실패하면 brief 없이 내보낸다. 읽을 때 선택 번호와 현재 요약으로 재구성한 문자열이 정확히 일치해야 하며 이전 자유 서술 캐시는 재사용하지 않는다.
- 표시명은 “대표 신고 요약 (AI 요약 인용·담당자 검토)”다. 기존 AI 요약의 원문 의미 정확성과 신고 분류 정확도는 미측정이며 담당자 원문 대조가 필요하다. 대표 인용은 전체 신고의 동일 상황·빈도·공통 원인을 뜻하지 않는다. 공개 `briefs` 문자열 계약은 유지한다.
- 요청서 나머지 항목은 LLM이 쓰지 않는다. `LLM_PROMPTS.md` §3 구조에 파이프라인 값과 담당자 입력을 채운다.

## 5. 콘솔 우선순위 (선택 사항 · 데모용 가정, 쓰면 화면에 명시)
> 5단계 흐름에서는 경보 목록을 배수 순으로 정렬하는 것으로 충분하다. 시간이 남을 때만 아래 점수를 붙인다.

`score = 10×min(log2(n/max(λ,0.5)), 4) + 6×min(근거 중 화재, 5) + 6×min(부상자, 5) + 4×min(연속 경보−1, 3) + 5×min(같은 달 같은 증상 급증 차종 수, 4)`

## 6. 당일 개선 후보 (검증과 개선 점수용 — 하나 이상 실제로 하고 기록)
1. **대조군 품질**: 신고량이 너무 적은 대조군(예: SMART FORTWO COUPE ELECTRIC 1건, MERCEDES GLE350 23건)이 있다. "사례 신고량의 30% 이상" 조건을 추가해 다시 고르고 결과 비교.
2. **공정한 비교**: 사례는 차종이 여러 개 묶이는데 대조군은 1개. 차종 1개짜리 사례만으로 다시 계산(10/8: 사례 6/20 vs 대조 1/19).
3. **LLM 라벨 효과**: 같은 데모 범위에서 키워드 vs LLM 탐지 비교(10/8: 시점은 동일, LLM이 엔진 파손 범주를 새로 드러냄).
4. **라벨 검수(당일 미완료·후속 과제)**: 사람이 독립 30건 정답을 달아 키워드·LLM을 대조하려던 계획이다. 자료는 준비했지만 사용자가 도메인 지식·공모전 시간 제약으로 검수 완료를 취소했다(ADR-020·S23). 완료 정답은 0건이고 분류 정확도는 미측정이다. AI 정답으로 대체하지 않으며 전문가의 독립 검수는 후속 미완료 과제로 남긴다.
5. **추세 띠 검증**: 백테스트의 모든 경보에서 "다음 달 실제 건수가 추세 연장 띠 안에 든 비율"과 "평소 범위 띠 안에 든 비율"을 계산해 검증 결과 화면에 싣는다. 추세 띠를 '가정'에서 '확인된 참고치'로 올릴 수 있는지 판단 근거.
