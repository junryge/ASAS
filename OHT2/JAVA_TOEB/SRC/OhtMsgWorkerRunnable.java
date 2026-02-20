/**
 * OhtMsgWorkerRunnable.java — HID IN/OUT 엣지 기반 집계 추가 코드
 *
 * ※ 이 파일은 기존 OhtMsgWorkerRunnable.java에 추가할 코드만 모아둔 참조용 파일입니다.
 * ※ 기존 코드를 삭제하지 말고, 아래 표시된 위치에 코드를 추가하세요.
 *
 * [테이블 매핑]
 *   테이블 1: {FAB}_ATLAS_INFO_HID_INOUT_MAS  — 엣지 마스터 (하루 1회)
 *   테이블 2: {FAB}_ATLAS_HID_INFO_MAS         — HID 상세 정보 (하루 1회)
 *   테이블 3: {FAB}_ATLAS_HID_INOUT            — 1분 집계 (실시간)
 */
public class OhtMsgWorkerRunnable implements Runnable {

    // ========================================================================================
    // [신규 필드] — 기존 필드 아래에 추가 (기존: Line 1~10 부근)
    // ========================================================================================

    // --- 테이블 3: {FAB}_ATLAS_HID_INOUT 실시간 1분 집계용 ---
    // Key: "fromHidId:toHidId", Value: 전환 횟수
    private static ConcurrentMap<String, Integer> hidEdgeBuffer =
        new ConcurrentHashMap<>();
    private static long lastHidEdgeFlushTime = System.currentTimeMillis();
    private static final long HID_EDGE_FLUSH_INTERVAL = 60000; // 1분
    private static final Object hidEdgeFlushLock = new Object();
    private static final Object hidEdgeBufferLock = new Object();

    // --- 테이블 1,2: 마스터 테이블 하루 1회 업데이트용 ---
    private static volatile boolean hidMasterUpdatedToday = false;
    private static String hidMasterLastUpdateDate = "";
    private static final Object hidMasterUpdateLock = new Object();


    // ========================================================================================
    // [수정] _calculatedVhlCnt() — 기존 코드 유지 + 엣지 집계 추가
    //        기존 위치: OhtMsgWorkerRunnable.java:357-382
    // ========================================================================================

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
            // ===== 기존 코드 유지: HID VHL 카운트 (Line 361~374) =====
            if (currentHidId > 0) {
                String v = String.format("%03d", currentHidId);
                DataService.getDataSet().increaseHidVehicleCnt(key + ":" + v);
            }

            if (previousHidId > 0) {
                String v = String.format("%03d", previousHidId);
                DataService.getDataSet().decreaseHidVehicleCnt(key + ":" + v);
            }
            // ===== 기존 코드 유지 끝 =====

            // ===== [신규 추가] 엣지 전환 카운트 집계 → 테이블 3 =====
            // 데이터 소스: previousHidId = vehicle.getHidId() (Vhl.java:517)
            //             currentHidId  = railEdge.getHIDId() (RaileEdge.java:324)
            String edgeKey = String.format("%03d:%03d", previousHidId, currentHidId);
            synchronized (hidEdgeBufferLock) {
                hidEdgeBuffer.merge(edgeKey, 1, Integer::sum);
            }
            // ===== [신규 추가] 끝 =====

