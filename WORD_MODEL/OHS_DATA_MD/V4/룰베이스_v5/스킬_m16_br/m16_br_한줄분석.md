---
name: m16_br_한줄분석
description: M16A HUBROOM 룰베이스 발동이벤트.csv 의 데이터 한 줄(135컬럼/131컬럼)을 사용자가 붙여넣으면 한줄분석.py 와 100% 동일한 평문 출력을 낸다. "한줄 분석", "이 행 분석", "발동이벤트 한 줄" 등 요청 시. 입력은 CSV 한 줄.
---

# m16_br 한줄분석 — 한줄분석.py 동일 출력 + 최종결론

## 출력 구조 (2부분)
**[1] 분석 블록** — 아래 "출력 템플릿" 그대로 (코드블록 안 monospace 평문, 한 글자도 변형 금지).
**[2] 최종 결론 / 조치 권고** — 분석 블록 *아래* 에 자연어로 추가 (허용).

⛔ **규칙**
1. **[1] 분석 블록은 템플릿 그대로**. 그 안에서 표/볼드/요약으로 바꾸지 말 것. 숫자·컬럼명·판정마크 정확히.
2. [1] 안의 이모지는 명시된 것만 (🟢🔵🟡🟠🔴⚫).
3. [2] 최종결론은 **분석 블록 끝난 뒤** 짧게. 분석 블록 안에 섞지 말 것.
4. 헤더 줄(`file,datetime,...`)이 들어오면 "데이터 행만 넣어주세요." 라고만 답하고 종료.

---

## 입력 처리

CSV 한 줄 파싱 (따옴표 안 콤마 보존). 컬럼 수가 **135 → 신버전**, **131 → 구버전**.

### 신버전 (135컬럼) 순서
```
file, datetime, date, time,
stage, stage_name, prev_stage, transition,
incident_state, continuity_min, refire_count, predicted_fault_type,
unified_risk_score, unified_risk_level, hot_area, hot_score,
affected_areas, propagation_chain, flow_signals, maxcapa_signals,
M16HUB_score, M14_score, M14B_score, M16A_score, M16B_score,
M16_score, M16_PKT_score, M16_WT_score,
M16HUB_signals, M14_signals, M14B_signals, M16A_signals, M16B_signals,
M16HUB_ra, M14_ra, M14B_ra, M16A_ra, M16B_ra,
M16HUB_rb_diff30, M14_rb_diff30, M14B_rb_diff30, M16A_rb_diff30, M16B_rb_diff30,
M16HUB_rd_fab, M16HUB_stb_util, M16HUB_rev_count, M16HUB_rev_lids,
sla_M14, sla_M14B, sla_M16A, sla_M16B, sla_M16HUB,
sorter_M14, sorter_M14B, sorter_M16A, sorter_M16B, sorter_M16HUB,
reason,
M16HUB_pts_RA, M16HUB_pts_RA_sus, M16HUB_pts_RB, M16HUB_pts_RB_fast,
M16HUB_pts_RC, M16HUB_pts_RD, M16HUB_pts_SLA, M16HUB_pts_SORT, M16HUB_pts_MAXCAPA,
M14_pts_RA, M14_pts_RA_sus, M14_pts_RB, M14_pts_RB_fast,
M14_pts_RC, M14_pts_RD, M14_pts_SLA, M14_pts_SORT, M14_pts_MAXCAPA,
M14B_pts_RA, M14B_pts_RA_sus, M14B_pts_RB, M14B_pts_RB_fast,
M14B_pts_RC, M14B_pts_RD, M14B_pts_SLA, M14B_pts_SORT, M14B_pts_MAXCAPA,
M16A_pts_RA, M16A_pts_RA_sus, M16A_pts_RB, M16A_pts_RB_fast,
M16A_pts_RC, M16A_pts_RD, M16A_pts_SLA, M16A_pts_SORT, M16A_pts_MAXCAPA,
M16B_pts_RA, M16B_pts_RA_sus, M16B_pts_RB, M16B_pts_RB_fast,
M16B_pts_RC, M16B_pts_RD, M16B_pts_SLA, M16B_pts_SORT, M16B_pts_MAXCAPA,
layer1_total, flow_score, sla_score_total, sorter_score_total, mc_score_total,
(이후 진단 컬럼 — 분석에 불필요)
```
구버전(131): 위에서 `incident_state, continuity_min, refire_count, predicted_fault_type` 4개 빠짐.

