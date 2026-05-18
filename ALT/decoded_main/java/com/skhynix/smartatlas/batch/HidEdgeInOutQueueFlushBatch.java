package com.skhynix.smartatlas.batch;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

import org.apache.logging.log4j.util.Strings;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.data.Msg.MSG_TYP;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.map.AbstractEdge;
import com.skhynix.smartatlas.map.edge.RailEdge;
import com.skhynix.smartatlas.util.DataService;

public class HidEdgeInOutQueueFlushBatch implements Job {

	private static final Logger logger = LoggerFactory.getLogger(HidEdgeInOutQueueFlushBatch.class);
	
	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		if (DataService.getInstance() == null || !DataService.getInstance().getInitialized()) {
			return;
		}
		
		logger.info("HID Edge flush start");
		
		var copyMap = new HashMap<String, Integer>();
		
		DataService.getDataSet().getEdgeInOutCountMap().forEach((k, v) -> {
			copyMap.put(new String(k), v.intValue());
		});
		
		DataService.getDataSet().setEdgeInOutCountMap(new ConcurrentHashMap<>());
		
        logger.info("HID Edge flush copied: {}", copyMap.size());

        // 현재 시간 (1분 단위로 정렬)
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:00");
        SimpleDateFormat dateOnlyFormat = new SimpleDateFormat("yyyy-MM-dd");
        Date now = new Date();
        String eventDt = dateFormat.format(now);
        String eventDate = dateOnlyFormat.format(now);

        var fabIdTuples = new HashMap<String, List<Tuple>>();

        for (Map.Entry<String, Integer> entry : copyMap.entrySet()) {
            String[] parts = entry.getKey().split(":");
            var fromHidId = Integer.parseInt(parts[0]);
            var toHidId = Integer.parseInt(parts[1]);
            var fabId = parts[2];
            String mcpName = parts[3];
            String vhlFabId = parts[4];
            String vhlId = parts[5];
            String eqpId = parts[6];                 
            int vhlCountLimit = Integer.parseInt(parts[7]);
            int vhlPrecaution = Integer.parseInt(parts[8]);
            double freeFlowSpeed = Double.parseDouble(parts[9]);
            int hidValue = Integer.parseInt(parts[10]);     
            int transCnt = entry.getValue();

            Tuple tuple = new Tuple();
            tuple.put("EVENT_DATE", eventDate);
            tuple.put("EVENT_DT", eventDt);
            tuple.put("FROM_HIDID", fromHidId);
            tuple.put("TO_HIDID", toHidId);
            tuple.put("TRANS_CNT", transCnt);
            tuple.put("FAB_ID", vhlFabId);
            tuple.put("VHL_ID", vhlId);
            tuple.put("EQP_ID", eqpId);
            tuple.put("MCP_NM", mcpName);
            tuple.put("ENV", Env.getEnv());
            tuple.put("VHL_COUNT_LIMIT", vhlCountLimit);
            tuple.put("VHL_PRECAUTION", vhlPrecaution);
            tuple.put("FREE_FLOW_SPEED", freeFlowSpeed);
            tuple.put("HID_VALUE", hidValue);

            if (fabIdTuples.get(fabId) == null) {
            	fabIdTuples.put(fabId, new ArrayList<Tuple>());
            }
            
            fabIdTuples.get(fabId).add(tuple);
            
            
            // add tib
//            if(임계치조건추가) {
//            	String type = MSG_TYP.OHT.toString() + ".HID.INOUT";
//                Map<String, Object> dataMap = new HashMap<>();
//                
//                dataMap.put("TYPE", type);
//                dataMap.put("FAB_ID", fabId);
//                dataMap.put("EVENT_DT", eventDt);
//                dataMap.put("EVENT_DATE", eventDate);  
//                dataMap.put("FROM_HIDID", fromHidId);  
//                dataMap.put("TO_HIDID", toHidId);  
//                dataMap.put("VHL_ID", vhlId);  
//                dataMap.put("EQP_ID", eqpId);
//                dataMap.put("TRANS_CNT", transCnt);
//                dataMap.put("MCP_NM", mcpName);
//                dataMap.put("ENV", Env.getEnv());
//                dataMap.put("FREE_FLOW_SPEED", freeFlowSpeed);
//                dataMap.put("HID_VALUE", hidValue);
//                
//                for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:amos").keySet()) {
//        			DataService.getInstance().addTibrvMessageQueue(
//        					tibrvKey,
//        					type,
//        					dataMap
//        			);
//        		}	
//            }            
        }

        for (var entry : fabIdTuples.entrySet()) {
        	var fabId = entry.getKey();
        	var tuples = entry.getValue();
        	
            if (Strings.isBlank(fabId)) {
            	return;
            }
            
            // 테이블명: {FAB}_ATLAS_HID_INOUT (예: M14A_ATLAS_HID_INOUT)
            String tableName = fabId + "_ATLAS_HID_INOUT";

            boolean success = LogpressoAPI.setInsertTuples(tableName, tuples, 100);

            if (success) {
                logger.info("HID Edge flush: {} - {} records", tableName, tuples.size());
            }
        }
	}
	
}