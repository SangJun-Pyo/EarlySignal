# S40 — Step9 컴팩트 차량 이미지·청록 강조

- 시각: 2026-10-09 (Asia/Seoul)
- 관련: SPEC Step9, ADR-022·027, 이슈 #37

## 목표
사용자가 승인한 작은 차량 이미지1장과 제목·주요 버튼의 청록 강조·은은한 빛만 적용한다.

## 완료 기준
- [x] 코드 전 ADR·세션 작성
- [x] 기존 이미지 재사용·출처 기록, 모바일 숨김·컴팩트 높이
- [x] 데이터·문구·CTA 기능 유지
- [x] 웹 tests/typecheck/build 성공·PR 준비

## Codex에 맡긴 일
별도 작업트리에서 페이지 제목·스타일·공개 이미지1장·ADR·세션만 변경한다. API·DB·원본 이미지·PDF·통계 자료는 변경하지 않는다. 기존 이미지 출처는 발표 커밋7bb7883이며 실차 근거가 아닌 장식이다.

## 결과
중복 이슈 목록을 확인하고 이슈 #37을 만들었다. 코드 전에 ADR-027과 세션을 작성했고, Next.js 설치 버전의 로컬 static export 문서를 읽었다. 발표 PR36 통합 후 `git fetch origin; git merge origin/main`으로 main39e6e07을 받았다(구현 커밋 전 fast-forward, rebase/squash 없음).

기존 컴팩트 샘플의 축소 WebP를 `web/public/images/vehicle-concept.webp`로 바이트 그대로 복사했다.960×540·19,298B, SHA256 `e59cbb471d617733016b62ea389b5df1e7e8df53e76ff249eee970572b184841`다. 원본 출처 커밋7bb7883의 cover.png를 확인했고 ADR-026에 연결했다. 새 이미지 생성·원본 변경은 하지 않았다. 화면에서는192×96px 장식이며1100px 이하에서 숨긴다. 빈 alt·aria-hidden·pointer-events:none을 적용했다.

소개 제목과 주요 버튼에 기존 청록색·작은 그림자를 적용했다. 데모 버튼의 핸들러·문구, 통계·공개JSON·요청서 내용은 바꾸지 않았다. 웹26 tests·typecheck·정적 build가 통과했고 `git diff --check`도 통과했다. 최초 build는 node_modules 심볼릭 링크가 Turbopack root 밖이라는 이유로 실패했다. 링크를 제거하고 승인된 기존 의존성을 작업트리로 복사한 뒤 build가 통과했다. build의 prebuild hook은 기존26 tests를 자동 실행했다. 의존성·lockfile·Next 설정을 변경하지 않았다.

구현자 외 label_failure_review가 diff·26 tests·typecheck·이미지·접근성·모바일 숨김을 독립 확인해 차단 사항이 없다고 보고했다. 브라우저 시각 검수용 정적 서버 `http://127.0.0.1:8797/`를 총괄에게 전달했다. 이 세션 작성 시 실제 브라우저·공개 배포 검수는 총괄이 진행 중이며 구현자는 브라우저를 조작하지 않았다. API·DB·개인정보·원본자료 접근·PDF 재생성은 하지 않았다.

## 문제와 해결
| 문제 | 원인 | 해결 | 누가 |
|---|---|---|---|
| 소개 화면과 발표 시각 언어의 차이 | 웹에 작은 차량 이미지와 제목 강조가 없음 | 기존 축소 이미지와 제한된 청록 강조만 적용 | Codex |
| 최초 정적 build 실패 | 외부 node_modules 심볼릭 링크를 Turbopack이 거부 | 기존 의존성을 작업트리에 복사한 뒤 build 통과 | Codex |

## 사람이 검토하며 고친 것
- 사용자가 두 시각 변경만 승인했다. 기존 경보·근거·요청서 흐름은 유지한다.

## 다음 세션으로 넘길 것
- 독립 검수·병합·실제 배포 확인은 총괄이 담당한다.
