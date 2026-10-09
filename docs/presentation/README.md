# EarlySignal 발표자료

## 현재 예선: 4분 발표 7장

- [예선 4분 PDF](output/pdf/EarlySignal-preliminary-4min-humanized.pdf): 본문7 + 부록15 = 22쪽. 발표자 표상준.
- [4분 대본 Markdown](speaker-script-4min.md): 읽을 문장과 조작 메모. 대본 PDF는 새로 만들지 않는다.
- 문제→역할→60초 시연→증가 신호→검증 범위→마무리 순서다. 상세 통계·키워드/LLM 비교·도입/Codex는 부록으로 옮겼다. 기존11개 부록도 보존하며 이슈#35는21·22쪽이다.
- 시간은20·30·25·60·35·40·30초=240초 배분이며 실제 리허설은 미완료다.
- 재생성: `python docs/presentation/build_simple_deck.py --storyboard docs/presentation/storyboard-humanized.json --manifest docs/presentation/humanized-build-manifest.json`. 원본은 `storyboard-humanized.json`, 근거·해시는 `humanized-build-manifest.json`, 검수는 `qa-humanized.json`·[R15](../Reviews/R15-presentation-copy.md).
- 심사 기준01·02에 맞춰2장의 담당자·키워드 한계,3장의AI 입력과 역할을 명시했다. im-not-ai light 윤문 게이트 통과. 이전7장 PDF와 R14/qa-simple, 이전 대본 history는 보존한다.
- 결선은 아래23쪽 최종본과 기존 결선 대본을 사용한다. 이전 예선20쪽과 검수는 보존한다.

## 결선 최종본·이전 예선 보존본

- [이전 예선 4분 PDF](output/pdf/EarlySignal-preliminary-4min-final.pdf): 본문9 + 부록11 = 20쪽.
- [결선 8분 + 질의응답 2분 PDF](output/pdf/EarlySignal-finals-8min-qa2min-final.pdf): 본문9 + 부록14 = 23쪽.
- [기존9장 구성 발표 대본 PDF](output/pdf/EarlySignal-presentation-script-final.pdf): 10쪽. [편집용 Markdown](speaker-script-final.md).
- 표지·본문 마무리·대본 첫 쪽과 PDF 작성자에 표상준을 표기했다. 추가 장식 없이 기존 구도를 유지하고 7쪽의 검증 대조 막대를 실제 1/17 비율에 맞췄다. 수치·문구·시간 배분은 유지한다.
- 재생성: `python docs/presentation/finalize_pdfs.py`. 발표자 설정은 `finalization.json`, 입력은 아래 보존본과 `qa-v2.json`이다. 입력 SHA256이 바뀌면 중단한다. 대본을 편집할 때에는 `speaker-script.json`에서 시작하고 새 입력 PDF의 검수·해시도 갱신해야 한다.
- 근거와 출력 해시는 `final-build-manifest.json`, 순서는 `storyboard-final.json`, 검수는 `qa-final.json`·[R13](../Reviews/R13-presentation-final.md)이다. 이전 검수 스냅샷과 PDF는 보존한다.

## 이전 3D v2: 모델연도 부록 + 발표 대본 (보존)