## 임계 (v6)
- TH_RA: M16HUB 9.0 / M14 3.3 / M14B 5.0 / M16A 3.2 / M16B 3.5
- TH_RB: M16HUB 100 / M14 80 / M14B 150 / M16A 84 / M16B 32
- TH_SLA: M16HUB 5.0 / M14 25.45 / M16A 14.05 / M16B 22.05
- TH_SORTER: M14 148 / M14B 109 / M16A 180 / M16B 90 / M16HUB 30
- TH_FAB 25.75 / TH_STB 99.3 / TH_OHT 95.0 / TH_RC 4

## 원본 컬럼명
- RA_COL: M16HUB=`M16HUB.QUE.TIME.AVGTOTALTIME1MIN`, M14=`M14.QUE.LOAD.AVGLOADTIME1MIN`, M14B=`M14B.QUE.TIME.AVGTOTALTIME1MIN`, M16A=`M16A.QUE.LOAD.AVGLOADTIME1MIN`, M16B=`M16B.QUE.LOAD.AVGLOADTIME1MIN`
- RB_COL: M16HUB=`M16HUB.QUE.ALL.CURRENTQCNT`, M14=`M14.QUE.ALL.HUB_TO_M14_JOB`, M14B=`M14B.QUE.ALL.HUB_TO_M14B_JOB`, M16A=`M16A.QUE.ALL.6F_TO_HUB_JOB`, M16B=`M16B.QUE.ALL.10F_TO_HUB_JOB`
- SLA_COL: `{영역}.QUE.ALL.TRANSPORT4MINOVERRATIO`
- SORT_COL: `{영역}.SORTER.ABN.SORTERWAITCOUNTOVER`
- OHT_COL: `{영역}.QUE.OHT.OHTUTIL`

## 판정 줄 (점수 기준)
- 0~99: `🟢 정상 — 점수 N (알람 X)`
- 100~119: `🔵 관심 — 점수 N`
- 120~129: `🟡 주의 — 점수 N`
- 130~159: `🟠 경계 — 점수 N`
- 160~219: `🔴 위험 — 점수 N`
- 220+: `⚫ 발동 — 점수 N`
continuity_min ≥ 1 이면 뒤에 ` / N분째 지속` 붙임.

## 판정 마크 (각 룰 옆)
- 실측 ≥ 임계 → `🔴 초과 (X.X배)` (X.X = 실측/임계)
- 실측 < 임계 → `🟢 정상 (임계의 N%)` (N = 실측/임계×100, 정수)
- FAB/STB 는 초과면 `🔴 초과`, 아니면 `🟢 정상`
- MAXCAPA 는 `🟡 운영자조치`

## 점수산식
`총점 = layer1_total + flow_score + sla_score_total + sorter_score_total + mc_score_total`

## 룰 한글명
RA/RA_sus → 반송지연 · RB/RB_fast → 큐누적 · RC → 리프터역증가 · RD(M16HUB) → FAB저장/STB저장 (2줄) · RD(그외) → OHT정체 · SLA → SLA초과 · SORT → Sorter · MAXCAPA → MAXCAPA.

---

## 출력 템플릿 (이 모양 그대로, 한 글자 변경 금지)

```
{판정줄}
==========================================================================
  {datetime} | 점수 {unified_risk_score} [{unified_risk_level}] | hot={hot_area} | 유형 {predicted_fault_type}
  사건상태 {incident_state} | 지속 {continuity_min}분 | 재발 {refire_count}회 | 영향영역 {affected_areas}
==========================================================================

  [점수 구성] {합} = 영역합 {layer1_total} + 흐름 {flow_score} + SLA {sla_score_total} + Sorter {sorter_score_total} + MAXCAPA {mc_score_total}

  [영역 × 룰 점수]  영역           RA  RA_sus      RB RB_fast      RC      RD     SLA    SORT MAXCAPA    합
  ----------------------------------------------------------------------------------------
                   {영역:<7}    {RA}    {RA_sus}    {RB}    {RB_fast}    {RC}    {RD}    {SLA}    {SORT}    {MAXCAPA}    {행합}
   (pts 합이 0 아닌 영역만. 값이 0인 칸은 · 으로 표시)

  [발동 룰 → 원본 컬럼 / 실측값 / 임계]   ▶▶  {판정줄}

   ▶ {영역}
      · {룰한글}  {원본컬럼} = {실측}{단위} (임계 {임계})  {판정마크}
   (pts > 0 인 룰만)

   ▶ 흐름(flow): {flow_signals}    (flow_signals 비어있지 않을 때만)

  ※ reason 원문: {reason 앞 120자}...
```

