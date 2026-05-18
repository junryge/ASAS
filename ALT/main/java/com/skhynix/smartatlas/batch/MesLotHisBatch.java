package com.skhynix.smartatlas.batch;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.Set;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.stream.Collectors;

import org.apache.logging.log4j.util.Strings;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.util.FilePathUtil;
import com.skhynix.smartatlas.util.JsonUtil;
import com.skhynix.smartatlas.util.Util;
import com.skhynix.smartatlas.util.XmlUtil;
import com.skhynix.smartfx.dataaccessfx.QueryExecutor;
import com.skhynix.smartfx.dataaccessfx.QueryExecutorFactory;

public class MesLotHisBatch implements Job{
    private final Logger logger     = LoggerFactory.getLogger(getClass());
    private final int DELAYED_TIME  = 1000 * 60;
    private final List<String> facIds = List.of("M16");    
    
    private ConcurrentLinkedQueue<Map<String, Object>> fabTransQueue = new ConcurrentLinkedQueue<>();	// FAB간 반송
    private ConcurrentLinkedQueue<Map<String, Object>> floorTransQueue = new ConcurrentLinkedQueue<>();	// 층간 반송
    private List<Map<String, Object>> mesLotHisList = new ArrayList<>();
    private List<Map<String, Object>> lotProcTimeInfList = new ArrayList<>();
    private List<Map<String, Object>> jobEndList = new ArrayList<>();
    private List<Map<String, Object>> jobOperList = new ArrayList<>();
    private List<Map<String, Object>> jobMesNodeMasList = new ArrayList<>();
    private List<Map<String, Object>> jobBizLotfutureactInfList = new ArrayList<>();
    private List<Map<String, Object>> jobMesOperMasList = new ArrayList<>();    
    private List<Map<String, Object>> jobMesLotMasList = new ArrayList<>();
    private List<Map<String, Object>> jobSFabLotMoveMasList = new ArrayList<>();    
    private List<String> exclusiveOperList = new ArrayList<>();
    private Set<String> existingKeys = new HashSet<>();
    private Map<String, List<Map<String, Object>>> operListLogMap = new HashMap<>();
    private List<Tuple> tplList = new ArrayList<>();
    
//  (( 다음 공정 기반 Hubroom 반송량 예측 )) 1차로 설계된 내용 공유드립니다.  
//  차주중으로 쿼리및 상세 로직 추가로 작성해서 전달 드리겠습니다.  
//  Jobend 시간은 job의 평균 시간을 가져와서 사용 예정입니다. ( 추후 Develop 예정입니다. )  
//  - 현재 평균 Jobend 예상 시간 정확도는 아래와 같습니다.  
//  실제 종료 시간 과 예상 종료 시간의 차이가 1분 이내 : 79% ( 420 공정 )  
//  실제 종료 시간 과 예상 종료 시간의 차이가 2분 이내 : 88% ( 468 공정 )  
//  실제 종료 시간 과 예상 종료 시간의 차이가 3분 이내 : 91% ( 487 공정 )  
//   - Next Oper 공정 예상로직의 정확도는 87% 입니다.  ( 개선중입니다.  )
//
//  확인후 추가 개선점이나 아이디어 있으시면 편하게 주시면 감사드리겠습니다.
//
//- Batch Cron : 0 * * * * ? 에 실행,VIEW가 매분0초에 갱신되는 듯, -1분 >= jobstart && jobstart < 현재시간 기준으로  가져옴
//- ATLAS_LOTPROCTIME_INF : updatePredictJobendTime, 예상 jobend 시간 계산 결과 저장 테이블
//- ATLAS_LOTPROCTIME_FAB_TRANS : FAB간 반송 
//- ATLAS_LOTPROCTIME_FLOOR_TRANS : 층간 반송
       
    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
    	if (!Util.isCurrentIC()) return;
    	
    	logger.info("... `{}` has started`", this.getClass().getName());

        long timer = System.currentTimeMillis();

        this._start();

        long checkTimer = System.currentTimeMillis() - timer;

