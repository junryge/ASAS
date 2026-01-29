# 기존 Java 소스 수정 사항

## FABID 종류
- M14, M16, M17, ... (프로젝트별)

---

## 1. HidEvent.java 수정

### 수정 전
```java
public class HidEvent {
    private int zoneId;
    private String eventType;
    private String vehicleId;
    private long timestamp;
    private int fromNode;
    private int toNode;
}
```

### 수정 후
```java
public class HidEvent {
    private int zoneId;
    private String eventType;
    private String vehicleId;
    private long timestamp;
    private int fromNode;
    private int toNode;
    private String fabId;      // ★ 추가

    // ★ getter/setter 추가
    public String getFabId() { return fabId; }
    public void setFabId(String fabId) { this.fabId = fabId; }
}
```

---

## 2. HidZoneService.java (또는 Handler) 수정

### 수정 전
```java
public void saveHidEvent(HidEvent event) {
    // 단일 테이블에 저장
    String sql = "INSERT INTO hid_events VALUES (...)";
    jdbcTemplate.update(sql, ...);
}
```

### 수정 후
```java
// ★ FABID별 테이블명 맵 추가
private static final Map<String, String> FABID_TABLE_MAP = new HashMap<>();
static {
    FABID_TABLE_MAP.put("M14", "hid_events_m14");
    FABID_TABLE_MAP.put("M16", "hid_events_m16");
    FABID_TABLE_MAP.put("M17", "hid_events_m17");
}

public void saveHidEvent(HidEvent event) {
    // ★ FABID 추출
    String fabId = extractFabId(event.getZoneId());
    event.setFabId(fabId);

    // ★ FABID별 테이블에 저장
    String tableName = FABID_TABLE_MAP.getOrDefault(fabId, "hid_events_unknown");
    String sql = "INSERT INTO " + tableName + " VALUES (...)";
    jdbcTemplate.update(sql, ...);
}

// ★ 신규 메서드: Zone ID로 FABID 추출
private String extractFabId(int zoneId) {
    // Zone 범위별 FABID 매핑 (실제 범위에 맞게 수정)
    if (zoneId >= 1 && zoneId <= 700) {
        return "M14";
    } else if (zoneId >= 701 && zoneId <= 1400) {
        return "M16";
    } else {
        return "M17";
    }
}
```

---

## 3. LogpressoSender.java 수정

### 수정 전
```java
public void send(HidEvent event) {
    String endpoint = "/api/hid_events";
    httpClient.post(endpoint, toJson(event));
}
```

### 수정 후
```java
public void send(HidEvent event) {
    // ★ FABID별 엔드포인트 분리
    String fabId = event.getFabId();
    String endpoint = "/api/hid_events_" + fabId.toLowerCase();
    httpClient.post(endpoint, toJson(event));
}

// ★ 배치 전송시 FABID별 그룹핑
public void sendBatch(List<HidEvent> events) {
    // FABID별로 그룹핑
    Map<String, List<HidEvent>> byFabId = events.stream()
        .collect(Collectors.groupingBy(HidEvent::getFabId));

    // 각 FABID별로 전송
    for (Map.Entry<String, List<HidEvent>> entry : byFabId.entrySet()) {
        String fabId = entry.getKey();
        String endpoint = "/api/hid_events_" + fabId.toLowerCase();
        httpClient.post(endpoint, toJsonArray(entry.getValue()));
    }
}
```

---

## 4. 설정 파일 수정 (application.properties 또는 config)

### 수정 전
```properties
hid.table.name=hid_events
```

### 수정 후
```properties
# ★ FABID별 테이블 설정
hid.fabid.list=M14,M16,M17

hid.table.m14=hid_events_m14
hid.table.m16=hid_events_m16
hid.table.m17=hid_events_m17

# ★ Zone-FABID 매핑
hid.zone.m14.start=1
hid.zone.m14.end=700

hid.zone.m16.start=701
hid.zone.m16.end=1400

hid.zone.m17.start=1401
hid.zone.m17.end=2008
```

---

## 5. SQL 스크립트 (테이블 생성)

### 신규 추가
```sql
-- M14용 테이블
CREATE TABLE hid_events_m14 (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    zone_id INT,
    event_type VARCHAR(10),
    vehicle_id VARCHAR(50),
    fab_id VARCHAR(20),
    from_node INT,
    to_node INT,
    timestamp DATETIME,
    INDEX idx_zone (zone_id),
    INDEX idx_time (timestamp)
);

-- M16용 테이블
CREATE TABLE hid_events_m16 (
    -- 동일 구조
);

-- M17용 테이블
CREATE TABLE hid_events_m17 (
    -- 동일 구조
);
```

---

## 수정 파일 요약

| 파일 | 수정 내용 |
|------|----------|
| HidEvent.java | `fabId` 필드 추가 |
| HidZoneService.java | `extractFabId()` 메서드, FABID별 테이블 저장 |
| LogpressoSender.java | FABID별 엔드포인트 분리 |
| application.properties | FABID 설정 추가 |
| DB | FABID별 테이블 생성 |

---

## Zone-FABID 매핑 (확인 필요)

| FABID | Zone 범위 | 비고 |
|-------|----------|------|
| M14 | 1 ~ ? | 확인 필요 |
| M16 | ? ~ ? | 확인 필요 |
| M17 | ? ~ 2008 | 확인 필요 |

**→ 실제 Zone 범위는 운영 데이터 확인 후 수정 필요**
