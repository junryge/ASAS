package com.skhynix.smartatlas.batch;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import org.apache.commons.lang3.StringUtils;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.util.FilePathUtil;
import com.skhynix.smartatlas.util.Util;
import com.skhynix.smartatlas.util.XmlUtil;
import com.skhynix.smartfx.dataaccessfx.QueryExecutor;
import com.skhynix.smartfx.dataaccessfx.QueryExecutorFactory;

public class AmosBoundryBatch implements Job{
    private final Logger logger     = LoggerFactory.getLogger(getClass());
    private static final int DELAYED_TIME  = 1000 * 60;
    private static final DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMddHHmm00");
    private static final String FILE_PATH_STAR_IDC = FilePathUtil.PYTHON_FILE_PATH + "/star_idc/";
    private static final String FILE_NAME_STAR_IDC = "data/star_standardmodel_m41a_data_longterm_test%s.csv";
    private final List<String> starIdcNmList = new ArrayList<String>();
    private final List<String> tsM14IdcNmList = new ArrayList<String>();
    private final List<String> bridgeLayoutIdcNmList = new ArrayList<String>();
       
    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
    	if (!Util.isCurrentIC()) return;
    	
    	logger.info("... `{}` has started`", this.getClass().getName());

        long timer = System.currentTimeMillis();

        this._run();

        long checkTimer = System.currentTimeMillis() - timer;

