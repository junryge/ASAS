package com.skhynix.smartatlas.hidinout;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicReference;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.data.McpProperties;
import com.skhynix.smartatlas.data.raw.RawHid;
import com.skhynix.smartatlas.map.AbstractEdge;
import com.skhynix.smartatlas.map.edge.RailEdge;
import com.skhynix.smartatlas.map.Vhl;
import com.skhynix.smartatlas.util.DataService;

/**
 * OHT 워커 스레드에서 호출되는 HID IN/OUT 이벤트 수집기.
 *
 * 핵심 책임:
 *  1) 차량의 직전 HID 와 현재 HID 가 다를 때 카운트 누적
 *  2) HID 정의(RawHid) 로부터 차량 상한/경고치 조회
 *  3) 현재 HID 구간 평균 속도 계산
 *  4) 현재 HID 차량 수 조회
 *
 * flush 와의 동시성:
 *  - 누적 map 은 AtomicReference 로 감싸 flush 시 새 map 으로 atomic swap 한다.
 *  - 기존 HidEdgeInOutQueueFlushBatch 는 "forEach + setEdgeInOutCountMap(new ...)"
 *    구성이라 그 사이 도착한 이벤트가 새 map 으로 들어가 직전 통계가 흐려질 수
 *    있었다. 본 구현은 swap 후 이전 map 만 직렬화하므로 손실/이중집계 가능성을
 *    원천 차단한다.
 *
 * 기존 DataService.getEdgeInOutCountMap() 와는 별개의 누적 저장소를 사용한다.
 * (기존 코드와의 병행 운영 안전)
 */
public final class HidInoutCollector {

    private static final Logger logger = LoggerFactory.getLogger(HidInoutCollector.class);

    private static final HidInoutCollector INSTANCE = new HidInoutCollector();
    public  static HidInoutCollector getInstance() { return INSTANCE; }

    private final AtomicReference<ConcurrentHashMap<HidInoutEventKey, HidInoutAggregate>> bucketRef =
            new AtomicReference<>(new ConcurrentHashMap<>());

    private HidInoutCollector() {}

    // ------------------------------------------------------------------
    // 이벤트 수집
    // ------------------------------------------------------------------

    /**
     * 차량의 HID 가 변경되었을 때 호출. 변경이 없으면 호출 측에서 미리 필터링하는 것이
     * 이상적이지만, 안전을 위해 내부에서도 한 번 더 검사한다.
     *
     * @param previousHidId 직전 HID (vehicle.getHidId() 의 갱신 전 값)
     * @param currentHidId  현재 HID (railEdge.getHIDId())
     * @param fabId         DataService 의 fab 키
     * @param mcpName       MCP 이름
     * @param vehicle       차량 객체
     */
    public void recordTransition(int previousHidId, int currentHidId,
                                 String fabId, String mcpName, Vhl vehicle) {
        if (previousHidId == currentHidId) {
            return; // no-op
        }
        if (vehicle == null) {
            logger.debug("[HID INOUT] skip: vehicle is null [fab={} mcp={}]", fabId, mcpName);
            return;
        }

        try {
            HidInoutEventKey key = buildKey(previousHidId, currentHidId, fabId, mcpName, vehicle);
            HidInoutAggregate agg = bucketRef.get().computeIfAbsent(key, k -> new HidInoutAggregate());
            agg.incrementTransCnt();

            int vhlCountLimit  = 0;
            int vhlPrecaution  = 0;
            McpProperties mcp = resolveMcp(fabId, mcpName);
            if (mcp != null && mcp.getMcp75Config() != null) {
                for (RawHid rawHid : mcp.getMcp75Config().getRawHidMap().values()) {
                    if (rawHid.getId() == currentHidId) {
                        vhlCountLimit = rawHid.getVhlMax();
                        vhlPrecaution = rawHid.getVhlPreCaution();
                        break;
                    }
                }
            }

            double freeFlowSpeed = computeFreeFlowSpeed(currentHidId);
            int    hidValue      = readHidValue(fabId, mcpName, currentHidId);

            agg.updateSnapshot(vhlCountLimit, vhlPrecaution, freeFlowSpeed, hidValue);

        } catch (Exception e) {
            // 개별 이벤트 처리 실패가 전체 메시지 처리 흐름을 막지 않도록 흡수
            logger.warn("[HID INOUT] recordTransition failed [fab={} mcp={} prev={} curr={}]",
                    fabId, mcpName, previousHidId, currentHidId, e);
        }
    }

