# HID IN/OUT 카운트 및 FABID 분리 저장 수정 안내서

## 1. 현재 코드 분석

### 1.1 기존 HID 구간별 VHL 카운트 로직
**파일**: `OhtMsgWorkerRunnable.java`
**메소드**: `_calculatedVhlCnt()` (Line 357-382)

```java
// [현재 코드] - HID 구간별 VHL 수만 카운트
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
    // ... 생략
}
```

**분석**:
- `previousHidId != currentHidId` → 차량이 HID 구간을 이동했을 때 감지
- `currentHidId > 0` → 새로운 HID 구간에 **진입 (IN)**
- `previousHidId > 0` → 이전 HID 구간에서 **이탈 (OUT)**
- 현재는 카운트만 증감하고 별도 로그 기록 안함

---

### 1.2 기존 Logpresso 저장 로직
**파일**: `OhtMsgWorkerRunnable.java`
**메소드**: `_insertHidOffLogpresso()` (Line 494-514)

```java
// [현재 코드] - HID OFF 이벤트만 Logpresso에 저장
private boolean _insertHidOffLogpresso(HidOffRecordItem recordItem, long currentMilli) {
    Tuple tuple = new Tuple();
    String state = recordItem.getState();

    tuple.put("FAB_ID", recordItem.getFabId());      // ← FAB_ID 이미 사용 중!
    tuple.put("MCP_NM", recordItem.getMcpName());
    tuple.put("ALARM_CD", recordItem.getErrorCode());
    tuple.put("EVENT_DT", recordItem.getEventDateTimeString());
    tuple.put("HID_ID", recordItem.getHidId());
    tuple.put("ADDR_LST", recordItem.getHidAreaAddressString());
    tuple.put("PORT_LST", recordItem.getAffectedPortString());
    tuple.put("ENV", Env.getEnv());
    tuple.put("STATE", state);

    if (state.equals(OHT_TIB_STATE.NORMAL)) {
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        tuple.put("RECOVERY_DT", dateFormat.format(new Date(currentMilli)));
    }

    return LogpressoAPI.setInsertTuples("ATLAS_OHT_HID_OFF", List.of(tuple), 20);
}
```

**분석**:
- FAB_ID(M14, M16 등)는 이미 저장되고 있음
- 테이블: `ATLAS_OHT_HID_OFF` (HID OFF 이벤트 전용)
- HID IN/OUT 이벤트는 별도 저장 안함

---

## 2. 수정 방안

### 2.1 HID IN/OUT 이벤트 Logpresso 저장 메소드 추가

**[수정 전]**: HID IN/OUT 이벤트 저장 없음

**[수정 후]**: 새 메소드 추가

```java
// ===== 추가할 코드 (Line 515 이후에 추가) =====

/**
 * HID IN/OUT 이벤트를 Logpresso에 저장
 * @param hidId HID Zone ID
 * @param eventType "IN" 또는 "OUT"
 * @param vehicleName 차량 이름 (예: V00001)
 * @param currentMilli 이벤트 발생 시간
 */
private void _insertHidInOutLogpresso(int hidId, String eventType, String vehicleName, long currentMilli) {
    Tuple tuple = new Tuple();
    SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

    tuple.put("FAB_ID", this.fabId);           // M14, M16 등
    tuple.put("MCP_NM", this.mcpName);
    tuple.put("HID_ID", hidId);
    tuple.put("VHL_NM", vehicleName);
    tuple.put("EVENT_TYPE", eventType);        // "IN" or "OUT"
    tuple.put("EVENT_DT", dateFormat.format(new Date(currentMilli)));
    tuple.put("ENV", Env.getEnv());

    // FABID별 테이블 분리: ATLAS_OHT_HID_INOUT_M14, ATLAS_OHT_HID_INOUT_M16 등
    String tableName = "ATLAS_OHT_HID_INOUT_" + this.fabId;

    LogpressoAPI.setInsertTuples(tableName, List.of(tuple), 20);
}
```

---

### 2.2 _calculatedVhlCnt() 메소드 수정

