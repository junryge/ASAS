package com.skhynix.supply.secs.service.impl;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;

import javax.annotation.Resource;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.stereotype.Service;

import com.skhynix.supply.common.Common;
import com.skhynix.supply.common.MachineVo;
import com.skhynix.supply.secs.dao.EiDAO;
import com.skhynix.supply.secs.service.EiService;
import com.skhynix.supply.secs.vo.EiVo;

@Service("eiService")
public class EiServiceImpl implements EiService{
	protected Log log = LogFactory.getLog(EiServiceImpl.class);
	
	@Resource(name="eiDAO")
	EiDAO Client;
	
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2020. 3. 25. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 : EI_CS_DS 로그 조회
	 * @return
	 * @throws Exception
	 */
	
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(EiVo eiVo) throws Exception {
		List<Map> dataList = null; 
		long offset 	= (Long.parseLong(eiVo.getPageNum()) - 1) * Long.parseLong(eiVo.getRowNum());
		int   limit 	= Integer.parseInt(eiVo.getRowNum());
		String resultQuery = getQueryParser(eiVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			resultQuery += Common.sPipeLine + "limit " + offset + " " +  limit;		//결과 출력에 대해 limit을 적용한 쿼리 
			resultQuery += Common.sPipeLine + Common.sSort + Common.s_TIME;			//결과 출력에 대해 time sort를 적용한 쿼리
			resultQuery += String.format(Common.sEval, "No", "seq()") + Common.sPlus + offset;
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(eiVo.getFabSite(), resultQuery);
		}
		return dataList;
	}
	
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 8. 16. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 : Query 생성
	 * @return
	 * @throws Exception
	 */
	private String getQueryParser(EiVo eiVo) {
		if (eiVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();
		/*sQuery.append(String.format(Common.sTable_From, secsVo.getFrom(), secsVo.getTo(),
				Common.sOrder+ Common.sEqual_1+Common.sAsc+Common.sSpace
				+Common.sSECS_DATA));*/
		sQuery.append(String.format(Common.sTable_From, eiVo.getFrom(), eiVo.getTo(), 
				Common.sOrder+ Common.sEqual_1+Common.sAsc + Common.sParallel + Common.sSpace));	// 200918 hgJeon 병렬화 옵션 적용
		
		// 190107 FAB 선택시 테이블 쿼리 변경
		if ((eiVo.getFab()!=null && eiVo.getFab().size() > 0) 
			&& (eiVo.getLog()!=null && eiVo.getLog().size() > 0)){
			List<String> fab = eiVo.getFab();
			List<String> logType = eiVo.getLog();		// ts, ei, cs, ds
			List<String> tableName = null;
			LinkedHashSet<String> tableNameSet = new LinkedHashSet<String>();
			
			log.info("fab:"+eiVo.getFab());
			
			for(int i=0;i<eiVo.getFab().size();i++){
				tableName = new ArrayList<String>();
//				if(fab.get(i).contains("FAB_B")) {
//					//fabName = Common.sSECS_DATA_2;
//					tableName = eiVo.getLevel().contains(Common.sALL) || eiVo.getLevel().contains("INFO") 
//							|| eiVo.getLevel().contains("FINE") || eiVo.getLevel().contains("DEBUG") ?
//							getTableSelect("B", logType, true) : getTableSelect("B", logType, false);
//				}else if (fab.get(i).contains("FAB_A")) {
//					//fabName = Common.sSECS_DATA;
//					tableName = eiVo.getLevel().contains(Common.sALL) || eiVo.getLevel().contains("INFO") 
//							|| eiVo.getLevel().contains("FINE") || eiVo.getLevel().contains("DEBUG") ?
//							getTableSelect("A", logType, true) : getTableSelect("A", logType, false);
//				}else if (fab.get(i).contains("FAB_C")) {
//					tableName = eiVo.getLevel().contains(Common.sALL) || eiVo.getLevel().contains("INFO") 
//							|| eiVo.getLevel().contains("FINE") || eiVo.getLevel().contains("DEBUG") ?
//							getTableSelect("C", logType, true) : getTableSelect("C", logType, false);
//				}
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//tableName = eiVo.getLevel().contains(Common.sALL) || eiVo.getLevel().contains("INFO") || eiVo.getLevel().contains("FINE") || eiVo.getLevel().contains("DEBUG") ? 
				//				getTableSelect(fab.get(i), logType, true): getTableSelect(fab.get(i), logType, false); 
				tableName = eiVo.getLevel().contains(Common.sALL) || eiVo.getLevel().contains("INFO") || eiVo.getLevel().contains("FINE") || eiVo.getLevel().contains("DEBUG") ? 
						getTableSelect(eiVo.getFabSite(), fab.get(i), logType, true): getTableSelect(eiVo.getFabSite(), fab.get(i), logType, false);
				// 중복제거
				tableNameSet.addAll(tableName);
			}	// end of for
			
			tableName = new ArrayList<>(tableNameSet);
			sQuery.append(String.join(", ", tableName));
		}
		// 컬럼 설정 (CLASS, FAB, LOG, HOST, TEXT_XML)
		if(eiVo.getLog() != null && eiVo.getLog().contains("TS")) {	// 200921 hgJeon TS 조건 추가
			log.info("logType:"+eiVo.getLog().toString());
			
			sQuery.append(Common.sCRLF + String.format(Common.sEval, "CLASS", "OPERATION_NAME"));
			sQuery.append(Common.sCRLF + Common.sPipeLine + "eval FAB = case(contains(PROCESS, " 
								+ Common.sDoubleQuotation + "m11a" + Common.sDoubleQuotation + " ), " + Common.sDoubleQuotation + "M11A"+ Common.sDoubleQuotation 
								+ ", contains(PROCESS, " + Common.sDoubleQuotation + "m11b" + Common.sDoubleQuotation+ "), " + Common.sDoubleQuotation + "M11B" + Common.sDoubleQuotation
								+ ", contains(PROCESS, " + Common.sDoubleQuotation + "m14a" + Common.sDoubleQuotation+ "), " + Common.sDoubleQuotation + "M14A" + Common.sDoubleQuotation
								+ ", contains(PROCESS, " + Common.sDoubleQuotation + "m14b" + Common.sDoubleQuotation+ "), " + Common.sDoubleQuotation + "M14B" + Common.sDoubleQuotation
								+ ", contains(PROCESS, " + Common.sDoubleQuotation + "m15" + Common.sDoubleQuotation+ "), " + Common.sDoubleQuotation + "M15" + Common.sDoubleQuotation
								+ ", contains(PROCESS, " + Common.sDoubleQuotation + "m16a" + Common.sDoubleQuotation+ "), " + Common.sDoubleQuotation + "M16A" + Common.sDoubleQuotation
								+ ", contains(PROCESS, " + Common.sDoubleQuotation + "m16b" + Common.sDoubleQuotation+ "), " + Common.sDoubleQuotation + "M16B" + Common.sDoubleQuotation
								+ ", contains(PROCESS, " + Common.sDoubleQuotation + "c2" + Common.sDoubleQuotation+ "), " + Common.sDoubleQuotation + "C2" + Common.sDoubleQuotation
								+ ", contains(PROCESS, " + Common.sDoubleQuotation + "c2f" + Common.sDoubleQuotation+ "), " + Common.sDoubleQuotation + "C2F" + Common.sDoubleQuotation
								+ ")");
			sQuery.append(Common.sCRLF + Common.sPipeLine + "eval LOG = case(contains(PROCESS, " + Common.sDoubleQuotation + "ts" 
								+ Common.sDoubleQuotation + "), " + Common.sDoubleQuotation + "TS"+ Common.sDoubleQuotation+ ")");
			sQuery.append(Common.sCRLF + Common.sPipeLine + "eval HOST = if(contains(PROCESS, "+ Common.sDoubleQuotation + "ts0"+ Common.sDoubleQuotation 
								+"), "+ Common.sDoubleQuotation + "primary" + Common.sDoubleQuotation + ", "+ Common.sDoubleQuotation 
								+ "secondary" + Common.sDoubleQuotation + ")");
			sQuery.append(Common.sCRLF + String.format(Common.sEval, "TEXT_XML", "XML"));
		}
		
		// 200921 hgJeon fields 정렬 순서조정 ( 맨뒤 -> 앞 )
		sQuery.append(Common.sCRLF + Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX 
				+ Common.sComma + "FAB" + Common.sComma + "LOG" + Common.sComma + Common.sLEVEL
				+ Common.sComma + "THREAD" + Common.sComma + "CLASS" + Common.sComma + Common.sTEXT 
				+ Common.sComma + "HOST" + Common.sComma + Common.sPROCESS + Common.sComma + "TEXT_XML"
				);
		
		// Add Search filed Fab
		if(eiVo.getLog().contains("EI") || eiVo.getLog().contains("CS") || eiVo.getLog().contains("DS")) {
			StringBuilder sFab = new StringBuilder();
			sFab.append(Common.sCRLF + String.format(Common.sSearch_in, "FAB"));
			
			for (int i=0; i<eiVo.getFab().size(); i++) {
//				if(eiVo.getFab().get(i).equals(Common.sFAB_A)) {
//					sFab.append(Common.sComma + Common.sDoubleQuotation + Common.sFAB_M14A + Common.sDoubleQuotation);
//				}else if (eiVo.getFab().get(i).equals(Common.sFAB_B)) {
//					sFab.append(Common.sComma + Common.sDoubleQuotation + Common.sFAB_M14B + Common.sDoubleQuotation);
//				}else if (eiVo.getFab().get(i).equals(Common.sFAB_C)) {
//					sFab.append(Common.sComma + Common.sDoubleQuotation + Common.sFAB_M16 + Common.sDoubleQuotation);
//				}		
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//sFab.append(Common.getColumnFromFab(Common.sFAB_SITE, eiVo.getFab().get(i)));
				sFab.append(Common.getColumnFromFab(eiVo.getFabSite(), eiVo.getFab().get(i)));
			}
			
			sFab.append(" )");
			sQuery.append(sFab.toString());
		}
		
		// 5.Add LEVEL
		if (eiVo.getLevel()!=null && eiVo.getLevel().size() > 0) {
			StringBuilder sLevel = new StringBuilder();
			sLevel.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sLEVEL));
			/*log.info("level1:"+sLevel);*/
			for (String s : eiVo.getLevel()) {
				if (s.indexOf(Common.sALL) >= 0) {	// level 이 ALL 일때 
					/*sLevel.append(Common.sComma + Common.sDoubleQuotation + "WELL" + Common.sDoubleQuotation
							+Common.sComma + Common.sDoubleQuotation + "WARN" + Common.sDoubleQuotation
							+Common.sComma + Common.sDoubleQuotation + "ERROR" + Common.sDoubleQuotation
							+Common.sComma + Common.sDoubleQuotation + "FATAL" + Common.sDoubleQuotation
							+Common.sComma + Common.sDoubleQuotation + "DEBUG" + Common.sDoubleQuotation
							+Common.sComma + Common.sDoubleQuotation + "INFO" + Common.sDoubleQuotation
							+Common.sComma + Common.sDoubleQuotation + "FINE" + Common.sDoubleQuotation);*/
					sLevel = new StringBuilder();
					break;
				} else {
					sLevel.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
				}
			}

			if (sLevel != null || !(sLevel.toString().isEmpty())) {
				/*log.info("level2:"+sLevel);*/
				if (sLevel.toString().indexOf("(") >= 0) {
					sLevel.append(" )");
				} // search in ( ... )
				sQuery.append(sLevel.toString());
			}
		}
		
