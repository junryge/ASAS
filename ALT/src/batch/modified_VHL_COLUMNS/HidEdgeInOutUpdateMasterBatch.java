public class HidEdgeInOutUpdateMasterBatch implements Job {

	private static final Logger logger = LoggerFactory.getLogger(HidEdgeInOutUpdateMasterBatch.class);
	
	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		if (DataService.getInstance() == null || !DataService.getInstance().getInitialized()) {
			return;
		}
		
		for (var fabPropertiesEntry : DataService.getInstance().getFabPropertiesMap().entrySet()) {
			var fabId = fabPropertiesEntry.getKey();
			var fabProperties = fabPropertiesEntry.getValue();
			
			logger.info("Starting HID Master Tables update [fab: {}]", fabId);

	        // ---- layout.zip 경로 확인 ----
	        // 데이터 소스: fabProperties.getMapDir() (DataService.java:295)x
	        if (fabProperties == null) {
	            logger.warn("[HID Master] FabProperties not found, SKIP [fab: {}]", fabId);
	            continue;
	        }
	        
	        String mapDir = fabProperties.getMapDir();
	        File mapDirFile = new File(mapDir);

	        if (!mapDirFile.exists() || !mapDirFile.isDirectory()) {
	            logger.warn("[HID Master] map directory not found, SKIP [fab: {} | path: {}]", fabId, mapDir);
	            continue;
	        }

	        // ---- layout.zip 파일 찾기 ----
	        File[] layoutZipFiles = mapDirFile.listFiles((dir, name) -> name.endsWith(".layout.zip"));

	        if (layoutZipFiles == null || layoutZipFiles.length == 0) {
	            logger.warn("[HID Master] *.layout.zip not found, SKIP [fab: {} | path: {}]", fabId, mapDir);
	            continue;
	        }

	        // 첫 번째 layout.zip 사용
	        File layoutZipFile = layoutZipFiles[0];
	        logger.info("[HID Master] layout.zip found [fab: {} | file: {}]", fabId, layoutZipFile.getName());

	        var edgeMapCopied = new HashMap<>(DataService.getDataSet().getEdgeMap());
	        var edgeMapFiltered = edgeMapCopied.entrySet().stream()
	        	.filter(e -> e.getValue() instanceof RailEdge && e.getValue().getFabId().equals(fabId))
	        	.collect(Collectors.toMap(e -> e.getKey(), e -> e.getValue()));
	        
	        for (String mcpName : fabProperties.getMcpPropertiesMap().keySet()) {
	        	FunctionItem functionItem = Env.getSwitchMap().get(fabId + ":" + mcpName);
	        	
	        	if (functionItem.getUseFunction(FunctionType.HID_INOUT) == false) {
	        		continue;
	        	}
	        	
	        	logger.info("[HID Master] HID Tables update start [fab: {} | mcpName: {}]", fabId, mcpName);
	        	
		        // ---- 테이블 1: 엣지 마스터 업데이트 ----
	        	_updateHidEdgeMasterInfo(fabId, mcpName, layoutZipFile, edgeMapFiltered);

	        	// ---- 테이블 2: HID 상세 정보 업데이트 ----
	        	_updateHidInfoMaster(fabId, mcpName, edgeMapFiltered);
	        	
	        	logger.info("HID Master Tables update completed [fab: {} | mcpName: {}]", fabId, mcpName);
	        }
		}
	}
	
	
	private void _updateHidEdgeMasterInfo(String fabId, String mcpName, File layoutZipFile, Map<String, AbstractEdge> edgeMap) {
        List<Tuple> tuples = new ArrayList<>();
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        String updateDt = dateFormat.format(new Date());

        try {
            var hidNameMap = new HashMap<Integer, String>();  // hidId → hidName
            var processedEdges = new HashSet<String>();

            // 1단계: RailEdge 순회하며 FAB에 해당하는 HID 정보 수집
            for (Map.Entry<String, AbstractEdge> entry : edgeMap.entrySet()) {
                RailEdge railEdge = (RailEdge) entry.getValue();

                int hidId = railEdge.getHIDId();  // RaileEdge.java:324

                if (hidId > 0) {
                    hidNameMap.putIfAbsent(hidId, "HID_" + String.format("%03d", hidId));
                }
            }

            // 2단계: HID 간 전환 엣지 구성 (인접 RailEdge의 HID 전환 감지)
            for (Map.Entry<String, AbstractEdge> entry : edgeMap.entrySet()) {
                RailEdge railEdge = (RailEdge) entry.getValue();

                int fromHidId = railEdge.getHIDId();
                String toNodeId = railEdge.getToNodeId();

                // 연결된 다음 엣지들에서 HID가 바뀌는 경우 엣지 생성
                for (Map.Entry<String, AbstractEdge> nextEntry : edgeMap.entrySet()) {
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
            logger.error("[HID Master] Failed to build edge master info [fab: {}, mcpName: {}]", fabId, mcpName, e);
            return;
        }

        if (tuples.isEmpty()) {
            logger.warn("[HID Master] No edge data found [fab: {}, mcpName: {}]", fabId, mcpName);
            return;
        }

        // 테이블명: {FAB}_ATLAS_INFO_HID_INOUT_MAS (예: M14A_ATLAS_INFO_HID_INOUT_MAS)
        String tableName = fabId + "_ATLAS_INFO_HID_INOUT_MAS";

        // Full Refresh: 기존 데이터 삭제 후 전체 재적재
        LogpressoAPI.truncateTable(tableName);
        LogpressoAPI.setInsertTuples(tableName, tuples, 100);

        logger.info("[HID Master] Edge Master updated: {} - {} records", tableName, tuples.size());
    }
	
    private void _updateHidInfoMaster(String fabId, String mcpName, Map<String, AbstractEdge> edgeMap) {
        List<Tuple> tuples = new ArrayList<>();
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        String updateDt = dateFormat.format(new Date());

        try {
            // HID별 집계 맵
            Map<Integer, Double> railLenMap = new HashMap<>();       // HID → 레일 길이 합계
            Map<Integer, List<Double>> maxVelMap = new HashMap<>();   // HID → maxVelocity 목록
            Map<Integer, Integer> portCntMap = new HashMap<>();       // HID → 포트 수 합계

            // RawHidMap에서 VHL_COUNT_LIMIT, VHL_PRECAUTION 조회
            Map<Integer, Integer> vhlCountLimitMap = new HashMap<>();  // HID → vhlMax
            Map<Integer, Integer> vhlPrecautionMap = new HashMap<>();  // HID → vhlPreCaution
            McpProperties mcpProperties = DataService.getInstance().getFabPropertiesMap().get(fabId).getMcpPropertiesMap().get(mcpName);
            if (mcpProperties != null && mcpProperties.getMcp75Config() != null) {
                for (RawHid rawHid : mcpProperties.getMcp75Config().getRawHidMap().values()) {
                    vhlCountLimitMap.put(rawHid.getId(), rawHid.getVhlMax());
                    vhlPrecautionMap.put(rawHid.getId(), rawHid.getVhlPreCaution());
                }
            }

            // RailEdge 순회하며 FAB에 해당하는 HID별 데이터 집계
            for (Map.Entry<String, AbstractEdge> entry : edgeMap.entrySet()) {
                RailEdge railEdge = (RailEdge) entry.getValue();

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

                // VHL_COUNT_LIMIT, VHL_PRECAUTION → RawHid (layout.xml VEHICLE_MAX, VEHICLE_PRECAUTION)
                tuple.put("VHL_COUNT_LIMIT", vhlCountLimitMap.getOrDefault(hidId, 0));
                tuple.put("VHL_PRECAUTION", vhlPrecautionMap.getOrDefault(hidId, 0));

                tuple.put("UPDATE_DT", updateDt);

                tuples.add(tuple);
            }
        } catch (Exception e) {
            logger.error("[HID Master] Failed to build HID info [fab: {}, mcpName: {}]", fabId, e);
            return;
        }

        if (tuples.isEmpty()) {
            logger.warn("[HID Master] No HID info data found [fab: {}, mcpName: {}]", fabId);
            return;
        }

        // 테이블명: {FAB}_ATLAS_HID_INFO_MAS (예: M14A_ATLAS_HID_INFO_MAS)
        String tableName = fabId + "_ATLAS_HID_INFO_MAS";

        // Full Refresh: 기존 데이터 삭제 후 전체 재적재
        LogpressoAPI.truncateTable(tableName);
        LogpressoAPI.setInsertTuples(tableName, tuples, 100);

        logger.info("[HID Master] HID Info Master updated: {} - {} records", tableName, tuples.size());
    }
}
