# M16 HUBROOM — FAB별 위험도 스코어 (에이전트용 참조)

> 이 파일은 `python fab_score_doc.py --md` 로 **생성**된다. 손으로 고치지 마라 — 다음 생성 때 지워진다. 임계가 바뀌면 `config.json` 의 `fab_score.thresholds` 를 고치고 다시 생성한다.

- 출처: 스코어 산출 문서 (`hubroom_predictor.py` 의 `eval_area_rules` / `evaluate_unified`, `thresholds.json`)
- 코드: `real_time_amhs/fab_score.py`
- 등급 컷은 `config.grade` 에서 읽는다 (현재 경계 **60** · 위험 **71** · 초위험 **85**)

## 0. 틀리기 쉬운 것 먼저

| 헷갈리는 짝 | 사실 |
| --- | --- |
| `50` vs `60` | **50 은 영역점수 상한**(9룰 합 63을 자르는 값), **60 은 경계 등급 컷**. 아무 관계 없다. |
| ALL 점수 vs FAB 위험도 | 둘 다 0~100 이고 등급 컷도 같지만 **잰 대상이 다르다.** ALL 은 실제로 경보가 나는 값, FAB 은 그 영역의 영역점수를 100점으로 편 값. |
| `unified_risk_score` | 통합 파일에서는 전체 점수, **FAB 분리 파일의 정규화된 행에서는 그 FAB 의 점수**(= `area_score`). 전체 점수는 `all_score` 로 밀려나 있다. |
| 경계 컷 50 vs 60 | 50 은 **옛 값**. 2026-08 에 60 으로 올라갔다. 기존 스코어 산출 문서의 `50/71/85` 표기는 낡았다. |

## 1. 점수가 만들어지는 순서

```
1분 CSV 한 줄
  → 영역마다 9개 룰을 임계와 대조 (켜짐/꺼짐)
  → 영역점수 = min(50, Σ 켜진 룰 배점)      ← 영역당 0~50
  → raw = Σ(영역점수 × 가중치) + 흐름 + SLA + Sorter + MAXCAPA
  → 전체 점수 = min(100, round(raw × 100 ÷ 220))
```

- 대상 영역 8개: `M14` · `M14B` · `M16A` · `M16B` · `M16HUB` · `M16` · `M16_PKT` · `M16_WT` (뒤 3개는 `{영역}_score` 만 있고 상세 컬럼이 없다)
- 영역 가중치: `M14` 1, `M14B` 1, `M16A` 1, `M16B` 0.5, `M16HUB` 1
- **SLA·Sorter·MAXCAPA 는 두 번 반영된다** — 영역점수 안에 이미 들어 있고 융합에서 한 번 더 더해진다. 실질 가중치가 두 배다.

## 2. 9개 룰 배점 (모든 영역 공통)

| 룰 | 배점 | 무엇을 보나 | 언제 켜지나 |
| --- | ---: | --- | --- |
| `R-A` | 10 | 반송·적재 시간 초과 | 최근 10분 중 1회라도 임계 이상 |
| `R-A′` | 5 | 그 상태가 이어짐 | 최근 5분 중 3분 이상 · 임계는 R-A 의 70% |
| `R-B` | 10 | 대기 물량 30분 증가 | 31분 전 값과 비교 |
| `R-B fast` | 5 | 10분새 급증 | 11분 전과 비교 · 임계는 R-B 의 30% |
| `R-C` | 8 | 리프터 역증가 · 컨베이어 쏠림 | 총합은 주는데 개별은 늘어남 (20분 전 대비) |
| `R-D` | 7 | 저장·설비 포화 | 조건 하나만 걸려도 켜짐 |
| `SLA` | 5 | 4분 초과 반송 비율 | 비율이 임계를 넘거나 초과건수가 10분새 +20 |
| `SORT` | 3 | 소터 대기 · 이재 실패 | 이재 실패는 1건만 나도 켜짐 |
| `MAXCAPA` | 10×n | 설비 상한 하락 | 임계 이하로 내려간 컬럼 1개당 10점 |

