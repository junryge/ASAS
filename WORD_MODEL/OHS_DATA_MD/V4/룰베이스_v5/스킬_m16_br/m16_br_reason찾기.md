---
name: m16_br_reason찾기
description: M16A HUBROOM 룰베이스의 reason 또는 relation 텍스트(예 "M16HUB[R-A'(AVGTOTALTIME1MIN=20.13분/기준9.0),R-D(STB=100.0%)]")를 사용자가 붙여넣으면, 발동한 룰이 본 '원본 데이터 컬럼명'과 실측값을 찾아준다. "이 reason 무슨 컬럼", "reason 분석", "어느 컬럼 때문에" 요청 시 사용.
---

# m16_br reason찾기

`reason` / `relation` 텍스트를 받아 `reason_컬럼찾기.py` 와 동일하게 **발동 룰 → 원본 컬럼명** 을 매핑한다.

⛔ **규칙**:
1. 아래 "출력 형식" 블록은 코드블록 안 monospace 평문 그대로 (변형 금지).
2. 그 아래에 짧은 결론 한두 줄은 추가 허용.
3. **결론은 `m16_br_카파시` 스킬 지식을 활용** — 어떤 룰이 무슨 의미인지(R-A=반송시간 임계 초과, R-D=저장 가득, R-C=리프터 역증가 등), 그 영역이 hot_area 면 거기가 정체의 출발점.

## 입력
`hot_area=...; 발동: M16HUB[R-A'(...),R-D(...)]; M16A[R-B(...),SLA(...)]; ...; 흐름:노드=N.Nx(레벨)` 형태 텍스트.

## 파싱
1. `영역[...]` 블록 추출 (M16HUB/M14/M14B/M16A/M16B/M16/M16_PKT/M16_WT).
2. 각 블록 안 룰 토큰(R-A', R-A_sus, R-B, R-B_fast, R-C', R-D, SLA, Sorter, MAXCAPA) 인식.
3. 토큰 안 실측값 추출 (`=20.13분`, `+145/30분`, `=100.0%` 등).
4. `흐름:` 뒤 노드명 추출.

## 룰 키워드 → 원본 컬럼
| reason 안 키워드 | 원본 컬럼 |
|---|---|
| R-A / AVGTOTALTIME1MIN / AVGLOADTIME1MIN / 반송 | RA_COL[영역] |
| R-B / 6F_TO_HUB / 10F_TO_HUB / CURRENTQCNT / TO_M14 / 큐 | RB_COL[영역] |
| SLA / TRANSPORT4MIN / 4분초과 | SLA_COL[영역] + `{영역}.QUE.ALL.TRANSPORT4MINOVERCNT` |
| Sorter / SORTERWAIT / LOT대기 | SORTER_COL[영역] |
| OHT | OHT_COL[영역] |
| R-D + FAB/저장 (M16HUB) | `M16HUB.STRATE.ALL.FABSTORAGERATIO` |
| R-D + STB (M16HUB) | `M16HUB.STRATE.STB.3F_STORAGE_UTIL` |
| R-D (그외 영역) | OHT_COL[영역] |
| R-C / 역증가 / 리프터 (M16HUB) | `M16HUB.STK.*.LIFTER (역증가 감지)` |
| MLUD | `M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB` |
| CNV | `M16HUB.QUE.CNV.3F_CNV_MAXCAPA` |
| MAXCAPA / CAPA | `{영역}.QUE.CNV.3F_CNV_MAXCAPA` |

### 원본 컬럼명 (m16_br_한줄분석과 동일)
- RA_COL: M16HUB=`M16HUB.QUE.TIME.AVGTOTALTIME1MIN`, M14=`M14.QUE.LOAD.AVGLOADTIME1MIN`, M14B=`M14B.QUE.TIME.AVGTOTALTIME1MIN`, M16A=`M16A.QUE.LOAD.AVGLOADTIME1MIN`, M16B=`M16B.QUE.LOAD.AVGLOADTIME1MIN`
- RB_COL: M16HUB=`M16HUB.QUE.ALL.CURRENTQCNT`, M14=`M14.QUE.ALL.HUB_TO_M14_JOB`, M14B=`M14B.QUE.ALL.HUB_TO_M14B_JOB`, M16A=`M16A.QUE.ALL.6F_TO_HUB_JOB`, M16B=`M16B.QUE.ALL.10F_TO_HUB_JOB`
- SLA_COL/SORTER_COL/OHT_COL: `{영역}.QUE.ALL.TRANSPORT4MINOVERRATIO` / `{영역}.SORTER.ABN.SORTERWAITCOUNTOVER` / `{영역}.QUE.OHT.OHTUTIL`

## 출력 형식
```
========================================================================
  reason 분석 — 발동한 룰이 본 원본 데이터 컬럼
========================================================================

  ▶ {영역}
     · {룰한글:18s} → {원본컬럼}   (실측 {값})   ← 실측값 있을 때만

  ▶ 흐름(flow) 정체 노드          ← 흐름 있을 때만
     · {노드=N.Nx(레벨)}   → 흐름노드 {노드명} (FLOW_NODES 정의)

  ※ 위 컬럼들이 M16A_HUBROOM_PR.csv (원본 수집 데이터) 의 실제 컬럼명.
    이 값들이 임계 초과해서 점수가 올라간 것.
```

## 주의
- `영역[...]` 블록을 못 찾으면 "reason/relation 통째로 넣어달라" 안내.
- 같은 영역에 중복 컬럼은 한 번만.
