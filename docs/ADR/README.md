# ADR 목록

설계 결정 기록. 10/8 사전 조사에서 정한 결정은 '사전 작업'이고, 당일 새 결정이나 변경은 ADR-009부터 추가한다(기존 ADR을 고칠 때는 '변경 이력'을 덧붙인다).

| 번호 | 제목 |
|---|---|
| [ADR-001](ADR-001-monitoring-unit.md) | 감시 단위는 브랜드+모델(연식 통합) |
| [ADR-002](ADR-002-time-basis.md) | 시간 기준은 NHTSA 접수일(LDATE), 판단 시점 이후 정보는 쓰지 않는다 |
| [ADR-003](ADR-003-detection-rule.md) | 탐지 규칙: 직전 12개월 포아송 기준선, p<0.001 그리고 3건 이상 |
| [ADR-004](ADR-004-ai-roles.md) | AI 역할 분담: LLM=측정, 통계=판단, 사람=결정 |
| [ADR-005](ADR-005-validation-design.md) | 검증 설계: 기계적 사례 선정, dev/holdout, 대조군, 12개월 선행 창 |
| [ADR-006](ADR-006-static-delivery.md) | 배포: 미리 계산한 JSON + Next.js 정적 사이트 |
| [ADR-007](ADR-007-dashboard-encoding.md) | 대시보드 표현: 히트맵 색=평소 대비 배수, 기준일 이후는 두 개의 전망 띠, 데이터 연결 현황은 사실대로 |
| [ADR-008](ADR-008-privacy-and-sources.md) | 개인정보 제외와 출처 명시 |
| [ADR-009](ADR-009-demo-goal-investigation-request.md) | 데모 목표 = 조사 준비 끝내기, 주인공 = 조사 요청서 |

## 새 ADR 양식
```
# ADR-0NN: 제목
- 상태: 제안/채택/대체(ADR-0XX)
- 날짜:
## 배경
## 결정
## 결과와 트레이드오프
```
