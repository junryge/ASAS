package com.skhynix.smartatlas.batch;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.service.TibrvService;
import com.skhynix.smartatlas.util.DataService;
import com.skhynix.smartatlas.util.Util;
import com.skhynix.smartatlas.util.XmlUtil;
import com.skhynix.smartfx.dataaccessfx.DataRow;
import com.skhynix.smartfx.dataaccessfx.DataTable;
import com.skhynix.smartfx.dataaccessfx.QueryExecutor;
import com.skhynix.smartfx.dataaccessfx.QueryExecutorFactory;

public class SystemMessageDetectBatch implements Job {
    private final Logger logger = LoggerFactory.getLogger(SystemMessageDetectBatch.class);
    private double limitedCondition = -1;
    private String eventDateTimeStr;
    private String eventOnlyTimeStr;
    private String confirmEventDateTimeStr; // 데이터 보완용

    private List<Integer> mesReqTsJobCntList = new ArrayList<>();
    private List<Integer> mcsRepTsJobCntList = new ArrayList<>();
    private int currentMesReqTsJobCnt = -1;
    private int currentMcsRepTsJobCnt = -1;
    private double mesReqTsJobAverage = -1;
    private double mcsRepTsJobAverage = -1;
    private List<Integer> mcsRemoteCmdCntList = new ArrayList<>();
    private List<Integer> mcsRemoteCmdAckCntList = new ArrayList<>();
    private int currentMcsRemoteCmdCnt = -1;
    private int currentMcsRemoteCmdAckCnt = -1;
    private double mcsRemoteCmdAverage = -1;
    private double mcsRemoteCmdAckAverage = -1;
    private List<Integer> mcpEventReportCntList = new ArrayList<>();
    private List<Integer> mcpEventReportAckCntList = new ArrayList<>();
    private int currentMcpEventReportCnt = -1;
    private int currentMcpEventReportAckCnt = -1;
    private double mcpEventReportAverage = -1;
    private double mcpEventReportAckAverage = -1;

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        final int DELAYED_TIME = 1000 * 60;

        if (Util.isCurrentIC()) {
            logger.info("... `SystemMessageDetectBatch` has started");

            long timer = System.currentTimeMillis();

            this._run();

            long checkTimer = System.currentTimeMillis() - timer;

            if (checkTimer >= DELAYED_TIME) {
                logger.error("... !!!DELAYED!!! `SystemMessageDetectBatch` has finished [elapsed time: {}m ({}ms)]", checkTimer / (60 * 1000), checkTimer);
            } else {
                logger.info("... `SystemMessageDetectBatch` has finished [elapsed time: {}ms]", checkTimer);
            }
        }
    }

    private void _run() {
        LocalDateTime now = LocalDateTime.now();
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");
        this.eventDateTimeStr = now.format(formatter);
        LocalDateTime ago = now.minusMinutes(1);
        this.confirmEventDateTimeStr = ago.format(formatter);

        formatter = DateTimeFormatter.ofPattern("HH:mm");   // displayed comments under graph
        this.eventOnlyTimeStr = now.format(formatter);

        this._preprocessing();

        List<Tuple> countList = this._collectData();

        LogpressoAPI.setInsertTuples("abnormal_detect_data", countList,15);
    }

    private List<Tuple> _collectData() {
        final List<Tuple> result = new ArrayList<>();

        List<Map<String, Object>> mhsMcsMessageList = this._getMhsMcsMessage();

        List<Map<String, Object>> mcsMcpMessageList = this._getMcsMcpMessage();

        List<Map<String, Object>> mesJobMonitoringList = this._getMesJobMonitoring();

        List<Map<String, Object>> mcsSecsLWarnList = _getMcsSecsWarnLog();

        List<Map<String, Object>> mesLogPatternList = this._getMesJobTsLogPattern();

        mhsMcsMessageList.addAll(mcsMcpMessageList);
        mhsMcsMessageList.addAll(mesJobMonitoringList);
        mhsMcsMessageList.addAll(mcsSecsLWarnList);
        mhsMcsMessageList.addAll(mesLogPatternList);

        for(Map<String, Object> map : mhsMcsMessageList) {
            final Tuple countMapSet = new Tuple();

            XmlUtil.mapToTplConvert(map, countMapSet);

            result.add(countMapSet);
        }

        return result;
    }

    /**
     * 저장시 기준으로 바로 이전 시간의 데이터가 존재하는 지 확인 후 데이터 추가 저장
     */
