# HID IN/OUT 로직 흐름도

`ALT/hid_inout_new/` 신규 구현의 전체 데이터 흐름을 시각화한 문서.
(기존 `HidEdgeInOutQueueFlushBatch` / `HidEdgeInOutUpdateMasterBatch` 와 병행
가능하지만, 운영 시에는 한쪽 Quartz Job 만 enable)

---

## 1. 전체 아키텍처

```mermaid
flowchart LR
    subgraph SRC["데이터 발생"]
        OHT[OHT 차량<br/>UDP/TIB 메시지]
    end

    subgraph WORKER["메시지 처리 (실시간)"]
        OMW[OhtMsgWorkerRunnable<br/>_handleVehicleUpdate]
        SW{HID_INOUT<br/>switch ON?}
        COL[HidInoutCollector<br/>recordTransition]
    end

    subgraph MEM["인메모리 누적 (1분)"]
        MAP[(AtomicReference&lt;<br/>ConcurrentHashMap&lt;<br/>HidInoutEventKey,<br/>HidInoutAggregate&gt;&gt;)]
    end

    subgraph BATCH["Quartz 배치"]
        FB[HidInoutFlushBatch<br/>매 1분]
        MB[HidInoutMasterBatch<br/>매일 1회]
    end

    subgraph DB["Logpresso 적재"]
        T1[("{FAB}_ATLAS_HID_INOUT")]
        T2[("{FAB}_ATLAS_INFO_HID_INOUT_MAS")]
        T3[("{FAB}_ATLAS_HID_INFO_MAS")]
    end

    subgraph NOTIFY["임계치 알림"]
        TIB[HidInoutTibrvNotifier]
        RV[(TibRV<br/>amos topic)]
    end

    OHT --> OMW --> SW
    SW -- ON --> COL
    SW -- OFF --> X[skip]
    COL --> MAP
    MAP -- drain --> FB
    FB --> T1
    FB --> TIB --> RV
    MB --> T2
    MB --> T3
```

---

## 2. 실시간 수집: HidInoutCollector.recordTransition()

```mermaid
flowchart TD
    A[OhtMsgWorkerRunnable<br/>vehicle 메시지 수신] --> B{prevHidId<br/>!= currHidId?}
    B -- no --> X1[no-op]
    B -- yes --> C[buildKey:<br/>HidInoutEventKey 생성<br/>fromHid, toHid, fab, mcp,<br/>vhlFab, vhlName, eqpName]
    C --> D[ConcurrentHashMap<br/>.computeIfAbsent]
    D --> E[agg.incrementTransCnt<br/>AtomicInteger]
    E --> F[McpProperties.getMcp75Config<br/>.getRawHidMap]
    F --> G[RawHid 매칭:<br/>vhlCountLimit, vhlPrecaution]
    G --> H[edgeMap 순회:<br/>해당 HID RailEdge.velocity<br/>평균 = freeFlowSpeed]
    H --> I[DataSet.hidVehicleCountMap<br/>읽기 = hidValue]
    I --> J[agg.updateSnapshot<br/>limit, precaution,<br/>speed, hidValue]
    J --> K[end]
```

**핵심:**
- `incrementTransCnt()` 는 `AtomicInteger.incrementAndGet()` — 다수 OHT 워커 동시 호출 안전
- 스냅샷 4개 필드는 `volatile` — 마지막 관측치만 보존 (분단위 통계라 단조성 불필요)
- 예외는 catch 후 흡수 → 단일 차량 처리 실패가 전체 메시지 루프 정지시키지 않음

---

## 3. 1분 적재: HidInoutFlushBatch.execute()

```mermaid
flowchart TD
    Q[Quartz cron<br/>0 * * * * ?] --> A[execute]
    A --> B{DataService<br/>initialized?}
    B -- no --> X1[return]
    B -- yes --> C[HidInoutCollector<br/>.drain]
    C -.->|getAndSet new map| MAP[(누적 map<br/>atomic swap)]
    C --> D{drained.isEmpty?}
    D -- yes --> X2[log + return]
    D -- no --> E[for each entry]

    E --> F{transCnt &gt; 0?}
    F -- no --> E
    F -- yes --> G{fabId blank?}
    G -- yes --> H1[skip row<br/>다른 fab 계속]
    H1 --> E
    G -- no --> H{HID_INOUT<br/>스위치 ON?}
    H -- no --> E
    H -- yes --> I[Tuple 빌드<br/>14개 컬럼 put]
    I --> J[tuplesByFab.add<br/>sourceByFab.add]
    J --> E

    E -.->|loop done| K[for each fab]
    K --> L[insertWithRetry<br/>최대 3회, 2s/4s/8s]
    L --> M{성공?}
    M -- yes --> N[로그: inserted N rows]
    M -- no --> O[mergeBack:<br/>다음 사이클 누적으로 합산]
    N --> P[HidInoutTibrvNotifier<br/>.notifyIfExceeded]
    P --> Q2[end fab loop]
    O --> Q2
    Q2 -.-> R[total log]
```

