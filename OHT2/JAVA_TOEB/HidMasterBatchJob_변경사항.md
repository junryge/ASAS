# HidMasterBatchJob.java 변경 사항

## 개요
마스터 테이블 구조 변경 및 신규 테이블 추가
- 테이블명 변경: `ATLAS_INFO_HID_INOUT` → `ATLAS_INFO_HID_INOUT_MAS`
- 신규 테이블: `ATLAS_HID_INFO_MAS` (HID 상세 정보)

---

## 1. 테이블명 변경

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

## 2. updateHidMasterInfo() 메소드 변경 (엣지 기반)

### 기존 코드
```java
@Scheduled(cron = "0 0 0 * * ?")
public void updateHidMasterInfo() {
    String xmlPath = "/path/to/LAYOUT.XML";
    List<Tuple> tuples = new ArrayList<>();
    SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
    String updateDt = dateFormat.format(new Date());

    try {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        DocumentBuilder builder = factory.newDocumentBuilder();
        Document doc = builder.parse(new File(xmlPath));
        doc.getDocumentElement().normalize();

        NodeList hidList = doc.getElementsByTagName("HID");

        for (int i = 0; i < hidList.getLength(); i++) {
            Element hid = (Element) hidList.item(i);
            Tuple tuple = new Tuple();

            tuple.put("HID_ID", Integer.parseInt(hid.getAttribute("id")));
            tuple.put("HID_NM", hid.getAttribute("name"));
            tuple.put("MCP_ID", hid.getAttribute("mcpId"));
            tuple.put("ZONE_ID", hid.getAttribute("zoneId"));
            tuple.put("IN_CNT", Integer.parseInt(hid.getAttribute("inCnt")));
            tuple.put("OUT_CNT", Integer.parseInt(hid.getAttribute("outCnt")));
            tuple.put("VHL_MAX", Integer.parseInt(hid.getAttribute("vhlMax")));
            tuple.put("ZCU_ID", hid.getAttribute("zcuId"));
            tuple.put("UPDATE_DT", updateDt);

            tuples.add(tuple);
        }
    } catch (Exception e) {
        logger.error("Failed to parse LAYOUT.XML", e);
        return;
    }

    LogpressoAPI.truncateTable("ATLAS_INFO_HID_INOUT");
    LogpressoAPI.setInsertTuples("ATLAS_INFO_HID_INOUT", tuples, 100);

    logger.info("HID Master Info updated from LAYOUT.XML: {} records", tuples.size());
}
```

### 변경 코드 (엣지 기반 마스터)
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

## 3. 신규 메소드: updateHidInfoMaster() 추가

HID 상세 정보 마스터 테이블 업데이트

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

## 4. 스케줄러 통합 (선택사항)

두 메소드를 하나로 통합하여 관리 가능:

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

## 5. 변경 요약

### 테이블 변경

| 테이블명 | 상태 | 용도 |
|----------|------|------|
| `ATLAS_INFO_HID_INOUT` | 삭제 | 기존 HID 마스터 |
| `ATLAS_INFO_HID_INOUT_MAS` | 신규 | 엣지 마스터 (FROM/TO HID) |
| `ATLAS_HID_INFO_MAS` | 신규 | HID 상세 정보 |

### 신규 컬럼

**ATLAS_INFO_HID_INOUT_MAS:**
- `FROM_HIDID` (INT) - 출발 HID Zone ID
- `TO_HIDID` (INT) - 도착 HID Zone ID
- `EDGE_ID` (STRING) - 엣지 고유 ID
- `FROM_HID_NM` (STRING) - 출발 HID 이름
- `TO_HID_NM` (STRING) - 도착 HID 이름
- `EDGE_TYPE` (STRING) - 엣지 유형 (IN/OUT/INTERNAL)

**ATLAS_HID_INFO_MAS:**
- `RAIL_LEN_TOTAL` (DOUBLE) - 레일 길이 총합 (mm)
- `FREE_FLOW_SPEED` (DOUBLE) - FREE FLOW 속도 (mm/s)
- `PORT_CNT_TOTAL` (INT) - 포트 개수 총합

---

## 6. 필요한 Import 추가

```java
import java.util.HashMap;
import java.util.Map;
```
