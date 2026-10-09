# LLM 프롬프트 (OpenAI, Structured Outputs)

## 1. 신고 라벨링 (`label_llm.py`)

### system
```
You label U.S. vehicle owner safety complaints (NHTSA) for a statistical early-warning system.
Judge ONLY from the complaint text. Do not use brand/model knowledge. Do not infer causes that are not stated.

primary_category: exactly one of
  fire_thermal       fire, flames, smoke, burning smell, melting, overheating parts
  electrical_failure electrical/battery/electronics malfunction WITHOUT fire or smoke (dead battery, warning lights, display, camera, sensors)
  loss_of_power      vehicle loses propulsion or will not accelerate while moving
  engine_stall       engine shuts off / stalls
  engine_failure     internal engine damage (rod knock, seized engine, oil starvation, engine replaced) when that is the main issue
  airbag, brakes, steering, seat_belt, fuel_leak, transmission, lighting,
  suspension         control arms, links, ball joints, springs, struts
  structure_body     doors, latches, hood, glass, trim, body or frame rust
  tires_wheels, other
secondary_categories: 0-2 other categories clearly present; never repeat the primary.
hazards: true only when the text explicitly supports it.
severity: 1 = defect/inconvenience only, 2 = safety concern without actual harm, 3 = actual crash, fire or injury happened.
Recall-notice-only complaints (no failure experienced): category of the recalled part, severity 1.
evidence_quote: copy 40-200 characters VERBATIM from the complaint that best supports the label.
summary_ko: one Korean sentence, max 40 characters, describing the safety issue (e.g. "주행 중 엔진룸에서 연기가 나고 화재 발생").
If unclear, use "other".
```

### user
```
Complaint:
{text}
```

### JSON Schema (strict)
```json
{
  "type": "object", "additionalProperties": false,
  "required": ["primary_category", "secondary_categories", "hazards", "severity", "evidence_quote", "summary_ko"],
  "properties": {
    "primary_category": {"type": "string", "enum": ["fire_thermal","electrical_failure","loss_of_power","engine_stall","engine_failure","airbag","brakes","steering","seat_belt","fuel_leak","transmission","lighting","suspension","structure_body","tires_wheels","other"]},
    "secondary_categories": {"type": "array", "items": {"type": "string", "enum": ["fire_thermal","electrical_failure","loss_of_power","engine_stall","engine_failure","airbag","brakes","steering","seat_belt","fuel_leak","transmission","lighting","suspension","structure_body","tires_wheels","other"]}},
    "hazards": {"type": "object", "additionalProperties": false,
      "required": ["fire","smoke","crash","injury","while_driving","while_parked_or_charging"],
      "properties": {"fire": {"type": "boolean"}, "smoke": {"type": "boolean"}, "crash": {"type": "boolean"},
                     "injury": {"type": "boolean"}, "while_driving": {"type": "boolean"}, "while_parked_or_charging": {"type": "boolean"}}},
    "severity": {"type": "integer", "enum": [1, 2, 3]},
    "evidence_quote": {"type": "string"},
    "summary_ko": {"type": "string"}
  }
}
```
후처리: secondary에서 primary 제거·최대 2개, `evidence_quote`가 원문 부분 문자열인지 검사해 `quote_mismatch` 비율 출력.

## 2. 경보 브리프 (`brief.py`)

> 당일 검수 보완: 첫 통계 문장은 LLM이 쓰지 않고 `statistics_sentence()`가 실제 경보 값으로 만든다. 아래 사전 프롬프트·예시는 준비 당시 형식이다. 현재 자유 서술은 근거 상황과 #ODINO만 쓰며, #ODINO 외 숫자·수량 표현을 포함하면 버린다. `compose_brief()`가 고정 통계문과 인용 서술을 합친 뒤 검증한다. 문장의 의미는 담당자 검토가 필요하다. 현재 키워드 화면에는 briefs가 비어 있다.

### system
```
당신은 제품 안전 담당자를 돕는 분석 보조입니다. 아래 경보 수치와 근거 신고 요약만 사용해 한국어 브리프를 2~3문장으로 씁니다.
규칙:
- 제공된 신고에 없는 사실, 원인, 부품, 공급사를 추측하지 않는다. "결함", "원인은", "리콜될" 같은 단정 표현 금지.
- 첫 문장: 차종, 증상, 이번 달 건수와 평소(직전 12개월 평균) 대비.
- 둘째 문장: 근거 신고에서 반복되는 상황 패턴과 대표 신고 번호 2~3개를 (#번호) 형태로.
- 필요하면 셋째 문장: 같은 시기 함께 급증한 다른 증상·차종(제공된 경우만).
```

### user (예시 형식)
```
차종: KIA OPTIMA / 증상: 화재·과열 / 월: 2018-10 / 접수 19건 / 평소 월 2.6건 / 연속 경보 1개월
같은 달 같은 증상 급증 차종: HYUNDAI SONATA, KIA SORENTO, KIA SOUL
근거 신고:
#11132429 (2018-10-01, 화재, 부상 1): 주행 중 엔진룸 폭발음과 화재로 충돌, 운전자 부상
#11133307 (2018-10-04, 화재): 고속도로 주행 중 연기와 화염, 브레이크 불능
...
```

### 시제품 브리프 예 (품질 기준)
> 옵티마 화재 신고 19건(평소 월 2.6건, 약 7배). 주행 중 연기와 화염이 나면서 제동·조향이 함께 상실됐다는 신고가 있고(#11133307, #11139148), 운전자 부상도 1건 보고됐습니다(#11132429).

## 3. 조사 요청서 구조 (LLM이 쓰지 않음 — `web/lib/request.ts`가 값으로 채움)
```
# 조사 요청서 {문서번호} ({초안|확정})
- 조사 대상: {차종} ({제조사}) · {증상}
- 분석 기준: {YYYY년 M월} 접수분까지 · 작성 가능일 {YYYY.MM.01}
- 데이터: NHTSA 소비자 신고 · AI 라벨 · 통계 경보(직전 12개월 대비, p<0.001, 3건 이상)

## 1. 신고 증가와 경보 근거
이번 달 {n}건, 평소 {λ}건, {배수}배 (p={p}). 연속 경보 {k}개월. 같은 시기 같은 증상 경보 차종: {목록|없음}.
최근 6개월: {월 n · …}

## 2. 반복되는 발생 상황 (AI 라벨, {N}건 기준)
{주행 중 a건 · 연기 b건 · 화재 언급 c건 · …}
함께 언급: {증상 n, …} / 연식: {연식(n), …}

## 3. 상황 요약 (AI 작성, 담당자 검토)
{brief — §2 결과, #번호 인용}

## 4. 인용 신고
- #{odino} {접수일} {summary_ko}            ← 담당자 인용
- #{odino} {접수일} {summary_ko} [AI 요약이 인용]
검토 후 제외 {m}건(#…). NHTSA ODI 번호로 원문 조회 가능.

## 5. 아직 확인되지 않은 사항
- 원인과 결함 여부 / 판매·운행 대수 대비 신고 비율 / 동일인·중복 신고 여부 / 정비·리콜 수리 이력 / 미국 외 시장 발생 여부

## 6. 내부 데이터로 확인할 항목
- AS·보증 수리 이력({연식}) / 생산 이력(MES): 생산 기간·공장·엔진 LOT / 부품 공급사·변경 이력

## 7. 담당자 판단과 다음 조치
판단: {조사 착수|보류|기각} / 다음 조치: {선택 항목} / 메모: {자유 입력}

> 결함·원인 판정이 아니라 조사 착수 여부를 정하기 위한 자료입니다.
```
