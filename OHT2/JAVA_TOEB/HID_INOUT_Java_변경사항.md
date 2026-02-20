# HID IN/OUT 처리 Java 코드 변경 사항

## 개요
HID IN/OUT 엣지 기반 집계 기능을 **기존 코드에 추가**합니다.
- 기존: HID별 VHL 카운트 (유지)
- 추가: FROM_HIDID → TO_HIDID 엣지 전환 집계 (2009개 엣지)

---

# 테이블 스키마 정의

## 테이블 1: {FAB}_ATLAS_INFO_HID_INOUT_MAS

**용도**: HID Zone 진입/진출 엣지 마스터 데이터 (기준 정보) — 하루 1회 업데이트
**테이블명 예시**: `M14A_ATLAS_INFO_HID_INOUT_MAS`, `M16A_ATLAS_INFO_HID_INOUT_MAS`
**데이터 원본**: `map/{FAB}/*.layout.zip` → `layout.xml` (McpZone Entry/Exit 파싱)

| 컬럼명 | 타입 | 설명 | 데이터 소스 |
|--------|------|------|-------------|
| `FROM_HIDID` | INT | 출발 HID Zone ID | `layout.xml` McpZone Entry start/end 주소 → HID 매핑 |
| `TO_HIDID` | INT | 도착 HID Zone ID | `layout.xml` McpZone Exit start/end 주소 → HID 매핑 |
| `EDGE_ID` | STRING | 엣지 고유 ID (FROM:TO) | `String.format("%03d:%03d", fromHidId, toHidId)` |
| `FROM_HID_NM` | STRING | 출발 HID Zone 이름 | HID명 매핑 (`"HID_" + String.format("%03d", hidId)`) |
| `TO_HID_NM` | STRING | 도착 HID Zone 이름 | HID명 매핑 (`"HID_" + String.format("%03d", hidId)`) |
| `MCP_ID` | STRING | MCP ID | `this.mcpName` (OhtMsgWorkerRunnable.java:9) |
| `ZONE_ID` | STRING | Zone ID | 추후 매핑 가능 |
| `EDGE_TYPE` | STRING | 엣지 유형 | `fromHidId==0 ? "IN" : toHidId==0 ? "OUT" : "INTERNAL"` |
| `UPDATE_DT` | STRING | 마지막 업데이트 일시 | `SimpleDateFormat("yyyy-MM-dd HH:mm:ss")` |

---

## 테이블 2: {FAB}_ATLAS_HID_INFO_MAS

**용도**: HID 상세 정보 마스터 데이터 — 레일 길이, FREE FLOW 속도, 포트 개수 등
**테이블명 예시**: `M14A_ATLAS_HID_INFO_MAS`, `M16A_ATLAS_HID_INFO_MAS`
**데이터 원본**: RailEdge 런타임 데이터 집계 + `map/{FAB}/*.layout.zip`

| 컬럼명 | 타입 | 설명 | 데이터 소스 |
|--------|------|------|-------------|
| `HID_ID` | INT | HID Zone ID (PK) | `RailEdge.getHIDId()` (RaileEdge.java:324) |
| `HID_NM` | STRING | HID Zone 이름 | `"HID_" + String.format("%03d", hidId)` |
| `MCP_ID` | STRING | MCP ID | `this.mcpName` (OhtMsgWorkerRunnable.java:9) |
| `ZONE_ID` | STRING | Zone ID | 추후 매핑 가능 |
| `RAIL_LEN_TOTAL` | DOUBLE | 레일 길이 총합 (mm) | `RailEdge.getLength()` HID별 합계 (AbstractEdge 상속) |
| `FREE_FLOW_SPEED` | DOUBLE | FREE FLOW 속도 (mm/s) | `RailEdge.getMaxVelocity()` HID별 평균 (RaileEdge.java:270) |
| `PORT_CNT_TOTAL` | INT | 포트 개수 총합 | `RailEdge.getPortIdList().size()` HID별 합계 (RaileEdge.java:19) |
| `IN_CNT` | INT | IN Lane 개수 | `layout.xml` McpZone Entry 개수 (추후 매핑) |
| `OUT_CNT` | INT | OUT Lane 개수 | `layout.xml` McpZone Exit 개수 (추후 매핑) |
| `VHL_MAX` | INT | 최대 허용 차량 수 | `layout.xml` McpZone vehicle-max (추후 매핑) |
| `ZCU_ID` | STRING | ZCU ID | `layout.xml` Entry stop-zcu (추후 매핑) |
| `UPDATE_DT` | STRING | 마지막 업데이트 일시 | `SimpleDateFormat("yyyy-MM-dd HH:mm:ss")` |

---

## 테이블 3: {FAB}_ATLAS_HID_INOUT

