package com.skhynix.supply.secs.service.impl;

import java.util.List;
import java.util.Map;

import javax.annotation.Resource;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.stereotype.Service;

import com.skhynix.supply.common.Common;
import com.skhynix.supply.common.MachineVo;
import com.skhynix.supply.secs.dao.SecsDAO;
import com.skhynix.supply.secs.service.SecsService;
import com.skhynix.supply.secs.vo.SecsVo;

@Service("secsService")
public class SecsServiceImpl implements SecsService {
	protected Log log = LogFactory.getLog(SecsServiceImpl.class);
	
	@Resource(name="secsDAO")
	SecsDAO Client;

	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 8. 16. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 : Secs 로그 조회
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getDataList(SecsVo secsVo) throws Exception {
		List<Map> dataList = null; 
		long offset 	= (Long.parseLong(secsVo.getPageNum()) - 1) * Long.parseLong(secsVo.getRowNum());
		int   limit 	= Integer.parseInt(secsVo.getRowNum());
		String resultQuery = getQueryParser(secsVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			resultQuery += Common.sPipeLine + "limit " + offset + " " +  limit;		//결과 출력에 대해 limit을 적용한 쿼리 
			resultQuery += Common.sPipeLine + Common.sSort + Common.s_TIME;			//결과 출력에 대해 time sort를 적용한 쿼리
			resultQuery += String.format(Common.sEval, "No", "seq()") + Common.sPlus + offset;
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			dataList = Client.dbExecuteQuery(secsVo.getFabSite(), resultQuery);
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
	private String getQueryParser(SecsVo secsVo) {
		if (secsVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();
		/*sQuery.append(String.format(Common.sTable_From, secsVo.getFrom(), secsVo.getTo(),
				Common.sOrder+ Common.sEqual_1+Common.sAsc+Common.sSpace
				+Common.sSECS_DATA));*/
		sQuery.append(String.format(Common.sTable_From, secsVo.getFrom(), secsVo.getTo(), 
				Common.sOrder+ Common.sEqual_1+Common.sAsc + Common.sParallel + Common.sSpace));	// 200918 hgJeon 병렬화 옵션 적용
		
		// 190107 C2, C2F FAB 선택시 테이블 쿼리 변경
		if (secsVo.getFab()!=null && secsVo.getFab().size() > 0) {
			List<String> fab = secsVo.getFab();
			String fabName = "";
			log.info("fab:"+secsVo.getFab());
			
			for(int i=0;i<secsVo.getFab().size();i++){
//				if(fab.get(i).contains("FAB_B")) {
//					fabName = getTableFromFab(Common.sFAB_SITE, "B");
//				}else if (fab.get(i).contains("FAB_A")) {
//					fabName = getTableFromFab(Common.sFAB_SITE, "A");
//				}/*else if (fab.get(i).contains("M15")) {
//					fabName = Common.sTS_TRANSPORT;
//				}*/
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//fabName = getTableFromFab(Common.sFAB_SITE,fab.get(i));
				fabName = getTableFromFab(secsVo.getFabSite(),fab.get(i)); 
				if(fabName != null && !fabName.isEmpty()) {
					if(i==0){
						sQuery.append(fabName);
					}else if(i==(secsVo.getFab().size()-1)) {
						sQuery.append(Common.sComma + fabName);
					}else{
						sQuery.append(Common.sComma + fabName);
					}
				}
			}
		}
		
		// 5.Add LEVEL
		if (secsVo.getLevel()!=null && secsVo.getLevel().size() > 0) {
			StringBuilder sLevel = new StringBuilder();
			sLevel.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sLEVEL));
			/*log.info("level1:"+sLevel);*/
			for (String s : secsVo.getLevel()) {
				if (s.indexOf(Common.sALL) >= 0) {
					/*sLevel.append(Common.sComma + Common.sDoubleQuotation + "TIME" + Common.sDoubleQuotation
							+Common.sComma + Common.sDoubleQuotation + "INFO" + Common.sDoubleQuotation
							+Common.sComma + Common.sDoubleQuotation + "WARN" + Common.sDoubleQuotation
							+Common.sComma + Common.sDoubleQuotation + "RECV" + Common.sDoubleQuotation
							+Common.sComma + Common.sDoubleQuotation + "SEND" + Common.sDoubleQuotation);*/
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
		if (secsVo.getSecs() != null && !secsVo.getSecs().trim().equals("")) {
			// 200304 hgJeon "," 추가시 multi 검색조건 검색 가능하게	
			if(secsVo.getSecs().contains(Common.sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] textNameArray = secsVo.getSecs().split(Common.sCommaOrigin);
				for(int i=0;i<textNameArray.length;i++){
					if(i==0){
						tempQuery.append(
						Common.sLeftParenthesis + Common.sLeftParenthesis
						+ Common.sSECS + Common.sEquals
						+ Common.sDoubleQuotation +Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis 
						);
					}else if(i==(textNameArray.length-1)){
						tempQuery.append(
						 Common.sOr + Common.sLeftParenthesis
						+ Common.sSECS + Common.sEquals
						+ Common.sDoubleQuotation +Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis + Common.sRightParenthesis
						);
					}else{
						tempQuery.append(
						 Common.sOr + Common.sLeftParenthesis
						+ Common.sSECS + Common.sEquals
						+ Common.sDoubleQuotation +Common.sAsterisk + textNameArray[i].trim() +Common.sAsterisk
						+ Common.sDoubleQuotation + Common.sRightParenthesis
						);
					}
				}sQuery.append(Common.sCRLF + Common.sSearch_0 + tempQuery.toString());
			}else {
				sQuery.append(Common.sCRLF + Common.sSearch_0
						+ Common.sSECS + Common.sEquals
						+ Common.sDoubleQuotation + secsVo.getSecs().trim() 
						+ Common.sDoubleQuotation);
			}
		}
		
		//6-2
		if (secsVo.getHost()!=null && secsVo.getHost().size() > 0) {
			StringBuilder sHost = new StringBuilder();
			sHost.append(Common.sCRLF + String.format(Common.sSearch_in, Common.sHOST));
			
			for (String s : secsVo.getHost()) {
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

		
		// 200304 hgJeon "," 추가시 multi 검색조건 검색 가능하게
		if (secsVo.getText() != null && !secsVo.getText().trim().equals("")) {
			
			if(secsVo.getText().toString().contains(Common.sAsterisk)) {		// 201223 hgJeon text 검색 시 * 문자 제외
				secsVo.setText(secsVo.getText().replaceAll("\\*", Common.sEmpty));
			}
			
			if(secsVo.getText().contains(Common.sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] textNameArray = secsVo.getText().split(Common.sCommaOrigin);
				String condition = Common.sOr;
				// 200305 hgJeon TEXT 검색 시 and, or 조건 검색 기능추가
				if(secsVo.getSecsTextConditionCheckBox() != null && !(secsVo.getSecsTextConditionCheckBox().isEmpty())) {
					condition = secsVo.getSecsTextConditionCheckBox().trim().equals(Common.sOr.trim()) ? Common.sOr : Common.sAnd;
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
						+ Common.sDoubleQuotation +Common.sAsterisk + secsVo.getText().trim() + Common.sAsterisk
						+ Common.sDoubleQuotation );
			}
		}
				
		sQuery.append(Common.sCRLF + Common.sFields + Common.s_TIME + Common.sComma + Common.sTIME_EX 
				+ Common.sComma + Common.sSECS + Common.sComma + Common.sLEVEL + Common.sComma + "S/F"
				+ Common.sComma + "SB" + Common.sComma + "NAME" + Common.sComma + "DATA" 
				+  Common.sComma + Common.sTEXT + Common.sComma + "SKEY" + Common.sComma + "HOST"
				);
		
		return sQuery.toString();
	}
	
	// 200409 hgJeon  
	private String getTableFromFab(String fabSite, String fab) {
				
		switch(fabSite) {
			case Common.sFABSITE_M14 : {
//				if(fab.equals("A")) {
//					return Common.sSECS_DATA;
//				}else { // B 일경우
//					return Common.sSECS_DATA_M16;
//					//return Common.sSECS_DATA_M14B;
//				}
				return Common.sSECS_DATA;
			}
			case Common.sFABSITE_M15 : {
//				if(fab.equals("A")) {
//					return Common.sSECS_DATA_M15;
//				}else { // B 일경우
//					return null;
//				}
				if(fab.equals(Common.sFAB_M15A)) {
					return Common.sSECS_DATA_M15A;
				}else if(fab.equals(Common.sFAB_M15B)) {
					return Common.sSECS_DATA_M15B;
				}
			}
			case Common.sFABSITE_M11 : {
				if(fab.equals(Common.sFAB_M11A)) {
					return Common.sSECS_DATA_M11A;
				}else if(fab.equals(Common.sFAB_M11B)) {
					return Common.sSECS_DATA_M11B;
				}
//				else { // B 일경우
//					return Common.sSECS_DATA_M11B;
//				}
			}
			case Common.sFABSITE_C2 : {
				if(fab.equals(Common.sFAB_C2)) {
					return Common.sSECS_DATA_C2;
				}else if(fab.equals(Common.sFAB_C2F)) {
					return Common.sSECS_DATA_C2F;
				}				
//				else { // B 일경우
//					return Common.sSECS_DATA_C2F;
//				}
			}
			case Common.sFABSITE_IC : {
				if(fab.equals(Common.sFAB_M14A)) {
					return Common.sSECS_DATA;
				}else if(fab.equals(Common.sFAB_M14B)) {
					return Common.sSECS_DATA_M14B;
				}else if(fab.equals(Common.sFAB_M16A)) {
					//return Common.sSECS_DATA_M16;
					return Common.sSECS_DATA_M16A;
				}else if(fab.equals(Common.sFAB_M16B)) {
					//return Common.sSECS_DATA_M16;
					return Common.sSECS_DATA_M16B;
				}
//				else { // B 일경우
//					return Common.sSECS_DATA_M16;
//					//return Common.sSECS_DATA_M14B;
//				}
			}
			default : return null;
		}
	}

	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getSelectList(String fabSite) throws Exception {
		List<Map> selectList = null;
		//String secsNameQuery = "memlookup name=secsList";
		//String secsNameQuery = "memlookup name=machine_list | eval SECSII=MACHINENAME, FAB=SHOPNAME | fields FAB, SECSII";
		//2022.06.08	X0122410 : machine_list에 MACHINETYPE이 null이 아닌것만 보이게
		String secsNameQuery = "memlookup name=machine_list | search isnotnull(MACHINETYPE) | eval SECSII=MACHINENAME, FAB=SHOPNAME | fields FAB, SECSII";
		//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
		selectList = Client.dbExecuteQuery(fabSite, secsNameQuery);
		
		return selectList;
	}

	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getSecsList(String fabSite) throws Exception {
		List<Map> selectList = null;
		//String secsNameQuery = "memlookup name=secsList | sort SECSII";
		//String secsNameQuery = "memlookup name=machine_list | eval SECSII=MACHINENAME, FAB=SHOPNAME | fields FAB, SECSII | sort SECSII";
		//2022.06.08	X0122410 : machine_list에 MACHINETYPE이 null이 아닌것만 보이게 
		String secsNameQuery = "memlookup name=machine_list | search isnotnull(MACHINETYPE) | eval SECSII=MACHINENAME, FAB=SHOPNAME | fields FAB, SECSII | sort SECSII";
		selectList = Client.dbExecuteQuery(fabSite, secsNameQuery);
		
		return selectList;
	}

	@SuppressWarnings("rawtypes")
	@Override
	public List<Map> getSecsFabList(MachineVo machineVo) throws Exception {
		if (machineVo == null) {
			return null;
		} // null exception
		List<Map> selectList = null;
		
		String resultQuery = getSecsFabQuery(machineVo);
		if (resultQuery != null && !(resultQuery.isEmpty())) {
			//2022. 6.16. X0122410 : fab site 추가로 dbExecuteQuery 접속로직 수정
			selectList = Client.dbExecuteQuery(machineVo.getFabSite(), resultQuery);
		}
		return selectList;
	}
	
	private String getSecsFabQuery(MachineVo machineVo){
		StringBuilder sQuery = new StringBuilder();
		//String secsNameQuery = "memlookup name=secsList | sort SECSII";
		//String secsNameQuery = "memlookup name=machine_list | eval SECSII=MACHINENAME, FAB=SHOPNAME | fields FAB, SECSII | sort SECSII";
		//2022.06.08	X0122410 : machine_list에 MACHINETYPE이 null이 아닌것만 보이게
		String secsNameQuery = "memlookup name=machine_list | search isnotnull(MACHINETYPE) | eval SECSII=MACHINENAME, FAB=SHOPNAME | fields FAB, SECSII | sort SECSII";
		sQuery.append(secsNameQuery);

		// Type
		if (machineVo.getSelectFab()!=null && machineVo.getSelectFab().size() > 0) {
			StringBuilder sMachine = new StringBuilder();
			sMachine.append(Common.sCRLF + String.format(Common.sSearch_in, "FAB"));

			for (String s : machineVo.getSelectFab()) {
				if (s.indexOf(Common.sALL) >= 0) {
					sMachine = null;
					break;
				} else {
					
					sMachine.append(Common.sComma + Common.sDoubleQuotation + s.toUpperCase() + Common.sAsterisk + Common.sDoubleQuotation);
//					String fabName = Common.getFabABC("secs", Common.sFAB_SITE, s.toUpperCase());
//					if(!fabName.isEmpty())
//						sMachine.append(Common.sComma + Common.sDoubleQuotation + fabName + Common.sDoubleQuotation);
				}
			}

			if (sMachine != null && !(sMachine.toString().isEmpty())) {
				if (sMachine.toString().indexOf("(") >= 0) {
					sMachine.append(" )");
				} // search in ( ... )
				sQuery.append(sMachine.toString());
			}
		}
		
		return sQuery.toString();
	}

	@Override
	public void getRawLogQueryStop() throws Exception {
		try {
			Client.dbExecuteQueryStop();
		} catch (Exception e) {
			log.info("getRawLogQueryStop Exception!!");
		}
	}
		
}
