# HID IN/OUT 처리 Java 코드 변경 사항

## 개요
HID IN/OUT 처리를 엣지 기반으로 변경하여 부하를 최적화합니다.
- 기존: HID별 IN/OUT 카운트 개별 저장
- 변경: FROM_HIDID → TO_HIDID 엣지 전환만 추적 (약 2010개 엣지)

### 테이블 변경 요약

| 테이블명 | 상태 | 용도 |
|----------|------|------|
| `ATLAS_INFO_HID_INOUT` | 삭제 | 기존 HID 마스터 |
| `ATLAS_INFO_HID_INOUT_MAS` | 신규 | 엣지 마스터 (FROM/TO HID) |
| `ATLAS_HID_INFO_MAS` | 신규 | HID 상세 정보 |
| `ATLAS_{FAB}_HID_INOUT` | 변경 | 엣지 전환 집계 (1분 배치) |

---

# Part 1: OhtMsgWorkerRunnable.java 변경

## 1.1 클래스 필드 변경

### 기존 코드 (삭제)
```java
// HID별 IN/OUT 카운트 집계 (1분간 모아서 배치 저장)
// Key: HID_ID, Value: [IN_CNT, OUT_CNT]
private static ConcurrentMap<Integer, int[]> hidCountBuffer =
    new ConcurrentHashMap<>();
```

### 변경 코드 (추가)
```java
import java.util.concurrent.atomic.AtomicInteger;

// HID 엣지별 전환 카운트 집계 (1분간 모아서 배치 저장)
// Key: "fromHidId:toHidId", Value: 전환 횟수
private static ConcurrentMap<String, AtomicInteger> hidEdgeBuffer =
    new ConcurrentHashMap<>();
private static long lastFlushTime = System.currentTimeMillis();
private static final long FLUSH_INTERVAL = 60000; // 1분
private static final Object flushLock = new Object();
```

---

## 1.2 _calculatedVhlCnt() 메소드 수정

### 기존 코드
```java
private void _calculatedVhlCnt(int currentHidId, String key, Vhl vehicle) {
    long timer = System.currentTimeMillis();
    int previousHidId = vehicle.getHidId();

    if (previousHidId != currentHidId) {
        // HID 구간 IN (새로운 HID 구간 진입)
        if (currentHidId > 0) {
            String v = String.format("%03d", currentHidId);
            DataService.getDataSet().increaseHidVehicleCnt(key + ":" + v);

            // IN 카운트 증가
            hidCountBuffer.computeIfAbsent(currentHidId, k -> new int[2]);
            synchronized (hidCountBuffer.get(currentHidId)) {
                hidCountBuffer.get(currentHidId)[0]++; // IN_CNT 증가
            }
        }

        // HID 구간 OUT (이전 HID 구간 이탈)
        if (previousHidId > 0) {
            String v = String.format("%03d", previousHidId);
            DataService.getDataSet().decreaseHidVehicleCnt(key + ":" + v);

            // OUT 카운트 증가
            hidCountBuffer.computeIfAbsent(previousHidId, k -> new int[2]);
            synchronized (hidCountBuffer.get(previousHidId)) {
                hidCountBuffer.get(previousHidId)[1]++; // OUT_CNT 증가
            }
        }

        vehicle.setHidId(currentHidId);
    }

    // 1분마다 버퍼 플러시
    if (timer - lastFlushTime >= FLUSH_INTERVAL) {
        synchronized (flushLock) {
            if (timer - lastFlushTime >= FLUSH_INTERVAL) {
                flushHidCountBuffer();
                lastFlushTime = timer;
            }
        }
    }
}
```