- 전부 켜지면 63점 → 상한 50 적용
- **배점이 다섯 FAB 에서 완전히 같다.** 그래서 영역점수는 그대로 FAB 간 비교가 된다. 다른 것은 임계값뿐이다.

## 3. FAB별 임계값

| 룰 | 배점 | M14 | M14B | M16A | M16B | M16HUB |
| --- | ---: | --- | --- | --- | --- | --- |
| `R-A` | 10 | ≥ 3.3분 | ≥ 5분 | ≥ 3.2분 | ≥ 3.5분 | ≥ 9분 |
| `R-A′` | 5 | ≥ 2.31분 | ≥ 3.5분 | ≥ 2.24분 | ≥ 2.45분 | ≥ 6.3분 |
| `R-B` | 10 | ≥ 80건 | ≥ 150건 | ≥ 84건 | ≥ 32건 | ≥ 100건 |
| `R-B fast` | 5 | ≥ 24건 | ≥ 45건 | ≥ 25건 | ≥ 10건 | ≥ 30건 |
| `R-C` | 8 | ≥ 0.7 | — | — | — | ≥ 4대 |
| `R-D` | 7 | ≥ 95% | ≥ 95% | ≥ 95% | ≥ 95% | ≥ 25.75%<br>≥ 99.3%<br>≥ 50건<br>≥ 30건<br>≥ 0.85 |
| `SLA` | 5 | ≥ 25.45%<br>10분 + 20건 | **임계 미정의** | ≥ 14.05%<br>10분 + 20건 | ≥ 22.05%<br>10분 + 20건 | ≥ 5%<br>10분 + 20건 |
| `SORT` | 3 | ≥ 148건 | ≥ 109건 | ≥ 180건<br>≥ 1건 | ≥ 90건<br>≥ 1건 | ≥ 30건 |
| `MAXCAPA` | 10×n | ≤ 150 (평상 244) | — | ≤ 40 (평상 54)<br>≤ 100 (평상 149) | — | ≤ 100 (평상 165)<br>≤ 50 (평상 66)<br>≤ 80 (평상 129) |

- `R-A′` 임계 = `R-A` × 0.7, `R-B fast` 임계 = `R-B` × 0.3 (정수 반올림)

## 4. ALL · FAB별 실제 보고 있는 컬럼

