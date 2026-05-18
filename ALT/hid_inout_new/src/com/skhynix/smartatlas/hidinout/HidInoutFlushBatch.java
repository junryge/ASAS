package com.skhynix.smartatlas.hidinout;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.logging.log4j.util.Strings;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.environment.type.FunctionItem;
import com.skhynix.smartatlas.environment.type.FunctionItem.FunctionType;
import com.skhynix.smartatlas.util.DataService;

/**
 * 1분 단위로 HidInoutCollector 의 누적 데이터를 {FAB}_ATLAS_HID_INOUT 에 적재한다.
 *
 * 기존 HidEdgeInOutQueueFlushBatch 대비 변경점:
 *  1) atomic swap (HidInoutCollector.drain) — 카운트 손실/이중집계 제거
 *  2) FAB 별로 처리하다가 빈 fabId 만나도 전체 return 하지 않음 (개별 skip)
 *  3) HID_INOUT 스위치 OFF 인 mcp 의 데이터는 적재 단계에서 한 번 더 필터링
 *  4) 적재 실패 시 mergeBack 으로 다음 사이클에 합쳐 재시도
 *  5) 컬럼명/테이블명은 HidInoutTableSchema 상수 사용
 *  6) Quartz 예외 전파 시 컨테이너가 재실행하도록 JobExecutionException 으로 래핑
 */
public class HidInoutFlushBatch implements Job {

    private static final Logger logger = LoggerFactory.getLogger(HidInoutFlushBatch.class);

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        if (DataService.getInstance() == null || !DataService.getInstance().getInitialized()) {
            return;
        }

        long t0 = System.currentTimeMillis();
        Map<HidInoutEventKey, HidInoutAggregate> drained = HidInoutCollector.getInstance().drain();

        if (drained.isEmpty()) {
            logger.info("[HID INOUT] flush: nothing to write");
            return;
        }

        SimpleDateFormat dtFmt   = new SimpleDateFormat("yyyy-MM-dd HH:mm:00");
        SimpleDateFormat dateFmt = new SimpleDateFormat("yyyy-MM-dd");
        Date now = new Date();
        String eventDt   = dtFmt.format(now);
        String eventDate = dateFmt.format(now);
        String envName   = Env.getEnv();

        Map<String, List<Tuple>> tuplesByFab        = new HashMap<>();
        Map<String, List<Map.Entry<HidInoutEventKey, HidInoutAggregate>>> sourceByFab = new HashMap<>();

        for (Map.Entry<HidInoutEventKey, HidInoutAggregate> entry : drained.entrySet()) {
            HidInoutEventKey key = entry.getKey();
            HidInoutAggregate agg = entry.getValue();
            int transCnt = agg.getTransCnt();
            if (transCnt <= 0) continue;

            String fabId   = key.getFabId();
            String mcpName = key.getMcpName();

            if (Strings.isBlank(fabId)) {
                logger.debug("[HID INOUT] skip row: blank fabId in key [{}]", key);
                continue;
            }
            if (!isHidInoutEnabled(fabId, mcpName)) {
                continue;
            }

            Tuple t = new Tuple();
            t.put(HidInoutTableSchema.COL_EVENT_DATE,      eventDate);
            t.put(HidInoutTableSchema.COL_EVENT_DT,        eventDt);
            t.put(HidInoutTableSchema.COL_FROM_HIDID,      key.getFromHidId());
            t.put(HidInoutTableSchema.COL_TO_HIDID,        key.getToHidId());
            t.put(HidInoutTableSchema.COL_TRANS_CNT,       transCnt);
            t.put(HidInoutTableSchema.COL_FAB_ID,          key.getVhlFabId());
            t.put(HidInoutTableSchema.COL_VHL_ID,          key.getVhlId());
            t.put(HidInoutTableSchema.COL_EQP_ID,          key.getEqpId());
            t.put(HidInoutTableSchema.COL_MCP_NM,          mcpName);
            t.put(HidInoutTableSchema.COL_ENV,             envName);
            t.put(HidInoutTableSchema.COL_VHL_COUNT_LIMIT, agg.getVhlCountLimit());
            t.put(HidInoutTableSchema.COL_VHL_PRECAUTION,  agg.getVhlPrecaution());
            t.put(HidInoutTableSchema.COL_FREE_FLOW_SPEED, agg.getFreeFlowSpeed());
            t.put(HidInoutTableSchema.COL_HID_VALUE,       agg.getHidValue());

            tuplesByFab.computeIfAbsent(fabId, k -> new ArrayList<>()).add(t);
            sourceByFab.computeIfAbsent(fabId, k -> new ArrayList<>()).add(entry);
        }

        int totalInserted = 0;
        Map<HidInoutEventKey, HidInoutAggregate> retryBucket = new HashMap<>();

        for (Map.Entry<String, List<Tuple>> e : tuplesByFab.entrySet()) {
            String fabId  = e.getKey();
            List<Tuple> tuples = e.getValue();
            String tableName = HidInoutTableSchema.tableInout(fabId);

            boolean ok = insertWithRetry(tableName, tuples);
            if (ok) {
                totalInserted += tuples.size();
                logger.info("[HID INOUT] flushed {} rows -> {}", tuples.size(), tableName);
            } else {
                logger.error("[HID INOUT] flush failed after retries -> {} ({} rows queued for retry)",
                        tableName, tuples.size());
                for (Map.Entry<HidInoutEventKey, HidInoutAggregate> src : sourceByFab.get(fabId)) {
                    retryBucket.put(src.getKey(), src.getValue());
                }
            }
        }

        if (!retryBucket.isEmpty()) {
            HidInoutCollector.getInstance().mergeBack(retryBucket);
        }

        logger.info("[HID INOUT] flush done: inserted={}, retryQueued={}, elapsed={}ms",
                totalInserted, retryBucket.size(), System.currentTimeMillis() - t0);
    }

    private boolean isHidInoutEnabled(String fabId, String mcpName) {
        FunctionItem fi = Env.getSwitchMap().get(fabId + ":" + mcpName);
        return fi != null && fi.getUseFunction(FunctionType.HID_INOUT);
    }

    private boolean insertWithRetry(String tableName, List<Tuple> tuples) {
        long backoff = HidInoutTableSchema.FLUSH_RETRY_BASE_MS;
        for (int attempt = 1; attempt <= HidInoutTableSchema.FLUSH_RETRY_MAX; attempt++) {
            try {
                boolean ok = LogpressoAPI.setInsertTuples(
                        tableName, tuples, HidInoutTableSchema.INSERT_BATCH_SIZE);
                if (ok) return true;
            } catch (Exception ex) {
                logger.warn("[HID INOUT] insert exception (attempt {}/{}): {}",
                        attempt, HidInoutTableSchema.FLUSH_RETRY_MAX, ex.toString());
            }
            if (attempt < HidInoutTableSchema.FLUSH_RETRY_MAX) {
                try { Thread.sleep(backoff); } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    return false;
                }
                backoff *= 2;
            }
        }
        return false;
    }
}