### 변경 코드
```java
private void _calculatedVhlCnt(int currentHidId, String key, Vhl vehicle) {
    long timer = System.currentTimeMillis();
    int previousHidId = vehicle.getHidId();

    if (previousHidId != currentHidId) {
        // HID 전환 감지 (엣지 이벤트)

        // 기존 HID VHL 카운트 업데이트
        if (currentHidId > 0) {
            String v = String.format("%03d", currentHidId);
            DataService.getDataSet().increaseHidVehicleCnt(key + ":" + v);
        }
        if (previousHidId > 0) {
            String v = String.format("%03d", previousHidId);
            DataService.getDataSet().decreaseHidVehicleCnt(key + ":" + v);
        }

        // ===== 변경: 엣지 전환 카운트 증가 =====
        String edgeKey = String.format("%03d:%03d", previousHidId, currentHidId);
        hidEdgeBuffer.computeIfAbsent(edgeKey, k -> new AtomicInteger(0))
                     .incrementAndGet();

        vehicle.setHidId(currentHidId);
    }

    // 1분마다 버퍼 플러시
    if (timer - lastFlushTime >= FLUSH_INTERVAL) {
        synchronized (flushLock) {
            if (timer - lastFlushTime >= FLUSH_INTERVAL) {
                flushHidEdgeBuffer();  // 메소드명 변경
                lastFlushTime = timer;
            }
        }
    }
}
```

---

## 1.3 flushHidCountBuffer() → flushHidEdgeBuffer() 변경

### 기존 코드 (삭제)
```java
private void flushHidCountBuffer() {
    if (hidCountBuffer.isEmpty()) {
        return;
    }

    Map<Integer, int[]> snapshot = new HashMap<>();
    for (Map.Entry<Integer, int[]> entry : hidCountBuffer.entrySet()) {
        synchronized (entry.getValue()) {
            snapshot.put(entry.getKey(),
                new int[]{entry.getValue()[0], entry.getValue()[1]});
            entry.getValue()[0] = 0;
            entry.getValue()[1] = 0;
        }
    }

    SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:00");
    SimpleDateFormat dateOnlyFormat = new SimpleDateFormat("yyyy-MM-dd");
    Date now = new Date();
    String eventDt = dateFormat.format(now);
    String eventDate = dateOnlyFormat.format(now);

    List<Tuple> tuples = new ArrayList<>();

    for (Map.Entry<Integer, int[]> entry : snapshot.entrySet()) {
        int hidId = entry.getKey();
        int inCnt = entry.getValue()[0];
        int outCnt = entry.getValue()[1];

        if (inCnt == 0 && outCnt == 0) {
            continue;
        }

        String hidKey = this.fabId + ":" + this.mcpName
                      + ":" + String.format("%03d", hidId);
        int vhlCnt = DataService.getDataSet().getHidVehicleCnt(hidKey);

        Tuple tuple = new Tuple();
        tuple.put("EVENT_DATE", eventDate);
        tuple.put("EVENT_DT", eventDt);
        tuple.put("HID_ID", hidId);
        tuple.put("IN_CNT", inCnt);
        tuple.put("OUT_CNT", outCnt);
        tuple.put("VHL_CNT", vhlCnt);
        tuple.put("MCP_NM", this.mcpName);
        tuple.put("ENV", Env.getEnv());

        tuples.add(tuple);
    }

    if (tuples.isEmpty()) {
        return;
    }

    String tableName = "ATLAS_" + this.fabId + "_HID_INOUT";
    boolean success = LogpressoAPI.setInsertTuples(tableName, tuples, 100);

    if (success) {
        logger.info("HID IN/OUT aggregated: {} - {} records",
                    tableName, tuples.size());
    }
}
```

### 변경 코드 (추가)
```java
/**
 * HID 엣지 전환 집계 데이터를 Logpresso에 1분 배치 저장
 * 테이블: ATLAS_{FABID}_HID_INOUT
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
    for (Map.Entry<String, AtomicInteger> entry : hidEdgeBuffer.entrySet()) {
        int count = entry.getValue().getAndSet(0);
        if (count > 0) {
            snapshot.put(entry.getKey(), count);
        }
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
        tuple.put("FROM_HIDID", fromHidId);   // 신규 컬럼
        tuple.put("TO_HIDID", toHidId);       // 신규 컬럼
        tuple.put("TRANS_CNT", transCnt);     // 컬럼명 변경 (IN_CNT/OUT_CNT → TRANS_CNT)
        tuple.put("MCP_NM", this.mcpName);
        tuple.put("ENV", Env.getEnv());

        tuples.add(tuple);
    }

    if (tuples.isEmpty()) {
        return;
    }

    // FABID별 테이블에 저장
    String tableName = "ATLAS_" + this.fabId + "_HID_INOUT";

    boolean success = LogpressoAPI.setInsertTuples(tableName, tuples, 100);

    if (success) {
        logger.info("HID Edge transitions aggregated: {} - {} records",
                    tableName, tuples.size());
    }
}
```

