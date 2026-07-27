---
name: m16_hub_컬럼선택
description: hubroom_predictor.py 룰베이스 / 그래프_분석 도구가 reason·relation 텍스트를 보고 "어느 raw 원본 컬럼이 원인인지" 어떻게 선택하는지 설명하는 스킬. 9룰 × 8영역이 각각 어떤 IDC 컬럼을 왜 보는지, 발동이벤트 축약명(M16HUB_ra)과 raw 풀네임(M16HUB.QUE.TIME.AVGTOTALTIME1MIN)이 어떻게 매핑되는지, 그래프에 왜 그 컬럼이 그려지는지, 새 룰·새 컬럼이 나오면 어떻게 확장하는지 묻거나 컬럼 추적을 도울 때 사용. "왜 이 컬럼", "어떤 컬럼 보는데", "컬럼 선택", "원본 컬럼 추적", "다른 컬럼 나오면", "raw 컬럼 매핑" 요청 시.
---

# m16_hub 컬럼선택 — 왜 그 컬럼이 원인으로 뽑히는가 (v7 / 0~100 척도)

> 배경은 `m16_hub_카파시`, 결과 읽기는 `m16_hub_결과해석`, 임계는 `m16_hub_임계값`.
> 이 스킬은 **reason/relation → 원본 raw 컬럼 추적** 로직 전담.
> 근거 코드: `그래프_분석/raw_columns.py` (RA_COL, RB_COL, … / parse_reason_pairs / parse_relation_pairs)

---

## 0. 핵심 한 줄
룰베이스는 매분 **8영역 × 9룰**을 평가한다. 룰이 발동하면 `reason`(발동이벤트) / `relation`(사건단위)
텍스트에 "어느 영역의 어느 룰이, 어떤 값으로" 터졌는지 적힌다. **그 텍스트를 거꾸로 읽어서
원인이 된 원본 IDC 컬럼(M16HUB.QUE.TIME.AVGTOTALTIME1MIN 같은 풀네임)을 골라낸다.**
그래프에 그려지는 컬럼은 "임의로 고른 것"이 아니라 **그 분에 실제로 룰을 터뜨린 컬럼**이다.

---

## 1. 컬럼이 3가지 이름으로 존재한다 (혼동 주의)

| 단계 | 이름 예 | 어디에 |
|---|---|---|
| **raw 풀네임** | `M16HUB.QUE.TIME.AVGTOTALTIME1MIN` | 수집 원본 M16A_HUBROOM_PR.csv (265 컬럼) |
| **발동이벤트 축약** | `M16HUB_ra` | predict_tobe/발동이벤트.csv |
| **사람 라벨** | `M16HUB 반송시간 (분)` | 그래프 좌측 큰 글씨 |

→ `raw_columns.py` 의 `EVT_TO_RAW` (22개) 가 축약↔풀네임 1:1 매핑.
→ 그래프엔 **사람 라벨(큰 글씨) + raw 풀네임(작은 monospace)** 을 같이 찍어 고객이 원본을 추적 가능.

---

## 2. 9룰이 "왜 그 컬럼을 보는가" — 룰별 근거 컬럼

각 룰은 정체를 가장 먼저 드러내는 **단일 대표 메트릭**을 본다. (영역별로 컬럼명이 다른 게 포인트)

### R-A′ (반송시간) — "물건이 늦게 도착한다"
가장 직접적인 정체 신호. 영역별로 측정 컬럼이 다름:
| 영역 | raw 컬럼 | 왜 |
|---|---|---|
| M16HUB / M14B / M16_PKT / M16_WT | `…QUE.TIME.AVGTOTALTIME1MIN` | 전체 반송시간 1분 평균 |
| M14 / M16A / M16B | `…QUE.LOAD.AVGLOADTIME1MIN` | 적재(LOAD) 시간 1분 평균 |
> 같은 "반송시간"이라도 HUB계열은 TIME, FAB계열은 LOAD 컬럼 — **영역마다 센서 위치가 달라서**.

### R-B (큐 누적) — "처리 못한 일감이 쌓인다"
HUB로 들어오는 잡 큐. 30분/10분 변화량으로 급증 감지:
| 영역 | raw 컬럼 |
|---|---|
| M16HUB | `M16HUB.QUE.M14TOM16.MESCURRENTQCNT` |
| M14 | `M14.QUE.ALL.3F_TO_HUB_JOB` |
| M14B | `M14B.QUE.ALL.7F_TO_HUB_JOB` |
| M16A | `M16A.QUE.ALL.6F_TO_HUB_JOB` |
| M16B | `M16B.QUE.ALL.10F_TO_HUB_JOB` |
| M16 | `M16.QUE.SFAB.SENDQUEUETOTAL` |

### R-C′ (리프터) — M16HUB 전용, "층간 이송 역류"
다층 리프터(`M16HUB.LFT.6ABL*.TOTAL_CURRENTQCNT` 여러 대)의 **추세 합산**으로 판정 →
**단일 컬럼이 아님**. 그래서 그래프엔 대표명 `M16HUB.LFT (리프터)` 로 표기.

### R-D (저장/가동률 포화) — "받아줄 공간/장비가 없다"
| 케이스 | raw 컬럼 |
|---|---|
| M16HUB FAB 저장율 | `M16HUB.STRATE.ALL.FABSTORAGERATIO` |
| M16HUB STB 저장율 | `M16HUB.STRATE.STB.3F_STORAGE_UTIL` |
| M14/M14B/M16A/M16B OHT 가동률 | `….QUE.OHT.OHTUTIL` |

### SLA (4분초과) — "납기 위반 비율"
| 영역 | raw 컬럼 |
|---|---|
| 전 영역 | `….QUE.ALL.TRANSPORT4MINOVERRATIO` |

