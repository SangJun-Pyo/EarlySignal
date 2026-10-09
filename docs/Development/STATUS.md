# EarlySignal 현재 제품·검증 상태

현재 설명은 커밋된 공개 결과와 배포 검수에 근거한다. 과거 실행·수정 과정은 [CODEX_LOG](../CODEX_LOG.md), 설계 변경은 [ADR](../ADR/README.md)에 보존한다.

## 완료된 제품과 결과

- [공개 제품](https://earlysignal.pages.dev/): 신고 원문 → 신호와 근거 → 조사 요청서. 담당자가 인용·제외, 조사 착수·보류·기각, 다음 조치를 정해 저장하고 Markdown·판단 JSON을 내려받는다.
- 전체 데모7,502건의 LLM 분류·출력 검사 완료. 콘솔은 현대·기아9개 차종의2018-03~10 접수월을 제공하고 기본월은2018-08이다.
- 공개JSON45개, 콘솔 신고2,142건·근거421칸. 대표 신고 요약은18개 경보 중16개 공개하고 수량 표현 검사에 걸린2개는 요약 없이 근거를 제공한다.
- 38사례·36대조의 주 백테스트는 키워드 기준선이다. dev9/19·대조0/19, holdout7/19·대조1/17. 실패·지연 사례와 별도 민감도 분석을 보존한다.
- 같은7,502건의 키워드·LLM 주 라벨 일치는3,793건이다. 정확도가 아니다. 같은4,464칸의 경보는34개·39개이며 LLM 우위를 입증하지 않는다.
- 누적 라벨·요약 실험 반환 사용량 추정$4.5740896. 실패·진단을 포함하며 청구액·잔액이 아니다. 정확한 현 캐시 건당단가는 미측정이다.
- 지정 PE19-003·004 대비209·240일과 선행 청원·조사 이력을 함께 표시한다. 기관 최초 인지·최초 조사보다 먼저 발견했다는 뜻이 아니다. 볼트 EV는 키워드 놓침·LLM23일 늦음이다.

## 검수 근거

[공개 배포 검수](../../data/results/deployment_llm_verification.json)는 `8b50a75` 배포의45JSON 바이트 일치, 실제 요청서 저장·다운로드·재접속 이력 확인 기록이다. 그 시점의 Python224개·웹26개 검사와 타입·정적 빌드를 통과했다. 이후 변경의 최신 CI·배포 결과는 해당 PR·세션을 따른다.

계산상 미래 접수 차단·64칸 독립 계산은 [R01](../Reviews/R01-methodology.md), 전체 분류 출력·동일 모집단 비교는 [R06](../Reviews/R06-full-llm-audit.md), 대표 요약·비용은 [R08](../Reviews/R08-brief-completion.md)에 있다. 이 검수들은 원문 의미의 사람 정답 정확도를 측정한 것이 아니다.

## 현재 안내 최신화

이슈#27의 전수 점검으로 홈페이지·README·현재 SPEC·계약·ADR 후속 상태·발표 링크를 맞췄다. 웹PR#28·문서PR#30은 각각 독립 검수 후 통합했다. [S37](../Sessions/S37-current-copy-audit.md)과 [공개 문구 검수](../../data/results/deployment_copy_verification.json)는 웹1db76f7의 새 문구, 공개45JSON 동일, 실제 요청서 저장·다운로드·재접속5기록을 확인한다. 과거 시험과 검수 보고는 당시 상태로 보존한다.

## 발표 산출물

- [예선 최종 PDF](../presentation/output/pdf/EarlySignal-preliminary-4min-simple.pdf): 본문7+부록15=22페이지,240초 배분·데모60초·상세 검증은 부록.
- [결선 최종 PDF](../presentation/output/pdf/EarlySignal-finals-8min-qa2min-final.pdf): 본문9+부록14=23페이지,480초 발표·데모+질의응답120초.
- [예선4분 Markdown 대본](../presentation/speaker-script-4min.md). 아래 기존 대본의 예선9장 부분은 이전 구성이다.
- [결선·질의응답 참고 대본](../presentation/speaker-script-final.md)·[인쇄용 대본PDF](../presentation/output/pdf/EarlySignal-presentation-script-final.pdf): 읽을 문장·조작·예상질문 포함. S39에서 이슈#35 연식 분석 후속 부록을 각2쪽 추가했다. 기존39쪽과 검수 스냅샷은 보존한다.
- [노트](../presentation/speaker-notes.md)·[근거표](../presentation/evidence-manifest.md)·[R09](../Reviews/R09-final-presentation.md). 총39페이지 독립 렌더·글리프·수치·출처·외관 검수 완료.

기본 근거판·DRAFT 호환본과 `qa.json`은 과거 검수 스냅샷으로 보존한다. 이전 3D v2와 대본은 [R12](../Reviews/R12-year-appendix-script.md)·`qa-v2.json`에서 별도로 검수했다. R09의39쪽은 기본판, R11은3D장식판, R12는연식부록·대본의 검수다. 현재 발표자 표기 최종본은 S41·R13·qa-final.json에서 검수했다.

## 남은 검증과 범위

사용자는 독립30건 자료로 검수를 시도했으나 도메인 전문성·시간 제약으로 완료하지 않기로 했다. **완료된 사람 정답0건, 분류·요약 의미 정확도 미측정**이며 AI를 정답으로 대체하지 않는다([ADR-020](../ADR/ADR-020-independent-blind-human-review.md), [S23](../Sessions/S23-human-review-deferred.md), 이슈#7).

타이머를 켠 실제 발화·조작 리허설, 동일 버전 장애 대비 녹화, 제출은 아직 수행하지 않았다. 제품·자료 완료와 시간 내 발표·제출 완료를 구분한다.

현업 검토 시간·구매 의사·실제 사고 예방 효과, 정비/생산 자료 연동·가설 생성, 유사 사례/RAG 검색은 미검증 또는 미구현이다. 콘솔의2024년까지 기간 확장은 후속 실험이다. 사전 목표 시각과 초기50건·중간 PDF 기록은 역사이며 현재 진행 상태가 아니다.
