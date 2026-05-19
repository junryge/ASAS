package com.skhynix.supply.secs.service;

import java.util.List;
import java.util.Map;

import com.skhynix.supply.common.MachineVo;
import com.skhynix.supply.secs.vo.EiVo;

/**
 * @Package Name   : com.skhynix.supply.secs.service
 * @FileName   : EiService.java
 * @작성일        : 2020. 3. 25. 
 * @작성자        :  전현구
 * @프로그램 설명 : EI_CS_DS 로그 조회 인터페이스
 */

public interface EiService {

	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(EiVo eiVo) throws Exception;
	
	//2022. 6.16. X0122410 : fab site 추가로 fab site 파라미터 추가
	@SuppressWarnings("rawtypes")
	public List<Map> getProcessList(String fabSite) throws Exception;
	
	@SuppressWarnings("rawtypes")
	public List<Map> getSelectProcessList(MachineVo machineVo) throws Exception;
	
	public void getRawLogQueryStop() throws Exception;	// 201106 hgJeon 쿼리 cancel 추가
	
}
