package com.skhynix.supply.tran.service.impl;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Map;

import javax.annotation.Resource;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.stereotype.Service;

import com.skhynix.supply.common.Common;
import com.skhynix.supply.tran.dao.TranDAO;
import com.skhynix.supply.tran.service.TranService;
import com.skhynix.supply.tran.vo.TranCmdFailVo;
import com.skhynix.supply.tran.vo.TranJobFailVo;
import com.skhynix.supply.tran.vo.TranVo;

/**
 * @Package Name : com.skhynix.supply.tran.service.impl
 * @FileName : TranServiceImpl.java
 * @작성일 : 2017. 3.20.
 * @작성자 : 최명수
 * @프로그램 설명 : 반송 이력 조회 서비스
 */
@Service("tranService")
public class TranServiceImpl implements TranService {
	protected Log log = LogFactory.getLog(TranServiceImpl.class);
	@Resource(name = "tranDAO")
	TranDAO Client;
	
	/**
	 * @Method Name : getDataList
	 * @작성일 : 2017. 3. 20.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 반송 이력 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(TranVo tranVo) throws Exception {
		List<Map> dataList = null; 
		long offset 	= (Long.parseLong(tranVo.getPageNum()) - 1) * Long.parseLong(tranVo.getRowNum());
		int   limit 	= Integer.parseInt(tranVo.getRowNum());
		String resultQuery = getTranQueryParser(tranVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			resultQuery += Common.sPipeLine + "limit " + offset + Common.sSpace +  limit;	//결과 출력에 대해 limit을 적용한 쿼리 
			resultQuery += Common.sPipeLine + Common.sSort + Common.s_TIME;			//결과 출력에 대해 time sort를 적용한 쿼리
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(tranVo.getFabSite(), resultQuery);
		}
		return dataList;
	}
	
	/**
	 * @Method Name : getTranJobHistoryDetail
	 * @작성일 : 2017. 3. 20.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 반송 이력 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getTranJobHistoryDetail(TranVo tranVo) throws Exception{
		List<Map> dataList = null; 
		String resultQuery = getTranJobHistoryDetailQueryParser(tranVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			dataList = Client.dbExecuteQuery(tranVo.getFabSite(), resultQuery);
		}
		return dataList;
	}
	
	/**
	 * @Method Name : getTranCmdHistoryDetail
	 * @작성일 : 2017. 3. 20.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 반송 이력 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	/*@Override
	public List<Map> getTranCmdHistoryDetail(TranVo tranVo) throws Exception{
		List<Map> dataList = null; 
		String resultQuery = getTranCmdHistoryQueryParser(tranVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			dataList = Client.dbExecuteQuery(resultQuery);
		}
		return dataList;
	}*/

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(TranCmdFailVo cmdFailVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}