| 룰 | ALL | M14 | M14B | M16A | M16B | M16HUB |
| --- | --- | --- | --- | --- | --- | --- |
| `R-A` | _영역별로만_ | `M14.QUE.LOAD.AVGLOADTIME1MIN`<br>csv `M14_ra` | `M14B.QUE.TIME.AVGTOTALTIME1MIN`<br>csv `M14B_ra` | `M16A.QUE.LOAD.AVGLOADTIME1MIN`<br>csv `M16A_ra` | `M16B.QUE.LOAD.AVGLOADTIME1MIN`<br>csv `M16B_ra` | `M16HUB.QUE.TIME.AVGTOTALTIME1MIN`<br>csv `M16HUB_ra` |
| `R-A′` | _영역별로만_ | `M14.QUE.LOAD.AVGLOADTIME1MIN`<br>csv `M14_ra` | `M14B.QUE.TIME.AVGTOTALTIME1MIN`<br>csv `M14B_ra` | `M16A.QUE.LOAD.AVGLOADTIME1MIN`<br>csv `M16A_ra` | `M16B.QUE.LOAD.AVGLOADTIME1MIN`<br>csv `M16B_ra` | `M16HUB.QUE.TIME.AVGTOTALTIME1MIN`<br>csv `M16HUB_ra` |
| `R-B` | _영역별로만_ | `M14.QUE.ALL.3F_TO_HUB_JOB`<br>csv `M14_rb_diff30` | `M14B.QUE.ALL.7F_TO_HUB_JOB`<br>csv `M14B_rb_diff30` | `M16A.QUE.ALL.6F_TO_HUB_JOB`<br>csv `M16A_rb_diff30` | `M16B.QUE.ALL.10F_TO_HUB_JOB`<br>csv `M16B_rb_diff30` | `M16HUB.QUE.M14TOM16.MESCURRENTQCNT`<br>csv `M16HUB_rb_diff30` |
| `R-B fast` | _영역별로만_ | `M14.QUE.ALL.3F_TO_HUB_JOB`<br>csv `M14_rb_diff10` | `M14B.QUE.ALL.7F_TO_HUB_JOB`<br>csv `M14B_rb_diff10` | `M16A.QUE.ALL.6F_TO_HUB_JOB`<br>csv `M16A_rb_diff10` | `M16B.QUE.ALL.10F_TO_HUB_JOB`<br>csv `M16B_rb_diff10` | `M16HUB.QUE.M14TOM16.MESCURRENTQCNT`<br>csv `M16HUB_rb_diff10` |
| `R-C` | _영역별로만_ | `M14.QUE.CNV.M14ATONORTHCURRENTQCNT / …SOUTH…`<br>csv `M14_cnv_skew` | — | — | — | `M16HUB.LFT.{6ABL6011…6ABL0122}.TOTAL_CURRENTQCNT`<br>csv `M16HUB_rev_count` |
| `R-D` | _영역별로만_ | `M14.QUE.OHT.OHTUTIL`<br>csv `M14_rd_oht` | `M14B.QUE.OHT.OHTUTIL`<br>csv `M14B_rd_oht` | `M16A.QUE.OHT.OHTUTIL`<br>csv `M16A_rd_oht` | `M16B.QUE.OHT.OHTUTIL`<br>csv `M16B_rd_oht` | `M16HUB.STRATE.ALL.FABSTORAGERATIO`<br>csv `M16HUB_rd_fab`<br>`M16HUB.STRATE.STB.3F_STORAGE_UTIL`<br>csv `M16HUB_stb_util`<br>`M16HUB.QUE.ALL.3F_TO_3F_MLUD_JOB`<br>_csv 없음_<br>`M16HUB.QUE.ALL.M16HUBTOM14MANUAL_CURRENTQCNT`<br>_csv 없음_<br>`M16HUB.CNV.SENDFAB.TO_M14A_CURRENTQCNT ÷ M16HUB.QUE.CNV.3F_CNV_MAXCAPA`<br>_csv 없음_ |
| `SLA` | `(집계)`<br>csv `sla_score_total` | `M14.QUE.ALL.TRANSPORT4MINOVERRATIO`<br>csv `sla_M14`<br>`M14.QUE.ALL.TRANSPORT4MINOVERCNT`<br>csv `M14_sla_cnt` | `M14B.QUE.ALL.TRANSPORT4MINOVERRATIO`<br>csv `sla_M14B` | `M16A.QUE.ALL.TRANSPORT4MINOVERRATIO`<br>csv `sla_M16A`<br>`M16A.QUE.ALL.TRANSPORT4MINOVERCNT`<br>csv `M16A_sla_cnt` | `M16B.QUE.ALL.TRANSPORT4MINOVERRATIO`<br>csv `sla_M16B`<br>`M16B.QUE.ALL.TRANSPORT4MINOVERCNT`<br>csv `M16B_sla_cnt` | `M16HUB.QUE.ALL.TRANSPORT4MINOVERRATIO`<br>csv `sla_M16HUB`<br>`M16HUB.QUE.ALL.TRANSPORT4MINOVERCNT`<br>csv `M16HUB_sla_cnt` |
| `SORT` | `(집계)`<br>csv `sorter_score_total` | `M14.SORTER.ABN.SORTERWAITCOUNTOVER`<br>csv `sorter_M14` | `M14B.SORTER.ABN.SORTERWAITCOUNTOVER`<br>csv `sorter_M14B` | `M16A.SORTER.ABN.SORTERWAITCOUNTOVER`<br>csv `sorter_M16A`<br>`M16A.SORTER.ABN.SORTERTRANSFERFAIL`<br>csv `M16A_sorter_fail` | `M16B.SORTER.ABN.SORTERWAITCOUNTOVER`<br>csv `sorter_M16B`<br>`M16B.SORTER.ABN.SORTERTRANSFERFAIL`<br>csv `M16B_sorter_fail` | `M16HUB.SORTER.ABN.SORTERWAITCOUNTOVER`<br>csv `sorter_M16HUB` |
| `MAXCAPA` | `(집계)`<br>csv `mc_score_total`<br>`(집계)`<br>csv `maxcapa_signals` | `M14.QUE.CNV.3F_CNV_MAXCAPA`<br>_csv 없음_ | — | `M16A.QUE.LFT.2F_LFT_MAXCAPA`<br>_csv 없음_<br>`M16A.QUE.LFT.6F_LFT_MAXCAPA`<br>_csv 없음_ | — | `M16HUB.QUE.LFT.3F_LFT_MAXCAPA`<br>_csv 없음_<br>`M16HUB.QUE.LFT.3F_M14BLFT_MAXCAPA`<br>_csv 없음_<br>`M16HUB.QUE.CNV.3F_CNV_MAXCAPA`<br>_csv 없음_ |
| `FLOW` _(ALL 전용)_ | `M16HUB.QUE.OHT.CURRENTOHTQCNT`<br>_csv 없음_<br>`M16HUB.QUE.M14TOM16.MESCURRENTQCNT`<br>_csv 없음_<br>`M14.QUE.CNV.M14ATOM16ACURRNETQCNT`<br>_csv 없음_<br>`M14.QUE.ALL.3F_TO_HUB_JOB`<br>_csv 없음_<br>`M14B.QUE.ALL.7F_TO_HUB_JOB`<br>_csv 없음_<br>`M14B.LFT.4ABLD_ALL.TOTAL_CURRENTQCNT_SUM`<br>_csv 없음_<br>`M14B.LFT.4ABLD_ALL.7F_TO_4F_CURRENTQCNT_SUM`<br>_csv 없음_<br>`M16A.QUE.ALL.6F_TO_HUB_JOB`<br>_csv 없음_<br>`M16A.QUE.ALL.2F_TO_HUB_JOB`<br>_csv 없음_<br>`M16B.QUE.ALL.10F_TO_HUB_JOB`<br>_csv 없음_ | — | — | — | — | — |
| `FUSE` _(ALL 전용)_ | `(집계)`<br>csv `flow_score`<br>`(집계)`<br>csv `layer1_total` | — | — | — | — | — |
| `SCORE` _(ALL 전용)_ | `unified_risk_score`<br>csv `unified_risk_score`<br>`hot_area`<br>csv `hot_area`<br>`stage`<br>csv `stage` | — | — | — | — | — |

