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
import com.skhynix.supply.secs.service.EiService;
import com.skhynix.supply.secs.vo.EiVo;
import com.skhynix.supply.tot.vo.TotalVo;

@Controller
public class EiLogController {
	protected Log log = LogFactory.getLog(EiLogController.class);
	
	@Resource(name="eiService")
	private EiService eiService;

	@RequestMapping(value = "ei/eiLogList")
	public ModelAndView eiLocLogList(@ModelAttribute EiVo param, HttpServletRequest request) 	throws Exception {
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
		mav.addObject("fabs", Common.getFabList("ei", sFabSite));
		param.setFab(Common.getBasicFabList("ei", sFabSite));
		//level
		mav.addObject("levels", Common.Levels);				
		List<String> level = new ArrayList<String>();
		level.add(Common.sWELL);
		level.add(Common.sWARN);
		level.add(Common.sERROR);
		level.add(Common.sFATAL);
		param.setLevel(level);
		
		mav.addObject("param", param);
		mav.addObject("params", param);
		mav.setViewName("ei/eiLogList");
		return mav;
	}
	
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "/ei/ajax/getEiLogList.do")
	public ModelAndView getList(@ModelAttribute EiVo param, HttpServletRequest request) throws Exception {
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
		//List<String> fabList = Common.getFabList("ei", Common.sFAB_SITE);
		List<String> fabList = Common.getFabList("ei", sFabSite);
		if(request.getParameter("eiFab1") !=null && !(request.getParameter("eiFab1").isEmpty()) && request.getParameter("eiFab1").equals(Common.sALL)) {
			param.setFab(fabList);
		} else {
			List<String> fabs = new ArrayList<String>();
			for (int i=1; i<=fabList.size() + 1; i++) {
				String result = request.getParameter("eiFab"+i);
				if(result != null && !result.equals("")) {
					fabs.add(result);
				}
			}
			param.setFab(fabs);
		}
		
		//200325 hgJeon (logType)
		List<String> logType = new ArrayList<String>();
		if(request.getParameter("logType1") !=null && !(request.getParameter("logType1").isEmpty()) && request.getParameter("logType1").equals(Common.sALL)) {
			logType.add("TS");	// 200918 hgJeon add TS.log option
			logType.add("EI");
			logType.add("CS");
			logType.add("DS");
			param.setLog(logType);
		}else {
			for(int i = 1; i <=5; i++) {
				String result = request.getParameter("logType" + i);
				if(result != null && !(result.equals(""))) {
					logType.add(result);
				}
			}
			param.setLog(logType);
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
		

		param.setPageNum(page);
		param.setRowNum(rows);

		if (param.getFrom() == null || param.getFrom().equals("")) {
			param.setFrom(strBeforeTenMinTime);
		}

		if (param.getTo() == null || param.getTo().equals("")) {
			param.setTo(strCurTime);
		}

		Paging paging = new Paging(Integer.parseInt(page), Integer.parseInt(param.getRowNum()));
		List list = eiService.getDataList(param);
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
	
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/filter/ajax/getProcessList")
	public @ResponseBody List<List> getSecsList(String fabSite) throws Exception {
		List ProcessList = eiService.getProcessList(fabSite);
		
		List<List> result = new ArrayList<List>();
		result.add(ProcessList);
		return result;
	}
	
	@RequestMapping(value = "ei/pop/textDetailPop")
	public ModelAndView filterPop(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		mav.setViewName("ei/pop/textDetailPop");
		return mav;
	}
	
	@RequestMapping(value = "ei/pop/textAreaPop")
	public ModelAndView textFilterPop(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		mav.setViewName("ei/pop/textAreaPop");
		return mav;
	}
	
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/filter/ajax/getSelectProcessList")
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
		list = eiService.getSelectProcessList(param);
		
		mav.setViewName("jsonView");
		mav.addObject("list", list);
		return mav;
	}
	
	@RequestMapping(value = "ei/ajax/getEiQueryStop")
	@ResponseBody
	public void getEiQueryStop(HttpServletRequest request) throws Exception {
		//log.info("eiLogList : Emergency Stop!!"); 
		
		eiService.getRawLogQueryStop();  
	}
	
}
