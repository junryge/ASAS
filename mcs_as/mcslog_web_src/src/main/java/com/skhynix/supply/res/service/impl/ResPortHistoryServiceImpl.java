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
@Service("resPortHistoryServiceImpl")
public class ResPortHistoryServiceImpl implements ResHistoryService {
	protected Log log = LogFactory.getLog(ResPortHistoryServiceImpl.class);
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
		// TODO Auto-generated method stub
		return null;
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(ResPortVo resPortVo) throws Exception {
		List<Map> dataList = null; 
		long offset 	= (Long.parseLong(resPortVo.getPageNum()) - 1) * Long.parseLong(resPortVo.getRowNum());
		int   limit 	= Integer.parseInt(resPortVo.getRowNum());
		String resultQuery = getQueryParser(resPortVo);
		log.info("resultQuery : " + resultQuery);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			resultQuery += Common.sPipeLine + "limit " + offset + " " +  limit;		//결과 출력에 대해 limit을 적용한 쿼리 
			resultQuery += Common.sPipeLine + Common.sSort + Common.s_TIME;			//결과 출력에 대해 time sort를 적용한 쿼리
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(resPortVo.getFabSite(), resultQuery);
		}
		return dataList;
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


	public String getQueryParser(ResPortVo resPortVo) {
		if (resPortVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(Common.sFulltext_Arg0_key1, 
				resPortVo.getFrom(), resPortVo.getTo(),
				(Common.sLeftParenthesis + Common.sMETHOD + Common.sEquals
				+ Common.sDoubleQuotation + "createPortHistory"
				+ Common.sDoubleQuotation + Common.sRightParenthesis)));

		// Condition & Filter --> AND , OR
		// PortName
		if (resPortVo.getPortName() != null && !resPortVo.getPortName().equals("")) {
			if(resPortVo.getPortName().contains(Common.sUnderbar)){
				StringBuilder tmpQuery = new StringBuilder();
				String[] portNameArray = resPortVo.getPortName().split(Common.sUnderbar);
				for(int i=0;i<portNameArray.length;i++){
					if(i==0){
						tmpQuery.append(
								Common.sCRLF + Common.sLeftParenthesis
								+ Common.sLeftParenthesis + Common.sPORTNAME + Common.sEquals
								+ Common.sDoubleQuotation + portNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}else if(i==(portNameArray.length-1)){
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sPORTNAME + Common.sEquals
								+ Common.sDoubleQuotation + portNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sRightParenthesis );
					}else{
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sPORTNAME + Common.sEquals
								+ Common.sDoubleQuotation + portNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}
				}
				sQuery.append(Common.sCRLF + Common.sAnd + tmpQuery.toString());
			}else{
				sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
						+ Common.sPORTNAME + Common.sEquals
						+ Common.sDoubleQuotation + resPortVo.getPortName() 
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}
		// State
		if (resPortVo.getState() != null && !resPortVo.getState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sSTATE + Common.sEquals
					+ Common.sDoubleQuotation + resPortVo.getState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// SubState
		if (resPortVo.getSubState() != null && !resPortVo.getSubState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sSUBSTATE + Common.sEquals
					+ Common.sDoubleQuotation + resPortVo.getSubState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// ProcessingState
		if (resPortVo.getProcessingState() != null && !resPortVo.getProcessingState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sPROCESSINGSTATE + Common.sEquals
					+ Common.sDoubleQuotation + resPortVo.getProcessingState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// Banned
		if (resPortVo.getBanned() != null && !resPortVo.getBanned().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sBANNED + Common.sEquals
					+ Common.sDoubleQuotation + resPortVo.getBanned() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// CraneAvailable
		if (resPortVo.getCraneAvailable() != null && !resPortVo.getCraneAvailable().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sCRANEAVAILABLE + Common.sEquals
					+ Common.sDoubleQuotation + resPortVo.getCraneAvailable() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// InOutType
		if (resPortVo.getInOutType() != null && !resPortVo.getInOutType().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sINOUTTYPE + Common.sEquals
					+ Common.sDoubleQuotation + resPortVo.getInOutType() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// Manual
		if (resPortVo.getManual() != null && !resPortVo.getManual().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sMANUAL + Common.sEquals
					+ Common.sDoubleQuotation + resPortVo.getManual() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// AccessMode
		if (resPortVo.getAccessMode() != null && !resPortVo.getAccessMode().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sACCESSMODE + Common.sEquals
					+ Common.sDoubleQuotation + resPortVo.getAccessMode() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// IdReadState
		if (resPortVo.getIdReadState() != null && !resPortVo.getIdReadState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sIDREADSTATE + Common.sEquals
					+ Common.sDoubleQuotation + resPortVo.getIdReadState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		
		// sAREANAME
		if (resPortVo.getAreaName()!=null && resPortVo.getAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + resPortVo.getAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 

		// sBAYNAME
		if (resPortVo.getBayName()!=null && resPortVo.getBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + resPortVo.getBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// 2021.03.22	X0122410 : 기존 검색조건이 잘못 연결되어 있었음, TYPE > MACHINETYPE으로 변경
		// sTYPE
		/*
		if (resPortVo.getMachineType()!=null && resPortVo.getMachineType().size() > 0) {
			List<String> typeList = resPortVo.getMachineType();
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
		if (resPortVo.getMachineType()!=null && resPortVo.getMachineType().size() > 0) {			
			subMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sMACHINETYPE));
			for (String s : resPortVo.getMachineType()) {
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
		if (resPortVo.getMachineName()!=null && resPortVo.getMachineName().size() > 0) {
			List<String> machineList = resPortVo.getMachineName();
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
//		if (resPortVo.getLevel()!=null && resPortVo.getLevel().size() > 0) {
//			StringBuilder sLevel = new StringBuilder();
//			sLevel.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sLEVEL));
//			for (String s : resPortVo.getLevel()) {
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
		if (resPortVo.getFab()!=null && resPortVo.getFab().size() > 0) {
			List<String> fab = resPortVo.getFab();
			String fabName = "";
			log.info("fab:"+resPortVo.getFab());
			
			for(int i=0;i<resPortVo.getFab().size();i++){
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//fabName = getTableFromFab(Common.sFAB_SITE,fab.get(i));
				fabName = getTableFromFab(resPortVo.getFabSite(), fab.get(i));
				if(fabName != null && !fabName.isEmpty()) {
					if(i==0){
						tQuery.append(fabName);
					}else if(i==(resPortVo.getFab().size()-1)) {
						tQuery.append(Common.sComma + fabName);
					}else{
						tQuery.append(Common.sComma + fabName);
					}
				}
			}
		}
		
		// 2021.03.24	X0122410 : MachineType조건 추가
//		sQuery.append(Common.sFrom + sTable + Common.sCRLF
//				+ Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX + Common.sComma
//				+ Common.sMACHINENAME + Common.sComma + Common.sPORTNAME + Common.sComma + Common.sSTATE
//				+ Common.sComma + Common.sPROCESSINGSTATE + Common.sComma + Common.sSUBSTATE + Common.sComma
//				+ Common.sINOUTTYPE + Common.sComma + Common.sMANUAL + Common.sComma + Common.sOCCUPIED
//				+ Common.sComma + Common.sBANNED + Common.sComma + Common.sTRANSPORTUNITACCESSIBLE + Common.sComma
//				+ Common.sIDREADSTATE + Common.sComma + Common.sACCESSMODE
//				);		
		//sQuery.append(Common.sFrom + sTable);
		sQuery.append(Common.sFrom + tQuery.toString());
		sQuery.append(Common.sCRLF + subMachineTypeQuery.toString());
		sQuery.append(Common.sCRLF
				+ Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX + Common.sComma
				+ Common.sMACHINENAME + Common.sComma + Common.sMACHINETYPE + Common.sComma + Common.sPORTNAME + Common.sComma + Common.sSTATE
				+ Common.sComma + Common.sPROCESSINGSTATE + Common.sComma + Common.sSUBSTATE + Common.sComma
				+ Common.sINOUTTYPE + Common.sComma + Common.sMANUAL + Common.sComma + Common.sOCCUPIED
				+ Common.sComma + Common.sBANNED + Common.sComma + Common.sTRANSPORTUNITACCESSIBLE + Common.sComma
				+ Common.sIDREADSTATE + Common.sComma + Common.sACCESSMODE);
		
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