### Sorter (분류대기) — "분류기 앞 적체"
| 영역 | raw 컬럼 |
|---|---|
| M14/M14B/M16A/M16B/M16HUB | `….SORTER.ABN.SORTERWAITCOUNTOVER` |

> R-B_fast / R-A_sus 는 같은 R-B / R-A 컬럼을 **시간창만 다르게**(10분 급증 / 지속) 본 것 → 컬럼 동일.
> MAXCAPA 는 운영자 변수라 그래프 시계열엔 안 그림(이벤트성).

---

## 3. reason 에서 컬럼 뽑는 규칙 (parse_reason_pairs)

발동이벤트 `reason` 은 **축약 키워드**로 적힌다. 키워드를 보고 영역+룰을 판정:

```
reason 예:
hot_area=M16HUB; S3확정; 발동:
  M16HUB[R-A'(AVGTOTALTIME1MIN=6.34분),R-D(FAB저장=0.0%,STB=100.0%)];
  M16B[R-D(OHT=98.7%),SLA(47.7%4분초과)]
```

| reason 안의 키워드 | → 선택되는 컬럼 |
|---|---|
| `AVGTOTALTIME1MIN` / `AVGLOADTIME1MIN` / `R-A'` | 그 영역 R-A 컬럼 |
| `FAB저장` / `FABSTORAGE` (M16HUB) | `M16HUB.STRATE.ALL.FABSTORAGERATIO` |
| `STB=` (M16HUB) | `M16HUB.STRATE.STB.3F_STORAGE_UTIL` |
| `OHT=` / `OHTUTIL` (HUB 외) | 그 영역 `.QUE.OHT.OHTUTIL` |
| `SLA(` / `TRANSPORT4MIN` | 그 영역 SLA 컬럼 |
| `Sorter(` / `SORTERWAIT` | 그 영역 Sorter 컬럼 |
| `역증가` (M16HUB) | `M16HUB.LFT (리프터)` 대표명 |

→ 위 예시는 **6개 컬럼** 선택: M16HUB R-A, M16HUB FAB, M16HUB STB, M16B OHT, M16B SLA (+리프터 있으면).

## 4. relation 은 더 쉽다 (parse_relation_pairs)
사건단위 `relation` 은 **raw 풀네임을 텍스트에 직접** 포함 → 정규식으로 풀네임을 바로 긁어 매칭.
```
[M16HUB R-A'] M16HUB.QUE.TIME.AVGTOTALTIME1MIN=6.34분 (기준 5.0분) |
[M16HUB R-D] M16HUB.STRATE.ALL.FABSTORAGERATIO=92.3% (기준 90%)
```

---

## 5. ★ "또 다른 컬럼이 나올 수도 있다" — 확장 규칙

컬럼 선택은 **고정 목록이 아니라 룰↔컬럼 매핑표 기반**이라 새 상황에 대응 가능:

1. **새 룰이 추가되면** (예 R-MLUD, R-CNVFULL)
   - `raw_columns.py` 의 매핑 dict(예 `RA_COL`)에 영역→컬럼 한 줄 추가
   - `parse_reason_pairs` 에 reason 키워드 1줄 추가 → 그래프 자동 반영
2. **기존 룰에 영역이 늘면** (예 M14B 에 SLA 추가)
   - 해당 dict(`SLA_COL`)에 `'M14B': 'M14B.QUE.ALL.TRANSPORT4MINOVERRATIO'` 추가
3. **컬럼명이 바뀌면** (설비 펌웨어 업데이트 등)
   - dict 값만 새 풀네임으로 교체 — 로직 변경 불필요
4. **raw CSV 에 그 컬럼이 없으면**
   - 원본raw 그래프는 자동으로 그 컬럼만 빼고 "raw 미존재 N개" 로그 (R-C′ 리프터가 대표 사례 — 단일 컬럼 없어 정상 제외)

> 즉 매핑표(raw_columns.py)만 손대면 **predictor·그래프 전부가 같은 컬럼을 일관되게** 선택한다.
> 265 컬럼 중 현재 룰이 쓰는 건 22종(EVT_TO_RAW). 나머지 243종은 "대기 컬럼" — 새 룰이 끌어 쓸 후보.

---

## 6. 고객 질문 대응 패턴

| 고객 질문 | 답하는 법 |
|---|---|
| "이 그래프 왜 이 컬럼이 나와?" | 그 분 reason 보여주고 → 발동한 룰 → 그 룰의 근거 컬럼 (2장 표) |
| "M16HUB 반송시간이 원인 맞아?" | reason 에 `AVGTOTALTIME1MIN=N분(기준 M)` 있으면 → 기준 초과라 R-A 발동 = 원인 |
| "리프터는 왜 그래프에 없어?" | R-C′ 는 다층 리프터 추세 합산이라 단일 raw 컬럼이 없음 → 대표명만 표기, 시계열 제외 |
| "다른 컬럼도 볼 수 있어?" | 5장 — 룰/컬럼은 raw_columns.py 매핑표라 추가·교체 가능 |
| "원본 값이랑 그래프 값 왜 미세하게 달라?" | 발동이벤트.csv 는 소수점 2자리 반올림본 / 원본raw 그래프는 raw CSV 3자리 직접 → 후자가 정밀 |

---

## 7. 빠른 점검 (자체 실행)
```bash
cd 그래프_분석
python raw_columns.py   # reason/relation 샘플 → 선택 컬럼 출력 데모
```
출력에 `[영역 룰] 축약 ← raw풀네임` 형태로 어떤 컬럼이 왜 뽑혔는지 그대로 보인다.
