<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ include file="/WEB-INF/views/common-taglib.jspf"%>
    <div class="contents_wrap" id="body_<c:out value="${param.uuid }" />">
        <!-- Location Information -->
        <div class="loc_info_basic">
            <span class="location_box">
                <a href="#" class="location"><span class="loc_info_ico loc_info_ico_home"></span>Home</a>
            </span>
            <span class="loc_info_ico loc_info_ico_arr_depth"></span>
            <span class="location_box">
                <a href="#" class="location">Material</a>
            </span>
            <span class="loc_info_ico loc_info_ico_arr_depth"></span>
            <span class="location_box">
                <a href="#" class="location"><spring:message code="site.carrierLocLogList" text="default text" /></a>
            </span>
        </div>
        <!-- //Location Information -->
        <!-- Page Title -->
        <table class="page_tit">
            <tr>
                <td class="tit_area">
                    <div class="tit"><spring:message code="site.carrierLocLogList" text="default text" /></div>
                </td>
            </tr>
        </table>
        <!-- //Page Title -->
        <!-- Search Type01 -->
        <!-- Sub Title -->
        <div class="lay_item vert">
        <form id="searchForm" name="searchForm" method="post" >
        <input type="hidden" id="fabSite" name="fabSite" value="" />
        <input type="hidden" id="type" name="type" value="" />
        <input type="hidden" id="page" name="page" value="1" />
        <input type="hidden" name="machineName" value="" />
        <input type="hidden" id="filter" name="filter" value="01" />
        <input type="hidden" id="uuid" name="uuid" value="<c:out value="${param.uuid }" />" />
                    <div class="lay_item_box">
                        	<div id="unfold_filter_view_wrap" class="lay_item_left" style="display:none;width:24px;">
                                <a id="unfold_filter_view" class="btn_fix btn_arr_right " style="margin-top:20px;"></a>
                            </div>
                            <div id="filter_view" class="lay_item_left" style="width:350px">
                                <div class="tree_set">
                                    <div class="tree_top">
                                        <!-- Tab Type02 -->
                                        <div class="tab_type02" id="tree_set_tab">
                                            <ul class="tab_list">
                                                <li class="tab_item">
                                                    <a class="tab_link" rel="tree_set_tab_contents1">Filter View</a>
                                                </li>
                                                <a id="fold_filter_view" class="btn_fix btn_arr_left " style="float:right;"></a>
                                                <div id="resetBtn" class="mini ui primary button" style="width:75px;float: right;margin-right: 10px;float:right">
													<i class="erase icon"></i>reset
												</div>
                                            </ul>
                                        </div>
                                    <!-- //Tab Type02 -->
                                    <!-- Tab contents -->
                                    <div class="tab_contents_wrap" rel="tree_set_tab">
                                        <div class="tab_contents" id="tree_set_tab_contents1">
                                            <!-- Search Type01 -->
                                            <!-- //Search Type01 -->
                                            <div class="tree_wrap">
                                            	<!-- 2021. 04. 01, X0122410 fab 선택box -->
                 								<div class="srch_type01">
                									<div class="condition_area">
                                                        <table class="condition_table" summary="검색조건 테이블">
								                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
								                            <tbody>
								                                <tr>
								                                    <td class="condition_t_head_top" colspan="3">
								                                    	<i class="minus square icon"></i>
								                                    	<span>FAB</span>
								                                    </td>
								                                </tr>
								                                <tr>
								                                	<th scope="col" class="condition_t_head">FAB</th>
								                                    <td class="condition_t_data">
							                                    	 	<!-- 2022. 6. 16, X0122410 : FabSite 리스트 이용 -->
																		<c:forEach items="${fabsites}" var="fabSite" varStatus="status">
																			<c:set var="num" value="${status.index}"/>
																			<c:set var="isVal" value="F" />
																			<c:forEach items="${params.fabSite}" var="item">
																			  <c:if test="${item eq fabSite}">
																				<c:set var="isVal" value="T" />
																			  </c:if>
																			</c:forEach>
																			<input type=radio class="jqForm" id="rdoFabSite<c:out value="${num}"/>" name="rdoFabSite" <c:if test="${isVal eq 'T'}">checked="checked"</c:if> value="<c:out value="${fabSite}"/>" ><label for="fabSite<c:out value="${num}"/>"><c:out value="${fabSite}"/></label><BR>
																		</c:forEach>
								                                    </td>								                                    						                                       
								                                    <td class="condition_t_data" id="tdFab">
								                                    	<input type="checkbox" class="jqForm" id="fab1" name="fab1" value="ALL"><label for="fab1">ALL</label><BR>
								                                    	<!-- 2021. 4. 5, X0122410 : Fabs 리스트 이용 -->								                                    
							                                    	 	<c:forEach  items="${fabs}" var="fab" varStatus="status">
																	 		<c:set var="num" value="${status.index + 2}"/>
																	 		<c:set var="isVal" value="F" />
																			<c:forEach var="item" items="${params.fab}">																			
																			  <c:if test="${item eq fab}">																			  	
																			    <c:set var="isVal" value="T" />
																			  </c:if>																			  
																			</c:forEach>
																			<input type="checkbox" class="jqForm" id="fab<c:out value="${num}"/>" name="fab<c:out value="${num}"/>" <c:if test="${isVal eq 'T'}">checked="checked"</c:if> value="<c:out value="${fab}"/>" ><label for="fab<c:out value="${num}"/>"><c:out value="${fab}"/></label><BR>
				                                            			</c:forEach>
								                                    </td>  
								                                </tr>
								                            </tbody>
								                        </table>
							                        </div>
                   								</div>
                                            <div class="srch_type01">
        									<div class="condition_area">
                                                <table class="condition_table" summary="검색조건 테이블">
					                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
					                            <tbody id="test">
					                                <tr>
					                                    <td class="condition_t_head_top" colspan="3">
					                                    	<i class="minus square icon"></i>
					                                    	<span>Machine</span>
					                                    </td>
					                                </tr>
					                                <tr>
					                                    <td class="condition_t_data" colspan="3">
					                                    	<input type="checkbox" class="jqForm" id="singleFilter" name="singleFilter" value="01" checked="checked" ><label for="singleFilter">Single Filter</label>
					                                    </td>
					                                </tr>
					                                <tr class="singleFilter">
														<th scope="col" class="condition_t_head">AREA</th>
														<td class="condition_t_data" colspan="2">
															<!-- 2021. 4. 5, X0122410 : 리스트를 서버에서 가져와서 보여준다 -->
															<select class="areaName_machine" id="areaName" name="areaName" style="width: 143px" >																
																<option value="ALL" <c:if test="${param.areaName == 'ALL' }" >selected="selected"</c:if>>ALL</option>
															</select>
														</td>
													</tr>
					                                <tr class="singleFilter" >
					                                    <th scope="col" class="condition_t_head">BAY</th>
					                                    <td class="condition_t_data" colspan="2" >
					                                         <select class="bayName" id="bayName" name="bayName" style="width: 143px" >
					                                            <option value="ALL" <c:if test="${param.bayName == 'ALL' }" >selected="selected"</c:if>>ALL</option>
					                                        </select>
					                                    </td>
					                                </tr>
					                                <tr  id="singleFilterChkBoxFab" class="singleFilter" >
														<th scope="col" class="condition_t_head">Type</th>
													</tr>
					                                <tr class="singleFilter" >
					                                	<th scope="col" class="condition_t_head">NAME</th>
					                                    <td class="condition_t_data" colspan="2">
					                                         <select class="machineName1" id="machineName1" name="machineName1" style="width: 143px" >
					                                            <option value="">NOTDESIGNATED</option>
					                                        </select>
					                                    </td>
					                                </tr>
					                                <tr>
					                                    <td class="condition_t_data" colspan="3">
					                                    	<input type="checkbox" class="jqForm" id="multiFilter" name="multiFilter" value="02" ><label for="multiFilter">Multi Filter</label>
					                                    </td>
					                                </tr>
					                                <tr class="multiFilter" >
					                                 	<td class="condition_t_data" colspan="3">
					                                    	 <input type="text" id="machineName2" name="machineName2"  style="width:163px" value="" disabled />
					                                         <div id="machineBtn" class="mini ui primary button" style="width:93px;float: right;margin-left: 4px">
																<i class="tasks icon"></i>Machine
															 </div>
					                                    </td>
					                                </tr>
					                            </tbody>
					                        </table>
					                        </div>
           								</div>
           								<div class="srch_type01">
        									<div class="condition_area">
                                                <table class="condition_table" summary="검색조건 테이블">
					                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
					                            <tbody>
					                                <tr>
					                                    <td class="condition_t_head_top" colspan="2">
					                                    	<i class="minus square icon"></i>
					                                    	<span>Condition</span>
					                                    </td>
					                                </tr>
					                                <tr>
					                                	<th scope="col" class="condition_t_head" style="width:200px">Carrier Name</th>
					                                    <td class="condition_t_data">
					                                         <input type="text" id="carrier" name="carrier" value="<c:out value="${param.carrier }" />" />
					                                    </td>
					                                </tr>
					                                <tr>
					                                	<th scope="col" class="condition_t_head">Lot ID</th>
					                                    <td class="condition_t_data">
					                                         <input type="text" id="lotId" name="lotId" value="<c:out value="${param.carrier }" />" />
					                                    </td>
					                                </tr>
					                                <tr>
					                                	<th scope="col" class="condition_t_head">Command ID</th>
					                                    <td class="condition_t_data">
					                                         <input type="text" id="commandId" name="commandId" value="<c:out value="${param.commandId }" />" />
					                                    </td>
					                                </tr>
					                                <tr>
					                                	<th scope="col" class="condition_t_head">Unit Name</th>
					                                    <td class="condition_t_data">
					                                         <input type="text" id="unit" name="unit" value="<c:out value="${param.unit }" />" />
					                                    </td>
					                                </tr>
					                            </tbody>
					                        </table>
					                        </div>
           								</div>
           								<div class="srch_type01">
        									<div class="condition_area">
                                                <table class="condition_table" summary="검색조건 테이블">
					                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
					                            <tbody>
					                                <tr>
					                                    <td class="condition_t_head_top" colspan="2">
					                                    	<i class="minus square icon"></i>
					                                    	<span>Time Range</span>
					                                    </td>
					                                </tr>
					                                <tr>
					                                    <td class="condition_t_data" colspan="2">
					                                    	<input type="radio" class="jqForm" id="time1<c:out value="${param.uuid }" />" name="time" value="01" <c:if test="${param.time == '01' }" >checked="checked"</c:if> ><label for="time1<c:out value="${param.uuid }" />">Last 10 Minutes</label>
					                                    	<div id="pasteBtn" class="mini ui primary button" style="width:65px;float: right;margin-left: 4px;padding-left: 10px;" title="paste">
															  <i class="paste icon"></i>Paste
															</div>
															<div id="copyBtn" class="mini ui primary button" style="width:65px;float: right;margin-left: 4px;padding-left: 10px;" title="copy">
															  <i class="copy icon"></i>Copy
															</div>
					                                    	<br>
                            								<input type="radio" class="jqForm" id="time2<c:out value="${param.uuid }" />" name="time" value="02" <c:if test="${param.time == '02' }" >checked="checked"</c:if> ><label for="time2<c:out value="${param.uuid }" />">Last 1 Hour</label><br>
                            								<input type="radio" class="jqForm" id="time3<c:out value="${param.uuid }" />" name="time" value="03" <c:if test="${param.time == '03' }" >checked="checked"</c:if> ><label for="time3<c:out value="${param.uuid }" />">Last 1 Day</label><br>
                            								<%-- <input type="radio" class="jqForm" id="time4<c:out value="${param.uuid }" />" name="time" value="04" <c:if test="${param.time == '04' }" >checked="checked"</c:if> ><label for="time4<c:out value="${param.uuid }" />">Specified Range</label> --%>
                            								<input type="hidden" id="from" name="from" />
                            								<input type="hidden" id="to" name="to" />
					                                    </td>
					                                </tr>
					                                <tr>
					                                	<th scope="col" class="condition_t_head" style="width:60px">Start</th>
					                                    <td class="condition_t_data" >
					                                    	<input type="text" class="inp_date" id="fromDt<c:out value="${param.uuid }" />" name="fromDt" value="<c:out value="${param.fromDt }" />" />
					                                          &nbsp;<input type="" id="fromHour" name="fromHour" class="onlynum" value="<c:out value="${param.fromHour }" />"  style="width:30px" maxlength="2" />:<input type="" id="fromMin" name="fromMin" class="onlynum" value="<c:out value="${param.fromMin }" />" style="width:30px" maxlength="2" />:<input type="" id="fromSec" name="fromSec" class="onlynum" value="<c:out value="${param.fromSec }" />" style="width:30px" maxlength="2" /><br>
					                                    </td>
					                                </tr>
					                                <tr>
					                                	<th scope="col" class="condition_t_head" >End</th>
					                                    <td class="condition_t_data" >
					                                    	<input type="text" class="inp_date" id="toDt<c:out value="${param.uuid }" />" name="toDt" value="<c:out value="${param.toDt }" />" />
					                                        &nbsp;<input type="" id="toHour" name="toHour" class="onlynum" value="<c:out value="${param.toHour }" />" style="width:30px" maxlength="2" />:<input type="" id="toMin" name="toMin" class="onlynum" value="<c:out value="${param.toMin }" />" style="width:30px" maxlength="2" />:<input type="" id="toSec" name="toSec" class="onlynum" value="<c:out value="${param.toSec }" />" style="width:30px" maxlength="2" /><br>
					                                    </td>
					                                </tr>
					                                <tr>
							                        	<td class="condition_t_data" colspan="2" style="text-align: center;">
			                                    			<div class="mini ui left labeled icon button prevTime"  id="prevTime">
																<i class="left arrow icon"></i>Prev
														    </div>
			                                    			<div class="mini ui right labeled icon button nextTime"  id="nextTime">
																<i class="right arrow icon"></i>Next
														    </div>
							                            </td>
							                        </tr>
					                            </tbody>
					                        </table>
					                        </div>
           								</div>
                                    </div>
                                    <div>
                                    	   <div>
                                            	<div style="padding: 10px 2px;">
			                                    	<div  class="ui primary button" id="searchBtn" >
			                                    		<i class="search icon"></i>Search
			                                    	</div>					
			                                    </div>
                                            </div>
                                    </div>
                               </div>
                            </div>
                            <!-- //Tab contents -->
                           </div>
                            </div>
                        </div>
                        <div class="lay_item_right">
                            <!-- Option Title -->
                            <div class="opt_tit">
                                <div class="opt_tit_left">
                                    <div class="elmt">
                                        <i class="minus square icon large fixed" style="color:#ccd2de"></i>
                                        <span class="txt">LIST
                                        </span>
                                    </div>
                                </div>
                                <div class="opt_tit_right">
                                    <div class="elmt">
                                            <div id="downloadLink" onclick="downloadExcel(data<c:out value="${param.uuid }" />);" class="mini ui primary button" style="width:85px;float: right;margin-left: 4px;white-space:nowrap;">
												<i class="file excel outline icon"></i>Excel
											</div>
                                        </div>
                                    </div>
                            	</div>
                            <!-- //Option Title -->
                            <div id="grid_container<c:out value="${param.uuid }" />">
                                <div id="list<c:out value="${param.uuid }" />" class="gridForResize_single" style="width:100%;height:915px; background: white; outline: 0; border: 1px solid gray;"></div>
                            	<c:import url="/WEB-INF/views/common/slickGridPager.jsp" charEncoding="utf-8" />
                    	</div>
                 </div>
        </div>
        </form>
    </div>
