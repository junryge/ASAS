# OHT Dijkstra 실행 가능성 검증 — 20260421

> **목적**: 20260421 M14A 데이터로 `OHT_DIJKSTRA_ARCHITECTURE.md`에 기술된 Dijkstra 경로 계산을 재현·검증한다.
>
> **데이터**: `WORD_MODEL/OHS_DATA_MD/20260421/out/*.csv` (1.99M 행)
> **토폴로지**: `OHT3/layout_cache.json` (9,402 노드, 10,422 엣지)

---

## 1. 결론 요약

| 항목 | 상태 | 비고 |
|---|:---:|---|
| 레일 네트워크 그래프 확보 | ✅ | layout_cache.json (정식 토폴로지) |
| 실시간 엣지 점유 (차량 수) | ✅ | 1,061대 스냅샷에서 990엣지 |
| Rail Cut(차단) 반영 | ✅ | 204개 차단 엣지 |
| Dijkstra 실행 | ✅ | 평균 < 20ms / 쿼리 |
| OD 도달성 | ✅ **100%** | 10/10 샘플 |
| **실제 경로 일치도** | ⚠️ **낮음** | 공유 노드 2/284 (V00894 샘플) |

**최종 판단**: 데이터로 Dijkstra 실행은 **가능**하나, **운영 결과와 일치하지 않음**. 2개의 핵심 차이가 있음 (§3 참조).

---

## 2. 검증 절차

### 2.1 1차 — 관측 데이터로만 그래프 구축 (실패)

`LOGPRESSO_oht_data_m14a_20260421.csv`의 `ADDRESS → NEXT_ADDRESS` 쌍으로 엣지 추출:

| 결과 | 값 |
|---|---|
| 추출 노드 | 9,194 |
| 추출 엣지 | 10,160 (관측된 한 방향만) |
| OD 도달성 | **20% (4/5 UNREACHABLE)** |

→ 관측 trace는 **부분 그래프**만 복원. 실운영 Dijkstra 재현 불가.

### 2.2 2차 — layout_cache.json 토폴로지 사용 (성공)

`/home/user/ASAS/OHT3/layout_cache.json`에는 양방향 엣지가 완전 포함:

```json
{
  "nodes": {"1": [x, y], ..., "9402": [x, y]},
  "edges": {"1,2": 666, "2,1": 666, "6,7": 364, ...},
  "adj":   {"1": [2], "2": [1], ...}
}
```

- 노드 수: **9,402**
- 엣지 수: **10,422** (양방향 쌍 존재)
- 거리: 엣지값으로 직접 제공

### 2.3 LineCost 공식 (문서 §3.2 그대로 적용)

```
LineCost(e) = max(distance, 1)
            + idle_vehicles(e)  × 3,000
            + busy_vehicles(e)  × 5,000
            + (대기작업 제외 — 데이터 없음)
```

현재 점유 계산:
- 각 차량 `(ADDRESS, NEXT_ADDRESS)`로 해당 엣지에 +1
- `STATUS == '0'` → idle, 그 외 → busy (단순화 가정)

### 2.4 결과 — 샘플 OD 10건

| 출발 | 도착 | 비용 | 홉수 |
|---:|---:|---:|---:|
| 3293 | 1805 | 231,332 | 216 |
| 1600 | 8350 | 116,760 | 132 |
| 8078 | 1801 | 70,179 | 83 |
| 7909 | 7593 | 231,498 | 277 |
| 1993 | 7863 | 192,946 | 274 |
| 3933 | 3208 | 113,792 | 97 |
| 3251 | 1241 | 167,875 | 201 |
| 6168 | 5009 | 70,724 | 73 |
| 3939 | 4126 | 60,755 | 49 |
| 4971 | 6039 | 174,015 | 224 |

**도달 가능: 10/10 (100%)**

---

## 3. 운영 결과와의 차이

### 3.1 차량 V00894 실제 경로 vs Dijkstra 예측