		// 6.Condition & Filter --> AND , OR
		// 6-1
		if (eiVo.getHost()!=null && eiVo.getHost().size() > 0) {
			StringBuilder sHost = new StringBuilder();
			sHost.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sHOST));
			
			for (String s : eiVo.getHost()) {
				sHost.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
			}

			if (sHost != null || !(sHost.toString().isEmpty())) {
				/*log.info("level2:"+sLevel);*/
				if (sHost.toString().indexOf("(") >= 0) {
					sHost.append(" )");
				} // search in ( ... )
				sQuery.append(sHost.toString());
			}
		}
		
		if (eiVo.getProcess() != null && !eiVo.getProcess().trim().equals("")) {
			// 200304 hgJeon "," 추가시 multi 검색조건 검색 가능하게	
			if(eiVo.getProcess().contains(Common.sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] textNameArray = eiVo.getProcess().split(Common.sCommaOrigin);
				for(int i=0;i<textNameArray.length;i++){
					if(i==0){
						tempQuery.append(
						Common.sLeftParenthesis + Common.sLeftParenthesis
						+ Common.sPROCESS + Common.sEquals
						+ Common.sDoubleQuotation +Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis 
						);
					}else if(i==(textNameArray.length-1)){
						tempQuery.append(
						 Common.sOr + Common.sLeftParenthesis
						+ Common.sPROCESS + Common.sEquals
						+ Common.sDoubleQuotation +Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis
						);
					}else{
						tempQuery.append(
						 Common.sOr + Common.sLeftParenthesis
						+ Common.sPROCESS + Common.sEquals
						+ Common.sDoubleQuotation +Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis
						);
					}
				}sQuery.append(Common.sCRLF + Common.sSearch_0 + tempQuery.toString());
			}else {
				sQuery.append(Common.sCRLF + Common.sSearch_0
						+ Common.sPROCESS + Common.sEquals
						+ Common.sDoubleQuotation + eiVo.getProcess().trim() + Common.sDoubleQuotation);
			}
		}

		
		// 200304 hgJeon "," 추가시 multi 검색조건 검색 가능하게
		if (eiVo.getText() != null && !eiVo.getText().trim().equals("")) {
			
			if(eiVo.getText().toString().contains(Common.sAsterisk)) {		// 201223 hgJeon text 검색 시 * 문자 제외
				eiVo.setText(eiVo.getText().replaceAll("\\*", Common.sEmpty));
			}
			
			if(eiVo.getText().contains(Common.sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] textNameArray = eiVo.getText().split(Common.sCommaOrigin);
				String condition = Common.sOr;
				// 200305 hgJeon TEXT 검색 시 and, or 조건 검색 기능추가
				if(eiVo.getEiTextConditionCheckBox() != null && !(eiVo.getEiTextConditionCheckBox().isEmpty())) {
					condition = eiVo.getEiTextConditionCheckBox().trim().equals(Common.sOr.trim()) ? Common.sOr : Common.sAnd;
				}
				
				for(int i=0;i<textNameArray.length;i++){
					if(i==0){
						tempQuery.append(
						Common.sLeftParenthesis + Common.sLeftParenthesis
						+ Common.sTEXT + Common.sEquals
						+ Common.sDoubleQuotation +Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis 
						);
					}else if(i==(textNameArray.length-1)){
						tempQuery.append(
						condition + Common.sLeftParenthesis
						+ Common.sTEXT + Common.sEquals
						+ Common.sDoubleQuotation +Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis
						);
					}else{
						tempQuery.append(
						condition + Common.sLeftParenthesis
						+ Common.sTEXT + Common.sEquals
						+ Common.sDoubleQuotation +Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis
						);
					}
				}
				sQuery.append(Common.sCRLF + Common.sSearch_0 + tempQuery.toString());
			}else {
				sQuery.append(Common.sCRLF + Common.sSearch_0
						+ Common.sTEXT + Common.sEquals 
						+ Common.sDoubleQuotation +Common.sAsterisk + eiVo.getText().trim() + Common.sAsterisk
						+ Common.sDoubleQuotation );
			}
		}
		
		return sQuery.toString();
	}
	
	private List<String> getTableSelect(String fabSite, String fab, List<String>LogType, boolean isAll) {	
		
		List<String> tableName = new ArrayList<String>();
		
		for (String log : LogType) {		// ei, cs, ds
			switch(log) {
				case "TS" :
				{
					tableName.add(getTSTableFromFab(fabSite, fab, isAll));
				}
				break;
				case "EI" : 
				{
					tableName.add(getEITableFromFab(fabSite, fab));
				}
				break;
				case "CS" :
				{
					tableName.add(getCSTableFromFab(fabSite, fab));
				}
				break;
				case "DS" :
				{
					tableName.add(getDSTableFromFab(fabSite, fab));
				}
				break;
				default : break;
			}
		}
		return tableName;
	}
	
	private String getTSTableFromFab(String fabSite, String fab, boolean isAll) {
		
		switch(fabSite) {
			case Common.sFABSITE_M14 : {
				return isAll ? Common.sTS_DATA_M14A + "," + Common.sTS_DATA_M14B : Common.sTS_DATA_VIEW_M14A + "," + Common.sTS_DATA_VIEW_M14B;
			}
			case Common.sFABSITE_M15 : {
				if(fab.equals(Common.sFAB_M15A)) {
					return isAll ? Common.sTS_DATA_M15A : Common.sTS_DATA_VIEW_M15A;
				}else { // B 일경우 
					return isAll ? Common.sTS_DATA_M15B : Common.sTS_DATA_VIEW_M15B;
				}
			}
			case Common.sFABSITE_M11 : {
				if(fab.equals(Common.sFAB_M11A)) {
					return isAll ? Common.sTS_DATA_M11A : Common.sTS_DATA_VIEW_M11A;
				}else { // B 일경우 
					return isAll ? Common.sTS_DATA_M11B : Common.sTS_DATA_VIEW_M11B;
				}
			}
			case Common.sFABSITE_C2 : {
				if(fab.equals(Common.sFAB_C2)) {
					return isAll ?  Common.sTS_DATA_C2 : Common.sTS_DATA_VIEW_C2;
				}else { // B 일경우 
					return isAll ? Common.sTS_DATA_C2F : Common.sTS_DATA_VIEW_C2F;
				}
			}
			case Common.sFABSITE_IC : {
				if(fab.equals(Common.sFAB_M14A)) {
					return isAll ? Common.sTS_DATA_M14A : Common.sTS_DATA_VIEW_M14A;
				}else if(fab.equals(Common.sFAB_M14B)) {
					return isAll ? Common.sTS_DATA_M14B : Common.sTS_DATA_VIEW_M14B;
				}else if(fab.equals(Common.sFAB_M16A)) {
					return isAll ? Common.sTS_DATA_M16A : Common.sTS_DATA_VIEW_M16A; 
				}else if(fab.equals(Common.sFAB_M16B)) {
					return isAll ? Common.sTS_DATA_M16B : Common.sTS_DATA_VIEW_M16B; 
				}
			}
			default : return Common.sEmpty;
		}
	}
	
	private String getEITableFromFab(String fabSite, String fab) {
		
		switch(fabSite) {
			case Common.sFABSITE_M14 : {
				return Common.sEI_DATA;
			}
			case Common.sFABSITE_M15 : {
				if(fab.equals(Common.sFAB_M15A)) {
					return Common.sEI_DATA_M15A;
				}else { // B 일경우
					return Common.sEI_DATA_M15B;
				}
			}
			case Common.sFABSITE_M11 : {
				if(fab.equals(Common.sFAB_M11A)) {
					return Common.sEI_DATA_M11A;
				}else { // B 일경우
					return Common.sEI_DATA_M11B;
				}
			}
			case Common.sFABSITE_C2 : {
				if(fab.equals(Common.sFAB_C2)) {
					return Common.sEI_DATA_C2;
				}else { // B 일경우
					return Common.sEI_DATA_C2F;
				}
			}
			case Common.sFABSITE_IC : {
				if(fab.equals(Common.sFAB_M14A)) {
					return Common.sEI_DATA;
				}else if(fab.equals(Common.sFAB_M16A)) {
					return Common.sEI_DATA_M16A;
				}else if(fab.equals(Common.sFAB_M16B)) {
					return Common.sEI_DATA_M16B;
				}
			}
			default : return Common.sEmpty;
		}
	}
	
	private String getCSTableFromFab(String fabSite, String fab) {
				
		switch(fabSite) {
			case Common.sFABSITE_M14 : {
				return Common.sCS_DATA;
			}
			case Common.sFABSITE_M15 : {
				if(fab.equals(Common.sFAB_M15A)) {
					return Common.sCS_DATA_M15A;
				}else { // B 일경우
					return Common.sCS_DATA_M15B;
				}
			}
			case Common.sFABSITE_M11 : {
				if(fab.equals(Common.sFAB_M11A)) {
					return Common.sCS_DATA_M11A;
				}else { // B 일경우
					return Common.sCS_DATA_M11B;
				}
			}
			case Common.sFABSITE_C2 : {
				if(fab.equals(Common.sFAB_C2)) {
					return Common.sCS_DATA_C2;
				}else { // B 일경우
					return Common.sCS_DATA_C2F;
				}
			}
			case Common.sFABSITE_IC : {
				if(fab.equals(Common.sFAB_M14A)) {
					return Common.sCS_DATA;
				}else if(fab.equals(Common.sFAB_M16A)) {
					return Common.sCS_DATA_M16A;
				}else if(fab.equals(Common.sFAB_M16B)) {
					return Common.sCS_DATA_M16B;
				}
			}
			default : return Common.sEmpty;
		}
	}

	private String getDSTableFromFab(String fabSite, String fab) {
		
		switch(fabSite) {
			case Common.sFABSITE_M14 : {
				return Common.sDS_DATA;
			}
			case Common.sFABSITE_M15 : {
				if(fab.equals(Common.sFAB_M15A)) {
					return Common.sDS_DATA_M15A;
				}else { // B 일경우
					return Common.sDS_DATA_M15B;
				}
			}
			case Common.sFABSITE_M11 : {
				if(fab.equals(Common.sFAB_M11A)) {
					return Common.sDS_DATA_M11A;
				}else { // B 일경우
					return Common.sDS_DATA_M11B;
				}
			}			
			case Common.sFABSITE_C2 : {
				if(fab.equals(Common.sFAB_C2)) {
					return Common.sDS_DATA_C2;
				}else { // B 일경우
					return Common.sDS_DATA_C2F;
				}
			}
			case Common.sFABSITE_IC : {
				if(fab.equals(Common.sFAB_M14A)) {
					return Common.sDS_DATA;
				}else if(fab.equals(Common.sFAB_M16A)) {
					return Common.sDS_DATA_M16A;
				}else if(fab.equals(Common.sFAB_M16B)) {
					return Common.sDS_DATA_M16B;
				}
			}
			default : return Common.sEmpty;
		}
	}

	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getProcessList(String fabSite) throws Exception {	// 200921 hgJeon 최초 loading 시 ts 검색
		List<Map> processList = null;
		//String processQuery = "memlookup name=ProcessList | sort PROCESS | search PROCESS =="
		String processQuery = "memlookup name=ProcessList2 | sort PROCESS | search PROCESS =="
		+ Common.sDoubleQuotation + "ts" + Common.sAsterisk + Common.sDoubleQuotation
		+ " | stats count by PROCESS | fields PROCESS";
		
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		processList = Client.dbExecuteQuery(fabSite, processQuery);
		
		return processList;
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getSelectProcessList(MachineVo machineVo) throws Exception {
		if (machineVo == null) {
			return null;
		} // null exception
		List<Map> selectList = null;
		
		String resultQuery = getSelectProcessQuery(machineVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			selectList = Client.dbExecuteQuery(machineVo.getFabSite(), resultQuery);
		}
		return selectList;
	}
	
	private String getSelectProcessQuery(MachineVo machineVo) {
		StringBuilder sQuery = new StringBuilder();
		//String ProcessQuery = "memlookup name=ProcessList | sort PROCESS";
		String ProcessQuery = "memlookup name=ProcessList2 | sort PROCESS";
		sQuery.append(ProcessQuery);

		if(machineVo.getSelectType()!=null && machineVo.getSelectType().size() > 0) {
			StringBuilder sLogType = new StringBuilder();
			sLogType.append(Common.sCRLF + String.format(Common.sSearch_in, "PROCESS"));

			for (String s : machineVo.getSelectType()) {
				if (s.indexOf(Common.sALL) >= 0) {
					sLogType = null;
					break;
				} else {
					sLogType.append(Common.sComma + Common.sDoubleQuotation + s.toLowerCase() + Common.sAsterisk + Common.sDoubleQuotation);
				}
			}

			if (sLogType != null && !(sLogType.toString().isEmpty())) {
				if (sLogType.toString().indexOf("(") >= 0) {
					sLogType.append(" )");
				} // search in ( ... )
				sQuery.append(sLogType.toString());
			}
		}
		
		// Type
		if (machineVo.getSelectFab()!=null && machineVo.getSelectFab().size() > 0) {
			StringBuilder sFabType = new StringBuilder();
			sFabType.append(Common.sCRLF + String.format(Common.sSearch_in, "FAB"));

			for (String s : machineVo.getSelectFab()) {
				if (s.indexOf(Common.sALL) >= 0) {
					sFabType = null;
					break;
				} else {
					
					sFabType.append(Common.sComma + Common.sDoubleQuotation + s.toUpperCase() + Common.sAsterisk + Common.sDoubleQuotation);					
//					String fabName = Common.getFabABC("ei", Common.sFAB_SITE, s.toUpperCase());
//					if(!fabName.isEmpty())
//						sFabType.append(Common.sComma + Common.sDoubleQuotation + fabName + Common.sAsterisk + Common.sDoubleQuotation);
				}
			}

			if (sFabType != null && !(sFabType.toString().isEmpty())) {
				if (sFabType.toString().indexOf("(") >= 0) {
					sFabType.append(" )");
				} // search in ( ... )
				sQuery.append(sFabType.toString());
			}
		}
		
		sQuery.append(" | stats count by PROCESS | fields PROCESS");
		
		return sQuery.toString();
	}

	// 201106 hgJeon 쿼리 Cancel 추가
	@Override
	public void getRawLogQueryStop() throws Exception {
		try {
			Client.dbExecuteQueryStop();
		} catch (Exception e) {
			log.info("getRawLogQueryStop Exception!!");
		}
	}

}
