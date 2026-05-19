package com.skhynix.supply.tran.controller;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.List;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.servlet.ModelAndView;

import com.skhynix.supply.common.Common;
import com.skhynix.supply.common.Paging;
import com.skhynix.supply.tran.service.TranService;
import com.skhynix.supply.tran.vo.TranVo;


/**
 * @Package Name   : com.skhynix.supply.tran.controller
 * @FileName   : TranCmdHistoryController.java
 * @작성일        : 2017. 3. 20. 
 * @작성자        :  최명수
 * @프로그램 설명 : 반송 CMD 이력 조회 컨트롤러
 */
@Controller
public class TranCmdHistoryController {
	protected Log log = LogFactory.getLog(TranCmdHistoryController.class);
	@Resource(name = "tranCmdHistoryService")
	private TranService tranService;
	
//	@Resource(name = "totalService")
//	private TotalService totService;

	@RequestMapping(value = "tran/returnCmdLogList")
	public ModelAndView returnCmdLogList(@ModelAttribute TranVo param, HttpServletRequest request) 	throws Exception {
		ModelAndView mav = new ModelAndView();
		//List bayNameList = totService.getBayNameList();
		//List machineNameList = totService.getMachineNameList();
		//mav.addObject("bayNameList", bayNameList);
		//mav.addObject("machineNameList", machineNameList);
		
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
		mav.addObject("fabs", Common.getFabList("tran", sFabSite));
		param.setFab(Common.getBasicFabList("tran", sFabSite));
//		param.setTransportFab(Common.getBasicFabList("tran",Common.sFAB_SITE));
//		param.setFromFab(Common.getBasicFabList("tran",Common.sFAB_SITE));
//		param.setToFab(Common.getBasicFabList("tran",Common.sFAB_SITE));
		
		mav.addObject("param", param);
		mav.addObject("params", param);
		//2021.03.23	X0122410	:	machineTypeInfoList 파리미터 추가
		//mav.addObject("fabSite", Common.sFAB_SITE);
		mav.setViewName("tran/returnCmdLogList");
		return mav;
	}
	
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tran/ajax/getReturnCmdLogList")
	public ModelAndView getReturnCmdLogList(@ModelAttribute TranVo param, HttpServletRequest request) throws Exception {
		log.info("getReturnCmdLogList : Start!!");
		ModelAndView mav = new ModelAndView();
		SimpleDateFormat dateFormat = new SimpleDateFormat("yyyyMMddHHmmss");
		Calendar curTime = Calendar.getInstance();
		String strCurTime = dateFormat.format(curTime.getTime());
		curTime.add(Calendar.MINUTE, -10);
		String strBeforeTenMinTime = dateFormat.format(curTime.getTime());
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

		//2021. 4. 5, X0122410 : fab 조건 추가
		//List<String> fabList = Common.getFabList("tran", Common.sFAB_SITE);		
		List<String> fabList = Common.getFabList("tran", sFabSite);
		if(request.getParameter("fab1") !=null && !request.getParameter("fab1").equals("") && request.getParameter("fab1").equals(Common.sALL)) {
			param.setFab(fabList);
		} else {
			List<String> fabs = new ArrayList<String>();
			for (int i=1; i<=fabList.size() + 1; i++) {
				String result = request.getParameter("fab"+i);
				if(result != null && !result.equals("")) {
					fabs.add(result);
				}
			}
			param.setFab(fabs);
		}
		
		// 변수 초기화 (transMachineType)
		List<String> transportMachineType = new ArrayList<String>();
		if (request.getParameter("transportMachineType1") != null && !request.getParameter("transportMachineType1").equals("") && request.getParameter("transportMachineType1").equals(Common.sALL)) {
			transportMachineType.clear();
		}else{
			String sMachineTypes = request.getParameter("transportMachineTypes");
			if(sMachineTypes != null && !sMachineTypes.trim().isEmpty())
			{
				String[] splitStr = sMachineTypes.split(",");
				if(splitStr[0].trim().equals(Common.sALL))
				{
					transportMachineType.clear(); 
				} 
				else
				{
					for(int i=0; i<splitStr.length; i++)
					{
						transportMachineType.add(splitStr[i]);
					}	
				}			
			}
		}
		param.setTransportMachineType(transportMachineType);
		
		// 변수 초기화 (fromMachineType)
		List<String> fromMachineType = new ArrayList<String>();
		if (request.getParameter("fromMachineType1") != null && !request.getParameter("fromMachineType1").equals("")
				&& request.getParameter("fromMachineType1").equals(Common.sALL)) {
			fromMachineType.clear();
		}else{
			String sMachineTypes = request.getParameter("fromMachineTypes");
			if(sMachineTypes != null && !sMachineTypes.trim().isEmpty())
			{
				String[] splitStr = sMachineTypes.split(",");
				if(splitStr[0].trim().equals(Common.sALL))
				{
					fromMachineType.clear(); 
				} 
				else
				{
					for(int i=0; i<splitStr.length; i++)
					{
						fromMachineType.add(splitStr[i]);
					}	
				}			
			}
		}
		param.setFromMachineType(fromMachineType);
		
		// 변수 초기화 (toMachineType)
		List<String> toMachineType = new ArrayList<String>();
		if (request.getParameter("toMachineType1") != null && !request.getParameter("toMachineType1").equals("") && request.getParameter("toMachineType1").equals(Common.sALL)) {
			toMachineType.clear();
		}else{
			String sMachineTypes = request.getParameter("toMachineTypes");
			if(sMachineTypes != null && !sMachineTypes.trim().isEmpty())
			{
				String[] splitStr = sMachineTypes.split(",");
				if(splitStr[0].trim().equals(Common.sALL))
				{
					toMachineType.clear(); 
				} 
				else
				{
					for(int i=0; i<splitStr.length; i++)
					{
						toMachineType.add(splitStr[i]);
					}	
				}			
			}
		}
		param.setToMachineType(toMachineType);
		
		List<String> states = new ArrayList<String>();
		if (request.getParameter("state1") != null && !request.getParameter("state1").equals("") && request.getParameter("state1").equals(Common.sALL)) {
			states.clear();
		}else{
			String sStates = request.getParameter("states");
			if(sStates != null && !sStates.trim().isEmpty())
			{
				String[] splitStr = sStates.split(",");
				if(splitStr[0].trim().equals(Common.sALL))
				{
					states.clear(); 
				} 
				else
				{
					for(int i=0; i<splitStr.length; i++)
					{
						states.add(splitStr[i]);
					}	
				}			
			}
		}
		param.setState(states);

		if (param.getTransportAreaName() == null || param.getTransportAreaName().equals("")) {
			param.setTransportAreaName(Common.sALL);
		}

		if (param.getTransportBayName() == null || param.getTransportBayName().equals("")) {
			param.setTransportBayName(Common.sALL);
		}
		
		if (param.getFromAreaName() == null || param.getFromAreaName().equals("")) {
			param.setFromAreaName(Common.sALL);
		}

		if (param.getFromBayName() == null || param.getFromBayName().equals("")) {
			param.setFromBayName(Common.sALL);
		}
		
		if (param.getToAreaName() == null || param.getToAreaName().equals("")) {
			param.setToAreaName(Common.sALL);
		}

		if (param.getToBayName() == null || param.getToBayName().equals("")) {
			param.setToBayName(Common.sALL);
		}

		param.setPageNum(page);
		param.setRowNum(rows);

		if (param.getFrom() == null || param.getFrom().equals("")) {
			param.setFrom(strBeforeTenMinTime);
		}

		if (param.getTo() == null || param.getTo().equals("")) {
			param.setTo(strCurTime);
		}

		Paging paging = new Paging(Integer.parseInt(param.getPageNum()), Integer.parseInt(param.getRowNum()));
		List list = tranService.getDataList(param);
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

}
