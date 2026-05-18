package com.skhynix.smartatlas.util;

import com.skhynix.smartatlas.data.HidOffRecordItem;
import com.skhynix.smartatlas.data.RailCutRecordItem;
import com.skhynix.smartatlas.data.RailVibrationRecordItem;
import com.skhynix.smartatlas.data.VhlOffRecordItem;
import com.skhynix.smartatlas.process.OhtMsgWorkerRunnable.*;
import com.skhynix.smartatlas.service.TibrvService.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;

public class LayoutUtil {
    private static final Logger logger = LoggerFactory.getLogger(LayoutUtil.class);

    public static <T> Map<String, String> buildLayoutMessageDataMap(T data) {
        XmlUtil.loadAlarmMessage();

        String className = "";

        if (data instanceof HidOffRecordItem) {
            className = "HidOffRecordItem";
        } else if (data instanceof VhlOffRecordItem) {
            className = "VhlOffRecordItem";
        } else if (data instanceof RailCutRecordItem) {
            className = "RailCutRecordItem";
        } else if (data instanceof RailVibrationRecordItem) {
            className = "RailVibrationRecordItem";
        }

        String type;    // ex: HIDOFF, VHLOFF, RAILCUT
        String fabId;
        String facId;
//        String eventDate; // event date (exclude time)
        String deviceName;  // device name (전 device id)
        String state;
        Object addressList = "";
        Object portList;
        String alarmCode = "";
        String alarmDescription = "";
        String alarmTitle = "";
        String alarmMessageContents = "";

        switch (className) {
            case "HidOffRecordItem": {
                HidOffRecordItem temp = (HidOffRecordItem) data;
                String code = String.format("HID%03d", temp.getHidId());

                type = temp.getAlarmType();
                fabId = temp.getFabId();
                facId = temp.getFacId();
//                eventDate = temp.getEventDateTimeString();
                deviceName = temp.getDeviceId();
                state = temp.getState();
                addressList = temp.getHidAreaAddressString();
                portList = temp.getAffectedPortString();
                alarmCode = temp.getAlarmCode();

                if (state.equals(OHT_TIB_STATE.ABNORMAL)) {
	                alarmDescription = XmlUtil.getMessage("OHT_LAYOUT_HID_OFF_DESC", fabId, code);
	                alarmTitle = XmlUtil.getMessage("OHT_LAYOUT_HID_OFF_TITLE", fabId, code);
	                alarmMessageContents = XmlUtil.getMessage("OHT_LAYOUT_HID_OFF_CONTENTS", temp.getAffectedPortString());
                }
            } break;
            case "VhlOffRecordItem": {
                VhlOffRecordItem temp = (VhlOffRecordItem) data;
                String machineId = temp.getMachineId();

                type = temp.getAlarmType();
                fabId = temp.getFabId();
                facId = temp.getFacId();
//                eventDate = temp.getEventDateTimeString();
                deviceName = temp.getDeviceId();
                state = temp.getState();
                addressList = temp.getAffectedAddressString();
                portList = temp.getAffectedPortString();
                alarmCode = temp.getErrorCode();
                
                if (state.equals(OHT_TIB_STATE.ABNORMAL)) {
	                alarmDescription = XmlUtil.getMessage("OHT_LAYOUT_VHL_OFF_DESC", fabId, machineId);
	                alarmTitle = XmlUtil.getMessage("OHT_LAYOUT_VHL_OFF_TITLE", fabId, temp.getStoppedFromAddress() + ":" + temp.getStoppedToAddress());
	                alarmMessageContents = XmlUtil.getMessage("OHT_LAYOUT_VHL_OFF_CONTENTS", temp.getAffectedPortString());
                }
            } break;
            case "RailCutRecordItem": {
                RailCutRecordItem temp = (RailCutRecordItem) data;

                type = temp.getAlarmType();
                fabId = temp.getFabId();
                facId = temp.getFacId();
//                eventDate = temp.getEventDateTimeString();
                deviceName = temp.getDeviceId();
                state = temp.getState();
                addressList = temp.getAffectedAddressString();
                portList = temp.getAffectedPortString();
                alarmCode = "";

                if (state.equals(OHT_TIB_STATE.ABNORMAL)) {
	                alarmDescription = XmlUtil.getMessage("OHT_LAYOUT_RAIL_CUT_DESC", fabId, deviceName);
	                alarmTitle = XmlUtil.getMessage("OHT_LAYOUT_RAIL_CUT_TITLE", fabId, temp.getRailCutFromAddress() + ":" + temp.getRailCutToAddress());
	                alarmMessageContents = XmlUtil.getMessage("OHT_LAYOUT_RAIL_CUT_CONTENTS", temp.getAffectedPortString());
                }
            } break;
            case "RailVibrationRecordItem": {
                RailVibrationRecordItem temp = (RailVibrationRecordItem) data;
                String directory = String.join(",", temp.getDirectory());

                type = temp.getAlarmType();
                fabId = temp.getFabId();
                facId = temp.getFacId();
//                eventDate = temp.getEventDateTimeString();
                deviceName = String.valueOf(temp.getAddress());
                portList = String.join(",", temp.getDirectory());
                state = temp.getState();

                if (state.equals(OHT_TIB_STATE.ABNORMAL)) {
                    addressList = XmlUtil.getMessage(
                            "OHT_LAYOUT_RAIL_VIBRATION_TOOLTIP",
                            temp.getAddressString(), // 0
                            String.join("/", temp.getDirectory()), // 1
                            temp.getTerm1(), // 2
                            temp.getTerm1EachGForce(), // 3
                            (temp.getTerm2() - temp.getTerm1()), // 4
                            temp.getTerm2EachGForce(), // 5
                            temp.getUpDownRate() // 6
                    );
                    alarmDescription = XmlUtil.getMessage("OHT_LAYOUT_RAIL_VIBRATION_DESC", fabId, temp.getAddress(), directory);
                    alarmTitle = XmlUtil.getMessage("OHT_LAYOUT_RAIL_VIBRATION_TITLE", fabId, temp.getAddress(), directory);
                    alarmMessageContents = XmlUtil.getMessage("OHT_LAYOUT_RAIL_VIBRATION_CONTENTS", fabId, temp.getAddress(), directory);
                }
            } break;
            default: {
                logger.error("... Invalid data type({}) [building message content] !!!", className);

                return new HashMap<>() ;
            }
        }

        return buildLayoutMessageDataMap(
                    type,
                    fabId,
//                    eventDate,
                    deviceName,
                    state,
                    addressList,
                    portList,
                    alarmMessageContents,
                    alarmCode,
                    facId,
                    alarmDescription,
                    alarmTitle,
                    state.equals(OHT_TIB_STATE.ABNORMAL)
        );
    }

