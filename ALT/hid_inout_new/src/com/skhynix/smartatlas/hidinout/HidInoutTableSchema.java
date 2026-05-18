package com.skhynix.smartatlas.hidinout;

/**
 * {FABID}_ATLAS_HID_INOUT 및 마스터 테이블의 컬럼/테이블 명세.
 *
 * 컬럼 상수화 목적:
 *   - 오타로 인한 Logpresso schema mismatch 방지
 *   - 컬럼 추가/변경 시 단일 지점 수정으로 영향 범위 최소화
 *   - 테스트/디버깅에서 동일한 이름을 재사용 가능
 *
 * 기존 코드(HidEdgeInOutQueueFlushBatch / HidEdgeInOutUpdateMasterBatch)와
 * 동일한 컬럼명/테이블 suffix 를 사용하여 schema 호환을 유지한다.
 */
public final class HidInoutTableSchema {

    private HidInoutTableSchema() {}

    // ------------------------------------------------------------------
    // 테이블명 (FAB ID 를 prefix 로 사용)
    // ------------------------------------------------------------------

    /** {FAB}_ATLAS_HID_INOUT — 분 단위 IN/OUT 전환 카운트 적재 */
    public static final String TABLE_SUFFIX_INOUT          = "_ATLAS_HID_INOUT";

    /** {FAB}_ATLAS_INFO_HID_INOUT_MAS — IN/OUT 엣지 마스터 */
    public static final String TABLE_SUFFIX_EDGE_MASTER    = "_ATLAS_INFO_HID_INOUT_MAS";

    /** {FAB}_ATLAS_HID_INFO_MAS — HID 정보 마스터 */
    public static final String TABLE_SUFFIX_HID_INFO_MAS   = "_ATLAS_HID_INFO_MAS";

    public static String tableInout(String fabId)         { return fabId + TABLE_SUFFIX_INOUT; }
    public static String tableEdgeMaster(String fabId)    { return fabId + TABLE_SUFFIX_EDGE_MASTER; }
    public static String tableHidInfoMaster(String fabId) { return fabId + TABLE_SUFFIX_HID_INFO_MAS; }

    // ------------------------------------------------------------------
    // {FAB}_ATLAS_HID_INOUT 컬럼
    // ------------------------------------------------------------------
    public static final String COL_EVENT_DATE       = "EVENT_DATE";       // yyyy-MM-dd
    public static final String COL_EVENT_DT         = "EVENT_DT";         // yyyy-MM-dd HH:mm:00 (분단위 절삭)
    public static final String COL_FROM_HIDID       = "FROM_HIDID";       // int, 0 = OUTSIDE
    public static final String COL_TO_HIDID         = "TO_HIDID";         // int, 0 = OUTSIDE
    public static final String COL_TRANS_CNT        = "TRANS_CNT";        // int, 1분간 전환 횟수
    public static final String COL_FAB_ID           = "FAB_ID";           // 차량의 FAB_ID (vhl.getFabId())
    public static final String COL_VHL_ID           = "VHL_ID";           // 차량 short name
    public static final String COL_EQP_ID           = "EQP_ID";           // 설비 short name
    public static final String COL_MCP_NM           = "MCP_NM";           // MCP 이름
    public static final String COL_ENV              = "ENV";              // 실행 환경 (Env.getEnv())
    public static final String COL_VHL_COUNT_LIMIT  = "VHL_COUNT_LIMIT";  // RawHid.vhlMax
    public static final String COL_VHL_PRECAUTION   = "VHL_PRECAUTION";   // RawHid.vhlPreCaution
    public static final String COL_FREE_FLOW_SPEED  = "FREE_FLOW_SPEED";  // 1분 평균 속도 (double)
    public static final String COL_HID_VALUE        = "HID_VALUE";        // HID 내 현재 차량 수

    // ------------------------------------------------------------------
    // {FAB}_ATLAS_INFO_HID_INOUT_MAS 컬럼 (엣지 마스터)
    // ------------------------------------------------------------------
    public static final String COL_EDGE_ID          = "EDGE_ID";          // "%03d:%03d"
    public static final String COL_FROM_HID_NM      = "FROM_HID_NM";      // HID_001 / OUTSIDE
    public static final String COL_TO_HID_NM        = "TO_HID_NM";
    public static final String COL_MCP_ID           = "MCP_ID";
    public static final String COL_ZONE_ID          = "ZONE_ID";
    public static final String COL_EDGE_TYPE        = "EDGE_TYPE";        // IN / OUT / INTERNAL
    public static final String COL_UPDATE_DT        = "UPDATE_DT";

    // ------------------------------------------------------------------
    // {FAB}_ATLAS_HID_INFO_MAS 컬럼 (HID 마스터)
    // ------------------------------------------------------------------
    public static final String COL_HID_ID           = "HID_ID";
    public static final String COL_HID_NM           = "HID_NM";
    public static final String COL_RAIL_LEN_TOTAL   = "RAIL_LEN_TOTAL";   // 총 레일 길이
    public static final String COL_PORT_CNT_TOTAL   = "PORT_CNT_TOTAL";   // 총 포트 수
    public static final String COL_IN_CNT           = "IN_CNT";
    public static final String COL_OUT_CNT          = "OUT_CNT";
    public static final String COL_VHL_MAX          = "VHL_MAX";
    public static final String COL_ZCU_ID           = "ZCU_ID";

    // ------------------------------------------------------------------
    // EDGE_TYPE 값
    // ------------------------------------------------------------------
    public static final String EDGE_TYPE_IN         = "IN";       // OUTSIDE -> HID
    public static final String EDGE_TYPE_OUT        = "OUT";      // HID -> OUTSIDE
    public static final String EDGE_TYPE_INTERNAL   = "INTERNAL"; // HID -> HID

    public static final String HID_NAME_OUTSIDE     = "OUTSIDE";
    public static final String HID_NAME_FORMAT      = "HID_%03d";

    // ------------------------------------------------------------------
    // 배치/플러시 파라미터
    // ------------------------------------------------------------------
    /** Logpresso bulk insert 한 번에 보낼 tuple 묶음 크기 */
    public static final int  INSERT_BATCH_SIZE      = 100;

    /** flush 실패 시 재시도 횟수 (지수 백오프 2s, 4s, 8s) */
    public static final int  FLUSH_RETRY_MAX        = 3;
    public static final long FLUSH_RETRY_BASE_MS    = 2_000L;
}