---

# Part 2: HidMasterBatchJob.java 변경

## 2.1 테이블명 변경

### 기존
```java
LogpressoAPI.truncateTable("ATLAS_INFO_HID_INOUT");
LogpressoAPI.setInsertTuples("ATLAS_INFO_HID_INOUT", tuples, 100);
```

### 변경
```java
LogpressoAPI.truncateTable("ATLAS_INFO_HID_INOUT_MAS");
LogpressoAPI.setInsertTuples("ATLAS_INFO_HID_INOUT_MAS", tuples, 100);
```

---

## 2.2 updateHidEdgeMasterInfo() 메소드 (엣지 기반 마스터)

```java
/**
 * HID Zone 진입/진출 엣지 마스터 데이터 업데이트
 * 테이블: ATLAS_INFO_HID_INOUT_MAS
 *
 * 컬럼:
 *   - FROM_HIDID: 출발 HID Zone ID
 *   - TO_HIDID: 도착 HID Zone ID
 *   - EDGE_ID: 엣지 고유 ID (FROM:TO)
 *   - FROM_HID_NM: 출발 HID Zone 이름
 *   - TO_HID_NM: 도착 HID Zone 이름
 *   - MCP_ID: MCP ID
 *   - ZONE_ID: Zone ID
 *   - EDGE_TYPE: 엣지 유형 (IN/OUT/INTERNAL)
 *   - UPDATE_DT: 마지막 업데이트 일시
 */
@Scheduled(cron = "0 0 0 * * ?")
public void updateHidEdgeMasterInfo() {
    String xmlPath = "/path/to/LAYOUT.XML";
    List<Tuple> tuples = new ArrayList<>();
    SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
    String updateDt = dateFormat.format(new Date());

    try {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        DocumentBuilder builder = factory.newDocumentBuilder();
        Document doc = builder.parse(new File(xmlPath));
        doc.getDocumentElement().normalize();

        // HID 정보 맵 구성
        Map<Integer, Element> hidMap = new HashMap<>();
        NodeList hidList = doc.getElementsByTagName("HID");
        for (int i = 0; i < hidList.getLength(); i++) {
            Element hid = (Element) hidList.item(i);
            int hidId = Integer.parseInt(hid.getAttribute("id"));
            hidMap.put(hidId, hid);
        }

        // 엣지 정보 파싱 (HID 간 연결)
        NodeList edgeList = doc.getElementsByTagName("EDGE");
        for (int i = 0; i < edgeList.getLength(); i++) {
            Element edge = (Element) edgeList.item(i);

            int fromHidId = Integer.parseInt(edge.getAttribute("fromHidId"));
            int toHidId = Integer.parseInt(edge.getAttribute("toHidId"));

            Tuple tuple = new Tuple();
            tuple.put("FROM_HIDID", fromHidId);
            tuple.put("TO_HIDID", toHidId);
            tuple.put("EDGE_ID", String.format("%03d:%03d", fromHidId, toHidId));

            // FROM HID 이름
            if (fromHidId == 0) {
                tuple.put("FROM_HID_NM", "OUTSIDE");
            } else if (hidMap.containsKey(fromHidId)) {
                tuple.put("FROM_HID_NM", hidMap.get(fromHidId).getAttribute("name"));
            } else {
                tuple.put("FROM_HID_NM", "HID_" + String.format("%03d", fromHidId));
            }

            // TO HID 이름
            if (toHidId == 0) {
                tuple.put("TO_HID_NM", "OUTSIDE");
            } else if (hidMap.containsKey(toHidId)) {
                tuple.put("TO_HID_NM", hidMap.get(toHidId).getAttribute("name"));
            } else {
                tuple.put("TO_HID_NM", "HID_" + String.format("%03d", toHidId));
            }

            // MCP_ID, ZONE_ID (TO HID 기준)
            if (toHidId > 0 && hidMap.containsKey(toHidId)) {
                Element toHid = hidMap.get(toHidId);
                tuple.put("MCP_ID", toHid.getAttribute("mcpId"));
                tuple.put("ZONE_ID", toHid.getAttribute("zoneId"));
            } else if (fromHidId > 0 && hidMap.containsKey(fromHidId)) {
                Element fromHid = hidMap.get(fromHidId);
                tuple.put("MCP_ID", fromHid.getAttribute("mcpId"));
                tuple.put("ZONE_ID", fromHid.getAttribute("zoneId"));
            } else {
                tuple.put("MCP_ID", "");
                tuple.put("ZONE_ID", "");
            }

            // 엣지 유형 결정
            String edgeType;
            if (fromHidId == 0) {
                edgeType = "IN";       // 외부에서 HID로 진입
            } else if (toHidId == 0) {
                edgeType = "OUT";      // HID에서 외부로 진출
            } else {
                edgeType = "INTERNAL"; // HID 간 이동
            }
            tuple.put("EDGE_TYPE", edgeType);

            tuple.put("UPDATE_DT", updateDt);

            tuples.add(tuple);
        }
    } catch (Exception e) {
        logger.error("Failed to parse LAYOUT.XML for edge info", e);
        return;
    }

    // Full Refresh
    LogpressoAPI.truncateTable("ATLAS_INFO_HID_INOUT_MAS");
    LogpressoAPI.setInsertTuples("ATLAS_INFO_HID_INOUT_MAS", tuples, 100);

    logger.info("HID Edge Master Info updated from LAYOUT.XML: {} records", tuples.size());
}
```