**실제 관측 (처음 15 노드)**:
```
9043 → 9039 → 9036 → 9031 → 9029 → 9028 → 9026 → 9025 → 9023 → 9020 → 9016 → 9015 → 9013 → 9011 → 9009
(주소 감소 방향으로 주행)
```

**Dijkstra 예측 (9043 → 7580, 해당 기간 DESTINATION 24912가 layout에 없어 대체)**:
```
9043 → 9044 → 9045 → 9046 → 9047 → 9048 → 9049 → 9050 → 9051 → 9052 → 9053 → 9054 → 9055 → 9056 → 9057
(주소 증가 방향으로 주행)
```

**공유 노드: 2 / 284** — 거의 완전히 다른 경로.

### 3.2 원인 분석

#### ① 방향 제약(directionality) 미반영 **[가장 큰 원인]**
- layout에 `(1,2)`와 `(2,1)` 양방향 엣지가 모두 존재 → Dijkstra는 양방향 모두 자유롭게 사용
- 실제 OHT 레일은 대부분 **단방향 트랙**. 제어기는 차량의 **주행 방향 제약**을 알고 있음
- layout_cache에는 이 정보가 없음 → 별도 메타(route.xml / OHT2/layout.xml) 필요

#### ② DESTINATION 노드 일부 누락
- V00894의 DESTINATION=24912는 layout에 없음 (stationeditor 논리 주소일 가능성)
- `route.xml`에 **"stationId → route_address"** 매핑 존재 (예: `4AFC3201: [8417, 4869]`)
- 이 매핑을 선적용해야 stationId → 실제 노드 id 변환 가능

#### ③ LineCost 파라미터 미튜닝
- 문서값(3,000 / 5,000) 사용 중이나 실운영 값은 다를 수 있음
- `ALT/src/data/PredictionPara.java`의 실값 확인 필요
- 속도 EMA(0.6/0.4) 미반영 — 엣지별 실측 속도 누적 데이터 부재

#### ④ 대기작업 수(work destination count) 데이터 부재
- 페널티 공식의 3번째 항 입력값이 현재 CSV에 없음
- MCS/TCS 측 작업 큐 스냅샷 필요

---

## 4. 검증 가능한 것 / 불가능한 것

### ✅ 현재 데이터로 가능
1. 네트워크 연결성 검증 (9,402 노드 도달성)
2. Rail Cut 적용 시 경로 존재 여부
3. "비용 없는" 순수 최단거리 경로 계산 (idle/busy 가중치 0)
4. 차량 실제 주행 시퀀스 추출 (시간순 정렬 후)
5. 엣지별 관측된 실측 속도 (연속 ADDRESS 이동 시간차 / 거리)

### ❌ 현재 데이터로 불가 — 추가 필요
1. **단방향 트랙 제약** — `OHT2/layout/layout/route.xml` 또는 `layout.xml`(222MB) 파싱
2. **stationId ↔ address 매핑** — `route.xml`의 route_address 리스트
3. **실운영 페널티 가중치** — `ALT/src/data/PredictionPara.java` 코드 확인
4. **대기작업 수** — MCS 측 커맨드 큐 로그 (현 CSV에 없음)
5. **속도 EMA 상태** — `OHT2/JAVA/RaileEdge.java`의 내부 상태 snapshot

---

## 5. 다음 단계 권장안

| 우선순위 | 작업 | 담당 |
|:---:|---|---|
| P0 | `route.xml` 파싱 → stationId ↔ address 매핑 테이블 생성 | 데이터 |
| P0 | `layout.xml`(222MB) 파싱 → 엣지 방향 제약 추출 | 데이터 |
| P1 | 실제 주행 시퀀스로 엣지별 관측 속도 계산 (EMA 재현) | 분석 |
| P1 | `PredictionPara.java`에서 실제 페널티 상수 추출 | 코드 |
| P2 | MCS 커맨드 큐 로그 확보 → 대기작업 수 반영 | MCS팀 |
| P2 | 3단계 통합 후 경로 일치도 재측정 (목표: 공유 노드 > 70%) | 분석 |

