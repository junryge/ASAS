# ATLAS_HID_INFO_MAS 테이블 - VHL_COUNT_LIMIT / VHL_PRECAUTION 컬럼 추가

## 변경 목적

`{FAB}_ATLAS_HID_INFO_MAS` 테이블에 HID별 차량 제한/경고 기준값이 없어서
layout.xml의 `VEHICLE_MAX`, `VEHICLE_PRECAUTION` 값을 신규 컬럼으로 추가한다.

- `VHL_COUNT_LIMIT`: HID 구간 내 최대 허용 차량 수 (이 값 초과 시 진입 제한)
- `VHL_PRECAUTION`: HID 구간 내 차량 경고 임계값 (이 값 도달 시 주의 상태)

---

## 수정 파일 목록

| 파일 | 수정 내용 |
|------|-----------|
| `src/batch/HidEdgeInOutUpdateMasterBatch.java` | `_updateHidInfoMaster()`에 VHL_COUNT_LIMIT, VHL_PRECAUTION 추가 + truncate 추가 |
| `src/HidMasterBatchJob.java` (OHT2/JAVA_TOEB/SRC) | `_updateHidInfoMaster()`에 VHL_COUNT_LIMIT, VHL_PRECAUTION 추가 |
| `src/OhtMsgWorkerRunnable.java` (OHT2/JAVA_MODIFIED) | `_updateHidInfoMaster()`에 VHL_COUNT_LIMIT, VHL_PRECAUTION 추가 |
| `src/OhtMsgWorkerRunnable.java` (OHT2/JAVA) | 위와 동일 (JAVA_MODIFIED 복사본) |

---

## 수정 내용 상세

### 1. RawHidMap 조회 로직 추가

`_updateHidInfoMaster()` 메서드 내부, HID별 집계 맵 선언부 아래에 추가.

**왜**: layout.xml에서 파싱된 VEHICLE_MAX, VEHICLE_PRECAUTION 값이 `RawHid` 객체에 있으므로
`Mcp75Config.getRawHidMap()`을 통해 HID ID별로 맵에 담아놓는다.

```java
// RawHidMap에서 VHL_COUNT_LIMIT, VHL_PRECAUTION 조회
Map<Integer, Integer> vhlCountLimitMap = new HashMap<>();
Map<Integer, Integer> vhlPrecautionMap = new HashMap<>();
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

### 2. tuple.put() 추가

HID별 Tuple 생성 루프 내부, `ZCU_ID` 아래 / `UPDATE_DT` 위에 추가.

**왜**: 위에서 조회한 맵에서 현재 HID ID에 해당하는 값을 꺼내서 테이블에 넣는다.

```java
tuple.put("VHL_COUNT_LIMIT", vhlCountLimitMap.getOrDefault(hidId, 0));
tuple.put("VHL_PRECAUTION", vhlPrecautionMap.getOrDefault(hidId, 0));
```

### 3. truncateTable() 추가 (src/batch/HidEdgeInOutUpdateMasterBatch.java만 해당)

`LogpressoAPI.setInsertTuples()` 호출 전에 추가.

**왜**: 기존 코드에 truncate가 빠져 있어서 배치 실행 시 데이터가 중복 적재되었음.
설계 문서 기준 Full Refresh (삭제 후 재적재) 방식이므로 truncate 추가.

```java
LogpressoAPI.truncateTable(tableName);
LogpressoAPI.setInsertTuples(tableName, tuples, 100);
```

---

## 데이터 흐름

```
layout.xml (VEHICLE_MAX, VEHICLE_PRECAUTION)
    ↓ 파싱
src/Mcp75Config.java → RawHid 객체 (vhlMax, vhlPreCaution)
    ↓ 배치 조회
src/HidEdgeInOutUpdateMasterBatch.java → _updateHidInfoMaster()
src/HidMasterBatchJob.java             → _updateHidInfoMaster()
src/OhtMsgWorkerRunnable.java          → _updateHidInfoMaster()
    ↓ 테이블 저장
{FAB}_ATLAS_HID_INFO_MAS (VHL_COUNT_LIMIT, VHL_PRECAUTION)
```

---

## 변경 후 테이블 컬럼 구조

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
