package com.skhynix.supply.tot.controller;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.List;
import java.util.Map;

import javax.annotation.Resource;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpSession;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.bind.annotation.ResponseBody;
import org.springframework.web.servlet.ModelAndView;
import org.springframework.web.servlet.i18n.SessionLocaleResolver;

import com.skhynix.supply.common.Common;
import com.skhynix.supply.common.FabVo;
import com.skhynix.supply.common.MachineVo;
import com.skhynix.supply.common.Paging;
import com.skhynix.supply.tot.service.TotalService;
import com.skhynix.supply.tot.vo.TotalVo;

/**
 * @Package Name : com.skhynix.supply.tot.controller
 * @FileName : TotalController.java
 * @작성일 : 2017. 3. 13.
 * @작성자 : 박민호
 * @프로그램 설명 : total 로그 조회 Controller
 */
@Controller
public class TotalController {
	protected Log log = LogFactory.getLog(TotalController.class);
	@Resource(name = "totalService")
	private TotalService totService;
	
	@Autowired
    SessionLocaleResolver localeResolver;

    private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(TotalController.class);
    
//    @RequestMapping(value = "/i18n.do", method = RequestMethod.GET) 
//    public String i18n(Locale locale, HttpServletRequest request, Model model) 
//    { 
//    	log.info("i18n : Start!!!");
//    	// RequestMapingHandler로 부터 받은 Locale 객체를 출력해 봅니다.
//    	logger.info("Welcome i18n! The client locale is {}.", locale);
//    	// localeResolver 로부터 Locale 을 출력해 봅니다.
//    	logger.info("Session locale is {}.", localeResolver.resolveLocale(request));
//    	logger.info("site.title : {}", messageSource.getMessage("site.title", null, "default text", locale));
//    	logger.info("site.count : {}", messageSource.getMessage("site.count", new String[] {"첫번째"}, "default text", locale));
//    	logger.info("not.exist : {}", messageSource.getMessage("not.exist", null, "default text", locale));
//    	//logger.info("not.exist 기본값 없음 : {}", messageSource.getMessage("not.exist", null, locale));
//    	// JSP 페이지에서 EL 을 사용해서 arguments 를 넣을 수 있도록 값을 보낸다.
//    	model.addAttribute("siteCount", messageSource.getMessage("msg.first", null, locale));
//    	model.addAttribute("siteLang", Common.getLocale());
//    	
//    	log.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
//		logger.info("Welcome i18n! The client locale is {}.", Common.getLocale());
//		logger.info("Session locale is {}.", localeResolver.resolveLocale(request));
//		log.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
//		
//    	return "i18n";    	
//    }

