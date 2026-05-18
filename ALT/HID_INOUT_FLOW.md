# `{FAB}_ATLAS_HID_INOUT` 적재 로직 — 기존 코드 분석

`ALT/decoded_main/` 의 SmartAtlas 기존 소스가 `{FAB}_ATLAS_HID_INOUT`
(예: `M14A_ATLAS_HID_INOUT`) 테이블에 데이터를 어떻게 적재하는지에 대한
End-to-End 분석. **신규/제안 코드 없음** — 디코딩된 원본 그대로의 흐름.

---

## 0. 등장 인물

| 파일 | 위치 | 역할 |
|---|---|---|
| `OhtMsgWorkerRunnable.java` | `process/` | OHT UDP 메시지 처리 워커. HID 변경 감지 후 카운트 누적 |
| `Vhl.java` | `map/` | 차량 객체. `hidId` 필드 보유 (직전 HID) |
| `RailEdge.java` | `map/edge/` | 레일 엣지. `getHIDId()`, `getVelocity()` |
| `DataSet.java` | `data/` | 전역 인메모리 저장소. `edgeInOutCountMap` 보유 |
| `DataService.java` | `util/` | DataSet 접근 게이트웨이, FabPropertiesMap, hidVehicleCountMap |
| `RawHid.java` | `data/raw/` | layout.xml 의 HID 정의 (vhlMax, vhlPreCaution) |
| `FunctionItem.java` | `environment/type/` | fab+mcp 별 기능 스위치 (`HID_INOUT` 포함) |
| `HidEdgeInOutQueueFlushBatch.java` | `batch/` | Quartz Job. 분단위로 map drain → Logpresso insert |
| `LogpressoAPI.java` | `db/logpresso/` | Logpresso bulk insert wrapper |
| `Env.java` | `environment/` | `getEnv()`, `getSwitchMap()` |

---

## 1. 전체 아키텍처

```mermaid
flowchart LR
    subgraph A["1) 실시간 수집 (OHT 워커 스레드)"]
        UDP[OHT UDP<br/>VHL_STATE_REPORT]
        OMW[OhtMsgWorkerRunnable<br/>_updateVehicle]
        PHI[_processHidInout]
    end

    subgraph B["2) 인메모리 누적 (DataSet)"]
        EMAP[(edgeInOutCountMap<br/>ConcurrentHashMap&lt;String, Integer&gt;)]
    end

    subgraph C["3) 1분 배치 (Quartz)"]
        FLUSH[HidEdgeInOutQueueFlushBatch.execute]
    end

    subgraph D["4) Logpresso 적재"]
        TBL[("{FAB}_ATLAS_HID_INOUT")]
    end

    UDP --> OMW --> PHI --> EMAP
    EMAP -- "1분마다 drain" --> FLUSH --> TBL
```

---

## 2. 단계 1 — 실시간 수집: `_processHidInout()`

**위치:** `OhtMsgWorkerRunnable.java:473-522`
**호출 조건:** `OhtMsgWorkerRunnable.java:310` — `functionItem.getUseFunction(FunctionType.HID_INOUT)` 가 true 일 때

```mermaid
flowchart TD
    A[UDP 메시지 수신] --> B[_updateVehicle]
    B --> C[railEdge = edgeMap.get railEdgeId]
    C --> D["hidId = railEdge.getHIDId<br/>OhtMsgWorkerRunnable:301"]
    D --> E["functionItem 조회<br/>Env.getSwitchMap.get fabId:mcpName"]
    E --> F{HID_INOUT<br/>스위치 ON?}
    F -- no --> X[skip]
    F -- yes --> G[_processHidInout 호출]

    G --> H["previousHidId = vehicle.getHidId<br/>OhtMsgWorker:474"]
    H --> I{previousHidId<br/>!= currentHidId?}
    I -- no --> X
    I -- yes --> J["vhlName, eqpName 추출<br/>: 마지막 토큰"]
    J --> K["McpProperties → Mcp75Config<br/>→ RawHidMap 순회"]
    K --> L["일치하는 hid의<br/>vhlCountLimit, vhlPrecaution 획득"]
    L --> M["edgeMap 전체 순회<br/>HID==currentHidId 인 RailEdge의<br/>velocity 평균 = freeFlowSpeed"]
    M --> N["hidVehicleCountMap.get<br/>fab:mcp:%03d hidId = hidValue"]
    N --> O["edgeKey 문자열 생성 11필드<br/>구분자 :"]
    O --> P["edgeInOutCountMap.merge<br/>edgeKey, 1, Integer::sum"]
    P --> END[end]

    note1[vehicle.setHidId currentHidId 는<br/>_calculatedVhlCnt 안에서 수행됨]
```