**기존 대비 핵심 차이:**

| 단계 | 기존 | 신규 |
|---|---|---|
| drain | `forEach` 후 `setEdgeInOutCountMap(new)` (그 사이 이벤트는 새 map으로) | `AtomicReference.getAndSet()` — 원자적 swap |
| blank fabId | `return` (전체 종료) | `continue` (해당 행만 skip) |
| insert 실패 | 손실 | 3회 백오프 → 그래도 실패 시 `mergeBack` |
| 알림 | 주석 처리 | `HidInoutTibrvNotifier` 호출 |

---

## 4. 키 구조: HidInoutEventKey

```mermaid
classDiagram
    class HidInoutEventKey {
        +int fromHidId
        +int toHidId
        +String fabId
        +String mcpName
        +String vhlFabId
        +String vhlId
        +String eqpId
        +equals(Object) boolean
        +hashCode() int
    }
    class HidInoutAggregate {
        -AtomicInteger transCnt
        -volatile int vhlCountLimit
        -volatile int vhlPrecaution
        -volatile double freeFlowSpeed
        -volatile int hidValue
        +incrementTransCnt()
        +updateSnapshot(int,int,double,int)
    }
    class HidInoutCollector {
        -AtomicReference bucketRef
        +recordTransition(...)
        +drain() Map
        +mergeBack(Map)
    }
    HidInoutCollector "1" --> "*" HidInoutEventKey : key
    HidInoutCollector "1" --> "*" HidInoutAggregate : value
```

기존: `"%03d:%03d:%s:%s:%s:%s:%s:%s:%s:%s:%s"` 11토큰 문자열 → `split(":")` 파싱
신규: 타입 안전 record-like class → 이름에 `:` 가 있어도 안전, `equals/hashCode` 명시

---

## 5. 일간 마스터 갱신: HidInoutMasterBatch

```mermaid
flowchart TD
    Q[Quartz cron<br/>0 30 2 * * ?] --> A[execute]
    A --> B[for each fab]
    B --> C{FabProperties<br/>null?}
    C -- yes --> B
    C -- no --> D[filterRailEdgesForFab<br/>fab + RailEdge만]
    D --> E{비어있음?}
    E -- yes --> B
    E -- no --> F[for each mcp]
    F --> G{HID_INOUT<br/>스위치 ON?}
    G -- no --> F
    G -- yes --> H[collectRawHidById<br/>id → RawHid 맵]

    H --> I[updateEdgeMaster]
    I --> I1[fromNodeId 인덱스 빌드<br/>O&#40;N&#41;]
    I1 --> I2[엣지 순회 → 다음 엣지의<br/>HID 와 비교, 다르면 전환]
    I2 --> I3[dedup&#58; fromHid:toHid]
    I3 --> I4[EDGE_TYPE 결정&#58;<br/>0→x = IN, x→0 = OUT,<br/>그 외 = INTERNAL]
    I4 --> I5[Tuple put → tuples 누적]
    I5 --> I6[Logpresso insert<br/>{FAB}_ATLAS_INFO_HID_INOUT_MAS]

    I6 --> J[updateHidInfoMaster]
    J --> J1[HID별 집계&#58;<br/>railLen 합계,<br/>maxVelocity 목록,<br/>portCnt 합계]
    J1 --> J2[RawHid에서<br/>VHL_MAX, ZCU_ID,<br/>IN_CNT, OUT_CNT]
    J2 --> J3[HID별 Tuple 빌드]
    J3 --> J4[Logpresso insert<br/>{FAB}_ATLAS_HID_INFO_MAS]

    J4 --> F
    F -.->|loop done| B
```

---

## 6. 임계치 알림: HidInoutTibrvNotifier

```mermaid
flowchart LR
    A[HidInoutAggregate<br/>flush row] --> B[ThresholdPolicy<br/>.evaluate]
    B --> C{limit &gt; 0 &amp;&amp;<br/>value &gt;= limit?}
    C -- yes --> D1[CRITICAL]
    C -- no --> E{warn &gt; 0 &amp;&amp;<br/>value &gt;= warn?}
    E -- yes --> D2[WARNING]
    E -- no --> D3[NONE]
    D3 --> X[no send]
    D1 --> F[Map 빌드:<br/>TYPE = OHT.HID.INOUT<br/>+ SEVERITY<br/>+ 14 fields]
    D2 --> F
    F --> G[DataService<br/>.getTibrvSenderLikeMap<br/>fabRouteId&#58;send&#58;amos]
    G --> H[for each sender<br/>addTibrvMessageQueue]
    H --> RV[(TibRV)]
```

`setThresholdPolicy(custom)` 으로 정책 교체 가능.

---

## 7. 동시성 모델