**[수정 전]**: Line 357-382

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
    // ... 생략
}
```

**[수정 후]**:

```java
private void _calculatedVhlCnt(int currentHidId, String key, Vhl vehicle) {
    long timer = System.currentTimeMillis();
    int previousHidId = vehicle.getHidId();
    String vehicleName = vehicle.getName();  // ← 추가

    if (previousHidId != currentHidId) {
        // HID 구간 IN (새로운 HID 구간 진입)
        if (currentHidId > 0) {
            String v = String.format("%03d", currentHidId);
            DataService.getDataSet().increaseHidVehicleCnt(key + ":" + v);

            // ===== 추가: HID IN 이벤트 Logpresso 저장 =====
            this._insertHidInOutLogpresso(currentHidId, "IN", vehicleName, timer);
        }

        // HID 구간 OUT (이전 HID 구간 이탈)
        if (previousHidId > 0) {
            String v = String.format("%03d", previousHidId);
            DataService.getDataSet().decreaseHidVehicleCnt(key + ":" + v);

            // ===== 추가: HID OUT 이벤트 Logpresso 저장 =====
            this._insertHidInOutLogpresso(previousHidId, "OUT", vehicleName, timer);
        }

        vehicle.setHidId(currentHidId);
    }

    long checkingTime = System.currentTimeMillis() - timer;

    if (checkingTime >= 60000) {
        logger.info("... `number of vehicles per hid section` process took more than 1 minute to complete [elapsed time: {}min]", checkingTime / 60000);
    }
}
```

---

## 3. FABID 별 테이블 분리 전략

### 3.1 단일 테이블 방식 (권장)
```java
// 모든 FABID 데이터를 하나의 테이블에 저장
String tableName = "ATLAS_OHT_HID_INOUT";
tuple.put("FAB_ID", this.fabId);  // M14, M16, M17 등
```

**장점**: 관리 편의성, 쿼리 유연성
**Logpresso 쿼리 예시**:
```sql
SELECT * FROM ATLAS_OHT_HID_INOUT WHERE FAB_ID = 'M14' AND EVENT_TYPE = 'IN'
```

### 3.2 FABID 별 분리 테이블 방식
```java
// FABID별 별도 테이블 생성
String tableName = "ATLAS_OHT_HID_INOUT_" + this.fabId;
// 결과: ATLAS_OHT_HID_INOUT_M14, ATLAS_OHT_HID_INOUT_M16 등
```

**장점**: 데이터 격리, 성능 최적화

---

## 4. Logpresso 테이블 스키마

### ATLAS_OHT_HID_INOUT 테이블 구조

| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| FAB_ID | STRING | 팹 ID | M14, M16, M17 |
| MCP_NM | STRING | MCP 이름 | MCP01 |
| HID_ID | INT | HID Zone ID | 001, 002, 187 |
| VHL_NM | STRING | 차량 이름 | V00001 |
| EVENT_TYPE | STRING | IN/OUT 구분 | IN, OUT |
| EVENT_DT | STRING | 이벤트 발생 시간 | 2026-01-29 15:30:00 |
| ENV | STRING | 환경 구분 | PROD, DEV |

---

## 5. 통계 쿼리 예시

### HID 구간별 IN/OUT 카운트
```sql
SELECT HID_ID, EVENT_TYPE, COUNT(*) as CNT
FROM ATLAS_OHT_HID_INOUT
WHERE FAB_ID = 'M14'
  AND EVENT_DT >= '2026-01-29 00:00:00'
GROUP BY HID_ID, EVENT_TYPE
ORDER BY HID_ID
```

### 특정 HID 구간 차량 흐름 추적
```sql
SELECT VHL_NM, EVENT_TYPE, EVENT_DT
FROM ATLAS_OHT_HID_INOUT
WHERE FAB_ID = 'M14'
  AND HID_ID = 99
ORDER BY EVENT_DT DESC
LIMIT 100
```

---

## 6. 요약

| 항목 | 현재 상태 | 수정 후 |
|------|-----------|---------|
| HID IN 감지 | O (카운트만) | O (카운트 + Logpresso 저장) |
| HID OUT 감지 | O (카운트만) | O (카운트 + Logpresso 저장) |
| FABID 분리 | O (HID_OFF만) | O (HID_INOUT 추가) |
| Logpresso 테이블 | ATLAS_OHT_HID_OFF | + ATLAS_OHT_HID_INOUT |

**수정 파일**: `OhtMsgWorkerRunnable.java`
**추가 메소드**: `_insertHidInOutLogpresso()`
**수정 메소드**: `_calculatedVhlCnt()`
