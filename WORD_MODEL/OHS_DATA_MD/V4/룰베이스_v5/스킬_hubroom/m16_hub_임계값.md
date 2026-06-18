---
name: m16_hub_임계값
description: hubroom_predictor.py 룰베이스의 임계값(thresholds.json) 전체 목록·의미·조정 방법 스킬. 어느 임계가 무슨 룰에 쓰이는지, 값을 어떻게 바꾸는지, 영향이 무엇인지 묻거나 튜닝을 도울 때 사용. "임계값", "thresholds", "임계 조정", "튜닝" 요청 시.
---

# m16_hub 임계값 — thresholds.json 가이드 (v6 / 배포 V2)

> 코드의 모든 임계는 `thresholds.json` 으로 덮어쓴다(없으면 코드 기본값). 수정 후 predictor 재시작 필요.

## 1. 임계 전체 목록 (코드 기본값)

### R-A (반송시간, 분) — 영역별
| 영역 | 임계 | 컬럼 |
|---|---|---|
| M16HUB | 9.0 | AVGTOTALTIME1MIN |
| M14 | 3.3 | AVGLOADTIME1MIN |
| M14B | 5.0 | AVGTOTALTIME1MIN |
| M16A | 3.2 | AVGLOADTIME1MIN |
| M16B | 3.5 | AVGLOADTIME1MIN |
| M16_PKT | 7.5 | AVGTOTALTIME1MIN |
| M16_WT | 2.8 | AVGTOTALTIME1MIN |

- `TH_RA_SUSTAINED_RATIO`=0.67, `TH_RA_SUSTAINED_COUNT`=3 (R-A 지속 판정: 최근 5분 중 임계×0.67 초과가 3회↑)

### R-B (30분 큐 누적, 건) — 영역별
| 영역 | 30분 임계 | 10분 급증 임계(자동) |
|---|---|---|
| M16HUB | 100 | 30 |
| M14 | 80 | 24 |
| M14B | 150 | 45 |
| M16A | 80 | 24 |
| M16B | 30 | 10 |
| M16 | 20 | 10 |

- `TH_RB_10`(10분 급증) = **30분값의 30%** 자동 산출 (최소 10). json 에 명시하면 그 값 우선.

### R-C (리프터 역증가)
| 키 | 기본값 | 뜻 |
|---|---|---|
| `TH_RC_REVERSE` | 2 | 역증가 리프터 N대 이상 |

### R-D (저장/OHT) + 신규(MLUD/CNV)
| 키 | 기본값 | 뜻 |
|---|---|---|
| `TH_RD_FABSTORAGE` | 25.0 | FAB 저장 비율 % |
| `TH_RD_HUB_STB_UTIL` | 99.0 | STB 저장 % |
| `TH_RD_OHT_UTIL` | 95.0 | OHT 가동률 % |
| `TH_MLUD_JOB` | 50 | MLUD 잡 적체(개) |
| `TH_MLUD_MANUAL` | 30 | 수동 이동 큐(개) |
| `TH_CNV_FULL_RATIO` | 0.85 | CNV 충만도(85%) |

### SLA (4분초과 비율, %) — 영역별
| 영역 | 임계 |
|---|---|
| M16HUB | 5.0 |
| M14 | 25.0 |
| M16A | 13.0 |
| M16B | 18.0 |

### Sorter (대기 LOT)
| 영역 | 임계 |
|---|---|
| M14 | 100 |
| M14B | 75 |
| M16A | 180 |
| M16B | 90 |
| M16HUB | 30 |

- `TH_SORTER_TRANSFER_FAIL` = 1 (전송 실패 1건↑ → 발동)

### 흐름(flow) 배수
| 키 | 기본값 | 등급 |
|---|---|---|
| `TH_FLOW_X1_5` | 1.5 | 주의(+5) |
| `TH_FLOW_X2_0` | 2.0 | 위험(+15) |
| `TH_FLOW_X3_0` | 3.0 | 심각(+30) |

### 사건/윈도우
| 키 | 기본값 | 뜻 |
|---|---|---|
| `WINDOW_MIN` | 90 | 관측 윈도우(분) |
| `INCIDENT_END_GAP_MIN` | 60 | ★ 사건 진동 흡수 — 60분 안 재발생은 같은 사건 |
| `PREDICT_LOOKBACK_MIN` | 60 | 예측 시각 소급 범위(분) — lead_min 상한 |

## 2. thresholds.json 구조 (예시 — 값은 운영자 조정본)
```json
{
  "TH_RA": {"M16HUB": 9.0, "M14": 3.3},
  "TH_RB_30": {"M16HUB": 100},
  "TH_RC_REVERSE": 4,
  "TH_RD_FABSTORAGE": 25.75, "TH_RD_HUB_STB_UTIL": 99.3,
  "TH_SLA_RATIO": {"M16HUB": 5.0},
  "TH_SORTER_WAIT": {"M14": 148},
  "INCIDENT_END_GAP_MIN": 60,
  "_comment": "메모 — 언더스코어 키는 무시됨"
}
```
> 위 `TH_RC_REVERSE: 4`, `TH_SORTER_WAIT M14:148` 등은 **조정 예시**다 (코드 기본값은 2, 100). 실제 운영 thresholds.json 값을 따른다.

## 3. 조정 영향 (튜닝 가이드)
| 임계 ↓ 낮추면 | 임계 ↑ 높이면 |
|---|---|
| 더 민감 → 재현율↑, **오탐(FP)↑** | 덜 민감 → 정밀도↑, **놓침(Miss)↑** |

- **`INCIDENT_END_GAP_MIN`** 이 성능에 가장 큼 — 늘리면 별개 사건 과합침, 줄이면 진동으로 사건이 쪼개져 FP 폭증.
- dict 임계(TH_RA 등)는 **영역별 부분 수정 가능** (빠진 영역은 코드 기본값 유지).

## 4. 주의
- json 깨져도 운영 안 멈춤(코드 기본값 사용).
- `_` 로 시작하는 키는 메모로 무시됨.
- 수정 후 **predictor 재시작** 해야 반영.
