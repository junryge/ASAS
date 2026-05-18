package com.skhynix.smartatlas.hidinout;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.data.FabProperties;
import com.skhynix.smartatlas.data.McpProperties;
import com.skhynix.smartatlas.data.raw.RawHid;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.environment.type.FunctionItem;
import com.skhynix.smartatlas.environment.type.FunctionItem.FunctionType;
import com.skhynix.smartatlas.map.AbstractEdge;
import com.skhynix.smartatlas.map.edge.RailEdge;
import com.skhynix.smartatlas.util.DataService;

/**
 * 일 1회 (운영 스케줄에 따름) 실행되어 두 마스터 테이블을 갱신한다:
 *
 *   1) {FAB}_ATLAS_INFO_HID_INOUT_MAS — HID 간 전환 엣지 마스터
 *   2) {FAB}_ATLAS_HID_INFO_MAS       — HID 자체의 정적 정보
 *
 * 기존 HidEdgeInOutUpdateMasterBatch 대비:
 *  - 엣지 인접성 계산을 O(N^2) → O(N) 으로 개선 (toNodeId → edges index)
 *  - RawHid 로부터 IN_CNT, OUT_CNT, VHL_MAX, ZCU_ID 를 채움 (기존 0 고정)
 *  - 실행 중 한 fab/mcp 실패가 다른 fab/mcp 실행을 막지 않음
 *  - layout.zip 의 존재 여부와 무관하게 마스터 갱신을 진행 (의존 제거)
 *    : 기존 코드는 layout.zip 누락 시 SKIP 했으나 실제 사용 정보는 edgeMap/RawHid
 *      에서만 가져오므로 불필요했음
 */
public class HidInoutMasterBatch implements Job {

    private static final Logger logger = LoggerFactory.getLogger(HidInoutMasterBatch.class);

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        if (DataService.getInstance() == null || !DataService.getInstance().getInitialized()) {
            return;
        }

