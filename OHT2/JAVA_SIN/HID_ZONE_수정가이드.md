# HID Zone FABID 분리 저장 - Java 코드 수정 가이드

## 목적
- HID Zone IN/OUT 이벤트를 FABID별로 분리
- 로그프레소에 FABID별 테이블로 저장

---

## 1. FABID 추출 로직 추가

### 수정 전
```java
public class HidZoneHandler {

    public void processHidEvent(HidEvent event) {
        // 기존: 모든 이벤트를 하나의 테이블에 저장
        saveToDatabase(event);
    }

    private void saveToDatabase(HidEvent event) {
        String sql = "INSERT INTO hid_events (zone_id, event_type, vehicle_id, timestamp) VALUES (?, ?, ?, ?)";
        // ...
    }
}
```

### 수정 후
```java
public class HidZoneHandler {

    // FABID별 테이블 매핑
    private Map<String, String> fabIdTableMap = new HashMap<>();

    public HidZoneHandler() {
        // FABID별 테이블명 초기화
        fabIdTableMap.put("FAB1", "hid_events_fab1");
        fabIdTableMap.put("FAB2", "hid_events_fab2");
        fabIdTableMap.put("FAB3", "hid_events_fab3");
        // 필요한 FABID 추가
    }

    public void processHidEvent(HidEvent event) {
        // 신규: FABID 추출
        String fabId = extractFabId(event);

        // FABID별 테이블에 저장
        saveToFabIdTable(event, fabId);
    }

    /**
     * 이벤트에서 FABID 추출
     * - Zone ID 기반 또는 Vehicle ID 기반으로 추출
     */
    private String extractFabId(HidEvent event) {
        // 방법 1: Zone ID 범위로 FABID 결정
        int zoneId = event.getZoneId();
        if (zoneId >= 1 && zoneId <= 500) {
            return "FAB1";
        } else if (zoneId >= 501 && zoneId <= 1000) {
            return "FAB2";
        } else {
            return "FAB3";
        }

        // 방법 2: Vehicle ID prefix로 FABID 결정
        // String vehicleId = event.getVehicleId();
        // if (vehicleId.startsWith("F1")) return "FAB1";
        // if (vehicleId.startsWith("F2")) return "FAB2";
    }

    private void saveToFabIdTable(HidEvent event, String fabId) {
        String tableName = fabIdTableMap.getOrDefault(fabId, "hid_events_unknown");
        String sql = String.format(
            "INSERT INTO %s (zone_id, event_type, vehicle_id, fab_id, timestamp) VALUES (?, ?, ?, ?, ?)",
            tableName
        );
        // PreparedStatement로 실행
    }
}
```

---

## 2. HidEvent 클래스에 FABID 필드 추가

### 수정 전
```java
public class HidEvent {
    private int zoneId;
    private String eventType;  // "IN" or "OUT"
    private String vehicleId;
    private long timestamp;
    private int fromNode;
    private int toNode;

    // getters, setters...
}
```

### 수정 후
```java
public class HidEvent {
    private int zoneId;
    private String eventType;  // "IN" or "OUT"
    private String vehicleId;
    private long timestamp;
    private int fromNode;
    private int toNode;
    private String fabId;      // 신규 추가

    // 기존 getters, setters...

    // 신규 추가
    public String getFabId() {
        return fabId;
    }

    public void setFabId(String fabId) {
        this.fabId = fabId;
    }
}
```

---

## 3. 로그프레소 연동 수정

### 수정 전
```java
public class LogpressoClient {

    public void sendEvent(HidEvent event) {
        // 기존: 단일 테이블로 전송
        String json = toJson(event);
        httpClient.post("/api/tables/hid_events/insert", json);
    }
}
```

### 수정 후
```java
public class LogpressoClient {

    private static final String BASE_URL = "/api/tables";

    public void sendEvent(HidEvent event, String fabId) {
        // 신규: FABID별 테이블로 전송
        String tableName = getTableName(fabId);
        String json = toJson(event);
        String endpoint = String.format("%s/%s/insert", BASE_URL, tableName);
        httpClient.post(endpoint, json);
    }

    /**
     * FABID별 로그프레소 테이블명 반환
     */
    private String getTableName(String fabId) {
        // 테이블 명명 규칙: hid_events_{fabid}
        return "hid_events_" + fabId.toLowerCase();
    }

    /**
     * 배치 전송 (성능 최적화)
     */
    public void sendEventsBatch(List<HidEvent> events) {
        // FABID별로 그룹핑
        Map<String, List<HidEvent>> eventsByFabId = events.stream()
            .collect(Collectors.groupingBy(HidEvent::getFabId));

        // FABID별로 배치 전송
        for (Map.Entry<String, List<HidEvent>> entry : eventsByFabId.entrySet()) {
            String fabId = entry.getKey();
            List<HidEvent> fabEvents = entry.getValue();

            String tableName = getTableName(fabId);
            String json = toJsonArray(fabEvents);
            String endpoint = String.format("%s/%s/insert-batch", BASE_URL, tableName);
            httpClient.post(endpoint, json);
        }
    }
}
```

