package com.skhynix.supply.mat.service.impl;

import java.util.List;
import java.util.Map;

import javax.annotation.Resource;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.stereotype.Service;

import com.skhynix.supply.common.Common;
import com.skhynix.supply.mat.dao.MaterialDAO;
import com.skhynix.supply.mat.service.MaterialService;
import com.skhynix.supply.mat.vo.MaterialVo;

@Service("materialService")
public class MeterialServiceImpl implements MaterialService {
	protected Log log = LogFactory.getLog(MeterialServiceImpl.class);
	@Resource(name = "materialDAO")
	MaterialDAO Client;
	

	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 16. 
	 * @작성자     : 최명수
	 * @param    :
	 * @Method 설명 : Carrier 위치 이력 조회
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(MaterialVo matVo) throws Exception {
		List<Map> dataList = null; 
		long offset 	= (Long.parseLong(matVo.getPageNum()) - 1) * Long.parseLong(matVo.getRowNum());
		int   limit 	= Integer.parseInt(matVo.getRowNum());
		String resultQuery = getQueryParser(matVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			resultQuery += Common.sPipeLine + "limit " + offset + " " +  limit;		//결과 출력에 대해 limit을 적용한 쿼리 
			resultQuery += Common.sPipeLine + Common.sSort + Common.s_TIME;			//결과 출력에 대해 time sort를 적용한 쿼리
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(matVo.getFabSite(), resultQuery);
		}
		return dataList;
	}
	
