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

    // --- 테이블 1,2: 마스터 테이블은 별도 Quartz Job (HidMasterBatchJob.java) 에서 처리 ---


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

        // ※ 테이블 1, 2 마스터 업데이트는 별도 HidMasterBatchJob.java (Quartz Job)에서 처리

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
    // 테이블 1, 2 마스터 업데이트는 별도 HidMasterBatchJob.java (Quartz Job)에서 처리
    //   → 테이블 1: {FAB}_ATLAS_INFO_HID_INOUT_MAS
    //   → 테이블 2: {FAB}_ATLAS_HID_INFO_MAS
    //   → 참조: JAVA_TOEB/SRC/HidMasterBatchJob.java
    // ========================================================================================
}
