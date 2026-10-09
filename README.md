# EarlySignal — 고객의 작은 불만이 큰 사고가 되기 전에

> DevDay Exchange Community Hackathon Seoul (2026-10-09), Track 1 AI for Safety & Resilience, 팀 FinVibe

소비자 결함 신고(자유서술)를 LLM이 증상 라벨로 바꾸고, 차종×증상별 월간 신고를 통계로 감시해 **조사해야 할 안전 신호를 더 일찍 찾는** 도구입니다. 결함이나 리콜을 판정하지 않으며, 최종 결정은 담당자가 합니다.

- 데모: {배포 URL}  /  녹화 영상: {링크}
- 발표 자료: {PDF 링크}

![콘솔](docs/img/console.png)

## 문제
{2~3문장: 신고는 조사·리콜보다 먼저 쌓이지만, 표현이 제각각이라 묶이지 않고 늦게 발견된다. 2018 BMW 사례.}

## 어떻게 판단하나
신고 원문 → **LLM 라벨(측정)** → 차종×증상 월별 집계 → **포아송 기준 경보(판단)**: 직전 12개월 평균 대비 p<0.001 그리고 3건 이상 → **담당자 결정(조사 착수/보류/기각)**

## 검증 결과 (당일 재현 값으로 채우기)
| | 조사로 이어진 차종 | 대조 차종 |
|---|---|---|
| dev | {8/19} | {0/19} |
| holdout | {7/19} | {1/17} |

- 미래 정보 차단 테스트: {통과 / cut-off n개}
- 대표: PE19003 현대 비충돌 화재 {209}일 먼저, PE19004 기아 {240}일 먼저
- 놓친 사례: {볼트 EV 등, 이유}
- 키워드 vs LLM 라벨: 일치 {x}%, 사람 검수 30건 정확도 키워드 {a}% / LLM {b}%
- 검토 업무량: 차종당 월 {0.08}건 경보

## 직접 확인한 것 / 가정 / 다음 단계
- 확인: {위 결과}
- 가정(미검증): 현업 수용성, 판매량 보정 효과, 국내 데이터 적용성, 우선순위 가중치
- 다음: 기업 VOC·보증 데이터 연동, 급성 결함용 고위험 단건 알림, 부품사용 브랜드 횡단 뷰

## 도입과 운영
- 대상: 완성차·부품사 품질/제품안전팀, 규제기관
- 운영: 매일 아침 콘솔 검토 → 조사 요청서 → 결정 이력 축적
- 비용: LLM 라벨 1,000건당 약 ${당일 측정값}, 월 신규 신고 처리 비용 {추정}

## 실행 방법
```bash
pip install -r pipeline/requirements.txt
python -m es.cli download            # NHTSA zip → data/raw
python -m es.cli ingest
python -m es.cli scope
python -m es.cli label-kw
OPENAI_API_KEY=... python -m es.cli label-llm   # 캐시: data/labels/labels_llm.jsonl
python -m es.cli detect && python -m es.cli backtest
pytest pipeline/tests
python -m es.cli export              # → web/public/data
cd web && npm install && npm run build   # → web/out (정적 배포)
```

## 사전 작업과 당일 작업의 구분
- **행사 전(10/8)**: 기획·명세 문서(`AGENTS.md`, `docs/*.md`, AI 도움을 받아 작성), 사례 목록 `data/cases_pool.yaml`, 데이터 탐색과 설계 검증(시제품 코드는 포함하지 않음). 자세한 내용과 시제품 수치는 [`docs/RESEARCH.md`](docs/RESEARCH.md).
- 행사 시작 시점 상태: 코드 없음. `[pre-work]` 커밋 = 위 문서와 사례 목록.
- **당일(10/9, Codex로 작성)**: {Step 1~10 목록, 당일 개선 내역(예: 대조군 신고량 조건 추가, 라벨 검수), OpenAI 라벨}
- Codex 활용 기록: [`docs/CODEX_LOG.md`](docs/CODEX_LOG.md)

## 외부 자산
- 데이터: NHTSA Office of Defects Investigation 신고·조사 파일(퍼블릭 도메인), {다운로드 일자}
- 모델: OpenAI {모델명} (라벨링·브리프)
- 라이브러리: DuckDB, pandas, SciPy, Next.js, Tailwind CSS, Recharts
- 폰트: IBM Plex Sans KR (SIL OFL)
