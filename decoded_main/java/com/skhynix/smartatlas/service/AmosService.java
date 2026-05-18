package com.skhynix.smartatlas.service;

import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.data.Carrier.PROCESS_TYPE;
import com.skhynix.smartatlas.data.eq.Conveyor;
import com.skhynix.smartatlas.data.eq.Eqp;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.util.DataService;
import com.skhynix.smartfx.annotation.Service;
import com.skhynix.smartfx.dataaccessfx.DataRow;
import com.skhynix.smartfx.dataaccessfx.DataTable;
import com.skhynix.smartfx.dataaccessfx.DataTableFactory;
import com.skhynix.smartfx.linkfx.channel.ChannelType;

@Service("AMOS_SERVICE")
public class AmosService {
	private static final Logger logger = LoggerFactory.getLogger(AmosService.class);
	private static final String MethodLog = "AMOS_SERVICE#{} : elapsed time={}ms, query={}";
    
    @SuppressWarnings("rawtypes")
	private static Map<String, Map> mapEqpCache = new HashMap<String, Map>();
    
	public String hello() {
	    return "hi";
	}
	
	public boolean alarmParameter(String fabId, String limitType, int value) {
		// 메모리에 기준정보 변경
		DataService.getDataSet().getAlarmLimitMap().put(fabId + ":" + limitType, value);
		
		Tuple tuple = new Tuple();
		tuple.put("FAB_ID", fabId);
		tuple.put("LIMIT_TYPE", limitType);
		tuple.put("VALUE", value);
		
		return LogpressoAPI.setInsertTuple("AMOS_ALARM_PARAMETER", tuple, 100);		
	}
	
	public int getAlarmParameter(String fabId, String limitType) {
		long start = System.currentTimeMillis();
        try {
            //String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "bridgeLayoutWeek");
        	String strQuery = String.format("table AMOS_ALARM_PARAMETER | search FAB_ID==\"%s\" and LIMIT_TYPE==\"%s\" | sort -_time | limit 1 | fields VALUE", fabId, limitType);        	
            List<Map<String, Object>> result = LogpressoAPI.responseResult(strQuery);
            if (result.size() == 0)
            {
            	return 0;
            }
            return (int)result.get(0).get("VALUE");

        }catch (Exception e) {
            logger.error("",e);
        }
        finally {
        	logger.info(MethodLog, "getAlarmParameter", (System.currentTimeMillis() - start));
        }
        return 0; 
	}
	
	public DataTable queryAllCnvTableForUI() {
		long start = System.currentTimeMillis();
		Collection<String> columnNames = new HashSet<String>();		 
		columnNames.add("id");
		//columnNames.add("displayFabMcpNameSet");
		columnNames.add("type"); // EQP, STK, CNV, FIO, SBG
		columnNames.add("portNodeIdList");		
		columnNames.add("isN2"); //STK, SBG
		columnNames.add("processTypeSet"); //STK, SBG		
		columnNames.add("cnvLayoutStr");		
		
		DataTable dt = DataTableFactory.createDataTable(columnNames);		
		for(Eqp eq : DataService.getDataSet().getConveyorMap().values()) {
//			if(eq.getConnectedFabMcpSet()==null || eq.getConnectedFabMcpSet().size() == 0)
//				continue;
			DataRow dr = dt.newRow();
			dr.set("id", eq.getId());
//			dr.set("displayFabMcpNameSet", String.join(",",eq.getConnectedFabMcpSet()));
			dr.set("type", eq.getId().split(":")[1]);
			dr.set("portNodeIdList", String.join(",",eq.getPortNodeIdList()));
			Set<String> pts = new HashSet<>();
			for(PROCESS_TYPE pt : ((Conveyor)eq).getProcessTypeSet()) {
				pts.add(pt.name());
			}
			dr.set("processTypeSet", String.join(",",pts));
			dr.set("cnvLayoutStr", ((Conveyor)eq).getConveyorLayout());
			dt.getRows().add(dr);
		}
		logger.info(MethodLog, "queryAllCnvTableForUI", (System.currentTimeMillis() - start));
		return dt;
	}
}
