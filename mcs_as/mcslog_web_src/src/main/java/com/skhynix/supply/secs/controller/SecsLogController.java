package com.skhynix.supply.secs.controller;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;
import java.util.Map;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.servlet.ModelAndView;

import com.skhynix.supply.common.Common;
import com.skhynix.supply.common.MachineVo;
import com.skhynix.supply.common.Paging;
import com.skhynix.supply.secs.service.SecsService;
import com.skhynix.supply.secs.vo.SecsVo;

@Controller
public class SecsLogController {
	protected Log log = LogFactory.getLog(SecsLogController.class);

	@Resource(name = "secsService")
	private SecsService secsService;
	
	/**
	 * @Method Name : SECSLogList
	 * @작성일 : 2017. 8. 16.
	 * @작성자 : 전현구
	 * @param :
	 * @Method 설명 : SECS 로그 조회
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@RequestMapping(value = "secs/secsLogList")
	public ModelAndView secsLocLogList(@ModelAttribute SecsVo param, HttpServletRequest request) 	throws Exception {
		ModelAndView mav = new ModelAndView();
		
		//2022. 6.15. X0122410 : fab site session으로 변경 
		mav.addObject("fabsites", Common.FabSites);
//		String sFabSite = Common.getFabSite(request);
//		param.setFabSite(sFabSite);
		String sFabSite = param.getFabSite();
		if(sFabSite == null || sFabSite.length() == 0)
		{
			sFabSite = Common.getFabSite(request);
			param.setFabSite(sFabSite);
		}
		else			
		{
			sFabSite = Common.setFabSite(request, sFabSite);
		}
		
		//2021. 4. 2. X0122410 : list info 가져오기
		//fab
		mav.addObject("fabs", Common.getFabList("secs", sFabSite));
		param.setFab(Common.getBasicFabList("secs", sFabSite));
		//level
		List<String> list = new ArrayList<String>();
		list.add(Common.sTIME);
		list.add(Common.sINFO);		
		list.add(Common.sWARN);
		list.add(Common.sRECV);
		list.add(Common.sSEND);
		mav.addObject("levels", list);
		//2022.03.25	X0122410	default로 ALL이 선택되게끔 수정
		List<String> level = new ArrayList<String>();
		level.add(Common.sALL);
		param.setLevel(level);
		
		mav.addObject("param", param);
		mav.addObject("params", param);
		mav.setViewName("secs/secsLogList");
		return mav;
	}
	
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "/secs/ajax/getsecsLogList.do")
	public ModelAndView getList(@ModelAttribute SecsVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		SimpleDateFormat dateFormat = new SimpleDateFormat("yyyyMMddHHmmss");
		Calendar curTime = Calendar.getInstance();
		String strCurTime = dateFormat.format(curTime.getTime());
		curTime.add(Calendar.MINUTE, -10);
		String strBeforeTenMinTime = dateFormat.format(curTime.getTime());
		int delayTime = Integer.parseInt(request.getParameter("searchDelay"));
		
		if(delayTime > 0) {
			Common.searchDelayTime = delayTime * 1000;
		}
		
		String page = request.getParameter("page");
		if (page == null || page.equals("")) {
			page = "1";
		}

		String rows = request.getParameter("rows");
		if (rows == null || rows.equals("")) {
			rows = "100";
		}
		
		//2022. 6.15. X0122410 : fab site session으로 변경 
		mav.addObject("fabsites", Common.FabSites);
//		String sFabSite = Common.getFabSite(request);
//		param.setFabSite(sFabSite);
		String sFabSite = param.getFabSite();
		if(sFabSite == null || sFabSite.length() == 0)
		{
			sFabSite = Common.getFabSite(request);
			param.setFabSite(sFabSite);
		}
		else			
		{
			sFabSite = Common.setFabSite(request, sFabSite);
		}
		
		//20190105 변수초기화 (fab)
		//List<String> fabList = Common.getFabList("secs", Common.sFAB_SITE);		
		List<String> fabList = Common.getFabList("secs", sFabSite);
		if(request.getParameter("secsFab1") !=null && !request.getParameter("secsFab1").equals("") && request.getParameter("secsFab1").equals(Common.sALL)) {
			param.setFab(fabList);
		} else {			
			List<String> fabs = new ArrayList<String>();
			for (int i=1; i<=fabList.size() + 1; i++) {
				String result = request.getParameter("secsFab"+i);
				if(result != null && !result.equals("")) {
					fabs.add(result);
				}
			}
			param.setFab(fabs);
		}
		
		// 변수 초기화 (host)
		List<String> host = new ArrayList<String>();
		for (int i = 1; i <= 3; i++) {
			String result = request.getParameter("host" + i);
			if (result != null && !result.equals("")) {
				host.add(result);
			}
		}
		param.setHost(host);
		
		// 변수 초기화 (level)
		List<String> levels = new ArrayList<String>();
		for (int i = 1; i <= Common.Levels.size() + 1; i++) {
			String result = request.getParameter("level" + i);
			if (result != null && !result.equals("")) {
				levels.add(result);
			}
		}
		param.setLevel(levels);
		
		// 변수 초기화 (machineTypes)
		/*
		List<String> machineTypes = new ArrayList<String>();
		for (int i = 1; i <= Common.Levels.size() + 1; i++) {
			String result = request.getParameter("machineType" + i);
			if (result != null && !result.equals("")) {
				if(result.trim().equals(Common.sALL)){
					machineTypes.clear();
					break;
				}else{
					machineTypes.add(result);
				}
			}
		}
		*/
		/*param.setMachineType(machineTypes);*/