- [예선 4분 PDF](output/pdf/EarlySignal-preliminary-4min-3d-v2.pdf): 본문 9 + 부록 11 = 20쪽. 새 연식 부록은 19·20쪽.
- [결선 8분 + 질의응답 2분 PDF](output/pdf/EarlySignal-finals-8min-qa2min-3d-v2.pdf): 본문 9 + 부록 14 = 23쪽. 새 연식 부록은 22·23쪽.
- [전체 발표 대본 PDF](output/pdf/EarlySignal-presentation-script.pdf): 예선·결선 발화, 데모 조작, 30초·60초 연식 답변, 예상 질문을 담은 10쪽. [편집용 Markdown](speaker-script.md)과 `speaker-script.json`도 제공한다.
- [이슈 #35](https://github.com/SangJun-Pyo/EarlySignal/issues/35)의 현재 연식 통합 감시와 후속 분석을 구분했다. 17건은 공개 근거 ID로 다시 집계한 2011년식4·2012년식5·2013년식7·2014년식1건이다. 위험률·세대 동일성·연식별 성능을 의미하지 않는다.
- 기존 3D판 39쪽을 모두 보존하고 부록만 2쪽씩 추가했다. 본문 9쪽·240/480초 배분은 유지하며 실제 타이머 리허설은 별도다. 제품 기능·통계 규칙은 변경하지 않았다.
- 재생성: `python docs/presentation/build_year_appendix.py`, `python docs/presentation/build_speaker_script.py`. 근거는 `year-appendix-source.json`, 순서는 `storyboard-v2.json`, 검수는 `qa-v2.json`·R12에 기록한다.

## 이전 3D 디자인 버전 (2026-10-09, 보존)

사용자가 제공한 Truve 레퍼런스의 남색 배경·유리 소재 3D 표현을 EarlySignal의 청록색에 맞췄다. 표지·문제 설명·역할 분담·마무리(1·2·3·9쪽)에만 새 개념 이미지를 넣었다. 기존 최종본과 과거 검수 기록은 그대로 보존한다.

- [예선 4분 3D 디자인 PDF](output/pdf/EarlySignal-preliminary-4min-3d.pdf): 본문 9 + 부록 9 = 18쪽.
- [결선 8분 + 질의응답 2분 3D 디자인 PDF](output/pdf/EarlySignal-finals-8min-qa2min-3d.pdf): 본문 9 + 부록 12 = 21쪽.
- [주요 디자인 미리보기](output/3d-design-preview.jpg).
- 편집 원본: `build_3d_decks.py`. 기존 최종 PDF·storyboard를 입력으로 쓰며 `python docs/presentation/build_3d_decks.py`로 재생성한다. Python 패키지는 reportlab·pypdf가 필요하다.
- 이미지: `assets/3d/`의 PNG 4개. built-in image_gen으로 제작했으며 최종 프롬프트는 `assets/3d/prompts.json`, 해시는 `output/pdf/3d-build-manifest.json`에 있다. 차량·문서·파형은 개념 이미지다.
- 검수: `qa-3d.json`, [R11](../Reviews/R11-presentation-3d.md). 수정 8쪽 독립 시각 검수·영역 밖 문자 0개, 나머지 31쪽 원본 대비 픽셀·텍스트 일치. 6개 통계 근거 테스트 통과. 시간 배분과 수치·한계는 그대로이며 실제 리허설은 별도다.

사용자가 확정한 “고객의 목소리를, 조사의 근거로.”의9장 서사다. LLM 분류 7,502건을 적용한 제품과 키워드 38사례 통계 검증을 구분한 발표자료다. 예선에서도 실제 월별 집계와 포아송 경보를 본문 두 장으로 설명한다. 사람 정답 기반 분류 정확도와 현업 효과는 미측정이다.

## 기본 근거판 두 버전 (보존)

| 파일 | 구성 | 시간 |
|---|---|---|
| `output/pdf/EarlySignal-preliminary-4min.pdf` | 본문 9장 + 부록 9장 | 발표·데모 240초 |
| `output/pdf/EarlySignal-finals-8min-qa2min.pdf` | 본문 9장 + 부록 12장 | 발표·데모 480초 + 질의응답 120초 |

위 표는 R09에서 검수한 기본 근거판이며, 현재 제출용 파일은 문서 상단의 발표자 표기 최종본이다. 이전 `DRAFT` 파일은 기본 근거판과 같은 바이트의 호환본으로 유지한다. 부록은 시간 외 참고자료다. 시간은 배분안이며 실제 타이머 리허설 완료를 뜻하지 않는다. 예선 제품 조작은 60초, 결선은 100초(후속 조사 설계 설명 10초 포함)다.

## 실제 결과와 한계

- 공개 제품은 LLM 분류 7,502건의 출력 검사 완료 결과다. 초기 50건의 인용 실패 14건을 원문 후보 선택으로 개선한 기록도 보존한다. 형식·원문 인용 검사 통과는 분류 정확도가 아니다.
- SONATA 화재·과열의 직전 12개월 합계는 59건, 평균 4.9167건이다. 2018년 8월은 17건·3.46배, 포아송 상측 확률은 0.000016130219674다. 실제 월별 건수와 가정한 확률분포를 구분한다.
- 38사례 주 백테스트는 키워드 기준선이다. 개발 사례9/19·대조0/19, 검증 사례7/19·대조1/17을 보존한다. 키워드의 기준일38회·64칸 검산, 같은 데모의 두 방식 각4,464칸 독립 검산과 모형 적합성 미검증도 구분한다.
- 같은7,502건의 주 증상 일치는3,793건(50.56%)이다. 정확도가 아니다. 같은4,464칸의 경보는 키워드34·LLM39개다. 지정 예비조사(PE) 개시일 대비 현대·기아209·240일은 같고 볼트는 키워드 놓침·LLM23일 늦음이다. 비교는 제한된 데모 관측창이며 LLM 우위를 입증하지 않는다. 앞선2018청원·검토가 있으므로 기관 최초 인지·조사보다 먼저 발견했다는 뜻도 아니다. 공식 타임라인은 기존 평가 부록에 담았다.
- 대표 신고 요약은18개 경보 중16개 공개,2개 수량 검사 실패다. AI가 번호1~3개만 고르고 코드가 기존 신고별 AI 요약을 그대로 연결한다. 기존 요약47회 복사의 일치를 검사했으나 의미 정확도나 대표성을 검증한 것은 아니다.
- 자유 종합54응답0/18 통과→구조화1개 형식 통과 후 의미 과장으로 공개 거부→기존 요약 인용의 개선 과정을 부록에 남긴다. 실패 요약을 고치거나 검사를 완화해 통과시키지 않았다.
- 누적 실험은 라벨$4.5448836 + 요약$0.0292060 = **$4.5740896**이다. 초기 실패·진단을 포함한 반환 사용량 추정이며 실제 청구액은 아니다. 초기 사용량 일부의 캐시 연결 누락으로 정확한 건당 단가는 미측정이다.
- 독립30건 검수 자료를 준비하고 사용자가 직접 시도했지만 전문성·시간 제약으로 당일 검수를 완료하지 않았다. 사람 정답0건, 정확도 미측정이다. AI를 사람 정답 대신 사용하지 않았으며 전문가 검수는 후속 계획이다.
- pgvector/RAG·유사 과거 사례 검색·별도 부품 추출은 미구현이다. 원래 기획과 현재 구현의 차이 및 보완 이유를 남겼다. 조사 가설·정비 기록·검사 확인은 설계이며 실제 원인 추정·자료 연결 기능은 없다.

## 편집 원본과 근거

- `build_decks.py`: ReportLab 편집 원본. console·meta·비교·요약 감사 결과를 읽는다.
- `figures/build_stat_figures.py`: console의 라벨 출처·데모 월·현재 건수·기준선을 계산하고 export와 독립 대조한다.
- `figures/source.json`: 수치·분모·확률·출처 SHA256·모형 가정.
- `storyboard.json`, `speaker-notes.md`: 순서·근거·초 단위 배분·발표와 질의응답 설명.
- `evidence-manifest.md`, `qa.json`: 주장·근거·한계 및 파일 해시·렌더 검수.
- `SESSION.md`, `../Sessions/S25-llm-presentation.md`: 결정·수정·실제 실행 기록.

그림과 PDF는 로컬 공개 결과만 읽으며 API를 호출하지 않는다. 아래 명령은 편집 후 새 산출물을 생성하는 명령이며, 실행 뒤에는 새 해시·렌더 검수가 필요하다. 이미 검수한 최종 PDF를 열기 위해 재생성할 필요는 없다. Python3.10+와 reportlab·matplotlib·scipy·numpy가 필요하다.

```bash
python docs/presentation/figures/build_stat_figures.py
python docs/presentation/build_decks.py
```

출력은 `output/pdf/`다. IBM Plex Sans KR 폰트의 라이선스는 `assets/OFL.txt`에 있다. 과거50건 시험 완료 중간 PDF는 parent commit `db26888`에 보존돼 있다.

## 최종 검수

main8b50a75의 실제 LLM 공개 화면 두 장을 변경 없이 복사했다. 요청서 저장 시각은2026-10-09 13:17:28 KST이며 촬영 시각은 별도 미기록이다. 캡처 출처·파일 해시는 `assets/screenshots/request-public.json`에 남겼다. 두 PDF 총39페이지를 렌더링해 QA를 갱신했다. 내용·그림·글리프·출처·시간을 독립 검수했고, 최종 표기 변경의 외관 검수도 통과했다. 실제 타이머 리허설과 동일 버전 장애 대비 녹화는 미완료다. 구현자 외 독립 검수와 PR #25 통합을 완료했다. `qa.json`의 PDF 검사·36개 원본 해시는 당시 스냅샷이며, 이후 문서 변경을 다시 검수했다고 의미하지 않는다. 최종 이름 추가는 기존 파일과 바이트 일치만 별도 확인했다.