**용도**: HID IN/OUT 1분 집계 데이터 — FABID별 테이블 분리
**테이블명 예시**: `M14A_ATLAS_HID_INOUT`, `M16A_ATLAS_HID_INOUT`

| 컬럼명 | 타입 | 설명 | 데이터 소스 |
|--------|------|------|-------------|
| `EVENT_DATE` | STRING | 이벤트 날짜 | `SimpleDateFormat("yyyy-MM-dd")` |
| `EVENT_DT` | STRING | 집계 시간 (1분 단위) | `SimpleDateFormat("yyyy-MM-dd HH:mm:00")` |
| `FROM_HIDID` | INT | 출발 HID Zone ID | `vehicle.getHidId()` (previousHidId) - Vhl.java:517 |
| `TO_HIDID` | INT | 도착 HID Zone ID | `currentHidId` 파라미터 - OhtMsgWorkerRunnable.java:357 |
| `TRANS_CNT` | INT | 1분간 전환 횟수 | `hidEdgeBuffer.get(edgeKey)` 집계값 |
| `MCP_NM` | STRING | MCP 이름 | `this.mcpName` - OhtMsgWorkerRunnable.java:9 |
| `ENV` | STRING | 환경 구분 | `Env.getEnv()` - OhtMsgWorkerRunnable.java:505 |

---

# Part 1: OhtMsgWorkerRunnable.java 변경

## 1.1 클래스 필드 추가

```java
// ===== 기존 코드 유지 =====

// ===== 신규 추가: HID 엣지별 전환 카운트 집계 (1분간 모아서 배치 저장) =====
// Key: "fromHidId:toHidId", Value: 전환 횟수
private static ConcurrentMap<String, Integer> hidEdgeBuffer =
    new ConcurrentHashMap<>();
private static long lastHidEdgeFlushTime = System.currentTimeMillis();
private static final long HID_EDGE_FLUSH_INTERVAL = 60000; // 1분
private static final Object hidEdgeFlushLock = new Object();
private static final Object hidEdgeBufferLock = new Object();
```

---

## 1.2 _calculatedVhlCnt() 메소드 수정

### 기존 코드 (OhtMsgWorkerRunnable.java:357-382)
```java
private void _calculatedVhlCnt(int currentHidId, String key, Vhl vehicle) {
    long timer = System.currentTimeMillis();
    int previousHidId = vehicle.getHidId();

    if (previousHidId != currentHidId) {
        if (currentHidId > 0) {
            String v = String.format("%03d", currentHidId);
            DataService.getDataSet().increaseHidVehicleCnt(key + ":" + v);
        }

        if (previousHidId > 0) {
            String v = String.format("%03d", previousHidId);
            DataService.getDataSet().decreaseHidVehicleCnt(key + ":" + v);
        }

        vehicle.setHidId(currentHidId);
    }

    long checkingTime = System.currentTimeMillis() - timer;

    if (checkingTime >= 60000) {
        logger.info("... `number of vehicles per hid section` process took more than 1 minute to complete [elapsed time: {}min]", checkingTime / 60000);
    }
}
```

### 변경 코드 (기존 유지 + 엣지 집계 추가)
```java
/**
 * HID 구간별 VHL 재적수
 * @param currentHidId 현재 vehicle 이 위치한 railEdge 의 hid 값
 * @param key DataSet 에서 특정 데이터를 호출하기 위한 key 값
 * @param vehicle vehicle 객체
 */
private void _calculatedVhlCnt(int currentHidId, String key, Vhl vehicle) {
    long timer = System.currentTimeMillis();
    int previousHidId = vehicle.getHidId();

    if (previousHidId != currentHidId) {
        // ===== 기존 코드 유지: HID VHL 카운트 =====
        if (currentHidId > 0) {
            String v = String.format("%03d", currentHidId);
            DataService.getDataSet().increaseHidVehicleCnt(key + ":" + v);
        }

        if (previousHidId > 0) {
            String v = String.format("%03d", previousHidId);
            DataService.getDataSet().decreaseHidVehicleCnt(key + ":" + v);
        }
        // ===== 기존 코드 유지 끝 =====

        // ===== 신규 추가: 엣지 전환 카운트 집계 =====
        String edgeKey = String.format("%03d:%03d", previousHidId, currentHidId);
        synchronized (hidEdgeBufferLock) {
            hidEdgeBuffer.merge(edgeKey, 1, Integer::sum);
        }
        // ===== 신규 추가 끝 =====

        vehicle.setHidId(currentHidId);
    }

    // ===== 신규 추가: 1분마다 버퍼 플러시 =====
    if (timer - lastHidEdgeFlushTime >= HID_EDGE_FLUSH_INTERVAL) {
        synchronized (hidEdgeFlushLock) {
            if (timer - lastHidEdgeFlushTime >= HID_EDGE_FLUSH_INTERVAL) {
                flushHidEdgeBuffer();
                lastHidEdgeFlushTime = timer;
            }
        }
    }
    // ===== 신규 추가 끝 =====

    long checkingTime = System.currentTimeMillis() - timer;

    if (checkingTime >= 60000) {
        logger.info("... `number of vehicles per hid section` process took more than 1 minute to complete [elapsed time: {}min]", checkingTime / 60000);
    }
}
```

