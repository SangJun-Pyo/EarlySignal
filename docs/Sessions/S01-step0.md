# S01 — Step 0 저장소 뼈대

- 시각: 2026-10-09 완료
- 관련: SPEC Step 0, ADR-001~005

## 목표
설정 가능한 경로와 재현 가능한 Python 패키지·CLI 실행 틀을 만든다.

## 완료 기준
- [x] Python 3.10+ 가상환경 생성, 의존성 설치
- [x] `python -m es.cli --help` 정상 종료

## Codex에 맡긴 일
부모 Astra가 실행 순서·통합을 맡고 파이프라인 구현 에이전트가 Step 0~6을 수행한다. 유료 API 호출은 하지 않는다.

## 결과
Python 3.12.11 가상환경 생성, pip editable 설치 완료. `python -m es.cli --help` 정상 종료.

## 문제와 해결
시스템 Python 3.9 대신 번들 Python 가상환경 사용. 실행 경로는 CLI와 Config에 둔다.

## 사람이 검토하며 고친 것
현재 없음.

## 다음 세션으로 넘길 것
Step 1 ZIP 적재.
