package com.atlas.cnv;

/*
 * IMPORTS REQUIRED (for reference):
 * import org.slf4j.Logger;
 * import org.slf4j.LoggerFactory;
 * import org.apache.commons.lang3.StringUtils;
 * import java.util.ArrayList;
 * import java.util.List;
 * import java.text.SimpleDateFormat;
 * import java.util.Date;
 * (Logpresso/Tuple import if available)
 */

/**
 * CNV (Conveyor) Message Worker Runnable for processing STK MCP7/SSS messages.
 * Handles CNV-specific Text IDs (1, 3, 4, 201, 202, 203).
 * Processes equipment state reports and inserts data into Logpresso.
 *
 * Text IDs:
 * - ID:1   - MCP online reports
 * - ID:3   - Alarm/recovery
 * - ID:4   - Equipment/Machine state reports (CNV core)
 * - ID:201 - Position information reports
 * - ID:202 - Load information reports (SSS → FabScope)
 * - ID:203 - Congestion reports
 */
public class CnvMsgWorkerRunnable implements Runnable {
    private static final Logger logger = LoggerFactory.getLogger(CnvMsgWorkerRunnable.class);
    private static final int MSG_ID_IDX = 0;
    private final String message;
    private final long receivedMilli;
    private final long messageSequence;
    private final String fabId;
    private final String mcpName;

    public CnvMsgWorkerRunnable(
            String fabId,
            String message,
            String mcpName,
            long receivedMilli,
            long messageSequence
    ) {
        this.fabId              = fabId;
        this.mcpName            = mcpName;
        this.message            = message;
        this.receivedMilli      = receivedMilli;
        this.messageSequence    = messageSequence;
    }

    @Override
    public void run() {
        String[] tokens = StringUtils.splitPreserveAllTokens(message, ',');

        if (tokens.length >= 2) {
            String messageId = tokens[MSG_ID_IDX];

            switch(messageId) {
                case MSG_ID.MCP_ONLINE_REPORT:
                    this._processMcpOnlineReport(tokens);
                    break;
                case MSG_ID.MACHINE_STATE_REPORT:
                    this._processCnvCoreReport(tokens);
                    break;
                case MSG_ID.ALARM_RECOVERY_REPORT:
                    this._processAlarmRecoveryReport(tokens);
                    break;
                case MSG_ID.LOAD_INFO_REPORT:
                    this._processLoadInfoReport(tokens);
                    break;
                case MSG_ID.POSITION_REPORT:
                    this._processPositionReport(tokens);
                    break;
                case MSG_ID.CONGESTION_REPORT:
                    this._processCongestionReport(tokens);
                    break;
                default:
                    logger.debug("... unhandled message type [fab: {} | mcp: {} | msgId: {}]", fabId, mcpName, messageId);
            }
        }
    }

    @Override
    public String toString() {
        return String.format("%s %s %s %s", getClass(), fabId, mcpName, message);
    }

    /**
     * Process MCP Online Report (Text ID:1)
     */
    private void _processMcpOnlineReport(String[] tokens) {
        try {
            if (tokens.length <= 1) {
                logger.error("... invalid token context for MCP online report [fab: {} | mcp: {}]", fabId, mcpName);
                return;
            }

            Tuple tuple = new Tuple();
            tuple.put("FAB_ID", fabId);
            tuple.put("MCP_NM", mcpName);
            tuple.put("TEXT_ID", tokens[MSG_ID_IDX]);
            tuple.put("RECV_TIME", receivedMilli);
            tuple.put("MSG_SEQUENCE", messageSequence);

            LogpressoAPI.setInsertTuples("ATLAS_CNV_MCP_ONLINE", List.of(tuple), 20);

            logger.debug("[MCP Online] Processed [fab: {} | mcp: {}]", fabId, mcpName);
        } catch (Exception e) {
            logger.error("[MCP Online] Error processing message [fab: {} | mcp: {}]", fabId, mcpName, e);
        }
    }