### 2.1 `edgeKey` 문자열 포맷 (11개 필드, `:` 구분)

`OhtMsgWorkerRunnable.java:515-517`:

```java
String edgeKey = String.format("%03d:%03d:%s:%s:%s:%s:%s:%s:%s:%s:%s",
        previousHidId, currentHidId, this.fabId, this.mcpName,
        vehicle.getFabId(), vhlName, eqpName,
        vhlCountLimit, vhlPrecaution, freeFlowSpeed, hidValue);
```

| 인덱스 | 필드 | 출처 |
|---|---|---|
| 0 | `previousHidId` (zero-pad 3) | `vehicle.getHidId()` (갱신 전 값) |
| 1 | `currentHidId` (zero-pad 3) | `railEdge.getHIDId()` |
| 2 | `fabId` | 워커의 fab (`this.fabId`) |
| 3 | `mcpName` | 워커의 mcp (`this.mcpName`) |
| 4 | `vhlFabId` | `vehicle.getFabId()` (DB에 적재되는 FAB_ID) |
| 5 | `vhlName` | `vehicle.getId()` 의 `:` 뒤 토큰 |
| 6 | `eqpName` | `vehicle.getEqpId()` 의 `:` 뒤 토큰 |
| 7 | `vhlCountLimit` | `RawHid.getVhlMax()` |
| 8 | `vhlPrecaution` | `RawHid.getVhlPreCaution()` |
| 9 | `freeFlowSpeed` | 현재 HID RailEdge 들의 `velocity` 평균 |
| 10 | `hidValue` | `hidVehicleCountMap[fab:mcp:%03d]` |

### 2.2 보조값 계산 상세

**`vhlCountLimit` / `vhlPrecaution`** — `OhtMsgWorkerRunnable.java:484-495`

```mermaid
flowchart LR
    A[this.fabId] --> B[DataService.getFabPropertiesMap<br/>.get fabId]
    B --> C[FabProperties]
    C --> D[.getMcpPropertiesMap<br/>.get this.mcpName]
    D --> E[McpProperties]
    E --> F[.getMcp75Config<br/>.getRawHidMap]
    F --> G[for each RawHid]
    G --> H{rawHid.getId<br/>== currentHidId?}
    H -- yes --> I["vhlCountLimit = rawHid.getVhlMax<br/>vhlPrecaution = rawHid.getVhlPreCaution<br/>break"]
    H -- no --> G
```

**`freeFlowSpeed`** — `OhtMsgWorkerRunnable.java:498-509`

```mermaid
flowchart LR
    A["DataService.getDataSet<br/>.getEdgeMap.values"] --> B[for each AbstractEdge]
    B --> C{instanceof RailEdge?}
    C -- no --> B
    C -- yes --> D{re.getHIDId<br/>== currentHidId<br/>&& re.getVelocity &gt; 0?}
    D -- no --> B
    D -- yes --> E["sumVelocity += velocity<br/>velCount++"]
    E --> B
    B -.->|loop end| F{velCount &gt; 0?}
    F -- yes --> G[freeFlowSpeed = sum / velCount]
    F -- no --> H[freeFlowSpeed = 0.0]
```

**`hidValue`** — `OhtMsgWorkerRunnable.java:512-513`

```java
String hidKey = this.fabId + ":" + this.mcpName + ":" + String.format("%03d", currentHidId);
int hidValue = DataService.getDataSet().getHidVehicleCountMap().getOrDefault(hidKey, 0);
```

`hidVehicleCountMap` 은 `_calculatedVhlCnt()` (`VHL_CNT` 스위치) 에서
HID 진입/이탈에 따라 증감되는 별도 맵.

### 2.3 카운트 누적 — `DataSet.edgeInOutCountMap`

```mermaid
sequenceDiagram
    participant W1 as OHT Worker-1
    participant W2 as OHT Worker-2
    participant MAP as edgeInOutCountMap<br/>(ConcurrentHashMap)

    W1->>MAP: merge edgeKey_A, 1, Integer::sum
    Note over MAP: edgeKey_A → 1
    W2->>MAP: merge edgeKey_A, 1, Integer::sum
    Note over MAP: edgeKey_A → 2
    W1->>MAP: merge edgeKey_B, 1, Integer::sum
    Note over MAP: edgeKey_B → 1
```

