package com.skhynix.supply.res.service.impl;

import java.util.List;
import java.util.Map;

import javax.annotation.Resource;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.stereotype.Service;

import com.skhynix.supply.common.Common;
import com.skhynix.supply.res.dao.ResHistoryDAO;
import com.skhynix.supply.res.service.ResHistoryService;
import com.skhynix.supply.res.vo.ResCraneVo;
import com.skhynix.supply.res.vo.ResMachineVo;
import com.skhynix.supply.res.vo.ResPortVo;
import com.skhynix.supply.res.vo.ResShelfVo;
import com.skhynix.supply.res.vo.ResStorageFullVo;
import com.skhynix.supply.res.vo.ResVehicleVo;
@Service("resMachineHistoryServiceImpl")
public class ResMachineHistoryServiceImpl implements ResHistoryService {
	protected Log log = LogFactory.getLog(ResMachineHistoryServiceImpl.class);
	@Resource(name = "resHistoryDAO")
	ResHistoryDAO Client;
	
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(ResCraneVo resHistoryVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(ResStorageFullVo resStorageFullVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(ResMachineVo resMachineVo) throws Exception {
		List<Map> dataList = null; 
		long offset 	= (Long.parseLong(resMachineVo.getPageNum()) - 1) * Long.parseLong(resMachineVo.getRowNum());
		int   limit 	= Integer.parseInt(resMachineVo.getRowNum());
		String resultQuery = getQueryParser(resMachineVo);
		log.info("resultQuery : " + resultQuery);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			resultQuery += Common.sPipeLine + "limit " + offset + " " +  limit;	//결과 출력에 대해 limit을 적용한 쿼리 
			resultQuery += Common.sPipeLine + Common.sSort + Common.s_TIME;			//결과 출력에 대해 time sort를 적용한 쿼리
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(resMachineVo.getFabSite(), resultQuery);
		}
		return dataList;
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(ResPortVo resPortVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(ResShelfVo resShelfVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(ResVehicleVo resVehicleVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}
	
	public String getQueryParser(ResMachineVo resMachineVo) {
		if (resMachineVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(Common.sFulltext_Arg0_key1, 
				resMachineVo.getFrom(), resMachineVo.getTo(),
				(Common.sLeftParenthesis + Common.sMETHOD + Common.sEquals
				+ Common.sDoubleQuotation + "createMachineHistory"
				+ Common.sDoubleQuotation + Common.sRightParenthesis)));

		// Condition & Filter --> AND , OR
		// State
		if (resMachineVo.getState() != null && !resMachineVo.getState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sSTATE + Common.sEquals
					+ Common.sDoubleQuotation + resMachineVo.getState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// ConnectionState
		if (resMachineVo.getConnectionState() != null && !resMachineVo.getConnectionState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sCONNECTIONSTATE + Common.sEquals
					+ Common.sDoubleQuotation + resMachineVo.getConnectionState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// ControlState
		if (resMachineVo.getControlState() != null && !resMachineVo.getControlState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sCONTROLSTATE + Common.sEquals
					+ Common.sDoubleQuotation + resMachineVo.getControlState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// TscState
		if (resMachineVo.getTscState() != null && !resMachineVo.getTscState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sTSCSTATE + Common.sEquals
					+ Common.sDoubleQuotation + resMachineVo.getTscState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// ProcessingState
		if (resMachineVo.getProcessingState() != null && !resMachineVo.getProcessingState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sPROCESSINGSTATE + Common.sEquals
					+ Common.sDoubleQuotation + resMachineVo.getProcessingState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		
		// sAREANAME
		if (resMachineVo.getAreaName()!=null && resMachineVo.getAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + resMachineVo.getAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 

		// sBAYNAME
		if (resMachineVo.getBayName()!=null && resMachineVo.getBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + resMachineVo.getBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// 2021.03.22	X0122410 : 기존 검색조건이 잘못 연결되어 있었음, TYPE > MACHINETYPE으로 변경
		// sTYPE
		/*
		if (resMachineVo.getMachineType()!=null && resMachineVo.getMachineType().size() > 0) {
			List<String> typeList = resMachineVo.getMachineType();
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
		// sMACHINETYPE
		StringBuilder subMachineTypeQuery = new StringBuilder();
		if (resMachineVo.getMachineType()!=null && resMachineVo.getMachineType().size() > 0) {			
			subMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sMACHINETYPE));
			for (String s : resMachineVo.getMachineType()) {
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
		if (resMachineVo.getMachineName()!=null && resMachineVo.getMachineName().size() > 0) {
			List<String> machineList = resMachineVo.getMachineName();
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
//		if (resMachineVo.getLevel()!=null && resMachineVo.getLevel().size() > 0) {
//			StringBuilder sLevel = new StringBuilder();
//			sLevel.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sLEVEL));
//			for (String s : resMachineVo.getLevel()) {
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
		
		//2021. 4. 9, X0122410 : FAB 선택시 테이블 쿼리 변경
//		String sTable = getTableFromFab();
		StringBuilder tQuery= new StringBuilder();		
		if (resMachineVo.getFab()!=null && resMachineVo.getFab().size() > 0) {
			List<String> fab = resMachineVo.getFab();
			String fabName = "";
			log.info("fab:"+resMachineVo.getFab());
			
			for(int i=0;i<resMachineVo.getFab().size();i++){
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//fabName = getTableFromFab(Common.sFAB_SITE,fab.get(i));
				fabName = getTableFromFab(resMachineVo.getFabSite(), fab.get(i));
				if(fabName != null && !fabName.isEmpty()) {
					if(i==0){
						tQuery.append(fabName);
					}else if(i==(resMachineVo.getFab().size()-1)) {
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
//				+ Common.sComma + Common.sSTATE + Common.sComma + Common.sCONTROLSTATE + Common.sComma + Common.sCONNECTIONSTATE
//				+ Common.sComma + Common.sTSCSTATE + Common.sComma + Common.sPROCESSINGSTATE 
//				);
		//sQuery.append(Common.sFrom + sTable);
		sQuery.append(Common.sFrom + tQuery.toString());
		sQuery.append(Common.sCRLF + subMachineTypeQuery.toString());
		sQuery.append(Common.sCRLF
				+ Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX + Common.sComma + Common.sMACHINENAME + Common.sComma + Common.sMACHINETYPE
				+ Common.sComma + Common.sSTATE + Common.sComma + Common.sCONTROLSTATE + Common.sComma + Common.sCONNECTIONSTATE
				+ Common.sComma + Common.sTSCSTATE + Common.sComma + Common.sPROCESSINGSTATE );
		
		return sQuery.toString();
	}
	
	private String getTableFromFab(String fabSite, String fab) {
		
		switch(fabSite) {
			case Common.sFABSITE_M14 : {
				return Common.sTS_RESOURCE_M14A;
			}
			case Common.sFABSITE_M15 : {
				if(fab.equals(Common.sFAB_M15A)) {
					return Common.sTS_RESOURCE_M15A;
				}
				else if(fab.equals(Common.sFAB_M15B)){
					return Common.sTS_RESOURCE_M15B;
				}
			}
			case Common.sFABSITE_M11 : {
				if(fab.equals(Common.sFAB_M11A)) {
					return Common.sTS_RESOURCE_M11A;
				}
				else if(fab.equals(Common.sFAB_M11B)){
					return Common.sTS_RESOURCE_M11B;
				}
			}
			case Common.sFABSITE_C2 : {				
				if(fab.equals(Common.sFAB_C2)) {
					return Common.sTS_RESOURCE_C2;
				}
				else if(fab.equals(Common.sFAB_C2F)){
					return Common.sTS_RESOURCE_C2F;
				}
			}
			case Common.sFABSITE_IC : {
				if(fab.equals(Common.sFAB_M14A)) {
					return Common.sTS_RESOURCE_M14A; 
				}else if(fab.equals(Common.sFAB_M16A)){
					return Common.sTS_RESOURCE_M16A;
				}else if(fab.equals(Common.sFAB_M16B)){
					return Common.sTS_RESOURCE_M16B;
				}
			}
			default : return null;
		}
	}
}