---

## 6. 재현 스크립트

```bash
# 1. 토폴로지 로드
python3 -c "import json; d=json.load(open('OHT3/layout_cache.json')); print(len(d['nodes']), len(d['edges']))"

# 2. Dijkstra 검증 실행 (약 7초)
python3 /tmp/dijkstra_with_layout.py
```

검증 스크립트: `/tmp/dijkstra_with_layout.py` (본 보고서와 함께 커밋 예정 시 `WORD_MODEL/OHS_DATA_MD/20260421/dijkstra_verify.py`).

---

## 7. 요약 한줄

> **데이터로 Dijkstra 실행은 가능 (100% 도달성). 다만 방향 제약·stationId 매핑·페널티 튜닝이 없어 실운영 경로와 거의 일치하지 않음. layout.xml 파싱이 가장 시급.**

---

## 8. 갱신(20260421 추가 검증)

### 8.1 layout.xml 파싱 성공
`OHT2/layout/layout/layout.zip → layout.xml (222MB)` 스트리밍 파싱 완료 (≈8초):

| 추출 항목 | 수량 |
|---|---|
| Addr (노드) | 9,403 |
| NextAddr (방향성 엣지) | 10,424 |
| Station (stationId↔addr 매핑) | 22,822 |

→ 산출물: `/tmp/layout_full.json` (재현 스크립트 `parse_layout_xml.py`)

### 8.2 Station 매핑 성공 사례
- DESTINATION=24912 → addr=12060, port=4AFZ62-512
- DESTINATION=1283 → addr=3143
- DESTINATION=15473 → addr=3237 … 등 다수 매핑 확인

### 8.3 CSV 역시간순 이슈 (수정됨)
`LOGPRESSO_oht_data_m14a_*.csv`는 **최신 `_id`가 먼저** (내림차순). 시간 정렬 필수.

**수정 후 V00894 실제 경로** (시간 오름차순):
```
9390 → 9391 → 9048 → 9050 → 9054 → 9058 → 9060 → 9063 → ... → 9043 (끝)
총 1,462 고유 노드 방문 (85분간)
```

→ 주소 번호가 증가 방향으로 주행. 앞서 보고한 "감소 방향" 은 **정렬 오류**였음.

### 8.4 `basic-direction` 의미 재해석 필요
- `basic_dir=true` 엣지만으로 Dijkstra → **30개 OD 중 3개 도달 (10%)**
- `basic_dir=true` + disable-type=0 필터링도 동일하게 단절
- → `basic-direction`은 "주행 허용 방향"이 **아님**. 다른 의미 (아마 엣지의 "기본 좌표/표시 방향")
- **대안**: `before-address` 리스트도 엣지로 추가하면 연결성 회복될 가능성

### 8.5 1.7초 샘플링 한계
- V00894 경로에 `9391 → 9048` 같은 **큰 주소 점프** 관찰
- 물리적 인접이 아니라, 1.7초 간격으로 샘플링되며 중간 주소 수백개가 로그에 누락됨
- → **개별 엣지 단위의 "실제 경로 vs 예측 경로" 검증은 구조적으로 불가**
- → 검증 가능한 것: ① start/end 도달성 ② 대략적인 경로 길이 ③ 주요 체크포인트 통과 여부

### 8.6 최종 현재 결론

| 검증 항목 | 결과 |
|---|:---:|
| 그래프 로드(양방향) | ✅ |
| Station → address 매핑 | ✅ |
| OD 도달성 | ✅ 100% (양방향 엣지 사용) |
| 방향 제약 적용 가능 | ⚠️ basic-direction 의미 재조사 필요 |
| 개별 엣지 경로 일치도 | ⚠️ 샘플링 한계로 직접 비교 불가 |
| 시작→도착 거리 정합성 | 🔲 미검증 |
| LineCost 가중치 운영값 | 🔲 미확보 |

