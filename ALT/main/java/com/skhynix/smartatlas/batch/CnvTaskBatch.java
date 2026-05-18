package com.skhynix.smartatlas.batch;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.data.CnvTask;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.map.edge.LongEdge;
import com.skhynix.smartatlas.util.DataService;
import com.skhynix.smartatlas.util.JsonUtil;

public class CnvTaskBatch implements Job {

	private static final Logger logger = LoggerFactory.getLogger(CnvTaskBatch.class);
	
	private static final String TABLE_CNV_TASK = "ATLAS_HIS_CNV_TASK";
    private static final String TABLE_CNV_LE_STATE = "ATLAS_HIS_CNV_LE_STATE";
    private static final int TIMEOUT_SECOND = 100;
	
	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		if (DataService.getInstance() == null || !DataService.getInstance().getInitialized()) {
			return;
		}
		
		logger.info("Cnv Task flush start");		
		
		List<Map.Entry<String, CnvTask>> copyTaskList = new ArrayList<>();
		Map.Entry<String, CnvTask> entryTask;		
		while ((entryTask = DataService.getDataSet().getCnvTaskBufferMap().poll()) != null) {		    
			copyTaskList.add(entryTask);
		}
		
        logger.info("Cnv Task flush copied: {}", copyTaskList.size());
        if (copyTaskList.size() > 0)
        {
        	List<CnvTask> cnvTaskList = copyTaskList.stream().map(Map.Entry::getValue).collect(Collectors.toList());

            // 출력
            List<Tuple> tplCnvTaskList = new ArrayList<>();
            cnvTaskList.forEach(task -> tplCnvTaskList.add(JsonUtil.getTupleByJsonElement(JsonUtil.toJsonTree(task))));
                
            LogpressoAPI.setInsertTuples(TABLE_CNV_TASK, tplCnvTaskList, TIMEOUT_SECOND);	
        }        
        
        logger.info("Cnv Task flush end");
        
        /////////////////////////////////////////////////////
        
        logger.info("Cnv LongEdge flush start");        
        List<Map.Entry<String, LongEdge>> copyCnvLongEdgeList = new ArrayList<>();
		Map.Entry<String, LongEdge> entryLongEdge;		
		while ((entryLongEdge = DataService.getDataSet().getCnvLongEdgeBufferMap().poll()) != null) {		    
			copyCnvLongEdgeList.add(entryLongEdge);
		}
		
        logger.info("Cnv LongEdge flush copied: {}", copyCnvLongEdgeList.size());
        if (copyCnvLongEdgeList.size() > 0)
        {
        	 List<LongEdge> cnvLongEdgeList = copyCnvLongEdgeList.stream().map(Map.Entry::getValue).collect(Collectors.toList());
        	 
             List<Tuple> tplList = new ArrayList<>();
             cnvLongEdgeList.forEach(le -> {
            	 Tuple tpl = new Tuple();
            	 
            	 long cost = le.getCost("");
            	 double speed = (double)le.getLength()/(double)cost*60d;
            	 
            	 tpl.put("id", le.getId());
            	 tpl.put("isAvailable", le.isAvailable());				
            	 tpl.put("cost", cost);
            	 tpl.put("speed", speed);           	 
             });
                 
             LogpressoAPI.setInsertTuples(TABLE_CNV_LE_STATE, tplList, TIMEOUT_SECOND); 	
        }        
        logger.info("Cnv LongEdge flush end");
	}	
}
