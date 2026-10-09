# S10 — Cloudflare Pages 정적 배포 준비

- 시각: 2026-10-09 (Asia/Seoul), 사용자 Cloudflare 선택 / 로컬 준비 검증 완료 / 계정 연결·공개 배포 진행 예정
- 관련: SPEC Step 9 배포, ADR-006

## 목표
사용자가 선택한 Cloudflare Pages에서 GitHub `main` 변경을 자동 빌드·배포하도록 준비한다. 검토한 JSON과 Next.js 정적 출력만 공개한다.

## 완료 기준
- [x] Cloudflare 프로젝트 root·빌드 명령·출력 경로·Node 버전 확정
- [x] 테스트·타입 검사·루트 경로 정적 빌드 통과
- [x] HTML·JavaScript·CSS·데이터 HTTP 200 및 JSON 동일성 확인
- [x] 기본 헤더 설정과 로컬 시연 파일 보존
- [ ] Cloudflare 계정 연결·GitHub 연동·실제 공개 빌드·공개 URL 검증

## Codex에 맡긴 일
Astra가 Cloudflare 계정 연결과 실제 배포를 맡고 웹 담당은 선택된 호스팅에 맞춰 정적 빌드·설정·파일 검증을 준비한다. 웹 담당은 외부 계정에 쓰기 작업을 하지 않았다.

## 결과
로컬 Node 26.3.0·npm 11.16.0에서 `npm ci`를 확인했고, Cloudflare 전환 후 `NEXT_PUBLIC_BASE_PATH='' npm run build`와 별도 `npm run typecheck`가 통과했다. `prebuild`에 기존 `npm test`를 연결하여 Cloudflare의 `npm run build`에서도 **19개 테스트**를 먼저 실행한다. Next.js build 자체 TypeScript 검사도 통과했다. Cloudflare Linux 빌드는 아직 실행하지 않았으므로 원격 빌드 성공으로 기록하지 않는다.

정적 미리보기 `http://127.0.0.1:3103/`에서 HTML 1개·JavaScript 7개·CSS 2개·데이터 JSON 3개, 총 **13개 경로 HTTP 200**을 확인했다. 출력은 **641개 파일·17,580,256 bytes**, 가장 큰 파일은 **2,089,612 bytes**다. 공개 JSON **42개**는 계약 식별자와 원본 `web/public/data` 대비 SHA256 동일성을 확인했다. 심볼릭 링크·`.env`·ZIP·DuckDB·JSONL 파일이 출력에 없는 것을 확인했다. 전체 브라우저 상호작용과 모바일 검수는 Astra가 별도로 수행한다.

앞서 GitHub Pages 비교용 `/EarlySignal` 빌드는 로컬에서만 검사했고, 실제 GitHub Pages 활성화·게시·원격 실행은 하지 않았다. 사용자의 Cloudflare 선택 후 미사용 `.github/workflows/pages.yml`과 Next.js basePath 설정을 제거했다. Cloudflare GitHub integration이 빌드를 수행하므로 GitHub Actions 배포 토큰을 별도로 준비하지 않는다.

Cloudflare 연결 설정:

| 설정 | 값 |
|---|---|
| GitHub repository | `SangJun-Pyo/EarlySignal` |
| Production branch | `main` |
| Framework preset | Next.js (Static HTML Export) |
| Root directory | `web` |
| Build command | `npm run build` |
| Build output directory | `out` |
| Node version | `26.3.0` (`web/.node-version`, 필요하면 `NODE_VERSION=26.3.0`) |
| `NEXT_PUBLIC_BASE_PATH` | 설정하지 않음 / 빈 값 |
| OpenAI API key | 정적 배포에는 사용하지 않음 |

설치된 Next.js 16.4.0의 Node 요구사항은 `>=20.9.0`, TypeScript 7.0.2는 `>=16.20.0`이며 로컬 Node 26.3.0이 충족한다. Cloudflare build image는 `.node-version` 또는 `NODE_VERSION`으로 버전을 지정할 수 있고, `package.json`의 engines에서 자동 감지하지 않는다는 공식 안내를 확인했다. 이를 위해 `web/.node-version`을 추가했다.

`web/public/_headers`는 `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `/data/*`의 재검증 캐시 정책만 설정한다. `_headers`가 `out`에 동일하게 복사된 것을 검사했다. 새 CSP를 추가하지 않았으며 실제 헤더 적용 여부는 Cloudflare 공개 URL에서 후속 확인해야 한다. 로컬 Python 서버는 Cloudflare `_headers`를 적용하지 않는다.

공식 근거(2026-10-09 확인): [Next.js static export](https://developers.cloudflare.com/pages/framework-guides/nextjs/deploy-a-static-nextjs-site/), [build image](https://developers.cloudflare.com/pages/configuration/build-image/), [정적 응답 헤더](https://developers.cloudflare.com/pages/configuration/headers/).

현재 Cloudflare용 루트 빌드는 `web/out`과 `data/private/cloudflare-preview`에 있다. 이전 `data/private/preview-root`와 GitHub Pages 비교용 `data/private/pages-preview/EarlySignal`도 로컬 기록으로 보존했다. `data/private` 경로는 gitignore 대상이다. 공개 대상은 빌드된 웹 자산과 `web/public/data`의 공개용 JSON이며, `.env`·원본 ZIP·작업 DB·라벨 캐시·발표 초안은 업로드하지 않는다.

로컬 서버 재실행(저장소 루트):

```sh
.venv/bin/python -m http.server 3103 --bind 127.0.0.1 --directory data/private/cloudflare-preview
```

현재 `web/out`의 HTML에는 `/EarlySignal/` 경로가 없다. 데이터 fetch는 `./data/*.json` 상대 경로를 유지하여 Pages 프로젝트 루트에서 읽는다.

## 문제와 해결
| 문제 | 원인 | 해결 | 누가 |
|---|---|---|---|
| 이전 호스팅 경로 설정이 남으면 자산을 찾지 못함 | GitHub Pages 비교 빌드에 `/EarlySignal` 사용 | 미사용 workflow·basePath 제거 후 루트 경로 재검증 | Codex |
| Cloudflare 기본 Node 버전은 로컬과 다를 수 있음 | 빌드 이미지의 기본값 변경 | 검증한 26.3.0을 `.node-version`으로 고정 | Codex |

## 사람이 검토하며 고친 것
- 사용자가 Cloudflare Pages 배포를 명시적으로 선택했다.

## 다음 세션으로 넘길 것
- Astra의 Cloudflare 계정 연결·GitHub 연동·최초 배포
- 공개 URL의 데이터·정적 자산·기본 헤더·요청서 저장 흐름 검증
