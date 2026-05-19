package com.skhynix.supply.res.service;
 
import java.util.List;
import java.util.Map;

import com.skhynix.supply.res.vo.ResCraneVo;
import com.skhynix.supply.res.vo.ResMachineVo;
import com.skhynix.supply.res.vo.ResPortVo;
import com.skhynix.supply.res.vo.ResShelfVo;
import com.skhynix.supply.res.vo.ResStorageFullVo;
import com.skhynix.supply.res.vo.ResVehicleVo;

/**
 * @Package Name   : com.skhynix.supply.res.service
 * @FileName   : ResHistoryService.java
 * @작성일        : 2017. 3. 22. 
 * @작성자        :  최명수
 * @프로그램 설명 : ResourceHistory 로그 조회 인터페이스
 */
public interface ResHistoryService 
{
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 22. 
	 * @작성자     : 최명수
	 * @param    : getDataList 로그 조회
	 * @Method 설명 :
	 * @param ResCraneVo
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(ResCraneVo resHistoryVo)  throws Exception;
	
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 22. 
	 * @작성자     : 최명수
	 * @param    : getDataList 로그 조회
	 * @Method 설명 :
	 * @param ResStorageFullVo
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(ResStorageFullVo resStorageFullVo)  throws Exception;
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 22. 
	 * @작성자     : 최명수
	 * @param    : getDataList 로그 조회
	 * @Method 설명 :
	 * @param ResStorageFullVo
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(ResMachineVo resMachineVo)  throws Exception;
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 22. 
	 * @작성자     : 최명수
	 * @param    : getDataList 로그 조회
	 * @Method 설명 :
	 * @param ResStorageFullVo
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(ResPortVo resPortVo)  throws Exception;
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 22. 
	 * @작성자     : 최명수
	 * @param    : getDataList 로그 조회
	 * @Method 설명 :
	 * @param ResStorageFullVo
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(ResShelfVo resShelfVo)  throws Exception;
	
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 22. 
	 * @작성자     : 최명수
	 * @param    : getDataList 로그 조회
	 * @Method 설명 :
	 * @param ResStorageFullVo
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(ResVehicleVo resVehicleVo)  throws Exception;
}