//    private void _confirm() {
//        List<Map<String, Object>> data = XmlUtil.selectLogpressoQuery("confirmAbnormalDetectData");
//
//        if (data != null && !data.isEmpty()) {
//            for (Map<String, Object> t : data) {
//                String time = t.get("TIME").toString();
//
//                if (time.equals(confirmEventDateTimeStr)) {
//                    // 일치하는 시간이 존재한다면 바로 이전 시간의 데이터가 존재한다는 것이므로 과정 종료
//                    return;
//                }
//            }
//        }
//
//        // 바로 이전 시간의 데이터가 존재하지 않는 경우
//        this.confirmEventDateTimeStr
//    }

    private List<Map<String, Object>> _getMhsMcsMessage(){
        List<Map<String, Object>> result = XmlUtil.selectLogpressoQuery("mhsMcsMessage");
        int index = -1;

        logger.info("MHS-MCS SECS Message Data {}", result.size());

        try {
            for (int i = 0; i < result.size(); i++) {
                Map<String, Object> row = result.get(i);
                int count = Integer.parseInt(row.get("MINUTE_PER_CNT").toString());
                String messageName = row.get("MSG_NM").toString();
                String fabId = row.get("FAB_ID").toString();

                if (this.currentMesReqTsJobCnt > -1 && this.currentMcsRepTsJobCnt > -1) break;

                if (messageName != null && !messageName.isEmpty() && fabId.equals("M14A")) {
                    switch (messageName) {
                        case "MHSMCS_TRANSPORT_JOB_SCHEDULE_REQ": {
                            this.currentMesReqTsJobCnt = count;
                            index = i;
                        } break;
                        case "MCSMHS_TRANSPORT_JOB_SCHEDULE_REP": {
                            this.currentMcsRepTsJobCnt = count;
                        } break;
                    }
                }
            }

            if (index > -1) {
                Map<String, Object> data = this._validateMesMcsTransportCommandJob(this.currentMesReqTsJobCnt);

                this._reflectAlarmField(result.get(index), data);
            }
        } catch (Exception e) {
            logger.error("", e);
        }

        return result;
    }

    private List<Map<String, Object>> _getMcsMcpMessage(){
        List<Map<String, Object>> result = XmlUtil.selectLogpressoQuery("mcsMcpMessage");
        int remoteIndex = -1;
        int reportIndex = -1;

        logger.info("MCS-MCP SECS Message Data {}", result.size());

        try {
            for (int i = 0; i < result.size(); i++) {
                Map<String, Object> row = result.get(i);
                int count = Integer.parseInt(row.get("SECS_LOG_CNT").toString());
                String messageName = row.get("MSG_NM").toString();

                if (
                        this.currentMcpEventReportCnt > -1
                                && this.currentMcpEventReportAckCnt > -1
                                && this.currentMcsRemoteCmdCnt > -1
                                && this.currentMcsRemoteCmdAckCnt > -1
                ) break;

                if (messageName != null && !messageName.isEmpty()) {
                    switch (messageName) {
                        case "S6F11 Event Report Send": {
                            this.currentMcpEventReportCnt = count;
                            reportIndex = i;
                        } break;
                        case "S6F12 Event Report Acknowledge": {
                            this.currentMcpEventReportAckCnt = count;
                        } break;
                        case "S2F49 Enhanced Remote Command": {
                            this.currentMcsRemoteCmdCnt = count;
                            remoteIndex = i;
                        } break;
                        case "S2F50 Enhanced Remote Command Acknowledge": {
                            this.currentMcsRemoteCmdAckCnt = count;
                        }
                    }
                }
            }

            if (reportIndex > -1) {
                Map<String, Object> data = this._validateMcpEventReport(this.currentMcpEventReportAckCnt);

                this._reflectAlarmField(result.get(reportIndex), data);
            }

            if (remoteIndex > -1) {
                Map<String, Object> data = this._validateMcsMcpTransportCommandJob(this.currentMcsRemoteCmdCnt);

                this._reflectAlarmField(result.get(remoteIndex), data);
            }
        } catch (Exception e) {
            logger.error("", e);
        }

        return result;
    }

    /**
     * 알람 기능의 동작을 위한 내용을 추가
     * @param row 호출한 쿼리의 데이터
     * @param data 추가할 데이터
     */
    private void _reflectAlarmField(Map<String, Object> row, Map<String, Object> data) {
        row.put("FALR_JUDGE_YN", data.get("FALR_JUDGE_YN"));
        row.put("ABNORM_CTN", data.get("ABNORM_CTN"));
        row.put("ALARM_CMT", data.get("ALARM_CMT"));
        row.put("ALARM_MSG_CTN", data.get("ALARM_MSG_CTN"));
        row.put("ALARM_DESC", data.get("ALARM_DESC"));
        row.put("ALARM_YN", data.get("ALARM_YN"));
    }

    private List<Map<String, Object>> _getMesJobMonitoring() {
        List<Map<String, Object>> result = XmlUtil.selectLogpressoQuery("mesJobMonitoring");

        logger.info("MES Job Monitoring Data {}", result.size());

        return result;
    }

    private List<Map<String, Object>> _getMcsSecsWarnLog() {
        List<Map<String, Object>> queryData = XmlUtil.selectLogpressoQuery("mcsSecsWarnLog");
        List<Map<String, Object>> result = new ArrayList<>();

        logger.info("MCS SECS Warn Log Data {}", queryData.size());

        if (queryData.isEmpty()) {
            result.add(this._getMcsSecsWarnLogHandler(null));
        } else {
            for (Map<String, Object> data : queryData) {
                result.add(this._getMcsSecsWarnLogHandler(data));
            }
        }

        return result;
    }

    private List<Map<String, Object>> _getMesJobTsLogPattern() {
        List<Map<String, Object>> queryData = XmlUtil.selectLogpressoQuery("mesJobTsLogPattern");

        logger.info("MES Message Pattern Data {}", queryData.size());

        Map<String, Object> dataMap = new HashMap<>();
        LocalDateTime now = LocalDateTime.now();
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");

        dataMap.put("TIME", formatter.format(now));
        dataMap.put("FAB_ID", "M14A");
        dataMap.put("IDC_NM", "MES_PATTERN");

        List<Map<String, Object>> result = new ArrayList<>();

        for (Map<String, Object> data : queryData) {
            if(data.get("OMIT_VAL") != null && !data.get("OMIT_VAL").toString().isEmpty()) {
                dataMap.put("JUDGE_YN", "Y");
                this._getCommonMap(
                        dataMap,
                        "MES_TRANSPORT_DATA_REQUIRED_EXCEPT",
                        this.currentMesReqTsJobCnt,
                        this.currentMcsRepTsJobCnt,
                        this.mesReqTsJobAverage,
                        this.mcsRepTsJobAverage
                );

                result.add(dataMap);

                return result;
            }
        }

        dataMap.put("JUDGE_YN", "N");

        result.add(dataMap);

        return result;
    }

    /**
     * &#064;ABNORMAL#1&2  MES 반송명령 감소 | MES -> MCS
     * @return alarm 내용
     */
    private Map<String, Object> _validateMesMcsTransportCommandJob(int count) {
        final int abnormalMessageType1 = 1;
        final int abnormalMessageType2 = 2;
        int rdsCount = 0; // RDS 값

        if (count > 0) {
            if (this._getAbnormalCount(count, this.mesReqTsJobAverage)) {
                // TS LOG 이상
                TibrvService ts = DataService.getInstance().getTibrvReceiverMap().get("M14A:rev:mhs");

                if (ts != null && ts.getMessageCount(this.confirmEventDateTimeStr) > 0) {
                    rdsCount = ts.getMessageCount(this.confirmEventDateTimeStr);

                    if (this._getAbnormalCount(rdsCount, this.mesReqTsJobAverage)) {
                        // TS LOG & RDS 이상
                        return this._getAbnormalMesMcsTransportCommand(count, rdsCount, true, abnormalMessageType1);
                    } else {
                        // TS LOG 만 이상
                        return this._getAbnormalMesMcsTransportCommand(count, rdsCount, true, abnormalMessageType2);
                    }
                } else {
                    return this._getAbnormalMesMcsTransportCommand(count, rdsCount, true, abnormalMessageType2);
                }
            } else {
                // TS LOG 정상
                return this._getAbnormalMesMcsTransportCommand(count, -1, false, abnormalMessageType2);
            }
        }

        return new HashMap<>();
    }

    private Map<String, Object> _getAbnormalMesMcsTransportCommand(
            int tsLogCount,
            int rdsCount,
            boolean isOccurred,
            int messageSequence
    ) {
        Map<String, Object> result = new HashMap<>();
        double responseRate = this._calculateResponseRate(this.mcsRepTsJobCntList, this.mesReqTsJobCntList);

        result.put("FALR_JUDGE_YN", isOccurred ? "Y" : "N");
        result.put("ALARM_YN", isOccurred ? "Y" : "N");
        result.put("TIME", this.eventDateTimeStr);
        result.put(
                ABNORM_CTN,
                XmlUtil.getMessage(
                        isOccurred ?
                                "MES_TRANSPORT_DECLARE_ABNORMAL_CONTENTS"
                                : "MES_TRANSPORT_DECLARE_NORMAL_CONTENTS",
                        tsLogCount, // 0
                        this.mesReqTsJobAverage, // 1
                        this._calculatePercentage(tsLogCount, this.mesReqTsJobAverage), // 2
                        responseRate, // 3
                        this.eventOnlyTimeStr
                )
        );

        if (isOccurred) {
            this._getCommonMap(
                    result,
                    "MES_TRANSPORT_DECLARE_EXCEPT_" + messageSequence,
                    tsLogCount, // 0
                    this.mesReqTsJobAverage, // 1
                    this._calculatePercentage(tsLogCount, this.mesReqTsJobAverage), // 2
                    rdsCount, // 3
                    this._calculatePercentage(rdsCount, this.mesReqTsJobAverage), // 4
                    this.currentMcsRepTsJobCnt, // 5
                    this.mcsRepTsJobAverage, // 6
                    responseRate // 7
            );
        }

        return result;
    }

    /**
     * &#064;ABNORMAL#3  MCS 반송 CMD 생성 수 감소 | MCS -> MCP
     * @return alarm 내용
     */
    private Map<String, Object> _validateMcsMcpTransportCommandJob(int count) {
        // S2F49 Enhanced Remote Command
        if (count > 0) {
            return this._getMcsMcpTransportCommandJobAlarm(count, this._getAbnormalCount(count, this.mcsRemoteCmdAverage));
        } else {
            return new HashMap<>();
        }
    }

    private Map<String, Object> _getMcsMcpTransportCommandJobAlarm(int tsLogCount, boolean isOccurred) {
        Map<String, Object> result = new HashMap<>();
        double responseRate = this._calculateResponseRate(
                this.mcsRemoteCmdCntList,
                this.mcsRemoteCmdAckCntList
        ); // 3

        result.put("FALR_JUDGE_YN", isOccurred ? "Y" : "N");
        result.put("ALARM_YN", isOccurred ? "Y" : "N");
        result.put("TIME", this.eventDateTimeStr);
        result.put(
                ABNORM_CTN,
                XmlUtil.getMessage(
                        isOccurred ?
                                "MCS_TRANSPORT_COMMAND_DECLARE_ABNORMAL_CONTENTS"
                                : "MCS_TRANSPORT_COMMAND_DECLARE_NORMAL_CONTENTS",
                        tsLogCount, // 0
                        this.mcsRemoteCmdAverage, // 1
                        this._calculatePercentage(tsLogCount, this.mcsRemoteCmdAverage), // 2
                        responseRate,
                        this.eventOnlyTimeStr
                )
        );

        if (isOccurred) {
            String controlState = "";
            String connectionState = "";
            String tscState = "";

            try (QueryExecutor executor = QueryExecutorFactory.build("M14A")) {
                DataTable queryData = executor.selectDataTable("SELECT_MCS_MCP_STATE");

                if (queryData != null && queryData.getRowCount() > 0) {
                    DataRow row = queryData.getRow(0);
                    controlState = row.getString("CONTROLSTATE");
                    connectionState = row.getString("CONNECTIONSTATE");
                    tscState = row.getString("TSCSTATE");
                }
            } catch (Exception e) {
                logger.error("... An error occurred while searching query !!!", e);
            }

            this._getCommonMap(
                    result,
                    "MCS_TRANSPORT_COMMAND_DECLARE_EXCEPT",
                    tsLogCount, // 0
                    this.mcsRemoteCmdAverage, // 1
                    this._calculatePercentage(tsLogCount, this.mcsRemoteCmdAverage), // 2
                    this.currentMesReqTsJobCnt, // 3
                    this.mesReqTsJobAverage, // 4
                    this._calculatePercentage(this.currentMesReqTsJobCnt, this.mesReqTsJobAverage), // 5
                    responseRate, // 6
                    this.currentMcsRepTsJobCnt, // 7
                    this.mcsRepTsJobAverage, // 8
                    connectionState, // 9
                    controlState, // 10
                    tscState // 11
            );
        }

        return result;
    }

    /**
     * &#064;ABNORMAL#4  MCP 반송 Event Report 수 감소 | MCP -> MCS
     * @return alarm 내용
     */
    private Map<String, Object> _validateMcpEventReport(int count) {
        if (count > 0) {
            return this._mcpEventReportAlarm(count, this._getAbnormalCount(count, this.mcpEventReportAverage));
        } else {
            return new HashMap<>();
        }
    }

    private Map<String, Object> _mcpEventReportAlarm(int tsLogCount, boolean isOccurred) {
        Map<String, Object> result = new HashMap<>();
        double responseRate = this._calculateResponseRate(
                this.mcpEventReportAckCntList,
                this.mcpEventReportCntList
        );

        result.put("FALR_JUDGE_YN", isOccurred ? "Y" : "N");
        result.put("ALARM_YN", isOccurred ? "Y" : "N");
        result.put("TIME", this.eventDateTimeStr);
        result.put(
                ABNORM_CTN,
                XmlUtil.getMessage(
                        isOccurred ?
                                "MCP_TRANSPORT_S6F11_DECLARE_ABNORMAL_CONTENTS"
                                : "MCP_TRANSPORT_S6F11_DECLARE_NORMAL_CONTENTS",
                        this.currentMcpEventReportCnt, // 0
                        this.mcpEventReportAverage, // 1
                        this._calculatePercentage(this.currentMcpEventReportCnt, this.mcpEventReportAverage), // 2
                        responseRate, // 3
                        this.eventOnlyTimeStr
                )
        );

        if (isOccurred) {
            String controlState = "";
            String connectionState = "";
            String tscState = "";

            try (QueryExecutor executor = QueryExecutorFactory.build("M14A")) {
                DataTable queryData = executor.selectDataTable("SELECT_MCS_MCP_STATE");

                if (queryData != null && queryData.getRowCount() > 0) {
                    DataRow row = queryData.getRow(0);
                    controlState = row.getString("CONTROLSTATE");
                    connectionState = row.getString("CONNECTIONSTATE");
                    tscState = row.getString("TSCSTATE");
                }
            } catch (Exception e) {
                logger.error("... An error occurred while searching query !!!", e);
            }

            this._getCommonMap(
                    result,
                    "MCP_TRANSPORT_S6F11_DECLARE_EXCEPT",
                    this.currentMcpEventReportCnt, // 0
                    this.mcpEventReportAverage, // 1
                    this._calculatePercentage(this.currentMcpEventReportCnt, this.mcpEventReportAverage), // 2
                    tsLogCount, // 3
                    this.mcpEventReportAckAverage, // 4
                    this._calculatePercentage(tsLogCount, this.mcpEventReportAckAverage), // 5
                    responseRate, // 6
                    this.currentMesReqTsJobCnt, // 7
                    this.mesReqTsJobAverage, // 8
                    this.currentMcsRepTsJobCnt, // 9
                    this.mcsRepTsJobAverage, // 10
                    connectionState, // 11
                    controlState, // 12
                    tscState // 13
            );
        }

        return result;
    }