`DataSet.java:116` :
```java
private ConcurrentHashMap<String, Integer> edgeInOutCountMap = new ConcurrentHashMap<>();
```
- 키: 위 11필드 문자열
- 값: 누적 전환 횟수
- `merge(k, 1, Integer::sum)` 으로 동시성 안전하게 증가

---

## 3. 단계 2 — 1분 배치: `HidEdgeInOutQueueFlushBatch.execute()`

**위치:** `HidEdgeInOutQueueFlushBatch.java:31-141`
**트리거:** Quartz Job (운영 cron 별도 등록)

```mermaid
flowchart TD
    Q[Quartz trigger] --> A[execute]
    A --> B{DataService<br/>initialized?}
    B -- no --> X1[return]
    B -- yes --> C["copyMap = HashMap 생성"]
    C --> D["edgeInOutCountMap.forEach:<br/>copyMap.put new String k, v.intValue<br/>(라인 40-42)"]
    D --> E["setEdgeInOutCountMap<br/>new ConcurrentHashMap<br/>(라인 44)"]
    E --> F["now 시각으로<br/>eventDt yyyy-MM-dd HH:mm:00<br/>eventDate yyyy-MM-dd 포맷"]
    F --> G["fabIdTuples = HashMap"]
    G --> H[for each copyMap entry]

    H --> I["key.split : 11토큰"]
    I --> J[Tuple 생성<br/>14개 컬럼 put]
    J --> K["fabIdTuples.computeIfAbsent fabId<br/>.add tuple"]
    K --> H

    H -.->|loop done| L[for each fabIdTuples entry]
    L --> M{fabId<br/>blank?}
    M -- yes --> XBlankReturn["return ⚠ 전체 종료<br/>HidEdgeInOutQueueFlushBatch:128-130"]
    M -- no --> N["tableName = fabId +<br/>_ATLAS_HID_INOUT"]
    N --> O["LogpressoAPI.setInsertTuples<br/>tableName, tuples, 100"]
    O --> P{success?}
    P -- yes --> Q1[log info: N records]
    P -- no --> Q2[no-op<br/>로그도 없음]
    Q1 --> L
    Q2 --> L
```

### 3.1 Tuple 빌드 (라인 72-86)

```java
Tuple tuple = new Tuple();
tuple.put("EVENT_DATE",       eventDate);     // yyyy-MM-dd
tuple.put("EVENT_DT",         eventDt);       // yyyy-MM-dd HH:mm:00
tuple.put("FROM_HIDID",       fromHidId);     // parts[0]
tuple.put("TO_HIDID",         toHidId);       // parts[1]
tuple.put("TRANS_CNT",        transCnt);      // entry.getValue()
tuple.put("FAB_ID",           vhlFabId);      // parts[4] (차량의 fab)
tuple.put("VHL_ID",           vhlId);         // parts[5]
tuple.put("EQP_ID",           eqpId);         // parts[6]
tuple.put("MCP_NM",           mcpName);       // parts[3]
tuple.put("ENV",              Env.getEnv());
tuple.put("VHL_COUNT_LIMIT",  vhlCountLimit); // parts[7]
tuple.put("VHL_PRECAUTION",   vhlPrecaution); // parts[8]
tuple.put("FREE_FLOW_SPEED",  freeFlowSpeed); // parts[9]
tuple.put("HID_VALUE",        hidValue);      // parts[10]
```

⚠ `fabId` 그루핑 키는 `parts[2]` (워커의 fab), DB 적재 컬럼 `FAB_ID` 는 `parts[4]` (차량의 fab). **두 값이 다를 수 있음.**

### 3.2 `{FAB}_ATLAS_HID_INOUT` 컬럼 매핑 표

| DB 컬럼 | 타입 | 출처 (edgeKey 파싱 후) | 비고 |
|---|---|---|---|
| `EVENT_DATE` | string | flush 시각 | `yyyy-MM-dd` |
| `EVENT_DT` | string | flush 시각 | `yyyy-MM-dd HH:mm:00` (분 단위로 절삭) |
| `FROM_HIDID` | int | `parts[0]` | 직전 HID (0 = OUTSIDE) |
| `TO_HIDID` | int | `parts[1]` | 현재 HID |
| `TRANS_CNT` | int | `entry.getValue()` | 1분 누적 전환 횟수 |
| `FAB_ID` | string | `parts[4]` | `vehicle.getFabId()` — 차량 소속 FAB |
| `VHL_ID` | string | `parts[5]` | 차량 short name |
| `EQP_ID` | string | `parts[6]` | 설비 short name |
| `MCP_NM` | string | `parts[3]` | MCP 이름 |
| `ENV` | string | `Env.getEnv()` | 실행 환경 |
| `VHL_COUNT_LIMIT` | int | `parts[7]` | RawHid.vhlMax |
| `VHL_PRECAUTION` | int | `parts[8]` | RawHid.vhlPreCaution |
| `FREE_FLOW_SPEED` | double | `parts[9]` | 현 HID 평균 속도 |
| `HID_VALUE` | int | `parts[10]` | 현 HID 차량 수 |

