package com.skhynix.supply.secs.service;

import java.util.List;
import java.util.Map;

import com.skhynix.supply.common.MachineVo;
import com.skhynix.supply.secs.vo.SecsVo;

/**
 * @Package Name   : com.skhynix.supply.tot.service
 * @FileName   : TotalService.java
 * @작성일        : 2017. 8. 16. 
 * @작성자        :  전현구
 * @프로그램 설명 : secs 로그 조회 인터페이스
 */
public interface SecsService {
	
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(SecsVo secsVo) throws Exception;
	/**
	 * @Method Name  : getSelectList
	 * @작성일     : 2017. 8. 16. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 :
	 * @return
	 * @throws Exception
	 */
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	public List<Map> getSelectList(String fabSite) throws Exception;
	
	/**
	 * @Method Name  : getSecsList
	 * @작성일     : 2017. 8. 17. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 :
	 * @return
	 * @throws Exception
	 */
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	public List<Map> getSecsList(String fabSite) throws Exception;
	
	/**
	 * @param param 
	 * @Method Name  : getSecsFabList
	 * @작성일     : 2019. 1. 07. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 :
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getSecsFabList(MachineVo machineVo) throws Exception;
	
	public void getRawLogQueryStop() throws Exception;	// 201106 hgJeon 쿼리 cancel 추가

}