### 8.7 다음 P0 작업

1. **`before-address` 리스트를 엣지로 편입** → 연결성 정상화
2. **Java 소스(DijkstraVhlRouteFind.java) 실제 코드 리뷰** → 가중치/필터 조건 확정
3. 도달성 검증을 **양방향 그래프**로 재확정 (100% 유지)
4. **경로 거리 (Dijkstra cost) vs 실제 이동 시간** 거시 비교 (상관관계 분석)
5. 최종적으로 엣지 단위 일치도가 아닌 **출발·도착·총거리** 기준 검증 권장

---

## 9. 최종 판정 (20260421 완료)

### 9.1 결론

> ## ✅ **Dijkstra 분석 가능**

### 9.2 실측 근거

| 지표 | 결과 | 기준 |
|---|---:|---|
| OD 도달성 (200개 랜덤) | **100.0%** | ≥95% → 합격 |
| DESTINATION 도달성 | **100.0%** | ≥95% → 합격 |
| **거리↔시간 피어슨 상관 r** | **0.896** | 0.80↑ 매우 강함 |
| Dijkstra 실행 속도 | 평균 0.6ms, 최대 5.9ms | <10ms 실시간 가능 |
| 유효 검증 세그먼트 | 61,692 | 표본 충분 |

### 9.3 검증 방법

- `LOGPRESSO_oht_data_m14a_*.csv`에서 차량별 시간순 정렬 → DEST 변화점 기준 **세그먼트 분리**
- 각 세그먼트의 `(start_addr, end_addr, elapsed_time)` 추출
- layout.xml의 distance-puls 거리 기반 Dijkstra 실행
- 200개 무작위 세그먼트에 대해 도달성 검사
- 실측 경과시간 vs Dijkstra 거리의 피어슨 상관계수 계산

### 9.4 핵심 시사점

1. **그래프 완전성 확보**: 10,424 엣지로 61,692 세그먼트 전수 도달 가능
2. **거리 단위의 물리적 일치**: Dijkstra의 distance-puls 가중치가 실측 이동시간과 **89,614 pulse/s** 비율로 선형 대응 → 기본 통과시간 계산에 그대로 사용 가능
3. **Station 매핑 정상**: 22,822개 매핑으로 모든 DESTINATION(ex: 24912→12060) 해결
4. **실시간 가능**: 쿼리당 <1ms → OHS 운영 부하 없이 실시간 경로 재계산 가능

### 9.5 남은 이슈(후속)

1. **LineCost 페널티 가중치(idle/busy/대기작업)** — 실운영값 미확보 (문서 기본값 사용 중)
   - 검증 방법: 혼잡 시점과 비혼잡 시점의 경로 차이 분석
2. **속도 EMA 상태 재현** — `RaileEdge.java` 내부 상태 스냅샷 필요
3. **단방향/양방향 제약의 정확한 의미** — `basic-direction`은 "주행 방향"이 아닌 것으로 판명. `OHT2/JAVA/DijkstraVhlRouteFind.java` 소스에서 확정 필요

### 9.6 재현 스크립트

- `WORD_MODEL/OHS_DATA_MD/20260421/parse_layout_xml.py`
- `WORD_MODEL/OHS_DATA_MD/20260421/dijkstra_v3_timesort.py`
- `WORD_MODEL/OHS_DATA_MD/20260421/dijkstra_final_verify.py` (본 검증)

```bash
unzip /home/user/ASAS/OHT2/layout/layout/layout.zip -d /tmp/
python3 WORD_MODEL/OHS_DATA_MD/20260421/parse_layout_xml.py
python3 WORD_MODEL/OHS_DATA_MD/20260421/dijkstra_final_verify.py
```

기대 출력: `도달성 200/200 (100%), 피어슨 r = 0.896`