### 3.3 적재 — `LogpressoAPI.setInsertTuples`

`HidEdgeInOutQueueFlushBatch.java:135`:
```java
String tableName = fabId + "_ATLAS_HID_INOUT";
boolean success = LogpressoAPI.setInsertTuples(tableName, tuples, 100);
```
- 테이블명 prefix = **워커의 fabId** (`parts[2]`)
- 배치 크기 100 tuple

---

## 4. 동시성 — drain 의 race window

```mermaid
sequenceDiagram
    participant W as OHT Worker
    participant DS as DataSet
    participant FB as FlushBatch

    Note over W,FB: t=0 ~ t=60s: 정상 누적
    W->>DS: edgeInOutCountMap.merge keyA, 1
    Note over DS: keyA=1

    Note over FB: t=60s flush 시작
    FB->>DS: getEdgeInOutCountMap.forEach
    DS-->>FB: keyA=1 (복사)

    Note over W,DS: ⚠ race window
    W->>DS: edgeInOutCountMap.merge keyA, 1
    Note over DS: keyA=2 (구 map에 들어감)

    FB->>DS: setEdgeInOutCountMap new ConcurrentHashMap
    Note over DS: 새 map으로 교체

    W->>DS: edgeInOutCountMap.merge keyA, 1
    Note over DS: 새 map keyA=1

    FB->>FB: copyMap = keyA:1 만 가짐
    Note over FB: ⚠ 위 race window 의<br/>+1 은 copyMap에 누락
```

**관찰:** forEach 가 완전히 끝나기 전에 들어오는 증가분은 옛 map 에 들어가지만,
forEach 가 끝난 직후 `setEdgeInOutCountMap(new ...)` 이전에 들어오는 증가분도
옛 map 에 들어가며, **이는 copyMap 에 반영되지 않은 채 GC 됨.**
운영상 대규모 손실은 아니지만 정확한 카운트 보장은 없음.

---

## 5. 빈 fabId 처리의 함정

`HidEdgeInOutQueueFlushBatch.java:124-130`:

```java
for (var entry : fabIdTuples.entrySet()) {
    var fabId = entry.getKey();
    var tuples = entry.getValue();

    if (Strings.isBlank(fabId)) {
        return;          // ⚠ continue 가 아닌 return
    }
    ...
}
```

```mermaid
flowchart TD
    A[fabIdTuples 정렬되지 않은 HashMap] --> B[iterator]
    B --> C[fab1 → insert OK]
    C --> D[blank → return]
    D --> X[fab2, fab3 ...<br/>모두 처리되지 않음 ⚠]
```

`HashMap` 의 iteration 순서는 비결정적이므로, **blank fabId 가 어디서 등장하느냐에
따라 그 뒤의 정상 FAB 들이 통째로 누락**될 수 있음.

---

## 6. `HID_INOUT` 스위치 흐름

```mermaid
flowchart LR
    A["Env.getSwitchMap<br/>Map fabId:mcpName, FunctionItem"] --> B[FunctionItem]
    B --> C[getUseFunction FunctionType.HID_INOUT]
    C --> D[useHidInout boolean]

    subgraph CHECK1["수집 단계 체크"]
        D1["OhtMsgWorkerRunnable:310"]
    end
    subgraph CHECK2["배치는 무조건 실행"]
        D2["HidEdgeInOutQueueFlushBatch 는<br/>스위치 검사 없음 ⚠"]
    end

    D --> CHECK1
```

**관찰:** flush 배치는 스위치를 검사하지 않으므로, 누군가 우회 경로로
`edgeInOutCountMap` 에 키를 넣어두면 스위치 OFF 인 mcp 의 데이터도 적재됨.
실제로는 `_processHidInout` 만 이 맵에 쓰므로 문제 없지만, 코드상 명시적
방어는 없음.

---

## 7. 1분 사이클 타임라인

```mermaid
gantt
    title 1분 사이클의 데이터 흐름
    dateFormat HH:mm:ss
    axisFormat %H:%M:%S

    section OHT 워커들
    이벤트 수집 (continuous)         :active, w, 00:00:00, 120s

    section DataSet
    edgeInOutCountMap 누적           :active, m1, 00:00:00, 60s
    새 map (다음 사이클)             :m2, 00:01:00, 60s

    section Flush 배치
    drain & insert                   :crit, f1, 00:01:00, 2s

    section Logpresso
    EVENT_DT = 00:01:00 적재        :crit, db1, 00:01:01, 1s
```