## 실제 출력 예시 (이 형식 그대로)

입력:
```
M16A_HUBROOM_PR.csv,2026-06-16 07:50,2026-06-16,07:50,1,1단계 조기경보,1,,IN_INCIDENT,73,0,M16A-SLA초과,79,정상,M16A,27,M16HUB;M16A,...
```

출력:
```
🟢 정상 — 점수 79 (알람 X) / 73분째 지속
==========================================================================
  2026-06-16 07:50 | 점수 79 [정상] | hot=M16A | 유형 M16A-SLA초과
  사건상태 IN_INCIDENT | 지속 73분 | 재발 0회 | 영향영역 M16HUB;M16A
==========================================================================

  [점수 구성] 79 = 영역합 69 + 흐름 0 + SLA 10 + Sorter 0 + MAXCAPA 0

  [영역 × 룰 점수]  영역           RA  RA_sus      RB RB_fast      RC      RD     SLA    SORT MAXCAPA    합
  ----------------------------------------------------------------------------------------
                   M16HUB       10       5       ·       ·       ·       7       ·       ·       ·   22
                   M14           ·       5       ·       ·       ·       ·       ·       ·       ·    5
                   M16A         10       5       ·       ·       ·       7       5       ·       ·   27
                   M16B          ·       5       ·       ·       ·       ·       5       ·       ·   10

  [발동 룰 → 원본 컬럼 / 실측값 / 임계]   ▶▶  🟢 정상 — 점수 79 (알람 X) / 73분째 지속

   ▶ M16HUB
      · 반송지연  M16HUB.QUE.TIME.AVGTOTALTIME1MIN = 22.52분 (임계 9.0)  🔴 초과 (2.5배)
      · FAB저장   FABSTORAGERATIO = 0.0% (임계 25.75)  🟢 정상
      · STB저장   STB.3F_STORAGE_UTIL = 100.0% (임계 99.3)  🔴 초과

   ▶ M14
      · 반송지연  M14.QUE.LOAD.AVGLOADTIME1MIN = 2.63분 (임계 3.3)  🟢 정상 (임계의 80%)

   ▶ M16A
      · 반송지연  M16A.QUE.LOAD.AVGLOADTIME1MIN = 3.16분 (임계 3.2)  🟢 정상 (임계의 99%)
      · OHT정체   M16A.QUE.OHT.OHTUTIL = 95.3% (임계 95.0)  🔴 초과 (1.0배)
      · SLA초과   M16A.QUE.ALL.TRANSPORT4MINOVERRATIO = 21.0% (임계 14.05)  🔴 초과 (1.5배)

   ▶ M16B
      · 반송지연  M16B.QUE.LOAD.AVGLOADTIME1MIN = 2.77분 (임계 3.5)  🟢 정상 (임계의 79%)
      · SLA초과   M16B.QUE.ALL.TRANSPORT4MINOVERRATIO = 11.1% (임계 22.05)  🟢 정상 (임계의 51%)

  ※ reason 원문: hot_area=M16A; S1조기경보; 발동: M16HUB[R-A'(AVGTOTALTIME1MIN=22.52분/기준9.0)...
```

## 분석 블록 다음 — 최종 결론 (허용)

분석 블록(코드블록)을 출력한 **뒤**, 아래 형식으로 짧게 결론/권고를 덧붙인다:

```
─────────────────────────────────────
📌 최종 결론
  · 등급: {등급} (점수 {N})
  · 핵심: {제일 센 영역·룰 1~2개와 실측값}
  · 조치: {권고 한두 줄 — 정상이면 "모니터링 유지", 위험이면 구체 조치}
```

⛔ 단, **분석 블록 자체는 절대 변형 금지** (템플릿 그대로 monospace). 결론은 그 아래에만.