//    private List<Map<String, Object>> _getMesNewBpelPattern() {
//        List<Map<String, Object>> result = this._selectLogpressoQuery("selectAhmsLogPattern");
//
//
//    }
//
//    private Map<String, Object> _buildBaseMesNewBpelPattern(Map<String, Object> data) {
//        Map<String, Object> result = new HashMap<>();
////
////
//        /*
//            STAR PK     | ATLAS FIELD(OR VALUE)
//            EVENT_DT    | EVENT_DT
//            FAB_ID      | FAB_ID
//            PROC_NM     | PROC_NM
//            MSG_NM      | MSG_NM
//            TXN_ID      | TXN_ID
//         */
//
//
//        result.put(FAB_ID, "ALL");
//        result.put(JUDGE_YN, "N");
//        result.put(HOST_NM, "");
//        result.put(ETC_CTN, "");
//        result.put(ALARM_MSG_CTN, "");
//        result.put(ALARM_CD, "");
//        result.put(ALARM_DESC, "");
//        result.put(ALARM_CMT, "");
//        result.put(ABNORM_CTN, "");
//        result.put(ALARM_YN, "N");
//
//        if (data == null) {
//            result.put(EVENT_DT, this.eventDateTimeStr);
//            result.put(IDC_NM, "SECS_WARN");
//            result.put(MSG_NM, "");
//            result.put(MSG_CTN, "");
//        } else {
//            result.put(EVENT_DT, data.get(EVENT_DT));
//            result.put(IDC_NM, data.get(IDC_NM));
//            result.put(MSG_NM, data.get(MSG_NM));
//            result.put(MSG_CTN, data.get(MSG_CTN));
//        }
//
//        return result;
//    }

    /**
     * &#064;ABNORMAL#7&8  MCS MCP SECS로그 패턴 분석 :: MCS-MCP 통신 간 System Byte 오류 발생 | MCS-MCP 간 MCP 메시지 Format 오류 발생
     * @return alarm 내용
     */
    private Map<String, Object> _getMcsSecsWarnLogHandler(Map<String, Object> data) {
        if (data == null) {
            return this._buildBaseMcsSecsWarnLog(null);
        }

        Map<String, Object> row = this._buildBaseMcsSecsWarnLog(data);
        Object idcNameObj = data.get(IDC_NM);

        if (idcNameObj instanceof String && idcNameObj.toString().equals("SECS_WARN")) {
            return row;
        }

        Object monitoringIdcNameObj = data.get(MSG_NM);

        if (monitoringIdcNameObj instanceof String) {
            String monitoringIdcName = monitoringIdcNameObj.toString();
            String commonPrefixCodeName = "";

            row.put("TIME", this.eventDateTimeStr);

            switch (monitoringIdcName) {
                case "RECEIVE UNKNOWN MESSAGE": {
                    // MCS-MCP 간 MCP 메시지 Format 오류 발생
                    commonPrefixCodeName = "MCP_MCP_TRANSPORT_MESSAGE_FORMAT_EXCEPT";
                } break;
                case "INVALID SECONDARY MESSAGE": {
                    // MCS-MCP 통신 간 System Byte 오류 발생
                    commonPrefixCodeName = "MCP_MCP_TRANSPORT_SYSTEM_BYTE_EXCEPT";
                } break;
            }

            if (!commonPrefixCodeName.isEmpty()) {
                row.put(JUDGE_YN, "Y");
                row.put(ALARM_YN, "Y");

                this._getCommonMap(
                        row,
                        commonPrefixCodeName
                );
            }
        }

        return row;
    }

    /**
     * abnormal_detect_data 에 적재하기 위한 기본 데이터 (alarm 에 대한 내용 등은 handler 에서 작성)
     * @param data 원본 데이터
     * @return abnormal_detect_data 에 적재할 기본 데이터
     */
    private Map<String, Object> _buildBaseMcsSecsWarnLog(Map<String, Object> data) {
        Map<String, Object> result = new HashMap<>();

        result.put(FAB_ID, "ALL");
        result.put(JUDGE_YN, "N");
        result.put("TIME", this.eventDateTimeStr);
        result.put(HOST_NM, "");
        result.put(ETC_CTN, "");
        result.put(ALARM_MSG_CTN, "");
        result.put(ALARM_CD, "");
        result.put(ALARM_DESC, "");
        result.put(ALARM_CMT, "");
        result.put(ABNORM_CTN, "");
        result.put(ALARM_YN, "N");

        if (data == null) {
            result.put(IDC_NM, "SECS_WARN");
            result.put(MSG_NM, "");
            result.put(MSG_CTN, "");
        } else {
            result.put(IDC_NM, data.get(IDC_NM));
            result.put(MSG_NM, data.get(MSG_NM));
            result.put(MSG_CTN, data.get(MSG_CTN));
        }

//        result.put(CATG_NM, "");
//        result.put(EQP_NM, "");

        return result;
    }