- `EVENT_DT` 는 **flush 실행 시각의 분 단위 절삭값**이므로 실제 이벤트 발생
  시점과 최대 ~60초 차이 존재
- `TRANS_CNT` 는 직전 1분 동안의 전환 횟수 (정확히는 직전 drain 이후)

---

## 8. 데이터 예시

차량 `M14A:OHT:0123` 이 1분 동안 HID 5→7 로 3번 전환 (왕복) 했다고 가정:

**edgeKey 예** (`OhtMsgWorkerRunnable:515` 포맷 적용):
```
005:007:M14A:MCP01:M14A:0123:EQP07:50:40:1.85:8
```

**1분 후 flush 결과:** `M14A_ATLAS_HID_INOUT` 에 1행 insert:

| EVENT_DATE | EVENT_DT | FROM_HIDID | TO_HIDID | TRANS_CNT | FAB_ID | VHL_ID | EQP_ID | MCP_NM | ENV | VHL_COUNT_LIMIT | VHL_PRECAUTION | FREE_FLOW_SPEED | HID_VALUE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-05-18 | 2026-05-18 09:23:00 | 5 | 7 | 3 | M14A | 0123 | EQP07 | MCP01 | PROD | 50 | 40 | 1.85 | 8 |

7→5 방향(역방향) 전환은 **별개 row** 로 적재됨 (`FROM_HIDID`/`TO_HIDID` 가
키의 일부이므로).

---

## 9. 호출 그래프 (요약)

```mermaid
flowchart TD
    UDP[OHT UDP 수신] --> OMW[OhtMsgWorkerRunnable<br/>.handleMessage]
    OMW --> UV[_updateVehicle]
    UV --> BR[_buildRailVelocity]
    UV --> SW{HID_INOUT<br/>switch?}
    SW -- yes --> PHI[_processHidInout]
    PHI --> DS[(DataSet<br/>edgeInOutCountMap)]
    PHI -.reads.-> FP[FabProperties<br/>→ McpProperties<br/>→ Mcp75Config<br/>→ RawHidMap]
    PHI -.reads.-> EM[DataSet.edgeMap<br/>RailEdge.velocity]
    PHI -.reads.-> HVC[DataSet.hidVehicleCountMap]

    Q[Quartz Scheduler] --> FLUSH[HidEdgeInOutQueueFlushBatch<br/>.execute]
    DS -.drain.-> FLUSH
    FLUSH --> LOG[LogpressoAPI<br/>.setInsertTuples]
    LOG --> TBL[("{FAB}_ATLAS_HID_INOUT")]
```

---

## 10. 라인 번호 인덱스

| 동작 | 파일:라인 |
|---|---|
| HID_INOUT 스위치 분기 | `OhtMsgWorkerRunnable.java:310` |
| `_processHidInout` 정의 | `OhtMsgWorkerRunnable.java:473` |
| HID 변경 검사 | `OhtMsgWorkerRunnable.java:474, 477` |
| vhl/eqp short name 추출 | `OhtMsgWorkerRunnable.java:478-481` |
| RawHid 매칭 (limit/precaution) | `OhtMsgWorkerRunnable.java:484-495` |
| freeFlowSpeed 계산 | `OhtMsgWorkerRunnable.java:498-509` |
| hidValue 조회 | `OhtMsgWorkerRunnable.java:512-513` |
| edgeKey 포맷 | `OhtMsgWorkerRunnable.java:515-517` |
| `edgeInOutCountMap.merge` | `OhtMsgWorkerRunnable.java:519-520` |
| `edgeInOutCountMap` 필드 선언 | `DataSet.java:116` |
| flush copy & swap | `HidEdgeInOutQueueFlushBatch.java:38-46` |
| Tuple put 14컬럼 | `HidEdgeInOutQueueFlushBatch.java:72-86` |
| fabId 그룹핑 | `HidEdgeInOutQueueFlushBatch.java:88-92` |
| 빈 fabId → return | `HidEdgeInOutQueueFlushBatch.java:128-130` |
| 테이블명 조합 | `HidEdgeInOutQueueFlushBatch.java:132-133` |
| Logpresso insert | `HidEdgeInOutQueueFlushBatch.java:135` |
| tibrv 송신 (주석 처리) | `HidEdgeInOutQueueFlushBatch.java:96-121` |