---

## 1.3 flushHidEdgeBuffer() 메소드 신규 추가

```java
/**
 * HID 엣지 전환 집계 데이터를 Logpresso에 1분 배치 저장
 * 테이블: {FAB}_ATLAS_HID_INOUT (예: M14A_ATLAS_HID_INOUT)
 *
 * 컬럼:
 *   - EVENT_DATE: 이벤트 날짜 (파티션 키)
 *   - EVENT_DT: 집계 시간 (1분 단위)
 *   - FROM_HIDID: 출발 HID Zone ID
 *   - TO_HIDID: 도착 HID Zone ID
 *   - TRANS_CNT: 1분간 전환 횟수
 *   - MCP_NM: MCP 이름
 *   - ENV: 환경 구분
 */
private void flushHidEdgeBuffer() {
    if (hidEdgeBuffer.isEmpty()) {
        return;
    }

    // 버퍼 스냅샷 생성 및 초기화
    Map<String, Integer> snapshot = new HashMap<>();
    synchronized (hidEdgeBufferLock) {
        for (Map.Entry<String, Integer> entry : hidEdgeBuffer.entrySet()) {
            int count = entry.getValue();
            if (count > 0) {
                snapshot.put(entry.getKey(), count);
            }
        }
        hidEdgeBuffer.clear();
    }

    // 현재 시간 (1분 단위로 정렬)
    SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:00");
    SimpleDateFormat dateOnlyFormat = new SimpleDateFormat("yyyy-MM-dd");
    Date now = new Date();
    String eventDt = dateFormat.format(now);
    String eventDate = dateOnlyFormat.format(now);

    List<Tuple> tuples = new ArrayList<>();

    for (Map.Entry<String, Integer> entry : snapshot.entrySet()) {
        String[] hidIds = entry.getKey().split(":");
        int fromHidId = Integer.parseInt(hidIds[0]);
        int toHidId = Integer.parseInt(hidIds[1]);
        int transCnt = entry.getValue();

        Tuple tuple = new Tuple();
        tuple.put("EVENT_DATE", eventDate);
        tuple.put("EVENT_DT", eventDt);
        tuple.put("FROM_HIDID", fromHidId);
        tuple.put("TO_HIDID", toHidId);
        tuple.put("TRANS_CNT", transCnt);
        tuple.put("MCP_NM", this.mcpName);
        tuple.put("ENV", Env.getEnv());

        tuples.add(tuple);
    }

    if (tuples.isEmpty()) {
        return;
    }

    // FABID별 테이블에 저장 (예: M14A_ATLAS_HID_INOUT)
    String tableName = this.fabId + "_ATLAS_HID_INOUT";

    boolean success = LogpressoAPI.setInsertTuples(tableName, tuples, 100);

    if (success) {
        logger.info("HID Edge transitions aggregated: {} - {} records",
                    tableName, tuples.size());
    }
}
```

---

# Part 2: OhtMsgWorkerRunnable.java 마스터 테이블 업데이트 (통합)

> ※ 별도 HidMasterBatchJob.java 없이 **OhtMsgWorkerRunnable 내부에서 하루 1회 실행**
> ※ `_calculatedVhlCnt()` 에서 날짜 비교 → `_updateHidMasterTables()` 호출
> ※ `map/{FAB}/*.layout.zip` 없으면 SKIP + `logger.warn`

## 2.1 _updateHidMasterTables() — 마스터 업데이트 오케스트레이터

```java
/**
 * HID 마스터 테이블 업데이트 (하루 1회)
 * 데이터 소스: map/{FAB}/*.layout.zip 내 layout.xml
 */
private void _updateHidMasterTables() {
    logger.info("Starting HID Master Tables update [fab: {}]", this.fabId);

    FabProperties fabProperties = DataService.getInstance().getFabPropertiesMap().get(this.fabId);
    String mapDir = fabProperties.getMapDir();  // DataService.java:295
    File mapDirFile = new File(mapDir);

    if (!mapDirFile.exists() || !mapDirFile.isDirectory()) {
        logger.warn("[HID Master] map directory not found, SKIP [fab: {} | path: {}]", this.fabId, mapDir);
        return;
    }

    File[] layoutZipFiles = mapDirFile.listFiles((dir, name) -> name.endsWith(".layout.zip"));

    if (layoutZipFiles == null || layoutZipFiles.length == 0) {
        logger.warn("[HID Master] *.layout.zip not found, SKIP [fab: {} | path: {}]", this.fabId, mapDir);
        return;
    }

    File layoutZipFile = layoutZipFiles[0];
    logger.info("[HID Master] layout.zip found [fab: {} | file: {}]", this.fabId, layoutZipFile.getName());

    _updateHidEdgeMasterInfo(layoutZipFile);   // 테이블 1
    _updateHidInfoMaster();                     // 테이블 2

    logger.info("HID Master Tables update completed [fab: {}]", this.fabId);
}
```