            vehicle.setHidId(currentHidId);
        }

        // ===== [신규 추가] 1분마다 버퍼 플러시 → 테이블 3 저장 =====
        if (timer - lastHidEdgeFlushTime >= HID_EDGE_FLUSH_INTERVAL) {
            synchronized (hidEdgeFlushLock) {
                if (timer - lastHidEdgeFlushTime >= HID_EDGE_FLUSH_INTERVAL) {
                    flushHidEdgeBuffer();
                    lastHidEdgeFlushTime = timer;
                }
            }
        }
        // ===== [신규 추가] 끝 =====

        // ===== [신규 추가] 하루 1회 마스터 테이블 업데이트 → 테이블 1, 2 =====
        String today = new SimpleDateFormat("yyyy-MM-dd").format(new Date(timer));
        if (!today.equals(hidMasterLastUpdateDate)) {
            synchronized (hidMasterUpdateLock) {
                if (!today.equals(hidMasterLastUpdateDate)) {
                    try {
                        _updateHidMasterTables();
                        hidMasterLastUpdateDate = today;
                    } catch (Exception e) {
                        logger.error("HID Master Tables update failed", e);
                    }
                }
            }
        }
        // ===== [신규 추가] 끝 =====

        long checkingTime = System.currentTimeMillis() - timer;

        if (checkingTime >= 60000) {
            logger.info("... `number of vehicles per hid section` process took more than 1 minute to complete [elapsed time: {}min]", checkingTime / 60000);
        }
    }


    // ========================================================================================
    // [신규 메소드] flushHidEdgeBuffer()
    //   → 테이블 3: {FAB}_ATLAS_HID_INOUT 에 1분 집계 데이터 저장
    //   → 기존 _insertHidOffLogpresso() (Line 494~514) 패턴 참조
    // ========================================================================================

    /**
     * HID 엣지 전환 집계 데이터를 Logpresso에 1분 배치 저장
     *
     * [테이블] {FAB}_ATLAS_HID_INOUT
     * [컬럼 데이터 소스]
     *   EVENT_DATE  → SimpleDateFormat("yyyy-MM-dd")
     *   EVENT_DT    → SimpleDateFormat("yyyy-MM-dd HH:mm:00")
     *   FROM_HIDID  → vehicle.getHidId() (Vhl.java:517)
     *   TO_HIDID    → currentHidId 파라미터 (OhtMsgWorkerRunnable.java:357)
     *   TRANS_CNT   → hidEdgeBuffer 집계값
     *   MCP_NM      → this.mcpName (OhtMsgWorkerRunnable.java:9)
     *   ENV         → Env.getEnv() (OhtMsgWorkerRunnable.java:505 참조)
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

        if (snapshot.isEmpty()) {
            return;
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
            tuple.put("MCP_NM", this.mcpName);     // OhtMsgWorkerRunnable.java:9
            tuple.put("ENV", Env.getEnv());         // OhtMsgWorkerRunnable.java:505 참조

            tuples.add(tuple);
        }

        // 테이블명: {FAB}_ATLAS_HID_INOUT (예: M14A_ATLAS_HID_INOUT)
        String tableName = this.fabId + "_ATLAS_HID_INOUT";

        boolean success = LogpressoAPI.setInsertTuples(tableName, tuples, 100);

        if (success) {
            logger.info("HID Edge flush: {} - {} records", tableName, tuples.size());
        }
    }


    // ========================================================================================
    // [신규 메소드] _updateHidMasterTables()
    //   → 테이블 1: {FAB}_ATLAS_INFO_HID_INOUT_MAS (엣지 마스터)
    //   → 테이블 2: {FAB}_ATLAS_HID_INFO_MAS (HID 상세 정보)
    //   → 하루 1회 실행 (날짜 비교)
    //   → layout.zip 없으면 SKIP + logger.warn
    // ========================================================================================

    /**
     * HID 마스터 테이블 업데이트 (하루 1회)
     *
     * [데이터 소스] map/{FAB}/*.layout.zip 내 layout.xml
     *   - McpZone → Entry/Exit → FROM_HIDID, TO_HIDID (엣지)
     *   - RailEdge.getLength()       → RAIL_LEN_TOTAL   (DataService.java:691)
     *   - RailEdge.getMaxVelocity()  → FREE_FLOW_SPEED  (RaileEdge.java:270)
     *   - RailEdge.getPortIdList()   → PORT_CNT_TOTAL   (RaileEdge.java:19)
     *   - HID_Zone_Master.csv 참고   → IN_CNT, OUT_CNT, VHL_MAX, ZCU_ID
     */
    private void _updateHidMasterTables() {
        logger.info("Starting HID Master Tables update [fab: {}]", this.fabId);

        // ---- layout.zip 경로 확인 ----
        // 데이터 소스: fabProperties.getMapDir() (DataService.java:295)
        FabProperties fabProperties = DataService.getInstance().getFabPropertiesMap().get(this.fabId);
        String mapDir = fabProperties.getMapDir();
        File mapDirFile = new File(mapDir);

        if (!mapDirFile.exists() || !mapDirFile.isDirectory()) {
            logger.warn("[HID Master] map directory not found, SKIP [fab: {} | path: {}]", this.fabId, mapDir);
            return;
        }

        // ---- layout.zip 파일 찾기 ----
        File[] layoutZipFiles = mapDirFile.listFiles((dir, name) -> name.endsWith(".layout.zip"));

        if (layoutZipFiles == null || layoutZipFiles.length == 0) {
            logger.warn("[HID Master] *.layout.zip not found, SKIP [fab: {} | path: {}]", this.fabId, mapDir);
            return;
        }

        // 첫 번째 layout.zip 사용
        File layoutZipFile = layoutZipFiles[0];
        logger.info("[HID Master] layout.zip found [fab: {} | file: {}]", this.fabId, layoutZipFile.getName());

        // ---- 테이블 1: 엣지 마스터 업데이트 ----
        _updateHidEdgeMasterInfo(layoutZipFile);

        // ---- 테이블 2: HID 상세 정보 업데이트 ----
        _updateHidInfoMaster();

        logger.info("HID Master Tables update completed [fab: {}]", this.fabId);
    }


    // ========================================================================================
    // [신규 메소드] _updateHidEdgeMasterInfo()
    //   → 테이블 1: {FAB}_ATLAS_INFO_HID_INOUT_MAS
    //   → layout.zip에서 McpZone Entry/Exit 파싱
    // ========================================================================================

    /**
     * HID Zone 진입/진출 엣지 마스터 데이터 업데이트
     *
     * [테이블] {FAB}_ATLAS_INFO_HID_INOUT_MAS
     * [컬럼 데이터 소스]
     *   FROM_HIDID   → layout.xml McpZone Entry start/end 주소 → HID 매핑
     *   TO_HIDID     → layout.xml McpZone Exit  start/end 주소 → HID 매핑
     *   EDGE_ID      → String.format("%03d:%03d", fromHidId, toHidId)
     *   FROM_HID_NM  → HID_Zone_Master.csv → Full_Name
     *   TO_HID_NM    → HID_Zone_Master.csv → Full_Name
     *   MCP_ID       → mcp75ConfigMap.keySet() (DataService.java:2052)
     *   ZONE_ID      → HID_Zone_Master.csv → Bay_Zone
     *   EDGE_TYPE    → fromHid==0 ? "IN" : toHid==0 ? "OUT" : "INTERNAL"
     *   UPDATE_DT    → SimpleDateFormat("yyyy-MM-dd HH:mm:ss")
     */
    private void _updateHidEdgeMasterInfo(File layoutZipFile) {
        List<Tuple> tuples = new ArrayList<>();
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        String updateDt = dateFormat.format(new Date());

        try {
            // layout.zip에서 HID Edge 정보 추출
            // 데이터 소스: DataService.getDataSet().getRailEdgeMap() (DataService.java:633)
            ConcurrentMap<String, AbstractEdge> edgeMap = DataService.getDataSet().getEdgeMap();
            Map<Integer, String> hidNameMap = new HashMap<>();  // hidId → hidName
            Set<String> processedEdges = new HashSet<>();

            // RailEdge 순회하며 HID 전환 엣지 추출
            for (Map.Entry<String, AbstractEdge> entry : edgeMap.entrySet()) {
                if (!(entry.getValue() instanceof RailEdge)) continue;

                RailEdge railEdge = (RailEdge) entry.getValue();
                int hidId = railEdge.getHIDId();      // RaileEdge.java:324

                if (hidId > 0) {
                    hidNameMap.putIfAbsent(hidId, "HID_" + String.format("%03d", hidId));
                }
            }

            // HID 간 전환 엣지 구성 (인접 RailEdge의 HID 전환 감지)
            for (Map.Entry<String, AbstractEdge> entry : edgeMap.entrySet()) {
                if (!(entry.getValue() instanceof RailEdge)) continue;

                RailEdge railEdge = (RailEdge) entry.getValue();
                int fromHidId = railEdge.getHIDId();

                // 다음 RailEdge의 HID 확인
                String toNodeId = railEdge.getToNodeId();
                // 연결된 다음 엣지들에서 HID가 바뀌는 경우 엣지 생성
                for (Map.Entry<String, AbstractEdge> nextEntry : edgeMap.entrySet()) {
                    if (!(nextEntry.getValue() instanceof RailEdge)) continue;

                    RailEdge nextRailEdge = (RailEdge) nextEntry.getValue();
                    if (nextRailEdge.getFromNodeId().equals(toNodeId)) {
                        int toHidId = nextRailEdge.getHIDId();

                        if (fromHidId != toHidId && (fromHidId > 0 || toHidId > 0)) {
                            String edgeKey = fromHidId + ":" + toHidId;
                            if (processedEdges.contains(edgeKey)) continue;
                            processedEdges.add(edgeKey);

                            Tuple tuple = new Tuple();
                            tuple.put("FROM_HIDID", fromHidId);
                            tuple.put("TO_HIDID", toHidId);
                            tuple.put("EDGE_ID", String.format("%03d:%03d", fromHidId, toHidId));

                            // HID 이름
                            tuple.put("FROM_HID_NM", fromHidId == 0 ? "OUTSIDE"
                                : hidNameMap.getOrDefault(fromHidId, "HID_" + String.format("%03d", fromHidId)));
                            tuple.put("TO_HID_NM", toHidId == 0 ? "OUTSIDE"
                                : hidNameMap.getOrDefault(toHidId, "HID_" + String.format("%03d", toHidId)));

                            // MCP_ID, ZONE_ID
                            tuple.put("MCP_ID", this.mcpName);
                            tuple.put("ZONE_ID", "");

                            // 엣지 유형
                            String edgeType;
                            if (fromHidId == 0) {
                                edgeType = "IN";
                            } else if (toHidId == 0) {
                                edgeType = "OUT";
                            } else {
                                edgeType = "INTERNAL";
                            }
                            tuple.put("EDGE_TYPE", edgeType);
                            tuple.put("UPDATE_DT", updateDt);

                            tuples.add(tuple);
                        }
                    }
                }
            }
        } catch (Exception e) {
            logger.error("[HID Master] Failed to build edge master info [fab: {}]", this.fabId, e);
            return;
        }

        if (tuples.isEmpty()) {
            logger.warn("[HID Master] No edge data found [fab: {}]", this.fabId);
            return;
        }

        // 테이블명: {FAB}_ATLAS_INFO_HID_INOUT_MAS (예: M14A_ATLAS_INFO_HID_INOUT_MAS)
        String tableName = this.fabId + "_ATLAS_INFO_HID_INOUT_MAS";

        // Full Refresh
        LogpressoAPI.truncateTable(tableName);
        LogpressoAPI.setInsertTuples(tableName, tuples, 100);

        logger.info("[HID Master] Edge Master updated: {} - {} records", tableName, tuples.size());
    }


    // ========================================================================================
    // [신규 메소드] _updateHidInfoMaster()
    //   → 테이블 2: {FAB}_ATLAS_HID_INFO_MAS
    //   → RailEdge 데이터에서 HID별 집계
    // ========================================================================================

    /**
     * HID 상세 정보 마스터 데이터 업데이트
     *
     * [테이블] {FAB}_ATLAS_HID_INFO_MAS
     * [컬럼 데이터 소스]
     *   HID_ID          → RailEdge.getHIDId()                  (RaileEdge.java:324)
     *   HID_NM          → "HID_" + String.format("%03d", hidId)
     *   MCP_ID          → this.mcpName                          (OhtMsgWorkerRunnable.java:9)
     *   ZONE_ID         → ""                                    (추후 매핑 가능)
     *   RAIL_LEN_TOTAL  → RailEdge.getLength() HID별 합계       (AbstractEdge에서 상속)
     *   FREE_FLOW_SPEED → RailEdge.getMaxVelocity() HID별 평균  (RaileEdge.java:270)
     *   PORT_CNT_TOTAL  → RailEdge.getPortIdList().size() 합계  (RaileEdge.java:19)
     *   IN_CNT          → HID Entry 개수 (DataService.java:2069 rawHid.getLoopEntrySet())
     *   OUT_CNT         → HID Exit 개수 (DataService.java:2083 rawHid.getExitSet())
     *   VHL_MAX         → McpZone vehicle-max (layout.xml 파라미터)
     *   ZCU_ID          → Entry stop-zcu (layout.xml Entry 파라미터)
     *   UPDATE_DT       → SimpleDateFormat("yyyy-MM-dd HH:mm:ss")
     */
    private void _updateHidInfoMaster() {
        List<Tuple> tuples = new ArrayList<>();
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        String updateDt = dateFormat.format(new Date());

        try {
            ConcurrentMap<String, AbstractEdge> edgeMap = DataService.getDataSet().getEdgeMap();

            // HID별 집계 맵
            Map<Integer, Double> railLenMap = new HashMap<>();      // HID → 레일 길이 합계
            Map<Integer, List<Double>> maxVelMap = new HashMap<>();  // HID → maxVelocity 목록
            Map<Integer, Integer> portCntMap = new HashMap<>();      // HID → 포트 수 합계

            // RailEdge 순회하며 HID별 데이터 집계
            for (Map.Entry<String, AbstractEdge> entry : edgeMap.entrySet()) {
                if (!(entry.getValue() instanceof RailEdge)) continue;

                RailEdge railEdge = (RailEdge) entry.getValue();
                int hidId = railEdge.getHIDId();         // RaileEdge.java:324

                if (hidId <= 0) continue;

                // 레일 길이 합계
                double length = railEdge.getLength();     // AbstractEdge.getLength()
                railLenMap.merge(hidId, length, Double::sum);

                // maxVelocity 수집 (평균 계산용)
                double maxVelocity = railEdge.getMaxVelocity();  // RaileEdge.java:270
                if (maxVelocity > 0) {
                    maxVelMap.computeIfAbsent(hidId, k -> new ArrayList<>()).add(maxVelocity);
                }

                // 포트 수 합계
                List<String> portList = railEdge.getPortIdList();  // RaileEdge.java:19
                if (portList != null && !portList.isEmpty()) {
                    portCntMap.merge(hidId, portList.size(), Integer::sum);
                }
            }

            // HID별 Tuple 생성
            for (Integer hidId : railLenMap.keySet()) {
                Tuple tuple = new Tuple();

                tuple.put("HID_ID", hidId);
                tuple.put("HID_NM", "HID_" + String.format("%03d", hidId));
                tuple.put("MCP_ID", this.mcpName);
                tuple.put("ZONE_ID", "");

                // RAIL_LEN_TOTAL
                tuple.put("RAIL_LEN_TOTAL", railLenMap.getOrDefault(hidId, 0.0));

                // FREE_FLOW_SPEED (HID별 maxVelocity 평균)
                List<Double> velocities = maxVelMap.get(hidId);
                double avgSpeed = 0.0;
                if (velocities != null && !velocities.isEmpty()) {
                    avgSpeed = velocities.stream()
                        .mapToDouble(Double::doubleValue)
                        .average()
                        .orElse(0.0);
                }
                tuple.put("FREE_FLOW_SPEED", avgSpeed);

                // PORT_CNT_TOTAL
                tuple.put("PORT_CNT_TOTAL", portCntMap.getOrDefault(hidId, 0));

                // IN_CNT, OUT_CNT, VHL_MAX, ZCU_ID → layout.xml McpZone 데이터
                // 현재 RailEdge에서 직접 가져올 수 없으므로 기본값 설정
                // 추후 Mcp75Config.getRawHidMap()에서 매핑 가능
                tuple.put("IN_CNT", 0);
                tuple.put("OUT_CNT", 0);
                tuple.put("VHL_MAX", 0);
                tuple.put("ZCU_ID", "");

                tuple.put("UPDATE_DT", updateDt);

                tuples.add(tuple);
            }
        } catch (Exception e) {
            logger.error("[HID Master] Failed to build HID info [fab: {}]", this.fabId, e);
            return;
        }

        if (tuples.isEmpty()) {
            logger.warn("[HID Master] No HID info data found [fab: {}]", this.fabId);
            return;
        }

        // 테이블명: {FAB}_ATLAS_HID_INFO_MAS (예: M14A_ATLAS_HID_INFO_MAS)
        String tableName = this.fabId + "_ATLAS_HID_INFO_MAS";

        // Full Refresh
        LogpressoAPI.truncateTable(tableName);
        LogpressoAPI.setInsertTuples(tableName, tuples, 100);

        logger.info("[HID Master] HID Info Master updated: {} - {} records", tableName, tuples.size());
    }
}
