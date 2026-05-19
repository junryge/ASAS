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
@Service("resShelfHistoryServiceImpl")
public class ResShelfHistoryServiceImpl implements ResHistoryService {
	protected Log log = LogFactory.getLog(ResShelfHistoryServiceImpl.class);
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
		// TODO Auto-generated method stub
		return null;
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(ResShelfVo resShelfVo) throws Exception {
		List<Map> dataList = null; 
		long offset 	= (Long.parseLong(resShelfVo.getPageNum()) - 1) * Long.parseLong(resShelfVo.getRowNum());
		int   limit 	= Integer.parseInt(resShelfVo.getRowNum());
		String resultQuery = getQueryParser(resShelfVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			resultQuery += Common.sPipeLine + "limit " + offset + " " +  limit;	//결과 출력에 대해 limit을 적용한 쿼리 
			resultQuery += Common.sPipeLine + Common.sSort + Common.s_TIME;			//결과 출력에 대해 time sort를 적용한 쿼리
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(resShelfVo.getFabSite(), resultQuery);
		}
		return dataList;
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(ResVehicleVo resVehicleVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}
	
	public String getQueryParser(ResShelfVo resShelfVo) {
		if (resShelfVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(Common.sFulltext_Arg0_key1, 
				resShelfVo.getFrom(), resShelfVo.getTo(),
				(Common.sLeftParenthesis + Common.sMETHOD + Common.sEquals
					+ Common.sDoubleQuotation + "createShelfHistory"
					+ Common.sDoubleQuotation + Common.sRightParenthesis)));

		// Condition & Filter --> AND , OR
		// ShelfName
		if (resShelfVo.getShelfName() != null && !resShelfVo.getShelfName().equals("")) {
			if(resShelfVo.getShelfName().contains(Common.sMinus)){
				StringBuilder tmpQuery = new StringBuilder();
				String[] shelfNameArray = resShelfVo.getShelfName().split(Common.sMinus);
				for(int i=0;i<shelfNameArray.length;i++){
					if(i==0){
						tmpQuery.append(
								Common.sCRLF + Common.sLeftParenthesis
								+ Common.sLeftParenthesis + Common.sSHELFNAME + Common.sEquals
								+ Common.sDoubleQuotation + shelfNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}else if(i==(shelfNameArray.length-1)){
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sSHELFNAME + Common.sEquals
								+ Common.sDoubleQuotation + shelfNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sRightParenthesis );
					}else{
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sSHELFNAME + Common.sEquals
								+ Common.sDoubleQuotation + shelfNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}
				}
				sQuery.append(Common.sCRLF + Common.sAnd + tmpQuery.toString());
			}else{
				sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
						+ Common.sSHELFNAME + Common.sEquals
						+ Common.sDoubleQuotation + resShelfVo.getShelfName() 
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}
		// State
		if (resShelfVo.getState() != null && !resShelfVo.getState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sSTATE + Common.sEquals
					+ Common.sDoubleQuotation + resShelfVo.getState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// ProcessingState
		if (resShelfVo.getProcessingState() != null && !resShelfVo.getProcessingState().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sPROCESSINGSTATE + Common.sEquals
					+ Common.sDoubleQuotation + resShelfVo.getProcessingState() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		// Banned
		if (resShelfVo.getBanned() != null && !resShelfVo.getBanned().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sBANNED + Common.sEquals
					+ Common.sDoubleQuotation + resShelfVo.getBanned() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		
		// sAREANAME
		if (resShelfVo.getAreaName()!=null && resShelfVo.getAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + resShelfVo.getAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 

		// sBAYNAME
		if (resShelfVo.getBayName()!=null && resShelfVo.getBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + resShelfVo.getBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// 2021.03.22	X0122410 : 기존 검색조건이 잘못 연결되어 있었음, TYPE > MACHINETYPE으로 변경
		// sTYPE
		/*
		if (resShelfVo.getMachineType()!=null && resShelfVo.getMachineType().size() > 0) {
			List<String> typeList = resShelfVo.getMachineType();
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
		if (resShelfVo.getMachineType()!=null && resShelfVo.getMachineType().size() > 0) {			
			subMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sMACHINETYPE));
			for (String s : resShelfVo.getMachineType()) {
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
		if (resShelfVo.getMachineName()!=null && resShelfVo.getMachineName().size() > 0) {
			List<String> machineList = resShelfVo.getMachineName();
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
//		if (resShelfVo.getLevel()!=null && resShelfVo.getLevel().size() > 0) {
//			StringBuilder sLevel = new StringBuilder();
//			sLevel.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sLEVEL));
//			for (String s : resShelfVo.getLevel()) {
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
		if (resShelfVo.getFab()!=null && resShelfVo.getFab().size() > 0) {
			List<String> fab = resShelfVo.getFab();
			String fabName = "";
			log.info("fab:"+resShelfVo.getFab());
			
			for(int i=0;i<resShelfVo.getFab().size();i++){
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//fabName = getTableFromFab(Common.sFAB_SITE,fab.get(i));
				fabName = getTableFromFab(resShelfVo.getFabSite(), fab.get(i));
				if(fabName != null && !fabName.isEmpty()) {
					if(i==0){
						tQuery.append(fabName);
					}else if(i==(resShelfVo.getFab().size()-1)) {
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
//				+ Common.sComma + Common.sSHELFNAME + Common.sComma + Common.sSTATE + Common.sComma + Common.sPROCESSINGSTATE
//				+ Common.sComma + Common.sBANNED
//				);		
		//sQuery.append(Common.sFrom + sTable);
		sQuery.append(Common.sFrom + tQuery.toString());
		sQuery.append(Common.sCRLF + subMachineTypeQuery.toString());
		sQuery.append(Common.sCRLF
				+ Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX + Common.sComma + Common.sMACHINENAME + Common.sComma + Common.sMACHINETYPE
				+ Common.sComma + Common.sSHELFNAME + Common.sComma + Common.sSTATE + Common.sComma + Common.sPROCESSINGSTATE
				+ Common.sComma + Common.sBANNED);
		
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