    /**
     * flush 시점에 호출. 현재 누적 map 을 빈 map 으로 atomic 교체하고
     * 기존 map 을 반환한다. flush 처리는 호출자(배치)가 담당.
     */
    public Map<HidInoutEventKey, HidInoutAggregate> drain() {
        return bucketRef.getAndSet(new ConcurrentHashMap<>());
    }

    /**
     * 실패 시 데이터 복구를 위해 외부에서 다시 합쳐 넣을 수 있도록 제공.
     * 동일 키는 transCnt 만 합산하고 스냅샷 값은 후행 입력으로 덮어쓴다.
     */
    public void mergeBack(Map<HidInoutEventKey, HidInoutAggregate> failed) {
        if (failed == null || failed.isEmpty()) return;

        ConcurrentHashMap<HidInoutEventKey, HidInoutAggregate> current = bucketRef.get();
        for (Map.Entry<HidInoutEventKey, HidInoutAggregate> e : failed.entrySet()) {
            HidInoutAggregate target = current.computeIfAbsent(e.getKey(), k -> new HidInoutAggregate());
            int restoreCnt = e.getValue().getTransCnt();
            for (int i = 0; i < restoreCnt; i++) target.incrementTransCnt();
            target.updateSnapshot(
                    e.getValue().getVhlCountLimit(),
                    e.getValue().getVhlPrecaution(),
                    e.getValue().getFreeFlowSpeed(),
                    e.getValue().getHidValue());
        }
    }

    // ------------------------------------------------------------------
    // helpers
    // ------------------------------------------------------------------

    private HidInoutEventKey buildKey(int prevHidId, int currHidId,
                                      String fabId, String mcpName, Vhl vehicle) {
        String vhlFull = vehicle.getId();
        String eqpFull = vehicle.getEqpId();
        String vhlName = (vhlFull == null) ? "" : vhlFull.substring(vhlFull.lastIndexOf(':') + 1);
        String eqpName = (eqpFull == null) ? "" : eqpFull.substring(eqpFull.lastIndexOf(':') + 1);

        return new HidInoutEventKey(prevHidId, currHidId, fabId, mcpName,
                vehicle.getFabId(), vhlName, eqpName);
    }

    private McpProperties resolveMcp(String fabId, String mcpName) {
        try {
            return DataService.getInstance()
                    .getFabPropertiesMap().get(fabId)
                    .getMcpPropertiesMap().get(mcpName);
        } catch (NullPointerException npe) {
            return null;
        }
    }

    /**
     * 현재 HID 에 속한 RailEdge 의 velocity 평균.
     * velocity == 0 인 엣지는 정지/미관측으로 보고 평균에서 제외한다.
     */
    private double computeFreeFlowSpeed(int hidId) {
        if (hidId <= 0) return 0.0;

        double sum = 0.0;
        int    n   = 0;
        for (AbstractEdge ae : DataService.getDataSet().getEdgeMap().values()) {
            if (!(ae instanceof RailEdge)) continue;
            RailEdge re = (RailEdge) ae;
            if (re.getHIDId() != hidId) continue;
            double v = re.getVelocity();
            if (v > 0) {
                sum += v;
                n++;
            }
        }
        return n > 0 ? sum / n : 0.0;
    }

    private int readHidValue(String fabId, String mcpName, int hidId) {
        if (hidId <= 0) return 0;
        String hidKey = fabId + ":" + mcpName + ":" + String.format("%03d", hidId);
        return DataService.getDataSet().getHidVehicleCountMap().getOrDefault(hidKey, 0);
    }

    /** 테스트/모니터링용 — 현재 누적 entry 수 */
    public int sizeForMonitoring() {
        return bucketRef.get().size();
    }
}
