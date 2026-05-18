package com.skhynix.smartatlas.process;

import java.util.AbstractMap;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.gson.Gson;
import com.skhynix.smartatlas.comm.TibrvAPI;
import com.skhynix.smartatlas.data.FabProperties;
import com.skhynix.smartatlas.data.Msg;
import com.skhynix.smartatlas.data.Msg.MSG_TYP;
import com.skhynix.smartatlas.data.eq.AmpUnit;
import com.skhynix.smartatlas.data.eq.Eqp;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.environment.type.FunctionItem;
import com.skhynix.smartatlas.environment.type.FunctionItem.FunctionType;
import com.skhynix.smartatlas.util.DataService;


public class AmpMsgWorkerRunnable implements Runnable {
    private static final Logger logger = LoggerFactory.getLogger(AmpMsgWorkerRunnable.class);    
    private Msg msg;
    private String message;
    private String[] tokens;	
    private String eqpId;
    private Eqp eqp;
    private String fabId;
    private String facId;
    private MSG_TYP msgTyp;
    //private String mcpName;
    //private long receivedMilli;
    private String daemon = "";
    private String subject = "";
    FabProperties fabProperties;
	
    public AmpMsgWorkerRunnable(Msg msg) {
    	this.msg = msg;
    }

    @Override
    public void run() {    	
    	this.message = msg.getMessage();
    	this.tokens = StringUtils.splitPreserveAllTokens(msg.getMessage(), ',');
//    	if(this.tokens.length < 20 )
//    	{
//    		logger.info("[{}] {} 수신 패킷: {}", this.tokens[1], this.tokens[2], this.message);	
//    		return;
//    	}
    	
    	this.eqpId = tokens[2]; // 설비 ID
    	this.eqp = DataService.getDataSet().getAllEqpNameMap().get(this.eqpId);
    	if(this.eqp == null || StringUtils.isEmpty(this.eqp.getFabId()))
    	{
    		//logger.info("일치하는 설비가 없습니다 [{}] {} 수신 패킷: {}", this.tokens[1], this.tokens[2], this.message);
    		return;
    	}
    	this.fabId = this.eqp.getFabId();
    	this.fabProperties = DataService.getInstance().getFabPropertiesMap().get(this.fabId);        
        this.facId = this.fabProperties.getFacId();
    	
		
		String requiredKey = fabId + ":AMP";
        FunctionItem functionItem = Env.getSwitchMap().get(requiredKey);        
        if(tokens[1].equals("AGV"))
    	{
        	msgTyp = MSG_TYP.AGV;
        	
        	// AGV_TIBRV_SEND
        	if (functionItem != null && functionItem.getUseFunction(FunctionType.AGV_TIBRV_SEND))
            {
        		this.daemon 	= this.fabProperties.getAgvDaemon();
        		this.subject 	= this.fabProperties.getAgvSubject();
        		TibrvAPI.send("", "", this.daemon, this.subject, "DATA", message);				
            }
        	//~AGV_TIBRV_SEND
        	// AGV_INOUT
            if (functionItem != null && functionItem.getUseFunction(FunctionType.AGV_INOUT))
            {
            	processAgvMsg(tokens);
            }
            //~AGV_INOUT
    	}
    	else if(tokens[1].equals("CNV"))
    	{
    		msgTyp = MSG_TYP.CNV;
    		
    		// CNV_TIBRV_SEND
    		if (functionItem != null && functionItem.getUseFunction(FunctionType.CNV_TIBRV_SEND))
            {
    			this.daemon 	= this.fabProperties.getConveyorDaemon();
        		this.subject 	= this.fabProperties.getConveyorSubject();    		
        		TibrvAPI.send("", "", this.daemon, this.subject, "DATA", message);					
            }
    		//~CNV_TIBRV_SEND
    		// CNV_INOUT
            if (functionItem != null && functionItem.getUseFunction(FunctionType.CNV_INOUT))
            {
            	processCnvMsg(tokens);
            }
            //~CNV_INOUT
    	}	    	
    }

