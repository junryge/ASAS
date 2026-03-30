# ATLAS_HID_INFO_MAS 테이블 - VHL_COUNT_LIMIT / VHL_PRECAUTION 컬럼 추가

## 변경 파일
- `ALT/src/batch/HidEdgeInOutUpdateMasterBatch.java`

---

## 추가된 컬럼

| 컬럼명 | 타입 | 설명 | 데이터 출처 |
|--------|------|------|------------|
| `VHL_COUNT_LIMIT` | INT | HID 내 최대 허용 차량 수 | `RawHid.getVhlMax()` ← layout.xml `VEHICLE_MAX` |
| `VHL_PRECAUTION` | INT | HID 내 차량 경고 임계값 | `RawHid.getVhlPreCaution()` ← layout.xml `VEHICLE_PRECAUTION` |

---

## 컬럼 의미 상세

### VHL_COUNT_LIMIT (= VEHICLE_MAX)
- HID 구간에 **동시에 진입할 수 있는 차량의 최대 수**
- 이 값을 초과하면 해당 HID로의 차량 진입이 제한됨
- layout.xml에서 `VEHICLE_MAX=N` 형태로 설정

### VHL_PRECAUTION (= VEHICLE_PRECAUTION)
- HID 구간 내 차량 수가 이 값에 도달하면 **경고(주의) 상태** 진입
- VHL_COUNT_LIMIT보다 작은 값으로 설정하여 사전 경고 역할
- layout.xml에서 `VEHICLE_PRECAUTION=N` 형태로 설정
- 예: VHL_PRECAUTION=3, VHL_COUNT_LIMIT=5이면 → 차량 3대부터 주의, 5대 초과 시 진입 제한

---

## 데이터 흐름

```
layout.xml (VEHICLE_MAX, VEHICLE_PRECAUTION)
    ↓ 파싱
Mcp75Config.getRawHidMap() → RawHid 객체
    ↓ 배치 조회
HidEdgeInOutUpdateMasterBatch._updateHidInfoMaster()
    ↓ 테이블 저장
{FAB}_ATLAS_HID_INFO_MAS (VHL_COUNT_LIMIT, VHL_PRECAUTION)
```

---

## 변경 내용 (HidEdgeInOutUpdateMasterBatch.java)

### 1. RawHidMap 조회 로직 추가 (169~178행)

```java
// RawHidMap에서 VHL_COUNT_LIMIT, VHL_PRECAUTION 조회
Map<Integer, Integer> vhlCountLimitMap = new HashMap<>();  // HID → vhlMax
Map<Integer, Integer> vhlPrecautionMap = new HashMap<>();  // HID → vhlPreCaution
McpProperties mcpProperties = DataService.getInstance()
    .getFabPropertiesMap().get(fabId)
    .getMcpPropertiesMap().get(mcpName);
if (mcpProperties != null && mcpProperties.getMcp75Config() != null) {
    for (RawHid rawHid : mcpProperties.getMcp75Config().getRawHidMap().values()) {
        vhlCountLimitMap.put(rawHid.getId(), rawHid.getVhlMax());
        vhlPrecautionMap.put(rawHid.getId(), rawHid.getVhlPreCaution());
    }
}
```

### 2. Tuple에 값 세팅 (238~240행)

```java
// VHL_COUNT_LIMIT, VHL_PRECAUTION → RawHid (layout.xml VEHICLE_MAX, VEHICLE_PRECAUTION)
tuple.put("VHL_COUNT_LIMIT", vhlCountLimitMap.getOrDefault(hidId, 0));
tuple.put("VHL_PRECAUTION", vhlPrecautionMap.getOrDefault(hidId, 0));
```

---

## 기존 테이블 컬럼 구조 (변경 후)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `HID_ID` | INT | HID ID |
| `HID_NM` | STRING | HID 이름 (HID_001 형식) |
| `MCP_ID` | STRING | MCP 이름 |
| `ZONE_ID` | STRING | Zone ID |
| `RAIL_LEN_TOTAL` | DOUBLE | 레일 길이 총합 (mm) |
| `FREE_FLOW_SPEED` | DOUBLE | FREE FLOW 속도 (mm/s) |
| `PORT_CNT_TOTAL` | INT | 포트 개수 총합 |
| `IN_CNT` | INT | IN Lane 개수 |
| `OUT_CNT` | INT | OUT Lane 개수 |
| `VHL_MAX` | INT | (기존, 현재 0 하드코딩) |
| `ZCU_ID` | STRING | ZCU ID |
| **`VHL_COUNT_LIMIT`** | **INT** | **최대 허용 차량 수 (신규)** |
| **`VHL_PRECAUTION`** | **INT** | **차량 경고 임계값 (신규)** |
| `UPDATE_DT` | STRING | 업데이트 일시 |

---

## 관련 클래스

| 클래스 | 위치 | 역할 |
|--------|------|------|
| `RawHid` | `ALT/src/data/raw/RawHid.java` | HID 원시 데이터 (vhlMax, vhlPreCaution 필드 보유) |
| `Mcp75Config` | `ALT/src/data/raw/Mcp75Config.java` | layout.xml 파싱, rawHidMap 관리 |
| `McpProperties` | `ALT/src/data/McpProperties.java` | MCP 설정, getMcp75Config() 제공 |
| `HidEdgeInOutUpdateMasterBatch` | `ALT/src/batch/HidEdgeInOutUpdateMasterBatch.java` | 배치 잡, ATLAS_HID_INFO_MAS 테이블 업데이트 |
