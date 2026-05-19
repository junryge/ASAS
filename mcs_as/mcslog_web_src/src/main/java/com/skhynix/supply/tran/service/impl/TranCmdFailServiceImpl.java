package com.skhynix.supply.tran.service.impl;

import java.util.List;
import java.util.Map;

import javax.annotation.Resource;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.stereotype.Service;

import com.skhynix.supply.common.Common;
import com.skhynix.supply.tot.service.TotalService;
//import com.skhynix.supply.common.MachineVo;
//import com.skhynix.supply.tot.service.impl.TotalServiceImpl;
import com.skhynix.supply.tran.dao.TranDAO;
import com.skhynix.supply.tran.service.TranService;
import com.skhynix.supply.tran.vo.TranCmdFailVo;
import com.skhynix.supply.tran.vo.TranJobFailVo;
import com.skhynix.supply.tran.vo.TranVo;

@Service("tranCmdFailService")
public class TranCmdFailServiceImpl implements TranService {
	protected Log log = LogFactory.getLog(TranCmdFailServiceImpl.class);
	@Resource(name = "tranDAO")
	TranDAO Client;
	
	@Resource(name = "totalService")
	private TotalService totService;
	
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(TranCmdFailVo cmdFailVo) throws Exception {
		List<Map> dataList = null; 
		long offset 	= (Long.parseLong(cmdFailVo.getPageNum()) - 1) * Long.parseLong(cmdFailVo.getRowNum());
		int   limit 	= Integer.parseInt(cmdFailVo.getRowNum());
		String resultQuery = getCmdFailQueryParser(cmdFailVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			resultQuery += Common.sPipeLine + "limit " + offset + Common.sSpace +  limit;	//결과 출력에 대해 limit을 적용한 쿼리 
			resultQuery += Common.sPipeLine + Common.sSort + Common.s_TIME;			//결과 출력에 대해 time sort를 적용한 쿼리
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(cmdFailVo.getFabSite(), resultQuery);
		}
		return dataList;
	}

	public String getCmdFailQueryParser(TranCmdFailVo cmdFailVo){
		if (cmdFailVo == null) {
			return null;
		} // null exception
		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(Common.sFulltext_Arg0_key1, 
				cmdFailVo.getFrom(), cmdFailVo.getTo(), 
				(Common.sLeftParenthesis + Common.sMETHOD + Common.sEquals
				+ Common.sDoubleQuotation + "createTransportCommandFailHistory"
				+ Common.sDoubleQuotation + Common.sRightParenthesis)));
				