- `ALL` 은 영역 룰(R-A…R-D)을 **직접 보지 않는다** — 영역별로만 본다. 대신 `FLOW`·`FUSE`·`SCORE` 항이 ALL 에만 있다. 자세한 건 5절.
- 반송시간만 갈린다 — `M16HUB`·`M14B` 는 `QUE.TIME.AVGTOTALTIME1MIN`(총 반송시간), `M14`·`M16A`·`M16B` 는 `QUE.LOAD.AVGLOADTIME1MIN`(적재시간). 같은 R-A 인데 **재는 것이 다르다.**
- _csv 없음_ 은 그 값이 발동이벤트 CSV 에 안 실려 온다는 뜻이다. 룰은 켜지는데 화면에서 근거 값을 볼 수 없다.

## 5. ALL 이 보는 컬럼

**ALL 은 영역이 아니다.** 자기 임계로 룰을 켜지 않고, 여덟 영역 점수에 네 항을 더한 합이다. 그래서 자기 임계값도 없고 '이 시스템만 걸리면 몇 점' 이라는 단독 상한도 없다. **그렇다고 보는 컬럼이 없는 것은 아니다** — 융합 단계에서 보는 것이 따로 있다.

| 항 | 컬럼 | 판정 |
| --- | --- | --- |
| `FLOW` 흐름 — 30분 평균 대비 배수 | `M16HUB.QUE.OHT.CURRENTOHTQCNT` | 30분 평균 대비 배수 (3.0배↑ 30 · 2.0배↑ 15 · 1.5배↑ 5) |
|  | `M16HUB.QUE.M14TOM16.MESCURRENTQCNT` | 30분 평균 대비 배수 (3.0배↑ 30 · 2.0배↑ 15 · 1.5배↑ 5) |
|  | `M14.QUE.CNV.M14ATOM16ACURRNETQCNT` | 30분 평균 대비 배수 (3.0배↑ 30 · 2.0배↑ 15 · 1.5배↑ 5) |
|  | `M14.QUE.ALL.3F_TO_HUB_JOB` | 30분 평균 대비 배수 (3.0배↑ 30 · 2.0배↑ 15 · 1.5배↑ 5) |
|  | `M14B.QUE.ALL.7F_TO_HUB_JOB` | 30분 평균 대비 배수 (3.0배↑ 30 · 2.0배↑ 15 · 1.5배↑ 5) |
|  | `M14B.LFT.4ABLD_ALL.TOTAL_CURRENTQCNT_SUM` | 30분 평균 대비 배수 (3.0배↑ 30 · 2.0배↑ 15 · 1.5배↑ 5) |
|  | `M14B.LFT.4ABLD_ALL.7F_TO_4F_CURRENTQCNT_SUM` | 30분 평균 대비 배수 (3.0배↑ 30 · 2.0배↑ 15 · 1.5배↑ 5) |
|  | `M16A.QUE.ALL.6F_TO_HUB_JOB` | 30분 평균 대비 배수 (3.0배↑ 30 · 2.0배↑ 15 · 1.5배↑ 5) |
|  | `M16A.QUE.ALL.2F_TO_HUB_JOB` | 30분 평균 대비 배수 (3.0배↑ 30 · 2.0배↑ 15 · 1.5배↑ 5) |
|  | `M16B.QUE.ALL.10F_TO_HUB_JOB` | 30분 평균 대비 배수 (3.0배↑ 30 · 2.0배↑ 15 · 1.5배↑ 5) |
| `SLA` SLA — 걸린 영역 수만큼 | `(집계)` / csv `sla_score_total` | 집계값 |
| `SORT` Sorter — 걸린 영역 수만큼 | `(집계)` / csv `sorter_score_total` | 집계값 |
| `MAXCAPA` MAXCAPA — 내려간 컬럼 수만큼 | `(집계)` / csv `mc_score_total` | 집계값 |
|  | `(집계)` / csv `maxcapa_signals` | 판정 결과 |
| `FUSE` 융합 집계 | `(집계)` / csv `flow_score` | 집계값 |
|  | `(집계)` / csv `layer1_total` | 집계값 |
| `SCORE` 판정 결과 | `unified_risk_score` / csv `unified_risk_score` | 판정 결과 |
|  | `hot_area` / csv `hot_area` | 판정 결과 |
|  | `stage` / csv `stage` | 판정 결과 |