---

## 2.2 _updateHidEdgeMasterInfo() — 테이블 1: {FAB}_ATLAS_INFO_HID_INOUT_MAS

```java
/**
 * HID Zone 진입/진출 엣지 마스터 데이터 업데이트
 * 테이블: {FAB}_ATLAS_INFO_HID_INOUT_MAS (예: M14A_ATLAS_INFO_HID_INOUT_MAS)
 *
 * 데이터 소스: DataService.getDataSet().getEdgeMap() → RailEdge HID 전환 감지
 */
private void _updateHidEdgeMasterInfo(File layoutZipFile) {
    // ... RailEdge 순회하며 HID 전환 엣지 추출 ...
    // 테이블명: this.fabId + "_ATLAS_INFO_HID_INOUT_MAS"
    // Full Refresh: truncateTable() → setInsertTuples()
}
```

> ※ 상세 구현 코드: `JAVA_TOEB/SRC/OhtMsgWorkerRunnable.java` 참조 (Line 261~357)

---

## 2.3 _updateHidInfoMaster() — 테이블 2: {FAB}_ATLAS_HID_INFO_MAS

```java
/**
 * HID 상세 정보 마스터 데이터 업데이트
 * 테이블: {FAB}_ATLAS_HID_INFO_MAS (예: M14A_ATLAS_HID_INFO_MAS)
 *
 * 데이터 소스:
 *   RAIL_LEN_TOTAL  → RailEdge.getLength() HID별 합계
 *   FREE_FLOW_SPEED → RailEdge.getMaxVelocity() HID별 평균
 *   PORT_CNT_TOTAL  → RailEdge.getPortIdList().size() 합계
 */
private void _updateHidInfoMaster() {
    // ... RailEdge 순회하며 HID별 집계 ...
    // 테이블명: this.fabId + "_ATLAS_HID_INFO_MAS"
    // Full Refresh: truncateTable() → setInsertTuples()
}
```

> ※ 상세 구현 코드: `JAVA_TOEB/SRC/OhtMsgWorkerRunnable.java` 참조 (Line 384~479)

---

# 변경 요약

## OhtMsgWorkerRunnable.java (모든 코드 통합)

| 구분 | 내용 |
|------|------|
| 기존 코드 | **유지** (HID VHL 카운트) |
| 신규 필드 | `hidEdgeBuffer`, `lastHidEdgeFlushTime`, `hidEdgeFlushLock`, `hidEdgeBufferLock` |
| 신규 필드 | `hidMasterUpdatedToday`, `hidMasterLastUpdateDate`, `hidMasterUpdateLock` |
| 수정 메소드 | `_calculatedVhlCnt()` (엣지 집계 + 1분 플러시 + 하루 1회 마스터 업데이트) |
| 신규 메소드 | `flushHidEdgeBuffer()` → `{FAB}_ATLAS_HID_INOUT` 저장 |
| 신규 메소드 | `_updateHidMasterTables()` → 마스터 업데이트 오케스트레이터 |
| 신규 메소드 | `_updateHidEdgeMasterInfo()` → `{FAB}_ATLAS_INFO_HID_INOUT_MAS` 저장 |
| 신규 메소드 | `_updateHidInfoMaster()` → `{FAB}_ATLAS_HID_INFO_MAS` 저장 |

## 신규 테이블 (FAB prefix)

| 테이블 | 테이블명 | 예시 |
|--------|---------|------|
| 테이블 1 | `{FAB}_ATLAS_INFO_HID_INOUT_MAS` | `M14A_ATLAS_INFO_HID_INOUT_MAS` |
| 테이블 2 | `{FAB}_ATLAS_HID_INFO_MAS` | `M14A_ATLAS_HID_INFO_MAS` |
| 테이블 3 | `{FAB}_ATLAS_HID_INOUT` | `M14A_ATLAS_HID_INOUT` |

## 참고 소스 코드

상세 구현 코드: `JAVA_TOEB/SRC/OhtMsgWorkerRunnable.java`

---