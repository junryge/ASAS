/**
 * HidMasterBatchJob.java — HID 마스터 테이블 하루 1회 업데이트 (Quartz Job)
 *
 * ※ 신규 파일 — TrafficBatch.java 패턴 참조
 * ※ Quartz 스케줄러에 등록하여 하루 1회 실행 (예: 0 0 1 * * ?)
 *
 * [테이블 매핑]
 *   테이블 1: {FAB}_ATLAS_INFO_HID_INOUT_MAS — 엣지 마스터 (HID 전환 엣지)
 *   테이블 2: {FAB}_ATLAS_HID_INFO_MAS       — HID 상세 정보 (레일길이/속도/포트)
 *
 * [데이터 소스]
 *   map/{FAB}/*.layout.zip → layout.xml 파싱 (McpZone Entry/Exit)
 *   RailEdge 런타임 데이터 → 레일길이, maxVelocity, 포트수 집계
 *
 * [참고 패턴]
 *   TrafficBatch.java — Env.getSwitchMap() 순회, Quartz Job 인터페이스
 */
public class HidMasterBatchJob implements Job {
    private final Logger logger = LoggerFactory.getLogger(getClass());
    private final int DELAYED_TIME = 1000 * 60;

    @Override
    public void execute(JobExecutionContext arg0) throws JobExecutionException {
        if (Util.isCurrentIC()) {
            // ---- TrafficBatch.java 패턴: Env.getSwitchMap() 순회 ----
            for (Map.Entry<String, FunctionItem> functionItemEntry : Env.getSwitchMap().entrySet()) {
                String key = functionItemEntry.getKey();     // {fabId}:{mcpName}
                FunctionItem functionItem = functionItemEntry.getValue();

                if (functionItem != null) {
                    String fabId   = functionItem.getFabId();
                    String mcpName = functionItem.getMcpName();

                    logger.info("... `HidMasterBatchJob` has started [fab: {} | mcp: {}]", fabId, mcpName);

                    long timer = System.currentTimeMillis();

                    _run(fabId, mcpName);

                    long checkTimer = System.currentTimeMillis() - timer;

                    if (checkTimer >= DELAYED_TIME) {
                        logger.error("... !!!DELAYED!!! `HidMasterBatchJob` has finished [fab: {} | mcp: {}] [elapsed time: {}m ({}ms)]",
                                fabId, mcpName, checkTimer / (60 * 1000), checkTimer);
                    } else {
                        logger.info("... `HidMasterBatchJob` has finished [fab: {} | mcp: {}] [elapsed time: {}ms]",
                                fabId, mcpName, checkTimer);
                    }
                }
            }
        }
    }


    // ========================================================================================
    // _run() — FAB별 마스터 테이블 업데이트
    // ========================================================================================

    private void _run(String fabId, String mcpName) {
        try {
            // ---- layout.zip 경로 확인 ----
            // 데이터 소스: fabProperties.getMapDir() (DataService.java:295)
            FabProperties fabProperties = DataService.getInstance().getFabPropertiesMap().get(fabId);

            if (fabProperties == null) {
                logger.warn("[HID Master] FabProperties not found, SKIP [fab: {}]", fabId);
                return;
            }

            String mapDir = fabProperties.getMapDir();
            File mapDirFile = new File(mapDir);

            if (!mapDirFile.exists() || !mapDirFile.isDirectory()) {
                logger.warn("[HID Master] map directory not found, SKIP [fab: {} | path: {}]", fabId, mapDir);
                return;
            }

            // ---- layout.zip 파일 찾기 ----
            // map/{FAB}/*.layout.zip (예: map/M14A/M14A.layout.zip)
            File[] layoutZipFiles = mapDirFile.listFiles((dir, name) -> name.endsWith(".layout.zip"));

            if (layoutZipFiles == null || layoutZipFiles.length == 0) {
                logger.warn("[HID Master] *.layout.zip not found, SKIP [fab: {} | path: {}]", fabId, mapDir);
                return;
            }

            // 첫 번째 layout.zip 사용
            File layoutZipFile = layoutZipFiles[0];
            logger.info("[HID Master] layout.zip found [fab: {} | file: {}]", fabId, layoutZipFile.getName());

            // ---- 테이블 1: 엣지 마스터 업데이트 ----
            _updateHidEdgeMasterInfo(fabId, mcpName, layoutZipFile);

            // ---- 테이블 2: HID 상세 정보 업데이트 ----
            _updateHidInfoMaster(fabId, mcpName);

        } catch (Exception e) {
            logger.error("[HID Master] Failed [fab: {}]", fabId, e);
        }
    }