		//Carrier
		if(cmdFailVo.getCarrier()!=null &&!cmdFailVo.getCarrier().equals("")){
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sCARRIER + Common.sEquals
					+ Common.sDoubleQuotation + cmdFailVo.getCarrier() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		//TransportJobId
		if(cmdFailVo.getTransportCmdId()!=null &&!cmdFailVo.getTransportCmdId().equals("")){
			System.out.println("getTransportCommandId : " + cmdFailVo.getTransportCmdId());
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sTRANSPORTCOMMANDID + Common.sEquals
					+ Common.sDoubleQuotation + cmdFailVo.getTransportCmdId() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		//Reason
		if(cmdFailVo.getReason()!=null && cmdFailVo.getReason().size() > 0){
			if(cmdFailVo.getReason().size()==1){
				sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
						+ Common.sREASON + Common.sEquals
						+ Common.sDoubleQuotation + cmdFailVo.getReason().get(0) 
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}else{
				for(int i=0;i<cmdFailVo.getReason().size();i++){
					if(i==0){
						sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis + Common.sLeftParenthesis
								+ Common.sREASON + Common.sEquals
								+ Common.sDoubleQuotation + cmdFailVo.getReason().get(i) 
								+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sOr);
					}else if(i==cmdFailVo.getReason().size()-1){
						sQuery.append(Common.sLeftParenthesis
								+ Common.sREASON + Common.sEquals
								+ Common.sDoubleQuotation + cmdFailVo.getReason().get(i) 
								+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis);
					}else{
						sQuery.append(Common.sLeftParenthesis
								+ Common.sREASON + Common.sEquals
								+ Common.sDoubleQuotation + cmdFailVo.getReason().get(i) 
								+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sOr);
					}
				}
			}
		}
		
		// sTransportAREANAME
		if (cmdFailVo.getTransportAreaName()!=null && cmdFailVo.getTransportAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sTRANSPORTAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + cmdFailVo.getTransportAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 
		// sTransportBAYNAME
		if (cmdFailVo.getTransportBayName()!=null && cmdFailVo.getTransportBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sTRANSPORTBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + cmdFailVo.getTransportBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}
		
		// sFromAREANAME
		if (cmdFailVo.getFromAreaName()!=null && cmdFailVo.getFromAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sSOURCEAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + cmdFailVo.getFromAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 
		// sFromBAYNAME
		if (cmdFailVo.getFromBayName()!=null && cmdFailVo.getFromBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sSOURCEBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + cmdFailVo.getFromBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// sToAREANAME
		if (cmdFailVo.getToAreaName()!=null && cmdFailVo.getToAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sDESTAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + cmdFailVo.getToAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 

		// sToBAYNAME
		if (cmdFailVo.getToBayName()!=null && cmdFailVo.getToBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sDESTBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + cmdFailVo.getToBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// Machine Name -- Single/Multi Filter
		//Transport MachineType
		StringBuilder subTransportMachineTypeQuery = new StringBuilder();
		if (cmdFailVo.getTransportMachineType()!=null && cmdFailVo.getTransportMachineType().size() > 0) {			
			subTransportMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sTRANSPORTTYPE2));
			for (String s : cmdFailVo.getTransportMachineType()) {
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
		if (cmdFailVo.getTransportMachineName()!=null && cmdFailVo.getTransportMachineName().size() > 0) {
			List<String> machineList = cmdFailVo.getTransportMachineName();
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
		if (cmdFailVo.getFromMachineType()!=null && cmdFailVo.getFromMachineType().size() > 0) {
			List<String> typeList = cmdFailVo.getFromMachineType();
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
		if (cmdFailVo.getFromMachineType()!=null && cmdFailVo.getFromMachineType().size() > 0) {			
			subFromMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sSOURCEMACHINETYPE2));
			for (String s : cmdFailVo.getFromMachineType()) {
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
		if (cmdFailVo.getFromMachineName()!=null && cmdFailVo.getFromMachineName().size() > 0) {
			List<String> machineList = cmdFailVo.getFromMachineName();
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
		if (cmdFailVo.getToMachineType()!=null && cmdFailVo.getToMachineType().size() > 0) {
			List<String> typeList = cmdFailVo.getToMachineType();
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
		if (cmdFailVo.getToMachineType()!=null && cmdFailVo.getToMachineType().size() > 0) {			
			subToMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sDESTTYPE2));
			for (String s : cmdFailVo.getToMachineType()) {
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
		if (cmdFailVo.getToMachineName()!=null && cmdFailVo.getToMachineName().size() > 0) {
			List<String> machineList = cmdFailVo.getToMachineName();
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
		if (cmdFailVo.getFab()!=null && cmdFailVo.getFab().size() > 0) {
			List<String> fab = cmdFailVo.getFab();
			String fabName = "";
			log.info("fab:"+cmdFailVo.getFab());
			
			for(int i=0;i<cmdFailVo.getFab().size();i++){
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//fabName = getTableFromFab(Common.sFAB_SITE,fab.get(i));
				fabName = getTableFromFab(cmdFailVo.getFabSite(),fab.get(i));
				if(fabName != null && !fabName.isEmpty()) {
					if(i==0){
						tQuery.append(fabName);
					}else if(i==(cmdFailVo.getFab().size()-1)) {
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
//		if (cmdFailVo.getTransportFab()!=null && cmdFailVo.getTransportFab().size() > 0) {
//			StringBuilder sFab = new StringBuilder();
//			sFab.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sTRANSPORTFAB));
//			
//			for (String s : cmdFailVo.getTransportFab()) {
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
//		if (cmdFailVo.getFromFab()!=null && cmdFailVo.getFromFab().size() > 0) {
//			StringBuilder sFab = new StringBuilder();
//			sFab.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sSOURCEFAB));
//			
//			for (String s : cmdFailVo.getFromFab()) {
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
//		if (cmdFailVo.getToFab()!=null && cmdFailVo.getToFab().size() > 0) {
//			StringBuilder sFab = new StringBuilder();
//			sFab.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sDESTFAB));
//			
//			for (String s : cmdFailVo.getToFab()) {
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
//		sQuery.append(Common.sFrom + sTable
//				+ Common.sCRLF + Common.sFields + Common.sCARRIER + Common.sComma + Common.sTRANSPORTJOBID + Common.sComma
//				+ Common.sTRANSPORTCOMMANDID + Common.sComma + Common.sSOURCEMACHINENAME + Common.sComma 
//				+ Common.sSOURCEAREANAME + Common.sComma + Common.sSOURCEBAYNAME + Common.sComma
//				// 2021.03.22	X0122410 : 기존 sSOURCEMACHINETYPE > sSOURCEMACHINETYPE2
//				// + Common.sSOURCEMACHINETYPE + Common.sComma + Common.sDESTMACHINENAME + Common.sComma 
//				+ Common.sSOURCEMACHINETYPE2 + Common.sComma + Common.sDESTMACHINENAME + Common.sComma
//				+ Common.sDESTAREANAME + Common.sComma + Common.sDESTBAYNAME + Common.sComma
//				// 2021.03.22	X0122410 : 기존 sDESTTYPE > sDESTTYPE2
//				// + Common.sDESTTYPE + Common.sComma + Common.sDESTUNITNAME + Common.sComma
//				+ Common.sDESTTYPE2 + Common.sComma + Common.sDESTUNITNAME + Common.sComma
//				+ Common.sREASON + Common.sComma + Common.sPRIORITY + Common.sComma + Common.sDESCRIPTION
//				+ Common.sComma + Common.sTIME_EX + Common.sComma + Common.sSOURCEUNITNAME);		
//		sQuery.append(Common.sFrom + sTable);
		sQuery.append(Common.sFrom + tQuery.toString());
		//Transport/From/To Fab
//		sQuery.append(Common.sCRLF + tQueryTransportFab.toString());
//		sQuery.append(Common.sCRLF + tQueryFromFab.toString());
//		sQuery.append(Common.sCRLF + tQueryToFab.toString());
		//MachineType
		sQuery.append(Common.sCRLF + subTransportMachineTypeQuery.toString());
		sQuery.append(Common.sCRLF + subFromMachineTypeQuery.toString());
		sQuery.append(Common.sCRLF + subToMachineTypeQuery.toString());
		sQuery.append(Common.sCRLF
				+ Common.sFields + Common.sCARRIER + Common.sComma + Common.sTRANSPORTJOBID + Common.sComma
				+ Common.sTRANSPORTCOMMANDID + Common.sComma + Common.sSOURCEMACHINENAME + Common.sComma 
				+ Common.sSOURCEAREANAME + Common.sComma + Common.sSOURCEBAYNAME + Common.sComma
				+ Common.sSOURCEMACHINETYPE + Common.sComma + Common.sSOURCEMACHINETYPE2 + Common.sComma + Common.sDESTMACHINENAME + Common.sComma
				+ Common.sDESTAREANAME + Common.sComma + Common.sDESTBAYNAME + Common.sComma
				+ Common.sDESTTYPE + Common.sComma + Common.sDESTTYPE2 + Common.sComma + Common.sDESTUNITNAME + Common.sComma
				+ Common.sREASON + Common.sComma + Common.sPRIORITY + Common.sComma + Common.sDESCRIPTION
				+ Common.sComma + Common.sTIME_EX + Common.sComma + Common.sSOURCEUNITNAME
			);
		
		return sQuery.toString();
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(TranVo tranVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}

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
	public List<Map> getTranJobHistoryDetail(TranVo tranVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
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
		// TODO Auto-generated method stub
		return null;
	}
}