//    private List<Map<String, Object>> _getMcsSecsWarnLogHandler(List<Map<String, Object>> dataList) {
//        String monitorIdcName1 = "RECEIVE UNKNOWN MESSAGE";
//        String monitorIdcName2 = "INVALID SECONDARY MESSAGE";
//        List<Map<String, Object>> base = this._buildBaseMcsSecsWarnLog(monitorIdcName1, monitorIdcName2);
//
//        if (dataList != null && !dataList.isEmpty()) {
//            for (Map<String, Object> data : dataList) {
//                String monitorIdcName = data.get("MONTR_IDC_NM").toString();
//                String commonPrefixCodeName = "";
//
//                if (monitorIdcName.equals(monitorIdcName1)) {
//                    commonPrefixCodeName = "MCP_MCP_TRANSPORT_MESSAGE_FORMAT_EXCEPT";
//                } else if (monitorIdcName.equals(monitorIdcName2)) {
//                    commonPrefixCodeName = "MCP_MCP_TRANSPORT_SYSTEM_BYTE_EXCEPT";
//                }
//
//                data.put("ALARM_YN", "Y");
//
//                this._getCommonMap(data, commonPrefixCodeName);
//            }
//        }
//
//        return base;
//    }
//
//    private List<Map<String, Object>> _buildBaseMcsSecsWarnLog(String t1, String t2) {
//        /*
//            STAR PK     | ATLAS FIELD(OR VALUE)
//            EVENT_DT    | TIME
//            CATG_NM     | IDC_NM
//            FAB_ID      | "ALL"
//            EQP_NM      | "ALL"
//            MSG_NM      | MONTR_IDC_NM
//         */
//        /*
//            MSG_NM = {"INVALID SECONDARY MESSAGE", "RECEIVE UNKNOWN MESSAGE"}
//         */
//        List<Map<String, Object>> result = new ArrayList<>();
//        Map<String, Object> dataMap1 = new HashMap<>() {{put("MONTR_IDC_NM", t1);}};
//        Map<String, Object> dataMap2 = new HashMap<>() {{put("MONTR_IDC_NM", t2);}};
//
//        result.add(dataMap1);
//        result.add(dataMap2);
//
//        for (Map<String, Object> data: result) {
//            data.put("IDC_NM", "SECS_WARN");
//            data.put("TIME", this.eventDateTimeStr);
//        }
////        result.put(ALARM_DESC, ""); // alarm title
////        result.put(ALARM_CMT, ""); // alarm title in message context
////        result.put(ABNORM_CTN, "");  // alarm message contents
//
//        return result;
//    }

    /**
     * 입력한 값이 `이상 현상`에 해당하는 지를 계산하여 판별
     * @param targetCount 비교 대상 값
     * @param average targetCount 이 속한 집합의 평균 값
     * @return 비교한 값에 대한 결과 :: true - abnormal 상태 | false - normal 상태
     */
    private boolean _getAbnormalCount(int targetCount, double average) {
        return targetCount <= average * this.limitedCondition;
    }

    // data 참조
    private void _getCommonMap(
            Map<String, Object> data,
            String alarmCommonCode,
            Object... parameter
    ) {
        Map<String, Object> result = new HashMap<>();

        if (data != null) {
            result = data;
        }

        String alarmComment = XmlUtil.getMessage(alarmCommonCode + "_DESC");
        String alarmDescription = XmlUtil.getMessage(alarmCommonCode + "_TITLE");
        String alarmMessageContents = XmlUtil.getMessage(alarmCommonCode + "_CONTENTS", parameter);

        result.put("ALARM_CMT", alarmComment);
        result.put("ALARM_DESC", alarmDescription);
        result.put("ALARM_MSG_CTN", alarmMessageContents);
    }

    // alarm 혹은 (graph 하단의)comments 를 적용 전의 전처리 과정
    private void _preprocessing() {
        // `이상 현상` 판별의 기준이 되는 조건 ---> variable.xml 에 명시
        String conditionStr = XmlUtil.getVariableEnv("ABNORMAL_LIMIT_CONDITION", (Object) null);

        try {
            if (conditionStr.equals("Unknown ALARM CODE: ABNORMAL_LIMIT_CONDITION")) {
                this.limitedCondition = 0.1;
            } else {
                this.limitedCondition = Double.parseDouble(conditionStr) / 100.0;
            }
        } catch (Exception e) {
            logger.error("... it is exception, because of missing default code !!! [setting `0.1`]");

            this.limitedCondition = 0.1;
        }

        logger.info("... setting limited condition: " + this.limitedCondition);

        // MES 현재 반송 수, MCS 현재 반송 수, 각각 1개월 평균
        final List<Map<String, Object>> mcsMesTsJobCntList = XmlUtil.selectLogpressoQuery("MHSMCS_TS_JOB_CNT_AT_1MONTH");
        this.mesReqTsJobCntList = this._collectIntegerCnt(mcsMesTsJobCntList, "REQ_CNT");
        this.mcsRepTsJobCntList = this._collectIntegerCnt(mcsMesTsJobCntList, "REP_CNT");

        final List<Map<String, Object>> mcsRemoteCmdCntList = XmlUtil.selectLogpressoQuery("MCS_REMOTE_CMD_CNT_AT_1MONTH");
        this.mcsRemoteCmdCntList = this._collectIntegerCnt(mcsRemoteCmdCntList, "CNT");
        this.mcsRemoteCmdAckCntList = this._collectIntegerCnt(mcsRemoteCmdCntList, "ACK_CNT");

        final List<Map<String, Object>> secsEventReportCntList = XmlUtil.selectLogpressoQuery("SECS_EVENT_REPORT_CNT_AT_1MONTH");
        this.mcpEventReportCntList = this._collectIntegerCnt(secsEventReportCntList, "CNT");
        this.mcpEventReportAckCntList = this._collectIntegerCnt(secsEventReportCntList, "ACK_CNT");

        if (!this.mesReqTsJobCntList.isEmpty()) {
            this.mesReqTsJobAverage = this._calculateAverage(this.mesReqTsJobCntList);
        }

        if (!this.mcsRepTsJobCntList.isEmpty()) {
            this.mcsRepTsJobAverage = this._calculateAverage(this.mcsRepTsJobCntList);
        }

        if (!this.mcsRemoteCmdCntList.isEmpty()) {
            this.mcsRemoteCmdAverage = this._calculateAverage(this.mcsRemoteCmdCntList);
        }

//        if (!this.mcsRemoteCmdAckCntList.isEmpty()) {
//            this.mcsRemoteCmdAckAverage = this._calculateAverage(this.mcsRemoteCmdAckCntList);
//        }

        if (!this.mcpEventReportCntList.isEmpty()) {
            this.mcpEventReportAverage = this._calculateAverage(this.mcpEventReportCntList);
        }

        if (!this.mcpEventReportAckCntList.isEmpty()) {
            this.mcpEventReportAckAverage = this._calculateAverage(this.mcpEventReportAckCntList);
        }
    }

    private List<Integer> _collectIntegerCnt(List<Map<String, Object>> entireDataList, String inquireKey) {
        if (entireDataList == null || entireDataList.isEmpty()) {
            return new ArrayList<>();
        }

        try {
            return entireDataList.stream()
                    .filter(i -> i.get(inquireKey) != null && !i.get(inquireKey).toString().isEmpty())
                    .map(i -> Integer.parseInt(i.get(inquireKey).toString()))
                    .sorted()
                    .collect(Collectors.toList());
        } catch (Exception e) {
            logger.error("", e);
        }

        return new ArrayList<>();
    }

    // (수적 대소 기준으로) 10% 씩 제외한 상태에서 평균값 계산
    private double _calculateAverage(List<Integer> dataList) {
        int listSize = dataList.size();

        if (listSize < 10) return 0;

        int lowerBoundIndex = (int) (listSize * 0.1);
        int upperBoundIndex = (int) (listSize * 0.9);
        List<Integer> filteredList = dataList.subList(lowerBoundIndex, upperBoundIndex);
        double average = filteredList.stream()
                .mapToInt(Integer::intValue)
                .average()
                .orElse(0);

        if (average == 0) {
            return 0;
        } else {
            return Math.round(average * 10.0) / 10.0;
        }
    }

    private double _calculatePercentage(double value, double total) {
        if (total == 0) return 0;

        return (Math.round((value / total) * 10.0) / 10.0) * 100.0;
    }

    // 각 배열의 합계를 통해 응답률 계산
    private double _calculateResponseRate(List<Integer> list1, List<Integer> list2) {
        double sum1 = list1.stream().mapToInt(Integer::intValue).sum();
        double sum2 = list2.stream().mapToInt(Integer::intValue).sum();

        return _calculatePercentage(sum1, sum2);
    }

    // key: abnormal_detect_data 에 적재되어 표시되는 컬럼 명 | value : 쿼리를 통해 호출되는 데이터 컬럼 명
    private final String JUDGE_YN = "FALR_JUDGE_YN";
    private final String ABNORM_CTN = "ABNORM_CTN";
    private final String ALARM_CMT = "ALARM_CMT";
    private final String ALARM_MSG_CTN = "ALARM_MSG_CTN";
    private final String ALARM_DESC = "ALARM_DESC";
    private final String ALARM_YN = "ALARM_YN";
    private final String MSG_NM = "MONTR_IDC_NM";
    private final String IDC_NM = "IDC_NM";
    private final String EVENT_DT = "TIME";
    private final String FAB_ID = "FAB_ID";
    private final String HOST_NM = "HOST_NM";
    private final String MSG_CTN = "MSG_DET_CTN";
    private final String ETC_CTN = "ETC_CTN";
    private final String ALARM_CD = "ALARM_CD";
}