> ⚠️ **확인된 구멍** — ALL 화면이 그리는 지표 20개 중 ALL 점수 계산에 들어가는 것은 1개(스코어 자신)뿐이다. 정작 점수를 만드는 `sla_score_total`, `sorter_score_total`, `mc_score_total`, `flow_score`, `layer1_total` 는 **ALL 화면 지표 목록(`config.ui.metric_groups`)에 없다.** CSV 에는 실려 온다.

## 6. 그 FAB 의 점수는 어느 컬럼인가 — ★제일 자주 틀리는 곳

| 어디서 온 행 | 그 FAB 점수 | 전체 점수 |
| --- | --- | --- |
| 통합 파일 `{day}_발동이벤트.csv` | `{FAB}_score` | `unified_risk_score` |
| FAB 분리 파일 `fab분리/…_{FAB}.csv` | **`area_score`** | `unified_risk_score` |
| 정규화된 행 (`jupyter_csv._fab_rows`) | `unified_risk_score` (= area_score) | `all_score` |

FAB 분리 파일을 받는 순간 `area_score` 가 `unified_risk_score` 자리로 옮겨 간다 (안 그러면 M14 화면이 전체 점수로 등급을 매긴다). 원본 전체 점수는 `all_score` 로 밀려난다. **`all_score` 가 있으면 정규화된 행**이다.