    public static Map<String, String> buildLayoutMessageDataMap (
            String type,    // ex: HIDOFF, VHLOFF, RAILCUT
            String fabId,
//            String eventDate, // event date (exclude time)
            String deviceName,  // device name (전 device id)
            String state,
            Object addressList,
            Object portList,
            String alarmMessageContents, // ALARM_MSG_CTN
            String alarmCode,
            String facId,   // fabId
            String alarmDescription, // ALARM_DESC
            String alarmComment, // ALARM_CMT
            boolean isOccurredAlarm // (2025-07-14) star 측, alarm 발생 구분을 위해 추가
    ) {
        // message 구성 전 검증
        if (type == null || type.isEmpty()) {
            logger.error("... Invalid device type [building message content] !!!");
            return new HashMap<>() ;
        }

        if (fabId == null || fabId.isEmpty()) {
            logger.error("... Invalid fab id [building message content] !!!");
            return new HashMap<>() ;
        }

//        if (eventDate == null) {
//            logger.error("... Invalid event date [building message content] !!!");
//            return new HashMap<>() ;
//        }

        if (deviceName == null || deviceName.isEmpty()) {
            logger.error("... Invalid device name [building message content] !!!");
            return new HashMap<>() ;
        }

        if (state == null || state.isEmpty()) {
            logger.error("... Invalid state [building message content] !!!");
            return new HashMap<>() ;
        }

        if (addressList == null) logger.warn("... address list is null [building message content] !");

        if (portList == null) logger.warn("... port list is null [building message content] !");

        if (alarmMessageContents == null) {
            logger.warn("... alarm message is null [building message content] !");

            alarmMessageContents = "";
        }

        if (alarmCode == null) {
            logger.warn("... alarm code is null [building message content] !");

            alarmCode = "";
        }

        if (facId == null || facId.isEmpty()) {
            logger.error("... Invalid fac id [building message content] !!!");
            return new HashMap<>() ;
        }

        if (alarmDescription == null) {
            logger.warn("... alarm description is null [building message content] !");

            alarmDescription = "";
        }

        // message 구성
        Map<String, String> dataMap = new HashMap<>();

        dataMap.put(LAYOUT_MEMBER.DEVICE_TYPE, type);
        dataMap.put(LAYOUT_MEMBER.FAB_ID, fabId);
//        dataMap.put(LAYOUT_MEMBER.EVENT_OCCURRED_DATE, eventDate);

        long now = System.currentTimeMillis();
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
        String time = dateFormat.format(now);

        dataMap.put(LAYOUT_MEMBER.EVENT_OCCURRED_DATE, time);
        dataMap.put(LAYOUT_MEMBER.DEVICE_NAME, deviceName);
        dataMap.put(LAYOUT_MEMBER.LAYOUT_STATE, state);

        if (addressList != null) {
            if (addressList instanceof String) {
                dataMap.put(LAYOUT_MEMBER.ADDRESS_LIST, (String) addressList);
            } else if (addressList instanceof List) {
                dataMap.put(LAYOUT_MEMBER.ADDRESS_LIST, String.join(",", (List<String>) addressList));
            } else if (addressList instanceof Set) {
                dataMap.put(LAYOUT_MEMBER.ADDRESS_LIST, String.join(",", (Set<String>) addressList));
            } else {
                throw new IllegalArgumentException(
                        String.format("... Invalid address list type(%s) [building message content] !!!", addressList.getClass().getName())
                );
            }
        }

        if (portList != null) {
            if (portList instanceof String) {
                dataMap.put(LAYOUT_MEMBER.PORT_LIST, (String) portList);
            } else if (portList instanceof List) {
                dataMap.put(LAYOUT_MEMBER.PORT_LIST, String.join(",", (List<String>) portList));
            } else if (portList instanceof Set) {
                dataMap.put(LAYOUT_MEMBER.PORT_LIST, String.join(",", (Set<String>) portList));
            } else {
                throw new IllegalArgumentException(
                        String.format("... Invalid port list type(%s) [building message content] !!!", portList.getClass().getName())
                );
            }
        }
        
        dataMap.put(LAYOUT_MEMBER.ALARM_DESCRIPTION, alarmDescription);
        dataMap.put(LAYOUT_MEMBER.ALARM_COMMENT, alarmComment);
        dataMap.put(LAYOUT_MEMBER.ALARM_MESSAGE_CONTENTS, alarmMessageContents);
        dataMap.put(LAYOUT_MEMBER.ALARM_CODE, alarmCode);
        dataMap.put(LAYOUT_MEMBER.FAC_ID, facId);
        
        switch(type) {
            case SEND_SUB_SUBJECT.HID_OFF: {
                dataMap.put(LAYOUT_MEMBER.ALARM_LEVEL, "1");
            } break;
            case SEND_SUB_SUBJECT.VHL_OFF:
            case SEND_SUB_SUBJECT.RAIL_CUT: {
                dataMap.put(LAYOUT_MEMBER.ALARM_LEVEL, "2");
            } break;
            case SEND_SUB_SUBJECT.RAIL_VIBRATION: {
                dataMap.put(LAYOUT_MEMBER.ALARM_LEVEL, "3");
            } break;
        }

        dataMap.put(LAYOUT_MEMBER.ALARM_YN, isOccurredAlarm ? "Y" : "N");

        return dataMap;
    }

    public static class LAYOUT_MEMBER {
        public static final String DEVICE_TYPE = "DEVICE_TYP";
        public static final String FAB_ID = "FAB_ID";
        public static final String EVENT_OCCURRED_DATE = "EVENT_DT";
        public static final String DEVICE_NAME = "DEVICE_NM";
        public static final String LAYOUT_STATE = "FALR_STAT_TYP";
        public static final String ADDRESS_LIST = "FALR_RAISE_ADDR_LVAL";
        public static final String PORT_LIST = "FALR_AFFECT_PORT_LVAL";
        public static final String ALARM_MESSAGE_CONTENTS = "ALARM_MSG_CTN";
        public static final String ALARM_COMMENT = "ALARM_CMT";
        public static final String ALARM_CODE = "ALARM_CD";
        public static final String FAC_ID = "FAC_ID";
        public static final String ALARM_DESCRIPTION = "ALARM_DESC";
        public static final String ALARM_LEVEL = "ALARM_LEVEL_VAL";
        public static final String ALARM_YN = "ALARM_YN";
    }
}