	/**
	 * @Method Name  : totalLogList
	 * @작성일     : 2017. 3. 14. 
	 * @작성자     : 박민호
	 * @param    :
	 * @Method 설명 : total 로그 조회 화면 이동
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@RequestMapping(value = "tot/totalLogList")
	public ModelAndView totalLogList(@ModelAttribute TotalVo param, HttpServletRequest request) 	throws Exception {
		ModelAndView mav = new ModelAndView();
		//String uuid = request.getParameter("uuid");
		
		// 2021.03.24	X0122410 : 아래코드 적용안됨, checked처리부분이  javascript에 별도처리 되어 있음
//		List<String> machineTypes = new ArrayList<String>();
//		machineTypes.add("ZIPTOWER");
//		machineTypes.add(Common.sOHT);
//		mav.addObject("machineTypes", machineTypes);		
		//2021.03.23	X0122410	:	machineTypeInfoList 파리미터 추가		
		//mav.addObject("fabSite", Common.sFAB_SITE)
		
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
		mav.addObject("fabs", Common.getFabList("tot", sFabSite));
		param.setFab(Common.getBasicFabList("tot", sFabSite));
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
		mav.setViewName("tot/totalLogList");
		return mav;
	}
		
	/**
	 * @Method Name  : getTotalLogList
	 * @작성일     : 2017. 3. 27. 
	 * @작성자     : 박민호
	 * @param    :
	 * @Method 설명 : total 로그 조회(ajax)
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/ajax/getTotalLogList")
	public ModelAndView getTotalLogList(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {
//		log.info("totalLogList : Start!!");
		ModelAndView mav = new ModelAndView();
//		String type = request.getParameter("type");
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
		
		//20180615 변수초기화 (fab)
		//List<String> fabList = Common.getFabList("tot", Common.sFAB_SITE);
		List<String> fabList = Common.getFabList("tot", sFabSite);
		if(request.getParameter("fab1") !=null && !request.getParameter("fab1").equals("") && request.getParameter("fab1").equals(Common.sALL)) {
//			fabs.add(Common.sFAB_A);
//			fabs.add(Common.sFAB_B);
//			if(Common.sFAB_SITE.equals("M14")) {
//				fabs.add(Common.sFAB_C);
//			}
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

		// 변수 초기화 (level)
		List<String> levels = new ArrayList<String>();
		for (int i = 1; i <= Common.Levels.size() + 1; i++) {
			String result = request.getParameter("level" + i);
			if (result != null && !result.equals("")) {
				levels.add(result);
			}
		}
		param.setLevel(levels);
//		if (request.getParameter("level1") != null && !request.getParameter("level1").equals("") && request.getParameter("level1").equals(Common.sALL)) {
//			/*levels.add(Common.sWELL);
//			levels.add(Common.sWARN);
//			levels.add(Common.sERROR);
//			levels.add(Common.sFATAL);
//			levels.add(Common.sDEBUG);
//			levels.add(Common.sINFO);
//			levels.add(Common.sFINE);*/
//			levels.add(Common.sALL);
//			param.setLevel(levels);
//		} else {
//			for (int i = 1; i <= Common.Levels.size() + 1; i++) {
//				String result = request.getParameter("level" + i);
//				if (result != null && !result.equals("")) {
//					levels.add(result);
//				}
//			}
//			param.setLevel(levels);
//		}
//		if (request.getParameter("level1")==null && request.getParameter("level2")==null &&
//				request.getParameter("level3")==null && request.getParameter("level4")==null &&
//				request.getParameter("level5")==null && request.getParameter("level6")==null &&
//				request.getParameter("level7")==null && request.getParameter("level8")==null){
//			List<String> level = new ArrayList<String>();
//			level.add(Common.sWELL);
//			level.add(Common.sWARN);
//			level.add(Common.sERROR);
//			level.add(Common.sFATAL);
//			param.setLevel(level);
//		}
		// 변수 초기화 (machineTypes)
		List<String> machineTypes = new ArrayList<String>();
		//2021.03.22	X0122410	:	machinetype 리스트를 서버에서 가져와서 보여준다
//		for (int i = 1; i <= 10; i++) { 
//			String result =	request.getParameter("machineType" + i); 
//			if (result != null && !result.equals("")) { 
//				if(result.trim().equals(Common.sALL)){
//					machineTypes.clear(); 
//					break; 
//				}
//				else
//				{ 
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
	
	@RequestMapping(value = "tot/ajax/getTotalLogListStop")
	@ResponseBody
	public void getTotalLogListStop(HttpServletRequest request) throws Exception {
		//log.info("totalLogList : Emergency Stop!!"); 
		
		totService.getTotalLogListStop();  
	}