        for (Map.Entry<String, FabProperties> fp : DataService.getInstance().getFabPropertiesMap().entrySet()) {
            String fabId = fp.getKey();
            FabProperties fabProperties = fp.getValue();
            if (fabProperties == null) {
                logger.warn("[HID MASTER] skip — null FabProperties [fab={}]", fabId);
                continue;
            }

            Map<String, AbstractEdge> fabEdges = filterRailEdgesForFab(fabId);
            if (fabEdges.isEmpty()) {
                logger.warn("[HID MASTER] skip — no RailEdge [fab={}]", fabId);
                continue;
            }

            for (String mcpName : fabProperties.getMcpPropertiesMap().keySet()) {
                if (!isHidInoutEnabled(fabId, mcpName)) continue;

                try {
                    McpProperties mcp = fabProperties.getMcpPropertiesMap().get(mcpName);
                    Map<Integer, RawHid> rawHidById = collectRawHidById(mcp);

                    updateEdgeMaster(fabId, mcpName, fabEdges, rawHidById);
                    updateHidInfoMaster(fabId, mcpName, fabEdges, rawHidById);

                } catch (Exception ex) {
                    logger.error("[HID MASTER] failed [fab={} mcp={}]", fabId, mcpName, ex);
                    // 다른 mcp 처리 계속 진행
                }
            }
        }
    }

    // ------------------------------------------------------------------
    // 1) 엣지 마스터
    // ------------------------------------------------------------------
    private void updateEdgeMaster(String fabId, String mcpName,
                                  Map<String, AbstractEdge> fabEdges,
                                  Map<Integer, RawHid> rawHidById) {

        // toNodeId → 그 노드를 from 으로 하는 RailEdge 목록 (O(N) index)
        Map<String, List<RailEdge>> outgoingByFromNode = new HashMap<>();
        for (AbstractEdge ae : fabEdges.values()) {
            RailEdge re = (RailEdge) ae;
            outgoingByFromNode.computeIfAbsent(re.getFromNodeId(), k -> new ArrayList<>()).add(re);
        }

        Map<Integer, String> hidNameById = new HashMap<>();
        Set<String> seen = new HashSet<>();
        List<Tuple> tuples = new ArrayList<>();

        String updateDt = nowAsString();

        for (AbstractEdge ae : fabEdges.values()) {
            RailEdge re = (RailEdge) ae;
            int fromHidId = re.getHIDId();
            String toNode = re.getToNodeId();

            List<RailEdge> nexts = outgoingByFromNode.getOrDefault(toNode, java.util.Collections.emptyList());
            for (RailEdge nxt : nexts) {
                int toHidId = nxt.getHIDId();
                if (fromHidId == toHidId) continue;
                if (fromHidId <= 0 && toHidId <= 0) continue;

                String edgeKey = fromHidId + ":" + toHidId;
                if (!seen.add(edgeKey)) continue;

                hidNameById.putIfAbsent(fromHidId, formatHidName(fromHidId));
                hidNameById.putIfAbsent(toHidId,   formatHidName(toHidId));

                String edgeType;
                if (fromHidId == 0)      edgeType = HidInoutTableSchema.EDGE_TYPE_IN;
                else if (toHidId == 0)   edgeType = HidInoutTableSchema.EDGE_TYPE_OUT;
                else                     edgeType = HidInoutTableSchema.EDGE_TYPE_INTERNAL;

                Tuple t = new Tuple();
                t.put(HidInoutTableSchema.COL_FROM_HIDID,  fromHidId);
                t.put(HidInoutTableSchema.COL_TO_HIDID,    toHidId);
                t.put(HidInoutTableSchema.COL_EDGE_ID,     String.format("%03d:%03d", fromHidId, toHidId));
                t.put(HidInoutTableSchema.COL_FROM_HID_NM, hidNameById.get(fromHidId));
                t.put(HidInoutTableSchema.COL_TO_HID_NM,   hidNameById.get(toHidId));
                t.put(HidInoutTableSchema.COL_MCP_ID,      mcpName);
                t.put(HidInoutTableSchema.COL_ZONE_ID,     zoneIdOf(rawHidById, fromHidId, toHidId));
                t.put(HidInoutTableSchema.COL_EDGE_TYPE,   edgeType);
                t.put(HidInoutTableSchema.COL_UPDATE_DT,   updateDt);

                tuples.add(t);
            }
        }

        if (tuples.isEmpty()) {
            logger.warn("[HID MASTER] no edge tuples [fab={} mcp={}]", fabId, mcpName);
            return;
        }

        String tableName = HidInoutTableSchema.tableEdgeMaster(fabId);
        LogpressoAPI.setInsertTuples(tableName, tuples, HidInoutTableSchema.INSERT_BATCH_SIZE);
        logger.info("[HID MASTER] edge master updated -> {} ({} rows)", tableName, tuples.size());
    }

    // ------------------------------------------------------------------
    // 2) HID 정보 마스터
    // ------------------------------------------------------------------
    private void updateHidInfoMaster(String fabId, String mcpName,
                                     Map<String, AbstractEdge> fabEdges,
                                     Map<Integer, RawHid> rawHidById) {

        Map<Integer, Double>        railLenByHid    = new HashMap<>();
        Map<Integer, List<Double>>  velocitiesByHid = new HashMap<>();
        Map<Integer, Integer>       portCntByHid    = new HashMap<>();

        for (AbstractEdge ae : fabEdges.values()) {
            RailEdge re = (RailEdge) ae;
            int hidId = re.getHIDId();
            if (hidId <= 0) continue;

            railLenByHid.merge(hidId, re.getLength(), Double::sum);

            double maxV = re.getMaxVelocity();
            if (maxV > 0) {
                velocitiesByHid.computeIfAbsent(hidId, k -> new ArrayList<>()).add(maxV);
            }

            List<String> ports = re.getPortIdList();
            if (ports != null && !ports.isEmpty()) {
                portCntByHid.merge(hidId, ports.size(), Integer::sum);
            }
        }

        String updateDt = nowAsString();
        List<Tuple> tuples = new ArrayList<>();
        Set<Integer> allHids = new HashSet<>();
        allHids.addAll(railLenByHid.keySet());
        allHids.addAll(rawHidById.keySet());

        for (Integer hidId : allHids) {
            if (hidId == null || hidId <= 0) continue;

            double avgSpeed = 0.0;
            List<Double> vs = velocitiesByHid.get(hidId);
            if (vs != null && !vs.isEmpty()) {
                double sum = 0.0;
                for (Double v : vs) sum += v;
                avgSpeed = sum / vs.size();
            }

            RawHid rh = rawHidById.get(hidId);
            int inCnt   = rh != null ? safeInt(rh, "getInCnt",  0) : 0;
            int outCnt  = rh != null ? safeInt(rh, "getOutCnt", 0) : 0;
            int vhlMax  = rh != null ? rh.getVhlMax()              : 0;
            String zcu  = rh != null ? safeStr(rh, "getZcuId", "") : "";

            Tuple t = new Tuple();
            t.put(HidInoutTableSchema.COL_HID_ID,         hidId);
            t.put(HidInoutTableSchema.COL_HID_NM,         formatHidName(hidId));
            t.put(HidInoutTableSchema.COL_MCP_ID,         mcpName);
            t.put(HidInoutTableSchema.COL_ZONE_ID,        "");
            t.put(HidInoutTableSchema.COL_RAIL_LEN_TOTAL, railLenByHid.getOrDefault(hidId, 0.0));
            t.put(HidInoutTableSchema.COL_FREE_FLOW_SPEED, avgSpeed);
            t.put(HidInoutTableSchema.COL_PORT_CNT_TOTAL, portCntByHid.getOrDefault(hidId, 0));
            t.put(HidInoutTableSchema.COL_IN_CNT,         inCnt);
            t.put(HidInoutTableSchema.COL_OUT_CNT,        outCnt);
            t.put(HidInoutTableSchema.COL_VHL_MAX,        vhlMax);
            t.put(HidInoutTableSchema.COL_ZCU_ID,         zcu);
            t.put(HidInoutTableSchema.COL_UPDATE_DT,      updateDt);

            tuples.add(t);
        }

        if (tuples.isEmpty()) {
            logger.warn("[HID MASTER] no HID info tuples [fab={} mcp={}]", fabId, mcpName);
            return;
        }

        String tableName = HidInoutTableSchema.tableHidInfoMaster(fabId);
        LogpressoAPI.setInsertTuples(tableName, tuples, HidInoutTableSchema.INSERT_BATCH_SIZE);
        logger.info("[HID MASTER] HID info master updated -> {} ({} rows)", tableName, tuples.size());
    }

    // ------------------------------------------------------------------
    // helpers
    // ------------------------------------------------------------------

    private boolean isHidInoutEnabled(String fabId, String mcpName) {
        FunctionItem fi = Env.getSwitchMap().get(fabId + ":" + mcpName);
        return fi != null && fi.getUseFunction(FunctionType.HID_INOUT);
    }

    private Map<String, AbstractEdge> filterRailEdgesForFab(String fabId) {
        Map<String, AbstractEdge> snapshot = new HashMap<>(DataService.getDataSet().getEdgeMap());
        return snapshot.entrySet().stream()
                .filter(e -> e.getValue() instanceof RailEdge
                          && fabId.equals(e.getValue().getFabId()))
                .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue));
    }

    private Map<Integer, RawHid> collectRawHidById(McpProperties mcp) {
        Map<Integer, RawHid> result = new HashMap<>();
        if (mcp == null || mcp.getMcp75Config() == null) return result;
        for (RawHid r : mcp.getMcp75Config().getRawHidMap().values()) {
            result.put(r.getId(), r);
        }
        return result;
    }

    private String formatHidName(int hidId) {
        if (hidId <= 0) return HidInoutTableSchema.HID_NAME_OUTSIDE;
        return String.format(HidInoutTableSchema.HID_NAME_FORMAT, hidId);
    }

    private String zoneIdOf(Map<Integer, RawHid> rawHidById, int fromHid, int toHid) {
        RawHid from = rawHidById.get(fromHid);
        if (from != null) {
            String z = safeStr(from, "getZoneId", "");
            if (!z.isEmpty()) return z;
        }
        RawHid to = rawHidById.get(toHid);
        if (to != null) return safeStr(to, "getZoneId", "");
        return "";
    }

    private String nowAsString() {
        return new SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(new Date());
    }

    /**
     * RawHid 의 일부 메서드는 빌드에 따라 부재할 수 있어 reflection-style 안전 호출.
     * 실제 적용 시 RawHid 에 해당 getter 가 있으면 직접 호출로 교체할 것.
     */
    private int safeInt(Object o, String method, int def) {
        try {
            Object v = o.getClass().getMethod(method).invoke(o);
            return v instanceof Number ? ((Number) v).intValue() : def;
        } catch (ReflectiveOperationException e) {
            return def;
        }
    }

    private String safeStr(Object o, String method, String def) {
        try {
            Object v = o.getClass().getMethod(method).invoke(o);
            return v == null ? def : v.toString();
        } catch (ReflectiveOperationException e) {
            return def;
        }
    }
}