    private void processAgvMsg(String[] tokens) {
    	// 2: UNIT 상태 보고
    	if(tokens[0].equals("2"))
    	{
    		AmpUnit agv = setAmpUnit(tokens);
        	DataService.getDataSet().getAmpAgvBufferMap().add(new AbstractMap.SimpleEntry<>(agv.getId(), agv));	
    	}
    	// 5: ACS POINT 상태 보고
    	// 6: ACS DISABLE POINT LIST 보고
    	// 51: 전체 UNIT 상태 보고 요청
    	// 52: ASC 전체 DISABLE POINT LIST 보고 요청    	
    }
    
    private void processCnvMsg(String[] tokens) {    
    	// 2: UNIT 상태 보고
    	if(tokens[0].equals("2"))
    	{
    		AmpUnit cnv = setAmpUnit(tokens);
        	DataService.getDataSet().getAmpCnvBufferMap().add(new AbstractMap.SimpleEntry<>(cnv.getId(), cnv));	
    	}
    	// 5: ACS POINT 상태 보고
    	// 6: ACS DISABLE POINT LIST 보고
    	// 51: 전체 UNIT 상태 보고 요청
    	// 52: ASC 전체 DISABLE POINT LIST 보고 요청
    }
    
    private AmpUnit setAmpUnit(String[] tokens)
    {
    	AmpUnit unit = new AmpUnit(
			eqp.getFabId(),
			eqp.getId(),
			eqp.getName(), 
			eqp.isAvailable(), 
			eqp.isUpdate(), 
			eqp.getMcsBayNm()
		);    	
    	
    	unit.setKind(tokens[0]);
    	unit.setUnitId(tokens[3]);
    	unit.setHostId(tokens[4]);
    	unit.setStatus(tokens[5]);
    	unit.setCarrierDetect(tokens[6]);
    	unit.setCarrierDetect2(tokens[7]);
    	unit.setErrorCode(tokens[8]);
    	unit.setErrorName(tokens[9]);
    	unit.setAddress(tokens[10]);
    	unit.setNextAddress(tokens[11] == null ? "":tokens[11]);
    	unit.setDestAddress(tokens[12] == null ? "":tokens[12]);    	
    	unit.setCarrierId(tokens[13] == null ? "":tokens[13]);
    	unit.setCarrierId2(tokens[14] == null ? "":tokens[14]);
    	unit.setCycle(tokens[15] == null ? "":tokens[15]);
    	unit.setBufferZoneReady(tokens[16] == null ? "":tokens[16]);
    	unit.setZoneId(tokens[17] == null ? "":tokens[17]);
//    	unit.setMode(tokens[18] == null ? "":tokens[18]);
//    	unit.setDirection(tokens[19] == null ? "":tokens[19]);
    	
    	return unit;
    }
    
//    private boolean _insertLogpresso(HidOffRecordItem recordItem, long currentMilli) {
//        Tuple tuple = new Tuple();
//        String state = recordItem.getState();
//
//        tuple.put("FAB_ID", recordItem.getFabId());
//        tuple.put("MCP_NM", recordItem.getMcpName());
//        tuple.put("ALARM_CD", recordItem.getErrorCode());
//        tuple.put("EVENT_DT", recordItem.getEventDateTimeString());
//        tuple.put("HID_ID", recordItem.getHidId());
//        tuple.put("ADDR_LST", recordItem.getHidAreaAddressString());
//        tuple.put("PORT_LST", recordItem.getAffectedPortString());
//        tuple.put("ENV", Env.getEnv());
//        tuple.put("STATE", state);
//
//        if (state.equals(OHT_TIB_STATE.NORMAL)) {
//            SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
//            tuple.put("RECOVERY_DT", dateFormat.format(new Date(currentMilli)));
//        }
//
//        return LogpressoAPI.setInsertTuples("ATLAS_OHT_HID_OFF", List.of(tuple), 20);
//    }
    
//    private static class UnitState {
//        public static final int Normal = 0;
//        public static final int Stop = 1;
//        public static final int Fault = 2;
//        public static final int Disable = 3;
//    }
}