        if (checkTimer >= DELAYED_TIME) {
            logger.error("... !!!DELAYED!!! `{}` has finished [elapsed time: {}m ({}ms)]", this.getClass().getSimpleName(), checkTimer / (60 * 1000), checkTimer);
        } else {
            logger.info("... `{}` has finished [elapsed time: {}ms]", this.getClass().getSimpleName(), checkTimer);
        }
    }
        
    private void _start() {

    	// 1분 동안  Jobstart 된 Lot list 불러오기
    	// 1. 파라미터를 담을 Map 생성
		// 현재 시간 가져오기
        LocalDateTime now = LocalDateTime.now();
        DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMddHHmm00000000");       
        
        String timeFrom = now.minusMinutes(10).format(DateTimeFormatter.ofPattern("yyyyMMddHHmm00000000"));
        String timeTo = now.format(formatter);

//        timeFrom = now.minusMinutes(1).format(DateTimeFormatter.ofPattern("yyyyMMddHHmm00000000"));
//        timeFrom = "20260424141533970378";
//        timeTo = "20260424141533970379";
        
    	for (String facId : facIds) {    		
			info(facId, timeFrom, timeTo, " Started", false);
			_run(facId, timeFrom, timeTo);
		}
	}
    
    private void _run(String facId, String timeFrom, String timeTo) {

        // init
    	fabTransQueue.clear();
        floorTransQueue.clear();
        mesLotHisList = new ArrayList<>();
        lotProcTimeInfList = new ArrayList<>();
        jobEndList = new ArrayList<>();
        jobOperList = new ArrayList<>();
        jobMesNodeMasList = new ArrayList<>();
        jobBizLotfutureactInfList = new ArrayList<>();
        jobMesOperMasList = new ArrayList<>();
        jobMesLotMasList = new ArrayList<>();
        jobSFabLotMoveMasList = new ArrayList<>();
        exclusiveOperList = new ArrayList<>();
        existingKeys = new HashSet<>();
        operListLogMap = new HashMap<>();
        
        try {
        	
        	// MES_LOT_HIS: LOT_ID, TIMEKEY 기준 unique        	
        	// Oracle에서 MES_LOT_HIS에서 timeFrom ~ timeTo 기준 LOT_ID, TIMEKEY 조회
        	mesLotHisList = getMesLotHisList(facId, timeFrom, timeTo);            
        	if (mesLotHisList == null || mesLotHisList.isEmpty()) return;
        	
            // logpresso에서 ATLAS_LOTPROCTIME_INF에서 timeFrom ~ timeTo 기준 LOT_ID, TIMEKEY 조회
        	lotProcTimeInfList = getLotProcTimeInf(facId, timeFrom, timeTo);        	
        	
            // 1. 참조 목록 (lotProcTimeInfList) 의 데이터를 빠른 검색을 위해 Set 에 저장
            // 키 포맷: "LOT_ID#LOT_ID" is unique            
            for (Map<String, Object> row : lotProcTimeInfList) {
                String _lotId = row.get("LOT_ID").toString();
                String _timekey = row.get("TIMEKEY").toString();
                
                // null 처리 안전장치
                if (_lotId != null && _timekey != null) {
                    existingKeys.add(createCompositeKey(_lotId, _timekey));
                }
            }

            // 2. 대상 목록 (mesLotHisList) 을 스트림으로 필터링
            jobEndList = mesLotHisList.stream()
                .filter(_row -> {
                	String _lotId = _row.get("LOT_ID").toString();
                    String _timekey = _row.get("TIMEKEY").toString();

                    if (_lotId == null || _timekey == null) return true;

                    String _key = createCompositeKey(_lotId, _timekey);
                    
                    // existingKeys 에 해당 키가 없는데이타만 대상
                    return !existingKeys.contains(_key);
                })
                .collect(Collectors.toList());
            
            if (jobEndList == null && jobEndList.size() == 0) return;
            
        	// 4.
            // [Return]
            // MesLotMas 가져오기		: jobMesLotMasList
            // SFabLotMoveMas 가져오기	: jobSFabLotMoveMasList
            // 공정수순 가져오기 		: jobOperList
            // [SetUpSetMo]
            // BizLotFutureActInf 가져오기	: jobBizLotfutureactInfList
            // [N2Purge]
            // MesOperMas 가져오기		: jobMesOperMasList            
            setJobSubList(facId, timeFrom, timeTo);
            if(jobOperList.size() == 0) return;            
            
            logger.debug("... _run jobEndList size: {}", jobEndList.size());
        	// 5.            
    		for(Map<String, Object> item : jobEndList)
    		{        			          
    			// LotId
    			String lotId = item.get("LOT_ID").toString();
    			// LotId
    			String timekey = item.get("TIMEKEY").toString();
    			// flowID
    			String flowId = item.get("FLOW_ID").toString();
    			// 현재 공정 가져오기
    	    	String operId = item.get("OPER_ID").toString();
    	    	// 다음 고정
    	    	String nextOper = "";
    	    	String nextStep = "";
    	    	
    	    	logger.debug("... _run lotId: {}, timekey: {}, flowId: {}, operId: {}", lotId, timekey, flowId, operId);
    	    	
    	    	// 집계 예외 공정 여부
    	    	if (exclusiveOperList.contains(operId)) {
    	    		String msg = String.format("... _run currentOper is in exclusiveOperList, lotId: %s, timekey: %s, flowId: %s, operId: %s", lotId, timekey, flowId, operId);
    	    		info(facId, timeFrom, timeTo, msg, false);
    	    		continue;
    	    	}
    	    	
    	    	// 5. 공정수순 가져오기 로직
    	    	List<Map<String, Object>> operList = getOperList(facId, timeFrom, timeTo, lotId, flowId, operId);
    	    	if(operList.size() == 0) {
    	    		String msg = String.format("... _run operList is empty, lotId: %s, timekey: %s, flowId: %s, operId: %s", lotId, timekey, flowId, operId);
    	    		info(facId, timeFrom, timeTo, msg, false);
    	    		continue;
    	    	}
    	    	
    	    	// log 저장용
    	    	String logKey = lotId + "#" + timekey;
    	    	operListLogMap.put(logKey, operList);
    	    	
    	    	// 6. next공정 찾기
    	    	// isReturn
    	    	// isSetUpSetMo
    	    	// isN2PurgeOper    	    	
    	    	// 문서에는 -2로 되어 있는데 -1로 변경
    	    	//for(int i=0;i<operList.size() - 2;i++)
    	    	for(int i=0;i<operList.size() - 1;i++)
    	    	{
    	    		Map<String, Object> operMap = operList.get(i);
    	    		String _nextFlowId = operMap.get("FLOW_ID").toString();
    	    		String _nextOperId = operMap.get("OPER_ID").toString();
    	    		//int _nextOpenSeq = Integer.parseInt(operMap.get("OPER_SEQ").toString());
    	    		//String _nextMidOperTyp = operMap.get("MID_OPER_TYP").toString();
    	    		//int _nextIsStopPoint = Integer.parseInt(operMap.get("IS_STOP_POINT").toString());
    	    		
    	    		//IsReturn
    	    		Boolean b0 = isReturnOper(facId, timeFrom, timeTo, lotId, _nextOperId); 
    	    		if(b0)
    	    		{
    	    			nextOper = _nextOperId;
    	    			nextStep = "isReturnOper";
    	    			break;
    	    		}
    	    		
    	    		// 해당 공정에 Setmo 가 걸려 있는지
    	    		Boolean b1 = isSetUpSetMo(facId, timeFrom, timeTo, lotId, _nextFlowId, _nextOperId); 
    	    		// 해당 공정이 진행 필요한 N2 purge 공정인지
    	    		Boolean b2 = isN2PurgeOper(facId, timeFrom, timeTo, lotId, operId, _nextOperId);
    	    		if(b1 || b2)
    	    		{
    	    			nextOper = _nextOperId;
    	    			nextStep = b1 && b2? "isSetUpSetMo|isN2PurgeOper"
    	    						:b1? "isSetUpSetMo":"isN2PurgeOper";
    	    			break;
    	    		}
    	    	}    	    	
    	    	if(nextOper.isEmpty())
    	    	{
    	    		nextOper = operList.get(operList.size() - 1).get("OPER_ID").toString();
    	    		nextStep = "IS_STOP_POINT";
    	    	}
    	    	item.put("NEXT_OPER", nextOper);
    	    	item.put("NEXT_STEP", nextStep);
//    	    	if(nextOper.equalsIgnoreCase("SEND"))
//    	    	{
//    	    		fabTransQueue.add(item);
//    	    	}
//    	    	else if(nextOper.equalsIgnoreCase("RETURN"))
//    	    	{
//    	    		fabTransQueue.add(item);
//    	    	}
    	    	String msg = String.format("... _run operList size: %s, First: %s, Last: %s, nextOper: %s, nextStep: %s"
    	    			, operList.size()
    	    			, operList.get(0).get("OPER_SEQ") + " | " + operList.get(0).get("OPER_ID")
    	    			, operList.get(operList.size() - 1).get("OPER_SEQ") + " | " + operList.get(operList.size() - 1).get("OPER_ID")
    	    			, nextOper
    	    			, nextStep);
    	    	
	    		info(facId, timeFrom, timeTo, msg, false);
    		}
    		
    		// 7. 로그프레소 저장
    		insertLotProctimeInftoLogpresso(jobEndList);
    		insertLogsToLogpresso(facId, timeFrom, timeTo, operListLogMap, jobBizLotfutureactInfList, jobMesOperMasList, jobMesLotMasList, jobSFabLotMoveMasList);
        	insertfabTransQueueToLogresso();
        	insertFloorTransQueueToLogresso();
        	
        } catch (Exception e) {
            logger.error("", e);
        }
        finally {
        	String msg = String.format(":::::::::: _run end : facId %s, mesLotHisList %s, lotProcTimeInfList %s, existingKeys %s, jobEndList(insert) %s, "
        			+ "jobOperList %s, jobMesNodeMasList %s, jobBizLotfutureactInfList %s, jobMesOperMasList %s, jobMesLotMasList %s, jobSFabLotMoveMasList %s, "
        			+ "fabTransQueue %s, floorTransQueue %s"
        			, facId
        			, mesLotHisList.size()
        			, lotProcTimeInfList.size()
        			, existingKeys.size()
        			, jobEndList.size()        		
        			
        			, jobOperList.size()
        			, jobMesNodeMasList.size()
        			, jobBizLotfutureactInfList.size()
        			, jobMesOperMasList.size()
        			, jobMesLotMasList.size()
        			, jobSFabLotMoveMasList.size()
        			
        			, fabTransQueue.size()
        			, floorTransQueue.size());
        	info(facId, timeFrom, timeTo, msg, true);
        }
    }    

    private List<Map<String, Object>> getMesLotHisList(String facId, String timeFrom, String timeTo)
    {
    	QueryExecutor factory = QueryExecutorFactory.getQueryExecutor(facId.toUpperCase() + "_VIEW_MES");
    	List<Map<String, Object>> list = new ArrayList<>();
		
    	try
    	{    		
    		String xmlPath = FilePathUtil.factoryPath(factory.getConnectionId());
    		String strQuery = XmlUtil.loadQuery(xmlPath , "SELECT_JOB_ENDTIME");
    		strQuery = String.format(strQuery, timeFrom, timeTo);    		
    		//logger.info(String.format(":::::::::: sQuery SELECT_JOB_ENDTIME : %s", strQuery));    		
    		list = factory.selectList(strQuery);
    	}
    	catch(Exception ex)
    	{
    		logger.error("getMesLotHisList error", ex);
    	}
    	finally
    	{
    		factory.close();    		
    	}   
    	return list;
    }

    public List<Map<String,Object>> getLotProcTimeInf(String facId, String timeFrom, String timeTo){
        List<Map<String, Object>> result = new ArrayList<>();
        
        try {
        	String strQuery = "table ATLAS_LOTPROCTIME_INF "
        			+ "| search FAC_ID==\"%s\" and TIMEKEY>=\"%s\" and TIMEKEY<\"%s\" "
        			+ "| fields LOT_ID, TIMEKEY";
			strQuery = String.format(strQuery, facId, timeFrom, timeTo);        	
        	result = LogpressoAPI.responseResult(strQuery);
        }catch (Exception e) {
            logger.error("getLotProcTimeInf error",e);
        }
        return result;
    }

    private static String createCompositeKey(String _lotId, String _timekey) {
        return _lotId + "#" + _timekey;
    }

    private void setJobSubList(String facId, String timeFrom, String timeTo) {
		QueryExecutor factory = null;
				
		try
		{
			factory = QueryExecutorFactory.getQueryExecutor(facId.toUpperCase() + "_VIEW_MES");
			String xmlPath = FilePathUtil.factoryPath(factory.getConnectionId());
			
			// 1	
	  		String sQuery = XmlUtil.loadQuery(xmlPath , "SELECT_JOB_OPER_LIST");
	  		sQuery = String.format(sQuery, facId, timeFrom, timeTo);	  		
    		//logger.info(String.format(":::::::::: sQuery SELECT_JOB_OPER_LIST : %s", sQuery));
	  		jobOperList = factory.selectList(sQuery);	        
	        
	        // 2
    		sQuery = XmlUtil.loadQuery(xmlPath , "SELECT_JOB_MES_NODE_MAS");
    		sQuery = String.format(sQuery, timeFrom, timeTo);
    		//logger.info(String.format(":::::::::: sQuery SELECT_JOB_MES_NODE_MAS : %s", sQuery));    		
			jobMesNodeMasList = factory.selectList(sQuery);				
	        	     	
			// 3
			sQuery = XmlUtil.loadQuery(xmlPath , "SELECT_JOB_BIZ_LOTFUTUREACT_INF_LIST");
			sQuery = String.format(sQuery, timeFrom, timeTo);
			//logger.info(String.format(":::::::::: sQuery SELECT_JOB_BIZ_LOTFUTUREACT_INF_LIST : %s", sQuery));    		
			jobBizLotfutureactInfList = factory.selectList(sQuery);	        	
	        	        
	        // 4		
	        sQuery = XmlUtil.loadQuery(xmlPath , "SELECT_JOB_MES_OPER_MAS_LIST");
	        sQuery = String.format(sQuery, facId, timeFrom, timeTo);
	        //logger.info(String.format(":::::::::: sQuery SELECT_JOB_MES_OPER_MAS_LIST : %s", sQuery));
			jobMesOperMasList = factory.selectList(sQuery);	        
	        
	        // 5
	        sQuery = XmlUtil.loadQuery(xmlPath , "SELECT_JOB_MES_LOT_MAS_LIST");
	        sQuery = String.format(sQuery, timeFrom, timeTo, "%"+facId+"%");
	        //logger.info(String.format(":::::::::: sQuery SELECT_JOB_MES_LOT_MAS_LIST : %s", sQuery));    		
	        jobMesLotMasList = factory.selectList(sQuery);	        
	        
	        // 6
	        sQuery = XmlUtil.loadQuery(xmlPath , "SELECT_JOB_SFAB_LOTMOVE_MAS_LIST");
	        sQuery = String.format(sQuery, timeFrom, timeTo);	        
	        //logger.info(String.format(":::::::::: sQuery SELECT_JOB_SFAB_LOTMOVE_MAS_LIST : %s", sQuery));    		
	        jobSFabLotMoveMasList = factory.selectList(sQuery);	        
		}
		catch(Exception ex)
		{
			logger.error(":::::::::: setJobSubList error", ex);	
		}
		finally {
			factory.close();
		}
    }
    
	// next공정 가져오기 로직
	private List<Map<String, Object>> getOperList(String facId, String timeFrom, String timeTo, String lotId, String flowId, String operId)
	{		
    	// 1. jobOperList에서 현재 Lot에 flowId와 동일한 공정수순 가져오기
    	List<Map<String, Object>> operList = (jobOperList != null) 
        ? jobOperList.stream()
            .filter(_item -> {
                Object _flowId = _item.get("FLOW_ID");
                return _flowId != null && flowId.equals(_flowId.toString());
            })
            .collect(Collectors.toList())
        : List.of();
    	if(operList.size() == 0) return operList;
    	
    	// 2.1 jobMesNodeMasList에서  현재 Lot에 flowId,operId가 동일한 row 가져오기 
    	Optional<Map<String, Object>> nodeItemOpt = (jobMesNodeMasList != null) 
        ? jobMesNodeMasList.stream()
            .filter(_item -> {
                Object _flowId = _item.get("FLOW_ID");
                Object _operId = _item.get("OPER_ID");
                return _flowId != null && _operId != null && flowId.equals(_flowId.toString()) && operId.equals(_operId.toString());
            })
            .findFirst()
        : Optional.empty();    	
    	// 2.2 jobOperList에서 위 row에 oper_seq보다 큰 데이타만 가져오기
    	if (!nodeItemOpt.isPresent()) {    		
    		info(facId, timeFrom, timeTo, String.format(":::::::::: getOperList > nodeItemOpt is empty. lotId:%s, flowId:%s, operId:%s", lotId, flowId, operId), false);
    		return new ArrayList<Map<String, Object>>();
    	}
    	Map<String, Object> nodeItem = nodeItemOpt.get();
		
		// 기준 행의 OPER_SEQ 추출
	    Object baseSeqObj = nodeItem.get("OPER_SEQ");
	    int baseSeq = (baseSeqObj != null) ? Integer.parseInt(baseSeqObj.toString()) : -1;
	    // 추출한 OPER_SEQ보다 큰것만 대상
	    operList = operList.stream()
            .filter(_item -> {
                Object _seqObj = _item.get("OPER_SEQ");
                if (_seqObj == null) return false;
                
                int _seq = Integer.parseInt(_seqObj.toString());
                return _seq > baseSeq;
            })
            .collect(Collectors.toList());
	    
	    if(operList.size() == 0) {
	    	info(facId, timeFrom, timeTo, String.format(":::::::::: getOperList > operList.size is 0. baseSeq:%s", baseSeq), false);
	    	return operList;
	    }
    	
    	// 3. operList에서 IS_STOP_POINT=1인 row중 가장 작은 oper_seq 가져오기        	    	
    	OptionalInt minSeqOpt = operList.stream()
		        // 1. 필터: IS_POINT 가 "1"인 행만 선택
		        .filter(row -> {
		            Object isPointObj = row.get("IS_STOP_POINT");
		            return isPointObj != null && "1".equals(isPointObj.toString());
		        })
		        // 2. 필터: OPER_SEQ 가 null 이 아닌 행만 선택 (안전장치)
		        .filter(row -> row.get("OPER_SEQ") != null)
		        // 3. 변환: OPER_SEQ 를 int 로 변환
		        .mapToInt(row -> Integer.parseInt(row.get("OPER_SEQ").toString()))
		        // 4. 연산: 최솟값 찾기
		        .min();
    	int minSeq = minSeqOpt.isEmpty() ? -1:minSeqOpt.getAsInt();
        // 4. operList에서 IS_STOP_POINT=1인 row중 가장 작은 oper_seq 가져오기        	  
    	operList = operList.stream()
                .filter(_item -> {
                	Integer _seq = Integer.parseInt(_item.get("OPER_SEQ").toString());
                	// 2026-04-27 
                	// PROCESS 공정이 없어서 공정 리스트 조회 못하는 문제, 조회조건 수정
                	// T.OPER_SEQ <= F.LIMIT_SEQ	=> (( F.LIMIT_SEQ IS NULL )) OR T.OPER_SEQ <= F.LIMIT_SEQ;
                    return minSeq==-1 || _seq <= minSeq;
                })
                .collect(Collectors.toList());
    	
        return operList;
	}

	private Boolean isReturnOper(String facId, String timeFrom, String timeTo, String lotId, String operId) {		
		// 해당 Lot이 백업 Lot
		long cnt = jobMesLotMasList.stream()
	            .filter(_row -> {
	                String _lotId = String.valueOf(_row.get("LOT_ID"));

	                return _lotId.equals(lotId);
	            }).count();

        if (cnt == 0) {
        	info(facId, timeFrom, timeTo, String.format(":::::::::: isReturnOper jobMesLotMasList lotId:%s"
    				, lotId
    				, operId)
        			, false);
        	return false;
        }
        
        // 해당 공정이 Return 공정
        cnt = jobSFabLotMoveMasList.stream()
	            .filter(_row -> {
	                String _lotId = String.valueOf(_row.get("LOT_ID"));
	                String _returnOperId = String.valueOf(_row.get("RETURN_OPER_ID"));

	                return _lotId.equals(lotId) && _returnOperId.equals(operId);
	            }).count();
     
        info(facId, timeFrom, timeTo, String.format(":::::::::: isReturnOper jobSFabLotMoveMasList lotId:%s, operId:%s, result:%s"
				, lotId
				, operId
				, cnt > 0 ? "Y":"N")
        		, false);
        
        return cnt > 0;
	}
	
	private Boolean isSetUpSetMo(String facId, String timeFrom, String timeTo, String lotId, String flowId, String operId) 
	{		
		if (jobBizLotfutureactInfList == null || jobBizLotfutureactInfList.isEmpty()) 
			return false;

		long cnt = jobBizLotfutureactInfList.stream()
	            .filter(_row -> {
	                // 1. 키가 존재하지 않으면 false
	                if (!_row.containsKey("ACT_FLOW_ID") || !_row.containsKey("ACT_OPER_ID") || !_row.containsKey("LOT_ID")) {
	                    return false;
	                }

	                String _flowId = String.valueOf(_row.get("ACT_FLOW_ID"));
	                String _operId = String.valueOf(_row.get("ACT_OPER_ID"));
	                String _lotId = String.valueOf(_row.get("LOT_ID"));

	                return _flowId.equals(flowId) && _operId.equals(operId) && _lotId.equals(lotId);
	            }).count();

		info(facId, timeFrom, timeTo, String.format(":::::::::: isSetUpSetMo lotId:%s, flowId:%s, operId:%s, result:%s"
				, lotId
				, flowId
				, operId
				, cnt > 0 ? "Y":"N")
				, false);
		
        return cnt > 0;
	}
	
	private Boolean isN2PurgeOper(String facId, String timeFrom, String timeTo, String lotId, String curOperId, String nextOperId) {
		if (jobMesOperMasList == null || jobMesOperMasList.isEmpty()) 
			return false;
		
		String curMidOperTyp = jobMesOperMasList.stream()
					            .filter(_row -> {
					                // 1. 키가 존재하지 않으면 false
					                if (!_row.containsKey("OPER_ID") || !_row.containsKey("MID_OPER_TYP")) {
					                    return false;
					                }
				
					                String _operId = String.valueOf(_row.get("OPER_ID"));
					                return _operId.equals(curOperId);
					            })
					            .map(_row -> String.valueOf(_row.get("MID_OPER_TYP")))
					            .findFirst()
					            .orElse("");
		
		String nextMidOperTyp = jobMesOperMasList.stream()
					            .filter(_row -> {
					                // 1. 키가 존재하지 않으면 false
					                if (!_row.containsKey("OPER_ID") || !_row.containsKey("MID_OPER_TYP")) {
					                    return false;
					                }
				
					                String _operId = String.valueOf(_row.get("OPER_ID"));
					                return _operId.equals(nextOperId);
					            })
					            .map(_row -> String.valueOf(_row.get("MID_OPER_TYP")))
					            .findFirst()
					            .orElse("");
		
		info(facId, timeFrom, timeTo, String.format(":::::::::: isN2PurgeOper lotId:%s, curOperId:%s, curMidOperTyp:%s, nextOperId:%s, nextMidOperTyp:%s, result:%s"
				, lotId
				, curOperId
				, curMidOperTyp
				, nextOperId
				, nextMidOperTyp
				, !curMidOperTyp.equalsIgnoreCase("N2Purge") && nextMidOperTyp.equalsIgnoreCase("N2Purge") ? "Y":"N")
				, false);
		
        return !curMidOperTyp.equalsIgnoreCase("N2Purge") && nextMidOperTyp.equalsIgnoreCase("N2Purge");
	}
    
	private void insertLotProctimeInftoLogpresso(List<Map<String, Object>> list) {    	
		List<Tuple> logpressoData = new ArrayList<>();
		
		for (Map<String, Object> item : list) {
			Tuple tuple = new Tuple();
			tuple.put("LOT_ID", item.get("LOT_ID"));
			tuple.put("EQP_ID", item.get("EQP_ID"));
			tuple.put("EQP_RECIPE_ID", item.get("EQP_RECIPE_ID"));
			tuple.put("OPER_ID", item.get("OPER_ID"));			
			tuple.put("TIMEKEY", item.get("TIMEKEY").toString());			
			tuple.put("FAC_ID", item.get("FAC_ID"));	
			tuple.put("SECTION_NM", item.get("SECTION_NM"));
			tuple.put("FLOW_ID", item.get("FLOW_ID"));
			tuple.put("AVG_VAL_1", item.get("AVG_VAL_1") == null ? "":item.get("AVG_VAL_1").toString());
			tuple.put("START_TM", item.get("START_TM"));
			tuple.put("PREDICT_END_TM", item.get("PREDICT_END_TM") == null ? "":item.get("PREDICT_END_TM"));
			tuple.put("NEXT_OPER", item.get("NEXT_OPER"));
			tuple.put("NEXT_STEP", item.get("NEXT_STEP"));
			
			logpressoData.add(tuple);
		}
	
		if(logpressoData.size() > 0)
			Util.insertInLogpressoDatabase(logpressoData, "ATLAS_LOTPROCTIME_INF", this.getClass().getSimpleName());
	}
	
	private void insertLogsToLogpresso(String facId, String fromTimekey, String toTimekey,
										Map<String, List<Map<String, Object>>> operListMapLog,										
										List<Map<String, Object>> jobBizLotfutureactInfLog,
										List<Map<String, Object>> jobMesOperMasLog,
										List<Map<String, Object>> jobMesLotMasLog, 
										List<Map<String, Object>> jobSFabLotMoveMasLog) {
		List<Tuple> tuples = new ArrayList<>();

		//
        for (Map.Entry<String, List<Map<String, Object>>> entry : operListMapLog.entrySet()) {
        	String[] parts = entry.getKey().split("#");
            var lotId = parts[0];
            var timekey = parts[1];
            
            for (Map<String, Object> _oper : entry.getValue()) {
            	Tuple tuple = new Tuple();
            	tuple.put("FAC_ID", facId);
            	tuple.put("FROM_TIMEKEY", fromTimekey);
    			tuple.put("TO_TIMEKEY", toTimekey);
    			tuple.put("LOT_ID", lotId);
    			tuple.put("TIMEKEY", timekey.toString());
    			tuple.put("FLOW_ID", _oper.get("FLOW_ID"));
    			tuple.put("OPER_SEQ", _oper.get("OPER_SEQ") == null ? "":_oper.get("OPER_SEQ").toString());
    			tuple.put("OPER_ID", _oper.get("OPER_ID"));			
    			tuple.put("MID_OPER_TYP", _oper.get("MID_OPER_TYP"));
    			tuple.put("IS_STOP_POINT", _oper.get("IS_STOP_POINT") == null ? "":_oper.get("IS_STOP_POINT").toString());
    			tuples.add(tuple);
            }            
        }
        if(tuples.size() > 0)
        {
        	Util.insertInLogpressoDatabase(tuples, "ATLAS_LOTPROCTIME_OPER_LOG", this.getClass().getSimpleName());
        }
        
        // 
        tuples = new ArrayList<>();
        for (Map<String, Object> item : jobBizLotfutureactInfLog) {
			Tuple tuple = new Tuple();
			tuple.put("FAC_ID", facId);
			tuple.put("FROM_TIMEKEY", fromTimekey);
			tuple.put("TO_TIMEKEY", toTimekey);
			tuple.put("ACT_FLOW_ID", item.get("ACT_FLOW_ID"));
			tuple.put("ACT_OPER_ID", item.get("ACT_OPER_ID"));
			tuple.put("LOT_ID", item.get("LOT_ID"));
			tuple.put("ACT_NM", item.get("ACT_NM"));
						
			tuples.add(tuple);
		}	
		if(tuples.size() > 0)
		{
			Util.insertInLogpressoDatabase(tuples, "ATLAS_BIZ_LOT_FUTURE_ACT_INF_LOG", this.getClass().getSimpleName());
		}
		
		//
		tuples = new ArrayList<>();
        for (Map<String, Object> item : jobMesOperMasLog) {
			Tuple tuple = new Tuple();
			tuple.put("FAC_ID", facId);
			tuple.put("FROM_TIMEKEY", fromTimekey);
			tuple.put("TO_TIMEKEY", toTimekey);
			tuple.put("OPER_ID", item.get("OPER_ID"));
			tuple.put("MID_OPER_TYP", item.get("MID_OPER_TYP"));
			tuple.put("OPER_VER", item.get("OPER_VER"));
			
			tuples.add(tuple);
		}	
		if(tuples.size() > 0)
		{
			Util.insertInLogpressoDatabase(tuples, "ATLAS_MES_OPER_MAS_LOG", this.getClass().getSimpleName());
		}
		        
        //
        tuples = new ArrayList<>();
        for (Map<String, Object> item : jobMesLotMasLog) {
			Tuple tuple = new Tuple();
			tuple.put("FAC_ID", facId);
			tuple.put("FROM_TIMEKEY", fromTimekey);
			tuple.put("TO_TIMEKEY", toTimekey);
			tuple.put("LOT_ID", item.get("LOT_ID"));	
			
			tuples.add(tuple);
		}	
		if(tuples.size() > 0)
		{
			Util.insertInLogpressoDatabase(tuples, "ATLAS_LOTPROCTIME_MES_LOT_MAS_LOG", this.getClass().getSimpleName());
		}
		 
		//
		tuples = new ArrayList<>();	
		for (Map<String, Object> item : jobSFabLotMoveMasLog) {
			Tuple tuple = new Tuple();
			tuple.put("FAC_ID", facId);
			tuple.put("FROM_TIMEKEY", fromTimekey);
			tuple.put("TO_TIMEKEY", toTimekey);
			tuple.put("LOT_ID", item.get("LOT_ID"));
			tuple.put("RETURN_OPER_ID", item.get("RETURN_OPER_ID"));
			
			tuples.add(tuple);
		}	
		if(tuples.size() > 0)
		{
			Util.insertInLogpressoDatabase(tuples, "ATLAS_LOTPROCTIME_SFAB_LOT_MOVE_MAS_LOG", this.getClass().getSimpleName());
		}		
	}
	    
	private void insertfabTransQueueToLogresso()
	{
        List<Tuple> tplList = new ArrayList<>();
        fabTransQueue.forEach(task -> tplList.add(JsonUtil.getTupleByJsonElement(JsonUtil.toJsonTree(task))));
        if(tplList.size() > 0)
			Util.insertInLogpressoDatabase(tplList, "ATLAS_LOTPROCTIME_FAB_TRANS", this.getClass().getSimpleName());
	}
	
	private void insertFloorTransQueueToLogresso() 
	{
		List<Tuple> tplList = new ArrayList<>();
		floorTransQueue.forEach(task -> tplList.add(JsonUtil.getTupleByJsonElement(JsonUtil.toJsonTree(task))));
		if(tplList.size() > 0)
			Util.insertInLogpressoDatabase(tplList, "ATLAS_LOTPROCTIME_FLOOR_TRANS", this.getClass().getSimpleName());
	}
    
	private void info(String facId, String timeFrom, String timeTo, String msg, boolean isLast)
    {
//    	logger.info("Fac ID {}, Period {} ~ {}, Message: {}", facId, timeFrom, timeTo, msg);
    	
    	Tuple tuple = new Tuple();
    	tuple.put("FAC_ID", facId);
    	tuple.put("FROM_TIMEKEY", timeFrom);
		tuple.put("TO_TIMEKEY", timeTo);
		tuple.put("MESSAGE", msg);		
		tplList.add(tuple);
    	
		if(isLast || tplList.size() > 200)
		{
			LogpressoAPI.setInsertTuples("ATLAS_LOTPROCTIME_INFO_LOG", tplList, 100);	
			tplList.clear(); 
		}
    }
}