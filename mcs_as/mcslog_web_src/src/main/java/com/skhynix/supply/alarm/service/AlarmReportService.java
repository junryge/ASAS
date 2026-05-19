package com.skhynix.supply.alarm.service;
 
import java.util.List;
import java.util.Map;

import com.skhynix.supply.alarm.vo.AlarmReportVo;


/**
 * @Package Name   : com.skhynix.supply.alarm.service
 * @FileName   : AlarmReportService.java
 * @작성일        : 2017. 3. 22. 
 * @작성자        :  최명수
 * @프로그램 설명 : AlarmReport 로그 조회 인터페이스
 */
public interface AlarmReportService 
{
	/**
	 * @Method Name  : getDataList
	 * @작성일     : 2017. 3. 22. 
	 * @작성자     : 최명수
	 * @param    : AlarmReport 로그 조회
	 * @Method 설명 :
	 * @param alarmReportVo
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	public List<Map> getDataList(AlarmReportVo alarmReportVo)  throws Exception;
}