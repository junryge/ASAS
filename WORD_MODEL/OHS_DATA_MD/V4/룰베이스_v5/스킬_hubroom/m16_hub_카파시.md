---
name: m16_hub_카파시
description: hubroom_predictor.py (M16A HUBROOM 룰베이스 v6) 가 무엇을 왜 어떻게 하는지 설명하는 배경/개념(컨텍스트) 스킬. 시스템 구조·데이터 흐름·8영역 9룰·S1S2S3 단계·점수 산식·출력 파일을 묻거나, 다른 hubroom 스킬의 배경 지식이 필요할 때 사용. "어떻게 동작", "구조 설명", "왜 이렇게" 요청 시.
---

# m16_hub 카파시 — hubroom_predictor.py 개념/배경 (초안)

> 이 스킬은 룰베이스가 **무엇을 왜 어떻게** 하는지 설명한다. 다른 hubroom 스킬(일반/임계값/결과해석)의 공통 배경 지식.

## 1. 목적
반도체 FAB AMHS(자동 물류)의 **반송 정체를 사전 예측**. 8개 영역 센서 데이터를 매분 룰로 평가해 위험 점수·등급을 산출, 운영자 인지·시스템 알람보다 먼저 신호.

## 2. 데이터 흐름
```
[수집기] → predict/M16A_HUBROOM_PR.csv (매분, 약 265컬럼 raw)
              ↓ hubroom_predictor.py (매분 평가)
       ┌──────────────┴───────────────┐
  발동이벤트.csv (매분 1행, 135컬럼)   사건단위.csv (사건당 1행, 170컬럼)
  - 모든 분 스냅샷                     - 점수 100+ 사건만, 종료 후 기록
              ↓ (선택)
       Rule_LO.py → Logpresso 적재
```

## 3. 8개 영역 (Area)
| 영역 | 구역 |
|---|---|
| M16HUB | M16 허브룸 (반송 중심·저장) |
| M14 / M14B | M14 / M14B 라인 |
| M16A / M16B | M16A / M16B 라인 |
| M16 / M16_PKT / M16_WT | M16 본체 / 포켓 / 대기 |

## 4. 9개 룰 (Rule)
| 룰 | 감지 | 핵심 컬럼 |
|---|---|---|
| R-A | 반송시간 느려짐 | `QUE.TIME.AVGTOTALTIME1MIN` / `QUE.LOAD.AVGLOADTIME1MIN` |
| R-A_sus | 반송 지연 지속 | 최근 N분 중 임계초과 비율 |
| R-B | 30분 큐 누적 | `QUE.ALL.{n}F_TO_HUB_JOB` 등 |
| R-B_fast | 큐 급증(10분) | 10분 변화량 |
| R-C | 리프터 역증가 | `LFT.6ABLxxxx` (리프터 10대) |
| R-D | 저장/OHT 정체 | `FABSTORAGERATIO`, `STB.3F_STORAGE_UTIL`, `QUE.OHT.OHTUTIL` |
| SLA | 4분초과 비율 | `QUE.ALL.TRANSPORT4MINOVERRATIO` |
| Sorter | 분류기 대기 | `SORTER.ABN.SORTERWAITCOUNTOVER` |
| MAXCAPA | 운영자 CAPA 변경 | `QUE.CNV.3F_CNV_MAXCAPA` |
| (신규) MLUD / CNVFull | 수동이동 적체 / CNV 충만 | `3F_TO_3F_MLUD_JOB`, `3F_CNV_MAXCAPA` |

> 컬럼 읽는 법: `영역.분류.세부.지표`. 예) `M16HUB.QUE.ALL.CURRENTQCNT` = M16HUB 큐 전체 현재 반송 대기 수.

## 5. 3단계 경보 (Stage)
```
S1 (조기경보) = any_RA  또는  RA 지속
S2 (주의보)   = any_RB
S3 (확정)     = any_RA AND (any_RD or any_SLA or any_RC) AND (any_RB or 흐름심각)
```
- **S3 = "확정"** — 여러 룰이 동시에 충족돼야 함 → 정체가 실제 진행 중인 강한 신호.

## 6. 점수 산식
```
unified_risk_score = layer1_total + flow_score + sla_score + sorter_score + mc_score  (최대 500)
  · layer1_total : 8영역 area_score 합 (룰별 점수 누적)
  · flow_score   : 흐름 비율 정체 (1.5x=+5, 2.0x=+15, 3.0x=+30)
  · sla_score    : SLA 초과 영역당 +5
  · sorter_score : Sorter 대기 영역당 +3
  · mc_score     : MAXCAPA 변경 영역당 +10
```

## 7. v6 5단계 등급
| 점수 | 등급 | 의미 |
|---|---|---|
| 0~99 | 정상 | 알람 X (사건 기록 안 됨) |
| 100~119 | 관심 | 약한 신호 (정밀도 41%) |
| 120~129 | 주의 | 모니터링 |
| 130~159 | 경계 | 원인 확인 |
| 160~219 | 위험 | 즉시 조치 (정밀도 75%) |
| 220+ | 발동 | 즉시 개입 |

## 8. v6 핵심 개선 (왜 이렇게)
1. **사건 진동 흡수** — gap 60분. 점수 잠깐 하락 후 재상승도 같은 사건(refire++).
2. **점수 100 미만 사건 제외** — 노이즈 차단.
3. **장애유형 자동 라벨** — hot_area + 증상 → `HUB-FAB정체` 등.
4. **지속성/재발생 컬럼** — continuity_min, refire_count (점수엔 영향 X, 참고용).

## 9. 중요 주의 (해석 시)
- **predict_time(사건 시작) ≠ max_risk_score(최고점) 시각** — 사건단위 한 줄에서 두 값은 서로 다른 분일 수 있음. 최고점이 언제 찍혔나는 발동이벤트에서 확인.
- **사건단위의 max_* 컬럼들은 각자 다른 분의 최고값** → 더하면 max_risk_score 와 안 맞음.
- 룰베이스는 **시스템 전체 흐름**에 강하고 **개별 장비 고장**엔 약함.
