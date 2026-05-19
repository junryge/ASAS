package com.skhynix.supply.tot.controller;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

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
import com.skhynix.supply.tot.service.TotalService;
import com.skhynix.supply.tot.vo.TotalNewVo;
import com.skhynix.supply.tot.vo.TotalVo;

/**
 * @Package Name : com.skhynix.supply.tot.controller
 * @FileName : TotalController.java
 * @작성일 : 2017. 3. 16.
 * @작성자 : 최명수
 * @프로그램 설명 : 신규 로그 조회 Controller
 */
@Controller
public class TotalNewController {
	protected Log log = LogFactory.getLog(TotalNewController.class);
	@Resource(name = "totalNewService")
	private TotalService totService;

	/**
	 * @Method Name  : totalNewLogList
	 * @작성일     : 2017. 3. 16. 
	 * @작성자     : 최명수
	 * @param    :
	 * @Method 설명 : 신규 로그 조회
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings({ "rawtypes", "unchecked" })
	@RequestMapping(value = "totNew/totalNewLogList")
	public ModelAndView totalNewLogList(@ModelAttribute TotalNewVo param, HttpServletRequest request) throws Exception {
		//log.info("totalNewLogList : Start!!");
		ModelAndView mav = new ModelAndView();
//		String type = request.getParameter("type");
		SimpleDateFormat dateFormat = new SimpleDateFormat("yyyyMMddHHmmss");
		Calendar curTime = Calendar.getInstance();
		String strCurTime = dateFormat.format(curTime.getTime());
		curTime.add(Calendar.MINUTE, -10);
		String strBeforeTenMinTime = dateFormat.format(curTime.getTime());

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
		
		// 변수 초기화 (machineTypes)
		//2021.03.22	X0122410	:	machinetype 리스트를 서버에서 가져와서 보여준다
		List<String> machineTypes = new ArrayList<String>();
//		for (int i = 1; i <= 8; i++) {
//			String result = request.getParameter("machineType" + i);
//			if (result != null && !result.equals("")) {
//				if(result.trim().equals(Common.sALL)){
//					machineTypes.clear();
//					break;
//				}else{
//					machineTypes.add(result);
//				}
//			}
//		}
		String sMachineTypes = request.getParameter("machineTypes");
		if(sMachineTypes != null && !sMachineTypes.trim().isEmpty())
		{
			String[] splitStr = sMachineTypes.split(",");
			if(splitStr[0].trim().equals(Common.sALL))
			{
				machineTypes.clear(); 
			} 
			else
			{
				for(int i=0; i<splitStr.length; i++)
				{
					machineTypes.add(splitStr[i]);
				}	
			}			
		}
		param.setMachineType(machineTypes);

		if (param.getAreaName() == null || param.getAreaName().equals("")) {
			param.setAreaName(Common.sALL);
		}

		if (param.getBayName() == null || param.getBayName().equals("")) {
			param.setBayName(Common.sALL);
		}

		if (param.getPageNum() == null || param.getPageNum().equals("")) {
			param.setPageNum("1");
		}

		if (param.getRowNum() == null || param.getPageNum().equals("")) {
			param.setRowNum("100");
		}

		if (param.getFrom() == null || param.getFrom().equals("")) {
			param.setFrom(strBeforeTenMinTime);
		}

		if (param.getTo() == null || param.getTo().equals("")) {
			param.setTo(strCurTime);
		}

		Paging paging = new Paging(Integer.parseInt(param.getPageNum()), Integer.parseInt(param.getRowNum()));

		List list = totService.getDataList(param);
		if (list != null && list.size() > 0) {
			Map<String, String> resultMap = new HashMap<String, String>();
			resultMap = (Map<String, String>) list.get(0);
			if (resultMap.get("count") != null && !String.valueOf(resultMap.get("count")).equals("")) {
				paging.setNumberOfRecords(Integer.parseInt(String.valueOf(resultMap.get("count"))));
				paging.makePaging();
			}
		}
		mav.addObject("list", list);
		mav.addObject("paging", paging);		
		mav.addObject("param", param);
		mav.addObject("params", param);
		//2021.03.23	X0122410	:	machineTypeInfoList 파리미터 추가		
		//mav.addObject("fabSite", Common.sFAB_SITE);
		mav.setViewName("tot/totalNewLogList");

		return mav;
	}
	
	@SuppressWarnings({ "rawtypes", "unchecked" })
	@RequestMapping(value = "totNew/ajax/totalNewLogList")
	public ModelAndView totalNewLogListAjax(@ModelAttribute TotalNewVo param, HttpServletRequest request) throws Exception {
		log.info("totalNewLogList : Start!!");
		ModelAndView mav = new ModelAndView();
//		String type = request.getParameter("type");
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
		
		// 변수 초기화 (machineTypes)
		//2021.03.22	X0122410	:	machinetype 리스트를 서버에서 가져와서 보여준다
		List<String> machineTypes = new ArrayList<String>();
//		for (int i = 1; i <= 8; i++) {
//			String result = request.getParameter("machineType" + i);
//			if (result != null && !result.equals("")) {
//				if(result.trim().equals(Common.sALL)){
//					machineTypes.add(Common.sSTB);
//					machineTypes.add(Common.sSTOCKER);
//					machineTypes.add(Common.sCONVEYOR);
//					machineTypes.add(Common.sLIFTER);
//					machineTypes.add(Common.sOHT);
//					machineTypes.add(Common.sPROCESS);
//					break;
//				}else{
//					machineTypes.add(result);
//				}
//			}
//		}
		String sMachineTypes = request.getParameter("machineTypes");
		if(sMachineTypes != null && !sMachineTypes.trim().isEmpty())
		{
			String[] splitStr = sMachineTypes.split(",");
			if(splitStr[0].trim().equals(Common.sALL))
			{
				machineTypes.clear(); 
			} 
			else
			{
				for(int i=0; i<splitStr.length; i++)
				{
					machineTypes.add(splitStr[i]);
				}	
			}			
		}
		param.setMachineType(machineTypes);

		if (param.getAreaName() == null || param.getAreaName().equals("")) {
			param.setAreaName(Common.sALL);
		}

		if (param.getBayName() == null || param.getBayName().equals("")) {
			param.setBayName(Common.sALL);
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

		List list = totService.getDataList(param);
		if (list != null && list.size() > 0) {
			Map<String, String> resultMap = new HashMap<String, String>();
			resultMap = (Map<String, String>) list.get(0);
			if (resultMap.get("count") != null && !String.valueOf(resultMap.get("count")).equals("")) {
				paging.setNumberOfRecords(Integer.parseInt(String.valueOf(resultMap.get("count"))));
				paging.makePaging();
			}
		}
		mav.addObject("total", paging.getNumberOfRecords());
		mav.addObject("records", paging.getRecordsPerPage());
		mav.addObject("paging", paging);
		mav.addObject("param", param);
		mav.addObject("params", param);
		mav.addObject("rows", list);
		mav.setViewName("jsonView");

		return mav;
	}
	
	/**
	 * @Method Name : machineNamePop
	 * @작성일 : 2017. 3. 16.
	 * @작성자 : 최명수
	 * @param :
	 * @Method 설명 : machine Name 조회 팝업
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "totNew/pop/machineNamePop")
	public ModelAndView machineNamePop(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		
		//2022. 6.21. X0122410 : fab list 가져오기
		String fabSite = param.getFabSite();
		fabSite = Common.setFabSite(request, fabSite);
		
		List list = new ArrayList<Map>(); 
		list = totService.getSelectList(fabSite);
		mav.addObject("list", list);
		//2021.03.23	X0122410	:	machineTypeInfoList 파리미터 추가		
		//mav.addObject("fabSite", Common.sFAB_SITE);
		mav.setViewName("tot/pop/machineNamePop");
		return mav;
	}
	

	/**
	 * @Method Name  : getCarrierElapsed
	 * @작성일     : 2017. 3. 16. 
	 * @작성자     : 최명수
	 * @param    :
	 * @Method 설명 : Machine 목록 조회( Ajax )
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "totNew/ajax/getCarrierElapsed")
	public ModelAndView getCarrierElapsed(@ModelAttribute TotalNewVo param, HttpServletRequest request) throws Exception {
		System.out.println("getCarrierElapsed 호출 : " + request.getParameter("addQuery"));
		ModelAndView mav = new ModelAndView();
		
		String fabSite = param.getFabSite();
		fabSite = Common.setFabSite(request, fabSite);
		
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
		if(request.getParameter("addQuery") != null && !request.getParameter("addQuery").equals("")){
			list = totService.getDetailDataList(fabSite, request.getParameter("addQuery"));
		}
		mav.addObject("list", list);
		mav.setViewName("jsonView");
		return mav;
	}
}