    // ========================================================================================
    // 테이블 1: {FAB}_ATLAS_INFO_HID_INOUT_MAS
    //   → HID Zone 진입/진출 엣지 마스터 데이터
    //   → RailEdge 순회하며 HID 전환 엣지 감지
    //
    // [컬럼 데이터 소스]
    //   FROM_HIDID   → RailEdge.getHIDId() 현재 엣지 (RaileEdge.java:324)
    //   TO_HIDID     → 다음 RailEdge.getHIDId() (toNode 연결)
    //   EDGE_ID      → String.format("%03d:%03d", fromHidId, toHidId)
    //   FROM_HID_NM  → "HID_" + String.format("%03d", fromHidId)
    //   TO_HID_NM    → "HID_" + String.format("%03d", toHidId)
    //   MCP_ID       → mcpName 파라미터
    //   ZONE_ID      → 추후 매핑 가능
    //   EDGE_TYPE    → fromHid==0 ? "IN" : toHid==0 ? "OUT" : "INTERNAL"
    //   UPDATE_DT    → SimpleDateFormat("yyyy-MM-dd HH:mm:ss")
    // ========================================================================================

    private void _updateHidEdgeMasterInfo(String fabId, String mcpName, File layoutZipFile) {
        List<Tuple> tuples = new ArrayList<>();
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        String updateDt = dateFormat.format(new Date());

        try {
            // DataService.getDataSet().getEdgeMap() 에서 RailEdge 순회
            ConcurrentMap<String, AbstractEdge> edgeMap = DataService.getDataSet().getEdgeMap();
            Map<Integer, String> hidNameMap = new HashMap<>();  // hidId → hidName
            Set<String> processedEdges = new HashSet<>();

            // 1단계: RailEdge 순회하며 FAB에 해당하는 HID 정보 수집
            for (Map.Entry<String, AbstractEdge> entry : edgeMap.entrySet()) {
                if (!(entry.getValue() instanceof RailEdge)) continue;

                RailEdge railEdge = (RailEdge) entry.getValue();

                // FAB 필터 — 해당 FAB 소속 RailEdge만 처리
                if (!railEdge.getFabId().equals(fabId)) continue;

                int hidId = railEdge.getHIDId();  // RaileEdge.java:324

                if (hidId > 0) {
                    hidNameMap.putIfAbsent(hidId, "HID_" + String.format("%03d", hidId));
                }
            }

            // 2단계: HID 간 전환 엣지 구성 (인접 RailEdge의 HID 전환 감지)
            for (Map.Entry<String, AbstractEdge> entry : edgeMap.entrySet()) {
                if (!(entry.getValue() instanceof RailEdge)) continue;

                RailEdge railEdge = (RailEdge) entry.getValue();
                if (!railEdge.getFabId().equals(fabId)) continue;

                int fromHidId = railEdge.getHIDId();
                String toNodeId = railEdge.getToNodeId();

                // 연결된 다음 엣지들에서 HID가 바뀌는 경우 엣지 생성
                for (Map.Entry<String, AbstractEdge> nextEntry : edgeMap.entrySet()) {
                    if (!(nextEntry.getValue() instanceof RailEdge)) continue;

                    RailEdge nextRailEdge = (RailEdge) nextEntry.getValue();
                    if (!nextRailEdge.getFabId().equals(fabId)) continue;

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

                            tuple.put("MCP_ID", mcpName);
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
            logger.error("[HID Master] Failed to build edge master info [fab: {}]", fabId, e);
            return;
        }

        if (tuples.isEmpty()) {
            logger.warn("[HID Master] No edge data found [fab: {}]", fabId);
            return;
        }

        // 테이블명: {FAB}_ATLAS_INFO_HID_INOUT_MAS (예: M14A_ATLAS_INFO_HID_INOUT_MAS)
        String tableName = fabId + "_ATLAS_INFO_HID_INOUT_MAS";

        // Full Refresh
        LogpressoAPI.truncateTable(tableName);
        LogpressoAPI.setInsertTuples(tableName, tuples, 100);

        logger.info("[HID Master] Edge Master updated: {} - {} records", tableName, tuples.size());
    }


    // ========================================================================================
    // 테이블 2: {FAB}_ATLAS_HID_INFO_MAS
    //   → HID 상세 정보 마스터 데이터
    //   → RailEdge 런타임 데이터에서 HID별 집계
    //
    // [컬럼 데이터 소스]
    //   HID_ID          → RailEdge.getHIDId()                  (RaileEdge.java:324)
    //   HID_NM          → "HID_" + String.format("%03d", hidId)
    //   MCP_ID          → mcpName 파라미터
    //   ZONE_ID         → 추후 매핑 가능
    //   RAIL_LEN_TOTAL  → RailEdge.getLength() HID별 합계       (AbstractEdge 상속)
    //   FREE_FLOW_SPEED → RailEdge.getMaxVelocity() HID별 평균  (RaileEdge.java:270)
    //   PORT_CNT_TOTAL  → RailEdge.getPortIdList().size() 합계  (RaileEdge.java:19)
    //   IN_CNT          → layout.xml McpZone Entry 개수 (추후 매핑)
    //   OUT_CNT         → layout.xml McpZone Exit 개수 (추후 매핑)
    //   VHL_MAX         → layout.xml McpZone vehicle-max (추후 매핑)
    //   ZCU_ID          → layout.xml Entry stop-zcu (추후 매핑)
    //   UPDATE_DT       → SimpleDateFormat("yyyy-MM-dd HH:mm:ss")
    // ========================================================================================

    private void _updateHidInfoMaster(String fabId, String mcpName) {
        List<Tuple> tuples = new ArrayList<>();
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        String updateDt = dateFormat.format(new Date());

        try {
            ConcurrentMap<String, AbstractEdge> edgeMap = DataService.getDataSet().getEdgeMap();

            // HID별 집계 맵
            Map<Integer, Double> railLenMap = new HashMap<>();       // HID → 레일 길이 합계
            Map<Integer, List<Double>> maxVelMap = new HashMap<>();   // HID → maxVelocity 목록
            Map<Integer, Integer> portCntMap = new HashMap<>();       // HID → 포트 수 합계

            // RailEdge 순회하며 FAB에 해당하는 HID별 데이터 집계
            for (Map.Entry<String, AbstractEdge> entry : edgeMap.entrySet()) {
                if (!(entry.getValue() instanceof RailEdge)) continue;

                RailEdge railEdge = (RailEdge) entry.getValue();

                // FAB 필터
                if (!railEdge.getFabId().equals(fabId)) continue;

                int hidId = railEdge.getHIDId();  // RaileEdge.java:324
                if (hidId <= 0) continue;

                // 레일 길이 합계
                double length = railEdge.getLength();  // AbstractEdge.getLength()
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
                tuple.put("MCP_ID", mcpName);
                tuple.put("ZONE_ID", "");

                // RAIL_LEN_TOTAL
                tuple.put("RAIL_LEN_TOTAL", railLenMap.getOrDefault(hidId, 0.0));

                // FREE_FLOW_SPEED (HID별 maxVelocity 평균)
                List<Double> velocities = maxVelMap.get(hidId);
                double avgSpeed = 0.0;
                if (velocities != null && !velocities.isEmpty()) {
                    double sum = 0.0;
                    for (Double v : velocities) {
                        sum += v;
                    }
                    avgSpeed = sum / velocities.size();
                }
                tuple.put("FREE_FLOW_SPEED", avgSpeed);

                // PORT_CNT_TOTAL
                tuple.put("PORT_CNT_TOTAL", portCntMap.getOrDefault(hidId, 0));

                // IN_CNT, OUT_CNT, VHL_MAX, ZCU_ID → layout.xml McpZone 데이터
                // 추후 Mcp75Config.getRawHidMap()에서 매핑 가능
                tuple.put("IN_CNT", 0);
                tuple.put("OUT_CNT", 0);
                tuple.put("VHL_MAX", 0);
                tuple.put("ZCU_ID", "");

                tuple.put("UPDATE_DT", updateDt);

                tuples.add(tuple);
            }
        } catch (Exception e) {
            logger.error("[HID Master] Failed to build HID info [fab: {}]", fabId, e);
            return;
        }

        if (tuples.isEmpty()) {
            logger.warn("[HID Master] No HID info data found [fab: {}]", fabId);
            return;
        }

        // 테이블명: {FAB}_ATLAS_HID_INFO_MAS (예: M14A_ATLAS_HID_INFO_MAS)
        String tableName = fabId + "_ATLAS_HID_INFO_MAS";

        // Full Refresh
        LogpressoAPI.truncateTable(tableName);
        LogpressoAPI.setInsertTuples(tableName, tuples, 100);

        logger.info("[HID Master] HID Info Master updated: {} - {} records", tableName, tuples.size());
    }
}
