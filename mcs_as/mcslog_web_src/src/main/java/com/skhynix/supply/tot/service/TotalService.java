package com.skhynix.supply.tot.service;
 
import java.util.List;
import java.util.Map;

import com.skhynix.supply.common.MachineVo;
import com.skhynix.supply.tot.vo.TotalNewVo;
import com.skhynix.supply.tot.vo.TotalVo;

/**
 * @Package Name   : com.skhynix.supply.tot.service
 * @FileName   : TotalService.java
 * @작성일        : 2017. 3. 15. 
 * @작성자        :  박민호
 * @프로그램 설명 : total 로그 조회 인터페이스
 */
public interface TotalService 
{
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : mwlee
	 * @param    : 로그 조회
	 * @Method 설명 :
	 * @param totVo
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(TotalVo totVo)  throws Exception;
	
	/**
	 * @Method Name  : getTotalLogListStop
	 * @작성일     : 2018. 7. 05. 
	 * @작성자     : mwlee
	 * @param    : 로그 조회 취소
	 * @Method 설명 :
	 * @param totVo
	 * @return
	 * @throws Exception
	 */
	public void getTotalLogListStop(/*TotalVo totVo*/)  throws Exception;
	
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : mwlee
	 * @param    : 신규로그 조회
	 * @Method 설명 :
	 * @param totVo
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(TotalNewVo totVo)  throws Exception;
	
	/**
	 * @Method Name  : getDetailDataList
	 * @작성일     : 2017. 3. 16. 
	 * @작성자     : mwlee
	 * @param    : 신규로그 조회
	 * @Method 설명 :
	 * @param totVo
	 * @return
	 * @throws Exception
	 */
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	public List<Map> getDetailDataList(String fabSite, String addQuery) throws Exception;
	/**
	 * @Method Name  : getXmlList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 최명수
	 * @param    :
	 * @Method 설명 : MESSAGE / SECSII 상세 조회
	 * @param totVo
	 * @return
	 * @throws Exception
	 */
	/*public List<Map> getXmlList(TotalVo totVo)  throws Exception; 사용안함 주석처리*/ 
	
	
	/**
	 * @Method Name  : getSelectList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 최명수
	 * @param    :
	 * @Method 설명 :
	 * @return
	 * @throws Exception
	 */
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	public List<Map> getSelectList(String fabSite)  throws Exception;
	/**
	 * @Method Name  : getBayNameList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 박민호
	 * @param    :
	 * @Method 설명 : BayName 리스트 조회
	 * @return
	 * @throws Exception
	 */
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	public List<Map> getBayNameList(String fabSite) throws Exception;
	/**
	 * @Method Name  : getMachineNameList 
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 최명수
	 * @param    :
	 * @Method 설명 : MachineName 리스트 조회
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getMachineNameList(MachineVo machineVo) throws Exception; 
	/**
	 * @Method Name  : getMachineNameListMachineTypeNotNull 
	 * @작성일     : 2022. 6. 8. 
	 * @작성자     : 강병민
	 * @param    :
	 * @Method 설명 : MachineName 리스트 조회
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getMachineNameListMachineTypeNotNull(MachineVo machineVo) throws Exception;
	/**
	 * @Method Name  : getMachineNameList 
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 최명수
	 * @param    :
	 * @Method 설명 : MachineName 리스트 조회
	 * @return
	 * @throws Exception
	 */
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	public List<Map> getMachineNameList(String fabSite) throws Exception; 
	
	/**
	 * @Method Name  : getCommMsgNameList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 박민호
	 * @param    :
	 * @Method 설명 : CommMsgName 리스트 조회
	 * @return
	 * @throws Exception
	 */
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	public List<Map> getCommMsgNameList(String fabSite) throws Exception;
	/**
	 * @Method Name  : getMessageNameList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 박민호
	 * @param    :
	 * @Method 설명 :
	 * @return
	 * @throws Exception
	 */
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	public List<Map> getMessageNameList(String fabSite) throws Exception;
	/**
	 * @Method Name  : getMachineNameListByType
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 최명수
	 * @param    :
	 * @Method 설명 :getMachineNameListByType
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getMachineNameListByType(TotalVo totVo)  throws Exception;
	/**
	 * @Method Name  : getMachineNameListByTypeMachineTypeNotNull
	 * @작성일     : 2022. 6. 8. 
	 * @작성자     : 강병민
	 * @param    :
	 * @Method 설명 :getMachineNameListByTypeMachineTypeNotNull
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getMachineNameListByTypeMachineTypeNotNull(TotalVo totVo)  throws Exception;
	/**
	 * @Method Name  : getXmlListGroup
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 최명수
	 * @param    :
	 * @Method 설명 :
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	/*public List getXmlListGroup(TotalVo param) throws Exception; 사용안함 주석처리*/
	
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	List<Map> getOperationNameList(String fabSite) throws Exception;

	/**
	 * @Method Name  : getAreaNameList
	 * @작성일     : 2019. 01. 09. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 :getAreaNameList
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	List<Map> getAreaNameList(String sFabSite) throws Exception;
	
	/**
	 * @Method Name  : getBayFromArea
	 * @작성일     : 2020. 08. 26. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 :
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	List<Map> getBayFromAreaList(MachineVo machineVo) throws Exception;
	
	/**
	 * @Method Name  : getAreaFromFab
	 * @작성일     : 2020. 08. 27. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 :
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	List<Map> getAreaFromFabList(MachineVo machineVo) throws Exception;
	
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
	public List<Map> getMachineTypeFromFab(MachineVo machineVo) throws Exception;
}