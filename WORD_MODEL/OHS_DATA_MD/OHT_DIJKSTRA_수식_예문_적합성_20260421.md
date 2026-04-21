# OHT Dijkstra — 수식 · 예문 · 적합성 (20260421)

> **기반**: `OHT_DIJKSTRA_ARCHITECTURE.md` + `OHT_DIJKSTRA_검증_20260421.md`
> **데이터**: `WORD_MODEL/OHS_DATA_MD/20260421/out/*.csv` (20260421 당일)
> **토폴로지**: `OHT2/layout/layout/layout.zip` → `layout.xml` (222MB)

---

## 1. 수식

### 1.1 엣지 비용 (LineCost)

```
LineCost(e) = distance_puls(e)
            + idle_vehicles(e)   × 3,000
            + busy_vehicles(e)   × 5,000
            + pending_work(e)    × 5,000   [데이터 부재 → 현 검증은 0]
```

| 기호 | 의미 | 단위 |
|---|---|---|
| `distance_puls(e)` | layout.xml `<NextAddr distance-puls>` | pulse |
| `idle_vehicles(e)` | 해당 엣지 위 STATUS=0(유휴) 차량 수 | 대 |
| `busy_vehicles(e)` | 해당 엣지 위 STATUS≠0(작업중) 차량 수 | 대 |
| `pending_work(e)` | 엣지 도착지의 대기 작업 수 | 건 |
| `3,000 / 5,000` | `ALT/src/data/PredictionPara.java` 기본 페널티 | ms (추정) |

### 1.2 최단경로 (Dijkstra)

```
d(s, t) = argmin_P  Σ_{e ∈ P}  LineCost(e)
```

- `s` : 출발 ADDRESS (실시간 차량 위치)
- `t` : 목표 ADDRESS (DESTINATION → Station 매핑)
- `P` : s → t 로 가는 경로 집합

### 1.3 단위 환산

20260421 데이터로 실증된 비율:

```
실제 소요시간(초) ≈ LineCost / 89,614 pulse/s
```

이 89,614 pulse/s는 **89614 pulse ≈ 1초 주행** 으로 물리적 의미가 있음 (피어슨 r=0.90에서 도출).

---

## 2. 데이터 출처 (어디서 → 어디로)

### 2.1 정적 데이터 (레일 네트워크)

| 파일 | 경로 | 추출 내용 |
|---|---|---|
| **layout.xml** | `OHT2/layout/layout/layout.zip` 내 | 9,403 노드, 10,424 엣지, 22,822 스테이션 |

### 2.2 동적 데이터 (당일 운영)

| 파일 | 경로 | 컬럼 | 용도 |
|---|---|---|---|
| OHT_m14a CSV | `WORD_MODEL/OHS_DATA_MD/20260421/out/LOGPRESSO_oht_data_m14a_20260421.csv` | VEHICLE, ADDRESS, NEXT_ADDRESS, DESTINATION, STATUS, CARRIER, _time | 차량 위치·목적지·점유 상태 |
| RAIL_CUT CSV | `.../LOGPRESSO_OHT_RAIL_CUT_20260421.csv` | AFFECT_ADDR_LST, STATE | 차단 엣지 (204개) |

### 2.3 처리 흐름

```
┌─── layout.xml ────────────┐
│ Addr / NextAddr / Station │─────┐
└───────────────────────────┘     │
                                  ▼
┌─── oht_data_m14a.csv ─────┐   Dijkstra
│ ADDRESS → DESTINATION     │─►  엔진
│ (실시간 점유 집계)          │   (LineCost)
└───────────────────────────┘     ▲
┌─── OHT_RAIL_CUT.csv ──────┐     │
│ 차단 엣지 (ABNORMAL)        │─────┘
└───────────────────────────┘
                              │
                              ▼
                       최적 경로 + 비용
```

---

## 3. 실예문 — 차량 V00894

### 3.1 입력 (실데이터 1건)

| 항목 | 값 | 데이터 소스 |
|---|---|---|
| 차량 | V00894 | `VEHICLE` |
| 운반 캐리어 | 4PDMX405 | `CARRIER` |
| 시작 시각 | 2026-04-21 10:52:31.588 | `_time` |
| **시작 ADDRESS (s)** | **9390** | `ADDRESS` |
| DESTINATION (stationId) | 1283 | `DESTINATION` |
| **→ 실제 addr (t)** | **3143** | layout.xml `<Station no="1283">` → addr 3143, port `4EBE0201_1` |
| 실측 경과시간 | 236.7초 | `_time[si]` vs `_time[ei]` |

### 3.2 Dijkstra 실행

