package com.skhynix.smartatlas.hidinout;

import java.util.HashMap;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.data.Msg.MSG_TYP;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.util.DataService;

/**
 * 기존 HidEdgeInOutQueueFlushBatch 의 주석 처리되어 있던 tibrv 송신 분기를
 * 별도 책임으로 분리한 클래스.
 *
 * 임계치 판단 규칙 (운영 협의 전 기본값):
 *  - vhlCountLimit > 0 이고 hidValue >= vhlCountLimit  → CRITICAL
 *  - vhlPrecaution > 0 이고 hidValue >= vhlPrecaution → WARNING
 *  - 그 외엔 송신하지 않음
 *
 * 실제 임계 조건은 운영 정책에 따라 setThresholdPolicy() 로 교체 가능하도록
 * functional interface 를 노출한다.
 */
public final class HidInoutTibrvNotifier {

    private static final Logger logger = LoggerFactory.getLogger(HidInoutTibrvNotifier.class);

    public enum Severity { NONE, WARNING, CRITICAL }

    @FunctionalInterface
    public interface ThresholdPolicy {
        Severity evaluate(HidInoutAggregate agg);
    }

    private static volatile ThresholdPolicy policy = HidInoutTibrvNotifier::defaultPolicy;

    private HidInoutTibrvNotifier() {}

    public static void setThresholdPolicy(ThresholdPolicy p) {
        if (p != null) policy = p;
    }

    private static Severity defaultPolicy(HidInoutAggregate agg) {
        int limit  = agg.getVhlCountLimit();
        int warn   = agg.getVhlPrecaution();
        int value  = agg.getHidValue();
        if (limit > 0 && value >= limit) return Severity.CRITICAL;
        if (warn  > 0 && value >= warn)  return Severity.WARNING;
        return Severity.NONE;
    }

    /**
     * flush 시점에 호출되어 임계치 초과 행에 한해 tibrv 메시지를 송신한다.
     *
     * @param fabDbId    DB 적재용 FAB_ID (vhl.getFabId())
     * @param fabRouteId tibrv sender 키에 쓰이는 fab 키 (DataService 의 fab 키)
     * @param eventDate  yyyy-MM-dd
     * @param eventDt    yyyy-MM-dd HH:mm:00
     */
    public static void notifyIfExceeded(HidInoutEventKey key, HidInoutAggregate agg,
                                        String fabRouteId, String eventDate, String eventDt) {
        Severity sev = policy.evaluate(agg);
        if (sev == Severity.NONE) return;

        String type = MSG_TYP.OHT.toString() + ".HID.INOUT";

        Map<String, Object> data = new HashMap<>();
        data.put("TYPE",            type);
        data.put("SEVERITY",        sev.name());
        data.put("FAB_ID",          key.getVhlFabId());
        data.put("EVENT_DT",        eventDt);
        data.put("EVENT_DATE",      eventDate);
        data.put("FROM_HIDID",      key.getFromHidId());
        data.put("TO_HIDID",        key.getToHidId());
        data.put("VHL_ID",          key.getVhlId());
        data.put("EQP_ID",          key.getEqpId());
        data.put("TRANS_CNT",       agg.getTransCnt());
        data.put("MCP_NM",          key.getMcpName());
        data.put("ENV",             Env.getEnv());
        data.put("FREE_FLOW_SPEED", agg.getFreeFlowSpeed());
        data.put("HID_VALUE",       agg.getHidValue());
        data.put("VHL_COUNT_LIMIT", agg.getVhlCountLimit());
        data.put("VHL_PRECAUTION",  agg.getVhlPrecaution());

        try {
            for (String tibrvKey : DataService.getInstance()
                    .getTibrvSenderLikeMap(fabRouteId + ":send:amos").keySet()) {
                DataService.getInstance().addTibrvMessageQueue(tibrvKey, type, data);
            }
        } catch (Exception e) {
            logger.warn("[HID INOUT] tibrv notify failed [fab={} sev={}]", fabRouteId, sev, e);
        }
    }
}