---

## 2.3 updateHidInfoMaster() 메소드 (신규 - HID 상세 정보)

```java
/**
 * HID 상세 정보 마스터 데이터 업데이트
 * 테이블: ATLAS_HID_INFO_MAS
 *
 * 컬럼:
 *   - HID_ID: HID Zone ID
 *   - HID_NM: HID Zone 이름
 *   - MCP_ID: MCP ID
 *   - ZONE_ID: Zone ID
 *   - RAIL_LEN_TOTAL: 레일 길이 총합 (mm)
 *   - FREE_FLOW_SPEED: FREE FLOW 속도 (mm/s)
 *   - PORT_CNT_TOTAL: 포트 개수 총합
 *   - IN_CNT: IN Lane 개수
 *   - OUT_CNT: OUT Lane 개수
 *   - VHL_MAX: 최대 허용 차량 수
 *   - ZCU_ID: ZCU ID
 *   - UPDATE_DT: 마지막 업데이트 일시
 */
@Scheduled(cron = "0 0 0 * * ?")
public void updateHidInfoMaster() {
    String xmlPath = "/path/to/LAYOUT.XML";
    List<Tuple> tuples = new ArrayList<>();
    SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
    String updateDt = dateFormat.format(new Date());

    try {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        DocumentBuilder builder = factory.newDocumentBuilder();
        Document doc = builder.parse(new File(xmlPath));
        doc.getDocumentElement().normalize();

        // HID별 레일, 포트 정보 집계용 맵
        Map<Integer, Double> railLengthMap = new HashMap<>();
        Map<Integer, Integer> portCountMap = new HashMap<>();

        // RAIL 정보 집계
        NodeList railList = doc.getElementsByTagName("RAIL");
        for (int i = 0; i < railList.getLength(); i++) {
            Element rail = (Element) railList.item(i);
            int hidId = Integer.parseInt(rail.getAttribute("hidId"));
            double length = Double.parseDouble(rail.getAttribute("length"));

            railLengthMap.merge(hidId, length, Double::sum);
        }

        // PORT 정보 집계
        NodeList portList = doc.getElementsByTagName("PORT");
        for (int i = 0; i < portList.getLength(); i++) {
            Element port = (Element) portList.item(i);
            int hidId = Integer.parseInt(port.getAttribute("hidId"));

            portCountMap.merge(hidId, 1, Integer::sum);
        }

        // HID 정보 파싱
        NodeList hidList = doc.getElementsByTagName("HID");

        for (int i = 0; i < hidList.getLength(); i++) {
            Element hid = (Element) hidList.item(i);
            int hidId = Integer.parseInt(hid.getAttribute("id"));

            Tuple tuple = new Tuple();

            tuple.put("HID_ID", hidId);
            tuple.put("HID_NM", hid.getAttribute("name"));
            tuple.put("MCP_ID", hid.getAttribute("mcpId"));
            tuple.put("ZONE_ID", hid.getAttribute("zoneId"));

            // 레일 길이 총합
            double railLenTotal = railLengthMap.getOrDefault(hidId, 0.0);
            tuple.put("RAIL_LEN_TOTAL", railLenTotal);

            // FREE FLOW 속도 (XML에서 가져오거나 기본값)
            double freeFlowSpeed = 2000.0; // 기본값 2000 mm/s
            if (hid.hasAttribute("freeFlowSpeed")) {
                freeFlowSpeed = Double.parseDouble(hid.getAttribute("freeFlowSpeed"));
            }
            tuple.put("FREE_FLOW_SPEED", freeFlowSpeed);

            // 포트 개수 총합
            int portCntTotal = portCountMap.getOrDefault(hidId, 0);
            tuple.put("PORT_CNT_TOTAL", portCntTotal);

            // 기존 컬럼
            tuple.put("IN_CNT", Integer.parseInt(hid.getAttribute("inCnt")));
            tuple.put("OUT_CNT", Integer.parseInt(hid.getAttribute("outCnt")));
            tuple.put("VHL_MAX", Integer.parseInt(hid.getAttribute("vhlMax")));
            tuple.put("ZCU_ID", hid.getAttribute("zcuId"));
            tuple.put("UPDATE_DT", updateDt);

            tuples.add(tuple);
        }
    } catch (Exception e) {
        logger.error("Failed to parse LAYOUT.XML for HID info", e);
        return;
    }

    // Full Refresh
    LogpressoAPI.truncateTable("ATLAS_HID_INFO_MAS");
    LogpressoAPI.setInsertTuples("ATLAS_HID_INFO_MAS", tuples, 100);

    logger.info("HID Info Master updated from LAYOUT.XML: {} records", tuples.size());
}
```

