<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ include file="/WEB-INF/views/common-taglib.jspf"%>
<div class="contents_wrap" id="body_<c:out value="${param.uuid }" />">
        <!-- Location Information -->
        <div class="loc_info_basic">
            <span class="location_box">
                <a href="javascript:movePage('<c:url value="/tran/returnLogList.do" />')" class="location"><span class="loc_info_ico loc_info_ico_home"></span>Home</a>
            </span>
            <span class="loc_info_ico loc_info_ico_arr_depth"></span>
            <span class="location_box">
                <a href="javascript:movePage('<c:url value="/tran/returnLogList.do" />')" class="location">Transport</a>
            </span>
            <span class="loc_info_ico loc_info_ico_arr_depth"></span>
            <span class="location_box">
                <a href="javascript:movePage('<c:url value="/tran/returnLogList.do" />')" class="location"><spring:message code="site.returnLogList" text="default text" /></a>
            </span>
        </div>
        <!-- //Location Information -->
        <!-- Page Title -->
        <table class="page_tit">
            <tr>
                <td class="tit_area">
                    <div class="tit"><spring:message code="site.returnLogList" text="default text" /></div>
                </td>
            </tr>
        </table>
        <!-- //Page Title -->
        <!-- Search Type01 -->
        <!-- Sub Title -->
        <div class="lay_item vert">
        <form id="searchForm" name="searchForm" method="post" >
        <input type="hidden" id="fabSite" name="fabSite" value="" />
        <%-- <input type="hidden" id="type" name="type" value="${param.type}" /> --%>
        <input type="hidden" id="page" name="page" value="1" />
        <input type="hidden" name="transportMachineName" value="" />
	    <input type="hidden" name="fromMachineName" value="" />
	    <input type="hidden" name="toMachineName" value="" />
        <!-- <input type="hidden" id="fromMachineType" name="fromMachineType"  value="" />
        <input type="hidden" id="toMachineType" name="toMachineType" value="" /> -->
        <input type="hidden" id="carrier" name="carrier" value="" />
        <input type="hidden" id="lotId" name="lotId" value="" />
        <input type="hidden" id="filterTransport" name="filterTransport" value="01" />
        <input type="hidden" id="filterFrom" name="filterFrom" value="01" />
    	<input type="hidden" id="filterTo" name="filterTo" value="01" />
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
                                                <div id="resetBtn2" class="mini ui primary button" style="width:75px;float: right;margin-right: 10px;float:right">
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
                                                       <table class="condition_table" summary="<spring:message code="site.common.filter" text="default text" />">
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
                                                <table class="condition_table" summary="<spring:message code="site.common.filter" text="default text" />">
					                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
					                            <tbody>
					                                <tr>
					                                    <td class="condition_t_head_top" colspan="2">
					                                    	<i class="minus square icon"></i>
					                                    	<span>Carrier ID or Lot ID</span>
					                                    </td>
					                                </tr>
					                                <tr>
					                                    <td class="condition_t_data" colspan="2">
					                                         <input type="radio" class="jqForm" id="searchOption1" name="searchOption" value="carrier" checked="checked" ><label for="searchOption1">Carrier ID</label>
					                                         <input type="radio" class="jqForm" id="searchOption2" name="searchOption" value="lotId"  ><label for="searchOption2">Lot ID</label>
					                                    </td>
					                                </tr>
					                                <tr>
					                                    <td class="condition_t_data" colspan="2">
					                                        <input type="text" id="carrierLotId" name="carrierLotId" style="width:200px" value="<c:out value="${param.carrierLotId }" />"   />
					                                    </td>
					                                </tr>
					                            </tbody>
					                        </table>
					                        </div>
           									</div>
                                            <div class="srch_type01">
        									<div class="condition_area">
                                                <table class="condition_table" summary="<spring:message code="site.common.filter" text="default text" />">
					                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
					                            <tbody>
					                                <tr>
					                                    <td class="condition_t_head_top" colspan="2">
					                                    	<i class="minus square icon"></i>
					                                    	<span>TransportJob ID</span>
					                                    </td>
					                                </tr>
					                                <tr>
					                                    <td class="condition_t_data" colspan="2">
					                                        <input type="text" id="transportJobId" name="transportJobId" value="<c:out value="${param.transportJobId }" />" style="width:200px" />
					                                    </td>
					                                </tr>
					                            </tbody>
					                        </table>
					                        </div>
           									</div>
           									
           									<!-- Transport machine -->
	                                        <%-- <div class="srch_type01">
		     									<div class="condition_area">
		                                             <table class="condition_table" summary="<spring:message code="site.common.filter" text="default text" />">
							                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
							                            <tbody id="test">
							                                <tr>
							                                    <td class="condition_t_head_top" colspan="3">
							                                    	<i class="minus square icon"></i>
							                                    	<span>Transport Machine</span>
							                                    </td>
							                                </tr>
							                                <tr>
							                                    <td class="condition_t_data" colspan="3">
							                                    	<input type="checkbox" class="jqForm" id="singleFilterTransport" name="singleFilterTransport" value="01" <c:if test="${param.singleFilterTransport == '01' }" >checked="checked"</c:if> ><label for="singleFilterTransport">Single Filter</label>
							                                    </td>
							                                </tr>
							                                <tr class="singleFilterTransport" >
							                                    <th scope="col" class="condition_t_head">AREA</th>
							                                    <td class="condition_t_data" colspan="2">
							                                        <select class="areaName_machine" id="transportAreaName" name="transportAreaName" style="width: 143px" >
							                                            <option value="ALL" <c:if test="${param.transportAreaName == 'ALL' }" >selected="selected"</c:if>>ALL</option>
							                                        </select>
							                                    </td>
							                                </tr>
							                                <tr class="singleFilterTransport" >
							                                    <th scope="col" class="condition_t_head">BAY</th>
							                                    <td class="condition_t_data" colspan="2" >
							                                         <select class="bayName" id="transportBayName" name="transportBayName" style="width: 143px" >
							                                            <option value="ALL" <c:if test="${param.transportBayName == 'ALL' }" >selected="selected"</c:if>>ALL</option>
							                                        </select>
							                                    </td>
							                                </tr>
							                                <tr  id="singleFilterChkBoxTransportMachineType" class="singleFilterTransport" >
							                                    <th scope="col" class="condition_t_head">Type</th>
							                                </tr>
							                                <tr class="singleFilterTransport" >
							                                	<th scope="col" class="condition_t_head">NAME</th>
							                                    <td class="condition_t_data" colspan="2">
							                                         <select class="machineName1" id="transportMachineName1" name="transportMachineName1" style="width: 143px" >
							                                            <option value="">NOTDESIGNATED</option>
							                                        </select>
							                                    </td>
							                                </tr>
							                                <tr>
							                                    <td class="condition_t_data" colspan="3">
							                                    	<input type="checkbox" class="jqForm" id="multiFilterTransport" name="multiFilterTransport" value="02" <c:if test="${param.multiFilterTransport == '02' }" >checked="checked"</c:if>><label for="multiFilter">Multi Filter</label>
							                                    </td>
							                                </tr>
							                                <tr class="multiFilterTransport">
							                                 	<td class="condition_t_data" colspan="3">
							                                    	 <input type="text" id="transportMachineName2" name="transportMachineName2"  style="width:163px" value="<c:out value="${param.machineName2 }" />" />
					                                                 <div id="fromMachineBtn" class="mini ui primary button" style="width:93px;float: right;margin-left: 4px">
																	 	<i class="tasks icon"></i>Machine
																	 </div>
							                                    </td>				                                    
							                                </tr>
							                            </tbody>
							                        </table>
						                        </div>
	        								</div> --%>
	        								<!-- //Transport machine -->
	        								
           									 <!-- From machine -->
                                            <div class="srch_type01">
	        									<div class="condition_area">
	                                                <table class="condition_table" summary="<spring:message code="site.common.filter" text="default text" />">
							                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
							                            <tbody id="test">
							                                <tr>
							                                    <td class="condition_t_head_top" colspan="3">
							                                    	<i class="minus square icon"></i>
							                                    	<span>Source Machine</span>
							                                    </td>
							                                </tr>
							                                <tr>
							                                    <td class="condition_t_data" colspan="3">
							                                    	<input type="checkbox" class="jqForm" id="singleFilterFrom" name="singleFilterFrom" value="01" checked="checked" ><label for="singleFilterFrom">Single Filter</label>
							                                    </td>
							                                </tr>
							                                <tr class="singleFilterFrom" >
							                                    <th scope="col" class="condition_t_head">AREA</th>
							                                    <td class="condition_t_data" colspan="2">
							                                        <select class="areaName_machine" id="fromAreaName" name="fromAreaName" style="width: 143px" >
							                                            <option value="ALL" <c:if test="${param.fromAreaName == 'ALL' }" >selected="selected"</c:if>>ALL</option>
							                                        </select>
							                                    </td>
							                                </tr>
							                                <tr>
							                                    <th scope="col" class="condition_t_head">BAY</th>
							                                    <td class="condition_t_data" colspan="2" >
							                                         <select class="bayName" id="fromBayName" name="fromBayName" style="width: 143px" >
							                                            <option value="ALL" <c:if test="${param.fromBayName == 'ALL' }" >selected="selected"</c:if>>ALL</option>
							                                        </select>
							                                    </td>
							                                </tr>
							                                <tr  id="singleFilterChkBoxFromMachineType" class="singleFilterFrom"  >
							                                    <th scope="col" class="condition_t_head">Type</th>
							                                </tr>
							                                <tr class="singleFilterFrom"  >
							                                	<th scope="col" class="condition_t_head">NAME</th>
							                                    <td class="condition_t_data" colspan="2">
							                                         <select class="machineName1" id="fromMachineName1" name="fromMachineName1" style="width: 143px" >
							                                            <option value="">NOTDESIGNATED</option>
							                                        </select>
							                                    </td>
							                                </tr>
							                                <tr>
							                                    <td class="condition_t_data" colspan="3">
							                                    	<input type="checkbox" class="jqForm" id="multiFilterFrom" name="multiFilterFrom" value="02" <c:if test="${param.filterFrom == '02' }" >checked="checked"</c:if>><label for="multiFilter">Multi Filter</label>
							                                    </td>
							                                </tr>
							                                <tr class="multiFilterFrom" >
							                                 	<td class="condition_t_data" colspan="3">
							                                    	 <input type="text" id="fromMachineName2" name="fromMachineName2"  style="width:163px" value="<c:out value="${param.machineName2 }" />" />
					                                                 <div id="fromMachineBtn" class="mini ui primary button" style="width:93px;float: right;margin-left: 4px">
																		<i class="tasks icon"></i>Machine
																	 </div>
							                                    </td>
							                                    
							                                </tr>
							                            </tbody>
							                        </table>
						                        </div>
	           								</div>
	           								<!-- //From machine -->
            								            								
            								<!-- To machine -->
                                            <div class="srch_type01">
	        									<div class="condition_area">
	                                                <table class="condition_table" summary="<spring:message code="site.common.filter" text="default text" />">
							                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
							                            <tbody id="test">
							                                <tr>
							                                    <td class="condition_t_head_top" colspan="3">
							                                    	<i class="minus square icon"></i>
							                                    	<span>Dest Machine</span>
							                                    </td>
							                                </tr>
							                                <tr>
							                                    <td class="condition_t_data" colspan="3">
							                                    	<input type="checkbox" class="jqForm" id="singleFilterTo" name="singleFilterTo" value="01" checked="checked" ><label for="singleFilterTo">Single Filter</label>
							                                    </td>
							                                </tr>
							                                <tr class="singleFilterTo" >
							                                    <th scope="col" class="condition_t_head">AREA</th>
							                                    <td class="condition_t_data" colspan="2">
							                                        <select class="areaName_machine" id="toAreaName" name="toAreaName" style="width: 143px" >
							                                            <option value="ALL" <c:if test="${param.toAreaName == 'ALL' }" >selected="selected"</c:if>>ALL</option>
							                                        </select>
							                                    </td>
							                                </tr>
							                                <tr class="singleFilterTo">
							                                    <th scope="col" class="condition_t_head">BAY</th>
							                                    <td class="condition_t_data" colspan="2" >
							                                         <select class="bayName" id="toBayName" name="toBayName" style="width: 143px" >
							                                            <option value="ALL" <c:if test="${param.toBayName == 'ALL' }" >selected="selected"</c:if>>ALL</option>
							                                        </select>
							                                    </td>
							                                </tr>
							                                <tr  id="singleFilterChkBoxToMachineType" class="singleFilterTo" >
							                                    <th scope="col" class="condition_t_head">Type</th>
							                                </tr>
							                                <tr class="singleFilterTo" >
							                                	<th scope="col" class="condition_t_head">NAME</th>
							                                    <td class="condition_t_data" colspan="2">
							                                         <select class="machineName1" id="toMachineName1" name="toMachineName1" style="width: 143px" >
							                                            <option value="">NOTDESIGNATED</option>
							                                        </select>
							                                    </td>
							                                </tr>
							                                <tr>
							                                    <td class="condition_t_data" colspan="3">
							                                    	<input type="checkbox" class="jqForm" id="multiFilterTo" name="multiFilterTo" value="02" <c:if test="${param.filter2 == '02' }" >checked="checked"</c:if>><label for="multiFilter">Multi Filter</label>
							                                    </td>
							                                </tr>
							                                <tr class="multiFilterTo" >
							                                 	<td class="condition_t_data" colspan="3">
							                                    	 <input type="text" id="toMachineName2" name="toMachineName2"  style="width:163px" value="<c:out value="${param.toMachineName2 }" />" />
					                                                 <div id="toMachineBtn" class="mini ui primary button" style="width:93px;float: right;margin-left: 4px">
																		<i class="tasks icon"></i>Machine
																	</div>
							                                    </td>
							                                    
							                                </tr>
							                            </tbody>
							                        </table>
						                        </div>
	           								</div>
	           								<!-- //To machine -->
	           								
           								<div class="srch_type01">
        									<div class="condition_area">
                                                <table class="condition_table" summary="<spring:message code="site.common.filter" text="default text" />">
					                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
					                            <tbody>
					                                <tr>
					                                    <td class="condition_t_head_top" colspan="2">
					                                    	<i class="minus square icon"></i>
					                                    	<span>State</span>
					                                    </td>
					                                </tr>
					                                <tr>
					                                	 <td class="condition_t_data" colspan="2">
					                                    	<input type="checkbox" class="jqForm" id="state" name="state" value="ALL"  checked="checked" ><label for="state">ALL</label>
					                                    </td>
					                                </tr>
					                            </tbody>
					                        </table>
					                        </div>
           								</div>
           								<div class="srch_type01">
        									<div class="condition_area">
                                                <table class="condition_table" summary="<spring:message code="site.common.filter" text="default text" />">
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
                                       <div style="padding: 10px 2px;">
                                           	<div  class="ui primary button" id="searchBtn" >
			                                   	<i class="search icon"></i>Search
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
                                        <i  class="minus square icon large fixed" style="color:#ccd2de"></i>
                                        <span class="txt">Transport Job History
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
                            	<div id="list<c:out value="${param.uuid }" />" class="gridForResize_triple" style="width:100%;height:548px; background: white; outline: 0; border: 1px solid gray;"></div>
                           		<c:import url="/WEB-INF/views/common/slickGridPager.jsp" charEncoding="utf-8" />
                    <div class="" style="height:100%;">
                        <div class="opt_tit">
                            <div class="opt_tit_left" id="" style="margin-top: 3px;">
                                <div class="elmt" style="width: 2000px">
                                    <i id="foldTableBtn1" class="minus square icon large" style="color:#ccd2de"></i>
                                    <span class="txt elmtTit">Transport Job History Detail</span>
                                </div>
                            </div>
                        </div>
                             <div id="list2<c:out value="${param.uuid }" />" style="width:100%;height:150px; background: white; outline: 0; border: 1px solid gray;margin-top: 16px"></div>
                     </div>
                     <div class="" style="height:100%;">
                        <div class="opt_tit">
                            <div class="opt_tit_left" id="" >
                                <div class="elmt">
                                    <i id="foldTableBtn2" class="minus square icon large" style="color:#ccd2de"></i>
                                    <span class="txt elmtTit">Transport Command Histories</span>
                                </div>
                            </div>
                        </div>
                        <div id="list3<c:out value="${param.uuid }" />" style="width:100%;height:150px;margin-bottom: 10px; background: white; outline: 0; border: 1px solid gray;"></div>
            		</div>
            	</div>
        	</div>
        </div>
        </form>
    </div>
