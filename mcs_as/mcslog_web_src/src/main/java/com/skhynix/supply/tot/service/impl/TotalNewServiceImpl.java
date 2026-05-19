package com.skhynix.supply.tot.service.impl;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import javax.annotation.Resource;

import org.springframework.stereotype.Service;

import com.skhynix.supply.common.Common;
import com.skhynix.supply.common.MachineVo;
import com.skhynix.supply.tot.dao.TotalDAO;
import com.skhynix.supply.tot.service.TotalService;
import com.skhynix.supply.tot.vo.TotalNewVo;
import com.skhynix.supply.tot.vo.TotalVo;

/**
 * @Package Name : com.skhynix.tot.service.impl
 * @FileName : TotalNewServiceImpl.java
 * @작성일 : 2017. 3. 16.
 * @작성자 : 최명수
 * @프로그램 설명 : 신규로그 조회 서비스
 */
@Service("totalNewService")
public class TotalNewServiceImpl implements TotalService {
	
	@Resource(name = "totalDAO")
	TotalDAO Client;
	
	/**
	 * @Method Name : getDataList
	 * @작성일 : 2017. 3. 16.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 신규로그 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(TotalNewVo totNewVo) throws Exception {
		List<Map> dataList = null; 
		long offset 	= (Long.parseLong(totNewVo.getPageNum()) - 1) * Long.parseLong(totNewVo.getRowNum());
		int   limit 	= Integer.parseInt(totNewVo.getRowNum());
		String resultQuery = "";
		if(totNewVo.getCarrier()!=null && !totNewVo.getCarrier().equals("")&&!totNewVo.getCarrier().isEmpty()){
			resultQuery = getCompletedCarrierListQueryByCarrier(totNewVo);
		}else{
			resultQuery = getCompletedCarrierListQuery(totNewVo);
		}
		
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			resultQuery += Common.sPipeLine + "limit " + offset + " " +  limit;		//결과 출력에 대해 limit을 적용한 쿼리 
			resultQuery += Common.sPipeLine + Common.sSort + Common.s_TIME;			//결과 출력에 대해 time sort를 적용한 쿼리
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(totNewVo.getFabSite(), resultQuery);
		}
		return dataList;
	}
	

	/**
	 * @Method Name : getDetailDataList
	 * @작성일 : 2017. 3. 16.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 신규로그 디테일조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDetailDataList(String fabSite, String addQuery) throws Exception {
		List<Map> dataList = null; 
		if (addQuery != null && !(addQuery.isEmpty())) {
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(fabSite, addQuery);
		}
		return dataList;
	}
	
	/**
	 * @Method Name : getSelectList
	 * @작성일 : 2017. 3. 16.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 신규로그 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@Override
	public List<Map> getSelectList(String fabSite) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}
	
	/**
	 * @Method Name : getBayNameList
	 * @작성일 : 2017. 3. 16.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 신규로그 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@Override
	public List<Map> getBayNameList(String fabSite) throws Exception {
		List<Map> selectList = null;
		// 2021. 04. 01. X0122410 대상 테이블 변경	machine_info > machine_list
//		String bayNameQuery = "memlookup name=machine_info | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search BAYNAME !="
//				+Common.sDoubleQuotation+Common.sDoubleQuotation;
		String bayNameQuery = "memlookup name=machine_list | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search BAYNAME !="
				+Common.sDoubleQuotation+Common.sDoubleQuotation;
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		selectList = Client.dbExecuteQuery(fabSite, bayNameQuery);
		return selectList;
	}
	
	/**
	 * @Method Name : getMachineNameList
	 * @작성일 : 2017. 3. 16.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 신규로그 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getMachineNameList(MachineVo machineVo) throws Exception {
//		if (machineVo == null) {
//			return null;
//		} // null exception
//		List<Map> machineList = null; 
//		String resultQuery = getMachineQueryParser(machineVo);
//		if (resultQuery != null && !(resultQuery.isEmpty())) {
//			machineList = Client.dbExecuteQuery(resultQuery);
//		}
//		return machineList;
		return null;
	}
	/**
	 * @Method Name : getMachineNameListMachineTypeNotNull
	 * @작성일 : 2022. 6. 8.
	 * @작성자 : 강병민
	 * @param :
	 * @Method 설명 : 신규로그 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getMachineNameListMachineTypeNotNull(MachineVo machineVo) throws Exception {
		return null;
	}
	/**
	 * @Method Name : getCommMsgNameList
	 * @작성일 : 2017. 3. 16.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 신규로그 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@Override
	public List<Map> getCommMsgNameList(String fabSite) throws Exception {
		List<Map> selectList = null;
		String commMsgNameQuery = "memlookup name=comm_msg_name | sort COMM_MSG";
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		selectList = Client.dbExecuteQuery(fabSite, commMsgNameQuery);
		return selectList;
	}
	
	/**
	 * @Method Name : getMessageNameList
	 * @작성일 : 2017. 3. 16.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 신규로그 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@Override
	public List<Map> getMessageNameList(String fabSite) throws Exception {
		List<Map> selectList = null;
		String messageNameQuery = "memlookup name=message_name | sort MESSAGE";
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		selectList = Client.dbExecuteQuery(fabSite, messageNameQuery);
		return selectList;
	}
	
	/**
	 * @Method Name : getCompletedCarrierListQueryByCarrier
	 * @작성일 : 2017. 3. 16.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : 신규로그 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	
	public String getCompletedCarrierListQueryByCarrier(TotalNewVo totNewVo){
		if (totNewVo == null) {
			return null;
		} // null exception
		StringBuilder sQuery = new StringBuilder();
		
		// 2021.03.22	X0122410 : MACHINETYPE조건 추가
		// sMACHINETYPE		
		StringBuilder subMachineTypeQuery = new StringBuilder();
		if (totNewVo.getMachineType()!=null && totNewVo.getMachineType().size() > 0) {			
			subMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sMACHINETYPE));
			for (String s : totNewVo.getMachineType()) {
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
		
		sQuery.append(Common.sProc + String.format(Common.sCOMPLETED_CARRIER_FROM_TO_CARRIER, 
				Common.sDoubleQuotation+totNewVo.getFrom()+Common.sDoubleQuotation, 
				Common.sDoubleQuotation+totNewVo.getTo()+Common.sDoubleQuotation,
				Common.sDoubleQuotation+totNewVo.getCarrier()+Common.sDoubleQuotation));
		
		// 2021.03.24	X0122410 : MachineType조건 추가
		sQuery.append(subMachineTypeQuery.toString());
				
		return sQuery.toString();
	}
	
	public String getCompletedCarrierListQuery(TotalNewVo totNewVo){
		if (totNewVo == null) {
			return null;
		} // null exception
		StringBuilder sQuery = new StringBuilder();
		
		// 2021.03.22	X0122410 : MACHINETYPE조건 추가
		// sMACHINETYPE		
		StringBuilder subMachineTypeQuery = new StringBuilder();
		if (totNewVo.getMachineType()!=null && totNewVo.getMachineType().size() > 0) {			
			subMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sMACHINETYPE));
			for (String s : totNewVo.getMachineType()) {
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
		
		sQuery.append(Common.sProc + String.format(Common.sCOMPLETED_CARRIER_FROM_TO, 
				Common.sDoubleQuotation+totNewVo.getFrom()+Common.sDoubleQuotation, 
				Common.sDoubleQuotation+totNewVo.getTo()+Common.sDoubleQuotation));
		
		// 2021.03.24	X0122410 : MachineType조건 추가
		sQuery.append(subMachineTypeQuery.toString());
		
		return sQuery.toString();
	}
	
	@SuppressWarnings("null")
	public String getQueryParser(TotalNewVo totNewVo) {
		if (totNewVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();

		// 1.Area Name
		if (totNewVo.getAreaName()!=null && totNewVo.getAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sAREANAME,
					Common.sDoubleQuotation + totNewVo.getAreaName() + Common.sDoubleQuotation));
		}

		// 2.Bay Name
		if (totNewVo.getBayName() != null && totNewVo.getBayName().indexOf(Common.sALL) >= 0) {
		} else {
			sQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sBAYNAME,
					Common.sDoubleQuotation + totNewVo.getBayName() + Common.sDoubleQuotation));
		}

		// 3. Type
		if (totNewVo.getMachineType()!=null && totNewVo.getMachineType().size() > 0) {
			StringBuilder sMachine = new StringBuilder();
			sMachine.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sTYPE));

			for (String s : totNewVo.getMachineType()) {
				if (s.indexOf(Common.sALL) >= 0) {
					sMachine = null;
					break;
				} else {
					sMachine.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
				}
			}

			if (sMachine != null && !(sMachine.toString().isEmpty())) {
				if (sMachine.toString().indexOf("(") >= 0) {
					sMachine.append(" )");
				} // search in ( ... )
				sQuery.append(sMachine.toString());
			}
		}

		// 4.Machine Name -- Single/Multi Filter
		if (totNewVo.getMachineName()!=null && totNewVo.getMachineName().size() > 0) {
			StringBuilder sMachineNM = new StringBuilder();
			sMachineNM.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sMACHINENAME));

			for (String s : totNewVo.getMachineName()) {
				if (s.indexOf(Common.sNOTDESIGNATED) >= 0) {
					sMachineNM = null;
					break;
				} else {
					sMachineNM.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
				}
			}

			if (sMachineNM != null && !(sMachineNM.toString().isEmpty())) {
				if (sMachineNM.toString().indexOf("(") >= 0) {
					sMachineNM.append(" )");
				} // search in ( ... )
				sQuery.append(sMachineNM.toString());
			}
		}else{
			// 1.Area Name
			if (totNewVo.getAreaName()!= null && totNewVo.getAreaName().indexOf(Common.sALL) >= 0) {
			} else {
				sQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sAREANAME,
						Common.sDoubleQuotation + totNewVo.getAreaName() + Common.sDoubleQuotation));
			} 

			// 2.Bay Name
			if (totNewVo.getBayName()!=null && totNewVo.getBayName().indexOf(Common.sALL) >= 0) {
			} else {
				sQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sBAYNAME,
						Common.sDoubleQuotation + totNewVo.getBayName() + Common.sDoubleQuotation));
			}

			// 3. Type
			if (totNewVo.getMachineType()!= null && totNewVo.getMachineType().size() > 0) {
				StringBuilder sMachine = new StringBuilder();
				sMachine.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sTYPE));

				for (String s : totNewVo.getMachineType()) {
					if (s.indexOf(Common.sALL) >= 0) {
						sMachine = null;
						break;
					} else {
						sMachine.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
					}
				}

				if (sMachine != null && !(sMachine.toString().isEmpty())) {
					if (sMachine.toString().indexOf("(") >= 0) {
						sMachine.append(" )");
					} // search in ( ... )
					sQuery.append(sMachine.toString());
				}
			}
		}

		// 5.Add LEVEL
		if (totNewVo.getLevel()!=null && totNewVo.getLevel().size() > 0) {
			StringBuilder sLevel = new StringBuilder();
			sLevel.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sLEVEL));

			for (String s : totNewVo.getLevel()) {
				if (s.indexOf(Common.sALL) >= 0) {
					sLevel = null;
					break;
				} else {
					sLevel.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
				}
			}

			if (sLevel != null || !(sLevel.toString().isEmpty())) {
				if (sLevel.toString().indexOf("(") >= 0) {
					sLevel.append(" )");
				} // search in ( ... )
				sQuery.append(sLevel.toString());
			}
		}

		// 6.Condition & Filter --> AND , OR
		ArrayList<String> sCondition = new ArrayList<String>();
		// 6-1
		if (totNewVo.getProcess() != null && !totNewVo.getProcess().equals("")) {
			sCondition.add(Common.sCRLF + Common.sPROCESSNAME + Common.sEquals + Common.sDoubleQuotation
					+ totNewVo.getProcess() + Common.sDoubleQuotation);
		}

		// 6-2
		if (totNewVo.getThread() != null && !totNewVo.getThread().equals("")) {
			sCondition.add(Common.sCRLF + Common.sTHREADNAME + Common.sEquals + Common.sDoubleQuotation
					+ totNewVo.getThread() + Common.sDoubleQuotation);
		}

		// 6-3
		if (totNewVo.getTransactionId() != null && !totNewVo.getTransactionId().equals("")) {
			sCondition.add(Common.sCRLF + Common.sTRANSACTIONID + Common.sEquals + Common.sDoubleQuotation
					+ totNewVo.getTransactionId() + Common.sDoubleQuotation);
		}

		// 6-4
		if (totNewVo.getMessageName() != null && !totNewVo.getMessageName().equals("")) {
			sCondition.add(Common.sCRLF + Common.sMESSAGENAME + Common.sEquals + Common.sDoubleQuotation
					+ totNewVo.getMessageName() + Common.sDoubleQuotation);
		}

		// 6-7
		if (totNewVo.getCarrier() != null && !totNewVo.getCarrier().equals("")) {
			sCondition.add(Common.sCRLF + Common.sCARRIER + Common.sEquals + Common.sDoubleQuotation
					+ totNewVo.getCarrier() + Common.sDoubleQuotation);
		}

		// 6-8
		if (totNewVo.getCommandId() != null && !totNewVo.getCommandId().equals("")) {
			sCondition.add(Common.sCRLF + Common.sCOMMANDID + Common.sEquals + Common.sDoubleQuotation
					+ totNewVo.getCommandId() + Common.sDoubleQuotation);
		}

		// 6-9
		if (totNewVo.getUnit() != null && !totNewVo.getUnit().equals("")) {
			sCondition.add(Common.sCRLF + Common.sUNIT + Common.sEquals + Common.sDoubleQuotation + totNewVo.getUnit()
					+ Common.sDoubleQuotation);
		}


		// 6-1 ~ 10 Add Filter : AND , OR
		if (sCondition.size() > 0) {
			if (sCondition.size() == 1) {
				sQuery.append(Common.sSearch_0 + sCondition.get(0).toString());

			} else {
				for (int i = 0; i < sCondition.size(); i++) {
					if (i == 0) {
						sQuery.append(Common.sSearch_0 + sCondition.get(0).toString() + Common.sSpace
								+ totNewVo.getSearchOption().toLowerCase());
					} else if (i == sCondition.size() - 1) {
						sQuery.append(sCondition.get(i).toString());
					} else {
						sQuery.append(Common.sSpace + sCondition.get(i).toString() + Common.sSpace
								+ totNewVo.getSearchOption().toLowerCase());
					}
				}
			}
		}
		return sQuery.toString();
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(TotalVo totVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getMachineNameListByType(TotalVo totVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}
	
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getMachineNameListByTypeMachineTypeNotNull(TotalVo totVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}

	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getMachineNameList(String fabSite) throws Exception {
//		// 2021. 04. 01. X0122410 대상 테이블 변경	machine_info > machine_list
//		//String sQuery = "memlookup name=machine_info | fields MACHINENAME | sort MACHINENAME";
//		String sQuery = "memlookup name=machine_list | fields MACHINENAME | sort MACHINENAME";
//		List<Map> machineList =  Client.dbExecuteQuery(sQuery);
//		
//		return machineList;
		return null;
	}

	// 200827 hgJeon 사용안함 주석처리
	/*@Override
	public List<Map> getXmlList(TotalVo totNewVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	public List getXmlListGroup(TotalVo param) {
		// TODO Auto-generated method stub
		return null;
	}*/


	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getOperationNameList(String fabSite) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}


	@Override
	public void getTotalLogListStop() throws Exception {
		// TODO Auto-generated method stub
		
	}


	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getAreaNameList(String fabSite) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}


	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getBayFromAreaList(MachineVo machineVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}


	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getAreaFromFabList(MachineVo machineVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}
	
	/**
	 * @Method Name  : getMachineTypeFromFab
	 * @작성일     : 2021. 3. 31. 
	 * @작성자     : X0122410
	 * @param    : 
	 * @Method 설명 : machine_list lookup table 조회
	 * @param 
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getMachineTypeFromFab(MachineVo machineVo) throws Exception {
		StringBuilder sQuery = new StringBuilder();
		sQuery.append("memlookup name=machine_list");

		// FAB 선택 machineVo SecsFab 사용
		if (machineVo.getSelectFab()!=null && machineVo.getSelectFab().size() > 0) {
			StringBuilder sFab = new StringBuilder();
			//SHOPNAME == FAB
			sFab.append(Common.sCRLF + String.format(Common.sSearch_in, "SHOPNAME"));
			
			for (String s : machineVo.getSelectFab()) {
				if (s.indexOf(Common.sALL) >= 0) {
					sFab = null;
					break;
				} else {
					//2022. 6.15. X0122410 : fab site 접근로직 변경 
					//sFab.append(Common.getColumnFromFab(Common.sFAB_SITE, s));
					sFab.append(Common.getColumnFromFab(machineVo.getFabSite(), s));
				}
			}

			if (sFab != null && !(sFab.toString().isEmpty())) {
				if (sFab.toString().indexOf("(") >= 0) {
					sFab.append(" )");
				} // search in ( ... )
				sQuery.append(sFab.toString());
			}
		}
		
		//Sort
		sQuery.append(" | stats count by TYPE | sort TYPE");
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		return Client.dbExecuteQuery(machineVo.getFabSite(), sQuery.toString());
	}
}