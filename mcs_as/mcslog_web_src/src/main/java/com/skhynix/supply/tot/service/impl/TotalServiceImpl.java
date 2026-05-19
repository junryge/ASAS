package com.skhynix.supply.tot.service.impl;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Map;

import javax.annotation.Resource;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.stereotype.Service;

import com.skhynix.supply.common.Common;
import com.skhynix.supply.common.MachineVo;
//import com.skhynix.supply.common.McslogCommon;
import com.skhynix.supply.tot.dao.TotalDAO;
import com.skhynix.supply.tot.service.TotalService;
import com.skhynix.supply.tot.vo.TotalNewVo;
import com.skhynix.supply.tot.vo.TotalVo;

/**
 * @Package Name : com.skhynix.supply.sam.service
 * @FileName : SampleServiceImpl.java
 * @작성일 : 2017. 3. 9.
 * @작성자 : mwlee
 * @프로그램 설명 : 샘플페이지 호출 서비스
 */
@Service("totalService")
public class TotalServiceImpl implements TotalService {
	protected Log log = LogFactory.getLog(TotalServiceImpl.class);
	@Resource(name = "totalDAO")
	TotalDAO Client;
	
	/**
	 * @Method Name : getList
	 * @작성일 : 2017. 3. 10.
	 * @작성자 : mwlee
	 * @param :
	 * @Method 설명 : 로그 조회
	 * @param param
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(TotalVo totVo) throws Exception{
		List<Map> dataList = null; 
		long offset 	= (Long.parseLong(totVo.getPageNum()) - 1) * Long.parseLong(totVo.getRowNum());
		int   limit 	= Integer.parseInt(totVo.getRowNum());
		String resultQuery = getQueryParser(totVo);
//		String resultQuery2 = "";
//		if(true)
//		{			
////			List<String> a = new ArrayList<String>();
////			a.add("ALL");
////			totVo.setMachineName(a);
////			List<String> b = new ArrayList<String>();
////			b.add("NOTDESIGNATED");
////			totVo.setMachineType(b);
//			resultQuery2 = getQueryParser2(totVo);
//			;
//		}
		
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			resultQuery += Common.sPipeLine + "limit " + offset + " " +  limit;		//결과 출력에 대해 limit을 적용한 쿼리 
			if (!(resultQuery.contains("sort"))) {
				resultQuery += Common.sPipeLine + Common.sSort + Common.s_TIME;			//결과 출력에 대해 time sort를 적용한 쿼리
			}
			resultQuery += String.format(Common.sEval, "No", "seq()") + Common.sPlus + offset;
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(totVo.getFabSite(), resultQuery);
		}
		return dataList;
	}

	@Override // 2018.07.05 
	public void getTotalLogListStop(/*TotalVo totVo*/) throws Exception{  
		try {
			Client.dbExecuteQueryStop();
		} catch (Exception e) {
			log.warn("getTotalLogListStop Exception!! : " + e.getMessage() );
		}
	}
	 
	// 200827 hgJeon 사용안함 주석처리
	/*@Override
	public List<Map> getXmlList(TotalVo totVo) throws Exception {
		List<Map> xmlList = null;
		String resultQuery = getQueryForXml(totVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			xmlList = Client.dbExecuteQuery(resultQuery);
		}
		return xmlList;
	}*/
	
	/*@Override
	public List<Map> getXmlListGroup(TotalVo totVo) throws Exception {
		List<Map> xmlList = null;
		String resultQuery = getQueryForXmlGroup(totVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			xmlList = Client.dbExecuteQuery(resultQuery);
		}
		return xmlList;
	}*/
	
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getSelectList(String fabSite) throws Exception {
		List<Map> selectList = null;
		// 2021. 04. 01. X0122410 대상 테이블 변경	machine_info > machine_list
//		String bayNameQuery = "memlookup name=machine_info | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search BAYNAME !="
//				+Common.sDoubleQuotation+Common.sDoubleQuotation;
//		String machineNameQuery = "memlookup name=machine_info | fields MACHINENAME | sort MACHINENAME";
		String bayNameQuery = "memlookup name=machine_list | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search BAYNAME !="
				+Common.sDoubleQuotation+Common.sDoubleQuotation;
		String machineNameQuery = "memlookup name=machine_list | fields MACHINENAME | sort MACHINENAME";
		String commMsgNameQuery = "memlookup name=comm_msg_name";
		String messageNameQuery = "memlookup name=message_name";
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		selectList = Client.dbExecuteQuery(fabSite, bayNameQuery);
		selectList.addAll(Client.dbExecuteQuery(fabSite, machineNameQuery));
		selectList.addAll(Client.dbExecuteQuery(fabSite, commMsgNameQuery));
		selectList.addAll(Client.dbExecuteQuery(fabSite, messageNameQuery));
		return selectList;
	}
	
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getMachineNameListByType(TotalVo totVo) throws Exception {
		List<Map> machineList = null;
		StringBuilder sQuery = new StringBuilder();
		// 2021. 04. 01. X0122410 대상 테이블 변경	machine_info > machine_list
//		sQuery.append(Common.sGetMachineQuery + String.format(Common.sSearch_1, Common.sTYPE,
//				Common.sDoubleQuotation + totVo.getMachineType().get(0) + Common.sDoubleQuotation));
		// 2022.06.08	X0122410 : machine_list 데이타 변경,  MACHINETYPE -> TYPE
		//sQuery.append(Common.sGetMachineQuery + String.format(Common.sSearch_1, Common.sMACHINETYPE, Common.sDoubleQuotation + totVo.getMachineType().get(0) + Common.sDoubleQuotation));
		sQuery.append(Common.sGetMachineQuery + String.format(Common.sSearch_1, Common.sTYPE, Common.sDoubleQuotation + totVo.getMachineType().get(0) + Common.sDoubleQuotation));
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		machineList = Client.dbExecuteQuery(totVo.getFabSite(), sQuery.toString());
		return machineList;
	}
	
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getMachineNameListByTypeMachineTypeNotNull(TotalVo totVo) throws Exception {
		List<Map> machineList = null;
		StringBuilder sQuery = new StringBuilder();
		// 2021. 04. 01. X0122410 대상 테이블 변경	machine_info > machine_list
//		sQuery.append(Common.sGetMachineQuery + String.format(Common.sSearch_1, Common.sTYPE,
//				Common.sDoubleQuotation + totVo.getMachineType().get(0) + Common.sDoubleQuotation));
		// 2022.06.08	X0122410 : machine_list 데이타 변경,  MACHINETYPE -> TYPE
		// 2022.06.08	X0122410 : machine_list에 MACHINETYPE이 null이 아닌것만 보이게
		//sQuery.append(Common.sGetMachineQuery + String.format(Common.sSearch_1, Common.sMACHINETYPE, Common.sDoubleQuotation + totVo.getMachineType().get(0) + Common.sDoubleQuotation));
		sQuery.append(Common.sGetMachineQuery + " | search isnotnull(MACHINETYPE) " + String.format(Common.sSearch_1, Common.sTYPE, Common.sDoubleQuotation + totVo.getMachineType().get(0) + Common.sDoubleQuotation));
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		machineList = Client.dbExecuteQuery(totVo.getFabSite(), sQuery.toString());
		return machineList;
	}
	
	/**
	 * @Method Name  : getAreaNameList
	 * @작성일     : 2019. 1. 09. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 : AreaNameList 리스트 조회
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getAreaNameList(String fabSite) throws Exception {
		List<Map> selectList = null;
		// 2021. 04. 01. X0122410 대상 테이블 변경	machine_info > machine_list
//		String areaNameQuery = 
//				"memlookup name=machine_info | stats count by AREANAME | fields AREANAME | search len(AREANAME) > 1";
		String areaNameQuery = 
				"memlookup name=machine_list | stats count by AREANAME | fields AREANAME | search len(AREANAME) > 1";
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		selectList = Client.dbExecuteQuery(fabSite,areaNameQuery);
		return selectList;
	}

	/**
	 * @Method Name  : getBayNameList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 박민호
	 * @param    :
	 * @Method 설명 : BayName 리스트 조회
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@Override
	public List<Map> getBayNameList(String fabSite) throws Exception {
		List<Map> selectList = null;
		// 2021. 04. 01. X0122410 대상 테이블 변경	machine_info > machine_list
//		String bayNameQuery = 
//				"memlookup name=machine_info | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search len(BAYNAME) > 1";
		String bayNameQuery = 
				"memlookup name=machine_list | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search len(BAYNAME) > 1";
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		selectList = Client.dbExecuteQuery(fabSite,bayNameQuery);
		return selectList;
	}
	
	/**
	 * @Method Name  : getMachineNameList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 박민호
	 * @param    :
	 * @Method 설명 : MachineName 리스트 조회
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getMachineNameList(MachineVo machineVo) throws Exception {
		if (machineVo == null) {
			return null;
		} // null exception
		List<Map> machineList = null; 
		String resultQuery = getMachineQueryParser(machineVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			machineList = Client.dbExecuteQuery(machineVo.getFabSite(),resultQuery);
		}
		return machineList;
	}
	
	/**
	 * @Method Name  : getMachineNameListMachineTypeNotNull
	 * @작성일     : 2022. 6. 8. 
	 * @작성자     : 강병민
	 * @param    :
	 * @Method 설명 : MachineName 리스트 조회 Machine Type is Not null 
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getMachineNameListMachineTypeNotNull(MachineVo machineVo) throws Exception {
		if (machineVo == null) {
			return null;
		} // null exception
		List<Map> machineList = null; 
		String resultQuery = getMachineQueryParserMachineTypeNotNull(machineVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			machineList = Client.dbExecuteQuery(machineVo.getFabSite(),resultQuery);
		}
		return machineList;
	}
	
	/**
	 * @Method Name  : getCommMsgNameList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 박민호
	 * @param    : CommMsgName 리스트 조회
	 * @Method 설명 :
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
		selectList = Client.dbExecuteQuery(fabSite,commMsgNameQuery);
		return selectList;
	}
	
	/**
	 * @Method Name  : getMessageNameList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 박민호
	 * @param    :
	 * @Method 설명 : MessageName 리스트 조회
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
		selectList = Client.dbExecuteQuery(fabSite,messageNameQuery);
		return selectList;
	}
	
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getOperationNameList(String fabSite) throws Exception {
		List<Map> selectList = null;
		String operationNameListQuery = "memlookup name=operation_name | sort OPERATION";
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		selectList = Client.dbExecuteQuery(fabSite,operationNameListQuery);
		return selectList;
	}
	
	
	public String getQueryParser(TotalVo totVo) {
		if (totVo == null) {
			return null;
		} // null exception
		
		//20170928 기본조회시 TABLE 쿼리 우선 적용 
		if( ( (totVo.getProcess() == null || totVo.getProcess().equals("")) &&
				(totVo.getCarrier()==null || totVo.getCarrier().equals("")) &&
				(totVo.getThread() == null || totVo.getThread().equals("")) &&
				(totVo.getGtxnId() == null || totVo.getGtxnId().equals("")) &&
				(totVo.getTransactionId() == null || totVo.getTransactionId().equals(""))&& 
				(totVo.getMessageName() == null || totVo.getMessageName().equals(""))&& 
				(totVo.getComMsgName() == null || totVo.getComMsgName().equals(""))&& 
				(totVo.getOperationName() == null || totVo.getOperationName().equals(""))&& 
				(totVo.getCommandId() == null || totVo.getCommandId().equals(""))&& 
				(totVo.getUnit() == null || totVo.getUnit().equals(""))&& 
				(totVo.getText() == null || totVo.getText().equals(""))&&
				// 200831 hgJeon MachineName 조건만 적용
				/*(totVo.getAreaName() == null || totVo.getAreaName().contains(Common.sALL) ) &&
				(totVo.getBayName() == null || totVo.getBayName().contains(Common.sALL) ) &&*/
				(totVo.getMachineType()==null || totVo.getMachineType().size() < 1) && 
				(totVo.getMachineName()==null || totVo.getMachineName().size() < 1) ) ){
			
			StringBuilder tQuery= new StringBuilder();
			tQuery.append(String.format(Common.sTable_From, totVo.getFrom(), totVo.getTo(),
					Common.sOrder+ Common.sEqual_1+Common.sAsc+ Common.sParallel + Common.sSpace));
			
			// 180808 FAB 선택시 테이블 쿼리 변경
			if (totVo.getFab()!=null && totVo.getFab().size() > 0) {
				List<String> fab = totVo.getFab();
				String fabName = "";
				log.info("fab:"+totVo.getFab());
				
				for(int i=0;i<totVo.getFab().size();i++){
//					if(fab.get(i).contains("FAB_B")) {
//						fabName = totVo.getLevel().contains(Common.sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
//								getTableFromFab("B", true) : getTableFromFab("B", false);
//					}else if (fab.get(i).contains("FAB_A")) {
//						fabName = totVo.getLevel().contains(Common.sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
//								getTableFromFab("A", true) : getTableFromFab("A", false);
//					}else if (fab.get(i).contains("FAB_C")) {	// 20200827 hgJeon M16 조건 추가
//						fabName = totVo.getLevel().contains(Common.sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
//								getTableFromFab("C", true) : getTableFromFab("C", false);
//					}
					//2022. 6.15. X0122410 : fab site 접근로직 변경 
//					fabName = totVo.getLevel().contains(Common.sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
//							getTableFromFab(Common.sFAB_SITE,fab.get(i), true) 
//							: getTableFromFab(Common.sFAB_SITE,fab.get(i), false);
					fabName = totVo.getLevel().contains(Common.sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
							getTableFromFab(totVo.getFabSite(),fab.get(i), true) 
							: getTableFromFab(totVo.getFabSite(),fab.get(i), false);
					if(fabName != null && !fabName.isEmpty()) {
						if(i==0){
							tQuery.append(fabName);
						}else if(i==(totVo.getFab().size()-1)) {
							tQuery.append(Common.sComma + fabName);
						}else{
							tQuery.append(Common.sComma + fabName);
						}
					}
				}
			}
			
			// 2021.03.22	X0122410 : MACHINETYPE조건 추가
			tQuery.append(Common.sCRLF
					+ Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX + Common.sComma + Common.sMACHINENAME + Common.sComma + Common.sMACHINETYPE
					+ Common.sComma + Common.sUNIT + Common.sComma + Common.sCARRIER + Common.sComma + Common.sCOMMANDID
					+ Common.sComma + Common.sCOMMAND + Common.sComma + Common.sOPERATIONNAME + Common.sComma
					+ Common.sMESSAGENAME + Common.sComma + Common.sPROCESS + Common.sComma + Common.sTRANSACTIONID
					+ Common.sComma + Common.sTEXT + Common.sComma + Common.sTHREADNAME + Common.sComma + Common.sKey
					 + Common.sComma + Common.sLEVEL + Common.sComma + Common.sXML + Common.sComma + Common.sSECS 
					 + Common.sComma + Common.sRESULTCODE
					);			
			
			// 5.Add LEVEL
			if (totVo.getLevel()!=null && totVo.getLevel().size() > 0) {
				StringBuilder sLevel = new StringBuilder();
				sLevel.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sLEVEL));
				log.info("level1:"+sLevel);
				for (String s : totVo.getLevel()) {
					if (s.indexOf(Common.sALL) >= 0) {	// 200414 hgJeon All 일경우 level 선택안함
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
					log.info("level2:"+sLevel);
					if (sLevel.toString().indexOf("(") >= 0) {
						sLevel.append(" )");
					} // search in ( ... )
					tQuery.append(sLevel.toString());
				}
			}
			
			SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMddHHss");
			try{
				Date fromTime = sdf.parse(totVo.getFrom());
				Date toTime = sdf.parse(totVo.getTo());
				long diff = toTime.getTime() - fromTime.getTime();
				//log.info("fromtime:"+fromTime);
				//log.info("totime:"+toTime);
				log.info("diff:"+diff);
				if(diff < 500001) {	//5분 이하 쿼리시 sort 적용
					tQuery.append(Common.sPipeLine + Common.sSort + Common.s_TIME);
				}
			}catch (Exception ignore) {}
			
			//20180625 fulltext 검색추가
			if (totVo.getFulltext() != null && !totVo.getFulltext().trim().equals("")) {
				if(totVo.getFulltext().toString().contains("\"")){
					totVo.setFulltext(totVo.getFulltext().replaceAll("\"", "\\\\\""));
				}
				tQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sTEXT,
						Common.sDoubleQuotation + Common.sAsterisk + totVo.getFulltext().trim() + Common.sAsterisk + Common.sDoubleQuotation));
			}
			
			return tQuery.toString();
		}	// end of table query
		
		// fulltext query
		boolean LevelIsAll = false;
		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(Common.sFulltext_Arg0, totVo.getFrom(), totVo.getTo()));
		
		// Add LEVEL and CARRIER
		if (totVo.getLevel()!=null && totVo.getLevel().size() > 0) {
			List<String> level = totVo.getLevel();
			
			if(!totVo.getLevel().contains(Common.sALL)) {
				for(int i=0;i<totVo.getLevel().size();i++){
					if(i==0){
						if(totVo.getLevel().size()==1){
							sQuery.append(Common.sLeftParenthesis+Common.sLEVEL+Common.sEquals
									+ Common.sDoubleQuotation + level.get(i)
									+ Common.sDoubleQuotation + Common.sRightParenthesis);
						}else{
							sQuery.append(Common.sLeftParenthesis+Common.sLEVEL+Common.sEquals
									+ Common.sDoubleQuotation + level.get(i)
									+ Common.sDoubleQuotation + Common.sOr);
						}
					}else if(i!=totVo.getLevel().size()-1){
						sQuery.append(Common.sLEVEL+Common.sEquals
						+ Common.sDoubleQuotation + level.get(i) 
						+ Common.sDoubleQuotation + Common.sOr);
					}else{
						sQuery.append(Common.sLEVEL+Common.sEquals
						+ Common.sDoubleQuotation + level.get(i) 
						+ Common.sDoubleQuotation+Common.sRightParenthesis);
					}
				}	// end of for
			}else {
				LevelIsAll = true;
			}
		}
		
		// 6.Condition & Filter --> AND , OR
		
		List<String> conditionList = new ArrayList<String>();

		//20180419 ,로 멀티조건 검색위해 수정
		if(totVo.getProcess()!= null && !totVo.getProcess().trim().equals("")) {
			if(totVo.getProcess().contains(Common.sCommaOrigin)){
				StringBuilder tempQuery = new StringBuilder();
				String[] processNameArray = totVo.getProcess().split(Common.sCommaOrigin);
				for(int i=0;i<processNameArray.length;i++){
					if(i==0){
						tempQuery.append(
								Common.sCRLF + Common.sLeftParenthesis + Common.sLeftParenthesis
								+ Common.sPROCESSNAME + Common.sEquals
								+ Common.sDoubleQuotation + processNameArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis 
								);
					}else if(i==(processNameArray.length-1)){
						tempQuery.append(
								 Common.sOr + Common.sLeftParenthesis
								+ Common.sPROCESSNAME + Common.sEquals
								+ Common.sDoubleQuotation + processNameArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis
								);
					}else{
						tempQuery.append(
								 Common.sOr + Common.sLeftParenthesis
								+ Common.sPROCESSNAME + Common.sEquals
								+ Common.sDoubleQuotation + processNameArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis
								);
					}
				}conditionList.add(tempQuery.toString());
			}else{
				conditionList.add(Common.sCRLF + Common.sLeftParenthesis 
						+ Common.sPROCESSNAME + Common.sEquals 
						+ Common.sDoubleQuotation + totVo.getProcess().trim() 
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}
		
		// getCarrierName 
		//20180419 ,로 멀티조건 검색위해 수정
		if(totVo.getCarrier()!=null && !totVo.getCarrier().trim().equals("")){
			if(totVo.getCarrier().contains(Common.sCommaOrigin)){
				StringBuilder tempQuery = new StringBuilder();
				String[] carrierNameArray = totVo.getCarrier().split(Common.sCommaOrigin);
				for(int i=0;i<carrierNameArray.length;i++) {
					if(i==0){
						tempQuery.append(
						Common.sCRLF + Common.sLeftParenthesis + Common.sLeftParenthesis
						+ Common.sCARRIER + Common.sEquals
						+ Common.sDoubleQuotation + carrierNameArray[i].trim()
						+ Common.sDoubleQuotation + Common.sRightParenthesis 
						);
					}else if(i==(carrierNameArray.length-1)){
						tempQuery.append(
						 Common.sOr + Common.sLeftParenthesis
						+ Common.sCARRIER + Common.sEquals
						+ Common.sDoubleQuotation + carrierNameArray[i].trim()
						+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis
						);
					}else{
						tempQuery.append(
						 Common.sOr + Common.sLeftParenthesis
						+ Common.sCARRIER + Common.sEquals
						+ Common.sDoubleQuotation + carrierNameArray[i].trim()
						+ Common.sDoubleQuotation + Common.sRightParenthesis
						);
					}
				}
				conditionList.add(tempQuery.toString());
			}else{
				conditionList.add(Common.sCRLF + Common.sLeftParenthesis
						+ Common.sCARRIER + Common.sEquals
						+ Common.sDoubleQuotation + totVo.getCarrier().trim()
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}
		
		// getThread 170802 인덱스빌드 이후 코드 수정
		//20180419 ,로 멀티조건 검색위해 수정
		if (totVo.getThread() != null && !totVo.getThread().trim().equals("")){
			if(totVo.getThread().contains(Common.sCommaOrigin)){
				StringBuilder tempQuery = new StringBuilder();
				String[] threadNameArray = totVo.getThread().split(Common.sCommaOrigin);
				for(int i=0;i<threadNameArray.length;i++) {
					if(i==0){
						tempQuery.append(
						Common.sCRLF + Common.sLeftParenthesis + Common.sLeftParenthesis
						+ Common.sTHREADNAME + Common.sEquals
						+ Common.sDoubleQuotation + threadNameArray[i].trim()
						+ Common.sDoubleQuotation + Common.sRightParenthesis 
						);
					}else if(i==(threadNameArray.length-1)){
						tempQuery.append(
						 Common.sOr + Common.sLeftParenthesis
						+ Common.sTHREADNAME + Common.sEquals
						+ Common.sDoubleQuotation + threadNameArray[i].trim()
						+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis
						);
					}else{
						tempQuery.append(
						 Common.sOr + Common.sLeftParenthesis
						+ Common.sTHREADNAME + Common.sEquals
						+ Common.sDoubleQuotation + threadNameArray[i].trim()
						+ Common.sDoubleQuotation + Common.sRightParenthesis
						);
					}
				}
				conditionList.add(tempQuery.toString());
			}else{
				conditionList.add(Common.sCRLF + Common.sLeftParenthesis
						+ Common.sTHREADNAME + Common.sEquals 
						+ Common.sDoubleQuotation + totVo.getThread().trim()
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}
		
		// getGtxnId	201023 hgJeon GTXN_ID 검색 추가
		if (totVo.getGtxnId() != null && !totVo.getGtxnId().trim().equals("")) {
			if(totVo.getGtxnId().contains(Common.sCommaOrigin)){
				StringBuilder tempQuery = new StringBuilder();
				String [] transNameArray = totVo.getGtxnId().split(Common.sCommaOrigin);
				for(int i=0; i<transNameArray.length; i++) {
					if(i==0) {
						tempQuery.append(
								Common.sCRLF + Common.sLeftParenthesis + Common.sLeftParenthesis
								+ Common.sGTXN_ID + Common.sEquals
								+ Common.sDoubleQuotation + transNameArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis
								);
					}else if(i==transNameArray.length-1) {
						tempQuery.append(
								Common.sOr + Common.sLeftParenthesis 
								+ Common.sGTXN_ID + Common.sEquals
								+ Common.sDoubleQuotation + transNameArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis
								);
					}else {
						tempQuery.append(
								Common.sOr + Common.sLeftParenthesis 
								+ Common.sGTXN_ID + Common.sEquals
								+ Common.sDoubleQuotation + transNameArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis
								);
					}
				}
				conditionList.add(tempQuery.toString());
			}else {
				conditionList.add(Common.sCRLF + Common.sLeftParenthesis
						+ Common.sGTXN_ID + Common.sEquals 
						+ Common.sDoubleQuotation + totVo.getGtxnId().trim() 
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}
		
		// getTransactionId
		//20180419 ,로 멀티조건 검색위해 수정
		if (totVo.getTransactionId() != null && !totVo.getTransactionId().trim().equals("")) {
			if(totVo.getTransactionId().contains(Common.sCommaOrigin)){
				StringBuilder tempQuery = new StringBuilder();
				String [] transNameArray = totVo.getTransactionId().split(Common.sCommaOrigin);
				for(int i=0; i<transNameArray.length; i++) {
					if(i==0) {
						tempQuery.append(
								Common.sCRLF + Common.sLeftParenthesis + Common.sLeftParenthesis
								+ Common.sTRANSACTIONID + Common.sEquals
								+ Common.sDoubleQuotation + transNameArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis
								);
					}else if(i==transNameArray.length-1) {
						tempQuery.append(
								Common.sOr + Common.sLeftParenthesis 
								+ Common.sTRANSACTIONID + Common.sEquals
								+ Common.sDoubleQuotation + transNameArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis
								);
					}else {
						tempQuery.append(
								Common.sOr + Common.sLeftParenthesis 
								+ Common.sTRANSACTIONID + Common.sEquals
								+ Common.sDoubleQuotation + transNameArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis
								);
					}
				}
				conditionList.add(tempQuery.toString());
			}else {
				conditionList.add(Common.sCRLF + Common.sLeftParenthesis
						+ Common.sTRANSACTIONID + Common.sEquals 
						+ Common.sDoubleQuotation + totVo.getTransactionId().trim() 
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}

		// getMessageName 170802 인덱스빌드 이후 코드 수정
		if (totVo.getMessageName() != null && !totVo.getMessageName().trim().equals("")) {
			conditionList.add(Common.sCRLF + Common.sLeftParenthesis
					+ Common.sMESSAGENAME + Common.sEquals 
					+ Common.sDoubleQuotation + totVo.getMessageName().trim() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// getComMsgName 170802 인덱스빌드 이후 코드 수정
		if (totVo.getComMsgName() != null && !totVo.getComMsgName().trim().equals("")) {
			conditionList.add(Common.sCRLF + Common.sLeftParenthesis
					+ Common.sLeftParenthesis
					+ Common.sCOMMSGNAME + Common.sEquals 
					+ Common.sDoubleQuotation + totVo.getComMsgName().trim() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sOr
					+ Common.sLeftParenthesis
					+ Common.sMESSAGENAME + Common.sEquals 
					+ Common.sDoubleQuotation + totVo.getComMsgName().trim() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis
					+Common.sRightParenthesis);
		}

		// getOperationName
		if (totVo.getOperationName() != null && !totVo.getOperationName().trim().equals("")) {
			conditionList.add(Common.sCRLF + Common.sLeftParenthesis
					+ Common.sOPERATIONNAME + Common.sEquals 
					+ Common.sDoubleQuotation + totVo.getOperationName().trim() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// getCommandId
		//20180419 ,로 멀티조건 검색위해 수정
		if (totVo.getCommandId() != null && !totVo.getCommandId().trim().equals("")) {
			if(totVo.getCommandId().contains(Common.sCommaOrigin)){
				StringBuilder tempQuery = new StringBuilder();
				String [] commandIdArray = totVo.getCommandId().split(Common.sCommaOrigin);
				for(int i=0; i<commandIdArray.length; i++){
					if(i==0){
						tempQuery.append(
								Common.sCRLF + Common.sLeftParenthesis + Common.sLeftParenthesis
								+ Common.sCOMMANDID + Common.sEquals 
								+ Common.sDoubleQuotation + commandIdArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis
								);
					}else if(i == commandIdArray.length-1){
						tempQuery.append(
								Common.sOr + Common.sLeftParenthesis
								+ Common.sCOMMANDID + Common.sEquals 
								+ Common.sDoubleQuotation + commandIdArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis
								);
						}else{
							tempQuery.append(
									Common.sOr + Common.sLeftParenthesis
									+ Common.sCOMMANDID + Common.sEquals 
									+ Common.sDoubleQuotation + commandIdArray[i].trim()
									+ Common.sDoubleQuotation + Common.sRightParenthesis
									);
						}
				}conditionList.add(tempQuery.toString());
			}else{
				conditionList.add(Common.sCRLF + Common.sLeftParenthesis
						+ Common.sCOMMANDID + Common.sEquals 
						+ Common.sDoubleQuotation + totVo.getCommandId().trim()
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}

		// getUnit 170802 인덱스빌드 이후 코드 수정
		if (totVo.getUnit() != null && !totVo.getUnit().trim().equals("")) {
			if(totVo.getUnit().contains(Common.sCommaOrigin)){
				StringBuilder tempQuery = new StringBuilder();
				String [] unitNameArray = totVo.getUnit().split(Common.sCommaOrigin);
				for(int i=0; i< unitNameArray.length; i++){
					if(i==0){
						tempQuery.append(Common.sCRLF + Common.sLeftParenthesis + Common.sLeftParenthesis
								+ Common.sUNIT + Common.sEquals
								+ Common.sDoubleQuotation + unitNameArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis
								);
					}else if(i == unitNameArray.length-1){
						tempQuery.append(
								Common.sOr + Common.sLeftParenthesis
								+ Common.sUNIT + Common.sEquals 
								+ Common.sDoubleQuotation + unitNameArray[i].trim()
								+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis
								);
						}else{
							tempQuery.append(
									Common.sOr + Common.sLeftParenthesis
									+ Common.sUNIT + Common.sEquals 
									+ Common.sDoubleQuotation + unitNameArray[i].trim()
									+ Common.sDoubleQuotation + Common.sRightParenthesis
									);
						}
				}conditionList.add(tempQuery.toString());
			}else{
				conditionList.add(Common.sCRLF + Common.sLeftParenthesis
						+ Common.sUNIT + Common.sEquals 
						+ Common.sDoubleQuotation + totVo.getUnit().trim()
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}
		}

		// getText 특수문자 ", ', [, ] 추가시 사용할 코드
		if (totVo.getText() != null && !totVo.getText().trim().equals("")) {
			if(totVo.getText().toString().contains("\"")){
				totVo.setText(totVo.getText().replaceAll("\"", "\\\\\""));
			}
			
			if(totVo.getText().toString().contains(Common.sAsterisk)) {	// 201223 hgJeon text 검색 시 * 문자 제외
				totVo.setText(totVo.getText().replaceAll("\\*", Common.sEmpty));
			}
			
			if(totVo.getText().contains(Common.sCommaOrigin)){
				StringBuilder tempQuery = new StringBuilder();
				String[] textNameArray = totVo.getText().split(Common.sCommaOrigin);
				for(int i=0;i<textNameArray.length;i++){
					if(i==0){
						tempQuery.append(
						Common.sCRLF + Common.sLeftParenthesis + Common.sLeftParenthesis
						+ Common.sTEXT + Common.sEquals
						+ Common.sDoubleQuotation + Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis 
						);
					}else if(i==(textNameArray.length-1)){
						tempQuery.append(
						 Common.sOr + Common.sLeftParenthesis
						+ Common.sTEXT + Common.sEquals
						+ Common.sDoubleQuotation + Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis
						);
					}else{
						tempQuery.append(
						 Common.sOr + Common.sLeftParenthesis
						+ Common.sTEXT + Common.sEquals
						+ Common.sDoubleQuotation + Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis
						);
					}
				}conditionList.add(tempQuery.toString());
			}else{
				conditionList.add(Common.sCRLF + Common.sLeftParenthesis
						+ Common.sTEXT + Common.sEquals 
						+ Common.sDoubleQuotation + Common.sAsterisk + totVo.getText().trim() + Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis);
			}			
		}		
		
		String searchOption = Common.sOr;
		if(totVo.getSearchOption()!=null && !(totVo.getSearchOption().equals(""))){
			searchOption = Common.sSpace + totVo.getSearchOption().toLowerCase() + Common.sSpace;	// 'and' or 'or'
		}
		if(!LevelIsAll) {
			if(conditionList.size()>0){
				if(conditionList.size()==1){
					sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis 
						+ conditionList.get(0) + Common.sRightParenthesis);
				}else{
					for(int i=0;i<conditionList.size();i++){
						if(i==0){
							sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis + conditionList.get(i));
						}else if(i==conditionList.size()-1){
							sQuery.append(searchOption + conditionList.get(i) + Common.sRightParenthesis);
						}else{
							sQuery.append(searchOption + conditionList.get(i));
						}
					}
				}
			}
		}else {	// level 이 All 일경우
			if(conditionList.size()>0){
				if(conditionList.size()==1){
					sQuery.append(conditionList.get(0));
				}else{
					for(int i=0;i<conditionList.size();i++){
						if(i==0){
							sQuery.append(conditionList.get(i));
						}else if(i==conditionList.size()-1){
							sQuery.append(searchOption + conditionList.get(i));
						}else{
							sQuery.append(searchOption + conditionList.get(i));
						}
					}
				}
			}
		}
		
		/*	200831 hgJeon Area, Bay, MachineType 의 독립적인 검색조건 기능 제거함
		 * Area, Bay, MachineType 은 Machine 선택을 위한 변수임
		// sAREANAME
		if (totVo.getAreaName()!=null && totVo.getAreaName().indexOf(Common.sALL) >= 0) {
		} else {
			log.info("AREANAME~~");
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sAREANAME + Common.sEquals
					+ Common.sDoubleQuotation + totVo.getAreaName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		} 

		// sBAYNAME
		if (totVo.getBayName()!=null && totVo.getBayName().indexOf(Common.sALL) >= 0) {
		} else {
			log.info("BAYNAME~~");
			sQuery.append(Common.sCRLF + Common.sAnd + Common.sLeftParenthesis
					+ Common.sBAYNAME + Common.sEquals
					+ Common.sDoubleQuotation + totVo.getBayName() 
					+ Common.sDoubleQuotation + Common.sRightParenthesis);
		}

		// 2021.03.22	X0122410 : 기존 검색조건이 잘못 연결되어 있었음, TYPE > MACHINETYPE으로 변경
		// sTYPE
		if (totVo.getMachineType()!=null && totVo.getMachineType().size() > 0) {
			List<String> typeList = totVo.getMachineType();
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
			log.info("MACHINETYPE ~~");
		}
		*/		
		// sMACHINETYPE		
		StringBuilder subMachineTypeQuery = new StringBuilder();
		if (totVo.getMachineType()!=null && totVo.getMachineType().size() > 0) {			
			subMachineTypeQuery.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sMACHINETYPE));
			for (String s : totVo.getMachineType()) {
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
		if (totVo.getMachineName()!=null && totVo.getMachineName().size() > 0) {
			List<String> machineList = totVo.getMachineName();
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
		
		// 180615 FAB 선택시 테이블 쿼리 변경
		if (totVo.getFab()!=null && totVo.getFab().size() > 0) {
			List<String> fab = totVo.getFab();
			String fabName = "";
			log.info("fab:"+totVo.getFab());
			
			for(int i=0;i<totVo.getFab().size();i++){
//				if(fab.get(i).contains("FAB_B")) {
//					fabName = totVo.getLevel().contains(Common.sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
//							getTableFromFab("B", true) : getTableFromFab("B", false);
//				}else if (fab.get(i).contains("FAB_A")) {
//					fabName = totVo.getLevel().contains(Common.sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
//							getTableFromFab("A", true) : getTableFromFab("A", false);
//				}else if (fab.get(i).contains("FAB_C")) {	// 20200827 hgJeon M16 조건 추가
//					fabName = totVo.getLevel().contains(Common.sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
//							getTableFromFab("C", true) : getTableFromFab("C", false);
//				}
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//fabName = totVo.getLevel().contains(Common.sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
				//		getTableFromFab(Common.sFAB_SITE,fab.get(i), true) : getTableFromFab(Common.sFAB_SITE,fab.get(i), false);
				fabName = totVo.getLevel().contains(Common.sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
						getTableFromFab(totVo.getFabSite(),fab.get(i), true) : getTableFromFab(totVo.getFabSite(),fab.get(i), false);
				if(fabName != null && !fabName.isEmpty()) {
					if(i==0){
						sQuery.append(Common.sFrom + fabName);
					}else if(i==(totVo.getFab().size()-1)) {
						sQuery.append(Common.sComma + fabName);
					}else{
						sQuery.append(Common.sComma + fabName);
					}
				}
			}
		}
		
		//2021.03.24	X0122410 : MachineType조건
		sQuery.append(subMachineTypeQuery.toString());
		
		sQuery.append(
				Common.sCRLF + Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX + Common.sComma + Common.sMACHINENAME + Common.sComma + Common.sMACHINETYPE
				+ Common.sComma + Common.sUNIT + Common.sComma + Common.sCARRIER + Common.sComma + Common.sCOMMANDID
				+ Common.sComma + Common.sCOMMAND + Common.sComma + Common.sOPERATIONNAME + Common.sComma
				+ Common.sMESSAGENAME + Common.sComma + Common.sPROCESS + Common.sComma + Common.sTRANSACTIONID
				+ Common.sComma + Common.sTEXT + Common.sComma + Common.sTHREADNAME /*+ Common.sComma + Common.sKey*/
				 + Common.sComma + Common.sLEVEL + Common.sComma + Common.sXML + Common.sComma + Common.sSECS
				 + Common.sComma + Common.sRESULTCODE
				);
		
		//20180625 fulltext 검색추가
		if (totVo.getFulltext() != null && !totVo.getFulltext().trim().equals("")) {
			if(totVo.getFulltext().toString().contains("\"")){
				totVo.setFulltext(totVo.getFulltext().replaceAll("\"", "\\\\\""));
			}
			if(totVo.getFulltext().toString().contains(Common.sAsterisk)) {	// 201223 hgJeon text 검색 시 * 문자 제외
				totVo.setFulltext(totVo.getFulltext().replaceAll("\\*", Common.sEmpty));
			}
			sQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sTEXT,
					Common.sDoubleQuotation + Common.sAsterisk + totVo.getFulltext().trim() + Common.sAsterisk + Common.sDoubleQuotation));
		}
		
		sQuery.append(Common.sPipeLine + Common.sSort + Common.s_TIME);
		LevelIsAll = false;	// 200414 hgJeon boolean 초기화
		
		return sQuery.toString();
	}
	
	public String getQueryForXml(TotalVo totVo) {	// 사용안함
		if (totVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(Common.sFulltext, totVo.getKey().get(0), "ts_xml"));

		return sQuery.toString();
	}
	
	public String getQueryForXmlGroup(TotalVo totVo) {	// 사용안함
		if (totVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();
		sQuery.append(Common.sFulltext0);
		for(int i=0;i<totVo.getKey().size();i++){
			if(i==0){
				if(totVo.getKey().size()==1){
					sQuery.append(Common.sLeftParenthesis
							+ Common.sKey + Common.sEquals + Common.sDoubleQuotation
							+ totVo.getKey().get(i)+Common.sDoubleQuotation + Common.sRightParenthesis
							+ Common.sFrom + "ts_xml");
				}else{
					sQuery.append(Common.sLeftParenthesis
							+ Common.sKey + Common.sEquals + Common.sDoubleQuotation
							+ totVo.getKey().get(i)+Common.sDoubleQuotation + Common.sOr);
				}
			}else if(i==totVo.getKey().size()-1){
				sQuery.append(
						Common.sKey + Common.sEquals + Common.sDoubleQuotation
						+ totVo.getKey().get(i)+Common.sDoubleQuotation + Common.sRightParenthesis
						+ Common.sFrom + "ts_xml");
			}else{
				sQuery.append(
						Common.sKey + Common.sEquals + Common.sDoubleQuotation
						+ totVo.getKey().get(i)+Common.sDoubleQuotation + Common.sOr); 
			}
			
		}

		return sQuery.toString();
	}
	
	// 신규로그 조회용 // 미사용
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(TotalNewVo totVo) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}

	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDetailDataList(String fabSite, String addQuery) throws Exception {
		// TODO Auto-generated method stub
		return null;
	}
	// ------------------

	private String getMachineQueryParser(MachineVo machineVo){
		StringBuilder sQuery = new StringBuilder();
		sQuery.append(Common.sGetMachineQuery);

		// 2021. 04. 01. X0122410 대상 테이블 변경	machine_info > machine_list
		// FAB 선택 machineVo SecsFab 사용
//		if (machineVo.getSelectFab()!=null && machineVo.getSelectFab().size() > 0) {
//			StringBuilder sFab = new StringBuilder();
//			sFab.append(Common.sCRLF + String.format(Common.sSearch_in, "FAB"));
//
//			for (String s : machineVo.getSelectFab()) {
//				if (s.indexOf(Common.sALL) >= 0) {
//					sFab = null;
//					break;
//				} else {
//					sFab.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
//				}
//			}
//
//			if (sFab != null && !(sFab.toString().isEmpty())) {
//				if (sFab.toString().indexOf("(") >= 0) {
//					sFab.append(" )");
//				} // search in ( ... )
//				sQuery.append(sFab.toString());
//			}
//		}
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
		
		// 2021.03.22	X0122410 : 기존 검색조건이 잘못 연결되어 있었음, TYPE > MACHINETYPE으로 변경
		// Type
		/*
		if (machineVo.getMachineType()!=null && machineVo.getMachineType().size() > 0) {
			StringBuilder sMachine = new StringBuilder();
			sMachine.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sTYPE));

			for (String s : machineVo.getMachineType()) {
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
		*/
		// sMACHINETYPE
		if (machineVo.getMachineType()!=null && machineVo.getMachineType().size() > 0) {
			StringBuilder sMachine = new StringBuilder();
			// 2022.06.08	X0122410 : machine_list 데이타 변경,  MACHINETYPE -> TYPE
			//sMachine.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sMACHINETYPE));
			sMachine.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sTYPE));

			for (String s : machineVo.getMachineType()) {
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
		
		// Area Name
		if (machineVo.getAreaName()!=null && !machineVo.getAreaName().equals("")) {
			if(machineVo.getAreaName().toUpperCase().equals(Common.sALL)){
			}else{
				sQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sAREANAME,
						Common.sDoubleQuotation + machineVo.getAreaName() + Common.sDoubleQuotation));
			}
		}

		// Bay Name
		if (machineVo.getBayName()!=null && !machineVo.getBayName().equals("")) {
			if(machineVo.getBayName().toUpperCase().equals(Common.sALL)){
			}else{
				sQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sBAYNAME,
						Common.sDoubleQuotation + machineVo.getBayName() + Common.sDoubleQuotation));
			}
		}
		
		sQuery.append(" | stats count by MACHINENAME | fields MACHINENAME | sort MACHINENAME");
		
		return sQuery.toString();
	}

	private String getMachineQueryParserMachineTypeNotNull(MachineVo machineVo){
		StringBuilder sQuery = new StringBuilder();
		sQuery.append(Common.sGetMachineQuery);
		// 2022.06.08	X0122410 : machine_list에 MACHINETYPE이 null이 아닌것만 보이게
		sQuery.append(Common.sCRLF + " | search isnotnull(MACHINETYPE) ");

		// 2021. 04. 01. X0122410 대상 테이블 변경	machine_info > machine_list
		// FAB 선택 machineVo SecsFab 사용
//		if (machineVo.getSelectFab()!=null && machineVo.getSelectFab().size() > 0) {
//			StringBuilder sFab = new StringBuilder();
//			sFab.append(Common.sCRLF + String.format(Common.sSearch_in, "FAB"));
//
//			for (String s : machineVo.getSelectFab()) {
//				if (s.indexOf(Common.sALL) >= 0) {
//					sFab = null;
//					break;
//				} else {
//					sFab.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
//				}
//			}
//
//			if (sFab != null && !(sFab.toString().isEmpty())) {
//				if (sFab.toString().indexOf("(") >= 0) {
//					sFab.append(" )");
//				} // search in ( ... )
//				sQuery.append(sFab.toString());
//			}
//		}
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
		
		// 2021.03.22	X0122410 : 기존 검색조건이 잘못 연결되어 있었음, TYPE > MACHINETYPE으로 변경
		// Type
		/*
		if (machineVo.getMachineType()!=null && machineVo.getMachineType().size() > 0) {
			StringBuilder sMachine = new StringBuilder();
			sMachine.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sTYPE));

			for (String s : machineVo.getMachineType()) {
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
		*/
		// sMACHINETYPE
		if (machineVo.getMachineType()!=null && machineVo.getMachineType().size() > 0) {
			StringBuilder sMachine = new StringBuilder();
			// 2022.06.08	X0122410 : machine_list 데이타 변경,  MACHINETYPE -> TYPE
			//sMachine.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sMACHINETYPE));
			sMachine.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sTYPE));

			for (String s : machineVo.getMachineType()) {
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
		
		// Area Name
		if (machineVo.getAreaName()!=null && !machineVo.getAreaName().equals("")) {
			if(machineVo.getAreaName().toUpperCase().equals(Common.sALL)){
			}else{
				sQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sAREANAME,
						Common.sDoubleQuotation + machineVo.getAreaName() + Common.sDoubleQuotation));
			}
		}

		// Bay Name
		if (machineVo.getBayName()!=null && !machineVo.getBayName().equals("")) {
			if(machineVo.getBayName().toUpperCase().equals(Common.sALL)){
			}else{
				sQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sBAYNAME,
						Common.sDoubleQuotation + machineVo.getBayName() + Common.sDoubleQuotation));
			}
		}
		
		sQuery.append(" | stats count by MACHINENAME | fields MACHINENAME | sort MACHINENAME");
		
		return sQuery.toString();
	}

	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getMachineNameList(String fabSite) throws Exception {
		// 2021. 04. 01. X0122410 대상 테이블 변경	machine_info > machine_list
		//String sQuery = "memlookup name=machine_info | search len(MACHINENAME) > 1 | fields MACHINENAME | sort MACHINENAME";
		String sQuery = "memlookup name=machine_list | search len(MACHINENAME) > 1 | stats count by MACHINENAME | fields MACHINENAME | sort MACHINENAME";
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		List<Map> machineList =  Client.dbExecuteQuery(fabSite,sQuery);
		
		return machineList;
	}
	
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getAreaFromFabList(MachineVo machineVo) throws Exception {
		if (machineVo == null) {
			return null;
		} // null exception
		
		List<Map> areaList = null;
		String resultQuery = getAreaBayQueryParser(machineVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			areaList = Client.dbExecuteQuery(machineVo.getFabSite(),resultQuery);
		}
		return areaList;
	}
	
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getBayFromAreaList(MachineVo machineVo) throws Exception {
		if (machineVo == null) {
			return null;
		} // null exception
		
		List<Map> bayList = null; 
		String resultQuery = getAreaBayQueryParser(machineVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			bayList = Client.dbExecuteQuery(machineVo.getFabSite(),resultQuery);
		}
		return bayList;
	}
	
	/**
	 * @Method Name  : getMachineTypeFromFab
	 * @작성일     : 2021. 3. 31
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
	
	private String getAreaBayQueryParser(MachineVo machineVo) {
		StringBuilder sQuery = new StringBuilder();
		String buildQuery;
		sQuery.append(Common.sGetMachineQuery);
		
		// 2021. 04. 01. X0122410 대상 테이블 변경	machine_info > machine_list
		// FAB 선택 machineVo SecsFab 사용
//		if (machineVo.getSelectFab()!=null && machineVo.getSelectFab().size() > 0) {
//			StringBuilder sFab = new StringBuilder();
//			sFab.append(Common.sCRLF + String.format(Common.sSearch_in, "FAB"));
//
//			for (String s : machineVo.getSelectFab()) {
//				if (s.indexOf(Common.sALL) >= 0) {
//					sFab = null;
//					break;
//				} else {
//					sFab.append(Common.sComma + Common.sDoubleQuotation + s + Common.sDoubleQuotation);
//				}
//			}
//
//			if (sFab != null && !(sFab.toString().isEmpty())) {
//				if (sFab.toString().indexOf("(") >= 0) {
//					sFab.append(" )");
//				} // search in ( ... )
//				sQuery.append(sFab.toString());
//			}
//		}
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
		
		if (machineVo.getAreaName()!=null && !machineVo.getAreaName().equals("")) {	// Bay 호출일때
			if(machineVo.getAreaName().toUpperCase().equals(Common.sALL)){	}
			else{
				sQuery.append(Common.sCRLF + String.format(Common.sSearch_1, Common.sAREANAME,
						Common.sDoubleQuotation + machineVo.getAreaName() + Common.sDoubleQuotation));
			}
			buildQuery = " | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search len(BAYNAME) > 1";
			
		}else {	// Area 호출일때
			buildQuery = " | stats count by AREANAME | fields AREANAME | sort AREANAME | search len(AREANAME) > 1";
		}
		
		/*String AreaQuery = " | stats count by AREANAME | fields AREANAME | sort AREANAME | search len(AREANAME) > 1";
		String BayQuery = " | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search len(BAYNAME) > 1";*/
		
		sQuery.append(Common.sCRLF + buildQuery);
		//log.info("QUERY : " + sQuery);
		return sQuery.toString();
	}
	
//	private String getTableFromFab(String FAB, boolean isAll) {
//		
//		String sFAB = Common.sFAB_SITE;
//		
//		switch(sFAB) {
//			case "M14" : {
//				if(FAB.equals("A")) {
//					return isAll ? Common.sTS_DATA : Common.sTS_DATA; 
//							//Common.sTS_DATA : Common.sTS_DATA_VIEW_M14A;
//				}else if(FAB.equals("B")){ // B 일경우
//					return isAll ? Common.sTS_DATA_M14B : Common.sTS_DATA_M14B; 
//							//Common.sTS_DATA_M14B : Common.sTS_DATA_VIEW_M14B;
//				}else {	// C 일경우 (M16)	
//					return isAll ? Common.sTS_DATA_M16 : Common.sTS_DATA_VIEW_M16;
//				}
//			}
//			case "M15" : {
//				if(FAB.equals("A")) {
//					return isAll ? Common.sTS_DATA_M15 : Common.sTS_DATA_VIEW_M15;
//				}else { // B 일경우
//					return null;
//				}
//			}
//			case "M11" : {
//				if(FAB.equals("A")) {
//					return isAll ? Common.sTS_DATA_M11 : Common.sTS_DATA_VIEW_M11;
//				}else { // B 일경우
//					return isAll ? Common.sTS_DATA_M11B : Common.sTS_DATA_VIEW_M11B;
//				}
//			}
//			case "C2" : {
//				if(FAB.equals("A")) {
//					return isAll ? Common.sTS_DATA_C2 : Common.sTS_DATA_VIEW_C2;
//				}else { // B 일경우
//					return isAll ? Common.sTS_DATA_C2F : Common.sTS_DATA_VIEW_C2F;
//				}
//			}
//			case "IC" : {
//				if(FAB.equals("A")) {
//					return isAll ? Common.sTS_DATA_M14A : Common.sTS_DATA_VIEW_M14A; 
//				}else if(FAB.equals("B")){ // B 일경우
//					return isAll ? Common.sTS_DATA_M14B : Common.sTS_DATA_VIEW_M14B; 
//				}else {	// C 일경우 (M16)	
//					return isAll ? Common.sTS_DATA_M16 : Common.sTS_DATA_VIEW_M16;
//				}
//			}
//			default : return null;
//		}
//	}
	
	private String getTableFromFab(String fabSite, String fab, boolean isAll) {
				
		switch(fabSite) {
			case Common.sFABSITE_M14 : {
				if(fab.equals(Common.sFAB_M14A)) {
					return isAll ? Common.sTS_DATA_M14A : Common.sTS_DATA_VIEW_M14A; 
				}else if(fab.equals(Common.sFAB_M14B)){
					return isAll ? Common.sTS_DATA_M14B : Common.sTS_DATA_VIEW_M14B; 
				}
			}
			case Common.sFABSITE_M15 : {
				if(fab.equals(Common.sFAB_M15A)) {
					return isAll ? Common.sTS_DATA_M15A : Common.sTS_DATA_VIEW_M15A;
				}
				else if(fab.equals(Common.sFAB_M15B)){
					return isAll ? Common.sTS_DATA_M15B : Common.sTS_DATA_VIEW_M15B;
				}
			}
			case Common.sFABSITE_M11 : {
				if(fab.equals(Common.sFAB_M11A)) {
					return isAll ? Common.sTS_DATA_M11A : Common.sTS_DATA_VIEW_M11A;
				}
				else if(fab.equals(Common.sFAB_M11B)){
					return isAll ? Common.sTS_DATA_M11B : Common.sTS_DATA_VIEW_M11B;
				}
			}
			case Common.sFABSITE_C2 : {				
				if(fab.equals(Common.sFAB_C2)) {
					return isAll ? Common.sTS_DATA_C2 : Common.sTS_DATA_VIEW_C2;
				}
				else if(fab.equals(Common.sFAB_C2F)){
					return isAll ? Common.sTS_DATA_C2F : Common.sTS_DATA_VIEW_C2F;
				}
			}
			case Common.sFABSITE_IC : {
				if(fab.equals(Common.sFAB_M14A)) {
					return isAll ? Common.sTS_DATA_M14A : Common.sTS_DATA_VIEW_M14A; 
				}else if(fab.equals(Common.sFAB_M14B)){
					return isAll ? Common.sTS_DATA_M14B : Common.sTS_DATA_VIEW_M14B; 
				}else if(fab.equals(Common.sFAB_M16A)){ 
					return isAll ? Common.sTS_DATA_M16A : Common.sTS_DATA_VIEW_M16A;
				}else if(fab.equals(Common.sFAB_M16B)){ 
					return isAll ? Common.sTS_DATA_M16B : Common.sTS_DATA_VIEW_M16B;
				}				
			}
			default : return null;
		}
	}
	
	
}