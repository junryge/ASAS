package com.skhynix.supply.alarm.service.impl;

import java.util.List;
import java.util.Map;

import javax.annotation.Resource;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.stereotype.Service;

import com.skhynix.supply.alarm.service.AlarmReportService;
import com.skhynix.supply.alarm.vo.AlarmReportVo;
import com.skhynix.supply.common.Common;
import com.skhynix.supply.tot.dao.TotalDAO;

@Service("alarmReportService")
public class AlarmReportServiceImpl implements AlarmReportService {
	protected Log log = LogFactory.getLog(AlarmReportServiceImpl.class);
	@Resource(name = "totalDAO")
	TotalDAO Client;
	
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(AlarmReportVo alarmReportVo) throws Exception {
		List<Map> dataList = null; 
		long offset 	= (Long.parseLong(alarmReportVo.getPageNum()) - 1) * Long.parseLong(alarmReportVo.getRowNum());
		int   limit 	= Integer.parseInt(alarmReportVo.getRowNum());
		String resultQuery = getQueryParser(alarmReportVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			resultQuery += Common.sPipeLine + "limit " + offset + " " +  limit;	//결과 출력에 대해 limit을 적용한 쿼리 
			resultQuery += Common.sPipeLine + Common.sSort + Common.s_TIME;			//결과 출력에 대해 time sort를 적용한 쿼리
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(alarmReportVo.getFabSite(), resultQuery);
		}
		return dataList;
	}

	
	public String getQueryParser(AlarmReportVo alarmReportVo) {
		if (alarmReportVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(Common.sFulltext_Arg0_key1, 
				alarmReportVo.getFrom(), alarmReportVo.getTo(),
				(Common.sLeftParenthesis + Common.sMETHOD + Common.sEquals 
				+ Common.sDoubleQuotation + "createAlarmReportHistory" + Common.sDoubleQuotation 
				+ Common.sRightParenthesis)));

		// Condition & Filter --> AND , OR
		// sUNIT
		if (alarmReportVo.getUnit() != null && !alarmReportVo.getUnit().equals("")) {
			if(alarmReportVo.getUnit().contains(Common.sUnderbar)){
				StringBuilder tmpQuery = new StringBuilder();
				String[] unitNameArray = alarmReportVo.getUnit().split(Common.sUnderbar);
				for(int i=0;i<unitNameArray.length;i++){
					if(i==0){
						tmpQuery.append(
								Common.sCRLF + Common.sLeftParenthesis
								+ Common.sLeftParenthesis + Common.sUNIT + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}else if(i==(unitNameArray.length-1)){
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sUNIT + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sRightParenthesis );
					}else{
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sUNIT + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}
				}
				sQuery.append(Common.sCRLF + Common.sAnd + tmpQuery.toString());
			}else if(!alarmReportVo.getUnit().contains(Common.sUnderbar)&&alarmReportVo.getUnit().contains(Common.sMinus)){
				StringBuilder tmpQuery = new StringBuilder();
				String[] unitNameArray = alarmReportVo.getUnit().split(Common.sMinus);
				for(int i=0;i<unitNameArray.length;i++){
					if(i==0){
						tmpQuery.append(
								Common.sCRLF + Common.sLeftParenthesis
								+ Common.sLeftParenthesis + Common.sUNIT + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}else if(i==(unitNameArray.length-1)){
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sUNIT + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sRightParenthesis );
					}else{
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sUNIT + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}
				}
				sQuery.append(Common.sCRLF + Common.sAnd +tmpQuery.toString());
			}else{
				sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
						+ Common.sUNIT + Common.sEquals 
						+ Common.sDoubleQuotation + alarmReportVo.getUnit()
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}
		// sALARMID
		if (alarmReportVo.getAlarmId() != null && !alarmReportVo.getAlarmId().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sALARMID + Common.sEquals
					+ Common.sDoubleQuotation + alarmReportVo.getAlarmId()
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// sALARMCODE
		if (alarmReportVo.getAlarmCode() != null && !alarmReportVo.getAlarmCode().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sALARMCODE + Common.sEquals
					+ Common.sDoubleQuotation + alarmReportVo.getAlarmCode() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// sALARMTEXT
		if (alarmReportVo.getAlarmText() != null && !alarmReportVo.getAlarmText().equals("")) {
			if(alarmReportVo.getAlarmText().contains(Common.sSpace) || 
					alarmReportVo.getAlarmText().contains(Common.sLeftParenthesis)
				||	alarmReportVo.getAlarmText().contains(Common.sRightParenthesis)
				||	alarmReportVo.getAlarmText().contains(Common.sSlash)
				||	alarmReportVo.getAlarmText().contains(Common.sMinus)
				||	alarmReportVo.getAlarmText().contains(Common.sUnderbar)){
				StringBuilder tmpQuery = new StringBuilder();
				String alarmText = alarmReportVo.getAlarmText();
				alarmText = alarmText.replaceAll("-", " ");
				alarmText = alarmText.replaceAll("_", " ");
				alarmText = alarmText.replaceAll("/", " ");
				alarmText = alarmText.replaceAll("\\(", " ");
				alarmText = alarmText.replaceAll("\\)", " ");
				System.out.println("alarmText : " + alarmText);
				String[] alarmTextArray = alarmText.split(Common.sSpace);
				for(int i=0;i<alarmTextArray.length;i++){
					if(!alarmTextArray[i].equals("")){
						if(i==0){
							tmpQuery.append(
									Common.sCRLF + Common.sLeftParenthesis
									+ Common.sLeftParenthesis + Common.sALARMTEXT + Common.sEquals
									+ Common.sDoubleQuotation + alarmTextArray[i]
											+ Common.sDoubleQuotation 
											+ Common.sRightParenthesis + Common.sAnd);
						}else if(i==(alarmTextArray.length-1)){
							tmpQuery.append(
									Common.sLeftParenthesis
									+ Common.sALARMTEXT + Common.sEquals
									+ Common.sDoubleQuotation + alarmTextArray[i]
											+ Common.sDoubleQuotation 
											+ Common.sRightParenthesis + Common.sRightParenthesis );
						}else{
							tmpQuery.append(
									Common.sLeftParenthesis
									+ Common.sALARMTEXT + Common.sEquals
									+ Common.sDoubleQuotation + alarmTextArray[i]
											+ Common.sDoubleQuotation 
											+ Common.sRightParenthesis + Common.sAnd);
						}
					}
				}
				sQuery.append(Common.sCRLF + Common.sAnd +tmpQuery.toString());
			}else{
				sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
						+ Common.sALARMTEXT + Common.sEquals
						+ Common.sDoubleQuotation + alarmReportVo.getAlarmText() 
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}
		// sSTATE
		if (alarmReportVo.getState() != null && !alarmReportVo.getState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sSTATE + Common.sEquals
					+ Common.sDoubleQuotation + alarmReportVo.getState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		
		// sAREANAME
		if (alarmReportVo.getAreaName()!=null && alarmReportVo.getAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + alarmReportVo.getAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 

		// sBAYNAME
		if (alarmReportVo.getBayName()!=null && alarmReportVo.getBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + alarmReportVo.getBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// 2021.03.22	X0122410 : 기존 검색조건이 잘못 연결되어 있었음, TYPE > MACHINETYPE으로 변경 
		// sTYPE
		/*
		if (alarmReportVo.getMachineType()!=null && alarmReportVo.getMachineType().size() > 0) {
			List<String> typeList = alarmReportVo.getMachineType();
			sQuery.append(Common.sCRLF + Common.sAnd);
			for (int i=0;i<typeList.size();i++) {
				if (typeList.get(i).indexOf(Common.sNOTDESIGNATED) >= 0) {
					break;
				}
				
				if(i==0) {
					sQuery.append(Common.sLeftParenthesis +
						Common.sTYPE + Common.sEquals +
						Common.sDoubleQuotation + typeList.get(i)+ Common.sDoubleQuotation);
				}else{
					sQuery.append(Common.sOr +
						Common.sTYPE + Common.sEquals +
						Common.sDoubleQuotation + typeList.get(i)+ Common.sDoubleQuotation);
				}
			}
			sQuery.append(Common.sRightParenthesis);
		}
		*/
		// MACHINETYPE		
		StringBuilder subMachineTypeQuery = new StringBuilder();
		if (alarmReportVo.getMachineType()!=null && alarmReportVo.getMachineType().size() > 0) {			
			subMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sMACHINETYPE));
			for (String s : alarmReportVo.getMachineType()) {
				if (s.indexOf(Common.sALL) >= 0) {	
					subMachineTypeQuery = new StringBuilder();
					break;
				} else {
					subMachineTypeQuery.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
				}
			}

			if (subMachineTypeQuery != null || !(subMachineTypeQuery.toString().isEmpty())) {
				if (subMachineTypeQuery.toString().indexOf("(") >= 0) {
					subMachineTypeQuery.append(" )");
				}				
			}
		}
		
		// sMACHINENAME
		if (alarmReportVo.getMachineName()!=null && alarmReportVo.getMachineName().size() > 0) {
			List<String> machineList = alarmReportVo.getMachineName();
			sQuery.append(Common.sAnd);
			for (int i=0;i<machineList.size();i++) {
				if (machineList.get(i).indexOf(Common.sNOTDESIGNATED) >= 0) {
					break;
				} 
				if(i==0) {
					sQuery.append(Common.sLeftParenthesis +
						Common.sMACHINENAME + Common.sEquals +
						Common.sDoubleQuotation + machineList.get(i)+ Common.sDoubleQuotation);
				}else{
					sQuery.append(Common.sOr +
						Common.sMACHINENAME + Common.sEquals +
						Common.sDoubleQuotation + machineList.get(i)+ Common.sDoubleQuotation);
				}
			}
			sQuery.append(Common.sRightParenthesis);
		}
		
		// LEVEL
//		if (alarmReportVo.getLevel()!=null && alarmReportVo.getLevel().size() > 0) {
//			StringBuilder sLevel = new StringBuilder();
//			sLevel.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sLEVEL));
//			for (String s : alarmReportVo.getLevel()) {
//				if (s.indexOf(Common.sALL) >= 0) {				
//					sLevel = new StringBuilder();
//					break;
//				} else {
//					sLevel.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
//				}
//			}
//
//			if (sLevel != null || !(sLevel.toString().isEmpty())) {				
//				if (sLevel.toString().indexOf("(") >= 0) {
//					sLevel.append(" )");
//				} // search in ( ... )
//				sQuery.append(sLevel.toString());
//			}
//		}
		
		//2021. 4. 6, X0122410 : FAB 선택시 테이블 쿼리 변경
//		String sTable = getTableFromFab();
		StringBuilder tQuery= new StringBuilder();		
		if (alarmReportVo.getFab()!=null && alarmReportVo.getFab().size() > 0) {
			List<String> fab = alarmReportVo.getFab();
			String fabName = "";
			log.info("fab:"+alarmReportVo.getFab());
			
			for(int i=0;i<alarmReportVo.getFab().size();i++){
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//fabName = getTableFromFab(Common.sFAB_SITE,fab.get(i));
				fabName = getTableFromFab(alarmReportVo.getFabSite(),fab.get(i));
				if(fabName != null && !fabName.isEmpty()) {
					if(i==0){
						tQuery.append(fabName);
					}else if(i==(alarmReportVo.getFab().size()-1)) {
						tQuery.append(Common.sComma + fabName);
					}else{
						tQuery.append(Common.sComma + fabName);
					}
				}
			}
		}		
		
		// 2021.03.24	X0122410 : MachineType조건 추가
//		sQuery.append(Common.sFrom + sTable + Common.sCRLF
//				+ Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX + Common.sComma + Common.sMACHINENAME
//				+ Common.sComma + Common.sUNIT + Common.sComma + Common.sSTATE + Common.sComma + Common.sALARMID
//				+ Common.sComma + Common.sALARMCODE + Common.sComma + Common.sALARMTEXT);
//		sQuery.append(Common.sFrom + sTable);
		sQuery.append(Common.sFrom + tQuery.toString());
		sQuery.append(Common.sCRLF + subMachineTypeQuery.toString());
		sQuery.append(Common.sCRLF
				+ Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX + Common.sComma + Common.sMACHINENAME + Common.sComma + Common.sMACHINETYPE
				+ Common.sComma + Common.sUNIT + Common.sComma + Common.sSTATE + Common.sComma + Common.sALARMID
				+ Common.sComma + Common.sALARMCODE + Common.sComma + Common.sALARMTEXT);
		
		/*if (alarmReportVo.getAlarmText() != null && !alarmReportVo.getAlarmText().equals("")) {
			sQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sALARMTEXT
					, Common.sDoubleQuotation + alarmReportVo.getAlarmText() + Common.sDoubleQuotation));
		}
		*/
		
		return sQuery.toString();
	}
	
	private String getTableFromFab(String fabSite, String fab) {
		switch(fabSite) {
			case Common.sFABSITE_M14 : {
				return Common.sTS_ALARM_M14A;
			}
			case Common.sFABSITE_M15 : {
				if(fab.equals(Common.sFAB_M15A)) {
					return Common.sTS_ALARM_M15A;
				}
				else if(fab.equals(Common.sFAB_M15B)){
					return Common.sTS_ALARM_M15B;
				}
			}
			case Common.sFABSITE_M11 : {
				if(fab.equals(Common.sFAB_M11A)) {
					return Common.sTS_ALARM_M11A;
				}
				else if(fab.equals(Common.sFAB_M11B)){
					return Common.sTS_ALARM_M11B;
				}
			}
			case Common.sFABSITE_C2 : {				
				if(fab.equals(Common.sFAB_C2)) {
					return Common.sTS_ALARM_C2;
				}
				else if(fab.equals(Common.sFAB_C2F)){
					return Common.sTS_ALARM_C2F;
				}
			}
			case Common.sFABSITE_IC : {
				if(fab.equals(Common.sFAB_M14A)) {
					return Common.sTS_ALARM_M14A; 
				}else if(fab.equals(Common.sFAB_M16A)){
					return Common.sTS_ALARM_M16A;
				}else if(fab.equals(Common.sFAB_M16B)){
					return Common.sTS_ALARM_M16B;
				}
			}
			default : return null;
		}
	}
}
