# ADR-006: 배포: 미리 계산한 JSON + Next.js 정적 사이트

- 상태: 채택
- 날짜: 2026-10-08 (사전 작업)

## 배경
제출물에 데모 링크가 필수이고, 하루 안에 서버·DB 배포까지 하면 실패 위험이 크다. 탐지 결과는 배치로 계산하면 된다.

## 결정
- 파이프라인이 `web/public/data/*.json`을 만들고, 웹은 이것만 읽는다(`output: "export"`).
- JSON 형식은 `docs/Contracts/data-contract-v1.md`로 고정하고 계약 테스트로 검사한다.
- 담당자 결정은 브라우저 localStorage(데모 범위).

## 결과와 트레이드오프
- 서버 없이 Vercel 등에 바로 배포 가능, 네트워크 장애 시 로컬 `npx serve`로 동일 시연
- 실시간 수집·다중 사용자 협업은 다음 단계

## 2026-10-09 사용자 호스팅 선택: Cloudflare Pages

사용자가 Cloudflare Pages를 선택했다. GitHub 저장소 연결 후 `main`의 변경을 자동 빌드·배포하는 방식으로 진행한다. 프로젝트 root는 `web`, 빌드 명령은 `npm run build`, 출력 디렉터리는 `out`이다. Next.js의 기존 `output: "export"`를 유지하며 루트 경로에 게시한다. OpenAI 키와 서버 런타임은 배포 환경에 필요하지 않다.

로컬에서 검증한 Node 26.3.0을 `web/.node-version`에 고정한다. Cloudflare 공식 build image 문서는 Node 버전을 `.node-version` 또는 `NODE_VERSION`으로 지정할 수 있다고 설명한다. `npm run build`는 기존 웹 테스트를 먼저 실행하고 Next.js 자체 타입 검사와 정적 빌드를 수행한다.

앞서 준비했던 GitHub Pages workflow는 실제 실행·활성화하지 않았으며, 호스팅 선택 후 삭제한다. 해당 비교용 `/EarlySignal` 빌드는 로컬 비공개 기록에만 남긴다. 공개 대상은 `web/out`의 정적 자산과 공개용 데이터 JSON이다. 원본 신고 ZIP·작업 DB·API 키·라벨 캐시·발표 초안은 포함하지 않는다.

기본 응답 헤더는 MIME sniffing 방지·referrer 범위·데이터 재검증만 설정한다. 새 CSP나 서버 기능을 추가하지 않는다. 계정 연결과 실제 게시·공개 URL 확인은 Astra가 담당한다.

공식 근거(2026-10-09 확인): [Next.js static export on Pages](https://developers.cloudflare.com/pages/framework-guides/nextjs/deploy-a-static-nextjs-site/), [build image와 Node 버전 설정](https://developers.cloudflare.com/pages/configuration/build-image/), [정적 응답 헤더](https://developers.cloudflare.com/pages/configuration/headers/).
