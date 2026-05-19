package com.skhynix.supply.mat.service;
 
import java.util.List;
import java.util.Map;

import com.skhynix.supply.mat.vo.MaterialVo;

/**
 * @Package Name   : com.skhynix.supply.mat.service
 * @FileName   : MaterialService.java
 * @작성일        : 2017. 3. 16. 
 * @작성자        :  최명수
 * @프로그램 설명 : Carrier 위치 이력 조회 인터페이스
 */
public interface MaterialService 
{
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 16. 
	 * @작성자     : 최명수
	 * @param    : 로그 조회
	 * @Method 설명 :
	 * @param totVo
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(MaterialVo matVo)  throws Exception;
}