	/**
	 * @Method Name : machineNamePop
	 * @작성일 : 2017. 3. 14.
	 * @작성자 : 박민호
	 * @param :
	 * @Method 설명 : machine Name 조회 팝업
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/pop/machineNamePop")
	public ModelAndView machineNamePop(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		//2021.03.23	X0122410	:	machineTypeInfoList 파리미터 추가		
		//mav.addObject("fabSite", Common.sFAB_SITE);
		List list = totService.getMachineTypeFromFab(new MachineVo());		
		mav.addObject("machineTypeInfoList", list);
		mav.setViewName("tot/pop/machineNamePop");
		return mav;
	}
	
	/**
	 * @Method Name  : getMachineList
	 * @작성일     : 2017. 3. 15. 
	 * @작성자     : 박민호
	 * @param    :
	 * @Method 설명 : Machine 목록 조회( Ajax )
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/ajax/getMachineList")
	public ModelAndView getMachineList(@ModelAttribute MachineVo param, HttpServletRequest request) throws Exception {
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
		list = totService.getMachineNameList(param);
		mav.setViewName("jsonView");
		mav.addObject("list", list);
		return mav;
	}
	
	/**
	 * @Method Name  : getMachineListMachineTypeNotNull
	 * @작성일     : 2022. 6. 8. 
	 * @작성자     : 강병민
	 * @param    :
	 * @Method 설명 : Machine 목록 조회( Ajax )
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/ajax/getMachineListMachineTypeNotNull")
	public ModelAndView getMachineListMachineTypeNotNull(@ModelAttribute MachineVo param, HttpServletRequest request) throws Exception {
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
		list = totService.getMachineNameListMachineTypeNotNull(param);
		mav.setViewName("jsonView");
		mav.addObject("list", list);
		return mav;
	}
	
	/**
	 * @Method Name  : getBayFromArea
	 * @작성일     : 2020. 8. 26. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 : bay 목록 조회( Ajax ) area 변경 시 마다 대응되는 bay List
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/ajax/getBayFromArea")
	public ModelAndView getBayFromArea (@ModelAttribute MachineVo param, HttpServletRequest request) throws Exception {
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
		list = totService.getBayFromAreaList(param);
		mav.setViewName("jsonView");
		mav.addObject("list", list);
		return mav;
	}
	
	/**
	 * @Method Name  : getAreaFromFab
	 * @작성일     : 2020. 8. 27. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 : bay 목록 조회( Ajax ) area 변경 시 마다 대응되는 bay List
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/ajax/getAreaFromFab")
	public ModelAndView getAreaFromFab (@ModelAttribute MachineVo param, HttpServletRequest request) throws Exception {
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
		list = totService.getAreaFromFabList(param);
		mav.setViewName("jsonView");
		mav.addObject("list", list);
		return mav;
	}
	/**
	 * @Method Name  : getMachineTypeFromFab
	 * @작성일     : 2021.03.23 
	 * @작성자     : X0122410
	 * @param    :
	 * @Method 설명 : MachineType List
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/ajax/getMachineTypeFromFab")
	public ModelAndView getMachineTypeFromFab(@ModelAttribute MachineVo param, HttpServletRequest request)	throws Exception {
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
		list = totService.getMachineTypeFromFab(param);
		mav.setViewName("jsonView");
		mav.addObject("list", list);
		return mav;
	}
	
	/**
	 * @Method Name  : getFabFromFabSite
	 * @작성일     : 2022.06.16 
	 * @작성자     : X0122410
	 * @param    :
	 * @Method 설명 : fab List
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/ajax/getFabFromFabSite")
	public ModelAndView getFabFromFabSite(@ModelAttribute FabVo param, HttpServletRequest request)	throws Exception {
		ModelAndView mav = new ModelAndView();
		
		//2022. 6.16. X0122410 : fab list 가져오기
		String fabSite = param.getFabSite();
		fabSite = Common.setFabSite(request, fabSite);
		
		String menu = param.getMenu();
		List list = new ArrayList<Map>();
		List basic_list = new ArrayList<Map>();
		list = Common.getFabList(menu, fabSite);
		basic_list = Common.getBasicFabList(menu, fabSite);
		mav.setViewName("jsonView");
		mav.addObject("list", list);
		mav.addObject("basic_list", basic_list);
		return mav;
	}
	
	/**
	 * @Method Name  : main
	 * @작성일     : 2017. 3. 27. 
	 * @작성자     : 박민호
	 * @param    :
	 * @Method 설명 : 메인 페이지 이동
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@RequestMapping(value = "tot/main")
	public ModelAndView main(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {				
		log.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
		log.info("main : Start!!");		
		logger.info("The client locale is {}.", Common.getLocale());
		logger.info("Session locale is {}.", localeResolver.resolveLocale(request));
		
		HttpSession session = request.getSession();        
		logger.info("Session ID: " + session.getId());
		logger.info("Creation Time: " + new Date(session.getCreationTime()));
		logger.info("Last Accessed Time: " + new Date(session.getLastAccessedTime()));
		//2022. 6.15. X0122410 : fab site session으로 변경		
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
		logger.info("FAB SITE: " + sFabSite);
		log.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
		
		ModelAndView mav = new ModelAndView();
		mav.addObject("fabsites", Common.FabSites);
		mav.addObject("param", param);		
		mav.addObject("location", Common.getLocale().toString());
		mav.setViewName("tot/main");
		return mav;
	}
	
	@RequestMapping(path= "tot/{query}" ,method=RequestMethod.GET)
	public ModelAndView getRequest(@ModelAttribute TotalVo param, @PathVariable String query, HttpServletRequest request) throws Exception {
		log.info("totalLogList : Start!!");
		ModelAndView mav = new ModelAndView();
		log.info(query);
		
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
		
		mav.addObject("param", param);
		mav.addObject("location", Common.getLocale().toString());		
		mav.setViewName("tot/main");
		return mav;
	}

	/**
	 * @Method Name  : main
	 * @작성일     : 2019. 1. 09. 
	 * @작성자     : 전현구
	 * @param    :
	 * @Method 설명 : 초기화 정보
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/filter/ajax/getAreaList")
	public @ResponseBody List<List> getAreaList(String fabSite) throws Exception {
		List areaNameList = totService.getAreaNameList(fabSite);
		
		List<List> result = new ArrayList<List>();
		result.add(areaNameList);
		return result;
	}
	
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/filter/ajax/getBayList")
	public @ResponseBody List<List> getBayList(String fabSite) throws Exception {
		List bayNameList = totService.getBayNameList(fabSite);
		
		List<List> result = new ArrayList<List>();
		result.add(bayNameList);
		return result;
	}
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/filter/ajax/getMachineNameList")
	public @ResponseBody List<List> getMachineNameList(String fabSite) throws Exception {
		List machineNameList = totService.getMachineNameList(fabSite);
		
		List<List> result = new ArrayList<List>();
		result.add(machineNameList);
		return result;
	}
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/filter/ajax/getCommMsgNameList")
	public @ResponseBody List<List> getCommMsgNameList(String fabSite) 	throws Exception {
		List commMsgNameList = totService.getCommMsgNameList(fabSite);
		
		List<List> result = new ArrayList<List>();
		result.add(commMsgNameList);
		return result;
	}
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/filter/ajax/getMessageNameList")
	public @ResponseBody List<List> getMessageNameList(String fabSite) 	throws Exception {
		List messageNameList = totService.getMessageNameList(fabSite);
		
		List<List> result = new ArrayList<List>();
		result.add(messageNameList);
		return result;
	}
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "tot/filter/ajax/getOperationNameList")
	public @ResponseBody List<List> getOperationNameList(String fabSite) 	throws Exception {
		List operationNameList = totService.getOperationNameList(fabSite);
		
		List<List> result = new ArrayList<List>();
		result.add(operationNameList);
		return result;
	}
	
		
	/**
	 * @Method Name : machineNamePop
	 * @작성일 : 2017. 3. 14.
	 * @작성자 : 박민호
	 * @param :
	 * @Method 설명 : machine Name 조회 팝업
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@RequestMapping(value = "tot/pop/filterPop")
	public ModelAndView filterPop(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		mav.setViewName("tot/pop/filterPop");
		return mav;
	}
	
	/**
	 * @Method Name  : settingPop
	 * @작성일     : 2017. 4. 18. 
	 * @작성자     : 박민호
	 * @param    :
	 * @Method 설명 : 환경 설정 팝업
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@RequestMapping(value = "common/pop/settingPop")
	public ModelAndView settingPop(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		mav.setViewName("common/pop/settingPop");
		return mav;
	}
	
	@RequestMapping(value = "tot/dashboard/elapsedAnalysis")
	public ModelAndView elapsed(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		mav.setViewName("tot/elapsedAnalysis");
		return mav;
	}
	@RequestMapping(value = "tot/dashboard/compressAnalysis")
	public ModelAndView elapsed2(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		mav.setViewName("tot/compressAnalysis");
		return mav;
	}
	@RequestMapping(value = "tot/dashboard/monitor")
	public ModelAndView monitor(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		mav.setViewName("tot/monitor");
		return mav;
	}
	@RequestMapping(value = "tot/dashboard/elapsed3")
	public ModelAndView elapsed3(@ModelAttribute TotalVo param, HttpServletRequest request) throws Exception {
		ModelAndView mav = new ModelAndView();
		mav.setViewName("tot/dashboard3");
		return mav;
	}
}
