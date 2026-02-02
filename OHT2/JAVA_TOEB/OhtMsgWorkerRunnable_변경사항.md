# OhtMsgWorkerRunnable.java 변경 사항

## 개요
HID IN/OUT 처리를 엣지 기반으로 변경하여 부하를 최적화합니다.
- 기존: HID별 IN/OUT 카운트 개별 저장
- 변경: FROM_HIDID → TO_HIDID 엣지 전환만 추적 (약 2010개 엣지)

---

## 1. 클래스 필드 변경

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

## 2. _calculatedVhlCnt() 메소드 수정

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

## 3. flushHidCountBuffer() → flushHidEdgeBuffer() 변경

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

## 4. 변경 요약

| 구분 | 기존 | 변경 |
|------|------|------|
| 버퍼 타입 | `ConcurrentMap<Integer, int[]>` | `ConcurrentMap<String, AtomicInteger>` |
| 버퍼 Key | HID_ID (정수) | "fromHidId:toHidId" (문자열) |
| 저장 컬럼 | HID_ID, IN_CNT, OUT_CNT, VHL_CNT | FROM_HIDID, TO_HIDID, TRANS_CNT |
| 데이터 볼륨 | HID 개수 × 2 (IN/OUT) | 엣지 개수 (약 2010개) |
| 부하 | 높음 | 낮음 (5~10% 수준) |

---

## 5. 필요한 Import 추가

```java
import java.util.concurrent.atomic.AtomicInteger;
```