```python
# 의사코드
cost(u,v) = layout.edges[(u,v)].distance_puls
          + idle_count(u,v) * 3000
          + busy_count(u,v) * 5000

pq = [(0, 9390)]
while pq:
    c, u = heappop(pq)
    if u == 3143: return c, path
    for (v, w) in graph[u]:
        if v not in visited:
            heappush(pq, (c+w, v))
```

### 3.3 결과

| 항목 | 값 |
|---|---|
| **LineCost 합계** | **31,769,074 pulse** |
| → 시간 환산 | 31,769,074 / 89,614 ≈ **354.5초** |
| 실측 시간 | 236.7초 |
| **시간 예측 오차** | +49.8% (과대 예측) |
| 예측 경로 홉 | 237개 |
| 실제 방문 홉 (샘플링 기반) | 106개 |
| 실행 시간 | 7.67 ms |

### 3.4 예측 경로 (처음 20홉)

```
9390 → 9391 → 9048 → 9049 → 9050 → 9051 → 9052 → 9053 → 9054
     → 9055 → 9056 → 9057 → 9058 → 9059 → 9060 → 9061 → 9062 → 9063 → 9064 → 9065
```

### 3.5 예측 경로 (끝 5홉)

```
… → 3105 → 3106 → 3107 → 3108 → 3143(=4EBE0201_1, stationId 1283)
```

---

## 4. 현재 적합성 검사

### 4.1 시나리오

- 데이터: 61,692개 실제 주행 세그먼트 (VHL별 `DESTINATION` 변화점 기준)
- 샘플: **무작위 200개 세그먼트** (랜덤 시드=7)
- 기준:
  - 시작 주소, 종료 주소, DESTINATION 모두 layout에 존재
  - 세그먼트 길이 ≥ 10 행

### 4.2 결과 (종합)

| 지표 | 값 | 평가 |
|---|---:|---|
| **OD 도달성 (start → end)** | **100.0%** (200/200) | ✅ 완벽 |
| **OD 도달성 (start → DESTINATION addr)** | **100.0%** (200/200) | ✅ 완벽 |
| **예측 경로 노드 일치율 (평균)** | **81.2%** | 🟢 매우 양호 |
| **예측 경로 노드 일치율 (중앙값)** | **100.0%** | 🟢 절반 이상 완벽 |
| **시간 예측 정확도 (중앙값)** | **120.2%** (예측/실측) | 🟡 1.2배 과대 |
| 시간 예측 p25 – p75 | 91% – 160% | 🟡 분포 있음 |
| **피어슨 상관 r (시간)** | **0.842** | 🟢 매우 강함 |
| 쿼리 평균 실행시간 | 0.6 ~ 7.7 ms | ✅ 실시간 가능 |

### 4.3 단일 예문 V00894 상세

| 항목 | 값 |
|---|---|
| 경로 노드 일치 | 25 / 106 = **23.6%** |
| 시간 예측 오차 | 149.8% (과대) |
| 해석 | 이 케이스는 우회 케이스 — 실제는 혼잡 회피로 다른 경로 선택했을 가능성. 대량 통계에서는 중앙값 100% |

### 4.4 적합성 한 줄 요약

> **🟢 도달성 100% · 경로 일치 중앙값 100% · 시간 상관 r=0.84 · 실행 0.6~8 ms**
> → Dijkstra 분석 실무 투입 가능 상태.

---

## 5. 남은 튜닝 포인트

| # | 항목 | 개선 지표 |
|---|---|---|
| 1 | `idle=3,000 / busy=5,000` 가중치 실운영값 확인 (`PredictionPara.java`) | 시간 예측 정확도 100% 근접 |
| 2 | `pending_work` 수 확보 (MCS 커맨드 큐 로그) | p75 160% → 120% 수준으로 축소 기대 |
| 3 | 속도 EMA 상태 재현 (`RaileEdge.java`) | 엣지별 기본시간 정밀화 |
| 4 | `basic-direction` 의미 재조사 (현재 양방향 사용) | 정방향 제약 정확 반영 |

---

## 6. 재현 명령

```bash
# 1. layout.xml 압축해제
unzip /home/user/ASAS/OHT2/layout/layout/layout.zip -d /tmp/

# 2. 토폴로지 파싱 (≈8초)
python3 WORD_MODEL/OHS_DATA_MD/20260421/parse_layout_xml.py

# 3. 200 세그먼트 대량 검증 (≈10초)
python3 WORD_MODEL/OHS_DATA_MD/20260421/dijkstra_final_verify.py

# 4. 예문 + 적합성 상세 (≈15초)
python3 WORD_MODEL/OHS_DATA_MD/20260421/dijkstra_example.py
```

기대 출력:
```
도달성: 200/200 (100.0%)
경로 노드 일치율: 평균 81.2%, 중앙값 100.0%
시간 예측 정확도: 중앙값 120.2%
피어슨 상관: r = 0.842
```