```python
# ✅ 이렇게
v, col = fab_score._stored_area(row, 'M14')   # 이름을 알아서 찾고,
                                              # 어디서 찾았는지도 준다
a = fab_score.all_row(row)                    # 정규화된 행이면 all_score 를 본다

# ❌ 이렇게 하면 한 FAB 점수를 전체 점수라고 화면에 띄운다
total = float(row['unified_risk_score'])      # 정규화된 행에서는 M14 점수다
```

## 7. 구조 — 한 FAB 만으로는 경보가 안 난다

| FAB | 가중치 | 흐름노드 | MAXCAPA컬럼 | 통상 단독상한 | 최대 단독상한 | 영역점수 천장 | 위험도 천장 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `M14` | 1 | 2 | 1 | **45** | 58 | 50/50 | 100 |
| `M14B` | 1 | 3 | 0 | **38** | 65 | 40/50 | 80 |
| `M16A` | 1 | 2 | 2 | **45** | 63 | 50/50 | 100 |
| `M16B` | 0.5 | 1 | 0 | **27** | 27 | 45/50 | 90 |
| `M16HUB` | 1 | 2 | 3 | **45** | 67 | 50/50 | 100 |

- **통상 조건에서 경계(60)에 못 가는 FAB: M14, M14B, M16A, M16B, M16HUB** — 다섯 FAB 전부다.
- 최대 조건까지 끌어올려도 못 가는 곳: M14, M16B
- 근거: 스코어 산출 문서가 **예측기를 직접 호출해** 낸 검증표에 "허브 한 곳에 룰 전부 + 흐름 심각 = 44점" 이라는 줄이 있고, 같은 조건을 이 계산에 넣으면 45점이 나온다.
- `M14B` 는 R-C(룰 없음), SLA(임계 미정의), MAXCAPA(룰 없음) 때문에 영역점수가 40점이 천장이다 → 위험도 80점 (**초위험 85점에 못 간다**)
- `M16B` 는 R-C(룰 없음), MAXCAPA(룰 없음) 때문에 영역점수가 45점이 천장이다 → 위험도 90점

## 8. 이 데이터를 다룰 때의 규칙

### 1. 비교는 절대 임계로 한다

- ✅ 배점이 모든 FAB 에서 같으니 영역점수 25점은 어디서든 같은 25점이다.
- ❌ 평소 대비 편차(robust-z)로 FAB 을 비교하면 **늘 나쁜 FAB 이 '정상'** 으로 보인다. 기준선도 같이 나쁘기 때문이다. 순위가 뒤집힌다. `contrib.py` 의 z 는 *한 FAB 안에서* '무엇이 점수를 올렸나' 를 볼 때만 쓴다.

### 2. 원본 값을 나란히 놓고 비교하지 않는다

- ✅ 임계를 넘었느냐(=점수)를 비교한다.
- ❌ 반송시간 임계가 M16HUB 9.0분 · M16A 3.2분으로 세 배 가까이 다르다. M16A 3.4분과 M16HUB 3.4분은 전혀 다른 상태다.

### 3. 영역점수는 재현이지 추정이 아니다

- ✅ `{FAB}_pts_*` 9개를 더하면 영역점수가 나온다. 저장된 값과 맞춰 본다.
- ❌ 저장값과 어긋나면 한쪽을 골라 맞는 척하지 말고 `area_score()['mismatch']` 로 알린다.