    /**
     * Process CNV Core Equipment/Machine State Report (Text ID:4)
     * Format: TXT_ID,MCP_NM,MODEL_NO,EQUIPMENT_NM,STATE,ERROR_CODE
     */
    private void _processCnvCoreReport(String[] tokens) {
        try {
            if (tokens.length <= CNV_STATE_REPORT.ERROR_CODE_IDX) {
                logger.error("... invalid token context for CNV state report [fab: {} | mcp: {} | token length: {}]",
                    fabId, mcpName, tokens.length);
                return;
            }

            String equipmentModelNo = Util.getTokenSafely(tokens, CNV_STATE_REPORT.MODEL_NO_IDX, "");
            String equipmentName = Util.getTokenSafely(tokens, CNV_STATE_REPORT.EQUIPMENT_NM_IDX, "");
            String state = Util.getTokenSafely(tokens, CNV_STATE_REPORT.STATE_IDX, "");
            String errorCode = Util.getTokenSafely(tokens, CNV_STATE_REPORT.ERROR_CODE_IDX, "");

            Tuple tuple = new Tuple();
            tuple.put("FAB_ID", fabId);
            tuple.put("MCP_NM", mcpName);
            tuple.put("MODEL_NO", equipmentModelNo);
            tuple.put("EQUIPMENT_NM", equipmentName);
            tuple.put("STATE", state);
            tuple.put("ERROR_CODE", errorCode);
            tuple.put("TEXT_ID", tokens[CNV_STATE_REPORT.TXT_ID_IDX]);
            tuple.put("RECV_TIME", receivedMilli);
            tuple.put("MSG_SEQUENCE", messageSequence);
            tuple.put("ENV", Env.getEnv());

            LogpressoAPI.setInsertTuples("ATLAS_CNV_EQUIPMENT_STATE", List.of(tuple), 20);

            logger.debug("[CNV Core] Equipment state processed [fab: {} | mcp: {} | equip: {} | state: {}]",
                fabId, mcpName, equipmentName, state);
        } catch (Exception e) {
            logger.error("[CNV Core] Error processing equipment state [fab: {} | mcp: {}]", fabId, mcpName, e);
        }
    }

    /**
     * Process Alarm/Recovery Report (Text ID:3)
     */
    private void _processAlarmRecoveryReport(String[] tokens) {
        try {
            if (tokens.length < 2) {
                logger.error("... invalid token context for alarm report [fab: {} | mcp: {}]", fabId, mcpName);
                return;
            }

            Tuple tuple = new Tuple();
            tuple.put("FAB_ID", fabId);
            tuple.put("MCP_NM", mcpName);
            tuple.put("TEXT_ID", tokens[MSG_ID_IDX]);
            tuple.put("RECV_TIME", receivedMilli);
            tuple.put("MSG_SEQUENCE", messageSequence);
            tuple.put("ALARM_DATA", message);
            tuple.put("ENV", Env.getEnv());

            LogpressoAPI.setInsertTuples("ATLAS_CNV_ALARM", List.of(tuple), 20);

            logger.info("[Alarm/Recovery] Processed [fab: {} | mcp: {} | data: {}]", fabId, mcpName, message);
        } catch (Exception e) {
            logger.error("[Alarm/Recovery] Error processing message [fab: {} | mcp: {}]", fabId, mcpName, e);
        }
    }

    /**
     * Process Load Information Report (Text ID:202)
     * Format includes SC name and repeated equipment data (max 10), report type (1:CONV/2:VC)
     */
    private void _processLoadInfoReport(String[] tokens) {
        try {
            if (tokens.length < CNV_LOAD_REPORT.MIN_LENGTH) {
                logger.error("... invalid token context for load info report [fab: {} | mcp: {} | token length: {}]",
                    fabId, mcpName, tokens.length);
                return;
            }

            String scName = Util.getTokenSafely(tokens, CNV_LOAD_REPORT.SC_NM_IDX, "");
            String reportType = Util.getTokenSafely(tokens, CNV_LOAD_REPORT.REPORT_TYPE_IDX, "");

            Tuple tuple = new Tuple();
            tuple.put("FAB_ID", fabId);
            tuple.put("MCP_NM", mcpName);
            tuple.put("TEXT_ID", tokens[CNV_LOAD_REPORT.TXT_ID_IDX]);
            tuple.put("SC_NM", scName);
            tuple.put("REPORT_TYPE", reportType);
            tuple.put("RECV_TIME", receivedMilli);
            tuple.put("MSG_SEQUENCE", messageSequence);
            tuple.put("LOAD_DATA", message);
            tuple.put("ENV", Env.getEnv());

            LogpressoAPI.setInsertTuples("ATLAS_CNV_LOAD_INFO", List.of(tuple), 20);

            logger.debug("[Load Info] Processed [fab: {} | mcp: {} | sc: {} | type: {}]",
                fabId, mcpName, scName, reportType);
        } catch (Exception e) {
            logger.error("[Load Info] Error processing message [fab: {} | mcp: {}]", fabId, mcpName, e);
        }
    }

