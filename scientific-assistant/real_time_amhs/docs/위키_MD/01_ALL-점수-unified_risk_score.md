---
title: ALL 점수 unified_risk_score 계산 방법
type: concept
domain: 관제
tags: [unified_risk_score, ALL, 전체점수, 융합, layer1_total, flow_score, 흐름, 위험도등급]
summary: 8영역 area_score 합에 흐름·SLA·소터·MAXCAPA 가산을 더해 min(500) 로 자른다. SLA·소터·MAXCAPA 는 두 번 세므로 FAB 합과 안 맞는다.
sources: []
author: 
updated: 
---

## 계산

```
layer1_total = Σ area_score            (8영역 전부)
flow_score   = 흐름 노드마다  심각 +30 / 위험 +15 / 주의 +5
sla_score    = SLA 켜진 영역 수 × 5
sorter_score = 소터 켜진 영역 수 × 3
mc_score     = Σ (영역별 MAXCAPA 바뀐 컬럼 수 × 10)

unified_risk_score = min(500, 위 다섯의 합)
```

> ★**SLA·소터·MAXCAPA 는 두 번 센다.** area_score 안에서 한 번(그 영역의 문제로), 융합에서 또 한 번(전체로 번질 신호로). 일부러 그렇게 둔 것이라, **ALL 점수를 FAB 점수 합으로 되계산하면 맞지 않는다.**

## 흐름 룰

노드마다 **지금 값 ÷ 최근 30분 평균** 배수를 본다. 절대값이 아니라 평소 대비라, 노드마다 크기가 달라도 같은 자로 잰다.

| 배수 | 등급 | 가산 |
|---|---|---|
| ≥ 3.0× | 심각 | +30 |
| ≥ 2.0× | 위험 | +15 |
| ≥ 1.5× | 주의 | +5 |

### 흐름 노드 10개

| 노드 | 영역 | 컬럼 |
|---|---|---|
| M14_CNV_TO_HUB | M14 | `M14.QUE.CNV.M14ATOM16ACURRNETQCNT` |
| M14_TO_HUB_JOB | M14 | `M14.QUE.ALL.3F_TO_HUB_JOB` |
| M14B_7F_TO_HUB | M14B | `M14B.QUE.ALL.7F_TO_HUB_JOB` |
| M14B_LFT_4ABLD_SUM | M14B | `M14B.LFT.4ABLD_ALL.TOTAL_CURRENTQCNT_SUM` |
| M14B_LFT_4ABLD_TO_HUB_SUM | M14B | `M14B.LFT.4ABLD_ALL.7F_TO_4F_CURRENTQCNT_SUM` |
| M16A_6F_TO_HUB | M16A | `M16A.QUE.ALL.6F_TO_HUB_JOB` |
| M16A_2F_TO_HUB | M16A | `M16A.QUE.ALL.2F_TO_HUB_JOB` |
| M16B_10F_TO_HUB | M16B | `M16B.QUE.ALL.10F_TO_HUB_JOB` |
| HUB_OHT_QCNT | M16HUB | `M16HUB.QUE.OHT.CURRENTOHTQCNT` |
| M14_TO_M16 | M16HUB | `M16HUB.QUE.M14TOM16.MESCURRENTQCNT` |

## 예측기 자체 등급 (관제 등급과 다르다)

| 점수 | 등급 |
|---|---|
| 250 이상 | 매우위험 |
| 150 ~ 249 | 위험 |
| 80 ~ 149 | 주의 |
| 65 ~ 79 | 경계 |
| 30 ~ 64 | 관심 |
| 0 ~ 29 | 정상 |

> 이름이 같아도 관제 등급과 **다른 값**이다. 예측기는 0~500 자, 관제는 0~100 자다.
