---
name: m16_hub_결과해석
description: hubroom_predictor.py 가 출력한 발동이벤트.csv / 사건단위.csv 의 컬럼·등급·장애유형·점수를 해석하는 가이드 스킬. CSV 결과를 어떻게 읽는지, 무슨 컬럼이 무슨 뜻인지, 사건이 진짜인지 판단하는 법을 묻거나 결과 분석을 도울 때 사용. "결과 해석", "이 컬럼 뭐야", "사건단위 읽는 법", "이게 진짜 장애야" 요청 시.
---

# m16_hub 결과해석 — 발동이벤트/사건단위 읽는 법 (초안)

> 배경 개념은 `m16_hub_카파시` 참조. 데이터 한 줄 정밀 분석은 `한줄분석.py` 또는 m16_br 스킬 사용.

## 1. 두 출력 파일 차이
| | 발동이벤트.csv | 사건단위.csv |
|---|---|---|
| 단위 | 매분 1행 | 사건당 1행 |
| 기록 | 즉시 | 사건 종료+60분 후, **점수 100+ 만** |
| 용도 | 실시간 모니터링 | 사후 사건 요약 |

## 2. 사건단위.csv 핵심 컬럼
| 컬럼 | 뜻 |
|---|---|
| `predict_time` | 룰베이스가 사건을 **처음 시작**한 시각 (S3 진입) |
| `start_time` | S3 확정 시각 |
| `end_time` | 종료 |
| `duration_min` | 지속 시간 |
| `refire_count` | 재발생 횟수 (진동) |
| `max_risk_score` | 사건 **최고 점수** (※ predict_time 과 다른 분일 수 있음) |
| `max_risk_level` | 최고 등급 (관심~발동) |
| `predicted_fault_type` | 장애유형 라벨 (HUB-FAB정체 등) |
| `hot_area` | 가장 강한 영역 |
| `affected_areas` | 영향 영역들 |
| `triggered_rules` | 발동 룰 (예: M16HUB:RA+RD; M14:SLA) |
| `reason` / `relation` | 사람이 읽는 사유 + 실측값/임계 |

> ⚠️ **predict_time ≠ max_risk_score 시각**. "16:57 시작, 최고점 162" 라면 162는 16:57 이 아니라 사건 중 다른 분에 찍힌 것. 최고점 시각은 발동이벤트.csv 에서 unified_risk_score 최댓값 행 확인.

## 3. 발동이벤트.csv 핵심 컬럼 (135 중)
| 컬럼 | 뜻 |
|---|---|
| `datetime` / `time` | 시각 |
| `stage` / `stage_name` | 단계 (1조기경보/2주의보/3확정) |
| `unified_risk_score` | 그 분 종합 점수 |
| `unified_risk_level` | 그 분 등급 |
| `incident_state` | IDLE / IN_INCIDENT |
| `continuity_min` | 사건 시작부터 N분째 |
| `refire_count` | 재발 횟수 |
| `predicted_fault_type` | 장애유형 |
| `hot_area` | 최강 영역 |
| `M16HUB_score`~ | 영역별 점수 |
| `layer1_total/flow_score/sla_score_total/...` | 점수 구성 (이 5개 합 = unified_risk_score) |
| `{영역}_pts_{룰}` | 영역×룰별 기여 점수 (45컬럼) |
| `reason` | 사람이 읽는 사유 |

## 4. 점수 검증 공식
```
unified_risk_score = layer1_total + flow_score + sla_score_total + sorter_score_total + mc_score_total
```
(발동이벤트 한 줄에서는 정확히 더해짐. 사건단위 max_* 는 시각 제각각이라 안 더해짐.)

## 5. 등급 → 대응
| 등급 | 점수 | 대응 |
|---|---|---|
| 정상 | <100 | 알람 X (세부 룰 🔴여도 통합 미달이면 대응 불요) |
| 관심 | 100~119 | 참고 (정밀도 41%) |
| 주의 | 120~129 | 모니터링 |
| 경계 | 130~159 | 원인 확인 |
| 위험 | 160~219 | 즉시 조치 (정밀도 75%) |
| 발동 | 220+ | 즉시 개입 |

## 6. "이게 진짜 장애인가" 판단 팁
- **위험(160+)** → 4번 중 3번 진짜 (정밀도 75%). 신뢰.
- **STB/FAB 100% + 반송시간 임계초과** → 점수 낮아도 실제 정체 신호.
- **continuity_min 큼 + 점수 낮음** → 작은 정체 지속, 저절로 풀릴 수 있음.
- **점수 100 미만 FP 여도** 메신저에 없는 "조용한 정체"일 수 있음 (메신저=불완전 정답지).

## 7. 장애유형 라벨 읽기
`{영역}-{증상}` 형식: HUB-FAB정체 / HUB-STB정체 / HUB-리프터역증가 / M14-Sorter대기 / M16B-SLA초과 / 광역정체(4영역+).

## 8. 추천 분석 도구
- **한 줄 정밀 분석**: `한줄분석.py` (점수 분해+룰별+실측값+판정)
- **파일 최고점**: `발동이벤트_점수분석.py`
- **reason → 원본 컬럼**: `reason_컬럼찾기.py`