    /**
     * Process Position Information Report (Text ID:201)
     */
    private void _processPositionReport(String[] tokens) {
        try {
            if (tokens.length < 2) {
                logger.error("... invalid token context for position report [fab: {} | mcp: {}]", fabId, mcpName);
                return;
            }

            Tuple tuple = new Tuple();
            tuple.put("FAB_ID", fabId);
            tuple.put("MCP_NM", mcpName);
            tuple.put("TEXT_ID", tokens[MSG_ID_IDX]);
            tuple.put("RECV_TIME", receivedMilli);
            tuple.put("MSG_SEQUENCE", messageSequence);
            tuple.put("POSITION_DATA", message);
            tuple.put("ENV", Env.getEnv());

            LogpressoAPI.setInsertTuples("ATLAS_CNV_POSITION", List.of(tuple), 20);

            logger.debug("[Position] Processed [fab: {} | mcp: {}]", fabId, mcpName);
        } catch (Exception e) {
            logger.error("[Position] Error processing message [fab: {} | mcp: {}]", fabId, mcpName, e);
        }
    }

    /**
     * Process Congestion Report (Text ID:203)
     */
    private void _processCongestionReport(String[] tokens) {
        try {
            if (tokens.length < 2) {
                logger.error("... invalid token context for congestion report [fab: {} | mcp: {}]", fabId, mcpName);
                return;
            }

            Tuple tuple = new Tuple();
            tuple.put("FAB_ID", fabId);
            tuple.put("MCP_NM", mcpName);
            tuple.put("TEXT_ID", tokens[MSG_ID_IDX]);
            tuple.put("RECV_TIME", receivedMilli);
            tuple.put("MSG_SEQUENCE", messageSequence);
            tuple.put("CONGESTION_DATA", message);
            tuple.put("ENV", Env.getEnv());

            LogpressoAPI.setInsertTuples("ATLAS_CNV_CONGESTION", List.of(tuple), 20);

            logger.debug("[Congestion] Processed [fab: {} | mcp: {}]", fabId, mcpName);
        } catch (Exception e) {
            logger.error("[Congestion] Error processing message [fab: {} | mcp: {}]", fabId, mcpName, e);
        }
    }

    /**
     * Message ID constants for CNV Text IDs
     */
    private static class MSG_ID {
        public static final String MCP_ONLINE_REPORT = "1";
        public static final String ALARM_RECOVERY_REPORT = "3";
        public static final String MACHINE_STATE_REPORT = "4";
        public static final String POSITION_REPORT = "201";
        public static final String LOAD_INFO_REPORT = "202";
        public static final String CONGESTION_REPORT = "203";
    }

    /**
     * Field indices for CNV Equipment/Machine State Report (Text ID:4)
     */
    public static class CNV_STATE_REPORT {
        public static final int TXT_ID_IDX = 0;             // 텍스트 id
        public static final int MCP_NM_IDX = 1;             // mcp 명칭
        public static final int MODEL_NO_IDX = 2;           // 장비 모델 번호
        public static final int EQUIPMENT_NM_IDX = 3;       // 장비 명칭
        public static final int STATE_IDX = 4;              // 상태
        public static final int ERROR_CODE_IDX = 5;         // error code
    }

    /**
     * Field indices for CNV Load Information Report (Text ID:202)
     */
    public static class CNV_LOAD_REPORT {
        public static final int TXT_ID_IDX = 0;             // 텍스트 id
        public static final int MCP_NM_IDX = 1;             // mcp 명칭
        public static final int SC_NM_IDX = 2;              // SC 명칭
        public static final int REPORT_TYPE_IDX = 3;        // 레포트 타입 (1:CONV/2:VC)
        public static final int MIN_LENGTH = 4;             // 최소 토큰 개수
    }

    /**
     * State constants for CNV messages
     */
    public static class CNV_STATE {
        public static final String NORMAL = "NORMAL";
        public static final String ABNORMAL = "ABNORMAL";

        public static List<String> getStates() {
            List<String> states = new ArrayList<>();
            states.add(NORMAL);
            states.add(ABNORMAL);
            return states;
        }
    }
}