	/**
	 * @Method Name  : getQueryParser
	 * @작성일     : 2017. 3. 16. 
	 * @작성자     : 최명수
	 * @param    :
	 * @Method 설명 : Query 생성
	 * @return
	 * @throws Exception
	 */
	public String getQueryParser(MaterialVo matVo) {
		if (matVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(Common.sFulltext_Arg0_key1, 
				matVo.getFrom(), matVo.getTo(),
				(Common.sLeftParenthesis + Common.sMETHOD + Common.sEquals 
				 + Common.sDoubleQuotation+"createCarrierLocationHistory"+Common.sDoubleQuotation
				 + Common.sRightParenthesis)));

		// 6.Condition & Filter --> AND , OR
		// 6-1
		if (matVo.getCarrier() != null && !matVo.getCarrier().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sCARRIER + Common.sEquals
					+ Common.sDoubleQuotation + matVo.getCarrier() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// 6-2
		if (matVo.getLotId() != null && !matVo.getLotId().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sLOTID + Common.sEquals
					+ Common.sDoubleQuotation + matVo.getLotId() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// 6-3
		if (matVo.getCommandId() != null && !matVo.getCommandId().equals("")) {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sTRANSPORTCOMMANDID + Common.sEquals
					+ Common.sDoubleQuotation + matVo.getCommandId() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// 6-4
		if (matVo.getUnit() != null && !matVo.getUnit().equals("")) {
			if(matVo.getUnit().contains(Common.sUnderbar)){
				StringBuilder tmpQuery = new StringBuilder();
				String[] unitNameArray = matVo.getUnit().split(Common.sUnderbar);
				for(int i=0;i<unitNameArray.length;i++){
					if(i==0){
						tmpQuery.append(
								Common.sCRLF + Common.sLeftParenthesis
								+ Common.sLeftParenthesis + Common.sCURRENTUNITNAME + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}else if(i==(unitNameArray.length-1)){
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sCURRENTUNITNAME + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sRightParenthesis );
					}else{
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sCURRENTUNITNAME + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}
				}
				sQuery.append(Common.sCRLF + Common.sAnd + tmpQuery.toString());
			}else if(!matVo.getUnit().contains(Common.sUnderbar)&&matVo.getUnit().contains(Common.sMinus)){
				StringBuilder tmpQuery = new StringBuilder();
				String[] unitNameArray = matVo.getUnit().split(Common.sMinus);
				for(int i=0;i<unitNameArray.length;i++){
					if(i==0){
						tmpQuery.append(
								Common.sCRLF + Common.sLeftParenthesis
								+ Common.sLeftParenthesis + Common.sCURRENTUNITNAME + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}else if(i==(unitNameArray.length-1)){
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sCURRENTUNITNAME + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sRightParenthesis );
					}else{
						tmpQuery.append(
								Common.sLeftParenthesis
								+ Common.sCURRENTUNITNAME + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i]
								+ Common.sDoubleQuotation 
								+ Common.sRightParenthesis + Common.sAnd);
					}
				}
				sQuery.append(Common.sCRLF + Common.sAnd + tmpQuery.toString());
			}else{
				sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
						+ Common.sCURRENTUNITNAME + Common.sEquals
						+ Common.sDoubleQuotation + matVo.getUnit() 
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}
		
		// sAREANAME
		if (matVo.getAreaName()!=null && matVo.getAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + matVo.getAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 

		// sBAYNAME
		if (matVo.getBayName()!=null && matVo.getBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + matVo.getBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// 2021.03.22	X0122410 : 기존 검색조건이 잘못 연결되어 있었음, TYPE > MACHINETYPE으로 변경
		// sTYPE
		/*
		if (matVo.getMachineType()!=null && matVo.getMachineType().size() > 0) {
			List<String> typeList = matVo.getMachineType();
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
		if (matVo.getMachineType()!=null && matVo.getMachineType().size() > 0) {			
			subMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sMACHINETYPE));
			for (String s : matVo.getMachineType()) {
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
		if (matVo.getMachineName()!=null && matVo.getMachineName().size() > 0) {
			List<String> machineList = matVo.getMachineName();
			sQuery.append(Common.sAnd);
			for (int i=0;i<machineList.size();i++) {
				if (machineList.get(i).indexOf(Common.sNOTDESIGNATED) >= 0) {
					break;
				} 
				if(i==0) {
					sQuery.append(Common.sLeftParenthesis +
						Common.sCURRENTMACHINENAME + Common.sEquals +
						Common.sDoubleQuotation + machineList.get(i)+ Common.sDoubleQuotation);
				}else{
					sQuery.append(Common.sOr +
						Common.sCURRENTMACHINENAME + Common.sEquals +
						Common.sDoubleQuotation + machineList.get(i)+ Common.sDoubleQuotation);
				}
			}
			sQuery.append(Common.sRightParenthesis);
		}
		
		// LEVEL
//		if (matVo.getLevel()!=null && matVo.getLevel().size() > 0) {
//			StringBuilder sLevel = new StringBuilder();
//			sLevel.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sLEVEL));
//			for (String s : matVo.getLevel()) {
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
		if (matVo.getFab()!=null && matVo.getFab().size() > 0) {
			List<String> fab = matVo.getFab();
			String fabName = "";
			log.info("fab:"+matVo.getFab());
			
			for(int i=0;i<matVo.getFab().size();i++){
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//fabName = getTableFromFab(Common.sFAB_SITE,fab.get(i));
				fabName = getTableFromFab(matVo.getFabSite(), fab.get(i));
				if(fabName != null && !fabName.isEmpty()) {
					if(i==0){
						tQuery.append(fabName);
					}else if(i==(matVo.getFab().size()-1)) {
						tQuery.append(Common.sComma + fabName);
					}else{
						tQuery.append(Common.sComma + fabName);
					}
				}
			}
		}		
		
		// 2021.03.24	X0122410 : MachineType조건 추가
//		sQuery.append(Common.sFrom + sTable + Common.sCRLF
//				+ Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX + Common.sComma + Common.sCARRIER
//				+ Common.sComma + Common.sLOTID + Common.sComma + Common.sTRANSPORTCOMMANDID + Common.sComma
//				+ Common.sCURRENTMACHINENAME + Common.sComma + Common.sCURRENTUNITNAME
//				);		
//		sQuery.append(Common.sFrom + sTable);
		sQuery.append(Common.sFrom + tQuery.toString());
		sQuery.append(Common.sCRLF + subMachineTypeQuery.toString());
		sQuery.append(Common.sCRLF
				+ Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX + Common.sComma + Common.sCARRIER
				+ Common.sComma + Common.sLOTID + Common.sComma + Common.sTRANSPORTCOMMANDID + Common.sComma
				+ Common.sCURRENTMACHINENAME + Common.sComma + Common.sMACHINETYPE + Common.sComma + Common.sCURRENTUNITNAME
				);
		
		return sQuery.toString();
	}
	
	private String getTableFromFab(String fabSite, String fab) {
		
		switch(fabSite) {
			case Common.sFABSITE_M14 : {
				return Common.sTS_MATERIAL_M14A;
			}
			case Common.sFABSITE_M15 : {
				if(fab.equals(Common.sFAB_M15A)) {
					return Common.sTS_MATERIAL_M15A;
				}
				else if(fab.equals(Common.sFAB_M15B)){
					return Common.sTS_MATERIAL_M15B;
				}
			}
			case Common.sFABSITE_M11 : {
				if(fab.equals(Common.sFAB_M11A)) {
					return Common.sTS_MATERIAL_M11A;
				}
				else if(fab.equals(Common.sFAB_M11B)){
					return Common.sTS_MATERIAL_M11B;
				}
			}
			case Common.sFABSITE_C2 : {				
				if(fab.equals(Common.sFAB_C2)) {
					return Common.sTS_MATERIAL_C2;
				}
				else if(fab.equals(Common.sFAB_C2F)){
					return Common.sTS_MATERIAL_C2F;
				}
			}
			case Common.sFABSITE_IC : {
				if(fab.equals(Common.sFAB_M14A)) {
					return Common.sTS_MATERIAL_M14A; 
				}else if(fab.equals(Common.sFAB_M16A)){
					return Common.sTS_MATERIAL_M16A;
				}else if(fab.equals(Common.sFAB_M16B)){
					return Common.sTS_MATERIAL_M16B;
				}
			}
			default : return null;
		}
	}
}
