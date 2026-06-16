---
name: m16_br_한줄분석
description: M16A HUBROOM 룰베이스 발동이벤트.csv 의 데이터 한 줄(135컬럼 또는 구버전 131컬럼)을 사용자가 붙여넣으면, 점수 구성·영역별 룰 점수·발동 룰별 원본 컬럼/실측값/임계/판정을 분석해 출력한다. "이 행 점수 왜 이래", "한줄 분석", "발동이벤트 분석" 요청 시 사용.
---

# m16_br 한줄분석 (LLM 버전)

발동이벤트.csv 의 **데이터 한 줄**을 받아 `한줄분석.py` 와 **동일한 출력**을 낸다. 파이썬 실행 없이 직접 분석한다.

## 입력
사용자가 발동이벤트.csv 의 데이터 행 1줄을 붙여넣음 (헤더 제외). CSV 파싱(따옴표 안 콤마 보존) 후 아래 컬럼순서로 매핑.

## 컬럼 순서 (신버전 135컬럼)
```
file, datetime, date, time, stage, stage_name, prev_stage, transition,
incident_state, continuity_min, refire_count, predicted_fault_type,
unified_risk_score, unified_risk_level, hot_area, hot_score,
affected_areas, propagation_chain, flow_signals, maxcapa_signals,
M16HUB_score, M14_score, M14B_score, M16A_score, M16B_score, M16_score, M16_PKT_score, M16_WT_score,
M16HUB_signals, M14_signals, M14B_signals, M16A_signals, M16B_signals,
M16HUB_ra, M14_ra, M14B_ra, M16A_ra, M16B_ra,
M16HUB_rb_diff30, M14_rb_diff30, M14B_rb_diff30, M16A_rb_diff30, M16B_rb_diff30,
M16HUB_rd_fab, M16HUB_stb_util, M16HUB_rev_count, M16HUB_rev_lids,
sla_M14, sla_M14B, sla_M16A, sla_M16B, sla_M16HUB,
sorter_M14, sorter_M14B, sorter_M16A, sorter_M16B, sorter_M16HUB,
reason,
(영역5 × 룰9 = 45 pts 컬럼: M16HUB_pts_RA, M16HUB_pts_RA_sus, M16HUB_pts_RB, M16HUB_pts_RB_fast,
 M16HUB_pts_RC, M16HUB_pts_RD, M16HUB_pts_SLA, M16HUB_pts_SORT, M16HUB_pts_MAXCAPA, 그 다음 M14_*, M14B_*, M16A_*, M16B_* 동일 순서),
layer1_total, flow_score, sla_score_total, sorter_score_total, mc_score_total,
(이후 진단키 컬럼들 — 분석에 불필요)
```
**구버전(131컬럼)**: 위에서 `incident_state, continuity_min, refire_count, predicted_fault_type` 4개가 빠짐. 컬럼 수 세서 131이면 이 4개 없는 것으로 매핑.

## 점수 산식
```
unified_risk_score = layer1_total + flow_score + sla_score_total + sorter_score_total + mc_score_total
```

## 등급 / 판정 (점수 기준)
| 점수 | 등급 | 판정 마크 |
|---|---|---|
| 0~99 | 정상 | 🟢 정상 — 점수 N (알람 X) |
| 100~119 | 관심 | 🔵 관심 — 점수 N |
| 120~129 | 주의 | 🟡 주의 — 점수 N |
| 130~159 | 경계 | 🟠 경계 — 점수 N |
| 160~219 | 위험 | 🔴 위험 — 점수 N |
| 220+ | 발동 | ⚫ 발동 — 점수 N |
지속(continuity_min)≥1 이면 판정 뒤에 ` / N분째 지속` 붙임.