---

## 2.4 스케줄러 통합 (선택사항)

```java
@Scheduled(cron = "0 0 0 * * ?")
public void updateAllHidMasterTables() {
    logger.info("Starting HID Master Tables update...");

    // 1. 엣지 마스터 업데이트
    updateHidEdgeMasterInfo();

    // 2. HID 상세 정보 업데이트
    updateHidInfoMaster();

    logger.info("HID Master Tables update completed.");
}
```

---

# 변경 요약

## OhtMsgWorkerRunnable.java

| 구분 | 기존 | 변경 |
|------|------|------|
| 버퍼 타입 | `ConcurrentMap<Integer, int[]>` | `ConcurrentMap<String, AtomicInteger>` |
| 버퍼 Key | HID_ID (정수) | "fromHidId:toHidId" (문자열) |
| 저장 컬럼 | HID_ID, IN_CNT, OUT_CNT, VHL_CNT | FROM_HIDID, TO_HIDID, TRANS_CNT |
| 데이터 볼륨 | HID 개수 × 2 (IN/OUT) | 엣지 개수 (약 2010개) |
| 부하 | 높음 | 낮음 (5~10% 수준) |

## HidMasterBatchJob.java

| 구분 | 기존 | 변경 |
|------|------|------|
| 마스터 테이블 | `ATLAS_INFO_HID_INOUT` | `ATLAS_INFO_HID_INOUT_MAS` |
| 신규 테이블 | - | `ATLAS_HID_INFO_MAS` |
| 신규 컬럼 | - | RAIL_LEN_TOTAL, FREE_FLOW_SPEED, PORT_CNT_TOTAL |
| 엣지 컬럼 | - | FROM_HIDID, TO_HIDID, EDGE_TYPE |

---

# 필요한 Import

```java
// OhtMsgWorkerRunnable.java
import java.util.concurrent.atomic.AtomicInteger;

// HidMasterBatchJob.java
import java.util.HashMap;
import java.util.Map;
```