---

## 4. Zone-FABID 매핑 테이블 (설정 파일)

### zone_fabid_mapping.properties (신규 생성)
```properties
# Zone ID 범위별 FABID 매핑
# 형식: zone.range.{순번}={시작}-{끝},{FABID}

zone.range.1=1-500,FAB1
zone.range.2=501-1000,FAB2
zone.range.3=1001-1500,FAB3
zone.range.4=1501-2008,FAB4
```

### 매핑 로더 클래스 (신규 생성)
```java
public class ZoneFabIdMapper {

    private Map<String, int[]> fabIdRanges = new HashMap<>();

    public void loadMapping(String propertiesPath) throws IOException {
        Properties props = new Properties();
        props.load(new FileInputStream(propertiesPath));

        for (String key : props.stringPropertyNames()) {
            if (key.startsWith("zone.range.")) {
                String value = props.getProperty(key);
                String[] parts = value.split(",");
                String[] range = parts[0].split("-");

                int start = Integer.parseInt(range[0]);
                int end = Integer.parseInt(range[1]);
                String fabId = parts[1];

                fabIdRanges.put(fabId, new int[]{start, end});
            }
        }
    }

    public String getFabId(int zoneId) {
        for (Map.Entry<String, int[]> entry : fabIdRanges.entrySet()) {
            int[] range = entry.getValue();
            if (zoneId >= range[0] && zoneId <= range[1]) {
                return entry.getKey();
            }
        }
        return "UNKNOWN";
    }
}
```

---

## 5. 기존 데이터 마이그레이션

### 기존 hid_events 테이블 → FABID별 테이블 분리

```sql
-- FAB1 데이터 마이그레이션
INSERT INTO hid_events_fab1
SELECT * FROM hid_events
WHERE zone_id BETWEEN 1 AND 500;

-- FAB2 데이터 마이그레이션
INSERT INTO hid_events_fab2
SELECT * FROM hid_events
WHERE zone_id BETWEEN 501 AND 1000;

-- FAB3 데이터 마이그레이션
INSERT INTO hid_events_fab3
SELECT * FROM hid_events
WHERE zone_id BETWEEN 1001 AND 1500;

-- FAB4 데이터 마이그레이션
INSERT INTO hid_events_fab4
SELECT * FROM hid_events
WHERE zone_id BETWEEN 1501 AND 2008;
```

---

## 6. 수정 체크리스트

| 순서 | 파일/위치 | 수정 내용 | 완료 |
|------|----------|----------|------|
| 1 | HidEvent.java | fabId 필드 추가 | [ ] |
| 2 | HidZoneHandler.java | extractFabId() 메서드 추가 | [ ] |
| 3 | HidZoneHandler.java | saveToFabIdTable() 메서드 추가 | [ ] |
| 4 | LogpressoClient.java | FABID별 테이블 전송 로직 | [ ] |
| 5 | zone_fabid_mapping.properties | 매핑 설정 파일 생성 | [ ] |
| 6 | ZoneFabIdMapper.java | 매핑 로더 클래스 생성 | [ ] |
| 7 | DB | FABID별 테이블 생성 | [ ] |
| 8 | DB | 기존 데이터 마이그레이션 | [ ] |

---

## 7. 테이블 구조 (로그프레소)

### FABID별 테이블 생성
```sql
-- hid_events_fab1, hid_events_fab2, ... 동일 구조
CREATE TABLE hid_events_fab1 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    zone_id INT NOT NULL,
    event_type VARCHAR(10) NOT NULL,  -- 'IN' or 'OUT'
    vehicle_id VARCHAR(50),
    fab_id VARCHAR(20),
    from_node INT,
    to_node INT,
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_zone_id (zone_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_vehicle_id (vehicle_id)
);
```