        if (checkTimer >= DELAYED_TIME) {
            logger.error("... !!!DELAYED!!! `{}` has finished [elapsed time: {}m ({}ms)]", this.getClass().getSimpleName(), checkTimer / (60 * 1000), checkTimer);
        } else {
            logger.info("... `{}` has finished [elapsed time: {}ms]", this.getClass().getSimpleName(), checkTimer);
        }
    }
    
    private void _run() {
    	LocalDateTime now = LocalDateTime.now();
    	
        LocalDateTime timeFrom = now.minusDays(7);
        LocalDateTime timeTo = now;
        
//        timeFrom = LocalDateTime.of(2026, 4, 27, 0, 0, 0);
//        timeTo = LocalDateTime.of(2026, 4, 27, 23, 59, 59);
        
        // 지표 리스트 세팅
        setIdcNm();
 		        
        // M14/M16
        _run_star_idc(timeFrom, timeTo);        
	}

    private void setIdcNm()
    {
    	// star - 102
    	starIdcNmList.add("M16HUB.QUE.M16TOM14B.CURRENTQCREATED");
    	starIdcNmList.add("M16HUB.QUE.M14BTOM16.CURRENTQCREATED");
    	starIdcNmList.add("M16HUB.QUE.M14TOM16.CURRENTQCREATED");
    	starIdcNmList.add("M16HUB.QUE.M16TOM14.CURRENTQCREATED");
    	starIdcNmList.add("M16HUB.QUE.M14TOM16.MESCURRENTQCNT");
    	starIdcNmList.add("M16HUB.QUE.M16TOM14.MESCURRENTQCNT");
    	starIdcNmList.add("M16HUB.QUE.M16TOM14A.MESCURRENTQCNT");
    	starIdcNmList.add("M16HUB.QUE.M16TOM14B.MESCURRENTQCNT");
    	starIdcNmList.add("M16HUB.QUE.ALL.M16HUBTOM14MANUAL_CURRENTQCNT");
    	starIdcNmList.add("M14.QUE.OHT.CURRENTRETICLEOHTQCNT");
    	starIdcNmList.add("M14.QUE.SENDFAB.VERTICALQUEUECOUNT");
    	starIdcNmList.add("M14.QUE.SENDFAB.CURRENTSENDFABCOMPLETED");
    	starIdcNmList.add("M14.QUE.OHT.OHTUTIL");
    	starIdcNmList.add("M14.QUE.LOAD.CURRENTLOADQCNT");
    	starIdcNmList.add("M14.QUE.ALL.CURRENTQCNT");
    	starIdcNmList.add("M14.QUE.ALL.CURRENTQCOMPLETED");
    	starIdcNmList.add("M14.QUE.ALL.CURRENTQCREATED");
    	starIdcNmList.add("M14.QUE.LOAD.AVGLOADTIME");
    	starIdcNmList.add("M14.QUE.OHT.RTCOHTUTIL");
    	starIdcNmList.add("M14.QUE.ALL.TRANSPORT4MINOVERCNT");
    	starIdcNmList.add("M14.QUE.ALL.TRANSPORT4MINOVERTIMEAVG");
    	starIdcNmList.add("M14.QUE.ALL.TRANSPORT4MINOVERRATIO");
    	starIdcNmList.add("M14.QUE.CNV.M14ATOM16ACURRNETQCNT");
    	starIdcNmList.add("M14.QUE.CNV.ALLTONORTHCNVCURRENTQCNT");
    	starIdcNmList.add("M14.QUE.CNV.ALLTOSOUTHCNVCURRENTQCNT");
    	starIdcNmList.add("M14.QUE.LOAD.AVGRETICLELOADTIME");
    	starIdcNmList.add("M14.QUE.LOAD.AVGLOADTIME1MIN");
    	starIdcNmList.add("M14.QUE.OHT.CURRENTOHTQCNT");
    	starIdcNmList.add("M14.QUE.LOAD.AVGFOUPLOADTIME");
    	starIdcNmList.add("M14.QUE.ALL.CURRENTRETICLEQCNT");
    	starIdcNmList.add("M14.QUE.LOAD.CURRENTRETICLELOADQCNT");
    	starIdcNmList.add("M14.QUE.STK.MANUALOUTCOUNT");
    	starIdcNmList.add("M14.QUE.CNV.NORTHCNVTOALLCURRENTQCNT");
    	starIdcNmList.add("M14.QUE.CNV.SOUTHCNVTOALLCURRENTQCNT");
    	starIdcNmList.add("M14.QUE.ALL.TOTALCNVCURRENTQCNT");
    	starIdcNmList.add("M14.QUE.ALL.M14ATOM10ACURRENTQCNT");
    	starIdcNmList.add("M14.QUE.ALL.M14ATOM10CCURRENTQCNT");
    	starIdcNmList.add("M14.QUE.CNV.NORTHM14TOCNVTIME");
    	starIdcNmList.add("M14.QUE.CNV.SOUTHM14TOCNVTIME");
    	starIdcNmList.add("M14.QUE.SFAB.SENDTOR3");
    	starIdcNmList.add("M14.QUE.SFAB.SENDTOM16");
    	starIdcNmList.add("M14.QUE.SFAB.SENDTOM10");
    	starIdcNmList.add("M14.QUE.SFAB.SENDQUEUETOTAL");
    	starIdcNmList.add("M14.QUE.SFAB.RECEIVETOR3");
    	starIdcNmList.add("M14.QUE.SFAB.RECEIVETOM16");
    	starIdcNmList.add("M14.QUE.SFAB.RECEIVETOM10");
    	starIdcNmList.add("M14.QUE.SFAB.RECEIVEQUEUETOTAL");
    	starIdcNmList.add("M14.QUE.SFAB.RETURNTOR3");
    	starIdcNmList.add("M14.QUE.SFAB.RETURNTOM16");
    	starIdcNmList.add("M14.QUE.SFAB.RETURNTOM10");
    	starIdcNmList.add("M14.QUE.SFAB.RETURNQUEUETOTAL");
    	starIdcNmList.add("M14.QUE.SFAB.COMPLETETOR3");
    	starIdcNmList.add("M14.QUE.SFAB.COMPLETETOM16");
    	starIdcNmList.add("M14.QUE.SFAB.COMPLETETOM10");
    	starIdcNmList.add("M14.QUE.SFAB.COMPLETEQUEUETOTAL");
    	starIdcNmList.add("M14.QUE.CNV.NORTHCNVTOM14TIME");
    	starIdcNmList.add("M14.QUE.CNV.SOUTHCNVTOM14TIME");
    	starIdcNmList.add("M14.QUE.CNV.NORTHM14TOCNVTIME1MIN");
    	starIdcNmList.add("M14.QUE.CNV.SOUTHM14TOCNVTIME1MIN");
    	starIdcNmList.add("M14.QUE.CNV.NORTHCNVTOM14TIME1MIN");
    	starIdcNmList.add("M14.QUE.CNV.SOUTHCNVTOM14TIME1MIN");
    	starIdcNmList.add("M14.QUE.CNV.NORTHCURRENTQCNT");
    	starIdcNmList.add("M14.QUE.CNV.SOUTHCURRENTQCNT");
    	starIdcNmList.add("M14.QUE.ALL.M14ATOM16MANUAL_CURRENTQCNT");
    	starIdcNmList.add("M14B.QUE.LOAD.CURRENTRETICLELOADQCNT");
    	starIdcNmList.add("M14B.QUE.SENDFAB.VERTICALQUEUECOUNT");
    	starIdcNmList.add("M14B.QUE.SENDFAB.CURRENTSENDFABCOMPLETED");
    	starIdcNmList.add("M14B.QUE.OHT.RTCOHTUTIL");
    	starIdcNmList.add("M14B.QUE.LFT.ALLTOLFTCURRENTQCNT");
    	starIdcNmList.add("M14B.QUE.LFT.LFTTOALLCURRENTQCNT");
    	starIdcNmList.add("M14B.QUE.LOAD.CURRENTLOADQCNT");
    	starIdcNmList.add("M14B.QUE.ALL.CURRENTQCNT");
    	starIdcNmList.add("M14B.QUE.ALL.CURRENTQCOMPLETED");
    	starIdcNmList.add("M14B.QUE.ALL.CURRENTQCREATED");
    	starIdcNmList.add("M14B.QUE.LOAD.AVGLOADTIME");
    	starIdcNmList.add("M14B.QUE.OHT.OHTUTIL");
    	starIdcNmList.add("M14B.QUE.OHT.CURRENTRETICLEOHTQCNT");
    	starIdcNmList.add("M14B.QUE.LOAD.AVGRETICLELOADTIME");
    	starIdcNmList.add("M14B.QUE.LOAD.AVGLOADTIME1MIN");
    	starIdcNmList.add("M14B.QUE.OHT.CURRENTOHTQCNT");
    	starIdcNmList.add("M14B.QUE.LOAD.AVGFOUPLOADTIME");
    	starIdcNmList.add("M14B.QUE.ALL.CURRENTRETICLEQCNT");
    	starIdcNmList.add("M14B.QUE.STK.MANUALOUTCOUNT");
    	starIdcNmList.add("M14B.QUE.LFT.M14BTOM16ACURRNETQCNT");
    	starIdcNmList.add("M14B.QUE.ALL.M14BTOM10ACURRENTQCNT");
    	starIdcNmList.add("M14B.QUE.ALL.M14BTOM16CURRENTQCNT");
    	starIdcNmList.add("M14B.QUE.ALL.FABOUTCURRENTQCNT");
    	starIdcNmList.add("M16.QUE.SFAB.SENDTOM14");
    	starIdcNmList.add("M16.QUE.SFAB.RECEIVETOM14");
    	starIdcNmList.add("M16.QUE.SFAB.RETURNTOM14");
    	starIdcNmList.add("M16.QUE.SFAB.COMPLETETOM14");
    	starIdcNmList.add("M16A.QUE.CNV.M16ATOM14ACURRNETQCNT");
    	starIdcNmList.add("M16A.QUE.CNV.M16ATOM14BCURRNETQCNT");
    	starIdcNmList.add("M16E.QUE.ALL.M16ETOM14BCURRENTQCNT");
    	starIdcNmList.add("M16E.QUE.ALL.M14ATOM16ECURRENTQCNT");
    	starIdcNmList.add("M16E.QUE.ALL.M14BTOM16ECURRENTQCNT");
    	starIdcNmList.add("M16E.QUE.ALL.M16ETOM14ACURRENTQCNT");
    	starIdcNmList.add("M14.STRATE.STB.STORAGERATIO");
    	starIdcNmList.add("M14.STRATE.N2.STORAGERATIO");
    	//starIdcNmList.add("M14.SORTER.ABN.SORTERTRANSFERFAIL");
    	starIdcNmList.add("M14.SORTER.ABN.SORTERWAITCOUNTOVER");
    	starIdcNmList.add("M14.SORTER.ABN.CUSORTERWAITCOUNTOVER");
    	
    	
    	// tsM14 - 11
    	//tsM14IdcNmList.add("CURRTIME");
    	tsM14IdcNmList.add("TOTALCNT");
    	tsM14IdcNmList.add("M14AM10A");
    	tsM14IdcNmList.add("M10AM14A");
    	tsM14IdcNmList.add("M14AM10ASUM");
    	tsM14IdcNmList.add("M14AM14B");
    	tsM14IdcNmList.add("M14BM14A");
    	tsM14IdcNmList.add("M14AM14BSUM");
    	tsM14IdcNmList.add("M14AM16");
    	tsM14IdcNmList.add("M16M14A");
    	tsM14IdcNmList.add("M14AM16SUM");
    	
    	
    	// bridgeLayout - 2
    	bridgeLayoutIdcNmList.add("M14.PDT.LAYOUT.HUBROOM_M14TOM16_CURRENTQCNT");
    	bridgeLayoutIdcNmList.add("M14.PDT.LAYOUT.M14A_M14ATOM14ACNV_CURRENTQCNT");    	
    }
    
    
    // ==================================================
    // STAR IDC
    // ==================================================
    private void _run_star_idc(LocalDateTime timeFrom, LocalDateTime timeTo)
    {
    	// STAR
		String filePath = _create_star_idc_input_data(timeFrom, timeTo);
		File file = new File(filePath);
		
		if (file.exists()) {
			this._predictor_star_idc_data();
		} else {
			logger.error("... csv file that input data of atlas hid prediction is not exist [directory: {}]", filePath);
		}
    }

    private String _create_star_idc_input_data(LocalDateTime timeFrom, LocalDateTime timeTo)
    {
    	String filePath = FILE_PATH_STAR_IDC + String.format(FILE_NAME_STAR_IDC, "");
    	
    	try
        {
        	StringBuilder sbCsv = new StringBuilder();
        	sbCsv.append("EVENT_DT");
        	for (int i = 0; i < starIdcNmList.size(); i++) {        		
        		sbCsv.append("," + starIdcNmList.get(i));
        	}
        	for (int i = 0; i < tsM14IdcNmList.size(); i++) {        		
        		sbCsv.append("," + tsM14IdcNmList.get(i));
        	}
        	for (int i = 0; i < bridgeLayoutIdcNmList.size(); i++) {        		
        		sbCsv.append("," + bridgeLayoutIdcNmList.get(i));
        	}
        	sbCsv.append(System.lineSeparator()); 
        	
        	List<Map<String,Object>> starList = getAwsIdcDataHis(timeFrom, timeTo);
        	List<Map<String,Object>> tsM14List = getTsCurrentJobOfM14List(timeFrom, timeTo);
        	List<Map<String,Object>> bridgeLayoutList = getbridgeLayoutList(timeFrom, timeTo);
        	        	
//        	String str = inoutList.stream()
//        		    .map(Map::toString)
//        		    .collect(Collectors.joining(", "));
//        	logger.info("inoutList: {}", str);
        		
        	// 시작 시간부터 종료 시간까지 반복 (종료 시간 미포함)
        	for (LocalDateTime current = timeFrom; current.isBefore(timeTo); current = current.plusMinutes(1))
            {
                String _key = current.format(formatter);	//yyyyMMddHHmm00
                
                DateTimeFormatter formatter2 = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:00");
                String _key2 = current.format(formatter2);
                
                // 1. EVENT_DT
                sbCsv.append(_key);                
                
                // 2. starList
                sbCsv.append(",");
                Optional<Map<String, Object>> _optMap = starList.stream()
                        .filter(_row -> {
                        	String _eventDt = _row.get("EVENT_DT").toString();
                            return _eventDt != null && _eventDt.equals(_key2);                            
                        }).findFirst();
                
                
                if (_optMap.isPresent()) {    		
                	Map<String, Object> _item = _optMap.get();
                	
                    StringBuilder _sb = new StringBuilder();       
                    for (int i = 0; i < starIdcNmList.size(); i++) {                    	
                    	if (i > 0) {
                        	_sb.append(",");
                        }
                    	
                    	Object _value = _item.get(commaToUnderbar(starIdcNmList.get(i)));
                        if (_value != null) {
                        	_sb.append(_value.toString());
                        }
                        else {
                        	_sb.append("");
                        }
                	}
                    sbCsv.append(_sb.toString());
            	}
                else
                {
                	StringBuilder _sb = new StringBuilder(); 
                	for (int i = 0; i < starIdcNmList.size(); i++) {
                		if (i > 0) {
                        	_sb.append(",");
                        }
                		_sb.append("");
                	}
                	sbCsv.append(_sb.toString());
                }
                
                // 3. tsM14List
                sbCsv.append(",");
                _optMap = tsM14List.stream()
                        .filter(_row -> {
                        	String _eventDt = _row.get("EVENT_DT").toString();
                            return _eventDt != null && _eventDt.equals(_key);                            
                        }).findFirst();
                
                if (_optMap.isPresent()) {    		
                	Map<String, Object> _item = _optMap.get();
                	
                    StringBuilder _sb = new StringBuilder();       
                    for (int i = 0; i < tsM14IdcNmList.size(); i++) {                    	
                    	if (i > 0) {
                        	_sb.append(",");
                        }
                    	
                    	Object _value = _item.get(commaToUnderbar(tsM14IdcNmList.get(i)));
                        if (_value != null) {
                        	_sb.append(_value.toString());
                        }
                        else {
                        	_sb.append("");
                        }
                	}
                    sbCsv.append(_sb.toString());
            	}
                else
                {
                	StringBuilder _sb = new StringBuilder(); 
                	for (int i = 0; i < tsM14IdcNmList.size(); i++) {
                		if (i > 0) {
                        	_sb.append(",");
                        }
                		_sb.append("");
                	}
                	sbCsv.append(_sb.toString());
                }
                
                // 4. bridgeLayoutList
                sbCsv.append(",");
                _optMap = bridgeLayoutList.stream()
                        .filter(_row -> {
                        	String _eventDt = _row.get("EVENT_DT").toString();
                            return _eventDt != null && _eventDt.equals(_key);                            
                        }).findFirst();
                
                if (_optMap.isPresent()) {    		
                	Map<String, Object> _item = _optMap.get();
                	
                    StringBuilder _sb = new StringBuilder();       
                    for (int i = 0; i < bridgeLayoutIdcNmList.size(); i++) {                    	
                    	if (i > 0) {
                        	_sb.append(",");
                        }
                    	
                    	Object _value = _item.get(commaToUnderbar(bridgeLayoutIdcNmList.get(i)));
                        if (_value != null) {
                        	_sb.append(_value.toString());
                        }
                        else {
                        	_sb.append("");
                        }
                	}
                    sbCsv.append(_sb.toString());
            	}
                else
                {
                	StringBuilder _sb = new StringBuilder(); 
                	for (int i = 0; i < bridgeLayoutIdcNmList.size(); i++) {
                		if (i > 0) {
                        	_sb.append(",");
                        }
                		_sb.append("");
                	}
                	sbCsv.append(_sb.toString());
                }
                
                // 5. 줄바꿈
                sbCsv.append(System.lineSeparator()); 
            }
            //info("star", timeFrom, timeTo, sbCsv.toString());
            
            // csv 파일 생성
            try {	            
	 			File file = new File(filePath);
	 			if (file.exists()) {
	 				file.delete();
	 			}
	 			FileWriter fileWriter = new FileWriter(filePath);
	 			fileWriter.write(sbCsv.toString());
	 			fileWriter.flush();
	             
	        } catch (IOException e) {
	             // 파일 쓰기 중 오류 발생 시 처리
	             System.err.println("파일 쓰기 중 오류가 발생했습니다.");
	             e.printStackTrace();
	        }
        	
        } catch (Exception e) {
            logger.error("", e);
        }
        finally {
        }
    	
    	return filePath;
    }

    private List<Map<String, Object>> getAwsIdcDataHis(LocalDateTime timeFrom, LocalDateTime timeTo) {
		QueryExecutor factory = null;
		
		List<Map<String, Object>> list = new ArrayList<>();
		
		try
		{
			//STAR DB
			factory = QueryExecutorFactory.getQueryExecutor("sfx2");
			
			StringBuilder sb = new StringBuilder();
	  		sb.append("SELECT TO_CHAR(CRT_TM, 'YYYY-MM-DD HH24:MI:SS') EVENT_DT ");	  		
	  		for(String idsNm : starIdcNmList)
	  		{
	  			sb.append(String.format(" , MAX(CASE WHEN IDC_NM = '%s' THEN IDC_VAL END) AS \"%s\" ", idsNm, commaToUnderbar(idsNm)));	
	  		}
	  		sb.append(" FROM STAADM.aws_idc_data_his ");	  		
	  		sb.append(" WHERE TO_CHAR(CRT_TM, 'SS') = '00' ");	  		
	  		sb.append(String.format("  AND CRT_TM >= TO_DATE('%s', 'YYYYMMDDHH24MISS')  ", timeFrom.format(formatter)));
	  		sb.append(String.format("  AND CRT_TM <  TO_DATE('%s', 'YYYYMMDDHH24MISS')   ", timeTo.format(formatter)));	  		
	  		sb.append("  AND IDC_NM IN ( ");	  		
  			for(int i=0;i<starIdcNmList.size();i++)
	  		{
  				if(i>0)
	  			{
	  				sb.append(",");	
	  			}
  				String idsNm = starIdcNmList.get(i);
	  			sb.append(String.format("'%s'",idsNm));
	  		}
	  		sb.append("  )  ");
	  		sb.append("GROUP BY CRT_TM ");
	  		sb.append("ORDER BY CRT_TM ");    		
	  		logger.info("getAwsIdcDataHis query: {}", sb.toString());
    		list = factory.selectList(sb.toString());
		}
		catch(Exception ex)
		{
			logger.error("", ex);	
		}
		finally {
			factory.close();
		}
		
		return list;
    }

    private List<Map<String, Object>> getTsCurrentJobOfM14List(LocalDateTime timeFrom, LocalDateTime timeTo) {
    	List<Map<String, Object>> result = new ArrayList<>();
        
        try {
        	String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "tsCurrentJobOfM14List");
        	strQuery = String.format(strQuery, timeFrom.format(formatter), timeTo.format(formatter));
        	logger.info("getTsCurrentJobOfM14List query: {}", strQuery);
        	result = LogpressoAPI.responseResult(strQuery);
        }catch (Exception e) {
            logger.error("getLotProcTimeInf error",e);
        }
        return result;
    }

    private List<Map<String, Object>> getbridgeLayoutList(LocalDateTime timeFrom, LocalDateTime timeTo) {
    	List<Map<String, Object>> result = new ArrayList<>();
    	if (bridgeLayoutIdcNmList.size() == 0) return result;
                  
        try {        	
        	String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "bridgeLayoutList");
        	
        	StringBuilder sb1 = new StringBuilder();
        	StringBuilder sb2 = new StringBuilder();
        	StringBuilder sb3 = new StringBuilder();
        	for(String idsNm : bridgeLayoutIdcNmList)
	  		{
        		sb1.append(String.format(", \"%s\"", idsNm));
        		sb2.append(String.format(" | eval %s=%s", commaToUnderbar(idsNm), idsNm));
        		sb3.append(String.format(" ,%s", commaToUnderbar(idsNm)));
	  		}
        	strQuery = String.format(strQuery, timeFrom.format(formatter), timeTo.format(formatter), sb1.toString(), sb2.toString(), sb3.toString());
        	logger.info("getbridgeLayoutList query: {}", strQuery);
        	result = LogpressoAPI.responseResult(strQuery);
        }catch (Exception e) {
            logger.error("getLotProcTimeInf error",e);
        }
        return result;
    }

    private void _predictor_star_idc_data() { 
    	logger.info("[PREDICT] calculating star idc data prediction has started");

    	// 1. features_data: 저장안함 
    	// 2. anomaly_data: 
//		List<Map<String, Object>> features_data = new ArrayList<>();
		List<Map<String, Object>> anomaly_data 	= new ArrayList<>();
		Process process                     	= null;
        ArrayList<String> command           	= new ArrayList<>();
		Boolean stderrFlag 						= false;		
		long timer 								= System.currentTimeMillis();
		String pyFileName						= "boundary_batch.py";

		try {
			File workingDir = new File(FILE_PATH_STAR_IDC);

			command.add("python");
			command.add(pyFileName);

			ProcessBuilder processBuilder = new ProcessBuilder(command);

			// ★ 핵심: Python 이 실행될 작업 디렉토리 설정
			// 이 설정이 없으면 Java 프로젝트 루트에서 실행되어 app 모듈을 못 찾습니다.
			processBuilder.directory(workingDir);
			
			// 표준 출력 및 오류 스트림 상속 (콘솔에서 로그 확인용)
	        //processBuilder.inheritIO();
	        
	        processBuilder.redirectErrorStream(stderrFlag);

	        process = processBuilder.start();

            int exitCode = process.waitFor();
            if (exitCode != 0) {
                logger.error("[{}] Python process exited with error code: {}", pyFileName, exitCode);
                // 오류 스트림 읽기 (파이썬 에러 메시지 확인용)
                try (BufferedReader errorReader = new BufferedReader(new InputStreamReader(process.getErrorStream(), "UTF-8"))) {
                    String errorLine;
                    StringBuilder errorOutput = new StringBuilder();
                    while ((errorLine = errorReader.readLine()) != null) {
                        errorOutput.append(errorLine).append("\n");
                    }
                    logger.error("[{}] Python Error Stream: {}", pyFileName, errorOutput.toString());
                }
            }            
            logger.info("[{}] process exited with code: {}", pyFileName, exitCode);
		
		} catch (Exception e) {
            logger.error("",e);
        } finally {
            if (process != null) {
                process.destroy();
            }
        }
    }
    
    // ==================================================
    private String commaToUnderbar(String str)
    {
    	if(StringUtils.isEmpty(str)) return "";
    		
		return str.replace(".", "_");
    }

}