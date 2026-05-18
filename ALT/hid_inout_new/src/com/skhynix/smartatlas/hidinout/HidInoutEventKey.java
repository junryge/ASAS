package com.skhynix.smartatlas.hidinout;

import java.util.Objects;

/**
 * HID IN/OUT 카운트를 누적할 때 사용하는 복합 키 (typed value object).
 *
 * 기존 구현(HidEdgeInOutQueueFlushBatch)은 String 의 ":" split 으로 11개 필드를
 * 파싱해 사용했지만, fab/mcp/vhl/eqp 이름에 ':' 가 포함될 경우 파싱이 깨진다.
 * 본 클래스는 그 위험을 제거하고 ConcurrentHashMap 의 key 로 안전하게 사용할 수
 * 있도록 equals/hashCode 를 명시적으로 구현한다.
 *
 * 누적 대상: fromHidId, toHidId, fabId, mcpName, vhlFabId, vhlId, eqpId 의 조합.
 * 보조 필드(vhlCountLimit, vhlPrecaution, freeFlowSpeed, hidValue)는 동일 키에
 * 대해 1분 동안 마지막 관측값으로 갱신한다 (flush 시점 스냅샷).
 */
public final class HidInoutEventKey {

    private final int    fromHidId;
    private final int    toHidId;
    private final String fabId;       // 차량이 속한 fab (DataService 의 fab key)
    private final String mcpName;
    private final String vhlFabId;    // vhl.getFabId() — DB에 적재되는 FAB_ID
    private final String vhlId;       // short name (':' 뒤)
    private final String eqpId;       // short name

    public HidInoutEventKey(int fromHidId, int toHidId, String fabId, String mcpName,
                            String vhlFabId, String vhlId, String eqpId) {
        this.fromHidId = fromHidId;
        this.toHidId   = toHidId;
        this.fabId     = nullToEmpty(fabId);
        this.mcpName   = nullToEmpty(mcpName);
        this.vhlFabId  = nullToEmpty(vhlFabId);
        this.vhlId     = nullToEmpty(vhlId);
        this.eqpId     = nullToEmpty(eqpId);
    }

    private static String nullToEmpty(String s) { return s == null ? "" : s; }

    public int    getFromHidId() { return fromHidId; }
    public int    getToHidId()   { return toHidId; }
    public String getFabId()     { return fabId; }
    public String getMcpName()   { return mcpName; }
    public String getVhlFabId()  { return vhlFabId; }
    public String getVhlId()     { return vhlId; }
    public String getEqpId()     { return eqpId; }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (!(o instanceof HidInoutEventKey)) return false;
        HidInoutEventKey k = (HidInoutEventKey) o;
        return fromHidId == k.fromHidId
            && toHidId   == k.toHidId
            && fabId.equals(k.fabId)
            && mcpName.equals(k.mcpName)
            && vhlFabId.equals(k.vhlFabId)
            && vhlId.equals(k.vhlId)
            && eqpId.equals(k.eqpId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(fromHidId, toHidId, fabId, mcpName, vhlFabId, vhlId, eqpId);
    }

    @Override
    public String toString() {
        return "HidInoutEventKey{" + fromHidId + "->" + toHidId
             + ", fab=" + fabId + ", mcp=" + mcpName
             + ", vhlFab=" + vhlFabId + ", vhl=" + vhlId + ", eqp=" + eqpId + '}';
    }
}