</div>
<script type="text/javascript">
	$content = $("#body_${param.uuid }");
	$(document).ready(function(){
		$content.find('#logInfo').hide();
		init<c:out value="${param.uuid }" />();
		
		// 페이징 마우스 over 효과
		$content.find(".ui-icon-container")
		.hover(function () {
		  $(this).toggleClass("ui-state-hover");
		});
		
		// 이전 페이지 조회
		$content.find(".ui-icon-seek-prev").click(function(){
			console.log("prev");
			var page = Number($content.find("#page").val())- 1;
			if(page < 1){
				page = 1;
			}
			$content.find("#page").val(page);
			$content.find("#pageTxt").text(page);
			getLogList<c:out value="${param.uuid }" />(page);
			
		});
		
		// 다음 페이지 조회
		$content.find(".ui-icon-seek-next").click(function(){
			console.log("next");
			var page = Number($content.find("#page").val()) + 1;
			$content.find("#page").val(page);
			$content.find("#pageTxt").text(page);
			getLogList<c:out value="${param.uuid }" />(page);
		});
		
		// Source Machine > \ AREA 셀렉트 값 변경 이벤트
		$content.find("#areaName").change(function(){
			var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
			getBayFromArea(_fabSite,"fab", "areaName", "bayName");	// 2021. 04. 01. X0122410 :fab 추가
			getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");	// 2021. 04. 01. X0122410 :fab 추가
		});
		
		// Source Machine > \ BAY 셀렉트 값 변경 이벤트
		$content.find("#bayName").change(function(){
			var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
			getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");
		});
		
		// Source Machine > \ Type 체크박스 클릭 이벤트
		// 2021. 03. 31. X0122410.	수정 : 동적바인딩으로 변환
		/* $content.find(":checkbox[name^=machineType]").click(function(){
			var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
			var val = $(this).val();
			if(val == "ALL"){
				$content.find(":checkbox[name^=machineType]:gt(0)").prop("checked",false);
			}else{
				$content.find(":checkbox[name^=machineType]:eq(0)").prop("checked",false);
			}
			getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");
		}); */
		$content.on("click",":checkbox[name^=machineType]", function(){		
			var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
			var val = $(this).val();
			if(val == "ALL"){ // ALL 체크시, 다른 체크 박스 해제
				$content.find(":checkbox[name^=machineType]:gt(0)").prop("checked",false);
			}else{ // 다른 체크박스 체크시 , ALL 체크박스 해제				
				var tmpChk = 0;
				$content.find(":checkbox[name^=machineType]:checked").each(function(){
					tmpChk += 1;
				});
				if( tmpChk > 0){
					$content.find(":checkbox[name^=machineType]:eq(0)").prop("checked",false);
				}else{
					$content.find(":checkbox[name^=machineType]:eq(0)").prop("checked",true);
				}
			}
			getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");
		});
		
		// 20220621 FAB SITE 클릭 이벤트
		$content.find('input[name="rdoFabSite"]').change(function() {
			//var _fabSite = $(this).val();
			var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
			
			getFabFromFabSite("mat", _fabSite, "fab", "tdFab");
			getMachineTypeFromFab(_fabSite,"fab", "machineType", "singleFilterChkBoxFab");				
			getAreaFromFab(_fabSite,"fab", "areaName");
			getBayFromArea(_fabSite,"fab", "areaName", "bayName");
			getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");
		});
		
		// 2021. 03. 31. X0122410.	FAB 클릭 이벤트
		$content.on("click", ":checkbox[name^=fab]", function(){
			var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
			var val = $(this).val();
			if(val == "ALL"){ // ALL 체크시, 다른 체크 박스 해제
				$content.find(":checkbox[name^=fab]:gt(0)").prop("checked",false);
				$content.find(":checkbox[name^=fab]:eq(0)").prop("checked",true);
			}else{  // 다른 체크박스 체크시 , ALL 체크박스 해제
				var tmpChk = 0;
				$content.find(":checkbox[name^=fab]:checked").each(function(){
					tmpChk += 1;
				});
				if( tmpChk > 0){
					$content.find(":checkbox[name^=fab]:eq(0)").prop("checked",false);
				}else{
					$content.find(":checkbox[name^=fab]:eq(0)").prop("checked",true);
				}
			}
			
			// 2021. 03. 31. X0122410.	fab별로 machinetype list 가져오기
			getMachineTypeFromFab(_fabSite,"fab", "machineType", "singleFilterChkBoxFab");				
			getAreaFromFab(_fabSite,"fab", "areaName");					// 200827 hgJeon Fab 변경 시 areaList 변경 추가 
			getBayFromArea(_fabSite,"fab", "areaName", "bayName");	// 200826 hgJeon Area 변경 시 bayList 변경 추가
			getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");
		});
		
		// LEVEL 클릭 이벤트
		$content.find(":checkbox[name^=level]").click(function(){
			var val = $(this).val();
			if(val == "ALL"){ // ALL 체크시, 다른 체크 박스 해제
				$content.find(":checkbox[name^=level]:gt(0)").prop("checked",false);
			}else{  // 다른 체크박스 체크시 , ALL 체크박스 해제
				$content.find(":checkbox[name^=level]:eq(0)").prop("checked",false);
			}
		});
		
		// copy 버튼 클릭
		$content.find("#copyBtn").click(function(){
			var from = $content.find("#fromDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#fromHour").val() +$content.find("#fromMin").val()+$content.find("#fromSec").val();
			var to = $content.find("#toDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#toHour").val() +$content.find("#toMin").val()+$content.find("#toSec").val();
			setCookie("mcsLogFromDt",from,null,"/",null);
			setCookie("mcsLogToDt",to,null,"/",null);
		});
		
		// paste 버튼 클릭
		$content.find("#pasteBtn").click(function(){
			var gFrom = getCookie("mcsLogFromDt");
			var gTo = getCookie("mcsLogToDt");
			if(gFrom != ""){
				var fromDt = gFrom.substr(0,4)+"."+gFrom.substr(4,2)+"."+gFrom.substr(6,2);
				var fromHour = gFrom.substr(8,2);
				var fromMin = gFrom.substr(10,2);
				var fromSec = gFrom.substr(12,2);
				$content.find("#fromDt<c:out value="${param.uuid }" />").val(fromDt);
				$content.find("#fromHour").val(fromHour);
				$content.find("#fromMin").val(fromMin);
				$content.find("#fromSec").val(fromSec);
			}
			if(gTo != ""){
				var toDt = gTo.substr(0,4)+"."+gTo.substr(4,2)+"."+gTo.substr(6,2);
				var toHour = gTo.substr(8,2);
				var toMin = gTo.substr(10,2);
				var toSec = gTo.substr(12,2);
				$content.find("#toDt<c:out value="${param.uuid }" />").val(toDt);
				$content.find("#toHour").val(toHour);
				$content.find("#toMin").val(toMin);
				$content.find("#toSec").val(toSec);
			}
		});
		
		// 조회 버튼 클릭 
		$content.find("#searchBtn").click(function(){
			data<c:out value="${param.uuid }" /> = [];
			getLogList<c:out value="${param.uuid }" />(1);
		});
		
		$content.find("#machineBtn").click(function(){
			if($(this).hasClass("disabled")){
				return false;					
			}
			var url = "<c:url value='/tot/pop/machineNamePop.do' />";
			openPopup(url , 600 , 610,function(data){
				console.log(JSON.stringify(data));
				$content.find("#machineName2").val(data);
			});
		});
		
		// single filter 클릭 이벤트)
		$content.find("#singleFilter").click(function(){
			var isChk = $(this).is(":checked");
			if(isChk){
				$content.find("#filter").val("01");
			}else{
				$content.find("#filter").val("02");
			}
			setFilter();
		});
	
		// multi filter 클릭 이벤트)
		$content.find("#multiFilter").click(function(){
				var isChk = $(this).is(":checked");
				if(isChk){
					$content.find("#filter").val("02");
					
				}else{
					$content.find("#filter").val("01");
				
				}
				setFilter();
			});
		
		// 테이블 컬럼 더블클릭 이벤트
		$content.find(".board_list_data").dblclick(function() {
			var colName = $(this).attr("id");
			console.log(colName);
			var colValue = $(this).text();
			switch(colName) {
			    case "carrier":
			    	$content.find("input[name=carrier]").val(colValue);
			        break;
			    case "machineName":
			    	$content.find("#machineName1").val(colValue).prop("selected", true);
			        break;
			    case "unitName":
			    	$content.find("#unit").val(colValue);
			        break;
			    case "commandId":
			    	$content.find("#commandId").val(colValue);
			        break;
			    case "lotId":
			    	$content.find("#lotId").val(colValue);
			        break;
			    default:
			}
			
		});
			
		// Time Range 클릭 이벤트
		$content.find(":radio[name=time]").click(function(){
			var val = $(this).val();
				switch(val) {
			    case "01":
			    	var d = new Date();
					var curTime = getTimeStamp(d,"");
					var beForeTenMin = getTimeStamp(new Date(Date.parse(d) + 1000 * 60 * -10),"");
					setSearchTime(beForeTenMin,curTime);
					$content.find("#fromDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
					$content.find("#toDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
					setSearchTimeReadOnly(false);
			        break;
			    case "02":
			    	var d = new Date();
					var curTime = getTimeStamp(d,"");
					var beForeOneHour = getTimeStamp(new Date(Date.parse(d) + 1000 * 60 * -60),"");
					setSearchTime(beForeOneHour,curTime);
					$content.find("#fromDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
					$content.find("#toDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
					setSearchTimeReadOnly(false);
			        break;
			    case "03":
			    	var d = new Date();
					var curTime = getTimeStamp(d,"");
					setSearchTime(curTime,curTime);
					$content.find("#fromDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date(Date.parse(d) - 1 * 1000 * 60 * 60 * 24)));
					$content.find("#toDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
					setSearchTimeReadOnly(false);
			        break;
			    /* case "04":
			    	setSearchTimeReadOnly(false);
			        break; */
			    default:
			}
		});
		setFilter();
     });
     
     // 초기화
	function init<c:out value="${param.uuid }" />(){
		
		init();
		setDatepicker('<c:out value="${param.uuid }" />');
		// 검색 시간 ( Last 10 Minute )
		drawGrid<c:out value="${param.uuid }" />();
		//필터 리스트 적용
		// 20220621	X0122410	fabSite 추가		
		getFilterList($content.find('input[name="rdoFabSite"]:checked').val());
		
		// 2021. 03. 31. X0122410.	fab별로 machinetype list 가져오기
		setTimeout(function(){	
			var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
			getMachineTypeFromFab(_fabSite,"fab", "machineType", "singleFilterChkBoxFab");		
		}, 800);
	}
	
	var dataView<c:out value="${param.uuid }" />;
	var grid<c:out value="${param.uuid }" />;
	var data<c:out value="${param.uuid }" /> = [];
	// 테이블  생성
	function drawGrid<c:out value="${param.uuid }" />(){
		var columns = [
			  {id: "TIME", name: "TIME", field: "TIME_EX", width: 120, minWidth: 120, cssClass: "cell-title", sortable: true},
			  {id: "CARRIER", name: "CARRIER", field: "CARRIER",  sortable: true},
			  {id: "LOTID", name: "LOTID", field: "LOTID",  sortable: true},
			  {id: "T/R COMMANDID", defaultSortAsc: false, name: "T/R COMMANDID", field: "TRANSPORTCOMMANDID", width: 80, sortable: true},
			  {id: "CURRENTMACHINE", name: "CURRENTMACHINE", field: "CURRENTMACHINENAME", minWidth: 60,  sortable: true},
			  {id: "CURRENTUNIT", name: "CURRENTUNIT", field: "CURRENTUNITNAME", minWidth: 60, sortable: true},
			  {id: "MACHINETYPE", name: "MACHINETYPE", field: "MACHINETYPE", minWidth: 60, sortable: true},
			];
		var options = {
		  forceFitColumns: true,
		  autoExpandColumns : true,
		  topPanelHeight: 30,
		  rowHeight: 21,
		  enableCellNavigation: true
		};
		  
		  dataView<c:out value="${param.uuid }" /> = new Slick.Data.DataView({ inlineFilters: true });
		  grid<c:out value="${param.uuid }" /> = new Slick.Grid("#list<c:out value="${param.uuid }" />", dataView<c:out value="${param.uuid }" />, columns, options);
		  grid<c:out value="${param.uuid }" />.setSelectionModel(new Slick.RowSelectionModel());
		  var columnpicker = new Slick.Controls.ColumnPicker(columns, grid<c:out value="${param.uuid }" />, options);
			  // 그리드 정렬 
			  grid<c:out value="${param.uuid }" />.onSort.subscribe(function(e, args) {
				  var field = args.sortCol.field;
			      var sign = args.sortAsc ? 1: -1;
			      dataView<c:out value="${param.uuid }" />.sort(function (dataRow1, dataRow2) {
			        value1 = dataRow1[field];
			        if(value1 == null) value1 = "";
			        value2 = dataRow2[field];
			        if(value2 == null) value2 = "";
			        var result = (value1 ==value2 ? 0 : (value1 > value2 ? 1: -1)) * sign;
			        return result;
			      });
			      grid<c:out value="${param.uuid }" />.invalidate();
				  grid<c:out value="${param.uuid }" />.render();
			  });
			  // 마우스 오른쪽 버튼 클릭
			  grid<c:out value="${param.uuid }" />.onContextMenu.subscribe(function (e) {
			  	e.preventDefault();
			  	var cell = grid<c:out value="${param.uuid }" />.getCellFromEvent(e);
			  	selRow = cell.row;
			  	$("#contextMenu a:eq(1)").hide();
				$("#contextMenu a:eq(2)").hide(); // 세번째 메뉴 숨김
			  	$("#contextMenu").data("row", cell.row).css("top", e.pageY).css("left", e.pageX) .show();
			  	$("body").one("click", function () {
			  		$("#contextMenu").hide();
			  	});
			});
		    grid<c:out value="${param.uuid }" />.onClick.subscribe(function(e, args) {
			});
		    grid<c:out value="${param.uuid }" />.onDblClick .subscribe(function(e, args) {
	        	var cell = args.cell;
			    var rowIdx = args.row;
			    var row = grid<c:out value="${param.uuid }" />.getDataItem(rowIdx);
			    var field = grid<c:out value="${param.uuid }" />.getColumns()[cell].field;
			    var value = row[field];
			    console.log("onDblClick{"+rowIdx+"},{"+cell+"},{"+value+"}");
	        	setSearchOption<c:out value="${param.uuid }" />(field,value);
			});
		     // wire up model events to drive the grid
			  dataView<c:out value="${param.uuid }" />.onRowCountChanged.subscribe(function (e, args) {
				console.log("onRowCountChanged");
				$content.find("#rowCount").text(args.current);
			    grid<c:out value="${param.uuid }" />.updateRowCount();
			    grid<c:out value="${param.uuid }" />.render();
			  });
			  dataView<c:out value="${param.uuid }" />.onPagingInfoChanged.subscribe(function (e, pagingInfo) {
				  console.log("onPagingInfoChanged :"+JSON.stringify(pagingInfo));
		        grid<c:out value="${param.uuid }" />.render();
			  });
			 if( data<c:out value="${param.uuid }" /> ==null || data<c:out value="${param.uuid }" />.length <= 0){
			 	 grid<c:out value="${param.uuid }" />.invalidateAllRows();
			 	 $content.find('.grid-canvas').html('<div class="alert-info-grid">No Record(s) Found</div>');
			 }
	}
	
	
	// searchOption 세팅
	function setSearchOption<c:out value="${param.uuid }" />(colName , colValue){
		console.log(colName);
		switch(colName) {
		    case "CARRIER":
		    	$content.find("input[name=carrier]").val(colValue);
		        break;
		    case "CURRENTMACHINENAME":
		    	$content.find("#machineName1").val(colValue).prop("selected", true);
		        break;
		    case "CURRENTUNITNAME":
		    	$content.find("#unit").val(colValue);
		        break;
		    case "TRANSPORTCOMMANDID":
		    	$content.find("#commandId").val(colValue);
		        break;
		    case "LOTID":
		    	$content.find("#lotId").val(colValue);
		        break;
		    default:
		}
	}
	
	// 조회
	function getLogList<c:out value="${param.uuid }" />(page){
		if(!chkValidate()) return;
		$content.find("#searchBtn").addClass('disabled');
		showLoadingbar($("#list<c:out value="${param.uuid }" />"));
		$content.find('#page').val(page);
		$content.find("#pageTxt").text(page);
		$content.find(".ui-icon-seek-prev , .ui-icon-seek-next").addClass("ui-state-disabled");
		var from = $content.find("#fromDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#fromHour").val() +$content.find("#fromMin").val()+$content.find("#fromSec").val();
		var to = $content.find("#toDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#toHour").val() +$content.find("#toMin").val()+$content.find("#toSec").val();
		$content.find("#from").val(from);
		$content.find("#to").val(to);
		var isChk = $content.find("#singleFilter").is(":checked");
		if(isChk){  // single filter
			$content.find(":hidden[name=machineName]").val($content.find('#machineName1').val());
		}else{      // multi filter
			$content.find(":hidden[name=machineName]").val($content.find('#machineName2').val());
		}
		$content.find("#fabSite").val($content.find('input[name="rdoFabSite"]:checked').val());
		var param = $content.find("#searchForm").serializeObject();
		console.log("param : ", param);
		//2021.03.24	X0122410 : machineTypes parameter 추가
		var machineTypes = $content.find(":checkbox[name^=machineType]:checked").map(function(){return $(this).val(); }).get().join();
		param['machineTypes'] = machineTypes;
		//console.dir(param);
		var url = "<c:url value='/mat/ajax/getCarrierLocLogList.do' />";
		$.ajax({
	            url: url,
	            type:'post',
	            data: param,
	            traditional: true,
	            success:function(result){
	            	dataView<c:out value="${param.uuid }" />.setItems([]);
		            	if(result != null  && result.rows != null){
		            		if($content.find("#reload").val() == "01"){
		            			data<c:out value="${param.uuid }" /> = result.rows;
		            		}else{
		            			data<c:out value="${param.uuid }" /> = data<c:out value="${param.uuid }" />.concat(result.rows);
		            		}
							dataView<c:out value="${param.uuid }" />.setItems(data<c:out value="${param.uuid }" />);
							if(dataView<c:out value="${param.uuid }" />.length <= 0){
								 grid<c:out value="${param.uuid }" />.invalidateAllRows();
							     $content.find('.grid-canvas').html('<div class="alert-info-grid">No Record(s) Found</div>');
							}
							setPagerState(result.rows);
		            	}
	            		loadingbarFadeOut();
	            		grid<c:out value="${param.uuid }" />.resizeCanvas();
						$content.find("#searchBtn").removeClass('disabled');
	            }
		});
	}
	
	// Filter View 숨기기
	$content.find("#fold_filter_view").click(function(){
		$content.find("#filter_view").css("display", "none");
		$content.find("#unfold_filter_view_wrap").css("display", "");
		grid<c:out value="${param.uuid }" />.resizeCanvas();
	});
	
	// Filter View 보이기
	$content.find("#unfold_filter_view").click(function(){
		$content.find("#unfold_filter_view_wrap").css("display", "none");
		$content.find("#filter_view").css("display", "");
		grid<c:out value="${param.uuid }" />.resizeCanvas();
	});
	
	// 메모리 해제..
	function destroy<c:out value="${param.uuid }" />(){
		delete dataView<c:out value="${param.uuid }" />;
		delete grid<c:out value="${param.uuid }" />;
		delete data<c:out value="${param.uuid }" />;
		delete getLogList<c:out value="${param.uuid }" />;
		delete drawGrid<c:out value="${param.uuid }" />;
		delete init<c:out value="${param.uuid }" />;
		console.log("delete memory done..");
	}
	reset();
</script>