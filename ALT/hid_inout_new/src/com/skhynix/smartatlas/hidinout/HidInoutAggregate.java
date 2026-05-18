package com.skhynix.smartatlas.hidinout;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * 단일 HidInoutEventKey 에 대해 1분 동안 누적되는 측정치.
 *
 * - transCnt : HID 전환 발생 횟수 (단순 증가)
 * - vhlCountLimit / vhlPrecaution : HID 정의(RawHid) 상의 상한·경고치
 * - freeFlowSpeed : 마지막 관측 시점의 1분 평균 RailEdge velocity
 * - hidValue : 마지막 관측 시점의 해당 HID 차량 수
 *
 * transCnt 는 다수 OHT 워커가 동시에 호출하므로 AtomicInteger 로 보호한다.
 * 나머지 보조 필드는 마지막 관측값으로 갱신되며, 정확성보다 처리량을 우선해
 * volatile 만 사용한다(분단위 통계이므로 단조성 요구는 없음).
 */
public final class HidInoutAggregate {

    private final AtomicInteger transCnt = new AtomicInteger(0);

    private volatile int    vhlCountLimit;
    private volatile int    vhlPrecaution;
    private volatile double freeFlowSpeed;
    private volatile int    hidValue;

    /** 카운트만 증가시키는 빠른 경로 */
    public void incrementTransCnt() {
        transCnt.incrementAndGet();
    }

    /** 보조 측정치 갱신 (호출 순서가 보장될 필요는 없음) */
    public void updateSnapshot(int vhlCountLimit, int vhlPrecaution,
                               double freeFlowSpeed, int hidValue) {
        this.vhlCountLimit = vhlCountLimit;
        this.vhlPrecaution = vhlPrecaution;
        this.freeFlowSpeed = freeFlowSpeed;
        this.hidValue      = hidValue;
    }

    public int    getTransCnt()      { return transCnt.get(); }
    public int    getVhlCountLimit() { return vhlCountLimit; }
    public int    getVhlPrecaution() { return vhlPrecaution; }
    public double getFreeFlowSpeed() { return freeFlowSpeed; }
    public int    getHidValue()      { return hidValue; }
}
