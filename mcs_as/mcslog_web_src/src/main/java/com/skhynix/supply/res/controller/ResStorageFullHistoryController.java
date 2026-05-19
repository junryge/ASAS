/**
 * 
 */
package com.skhynix.supply.res.controller;

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
import com.skhynix.supply.res.service.ResHistoryService;
import com.skhynix.supply.res.vo.ResStorageFullVo;
import com.skhynix.supply.tot.service.TotalService;


/**
 * @Package Name   : com.skhynix.supply.res.controller
 * @FileName   : ResMachineHistoryController.java
 * @작성일        : 2017. 3. 21. 
 * @작성자        :  박민호
 * @프로그램 설명 : Machine 이력 조회 컨트롤러
 */
@Controller
public class ResStorageFullHistoryController {
	protected Log log = LogFactory.getLog(ResStorageFullHistoryController.class);
	@Resource(name = "resStorageFullHistoryServiceImpl")
	private ResHistoryService resHistoryService;
	
	@Resource(name = "totalService")
	private TotalService totService;


	/**
	 * @Method Name : carrierLocLogList
	 * @작성일 : 2017. 3. 16.
	 * @작성자 : 박민호
	 * @param :
	 * @Method 설명 : machine 이력 조회
	 * @param param
	 * @param request
	 * @return
	 * @throws Exception
	 */
	@RequestMapping(value = "res/storageLogList")
	public ModelAndView carrierLocLogList(@ModelAttribute ResStorageFullVo param, HttpServletRequest request)	throws Exception {
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
		
		//2021. 4. 9. X0122410 : list info 가져오기
		//fab		
		mav.addObject("fabs", Common.getFabList("res", sFabSite));
		param.setFab(Common.getBasicFabList("res", sFabSite));
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
		//2021.03.23	X0122410	:	machineTypeInfoList 파리미터 추가
		//mav.addObject("fabSite", Common.sFAB_SITE);
		mav.setViewName("res/storageLogList");
		return mav;
	}
	
	@SuppressWarnings("rawtypes")
	@RequestMapping(value = "res/ajax/getStorageLogList")
	public ModelAndView getStorageLogList(@ModelAttribute ResStorageFullVo param, HttpServletRequest request)	throws Exception {
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
		
		//2021. 4. 9, X0122410 : fab가져오기		
		//List<String> fabList = Common.getFabList("res", Common.sFAB_SITE);		
		List<String> fabList = Common.getFabList("res", sFabSite);
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

		//2021. 4. 9, X0122410 : level가져오기
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
		
		// 변수 초기화 (machineTypes)
		List<String> machineTypes = new ArrayList<String>();
		//2021.03.22	X0122410	:	machinetype 리스트를 서버에서 가져와서 보여준다
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

		param.setPageNum(page);
		param.setRowNum(rows);

		if (param.getFrom() == null || param.getFrom().equals("")) {
			param.setFrom(strBeforeTenMinTime);
		}

		if (param.getTo() == null || param.getTo().equals("")) {
			param.setTo(strCurTime);
		}

		Paging paging = new Paging(Integer.parseInt(param.getPageNum()), Integer.parseInt(param.getRowNum()));
		List list = resHistoryService.getDataList(param);
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
