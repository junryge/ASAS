package com.skhynix.smartatlas.batch;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

import org.bson.Document;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.mongodb.client.model.InsertManyOptions;
import com.skhynix.smartatlas.data.eq.AmpUnit;
import com.skhynix.smartatlas.db.mongodb.MongodbAPI;
import com.skhynix.smartatlas.queryformat.MongodbMcslogQuery;
import com.skhynix.smartatlas.util.DataService;

public class AmpBufferFlushBatch implements Job {
	private static final Logger logger = LoggerFactory.getLogger(AmpBufferFlushBatch.class);	
    private final InsertManyOptions insertOptions = new InsertManyOptions().ordered(false);
    
	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		if (DataService.getInstance() == null || !DataService.getInstance().getInitialized()) {
			return;
		}
		
		logger.info("Amp Buffer Flush Batch start");		
		
		List<Map.Entry<String, AmpUnit>> copyAmpAgvBufferList = new ArrayList<>();
		Map.Entry<String, AmpUnit> entryAgv;		
		while ((entryAgv = DataService.getDataSet().getAmpAgvBufferMap().poll()) != null) {		    
			copyAmpAgvBufferList.add(entryAgv);
		}
		
        logger.info("amp Agv flush copied size: {}", copyAmpAgvBufferList.size());
        if (copyAmpAgvBufferList.size() > 0)
        {
        	List<AmpUnit> agvList = copyAmpAgvBufferList.stream().map(Map.Entry::getValue).collect(Collectors.toList());
        	
        	// 2. fabId 별로 그룹화 (핵심 코드)
            Map<String, List<AmpUnit>> groupedByFabId = agvList.stream().collect(Collectors.groupingBy(AmpUnit::getFabId));
            // 3. Group(FabId별로 저장)
            groupedByFabId.forEach((fabId, list) -> {
//                System.out.println("=== FabID: " + fabId + " ===");
//                list.forEach(System.out::println);
//                Gson gson 				= new Gson();
//                list.forEach(item -> logger.info("{}", gson.toJson(item)));
                
                //Logpresso에 저장
                //List<Tuple> tplList = new ArrayList<>();
                //list.forEach(agv -> tplList.add(JsonUtil.getTupleByJsonElement(JsonUtil.toJsonTree(agv))));
                //LogpressoAPI.setInsertTuples(TABLE_AMP_AGV, tplList, TIMEOUT_SECOND);
                
                //Mongo에 저장
                String suffix = MongodbMcslogQuery.getSuffix(fabId);
				Map<String,String> queryParameter = new HashMap<String, String>();				
				queryParameter.put("FABID", fabId);
				var docList = new ArrayList<Document>();
				list.forEach(item -> {
					ObjectMapper objectMapper = new ObjectMapper();
					Map<String, Object> map = objectMapper.convertValue(item, Map.class);
					docList.add(new Document(map));
				});
				MongodbAPI.insertMany(fabId, "amp_agv_status_"+ suffix, docList, insertOptions);
				//docList.clear();
            });
        }
        
		
		List<Map.Entry<String, AmpUnit>> copyAmpCnvBufferList = new ArrayList<>();
		Map.Entry<String, AmpUnit> entryCnv;		
		while ((entryCnv = DataService.getDataSet().getAmpCnvBufferMap().poll()) != null) {		    
			copyAmpCnvBufferList.add(entryCnv);
		}
		
        logger.info("amp Cnv flush copied size: {}", copyAmpCnvBufferList.size());
        if (copyAmpCnvBufferList.size() > 0)
        {
        	List<AmpUnit> cnvList = copyAmpCnvBufferList.stream().map(Map.Entry::getValue).collect(Collectors.toList());
        	
        	// 2. fabId 별로 그룹화 (핵심 코드)
            Map<String, List<AmpUnit>> groupedByFabId = cnvList.stream().collect(Collectors.groupingBy(AmpUnit::getFabId));
            // 3. Group(FabId별로 저장)
            groupedByFabId.forEach((fabId, list) -> {
//                System.out.println("=== FabID: " + fabId + " ===");
//                list.forEach(System.out::println);
//                Gson gson 				= new Gson();
//                list.forEach(item -> logger.info("{}", gson.toJson(item)));
                
                //Logpresso에 저장
                //List<Tuple> tplList = new ArrayList<>();
                //list.forEach(cnv -> tplList.add(JsonUtil.getTupleByJsonElement(JsonUtil.toJsonTree(cnv))));
                //LogpressoAPI.setInsertTuples(TABLE_AMP_CNV, tplList, TIMEOUT_SECOND);
                
                //Mongo에 저장
                String suffix = MongodbMcslogQuery.getSuffix(fabId);
				Map<String,String> queryParameter = new HashMap<String, String>();				
				queryParameter.put("FABID", fabId);
				var docList = new ArrayList<Document>();
				list.forEach(item -> {
					ObjectMapper objectMapper = new ObjectMapper();
					Map<String, Object> map = objectMapper.convertValue(item, Map.class);
					docList.add(new Document(map));
				});
				MongodbAPI.insertMany(fabId, "amp_cnv_status_"+ suffix, docList, insertOptions);				
				//docList.clear();
            });
        }
        
        logger.info("Amp Buffer Flush Batch end");       
	}	
}