	/**
	 * @Method Name : getTranQueryParser
	 * @작성일 : 2017. 3. 20.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 반송 이력 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	public String getTranQueryParser(TranVo tranVo){
		if (tranVo == null) {
			return null;
		} // null exception
		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(Common.sFulltext_Arg0_key1, 
				tranVo.getFrom(), tranVo.getTo(), 
				(Common.sLeftParenthesis + Common.sMETHOD + Common.sEquals
				+ Common.sDoubleQuotation + "createTransportJobHistory"
				+ Common.sDoubleQuotation 
				/*+ Common.sOr
				+ Common.sDoubleQuotation + "createTransportCommandHistory"
				+ Common.sDoubleQuotation*/ 
				+ Common.sRightParenthesis)));
						
		//Carrier
		if(tranVo.getCarrier()!=null && !tranVo.getCarrier().equals("")){
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sCARRIER + Common.sEquals
					+ Common.sDoubleQuotation + tranVo.getCarrier() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		//TransportJobId
		if(tranVo.getTransportJobId()!=null && !tranVo.getTransportJobId().equals("")){
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sTRANSPORTJOBID + Common.sEquals
					+ Common.sDoubleQuotation + tranVo.getTransportJobId() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}		
		//LotId
		if(tranVo.getLotId()!=null && !tranVo.getLotId().equals("")){
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sLOTID + Common.sEquals
					+ Common.sDoubleQuotation + tranVo.getLotId() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		
		// sTransportAREANAME
		if (tranVo.getTransportAreaName()!=null && tranVo.getTransportAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sTRANSPORTAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + tranVo.getTransportAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 
		// sTransportBAYNAME
		if (tranVo.getTransportBayName()!=null && tranVo.getTransportBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sTRANSPORTBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + tranVo.getTransportBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		
		// sFromAREANAME
		if (tranVo.getFromAreaName()!=null && tranVo.getFromAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sSOURCEAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + tranVo.getFromAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 
		// sFromBAYNAME
		if (tranVo.getFromBayName()!=null && tranVo.getFromBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sSOURCEBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + tranVo.getFromBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// sToAREANAME
		if (tranVo.getToAreaName()!=null && tranVo.getToAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sDESTAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + tranVo.getToAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 

		// sToBAYNAME
		if (tranVo.getToBayName()!=null && tranVo.getToBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sDESTBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + tranVo.getToBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// Machine Name -- Single/Multi Filter
		//Transport MachineType
		StringBuilder subTransportMachineTypeQuery = new StringBuilder();
		if (tranVo.getTransportMachineType()!=null && tranVo.getTransportMachineType().size() > 0) {			
			subTransportMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sTRANSPORTTYPE2));
			for (String s : tranVo.getTransportMachineType()) {
				if (s.indexOf(Common.sALL) >= 0) {	
					subTransportMachineTypeQuery = new StringBuilder();
					break;
				} else {
					subTransportMachineTypeQuery.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
				}
			}

			if (subTransportMachineTypeQuery != null || !(subTransportMachineTypeQuery.toString().isEmpty())) {
				if (subTransportMachineTypeQuery.toString().indexOf("(") >= 0) {
					subTransportMachineTypeQuery.append(" )");
				}				
			}
		}
		
		// sTransport MACHINENAME
		if (tranVo.getTransportMachineName()!=null && tranVo.getTransportMachineName().size() > 0) {
			List<String> machineList = tranVo.getTransportMachineName();
			sQuery.append(Common.sAnd);
			for (int i=0;i<machineList.size();i++) {
				if (machineList.get(i).indexOf(Common.sNOTDESIGNATED) >= 0) {
					break;
				} 
				if(i==0) {
					sQuery.append(Common.sLeftParenthesis +
						Common.sTRANSPORTMACHINENAME + Common.sEquals +
						Common.sDoubleQuotation + machineList.get(i)+ Common.sDoubleQuotation);
				}else{
					sQuery.append(Common.sOr +
						Common.sTRANSPORTMACHINENAME + Common.sEquals +
						Common.sDoubleQuotation + machineList.get(i)+ Common.sDoubleQuotation);
				}
			}
			sQuery.append(Common.sRightParenthesis);
		}
		
		// 2021.03.22	X0122410 : 기존 sSOURCEMACHINETYPE > sSOURCEMACHINETYPE2
		// sFromTYPE
		/*
		if (tranVo.getFromMachineType()!=null && tranVo.getFromMachineType().size() > 0) {
			List<String> typeList = tranVo.getFromMachineType();
			sQuery.append(Common.sCRLF + Common.sAnd);
			for (int i=0;i<typeList.size();i++) {
				if (typeList.get(i).indexOf(Common.sNOTDESIGNATED) >= 0) {
					break;
				}
				
				if(i==0) {
					sQuery.append(Common.sLeftParenthesis +
						Common.sSOURCEMACHINETYPE + Common.sEquals +
						Common.sDoubleQuotation + typeList.get(i)+ Common.sDoubleQuotation);
				}else{
					sQuery.append(Common.sOr +
						Common.sSOURCEMACHINETYPE + Common.sEquals +
						Common.sDoubleQuotation + typeList.get(i)+ Common.sDoubleQuotation);
				}
			}
			sQuery.append(Common.sRightParenthesis);
		}
		*/
		StringBuilder subFromMachineTypeQuery = new StringBuilder();
		if (tranVo.getFromMachineType()!=null && tranVo.getFromMachineType().size() > 0) {			
			subFromMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sSOURCEMACHINETYPE2));
			for (String s : tranVo.getFromMachineType()) {
				if (s.indexOf(Common.sALL) >= 0) {	
					subFromMachineTypeQuery = new StringBuilder();
					break;
				} else {
					subFromMachineTypeQuery.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
				}
			}

			if (subFromMachineTypeQuery != null || !(subFromMachineTypeQuery.toString().isEmpty())) {
				if (subFromMachineTypeQuery.toString().indexOf("(") >= 0) {
					subFromMachineTypeQuery.append(" )");
				}				
			}
		}
		
		// sFromMACHINENAME
		if (tranVo.getFromMachineName()!=null && tranVo.getFromMachineName().size() > 0) {
			List<String> machineList = tranVo.getFromMachineName();
			sQuery.append(Common.sAnd);
			for (int i=0;i<machineList.size();i++) {
				if (machineList.get(i).indexOf(Common.sNOTDESIGNATED) >= 0) {
					break;
				} 
				if(i==0) {
					sQuery.append(Common.sLeftParenthesis +
						Common.sSOURCEMACHINENAME + Common.sEquals +
						Common.sDoubleQuotation + machineList.get(i)+ Common.sDoubleQuotation);
				}else{
					sQuery.append(Common.sOr +
						Common.sSOURCEMACHINENAME + Common.sEquals +
						Common.sDoubleQuotation + machineList.get(i)+ Common.sDoubleQuotation);
				}
			}
			sQuery.append(Common.sRightParenthesis);
		}
		
		// 2021.03.22	X0122410 : 기존 sDESTTYPE > sDESTTYPE2
		// sToTYPE
		/*
		if (tranVo.getToMachineType()!=null && tranVo.getToMachineType().size() > 0) {
			List<String> typeList = tranVo.getToMachineType();
			sQuery.append(Common.sCRLF + Common.sAnd);
			for (int i=0;i<typeList.size();i++) {
				if (typeList.get(i).indexOf(Common.sNOTDESIGNATED) >= 0) {
					break;
				}
				
				if(i==0) {
					sQuery.append(Common.sLeftParenthesis +
						Common.sDESTTYPE + Common.sEquals +
						Common.sDoubleQuotation + typeList.get(i)+ Common.sDoubleQuotation);
				}else{
					sQuery.append(Common.sOr +
						Common.sDESTTYPE + Common.sEquals +
						Common.sDoubleQuotation + typeList.get(i)+ Common.sDoubleQuotation);
				}
			}
			sQuery.append(Common.sRightParenthesis);
		}
		*/
		StringBuilder subToMachineTypeQuery = new StringBuilder();
		if (tranVo.getToMachineType()!=null && tranVo.getToMachineType().size() > 0) {			
			subToMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sDESTTYPE2));
			for (String s : tranVo.getToMachineType()) {
				if (s.indexOf(Common.sALL) >= 0) {	
					subToMachineTypeQuery = new StringBuilder();
					break;
				} else {
					subToMachineTypeQuery.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
				}
			}

			if (subToMachineTypeQuery != null || !(subToMachineTypeQuery.toString().isEmpty())) {
				if (subToMachineTypeQuery.toString().indexOf("(") >= 0) {
					subToMachineTypeQuery.append(" )");
				}				
			}
		}
		
		// sToMACHINENAME
		if (tranVo.getToMachineName()!=null && tranVo.getToMachineName().size() > 0) {
			List<String> machineList = tranVo.getToMachineName();
			sQuery.append(Common.sAnd);
			for (int i=0;i<machineList.size();i++) {
				if (machineList.get(i).indexOf(Common.sNOTDESIGNATED) >= 0) {
					break;
				} 
				if(i==0) {
					sQuery.append(Common.sLeftParenthesis +
						Common.sDESTMACHINENAME + Common.sEquals +
						Common.sDoubleQuotation + machineList.get(i)+ Common.sDoubleQuotation);
				}else{
					sQuery.append(Common.sOr +
						Common.sDESTMACHINENAME + Common.sEquals +
						Common.sDoubleQuotation + machineList.get(i)+ Common.sDoubleQuotation);
				}
			}
			sQuery.append(Common.sRightParenthesis);
		}
		
		
		//2021. 4. 12, X0122410 : FAB 선택시 테이블 쿼리 변경		  		
		//String sTable = getTableFromFab();
		StringBuilder tQuery= new StringBuilder();		
		if (tranVo.getFab()!=null && tranVo.getFab().size() > 0) {
			List<String> fab = tranVo.getFab();
			String fabName = "";
			log.info("fab:"+tranVo.getFab());
			
			for(int i=0;i<tranVo.getFab().size();i++){
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//fabName = getTableFromFab(Common.sFAB_SITE,fab.get(i));
				fabName = getTableFromFab(tranVo.getFabSite(),fab.get(i));
				if(fabName != null && !fabName.isEmpty()) {
					if(i==0){
						tQuery.append(fabName);
					}else if(i==(tranVo.getFab().size()-1)) {
						tQuery.append(Common.sComma + fabName);
					}else{
						tQuery.append(Common.sComma + fabName);
					}
				}
			}
		}
		
//		//Machine Fab
//		//transportFab
//		StringBuilder tQueryTransportFab= new StringBuilder();
//		if (tranVo.getTransportFab()!=null && tranVo.getTransportFab().size() > 0) {
//			StringBuilder sFab = new StringBuilder();
//			sFab.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sTRANSPORTFAB));
//			
//			for (String s : tranVo.getTransportFab()) {
//				if (s.indexOf(Common.sALL) >= 0) {
//					sFab = null;
//					break;
//				} else {					
//					sFab.append(Common.getColumnFromFab(Common.sFAB_SITE, s));				
//				}
//			}
//
//			if (sFab != null && !(sFab.toString().isEmpty())) {
//				if (sFab.toString().indexOf("(") >= 0) {
//					sFab.append(" )");
//				} // search in ( ... )
//				tQueryTransportFab.append(sFab.toString());
//			}
//		}
//		//fromFab
//		StringBuilder tQueryFromFab= new StringBuilder();
//		if (tranVo.getFromFab()!=null && tranVo.getFromFab().size() > 0) {
//			StringBuilder sFab = new StringBuilder();
//			sFab.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sSOURCEFAB));
//			
//			for (String s : tranVo.getFromFab()) {
//				if (s.indexOf(Common.sALL) >= 0) {
//					sFab = null;
//					break;
//				} else {					
//					sFab.append(Common.getColumnFromFab(Common.sFAB_SITE, s));				
//				}
//			}
//
//			if (sFab != null && !(sFab.toString().isEmpty())) {
//				if (sFab.toString().indexOf("(") >= 0) {
//					sFab.append(" )");
//				} // search in ( ... )
//				tQueryFromFab.append(sFab.toString());
//			}
//		}
//		//toFab
//		StringBuilder tQueryToFab= new StringBuilder();
//		if (tranVo.getToFab()!=null && tranVo.getToFab().size() > 0) {
//			StringBuilder sFab = new StringBuilder();
//			sFab.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sDESTFAB));
//			
//			for (String s : tranVo.getToFab()) {
//				if (s.indexOf(Common.sALL) >= 0) {
//					sFab = null;
//					break;
//				} else {					
//					sFab.append(Common.getColumnFromFab(Common.sFAB_SITE, s));				
//				}
//			}
//
//			if (sFab != null && !(sFab.toString().isEmpty())) {
//				if (sFab.toString().indexOf("(") >= 0) {
//					sFab.append(" )");
//				} // search in ( ... )
//				tQueryToFab.append(sFab.toString());
//			}
//		}
				
		// 2021.03.24	X0122410 : MachineType조건 추가
//		sQuery.append(Common.sAnd + Common.sLeftParenthesis
//				+ Common.sSTATE + Common.sEquals
//				+ Common.sDoubleQuotation + Common.sCOMPLETED + Common.sDoubleQuotation + Common.sOr
//				+ Common.sSTATE + Common.sEquals
//				+ Common.sDoubleQuotation + Common.sCANCELED + Common.sDoubleQuotation + Common.sRightParenthesis
//				+ Common.sFrom + sTable
//				+ Common.sCRLF + Common.sFields + Common.sTRANS_JOBSTART + Common.sComma + Common.sTRANS_JOBEND
//				+ Common.sComma + Common.sTRANSPORTJOBID + Common.sComma + Common.sSTATE
//				+ Common.sComma + Common.sCARRIER + Common.sComma + Common.sREASON
//				+ Common.sComma + Common.sFIXEDROUTE + Common.sComma + Common.sPRIORITY
//				+ Common.sComma + Common.sLOTID + Common.sComma + Common.sBATCHID
//				+ Common.sComma + Common.sSTEPID + Common.sComma + Common.sPROCESSID
//				+ Common.sComma + Common.sDESCRIPTION+ Common.sComma + Common.sSOURCEMACHINENAME 
//				+ Common.sComma + Common.sSOURCEAREANAME + Common.sComma + Common.sSOURCEBAYNAME + Common.sComma + Common.sSOURCEUNITNAME
//				+ Common.sComma + Common.sSOURCEMACHINETYPE + Common.sComma + Common.sDESTMACHINENAME
//				+ Common.sComma + Common.sDESTAREANAME + Common.sComma + Common.sDESTBAYNAME + Common.sComma
//				+ Common.sDESTTYPE + Common.sComma + Common.sDESTUNITNAME + Common.sComma + Common.sCREATEUSER
//				+ Common.sComma + Common.sBATCHTYPE + Common.sComma + Common.sMETHOD
//				);
		if (tranVo.getState()!=null && tranVo.getState().size() > 0 && tranVo.getState().get(0).contains(Common.sALL)) {
		} else {
			sQuery.append(Common.sAnd + Common.sLeftParenthesis
					+ Common.sSTATE + Common.sEquals
					+ Common.sDoubleQuotation + Common.sCOMPLETED + Common.sDoubleQuotation + Common.sOr
					+ Common.sSTATE + Common.sEquals
					+ Common.sDoubleQuotation + Common.sCANCELED + Common.sDoubleQuotation + Common.sRightParenthesis
					+ Common.sFrom + tQuery.toString());
		} 
		
		//Transport/From/To Fab
//		sQuery.append(Common.sCRLF + tQueryTransportFab.toString());
//		sQuery.append(Common.sCRLF + tQueryFromFab.toString());
//		sQuery.append(Common.sCRLF + tQueryToFab.toString());
		//MachineType
		sQuery.append(Common.sCRLF + subTransportMachineTypeQuery.toString());
		sQuery.append(Common.sCRLF + subFromMachineTypeQuery.toString());
		sQuery.append(Common.sCRLF + subToMachineTypeQuery.toString());
		sQuery.append(Common.sCRLF + Common.sFields + Common.sTRANS_JOBSTART + Common.sComma + Common.sTRANS_JOBEND
				+ Common.sComma + Common.sTRANSPORTJOBID + Common.sComma + Common.sSTATE
				+ Common.sComma + Common.sCARRIER + Common.sComma + Common.sREASON
				+ Common.sComma + Common.sFIXEDROUTE + Common.sComma + Common.sPRIORITY
				+ Common.sComma + Common.sLOTID + Common.sComma + Common.sBATCHID
				+ Common.sComma + Common.sSTEPID + Common.sComma + Common.sPROCESSID
				+ Common.sComma + Common.sDESCRIPTION+ Common.sComma + Common.sSOURCEMACHINENAME 
				+ Common.sComma + Common.sSOURCEAREANAME + Common.sComma + Common.sSOURCEBAYNAME + Common.sComma + Common.sSOURCEUNITNAME
				+ Common.sComma + Common.sSOURCEMACHINETYPE + Common.sComma + Common.sSOURCEMACHINETYPE2 + Common.sComma + Common.sDESTMACHINENAME
				+ Common.sComma + Common.sDESTAREANAME + Common.sComma + Common.sDESTBAYNAME + Common.sComma
				+ Common.sDESTTYPE + Common.sComma + Common.sDESTTYPE2 + Common.sComma + Common.sDESTUNITNAME + Common.sComma + Common.sCREATEUSER
				+ Common.sComma + Common.sBATCHTYPE + Common.sComma + Common.sMETHOD
				);
		return sQuery.toString();
	}

	public String getTranJobHistoryDetailQueryParser(TranVo tranVo){
		if (tranVo == null) {
			return null;
		} // null exception
		StringBuilder sQuery = new StringBuilder();
		SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMddHHmmss");
		try{
			Date fromTime = sdf.parse(tranVo.getFrom());
			Date toTime = sdf.parse(tranVo.getTo());
			long diff = toTime.getTime() - fromTime.getTime();
			//log.info("diff:"+diff);
			if(diff>3600000){
				/*sQuery.append(String.format(Common.sFulltext_From_TRAN, 
				tranVo.getFrom(), tranVo.getTo(), 
				(Common.sLeftParenthesis +Common.sLeftParenthesis +Common.sLeftParenthesis+ Common.sMETHOD + Common.sEquals
						+ Common.sDoubleQuotation+Common.METHOD_INFO_CREATE_TRANSPORT_JOB_HISTORY+Common.sDoubleQuotation + Common.sRightParenthesis
						+ Common.sOr + Common.sLeftParenthesis+ Common.sMETHOD + Common.sEquals+Common.sDoubleQuotation
						+ Common.METHOD_INFO_CREATE_TRANSPORT_COMMAND_HISTORY + Common.sDoubleQuotation 
						+ Common.sRightParenthesis + Common.sRightParenthesis
						+ Common.sAnd + Common.sLeftParenthesis + Common.sTRANSPORTJOBID + Common.sEquals  
						+ Common.sDoubleQuotation + tranVo.getTransportJobId() + Common.sDoubleQuotation
						+ Common.sRightParenthesis) + Common.sRightParenthesis));*/
				// 200819 hgJeon 기존쿼리 프로시저로 수정
				sQuery.append(Common.sProc + String.format(Common.sFulltext_From_TRAN, 
						Common.sDoubleQuotation + tranVo.getFrom() + Common.sDoubleQuotation,
						Common.sDoubleQuotation + tranVo.getTo() + Common.sDoubleQuotation, 
						Common.sDoubleQuotation + tranVo.getTransportJobId() + Common.sDoubleQuotation));
			}else{				
				// 200818 hgJeon 기존 쿼리 프로시저로 수정
				sQuery.append(Common.sProc +String.format(Common.sTable_From_TRAN, 
						Common.sDoubleQuotation + tranVo.getFrom() + Common.sDoubleQuotation,
						Common.sDoubleQuotation + tranVo.getTo() + Common.sDoubleQuotation, 
						Common.sDoubleQuotation + tranVo.getTransportJobId() + Common.sDoubleQuotation));
			}
		}catch (Exception ignore){}
		return sQuery.toString();
	}
	
	/*public String getTranCmdHistoryQueryParser(TranVo tranVo){ // 사용안함 / 2017-07-18일 부 
		if (tranVo == null) {
			return null;
		} // null exception
		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(Common.sFulltext_From_TRAN, 
				tranVo.getFrom(), tranVo.getTo(), 
				(Common.sLeftParenthesis + Common.sMETHOD + Common.sEquals
				+ Common.sDoubleQuotation+"createTransportCommandHistory"+Common.sDoubleQuotation + Common.sRightParenthesis
				+ Common.sAnd + Common.sLeftParenthesis + Common.sTRANSPORTJOBID + Common.sEquals  
				+ Common.sDoubleQuotation + tranVo.getTransportJobId() + Common.sDoubleQuotation
				+ Common.sRightParenthesis)));
		
		return sQuery.toString();
	}*/
	
	// 200519 hgJeon FAB 별 table 선택 메소드 추가
//	private String getTableFromFab() {	
//		
//		String sFAB = Common.sFAB_SITE;
//		
//		switch(sFAB) {
//			case "M14" : {
//				return Common.sTS_TRANSPORT;
//			}
//			case "M15" : {
//				return Common.sTS_TRANSPORT_M15;			
//			}
//			case "M11" : {
//				return Common.sTS_TRANSPORT_M11 + Common.sComma + Common.sTS_TRANSPORT_M11B;
//			}
//			case "C2" : {
//				return Common.sTS_TRANSPORT_C2 + Common.sComma + Common.sTS_TRANSPORT_C2F;
//			}
//			case "IC" : {
//				return Common.sTS_TRANSPORT_M14A + Common.sComma + Common.sTS_TRANSPORT_M16;
//			}
//			default : return null;
//		}
//	}
	
	private String getTableFromFab(String fabSite, String fab) {
		
		switch(fabSite) {
			case Common.sFABSITE_M14 : {
				return Common.sTS_TRANSPORT_M14A;
			}
			case Common.sFABSITE_M15 : {
				if(fab.equals(Common.sFAB_M15A)) {
					return Common.sTS_TRANSPORT_M15A;
				}
				else if(fab.equals(Common.sFAB_M15B)){
					return Common.sTS_TRANSPORT_M15B;
				}
			}
			case Common.sFABSITE_M11 : {
				if(fab.equals(Common.sFAB_M11A)) {
					return Common.sTS_TRANSPORT_M11A;
				}
				else if(fab.equals(Common.sFAB_M11B)){
					return Common.sTS_TRANSPORT_M11B;
				}
			}
			case Common.sFABSITE_C2 : {				
				if(fab.equals(Common.sFAB_C2)) {
					return Common.sTS_TRANSPORT_C2;
				}
				else if(fab.equals(Common.sFAB_C2F)){
					return Common.sTS_TRANSPORT_C2F;
				}
			}
			case Common.sFABSITE_IC : {
				if(fab.equals(Common.sFAB_M14A)) {
					return Common.sTS_TRANSPORT_M14A; 
				}else if(fab.equals(Common.sFAB_M14B)){
					return Common.sTS_TRANSPORT_M14B; 
				}else if(fab.equals(Common.sFAB_M16A)){
					return Common.sTS_TRANSPORT_M16A;
				}else if(fab.equals(Common.sFAB_M16B)){
					return Common.sTS_TRANSPORT_M16B;
				}
			}
			default : return null;
		}
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(TranJobFailVo jobfailVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}

	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getReasonList(String fabSite) throws Exception {
		List<Map> selectList = null;
		String reasonList = "memlookup name=reasonList | fields REASON | sort REASON";
		selectList = Client.dbExecuteQuery(fabSite, reasonList);
		return selectList;
	}

}