</div>
<script type="text/javascript">	
	var loadingIndicator2 = null;
	var loadingIndicator3 = null;
	
	$content = $("#body_${param.uuid }");
 	$content.find(document).ready(function(){
			
			$content.find('#logInfo').hide();
			init<c:out value="${param.uuid }" />();
			// reset 버튼 클릭 이벤트
			$("body").on("click","#resetBtn2",function(){
			 reset<c:out value="${param.uuid }" />();
			});
			// 상세조회 테이블 fold / open
			$content.find("#foldTableBtn1").click(function(){
				var lth1 = $content.find("#list<c:out value="${param.uuid }" />").height();
				var dth2 = $content.find("#list2<c:out value="${param.uuid }" />").height();
				var $span = $(this);
				var isOpen = $span.hasClass("minus");
				var isShowList3 = $("#list3<c:out value="${param.uuid }" />").is(":visible");
				if(isOpen){
					$span.removeClass("add");
					$span.addClass("minus");
					$("#list2<c:out value="${param.uuid }" />").hide();
					$content.find("#list<c:out value="${param.uuid }" />").height(lth1 + 150);
				}else{
					$span.removeClass("minus");
					$span.addClass("add");
					$content.find("#list<c:out value="${param.uuid }" />").height(lth1 - 150);
					$("#list2<c:out value="${param.uuid }" />").show();
				}
				grid<c:out value="${param.uuid }" />.resizeCanvas();
			});
			
			$content.find("#foldTableBtn2").click(function(){
				var lth1 = $content.find("#list<c:out value="${param.uuid }" />").height();
				var dth2 = $content.find("#list3<c:out value="${param.uuid }" />").height();
				var $span = $(this);
				var isOpen = $span.hasClass("minus");
				var isShowList2 = $("#list2<c:out value="${param.uuid }" />").is(":visible");
				if(isOpen){
					$span.removeClass("add");
					$span.addClass("minus");
					$("#list3<c:out value="${param.uuid }" />").hide();
					$content.find("#list<c:out value="${param.uuid }" />").height(lth1 + 150);
				}else{
					$span.removeClass("minus");
					$span.addClass("add");
					$("#list3<c:out value="${param.uuid }" />").show();
					$content.find("#list<c:out value="${param.uuid }" />").height(lth1 - 150);
				}
				grid<c:out value="${param.uuid }" />.resizeCanvas();
			});
			
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
			
			// 20220621 FAB SITE 클릭 이벤트
			$content.find('input[name="rdoFabSite"]').change(function() {				
				//var _fabSite = $(this).val();
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				
				getFabFromFabSite("tran", _fabSite, "fab", "tdFab");
				getMachineTypeFromFab(_fabSite,"fab", "machineType", "singleFilterChkBoxFab");				
				getAreaFromFab(_fabSite,"fab", "areaName");
				getBayFromArea(_fabSite,"fab", "areaName", "bayName");
				getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");
			});
			
			// 
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
				
				getMachineTypeFromFab2(_fabSite,"fab", "transportMachineType|fromMachineType|toMachineType", "singleFilterChkBoxTransportMachineType|singleFilterChkBoxFromMachineType|singleFilterChkBoxToMachineType");				
				getAreaFromFab2(_fabSite,"fab","transportAreaName|fromAreaName|toAreaName");
				getBayFromArea2(_fabSite,"fab","transportBayName|fromBayName|toBayName");								
				getMachineNameList2(_fabSite,"fab","fromMachineName1|toMachineName1");
				getMachineNameList2MachineTypeNotNull(_fabSite,"fab","transportMachineName1");
			});
			
			// Transport Machine > \ AREA 셀렉트 값 변경 이벤트
			$content.find("#transportAreaName").change(function(){
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				getBayFromArea(_fabSite,"fab", "transportAreaName", "transportBayName");	// 200826 hgJeon Area 변경 시 bayList 변경 추가
				getMachineNameListMachineTypeNotNull(_fabSite,"fab", "transportAreaName","transportBayName","transportMachineType","transportMachineName1");
			});
			
			// Transport Machine > \ BAY 셀렉트 값 변경 이벤트
			$content.find("#transportBayName").change(function(){			
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				getMachineNameListMachineTypeNotNull(_fabSite,"fab", "transportAreaName","transportBayName","transportMachineType","transportMachineName1");
			});
			
			// Transport Machine > \ Type 체크박스 클릭 이벤트
			/* $content.find(":checkbox[name^=transportMachineType]").click(function(){
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				var val = $(this).val();
				if(val == "ALL"){
					$content.find(":checkbox[name^=transportMachineType]:gt(0)").prop("checked",false);
				}else{
					$content.find(":checkbox[name^=transportMachineType]:eq(0)").prop("checked",false);
				}
				getMachineNameListMachineTypeNotNull(_fabSite,"fab", "transportAreaName","transportBayName","transportMachineType","transportMachineName1");
			}); */
			$content.on("click",":checkbox[name^=transportMachineType]", function(){	
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				var val = $(this).val();
				if(val == "ALL"){ // ALL 체크시, 다른 체크 박스 해제
					$content.find(":checkbox[name^=transportMachineType]:gt(0)").prop("checked",false);
				}else{ // 다른 체크박스 체크시 , ALL 체크박스 해제				
					var tmpChk = 0;
					$content.find(":checkbox[name^=transportMachineType]:checked").each(function(){
						tmpChk += 1;
					});
					if( tmpChk > 0){
						$content.find(":checkbox[name^=transportMachineType]:eq(0)").prop("checked",false);
					}else{
						$content.find(":checkbox[name^=transportMachineType]:eq(0)").prop("checked",true);
					}
				}
				getMachineNameListMachineTypeNotNull(_fabSite,"fab", "transportAreaName","transportBayName","transportMachineType","transportMachineName1");
			});	
					
			// Source Machine > \ AREA 셀렉트 값 변경 이벤트
			$content.find("#fromAreaName").change(function(){			
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				getBayFromArea(_fabSite,"fab", "fromAreaName", "fromBayName");
				getMachineNameList(_fabSite,"fab", "fromAreaName","fromBayName","fromMachineType","fromMachineName1");
			});
			
			// Source Machine > \ BAY 셀렉트 값 변경 이벤트
			$content.find("#fromBayName").change(function(){
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				getMachineNameList(_fabSite,"fab", "fromAreaName","fromBayName","fromMachineType","fromMachineName1");
			});
			
			// Source Machine > \ Type 체크박스 클릭 이벤트
			/* $content.find(":checkbox[name^=fromMachineType]").click(function(){
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				var val = $(this).val();
				if(val == "ALL"){
					$content.find(":checkbox[name^=fromMachineType]:gt(0)").prop("checked",false);
				}else{
					$content.find(":checkbox[name^=fromMachineType]:eq(0)").prop("checked",false);
				}
								
				getMachineNameList(_fabSite,"fab","fromAreaName","fromBayName","fromMachineType","fromMachineName1");				
			}); */
			$content.on("click",":checkbox[name^=fromMachineType]", function(){		
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				var val = $(this).val();
				if(val == "ALL"){ // ALL 체크시, 다른 체크 박스 해제
					$content.find(":checkbox[name^=fromMachineType]:gt(0)").prop("checked",false);
				}else{ // 다른 체크박스 체크시 , ALL 체크박스 해제				
					var tmpChk = 0;
					$content.find(":checkbox[name^=fromMachineType]:checked").each(function(){
						tmpChk += 1;
					});
					if( tmpChk > 0){
						$content.find(":checkbox[name^=fromMachineType]:eq(0)").prop("checked",false);
					}else{
						$content.find(":checkbox[name^=fromMachineType]:eq(0)").prop("checked",true);
					}
				}
				getMachineNameList(_fabSite,"fab","fromAreaName","fromBayName","fromMachineType","fromMachineName1");
			});			
			
			// Destination Machine > \ AREA 셀렉트 값 변경 이벤트
			$content.find("#toAreaName").change(function(){
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				getBayFromArea(_fabSite,"fab", "toAreaName", "toBayName");
				getMachineNameList(_fabSite,"fab", "toAreaName","toBayName","toMachineType","toMachineName1");
			});
			
			// Destination Machine > \ BAY 셀렉트 값 변경 이벤트
			$content.find("#toBayName").change(function(){
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				getMachineNameList(_fabSite,"fab", "toAreaName","toBayName","toMachineType","toMachineName1");
			});
			
			// Destination Machine > \ Type 체크박스 클릭 이벤트
			/* $content.find(":checkbox[name^=toMachineType]").click(function(){
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				var val = $(this).val();
				if(val == "ALL"){
					$content.find(":checkbox[name^=toMachineType]:gt(0)").prop("checked",false);
				}else{
					$content.find(":checkbox[name^=toMachineType]:eq(0)").prop("checked",false);
				}
				
				getMachineNameList(_fabSite,"fab","toAreaName","toBayName","toMachineType","toMachineName1");
			}); */
			$content.on("click",":checkbox[name^=toMachineType]", function(){			
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				var val = $(this).val();
				if(val == "ALL"){ // ALL 체크시, 다른 체크 박스 해제
					$content.find(":checkbox[name^=toMachineType]:gt(0)").prop("checked",false);
				}else{ // 다른 체크박스 체크시 , ALL 체크박스 해제				
					var tmpChk = 0;
					$content.find(":checkbox[name^=toMachineType]:checked").each(function(){
						tmpChk += 1;
					});
					if( tmpChk > 0){
						$content.find(":checkbox[name^=toMachineType]:eq(0)").prop("checked",false);
					}else{
						$content.find(":checkbox[name^=toMachineType]:eq(0)").prop("checked",true);
					}
				}
				getMachineNameList(_fabSite,"fab","toAreaName","toBayName","toMachineType","toMachineName1");
			});	
			
			// state 클릭 이벤트
			$content.find(":checkbox[name^=state]").click(function(){
				var val = $(this).val();
				if(val == "ALL"){
					$content.find(":checkbox[name^=state]:gt(0)").prop("checked",false);
				}else{
					$content.find(":checkbox[name^=state]:eq(0)").prop("checked",false);
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
				grid<c:out value="${param.uuid }" />.resizeCanvas();
			});
			
			// machine 버튼 클릭 
			$content.find("#transportMachineBtn").click(function(){
				if($(this).hasClass("disabled")){
					return false;					
				}
				var url = "<c:url value='/tot/pop/machineNamePop.do' />";
				openPopup(url , 600 , 610,function(data){
					console.log(JSON.stringify(data));
					$content.find("#transportMachineName2").val(data);
				});
			});
			
			// machine 버튼 클릭 
			$content.find("#fromMachineBtn").click(function(){
				if($(this).hasClass("disabled")){
					return false;					
				}
				var url = "<c:url value='/tot/pop/machineNamePop.do' />";
				openPopup(url , 600 , 610,function(data){
					console.log(JSON.stringify(data));
					$content.find("#fromMachineName2").val(data);
				});
			});
			
			// machine 버튼 클릭 
			$content.find("#toMachineBtn").click(function(){
				if($(this).hasClass("disabled")){
					return false;					
				}
				var url = "<c:url value='/tot/pop/machineNamePop.do' />";
				openPopup(url , 600 , 610,function(data){
					console.log(JSON.stringify(data));
					$content.find("#toMachineName2").val(data);
				});
			});
			
			// single filter 클릭 이벤트)
			$content.find("#singleFilterTransport").click(function(){
				var isChk = $(this).is(":checked");
				if(isChk){
					$content.find("#filterTransport").val("01");
				}else{
					$content.find("#filterTransport").val("02");
				}
				setFilterTransport<c:out value="${param.uuid }" />();
			});
 	
			// multi filter 클릭 이벤트)
			$content.find("#multiFilterTransport").click(function(){
				var isChk = $(this).is(":checked");
				if(isChk){
					$content.find("#filterTransport").val("02");
				}else{
					$content.find("#filterTransport").val("01");
				}
				setFilterTransport<c:out value="${param.uuid }" />();
			});
			
			// single filter 클릭 이벤트)
			$content.find("#singleFilterFrom").click(function(){
				var isChk = $(this).is(":checked");
				if(isChk){
					$content.find("#filterFrom").val("01");
				}else{
					$content.find("#filterFrom").val("02");
				}
				setFilterFrom<c:out value="${param.uuid }" />();
			});
 	
			// multi filter 클릭 이벤트)
			$content.find("#multiFilterFrom").click(function(){
				var isChk = $(this).is(":checked");
				if(isChk){
					$content.find("#filterFrom").val("02");
				}else{
					$content.find("#filterFrom").val("01");
				}
				setFilterFrom<c:out value="${param.uuid }" />();
			});
			
			// single filter 클릭 이벤트)
			$content.find("#singleFilterTo").click(function(){
				var isChk = $(this).is(":checked");
				if(isChk){
					$content.find("#filterTo").val("01");
				}else{
					$content.find("#filterTo").val("02");
				}
				setFilterTo<c:out value="${param.uuid }" />();
			}); 	
			// multi filter 클릭 이벤트)
			$content.find("#multiFilterTo").click(function(){
				var isChk = $(this).is(":checked");
				if(isChk){
					$content.find("#filterTo").val("02");
				}else{
					$content.find("#filterTo").val("01");
				}
				setFilterTo<c:out value="${param.uuid }" />();
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
     });
     
    var dataView<c:out value="${param.uuid }" />;
    var grid<c:out value="${param.uuid }" />;
    var data<c:out value="${param.uuid }" /> = [];
    // 테이블  생성
   	function drawGrid<c:out value="${param.uuid }" />(){
	    var columns = [
	    	  {id: "START TIME", name: "START TIME", field: "TRANS_JOBSTART", minWidth: 170, cssClass: "cell-title", sortable: true},
	    	  {id: "END TIME", name: "END TIME", field: "TRANS_JOBEND", minWidth: 170, sortable: true},
	    	  {id: "TRANSPORTJOBID", name: "TRANSPORTJOBID", field: "TRANSPORTJOBID", minWidth: 200, sortable: true},
	    	  {id: "STATE", name: "STATE", field: "STATE", minWidth: 105, sortable: true},
	    	  {id: "CARRIER", name: "CARRIER", field: "CARRIER", minWidth: 80, sortable: true},
	    	  {id: "SOURCE MACHINE", name: "SOURCE MACHINE", field: "SOURCEMACHINENAME", minWidth: 100, sortable: true},
	    	  {id: "SOURCE MACHINETYPE", name: "SOURCE MACHINETYPE", field: "SOURCEMACHINETYPE2", minWidth: 100, sortable: true},	    	  
	    	  {id: "SOURCE UNIT", name: "SOURCE UNIT", field: "SOURCEUNITNAME", minWidth: 100, sortable: true},
	    	  {id: "DEST TYPE", name: "DEST TYPE", field: "DESTTYPE", minWidth: 60, sortable: true},
	    	  {id: "DEST MACHINE", name: "DEST MACHINE", field: "DESTMACHINENAME", minWidth: 100, sortable: true},
	    	  {id: "DEST MACHINETYPE", name: "DEST MACHINETYPE", field: "DESTMACHINETYPE2", minWidth: 100, sortable: true},
	    	  {id: "DEST UNIT", name: "DEST UNIT", field: "DESTUNITNAME", minWidth: 100, sortable: true},
	    	  {id: "REASON", name: "REASON", field: "REASON", minWidth: 40, sortable: true},
	    	  {id: "FIXEDROUTE", name: "FIXEDROUTE", field: "FIXEDROUTE", minWidth: 40, sortable: true},
	    	  {id: "PRIORITY", name: "PRIORITY", field: "PRIORITY", minWidth: 40, sortable: true},
	    	  {id: "LOTID", name: "LOTID", field: "LOTID", minWidth: 60, sortable: true},
	    	  {id: "BATCHID", name: "BATCHID", field: "BATCHID", minWidth: 60, sortable: true},
	    	  {id: "STEPID", name: "STEPID", field: "STEPID", minWidth: 60, sortable: true},
	    	  {id: "PROCESSID", name: "PROCESSID", field: "PROCESSID", minWidth: 60, sortable: true},
	    	  {id: "DESCRIPTION", name: "DESCRIPTION", field: "DESCRIPTION", minWidth: 60, sortable: true},
	    	  {id: "CREATE USER", name: "CREATE USER", field: "CREATEUSER", minWidth: 60, sortable: true},
	    	  {id: "BATCH TYPE", name: "BATCH TYPE", field: "BATCHTYPE", minWidth: 60, sortable: true}
	    	];
	    var options = {
	    	  enableCellNavigation: true,
	    	  forceFitColumns: false,
		      autoExpandColumns : true,
	  		  topPanelHeight: 30,
	  		  rowHeight: 21,
	  		  enableColumnReorder: true
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
			  	$("#contextMenu").data("row", cell.row).css("top", e.pageY).css("left", e.pageX) .show();
			  	$("body").one("click", function () {
			  		$("#contextMenu").hide();
			  	});
			});
			var copyGridColumnValue = '';
			//20180420 컬럼 data 클립보드에 복사  
		    grid<c:out value="${param.uuid }" />.onClick.subscribe(function(e, args) {
		    	var copyCell = args.cell;
			    var copyRowIdx = args.row;
			    var copyRow = grid<c:out value="${param.uuid }" />.getDataItem(copyRowIdx);
			    var copyField = grid<c:out value="${param.uuid }" />.getColumns()[copyCell].field;
			    var copyValue = copyRow[copyField];
			    if(copyField == "COMMAND" && (copyValue==null || copyValue=="")){ // COMM.MSG NAME , MESSAGE NAME 값 병합
		    		copyValue = copyRow["MESSAGENAME"];
			    }
			    copyGridColumnValue = copyValue;
			    console.log("onlClick{"+copyRowIdx+"},{"+copyCell+"},{"+copyValue+"}");
			  	//$("#copyGridColumn").click(function (e) {
			    //	copyToClipboard();
			    //	event.stopPropagation(); //상위DOM 으로 이벤트 전파 중지
			    //	/* event.cancelBubble = true;
			    //   if (event.stopPropagation) {
			    //        event.stopPropagation();
			    //    } IE 10 이하 version */
                //
			    //	copyToClipboard(copyValue);  // 클립보드 복사
			    //	$("#contextMenu").hide();
			    //});
			    $("#copyGridColumn").off('click');   //unbind
			    $("#copyGridColumn").on('click',function() {
			    	event.stopImmediatePropagation();
			    	copyToClipboard();
			    	event.stopPropagation(); //상위DOM 으로 이벤트 전파 중지		    	
			    	console.log("copyGridColumn click {"+copyGridColumnValue+"}");
			    	copyToClipboard(copyGridColumnValue);  // 클립보드 복사
			    	$("#contextMenu").hide();
			    });
			});	        
	    	grid<c:out value="${param.uuid }" />.onActiveCellChanged.subscribe(function (e, args) {
	    		var cell = args.cell;
	    	    var rowIdx = args.row;
	    	    if(rowIdx === undefined) return;
	    	    var row = grid<c:out value="${param.uuid }" />.getDataItem(rowIdx);
	    	    var field = grid<c:out value="${param.uuid }" />.getColumns()[cell].field;
	    	    var transportJobId = row["TRANSPORTJOBID"];
	        	var from = $content.find("#fromDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#fromHour").val() +$content.find("#fromMin").val()+$content.find("#fromSec").val();
	    		var to = $content.find("#toDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#toHour").val() +$content.find("#toMin").val()+$content.find("#toSec").val();
	    		var url2 = "<c:url value='/tran/ajax/getTranJobHistoryDetail.do' />";	 
	    		var fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
	    		//var url3 = "<c:url value='/tran/ajax/getTranCmdHistoryDetail.do' />";	 
	    		var param = { "fabSite": fabSite, "from": from, "to": to, "transportJobId": transportJobId };
	    		if($("#list2<c:out value="${param.uuid }" />").is(":visible"))
	    			loadingIndicator2 = showLoadingbar($("#list2<c:out value="${param.uuid }" />"));
	    		if($("#list3<c:out value="${param.uuid }" />").is(":visible")){
	    			loadingIndicator3 = showLoadingbar($("#list3<c:out value="${param.uuid }" />"));
	    		}else{
	    			startTime = new Date().getTime();
	    		}
	    		
	    		$.ajax({ 
    	            url: url2,
    	            type:'post',
    	            data: param,
    	            success:function(result2){
    	            	dataView2<c:out value="${param.uuid }" />.setItems([]);
    	            	dataView3<c:out value="${param.uuid }" />.setItems([]);
    	            	if(result2 != null  && result2.rows != null){
    						data2<c:out value="${param.uuid }" /> = result2.historyListRow;
    						//console.log(result2.historyListRow);
    	            		data3<c:out value="${param.uuid }" /> = result2.commandListRow;
    						dataView2<c:out value="${param.uuid }" />.setItems(data2<c:out value="${param.uuid }" />);
    						dataView3<c:out value="${param.uuid }" />.setItems(data3<c:out value="${param.uuid }" />);
    						if(result2.historyListRow.length <= 0){
   								grid2<c:out value="${param.uuid }" />.invalidateAllRows();
   							}			
    						if(result2.commandListRow.length <= 0){
   								grid3<c:out value="${param.uuid }" />.invalidateAllRows();
   							}
    	            	}
    	            }
    		    });
	    	
	    	});
	        
	        grid<c:out value="${param.uuid }" />.onDblClick .subscribe(function(e, args) {
	        	var cell = args.cell;
	    	    var rowIdx = args.row;
	    	    var row = grid<c:out value="${param.uuid }" />.getDataItem(rowIdx);
	    	    var field = grid<c:out value="${param.uuid }" />.getColumns()[cell].field;
	    	    var value = row[field];
	    	    console.log("onDblClick{"+rowIdx+"},{"+cell+"},{"+value+"}");
	    	    var from = $content.find("#fromDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#fromHour").val() +$content.find("#fromMin").val()+$content.find("#fromSec").val();
	    		var to = $content.find("#toDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#toHour").val() +$content.find("#toMin").val()+$content.find("#toSec").val();
	    	    var carrier = row["CARRIER"];
	    	    var param = "carrier="+carrier+"&text="+carrier+"&from="+from+"&to="+to;
	    	    movePage('<c:url value="/tot/totalLogList.do?'+param+'" />');
	        	//setSearchOption<c:out value="${param.uuid }" />(field,value);
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
   	
    var dataView2<c:out value="${param.uuid }" />;
    var grid2<c:out value="${param.uuid }" />;
    var data2<c:out value="${param.uuid }" /> = [];
    // 테이블  생성
    function drawGrid2<c:out value="${param.uuid }" />(){
        var columns = [
        	  {id: "TIME", name: "TIME", field: "TIME_EX", minWidth: 170, cssClass: "cell-title", sortable: true},
        	  {id: "TRASPORTJOBID", name: "TRANSPORTJOBID", field: "TRANSPORTJOBID", minWidth: 200, sortable: true},
        	  {id: "STATE", name: "STATE", field: "STATE", minWidth: 105, sortable: true},
        	  {id: "CARRIER", name: "CARRIER", field: "CARRIER", minWidth: 80, sortable: true},
        	  {id: "SOURCE MACHINE", name: "SOURCE MACHINE", field: "SOURCEMACHINENAME", minWidth: 100, sortable: true},
        	  {id: "SOURCE MACHINETYPE", name: "SOURCE MACHINETYPE", field: "SOURCEMACHINETYPE2", minWidth: 100, sortable: true},        	  
        	  {id: "SOURCE UNIT", name: "SOURCE UNIT", field: "SOURCEUNITNAME", minWidth: 100, sortable: true},
        	  {id: "DEST TYPE", name: "DEST TYPE", field: "DESTTYPE", minWidth: 60, sortable: true},
        	  {id: "DEST MACHINE", name: "DEST MACHINE", field: "DESTMACHINENAME", minWidth: 100, sortable: true},
        	  {id: "DEST MACHINETYPE", name: "DEST MACHINETYPE", field: "DESTMACHINETYPE2", minWidth: 100, sortable: true},
        	  {id: "DEST UNIT", name: "DEST UNIT", field: "DESTUNITNAME", minWidth: 100, sortable: true},
        	  {id: "REASON", name: "REASON", field: "REASON", minWidth: 40, sortable: true},
        	  {id: "FIXEDROUTE", name: "FIXEDROUTE", field: "FIXEDROUTE", minWidth: 40, sortable: true},
        	  {id: "PRIORITY", name: "PRIORITY", field: "PRIORITY", minWidth: 40, sortable: true},
        	  {id: "LOTID", name: "LOTID", field: "LOTID", minWidth: 60, sortable: true},
        	  {id: "BATCHID", name: "BATCHID", field: "BATCHID", minWidth: 60, sortable: true},
        	  {id: "STEPID", name: "STEPID", field: "STEPID", minWidth: 60, sortable: true},
        	  {id: "PROCESSID", name: "PROCESSID", field: "PROCESSID", minWidth: 60, sortable: true},
        	  {id: "DESCRIPTION", name: "DESCRIPTION", field: "DESCRIPTION", minWidth: 60, sortable: true},
        	  {id: "CREATE USER", name: "CREATE USER", field: "CREATEUSER", minWidth: 60, sortable: true},
        	  {id: "BATCH TYPE", name: "BATCH TYPE", field: "BATCHTYPE", minWidth: 60, sortable: true}
        	];
        var options = {
	        enableCellNavigation: true,
	    	forceFitColumns: false,
	    	autoExpandColumns : true,
	    	topPanelHeight: 30,
	    	rowHeight: 21,
	    	enableColumnReorder: true
        };
          
          dataView2<c:out value="${param.uuid }" /> = new Slick.Data.DataView({ inlineFilters: true });
          grid2<c:out value="${param.uuid }" /> = new Slick.Grid("#list2<c:out value="${param.uuid }" />", dataView2<c:out value="${param.uuid }" />, columns, options);
          grid2<c:out value="${param.uuid }" />.setSelectionModel(new Slick.RowSelectionModel());
          var columnpicker = new Slick.Controls.ColumnPicker(columns, grid2<c:out value="${param.uuid }" />, options);
        	  // 그리드 정렬 
          grid2<c:out value="${param.uuid }" />.onSort.subscribe(function(e, args) {
    			  var field = args.sortCol.field;
    		      var sign = args.sortAsc ? 1: -1;
    		      dataView2<c:out value="${param.uuid }" />.sort(function (dataRow1, dataRow2) {
    		        value1 = dataRow1[field];
    		        if(value1 == null) value1 = "";
    		        value2 = dataRow2[field];
    		        if(value2 == null) value2 = "";
    		        var result = (value1 ==value2 ? 0 : (value1 > value2 ? 1: -1)) * sign;
    		        return result;
    		      });
    		      grid2<c:out value="${param.uuid }" />.invalidate();
    			  grid2<c:out value="${param.uuid }" />.render();
    		  });
    		  // 마우스 오른쪽 버튼 클릭
    		  grid2<c:out value="${param.uuid }" />.onContextMenu.subscribe(function (e) {
    		  	e.preventDefault();
    		  	var cell = grid2<c:out value="${param.uuid }" />.getCellFromEvent(e);
    		  	selRow = cell.row;
    		  	$("#contextMenu").data("row", cell.row).css("top", e.pageY).css("left", e.pageX) .show();
    		  	$("body").one("click", function () {
    		  		$("#contextMenu").hide();
    		  	});
    		});
    		 grid2<c:out value="${param.uuid }" />.onContextMenu.subscribe(function (e) {
  			  	e.preventDefault();
  			  	var cell = grid2<c:out value="${param.uuid }" />.getCellFromEvent(e);
  			  	selRow = cell.row;
  			  	$("#contextMenu a:eq(1)").hide();
  			  	$("#contextMenu").data("row", cell.row).css("top", e.pageY).css("left", e.pageX) .show();
  			  	$("body").one("click", function () {
  			  		$("#contextMenu").hide();
  			  	});
  			});
          dataView2<c:out value="${param.uuid }" />.onRowCountChanged.subscribe(function (e, args) {
	     	console.log("onRowCountChanged");
	         grid2<c:out value="${param.uuid }" />.updateRowCount();
	         grid2<c:out value="${param.uuid }" />.render();
	         loadingbarFadeOut();
	      });
	     
	      dataView2<c:out value="${param.uuid }" />.onPagingInfoChanged.subscribe(function (e, pagingInfo) {
	     	  console.log("onPagingInfoChanged :"+JSON.stringify(pagingInfo));
	          grid2<c:out value="${param.uuid }" />.render();
	      });
    }
    
    var dataView3<c:out value="${param.uuid }" />;
    var grid3<c:out value="${param.uuid }" />;
    var data3<c:out value="${param.uuid }" /> = [];
    // 테이블  생성
    function drawGrid3<c:out value="${param.uuid }" />(){
        var columns = [
        	  {id: "TIME", name: "TIME", field: "TIME_EX", minWidth: 170, cssClass: "cell-title", sortable: true},
        	  {id: "TRANSPORTCOMMANDID", name: "TRANSPORTCOMMANDID", field: "TRANSPORTCOMMANDID", minWidth: 180, sortable: true},
        	  {id: "TRANSPORTJOBID", name: "TRANSPORTJOBID", field: "TRANSPORTJOBID", minWidth: 180, sortable: true},
        	  {id: "STATE", name: "STATE", field: "STATE", minWidth: 105, sortable: true},
        	  {id: "CARRIER", name: "CARRIER", field: "CARRIER", minWidth: 80, sortable: true},
        	  {id: "FROM MACHINE", name: "FROM MACHINE", field: "SOURCEMACHINENAME", minWidth: 80, sortable: true},
        	  {id: "FROM MACHINETYPE", name: "FROM MACHINETYPE", field: "SOURCEMACHINETYPE2", minWidth: 100, sortable: true},        	  
        	  {id: "FROM UNIT", name: "FROM UNIT", field: "SOURCEUNITNAME", minWidth: 80, sortable: true},
        	  {id: "TRANSPORT MACHINE", name: "TRANSPORT MACHINE", field: "TRANSPORTMACHINENAME", minWidth: 80, sortable: true},
        	  {id: "TRANSPORT UNIT", name: "TRANSPORT UNIT", field: "TRANSPORTUNITNAME", minWidth: 80, sortable: true},
        	  {id: "TO MACHINE", name: "TO MACHINE", field: "DESTMACHINENAME", minWidth: 100, sortable: true},
        	  {id: "TO MACHINETYPE", name: "TO MACHINETYPE", field: "DESTMACHINETYPE2", minWidth: 100, sortable: true},
        	  {id: "TO_TYPE", name: "TO_TYPE", field: "DESTTYPE", minWidth: 40, sortable: true},
        	  {id: "TO UNIT", name: "TO UNIT", field: "DESTUNITNAME", minWidth: 100, sortable: true},
        	  {id: "FIXEDROUTE", name: "FIXEDROUTE", field: "FIXEDROUTE", minWidth: 20, sortable: true},
        	  {id: "PRIORITY", name: "PRIORITY", field: "PRIORITY", minWidth: 20, sortable: true},
        	  {id: "DESCRIPTION", name: "DESCRIPTION", field: "DESCRIPTION", minWidth: 20, sortable: true}
        	];
        var options = {
	        enableCellNavigation: true,
	        forceFitColumns: false,
	    	autoExpandColumns : true,
	    	topPanelHeight: 30,
	    	rowHeight: 21,
	    	enableColumnReorder: true
        };
          
          dataView3<c:out value="${param.uuid }" /> = new Slick.Data.DataView({ inlineFilters: true });
          grid3<c:out value="${param.uuid }" /> = new Slick.Grid("#list3<c:out value="${param.uuid }" />", dataView3<c:out value="${param.uuid }" />, columns, options);
          grid3<c:out value="${param.uuid }" />.setSelectionModel(new Slick.RowSelectionModel());
          var columnpicker = new Slick.Controls.ColumnPicker(columns, grid3<c:out value="${param.uuid }" />, options);
        	  // 그리드 정렬 
    		  grid3<c:out value="${param.uuid }" />.onSort.subscribe(function(e, args) {
    			  var field = args.sortCol.field;
    		      var sign = args.sortAsc ? 1: -1;
    		      dataView3<c:out value="${param.uuid }" />.sort(function (dataRow1, dataRow2) {
    		        value1 = dataRow1[field];
    		        if(value1 == null) value1 = "";
    		        value2 = dataRow2[field];
    		        if(value2 == null) value2 = "";
    		        var result = (value1 ==value2 ? 0 : (value1 > value2 ? 1: -1)) * sign;
    		        return result;
    		      });
    		      grid3<c:out value="${param.uuid }" />.invalidate();
    			  grid3<c:out value="${param.uuid }" />.render();
    		  });
    		  // 마우스 오른쪽 버튼 클릭
    		  grid3<c:out value="${param.uuid }" />.onContextMenu.subscribe(function (e) {
    		  	e.preventDefault();
    		  	var cell = grid3<c:out value="${param.uuid }" />.getCellFromEvent(e);
    		  	selRow = cell.row;
    		  	$("#contextMenu").data("row", cell.row).css("top", e.pageY).css("left", e.pageX) .show();
    		  	$("body").one("click", function () {
    		  		$("#contextMenu").hide();
    		  	});
    		});
    		grid3<c:out value="${param.uuid }" />.onContextMenu.subscribe(function (e) {
  			  	e.preventDefault();
  			  	var cell = grid3<c:out value="${param.uuid }" />.getCellFromEvent(e);
  			  	selRow = cell.row;
  			  	$("#contextMenu a:eq(1)").hide();
  			  	$("#contextMenu").data("row", cell.row).css("top", e.pageY).css("left", e.pageX) .show();
  			  	$("body").one("click", function () {
  			  		$("#contextMenu").hide();
  			  	});
  			});
          dataView3<c:out value="${param.uuid }" />.onRowCountChanged.subscribe(function (e, args) {
  	     	console.log("onRowCountChanged");
  	         grid3<c:out value="${param.uuid }" />.updateRowCount();
  	         grid3<c:out value="${param.uuid }" />.render();
  	         loadingbarFadeOut();
  	      });
  	     
  	      dataView3<c:out value="${param.uuid }" />.onPagingInfoChanged.subscribe(function (e, pagingInfo) {
  	     	  console.log("onPagingInfoChanged :"+JSON.stringify(pagingInfo));
  	          grid3<c:out value="${param.uuid }" />.render();
  	      });
    }
    
	
	// 초기화
	function init<c:out value="${param.uuid }" />(){
		init();
		setDatepicker('<c:out value="${param.uuid }" />');
		// 레벨 기본 세팅
		if($content.find("#type").val() != "S"){
			$content.find('#fromDt<c:out value="${param.uuid }" />').val($.datepicker.formatDate('yy.mm.dd', new Date()));
			$content.find('#toDt<c:out value="${param.uuid }" />').val($.datepicker.formatDate('yy.mm.dd', new Date()));
			$content.find(":checkbox[name^=level] :gt(3)").prop("checked",true);
		}
		
		drawGrid<c:out value="${param.uuid }" />();
		drawGrid2<c:out value="${param.uuid }" />();
		drawGrid3<c:out value="${param.uuid }" />();
		
		//필터 리스트 적용
		// 20220621	X0122410	fabSite 추가
		getFilterList($content.find('input[name="rdoFabSite"]:checked').val());
		
		// 2021.4.16, X0122410.	fab별로 machinetype list 가져오기
		setTimeout(function(){	
			var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
			getMachineTypeFromFab2(_fabSite,"fab", "transportMachineType|fromMachineType|toMachineType", "singleFilterChkBoxTransportMachineType|singleFilterChkBoxFromMachineType|singleFilterChkBoxToMachineType");
		}, 800);
	}
	// 조회
	function getLogList<c:out value="${param.uuid }" />(page){
		if(!chkValidate()) return;
		$content.find("#searchBtn").addClass('disabled');
		showLoadingbar($("#list<c:out value="${param.uuid }" />"));
		$content.find('#page').val(page);
		$content.find("#pageTxt").text(page);
		$content.find(".ui-icon-seek-next,.ui-icon-seek-prev ").addClass("ui-state-disabled");
		var from = $content.find("#fromDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#fromHour").val() +$content.find("#fromMin").val()+$content.find("#fromSec").val();
		var to = $content.find("#toDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#toHour").val() +$content.find("#toMin").val()+$content.find("#toSec").val();
		$content.find("#from").val(from);
		$content.find("#to").val(to);
		
		//Transport machine
		var isChk = $content.find("#singleFilterTransport").is(":checked");
		if(isChk){  // single filter
			$content.find(":hidden[name=transportMachineName]").val($content.find('#transportMachineName1').val());
		}else{      // multi filter
			$content.find(":hidden[name=transportMachineName]").val($content.find('#transportMachineName2').val());
		}
		//From machine
		isChk = $content.find("#singleFilterFrom").is(":checked");
		if(isChk){  // single filter
			$content.find(":hidden[name=fromMachineName]").val($content.find('#fromMachineName1').val());
		}else{      // multi filter
			$content.find(":hidden[name=fromMachineName]").val($content.find('#fromMachineName2').val());
		}		
		//To machine
		isChk = $content.find("#singleFilterTo").is(":checked");
		if(isChk){  // single filter
			$content.find(":hidden[name=toMachineName]").val($content.find('#toMachineName1').val());
		}else{      // multi filter
			$content.find(":hidden[name=toMachineName]").val($content.find('#toMachineName2').val());
		}
		
		var searchOption = $content.find("input[name=searchOption]:checked").val();
		if(searchOption == 'carrier'){
			$content.find("#carrier").val($content.find("#carrierLotId").val());
			$content.find("#lotId").val("");
		}else{
			$content.find("#lotId").val($content.find("#carrierLotId").val());
			$content.find("#carrier").val("");
		}
		
		var transportMachineType = $content.find(":checkbox[id^=cTransportMachineType]:checked").map(function() { return this.value; }).get().join(',');
		var fromMachineType = $content.find(":checkbox[id^=cFromMachineType]:checked").map(function() { return this.value; }).get().join(',');
		var toMachineType = $content.find(":checkbox[id^=cToMachineType]:checked").map(function() { return this.value; }).get().join(',');
		$("#transportMachineType").val(transportMachineType);
		$("#fromMachineType").val(fromMachineType);
		$("#toMachineType").val(toMachineType);
		$content.find("#fabSite").val($content.find('input[name="rdoFabSite"]:checked').val());
		var param = $content.find("#searchForm").serializeObject();
		console.log("param : ", param);
		//2021.03.24	X0122410 : machineTypes parameter 추가
		var transportMachineTypes = $content.find(":checkbox[name^=transportMachineType]:checked").map(function(){return $(this).val(); }).get().join();
		var fromMachineTypes = $content.find(":checkbox[name^=fromMachineType]:checked").map(function(){return $(this).val(); }).get().join();
		var toMachineTypes = $content.find(":checkbox[name^=toMachineType]:checked").map(function(){return $(this).val(); }).get().join();
		param['transportMachineTypes'] = transportMachineTypes;
		param['fromMachineTypes'] = fromMachineTypes;
		param['toMachineTypes'] = toMachineTypes;
		//console.dir(param);
		var url = "<c:url value='/tran/ajax/getReturnLogList.do' />";
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
	    					if(data<c:out value="${param.uuid }" />.length <= 0){
	    						 grid<c:out value="${param.uuid }" />.invalidateAllRows();
	    						$content.find('.grid-canvas').html('<div class="alert-info-grid">No Record(s) Found</div>');
	    					}
	    					setPagerState(result.rows);
	                	}
	                	loadingbarFadeOut();
	                	$content.find("#searchBtn").removeClass('disabled');
	                }
		});
	}
	
	// 테이블 컬럼 더블클릭 이벤트
	function setSearchOption<c:out value="${param.uuid }" />(colName , colValue){
		console.log(colName);
		switch(colName) {
		    case "LOTID":
		    	$content.find("input[name=carrierLotId]").val(colValue);
		        break;
		    case "CARRIER":
		    	$content.find("input[name=carrierLotId]").val(colValue);
		        break;
		    case "TRANSPORTJOBID":
		    	$content.find("input[name=transportJobId]").val(colValue);
		        break;
		    case "SOURCEMACHINENAME":
		    	$content.find("#fromMachineName1").val(colValue).prop("selected", true);
		        break;
		    case "DESTMACHINENAME":
		    	$content.find("#toMachineName1").val(colValue).prop("selected", true);
		        break;
		    default:
		}
		
	}
	
	function reset<c:out value="${param.uuid }" />(){
		$content.find("#filterTransport").val("01");
		$content.find("#filterFrom").val("01");
		$content.find("#filterTo").val("01");
		$content.find("#searchForm")[0].reset();
		$content.find(":radio[name=time]:eq(0)").trigger("click");
		if($content.find("#transportMachineName2").length > 0 )
			$content.find("#transportMachineName2").prop('disabled',true);
		if($content.find("#fromMachineName2").length > 0 )
			$content.find("#fromMachineName2").prop('disabled',true);
		if($content.find("#toMachineName2").length > 0 )
			$content.find("#toMachineName2").prop('disabled',true);
		setFilterTransport<c:out value="${param.uuid }" />();
		setFilterFrom<c:out value="${param.uuid }" />();
		setFilterTo<c:out value="${param.uuid }" />();
	}
	
		// 검색옵션 Single  / multi 설정
		function setFilterTransport<c:out value="${param.uuid }" />(){
			var filter = $content.find("#filterTransport").val();
			if(filter == "01"){
				$content.find("#singleFilterTransport").prop("checked",true);
				$content.find("#multiFilterTransport").prop("checked",false);
				$content.find(".singleFilterTransport").find(":checkbox").prop('checked',false);
				//$content.find(".singleFilterTransport").find("#transportMachineType1").prop('checked',true);
				$content.find(".singleFilterTransport").find("select , :checkbox").prop('disabled',false);
				$content.find(".multiFilterTransport").find(":text").prop('disabled',true);
				$content.find("#transportMachineBtn").addClass('disabled');
			}else{
				$content.find("#singleFilterTransport").prop("checked",false);
				$content.find("#multiFilterTransport").prop("checked",true);
				$content.find(".singleFilterTransport").find(":checkbox").prop('checked',false);
				//$content.find(".singleFilterTransport").find("#transportMachineType1").prop('checked',true);
				$content.find(".singleFilterTransport").find("select , :checkbox").prop('disabled',true);
				$content.find(".multiFilterTransport").find(":text").prop('disabled',false);
				$content.find("#transportMachineBtn").removeClass('disabled');
			}
		} 
		
		// 검색옵션 Single  / multi 설정
		function setFilterFrom<c:out value="${param.uuid }" />(){
			var filter = $content.find("#filterFrom").val();
			if(filter == "01"){
				$content.find("#singleFilterFrom").prop("checked",true);
				$content.find("#multiFilterFrom").prop("checked",false);
				$content.find(".singleFilterFrom").find(":checkbox").prop('checked',false);
				//$content.find(".singleFilterFrom").find("#fromMachineType1").prop('checked',true);
				$content.find(".singleFilterFrom").find("select , :checkbox").prop('disabled',false);
				$content.find(".multiFilterFrom").find(":text").prop('disabled',true);
				$content.find("#fromMachineBtn").addClass('disabled');
			}else{
				$content.find("#singleFilterFrom").prop("checked",false);
				$content.find("#multiFilterFrom").prop("checked",true);
				$content.find(".singleFilterFrom").find(":checkbox").prop('checked',false);
				//$content.find(".singleFilterFrom").find("#fromMachineType1").prop('checked',true);
				$content.find(".singleFilterFrom").find("select , :checkbox").prop('disabled',true);
				$content.find(".multiFilterFrom").find(":text").prop('disabled',false);
				$content.find("#fromMachineBtn").removeClass('disabled');
			}
		} 
		
		// 검색옵션 Single  / multi 설정
		function setFilterTo<c:out value="${param.uuid }" />(){
			var filter = $content.find("#filterTo").val();
			if(filter == "01"){
				$content.find("#singleFilterTo").prop("checked",true);
				$content.find("#multiFilterTo").prop("checked",false);
				$content.find(".singleFilterTo").find(":checkbox").prop('checked',false);
				$content.find(".singleFilterTo").find("#toMachineType1").prop('checked',true);
				$content.find(".singleFilterTo").find("select , :checkbox").prop('disabled',false);
				$content.find(".multiFilterTo").find(":text").prop('disabled',true);
				$content.find("#toMachineBtn").addClass('disabled');
			}else{
				$content.find("#singleFilterTo").prop("checked",false);
				$content.find("#multiFilterTo").prop("checked",true);
				$content.find(".singleFilterTo").find(":checkbox").prop('checked',false);
				$content.find(".singleFilterTo").find("#toMachineType1").prop('checked',true);
				$content.find(".singleFilterTo").find("select , :checkbox").prop('disabled',true);
				$content.find(".multiFilterTo").find(":text").prop('disabled',false);
				$content.find("#toMachineBtn").removeClass('disabled');
			}
		} 
	
	// Filter View 숨기기
	$content.find("#fold_filter_view").click(function(){
		$content.find("#filter_view").css("display", "none");
		$content.find("#unfold_filter_view_wrap").css("display", "");
		grid<c:out value="${param.uuid }" />.resizeCanvas();
		grid2<c:out value="${param.uuid }" />.resizeCanvas();
		grid3<c:out value="${param.uuid }" />.resizeCanvas();
	});
	
	// Filter View 보이기
	$content.find("#unfold_filter_view").click(function(){
		$content.find("#unfold_filter_view_wrap").css("display", "none");
		$content.find("#filter_view").css("display", "");
		grid<c:out value="${param.uuid }" />.resizeCanvas();
		grid2<c:out value="${param.uuid }" />.resizeCanvas();
		grid3<c:out value="${param.uuid }" />.resizeCanvas();
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
	reset<c:out value="${param.uuid }" />();
</script>