### 4. 임계가 문서에 없으면 None 으로 둔다

- ✅ 화면·문서에 '임계 미정의' 라고 뜬다.
- ❌ 0 으로 채우면 '항상 켜짐' 이 되어 정반대 거짓말이 된다.

### 5. 등급 컷을 코드에 박지 않는다

- ✅ `sentinel.grade_cuts(cfg)` 로 `config.grade` 에서 읽는다.
- ❌ 2026-08 에 경계가 50→60 으로 바뀌었다. 또 바뀐다.

### 6. 컬럼 목록을 새로 정의하지 않는다

- ✅ ALL 은 `config.ui.metric_groups`, FAB 은 `lp_client._fab_strip()` — 이미 있다. `fab_score.screen_metrics()` 가 그걸 가져온다.
- ❌ 두 곳에 적으면 반드시 갈라진다.

### 7. 비교는 통합 파일 행으로 한다

- ✅ FAB 분리 파일은 자기 영역 컬럼만 있어 비교가 안 된다.
- ❌ 화면의 `?sys=` 를 따라가면 안 된다.

### 8. 데이터가 없으면 0 이 아니라 None 이다

- ✅ '30분 전 데이터 없음' 과 '변화 없음(0)' 은 다르다.

## 9. 코드에서 쓰는 법

```python
import fab_score as F
from lp_client import load_config
cfg = load_config()

F.compare(rows, at, cfg)      # ALL + FAB 5 를 한 시각으로 나란히 → rows[]
F.area_score(row, 'M14', cfg) # 그 1분의 영역점수 (pts 합, 상한 적용, mismatch)
F.all_row(row, cfg)           # ALL 줄 (융합 5항, 룰별 걸린 영역 수)
F.risk(area)                  # 영역점수 0~50 → 위험도 0~100
F.watch('M16HUB', cfg)        # 그 시스템이 보는 컬럼·임계 ('ALL' 도 된다)
F.screen_metrics(sys, cfg)    # 화면이 이미 그리는 지표 목록 (있는 정의)
F.join_columns(sys, cfg)      # 화면 지표 ⇄ 룰/임계 + 양쪽 구멍
F.max_area('M14B', cfg)       # 받을 수 있는 천장 (룰 없는 칸 반영)
F.solo_ceiling(f, cfg, mode)  # 단독 상한 'typical' | 'max'
F.fuse_check(row, cfg)        # 융합 공식 재현 검증
```

HTTP

```
GET /api/fab/compare?day=YYYYMMDD&at=YYYY-MM-DD HH:MM
GET /api/fab/columns
GET /docs/fab-score          # 사람이 읽는 HTML 문서
```

## 10. 아직 확인 안 된 것 (추측으로 메우지 마라)

1. **`M14B` 의 SLA 임계** — `sla_M14B` 컬럼은 CSV 에 실려 오는데 스코어 산출 문서의 SLA 표에 M14B 행이 없다. `None` 으로 두었다. `thresholds.json` 확인 후 `config.fab_score.thresholds.M14B.SLA` 에 넣는다.
2. **`{FAB}_score` 가 상한을 넘긴 행** — 샘플에 `M16HUB_score = 55` (> 50) 인 행이 있다. 손으로 만든 시험 행일 수도 있고, 예측기가 그 컬럼에는 상한을 안 거는 것일 수도 있다. 실데이터에서 나오는지 확인이 필요하다.
3. **`M16HUB_rd_fab` 의 눈금** — 임계는 25.75(%)인데 실제 값이 0.59 / 1.18 로 들어온다. 같은 단위인지 확인이 필요하다. 그래서 룰의 켜짐/꺼짐은 값이 아니라 **`{FAB}_pts_*` 로 판정한다.**

---

_생성: `python fab_score_doc.py --md` · 등급 컷 60/71/85 (`config.grade`) · 영역점수 상한 50 · 환산 기준 raw 220_
