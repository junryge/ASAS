package com.skhynix.supply.tran.service;
 
import java.util.List;
import java.util.Map;

import com.skhynix.supply.tran.vo.TranCmdFailVo;
import com.skhynix.supply.tran.vo.TranJobFailVo;
import com.skhynix.supply.tran.vo.TranVo;

/**
 * @Package Name   : com.skhynix.supply.tot.service
 * @FileName   : TotalService.java
 * @작성일        : 2017. 3. 15. 
 * @작성자        :  angelot
 * @프로그램 설명 : total 로그 조회 인터페이스
 */
public interface TranService 
{
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : angelot
	 * @param    : 로그 조회
	 * @Method 설명 :
	 * @param totVo
	 * @return
	 * @throws Exception
	 */ 
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(TranCmdFailVo cmdFailVo)  throws Exception;

	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : angelot
	 * @param    :
	 * @Method 설명 :getDataList
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	List<Map> getDataList(TranVo tranVo) throws Exception;
	/**
	 * @Method Name  : getTranJobHistoryDetail
	 * @작성일     : 2017. 3. 20. 
	 * @작성자     : 최명수
	 * @param    :
	 * @Method 설명 :getTranJobHistoryDetail
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getTranJobHistoryDetail(TranVo tranVo) throws Exception;
	
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 23. 
	 * @작성자     : 전현구
	 * @param    : 로그 조회
	 * @Method 설명 :
	 * @param jobfailVo
	 * @return
	 * @throws Exception
	 */ 
	@SuppressWarnings("rawtypes")
	List<Map> getDataList(TranJobFailVo jobfailVo) throws Exception;

	/**
	 * @Method Name  : getReasonList
	 * @작성일     : 2017. 4. 5
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 : ReasonList 리스트 조회(Ajax)
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	public List<Map> getReasonList(String fabSite) throws Exception;
	
}