```mermaid
sequenceDiagram
    participant W1 as OHT Worker-1
    participant W2 as OHT Worker-2
    participant COL as HidInoutCollector<br/>(singleton)
    participant MAP as bucketRef<br/>(AtomicReference)
    participant FB as FlushBatch<br/>(Quartz thread)
    participant DB as Logpresso

    Note over W1,W2: 다수 OHT 메시지 동시 처리

    W1->>COL: recordTransition(prev=1, curr=2, ...)
    COL->>MAP: bucketRef.get()
    MAP-->>COL: ConcurrentHashMap M0
    COL->>M0: computeIfAbsent(key1).incrementTransCnt() [atomic]

    W2->>COL: recordTransition(prev=1, curr=2, ...) [same key]
    COL->>M0: computeIfAbsent(key1).incrementTransCnt() [atomic]
    Note over M0: transCnt = 2

    Note over FB: 1분 경과 trigger
    FB->>COL: drain()
    COL->>MAP: getAndSet(new ConcurrentHashMap M1)
    MAP-->>FB: 이전 M0 반환
    Note over MAP: 이제 bucketRef = M1

    W1->>COL: recordTransition(...) [new event during flush]
    COL->>MAP: get() → M1
    COL->>M1: increment [M0과 무관, 손실 없음]

    FB->>DB: setInsertTuples({FAB}_ATLAS_HID_INOUT, M0)
    DB-->>FB: ok
    Note over FB: M0은 GC 대상
```

**보장:**
- flush 진행 중 도착한 이벤트는 새 map(M1) 에 들어가므로 **이중 집계 없음**
- M0 직렬화 중에는 그 누구도 M0 을 수정하지 않으므로 **카운트 손실 없음**
- 실패 시 `mergeBack(M0)` 으로 M1 에 합쳐 다음 사이클 재시도

---

## 8. {FAB}_ATLAS_HID_INOUT 컬럼 매핑

```mermaid
flowchart LR
    subgraph KEY["HidInoutEventKey"]
        K1[fromHidId]
        K2[toHidId]
        K3[mcpName]
        K4[vhlFabId]
        K5[vhlId]
        K6[eqpId]
    end
    subgraph AGG["HidInoutAggregate"]
        A1[transCnt]
        A2[vhlCountLimit]
        A3[vhlPrecaution]
        A4[freeFlowSpeed]
        A5[hidValue]
    end
    subgraph TIME["Flush 시점"]
        T1[eventDate]
        T2[eventDt 분단위 절삭]
        T3[Env.getEnv]
    end
    subgraph TABLE["{FAB}_ATLAS_HID_INOUT"]
        C1[EVENT_DATE]
        C2[EVENT_DT]
        C3[FROM_HIDID]
        C4[TO_HIDID]
        C5[TRANS_CNT]
        C6[FAB_ID]
        C7[VHL_ID]
        C8[EQP_ID]
        C9[MCP_NM]
        C10[ENV]
        C11[VHL_COUNT_LIMIT]
        C12[VHL_PRECAUTION]
        C13[FREE_FLOW_SPEED]
        C14[HID_VALUE]
    end

    T1 --> C1
    T2 --> C2
    K1 --> C3
    K2 --> C4
    A1 --> C5
    K4 --> C6
    K5 --> C7
    K6 --> C8
    K3 --> C9
    T3 --> C10
    A2 --> C11
    A3 --> C12
    A4 --> C13
    A5 --> C14
```

---

## 9. 상태 전이 (전체 라이프사이클)

```mermaid
stateDiagram-v2
    [*] --> Idle: 시스템 부팅
    Idle --> Collecting: DataService.initialized=true
    Collecting --> Collecting: recordTransition()
    Collecting --> Flushing: Quartz 1분 trigger
    Flushing --> Inserting: drain() 성공
    Inserting --> Notifying: insert 성공
    Inserting --> Retrying: insert 실패
    Retrying --> Inserting: 백오프 후 재시도 (≤3)
    Retrying --> MergeBack: 3회 모두 실패
    MergeBack --> Collecting: 다음 사이클에 합산
    Notifying --> Collecting: tibrv 큐잉
    Collecting --> MasterUpdating: Quartz 일 1회 trigger
    MasterUpdating --> Collecting: 두 마스터 테이블 갱신
```

---

## 10. 파일 구조

```
ALT/hid_inout_new/
├── README.md                          # 사용 가이드
├── LOGIC_DIAGRAM.md                   # ← 이 파일
└── src/com/skhynix/smartatlas/hidinout/
    ├── HidInoutTableSchema.java       (95)   상수
    ├── HidInoutEventKey.java          (73)   키
    ├── HidInoutAggregate.java         (45)   누적치
    ├── HidInoutCollector.java         (187)  수집기
    ├── HidInoutFlushBatch.java        (155)  1분 적재
    ├── HidInoutMasterBatch.java       (301)  일 마스터 갱신
    └── HidInoutTibrvNotifier.java     (95)   임계치 알림
```