		/*if (param.getAreaName() == null || param.getAreaName().equals("")) {
			param.setAreaName(Common.sALL);
		}

		if (param.getBayName() == null || param.getBayName().equals("")) {
			param.setBayName(Common.sALL);
		}*/

		param.setPageNum(page);
		param.setRowNum(rows);

		if (param.getFrom() == null || param.getFrom().equals("")) {
			param.setFrom(strBeforeTenMinTime);
		}

		if (param.getTo() == null || param.getTo().equals("")) {
			param.setTo(strCurTime);
		}

		Paging paging = new Paging(Integer.parseInt(page), Integer.parseInt(param.getRowNum()));
		List list = secsService.getDataList(param);
		if (list != null && list.size() > 0) {
			paging.setNumberOfRecords(Paging.nTotalCount);
			paging.makePaging();
		}
		mav.addObject("page", paging.getCurrentPageNo());
		mav.addObject("total", paging.getNumberOfRecords());
		mav.addObject("records", paging.getRecordsPerPage());
		mav.addObject("rows", list);
		mav.setViewName("jsonView");
		return mav;
	}
	
	/**
	 * @Method Name  : getSecsList
	 * @작성일     : 2017. 8. 17
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 : SecsList 조회(Ajax)
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/filter/ajax/getSecsList")
	public @ResponseBody List<List> getSecsList(String fabSite) throws Exception {
		List secsList = secsService.getSecsList(fabSite);	// 20220621	X0122410	fabSite 추가		
		List<List> result = new ArrayList<List>();
		result.add(secsList);
		return result;
	}
	
	/**
	 * @Method Name  : getSecsList
	 * @작성일     : 2019. 1. 07
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 : SecsList 조회(Ajax)
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/filter/ajax/getSecsFabList")
	public ModelAndView getSecsFabList(@ModelAttribute MachineVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		
		//2022. 6.15. X0122410 : fab site session으로 변경 
		mav.addObject("fabsites", Common.FabSites);
//		String sFabSite = Common.getFabSite(request);
//		param.setFabSite(sFabSite);
		String sFabSite = param.getFabSite();
		if(sFabSite == null || sFabSite.length() == 0)
		{
			sFabSite = Common.getFabSite(request);
			param.setFabSite(sFabSite);
		}
		else			
		{
			sFabSite = Common.setFabSite(request, sFabSite);
		}
		
		List list = new ArrayList<Map>();
		list = secsService.getSecsFabList(param);
		
		mav.setViewName("jsonView");
		mav.addObject("list", list);
		return mav;
	}
	
	@RequestMapping(value = "ei/ajax/getSecsQueryStop")
	@ResponseBody
	public void getSecsQueryStop(HttpServletRequest request) throws Exception {
		//log.info("eiLogList : Emergency Stop!!"); 
		
		secsService.getRawLogQueryStop();  
	}
	
}
