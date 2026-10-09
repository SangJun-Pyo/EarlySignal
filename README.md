# EarlySignal — 고객의 목소리를, 조사의 근거로.

> 2026-10-09 DevDay Exchange Community Hackathon Seoul · Track 1 AI for Safety & Resilience · FinVibe

자동차 회사에서 고객 안전을 살피는 담당자를 위한 조사 준비 도구입니다. 서로 다르게 쓰인 소비자 신고를 증상별로 정리하고, 평소보다 증가한 신호의 원문을 검토해 근거가 연결된 조사 요청서를 만듭니다. 담당자가 조사 착수·보류·기각을 결정합니다.

**진행 상태:** 전체 7,502건의 LLM 분류·출력 검사와 같은 모집단 비교를 완료하고 Cloudflare에 배포했습니다. 대표 신고 AI 요약은 18개 경보 중 16개에 기존 요약을 그대로 인용하고 번호를 연결합니다. 나머지 2개는 수량 표현 검사에서 거부돼 요약 없이 근거를 제공합니다. 공개 JSON 45개가 검수본과 일치하고 실제 요청서 저장·다운로드·재접속 후 이력 유지를 확인했습니다. Python 224개·웹 26개 검사와 타입·정적 빌드를 통과했습니다. 38사례 주 백테스트는 **키워드 기준선**이며, 사람 정답 기준 분류 정확도는 미측정입니다. [공개 데모](https://earlysignal.pages.dev/) · [공개 배포 검증 기록](data/results/deployment_llm_verification.json)

- [4분 예선 발표 초안](docs/presentation/output/pdf/EarlySignal-preliminary-4min-DRAFT.pdf)
- [결선 8분 발표 + 2분 질의응답 초안](docs/presentation/output/pdf/EarlySignal-finals-10min-DRAFT.pdf)
- [Codex 작업 기록](docs/CODEX_LOG.md) · [독립 검수](docs/Reviews/R01-methodology.md) · [현재 진행 상태](docs/Development/STATUS.md)

## 필요한 이유와 업무

운전자는 같은 현상을 ‘타는 냄새’, ‘연기’, ‘과열’처럼 다르게 설명합니다. 고객 안전 담당자는 많은 신고 속에서 반복되는 문제를 모으고, 조사할 이유를 원문 근거와 함께 정리해야 합니다. EarlySignal은 **경보 선택 → 원문 인용·제외 → 조사 요청서 저장**을 하나의 흐름으로 연결합니다.

AI는 원문을 정해진 증상과 상황으로 정리하고, 통계는 같은 차종의 과거 신고 건수와 비교하며, 사람은 근거를 검토하고 다음 조치를 정합니다. 같은 7,502건에서 키워드·LLM의 주 라벨은 3,793건 일치했습니다. 두 방법의 일치율은 정답 정확도가 아닙니다. 현대·기아 대표 사례의 선행 시점은 동일했고, 볼트 EV는 LLM도 23일 늦었습니다. AI의 분류 정확도와 현업 효과는 아직 입증하지 않았습니다.

## 오늘 직접 실행한 결과

원본 신고 1,301,663행에서 명세의 소비자·차량 필터와 ODINO 중복 제거를 적용한 **932,821건**을 적재했습니다. 접수일 파싱 실패는 0건, 사례·대조 범위는 122,989건, 데모 범위는 7,502건입니다. 원본 ZIP 해시는 [출처 manifest](data/results/source_manifest.json)에 있습니다.

고정 규칙: 직전 12개월 평균(최소 6개월, 하한 0.5), Poisson 상측 확률 p<0.001, 월 3건 이상. 접수월 기준으로 조사 개시 전 12개월 창을 적용하고 마지막 1개월은 제외합니다. 확인 가능일은 경보 월 다음 달 1일입니다.

| 사전 분할 | 조사 사례에 경보 | 매칭 대조에 경보 |
|---|---:|---:|
| dev | 9/19 | 0/19 |
| holdout | 7/19 | 1/17 |

이는 선정된 집단의 경보 발생 비율이며 일반적인 정확도·오탐률이 아닙니다. 여러 차종으로 묶인 사례와 단일 차종 대조군의 비대칭, 낮은 신고량의 대조군, 분할 간 차종 중복이 있습니다. 같은 규칙의 단일 차종 분석은 사례 8/20, 대조 1/19입니다. [전체 결과](data/backtest_kw.json)와 [보조 분석](data/results/sensitivity_single_group_kw.json)에 실패·지연 사례도 포함했습니다.

- PE19003: 키워드 주 검증은 2018-08 쏘나타 화재·과열 17건, 기준선 6.83건. 접수일 기준 회고적 확인 가능일과 지정 예비조사(PE) 개시일의 차이 **209일**. 현재 LLM 콘솔은 17건·기준선4.92건이며 같은 PE 대비209일이다.
- PE19004: 같은 방식으로 **240일**. 실제 조사를 앞당겼다는 효과 측정이 아닙니다.
- PE20016 볼트 EV는 현재 키워드 구현에서 **놓침**. 사전 시제품의 ‘늦음’과 다릅니다.
- 38개 조사 사례별 완료월 기준일(고유 날짜33개)에서 원본 신고를 잘라 다시 계산한 결과가 전체 계산의 같은 기간과 정확히 일치했습니다. [실행 결과](data/results/lookahead_kw.json)
- 독립 검수자가 64개 탐지 칸을 별도 계산해 기준선·확률·경보가 일치함을 확인했습니다.

**비교 사건의 한계:** PE19003/PE19004의 개시일은 2019-03-29다. 그전에 CAS 청원(2018-06-11)과 DP18-003 청원 검토(2018-08-21), 기존 엔진 리콜 관련 조사가 있었다. 209·240일은 지정 PE 대비 재현 값이며 기관의 최초 인지·최초 조사 또는 AI의 최초 발견을 뜻하지 않는다. [NHTSA 현대 개시 문서](https://static.nhtsa.gov/odi/inv/2019/INOA-PE19003-2613.PDF) · [기아 개시 문서](https://static.nhtsa.gov/odi/inv/2019/INOA-PE19004-4727.PDF)

사전 수치와의 차이를 맞추기 위해 임계값이나 키워드를 조정하지 않았습니다. 소비자 신고 16건 차이는 PROD_TYPE 공란 신고 수와 일치하며, 사전 원형 코드가 없어 당시 처리 방식은 확정할 수 없습니다. dev 8/19→9/19와 범위 건수 차이도 [세션 로그](docs/Sessions/S06-step6.md)에 공개합니다.

대표 신고 요약은 모델이 제공된 신고 번호 1~3개를 선택하고, 프로그램이 해당 신고의 기존 `summary_ko`를 그대로 복사합니다. 자유 종합에서 발견한 과한 일반화는 공개하지 않았습니다. 기존 AI 요약도 담당자의 원문 확인이 필요하며, 대표 인용이 모든 신고의 공통 상황이나 원인을 뜻하지 않습니다([ADR-024](docs/ADR/ADR-024-source-summary-selection.md)).

## 검증된 것과 남은 가정

**확인:** 실제 ZIP 적재, 고정 키워드 탐지, 등록 사례 백테스트, 계산상 미래 접수 차단, 알려진 원문 식별 패턴 제거, 7,502건 LLM 출력·출처 검사, 같은 모집단 비교와 독립 계산 검수. 신고별 AI 요약 자체의 의미 정확도 검증과는 구분합니다.

**아직 미확인:** AI 라벨 정확도·완료 배치 단가, 사람 검수 정답, 현업 검토 시간 감소, 구매 의사, 판매량 보정 효과, 국내 데이터 적용성. 현재 파일로 과거 접수일을 재현한 것이므로 당시 파일 공개·수정 상태까지 복원하지는 않습니다.

**사람 검수 미완료:** 독립 30건의 검수 자료를 준비하고 사용자가 검수를 시도했으나, 도메인 지식과 공모전 시간 제약으로 이번 제출에서는 진행하지 않기로 했습니다. 사람 정답 기준 정확도는 미측정입니다. AI가 대신 정답을 작성하지 않았습니다([ADR-020](docs/ADR/ADR-020-independent-blind-human-review.md), [S23](docs/Sessions/S23-human-review-deferred.md)).

**다음:** 후속 전문가의 독립 사람 검수, 요청서 업무의 사용자 평가, 고객 상담·보증 수리·생산 기록 연동. 대조군 구성과 차종 단위 분할 개선은 기존 평가와 구분한 새 실험으로 설계합니다.

## 도입 가설

첫 도입 후보는 자동차 회사의 고객 안전 담당자입니다. 신규 신고를 처리하고, 경보의 원문을 검토해 조사 요청서를 남기는 업무로 운영합니다. 규제기관은 추가 도입 후보입니다.

현재 대조군에서 390개 차종-월에 36개 증상 경보를 관측했습니다. 같은 발생량이 유지된다는 가정이라면 100개 차종당 월 약 9.2개 증상 경보에 해당하지만, 실제 조직의 검토량을 검증한 값은 아닙니다. 파일럿에서 요청서 준비 시간, 경보 검토량, 채택·제외 이유와 비용을 측정할 계획입니다.

고정 50건 시험에서는 실패·재시도·진단을 포함한 반환 응답 115개의 사용량 비용을 **$0.0593988**로 검산했습니다. 원문 인용 실패14건은 원문 후보 선택으로 처리했고 고정50건 전부 출력 검사를 통과했습니다. 이는 계정 청구액 대조나 사람 정답 기반 정확도가 아닙니다. 초기10개 응답의 입력 출처 연결 부족과 예산 환산의 한계를 [비용 검산](data/results/llm_pilot_completed.json)에 명시했습니다. 전체 7,502건 분류는 사용자 승인 후 완료했습니다. 실패·진단을 포함한 누적 라벨 실험 비용은 **$4.5448836**, 경보 요약은 **$0.0292060**, 합계 **$4.5740896**입니다. 이는 반환 사용량 기반 추정이며 계정 청구액이나 남은 크레딧이 아닙니다. [라벨 검산](data/results/llm_full_completed.json) · [요약·합산 검산](data/results/brief_completed.json)

## 재현 방법

Python 3.10+가 필요합니다. 저장소 루트에서 실행합니다.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install -e '.[test]'
python -m es.cli download
python -m es.cli ingest
python -m es.cli scope
python -m es.cli label-kw
python -m es.cli aggregate
python -m es.cli detect
python -m es.cli backtest --verify-lookahead
python -m es.cli export --method kw
python -m pytest pipeline/tests -q
```

API 키는 커밋하지 않는 `.env`에 설정합니다. 재현 시 먼저 고정50건 시험 결과를 확인합니다. 당일 전체 실행은 비용 보고 후 사용자가 승인했습니다.

```bash
cp .env.example .env  # 기존 .env가 있으면 덮어쓰지 마세요
python -m es.cli label-llm --limit 50 --concurrency 1 --max-attempts 1 --quote-selection-fallback
```

웹은 `cd web`, `npm ci`, `npm test`, `npm run typecheck`, `npm run build`로 검증합니다. `npm run dev`로 로컬 제품을 열 수 있습니다. API 없이 공개 JSON만으로 동작하며 판단 기록은 해당 브라우저에 저장합니다. Cloudflare Pages가 GitHub main을 web에서 npm run build로 빌드하고 out을 게시합니다. Node 26.3.0은 web/.node-version으로 고정하며 배포 환경에 OpenAI 키는 사용하지 않습니다.

## 사전 작업과 당일 작업

- **행사 전 10/8:** 기획·명세·ADR 9개, 사례 목록, 시제품 탐색 결과와 화면 설명을 준비했습니다. 사전 문서·시안에 Claude 도움을 사용한 사실을 [RESEARCH](docs/RESEARCH.md)와 S00에 명시했습니다. 시제품·시안 코드는 포함하지 않았습니다.
- **당일 10/9:** 자료만 있는 상태를 `3703356` `[pre-work]` 커밋으로 분리했습니다. Codex가 새 코드를 작성하고 구현·독립 검수·발표를 분담했습니다. 총괄이 검수 지적을 수정하고 실제 실행 결과를 통합합니다.
- [ADR](docs/ADR/) · [세션](docs/Sessions/) · [검수 기록](docs/Reviews/) · [발표 근거 연결표](docs/presentation/evidence-manifest.md)

## 외부 자산

데이터: [NHTSA ODI](https://static.nhtsa.gov/odi/ffdd/) 공개 신고·조사 파일. 원본은 저장소에 포함하지 않습니다. 구조화 식별정보를 제외하고 자유서술의 알려진 식별값·이메일·전화·VIN·주소 등을 검사합니다. 정규식 검사가 완전한 익명화를 보장하지는 않습니다.

기술: Python, DuckDB, pandas, SciPy, OpenAI SDK, Next.js, React, Tailwind CSS, Recharts. PDF: ReportLab, IBM Plex Sans KR ([OFL](docs/presentation/assets/OFL.txt)). 분류 모델: `gpt-4.1-mini-2025-04-14`(전체 7,502건 출력 검사 완료, 사람 정답 정확도 미측정).

제출 기획과 현재 구현의 차이, 보완 이유는 [ADR-017](docs/ADR/ADR-017-submitted-proposal-and-delivery-scope.md)에 기록했습니다. 유사 과거 사례 검색은 원래 기획의 미구현 항목이며, 분류 검증을 먼저 하고 RAG 근거 검색으로 보완하는 설계만 승인됐습니다.