## 룰 → 원본 컬럼 + 임계
| 룰(pts컬럼) | 원본 컬럼 | 실측 컬럼 | 임계 |
|---|---|---|---|
| RA, RA_sus | RA_COL[영역] | {영역}_ra | M16HUB 9.0 / M14 3.3 / M14B 5.0 / M16A 3.2 / M16B 3.5 |
| RB, RB_fast | RB_COL[영역] | {영역}_rb_diff30 | M16HUB 100 / M14 80 / M14B 150 / M16A 84 / M16B 32 |
| RC (M16HUB만) | 리프터 역증가 | M16HUB_rev_count | 4 |
| RD (M16HUB) | FABSTORAGERATIO / STB.3F_STORAGE_UTIL | M16HUB_rd_fab / M16HUB_stb_util | FAB 25.75 / STB 99.3 |
| RD (그외) | {영역}.QUE.OHT.OHTUTIL | {영역}_rd_oht | 95.0 |
| SLA | SLA_COL[영역] | sla_{영역} | M16HUB 5.0 / M14 25.45 / M16A 14.05 / M16B 22.05 |
| SORT | SORTER_COL[영역] | sorter_{영역} | M14 148 / M14B 109 / M16A 180 / M16B 90 / M16HUB 30 |
| MAXCAPA | {영역}.QUE.CNV.3F_CNV_MAXCAPA | — | 운영자 조치 |

### 원본 컬럼명
- RA_COL: M16HUB=`M16HUB.QUE.TIME.AVGTOTALTIME1MIN`, M14=`M14.QUE.LOAD.AVGLOADTIME1MIN`, M14B=`M14B.QUE.TIME.AVGTOTALTIME1MIN`, M16A=`M16A.QUE.LOAD.AVGLOADTIME1MIN`, M16B=`M16B.QUE.LOAD.AVGLOADTIME1MIN`
- RB_COL: M16HUB=`M16HUB.QUE.ALL.CURRENTQCNT`, M14=`M14.QUE.ALL.HUB_TO_M14_JOB`, M14B=`M14B.QUE.ALL.HUB_TO_M14B_JOB`, M16A=`M16A.QUE.ALL.6F_TO_HUB_JOB`, M16B=`M16B.QUE.ALL.10F_TO_HUB_JOB`
- SLA_COL: `{영역}.QUE.ALL.TRANSPORT4MINOVERRATIO`
- SORTER_COL: `{영역}.SORTER.ABN.SORTERWAITCOUNTOVER`
- OHT_COL: `{영역}.QUE.OHT.OHTUTIL`

### 판정 마크 규칙
- 실측 ≥ 임계 → `🔴 초과 (N.N배)` (N.N = 실측/임계)
- 실측 < 임계 → `🟢 정상 (임계의 N%)` (N = 실측/임계×100)
- FAB/STB 는 초과면 `🔴 초과`, 아니면 `🟢 정상`
- MAXCAPA 는 `🟡 운영자조치`

## 출력 형식 (정확히 이대로)
```
{판정줄}
==========================================================================
  {datetime} | 점수 {unified_risk_score} [{unified_risk_level}] | hot={hot_area} | 유형 {predicted_fault_type}
  사건상태 {incident_state} | 지속 {continuity_min}분 | 재발 {refire_count}회 | 영향영역 {affected_areas}
==========================================================================

  [점수 구성] {합} = 영역합 {layer1_total} + 흐름 {flow_score} + SLA {sla_score_total} + Sorter {sorter_score_total} + MAXCAPA {mc_score_total}

  [영역 × 룰 점수]  영역           RA  RA_sus      RB RB_fast      RC      RD     SLA    SORT MAXCAPA    합
  ----------------------------------------------------------------------------------------
  (pts 합이 0 아닌 영역만, 0인 칸은 · 으로)

  [발동 룰 → 원본 컬럼 / 실측값 / 임계]   ▶▶  {판정줄}

   ▶ {영역}
      · {룰한글}  {원본컬럼} = {실측}{단위} (임계 {임계})  {판정마크}
   (발동(pts>0)한 룰만)

   ▶ 흐름(flow): {flow_signals}   (있을 때만)

  ※ reason 원문: {reason 앞 120자}...
```
룰 한글명: RA/RA_sus=반송지연, RB/RB_fast=큐누적, RC=리프터역증가, RD(M16HUB)=FAB저장/STB저장, RD(그외)=OHT정체, SLA=SLA초과, SORT=Sorter, MAXCAPA=MAXCAPA.

## 주의
- 구버전/신버전 컬럼수 자동 판별 (131 vs 135).
- 헤더 줄(`file,datetime,...`)이 들어오면 "데이터 행만 넣어달라" 안내.
- 값이 비었거나 0이면 해당 룰 줄 생략.
