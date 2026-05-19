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
             <a href="#" class="location"><spring:message code="site.totalNewLogList" text="default text" /></a>
         </span>
         <span class="loc_info_ico loc_info_ico_arr_depth"></span>
         <span class="location_box">
             <a href="#" class="location"><spring:message code="site.totalNewLogList" text="default text" /></a>
         </span>
     </div>
     <!-- //Location Information -->
     <!-- Page Title -->
     <table class="page_tit">
         <tr>
             <td class="tit_area">
                 <div class="tit"><spring:message code="site.totalNewLogList" text="default text" /></div>
             </td>
         </tr>
     </table>
     <!-- //Page Title -->
     <!-- Search Type01 -->
     <!-- Sub Title -->
     <div class="lay_item vert">
     <form id="searchForm" name="searchForm" method="post" >
     <input type="hidden" id="fabSite" name="fabSite" value="" />
     <input type="hidden" id="type" name="type" value="${param.type}" />
     <input type="hidden" id="page" name="page" value="1" />
     <input type="hidden" name="machineName" value="" />
     <input type="hidden" id="gFrom" name="gFrom" value="<c:out value="${param.gFrom }" />" />
     <input type="hidden" id="filter" name="filter" value="01" />
     <input type="hidden" id="gTo" name="gTo" value="<c:out value="${param.gTo }" />" />
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
                                         	<!-- 2021. 4. 9, X0122410 : fab 선택box -->
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
							                                    	<input type="checkbox" class="jqForm" id="fab1" name="fab1" value="ALL" checked><label for="fab1">ALL</label><BR>
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
				                            <tbody id="test" >
				                                <tr>
				                                    <td class="condition_t_head_top" colspan="3">
				                                    	<i class="minus square icon"></i>
				                                    	<span>Machine</span>
				                                    </td>
				                                </tr>
				                                <tr>
				                                    <td class="condition_t_data" colspan="3">
				                                    	<input type="checkbox" class="jqForm" id="singleFilter" name="singleFilter" value="01" <c:if test="${param.singleFilter == '01' }" >checked="checked"</c:if> ><label for="singleFilter">Single Filter</label>
				                                    </td>
				                                </tr>
				                                <tr class="singleFilter" >
				                                    <th scope="col" class="condition_t_head">AREA</th>
				                                    <td class="condition_t_data" colspan="2">
				                                        <select class="areaName_machine" id="areaName" name="areaName" style="width: 143px" >
				                                            <option value="ALL" <c:if test="${param.areaName == 'ALL' }" >selected="selected"</c:if>>ALL</option>
				                                            <%-- <option value="CLEAN" <c:if test="${param.areaName == 'CLEAN' }" >selected="selected"</c:if>>CLEAN</option>
				                                            <option value="CMP" <c:if test="${param.areaName == 'CMP' }" >selected="selected"</c:if>>CMP</option>
				                                            <option value="CU" <c:if test="${param.areaName == 'CU' }" >selected="selected"</c:if>>CU</option>
				                                            <option value="DIFF" <c:if test="${param.areaName == 'DIFF' }" >selected="selected"</c:if>>DIFF</option>
				                                            <option value="ETCH" <c:if test="${param.areaName == 'ETCH' }" >selected="selected"</c:if>>ETCH</option>
				                                            <option value="F/C" <c:if test="${param.areaName == 'F/C' }" >selected="selected"</c:if>>F/C</option>
				                                            <option value="FIO" <c:if test="${param.areaName == 'FIO' }" >selected="selected"</c:if>>FIO</option>
				                                            <option value="IMP" <c:if test="${param.areaName == 'IMP' }" >selected="selected"</c:if>>IMP</option>
				                                            <option value="INV" <c:if test="${param.areaName == 'INV' }" >selected="selected"</c:if>>INV</option>
				                                            <option value="LIFTER" <c:if test="${param.areaName == 'LIFTER' }" >selected="selected"</c:if>>LIFTER</option>
				                                            <option value="PHOTO" <c:if test="${param.areaName == 'PHOTO' }" >selected="selected"</c:if>>PHOTO</option>
				                                            <option value="T/F" <c:if test="${param.areaName == 'T/F' }" >selected="selected"</c:if>>T/F</option>
				                                            <option value="반송" <c:if test="${param.areaName == '반송' }" >selected="selected"</c:if>>반송</option> --%>
				                                        </select>
				                                    </td>
				                                </tr>
				                                <tr class="singleFilter" >
				                                    <th scope="col" class="condition_t_head">BAY</th>
				                                    <td class="condition_t_data" colspan="2" >
				                                         <select class="bayName" id="bayName" name="bayName" style="width: 143px" >
				                                            <option value="ALL" <c:if test="${param.bayName == 'ALL' }" >selected="selected"</c:if>>ALL</option>
				                                            <%-- <c:forEach  items="${bayNameList}" var="row" varStatus="status"  >
				                                            	<option value="<c:out value="${row.BAYNAME  }" />" <c:if test="${param.bayName eq row.BAYNAME }" >selected="selected"</c:if>><c:out value="${row.BAYNAME  }" /></option>
				                                            </c:forEach> --%>
				                                        </select>
				                                    </td>
				                                </tr>
				                                <tr  id="singleFilterChkBoxFab" class="singleFilter"  >
				                                    <th scope="col" class="condition_t_head">Type</th>
				                                    <!-- 2021.03.22	X0122410 machinetype 리스트를 서버에서 가져와서 보여준다 -->
				                                    <%-- <td class="condition_t_data" >
				                                         <input type="checkbox" class="jqForm" id="machineType1" name="machineType1" value="ALL" checked ><label for="srch_chbox00">ALL</label><BR>
				                                         <input type="checkbox" class="jqForm" id="machineType2" name="machineType2" value="STOCKER" <c:if test="${param.machineType2 == 'STOCKER' }" >checked="checked"</c:if>><label for="srch_chbox00">STOCKER</label><BR>
				                                         <input type="checkbox" class="jqForm" id="machineType3" name="machineType3" value="STB" <c:if test="${param.machineType3 == 'STB' }" >checked="checked"</c:if>><label for="srch_chbox00">STB</label><BR>
				                                         <input type="checkbox" class="jqForm" id="machineType4" name="machineType4" value="LIFTER" <c:if test="${param.machineType4 == 'LIFTER' }" >checked="checked"</c:if>><label for="srch_chbox00">LIFTER</label><BR>
				                                    </td>
				                                    <td class="condition_t_data" id="singleFilterChkBox" >
				                                         <input type="checkbox" class="jqForm" id="machineType5" name="machineType5" value="CONVEYOR" <c:if test="${param.machineType5 == 'CONVEYOR' }" >checked="checked"</c:if>><label for="srch_chbox00">CONVEYOR</label><BR>
				                                         <input type="checkbox" class="jqForm" id="machineType6" name="machineType6" value="PROCESS" <c:if test="${param.machineType6 == 'PROCESS' }" >checked="checked"</c:if>><label for="srch_chbox00">PROCESS</label><BR>
				                                         <input type="checkbox" class="jqForm" id="machineType7" name="machineType7" value="OHT" <c:if test="${param.machineType7 == 'OHT' }" >checked="checked"</c:if>><label for="srch_chbox00">OHT</label><BR>
				                                    </td> --%>	
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
				                                    	<input type="checkbox" class="jqForm" id="multiFilter" name="multiFilter" value="02" <c:if test="${param.multiFilter == '02' }" >checked="checked"</c:if>><label for="multiFilter">Multi Filter</label>
				                                    </td>
				                                </tr>
				                                <tr class="multiFilter" >
				                                 	<td class="condition_t_data" colspan="3">
				                                    	 <input type="text" id="machineName2" name="machineName2"  style="width:163px" value="<c:out value="${param.machineName2 }" />" />
		                                                    <div id="machineBtn" class="mini ui primary button" style="width:93px;float: right;margin-left: 4px">
																<i class="tasks icon"></i>Machine
															</div>
				                                    </td>
				                                </tr>
				                            </tbody>
				                        </table>
				                        </div>
        								</div>
        								<%-- <div class="srch_type01">
              								<div class="condition_area">
												<table class="condition_table" summary="<spring:message code="site.common.filter" text="default text" />">
						                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
						                            <tbody>
						                                <tr>
						                                    <td class="condition_t_head_top" colspan="3">
						                                    	<i class="add square icon"></i>
						                                    	<span>Level</span>
						                                    </td>
						                                </tr>
						                                <tr>
						                                	<th scope="col" class="condition_t_head">Type</th>
						                                    <td class="condition_t_data">
						                                         <input type="checkbox" class="jqForm" id="level1" name="level1" <c:if test="${param.level1 == 'ALL' }" >checked="checked"</c:if> value="ALL"  ><label for="level1">ALL</label><BR>
						                                         <c:forEach  items="${levels}" var="level" varStatus="status">
						                                         	<c:if test="${status.index < 3}">
																    	<c:set var="num" value="${status.index + 2}"/>
																 		<c:set var="isVal" value="F" />
																		<c:forEach var="item" items="${params.level}">																			
																		  <c:if test="${item eq level}">																			  	
																		    <c:set var="isVal" value="T" />
																		  </c:if>																			  
																		</c:forEach>
																		<input type="checkbox" class="jqForm" id="level<c:out value="${num}"/>" name="level<c:out value="${num}"/>" <c:if test="${isVal eq 'T'}">checked="checked"</c:if> value="<c:out value="${level}"/>" ><label for="level<c:out value="${num}"/>"><c:out value="${level}"/></label><BR>
																  	</c:if>																 		
		                                            			</c:forEach>							                                         
						                                    </td>
						                                    <td class="condition_t_data">
						                                         <c:forEach  items="${levels}" var="level" varStatus="status">
						                                         	<c:if test="${status.index >= 3}">
																    	<c:set var="num" value="${status.index + 2}"/>
																 		<c:set var="isVal" value="F" />
																		<c:forEach var="item" items="${params.level}">																			
																		  <c:if test="${item eq level}">																			  	
																		    <c:set var="isVal" value="T" />
																		  </c:if>																			  
																		</c:forEach>
																		<input type="checkbox" class="jqForm" id="level<c:out value="${num}"/>" name="level<c:out value="${num}"/>" <c:if test="${isVal eq 'T'}">checked="checked"</c:if> value="<c:out value="${level}"/>" ><label for="level<c:out value="${num}"/>"><c:out value="${level}"/></label><BR>
																  	</c:if>																 		
		                                            			</c:forEach>		
						                                    </td>
						                                </tr>
						                            </tbody>
						                        </table>
					                        </div>
                						</div> --%>
        								<div class="srch_type01">
     									<div class="condition_area">
                                             <table class="condition_table" summary="<spring:message code="site.common.filter" text="default text" />">
				                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
				                            <tbody>
				                                <tr>
				                                    <td class="condition_t_head_top" colspan="2">
				                                    	<i class="minus square icon"></i>
				                                    	<span>Condition</span>
				                                    </td>
				                                </tr>
				                             <%--    <tr>
				                                	<th scope="col" class="condition_t_head" style="width:300px">Search condition</th>
				                                    <td class="condition_t_data">
				                                         <input type="radio" class="jqForm" id="searchOption1" name="searchOption" value="AND" <c:if test="${param.searchOption == 'AND' }" >checked="checked"</c:if> ><label for="srch_radio00">AND</label>
				                                         <input type="radio" class="jqForm" id="searchOption2" name="searchOption" value="OR" <c:if test="${param.searchOption == 'OR' }" >checked="checked"</c:if> ><label for="srch_radio00">OR</label>
				                                    </td>
				                                </tr> --%>
				                                <tr>
				                                	<th scope="col" class="condition_t_head">Carrier</th>
				                                    <td class="condition_t_data">
				                                         <input type="text" id="carrier" name="carrier" value="<c:out value="${param.carrier }" />" />
				                                    </td>
				                                </tr>
				                               <%--  <tr>
				                                	<th scope="col" class="condition_t_head">MES - MCS</th>
				                                    <td class="condition_t_data">
				                                         <select class="" id="command" name="comMsgName" style="width:143px">
				                                            <c:forEach  items="${comMsgNameList}" var="row" varStatus="status"  >
				                                            	<option value="<c:out value="${row.value  }" />" <c:if test="${param.comMsgName eq row.value }" >selected="selected"</c:if>><c:out value="${row.value  }" /></option>
				                                            </c:forEach>
				                                        </select>
				                                    </td>
				                                </tr>
				                                <tr>
				                                	<th scope="col" class="condition_t_head">MCS - MCP</th>
				                                    <td class="condition_t_data">
				                                         <select class="" id="messageName" name="operationName" style="width: 143px">
				                                            <option value="">선택</option>
				                                            <option value="HostInterface.send" <c:if test="${param.operationName eq 'HostInterface.send' }" >selected="selected"</c:if> >HostInterface.send</option>
				                                        </select>
				                                    </td>
				                                </tr>
				                                <tr>
				                                	<th scope="col" class="condition_t_head">Process Name</th>
				                                    <td class="condition_t_data">
				                                        <input type="text" id="process" name="process" value="<c:out value="${param.process }" />" />
				                                    </td>
				                                </tr>
				                                <tr>
				                                	<th scope="col" class="condition_t_head">Transaction ID</th>
				                                    <td class="condition_t_data">
				                                         <input type="text" id="transactionId" name="transactionId" value="<c:out value="${param.transactionId }" />" />
				                                    </td>
				                                </tr>
				                                <tr>
				                                	<th scope="col" class="condition_t_head">Command ID</th>
				                                    <td class="condition_t_data">
				                                         <input type="text" id="commandId" name="commandId" value="<c:out value="${param.commandId }" />" />
				                                    </td>
				                                </tr> --%>
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
                                      <i id="foldTableBtn2" class="minus square icon large" style="color:#ccd2de"></i>
                                      <span class="txt">목록
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
                              <div id="list<c:out value="${param.uuid }" />" class="gridForResize_single" style="width:100%;height:915px; background: white; outline: 0; border: 1px solid gray;">
                              </div>
                              <c:import url="/WEB-INF/views/common/slickGridPager.jsp" charEncoding="utf-8" />
				          </div>
                     </div>
              </div>
     	</div>
     </form>
 </div>
<script type="text/javascript">
	$content = $("#body_${param.uuid }");
	var dataView<c:out value="${param.uuid }" />;
	var grid<c:out value="${param.uuid }" />;
	var data<c:out value="${param.uuid }" /> = [];
	var unfoldIds<c:out value="${param.uuid }" /> = [];
	var unfoldIdsChild<c:out value="${param.uuid }" /> = {};
	unfoldIds<c:out value="${param.uuid }" />.push(-1);
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
				if($content.find("#reload").val() == "01"){
					unfoldIds<c:out value="${param.uuid }" /> = [];
					unfoldIdsChild<c:out value="${param.uuid }" /> = {};
				}
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
				if($content.find("#reload").val() == "01"){
					unfoldIds<c:out value="${param.uuid }" /> = [];
					unfoldIdsChild<c:out value="${param.uuid }" /> = {};
				}
				var page = Number($content.find("#page").val()) + 1;
				$content.find("#page").val(page);
				$content.find("#pageTxt").text(page);
				getLogList<c:out value="${param.uuid }" />(page);
			});
			
			// Source Machine > \ AREA 셀렉트 값 변경 이벤트
			$content.find("#areaName").change(function(){		
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				getBayFromArea(_fabSite,"fab", "areaName", "bayName");	// 200826 hgJeon Area 변경 시 bayList 변경 추가
				getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");
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
				if(val == "ALL"){ // ALL 체크시, 다른 체크 박스 해제
					$content.find(":checkbox[name^=machineType]:gt(0)").prop("checked",false);
				}else{ // 다른 체크박스 체크시 , ALL 체크박스 해제
					$content.find(":checkbox[name^=machineType]:eq(0)").prop("checked",false);
				}
				getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");
			}); 
			*/
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
			
			// 20180615 FAB 클릭 이벤트
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
				$content.find("#gFrom").val(from);
				$content.find("#gTo").val(to);
			});
			
			// paste 버튼 클릭
			$content.find("#pasteBtn").click(function(){
				var gFrom = $content.find("#gFrom").val();
				var gTo = $content.find("#gTo").val();
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
			
			/* $content.find(":checkbox[name^=machineType]").click(function(){
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				var val = $(this).val();
				if(val == "ALL"){
					$content.find(":checkbox[name^=machineType]:gt(0)").prop("checked",false);
				}else{
					$content.find(":checkbox[name^=machineType]:eq(0)").prop("checked",false);
				}
				getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");
			}); 
			*/
			$content.on("click",":checkbox[name^=machineType]", function(){				
				var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
				var val = $(this).val();
				if(val == "ALL"){
					$content.find(":checkbox[name^=machineType]:gt(0)").prop("checked",false);
				}else{
					$content.find(":checkbox[name^=machineType]:eq(0)").prop("checked",false);
				}
				getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");
			});
			
			// 조회 버튼 클릭 
			$content.find("#searchBtn").click(function(){
				unfoldIds<c:out value="${param.uuid }" /> = [];
				unfoldIdsChild<c:out value="${param.uuid }" /> = {};
				data<c:out value="${param.uuid }" /> = [];
				getLogList<c:out value="${param.uuid }" />(1);
				grid<c:out value="${param.uuid }" />.resizeCanvas();
			});
			
			// machine 버튼 클릭 
			$content.find("#machineBtn").click(function(){
				if($(this).hasClass("disabled")){
					return false;					
				}
				var url = "<c:url value='/tot/pop/machineNamePop.do' />";
				openPopup(url , 600 , 610);
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
 	
			// multi filter 클릭 이벤트
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
			/* $(document).on('dblclick',"#list", function() {
				var colName = $(this).attr("id");
				var colValue = $(this).text();
				switch(colName) {
				    case "carrier":
				    	$content.find("input[name=carrier]").val(colValue);
				        break;
				    case "machine":
				    	$content.find("#machineName1").val(colValue).prop("selected", true);
				        break;
				    case "commandId":
				    	$content.find("#commandId").val(colValue);
				        break;
				    case "command":
				    	$content.find("#command").val(colValue).prop("selected", true);
				        break;
				    case "messageName":
				    	$content.find("#messageName").val(colValue).prop("selected", true);
				        break;
				    case "process":
				    	$content.find("#process").val(colValue);
				        break;
				    case "transactionId":
				    	$content.find("#transactionId").val(colValue);
				        break;
				    case "commandId":
				    	$content.find("#commandId").val(colValue);
				        break;
				    default:
				}
				
			}); */
				
			// 테이블 행 클릭 이벤트
			$content.find("#totNew_table_body").on('click',".btn_txt.btn_type_a.btn_color_a, .btn_txt.btn_type_a.btn_color_b", function(){
				var thisClass = $(this);
				if(thisClass.attr('class')==='btn_txt btn_type_a btn_color_a'|| thisClass.attr('class')==='btn_txt btn_type_a btn_color_b'){
					var addQuery = $(this).parent().parent().attr("data-key");
					var thisRowIndex = $(this).parent().parent().get(0).rowIndex;
					var thisCarrierClass = $(this).parent().next().next().text();
					if(thisClass.attr('class')==='btn_txt btn_type_a btn_color_a'){
						thisClass.attr('class', 'btn_txt btn_type_a btn_color_b');						
						getLogDetail<c:out value="${param.uuid }" />(addQuery, thisRowIndex);
					}else{
						thisClass.attr('class', 'btn_txt btn_type_a btn_color_a');
						$.each($content.find("#totNew_table_body").children(), function(index,value){
							if($(value).attr('class')==='board_list_row boardListRow '+thisCarrierClass){
								$(value).remove();
							}
						});
						
					}	
				}
			});
			
			// 달력 초기화(시작일)
			$( "#fromDt<c:out value="${param.uuid }" />" ).datepicker({
                   showOn: "button",
                   buttonImage: "<c:url value='/styles/images/form/calendar.jpg' />",
                   buttonImageOnly: true,
                   buttonText: "Select date",
                   dateFormat: "yy.mm.dd",
                   changeMonth: true,
                   changeYear: true,
                   showButtonPanel: true
            });
			// 달력 초기화(종료일)
			$( "#toDt<c:out value="${param.uuid }" />" ).datepicker({
                 showOn: "button",
                 buttonImage: "<c:url value='/styles/images/form/calendar.jpg' />",
                 buttonImageOnly: true,
                 buttonText: "Select date",
                 dateFormat: "yy.mm.dd",
                 changeMonth: true,
                 changeYear: true,
                 showButtonPanel: true
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
			
			if($content.find("#type").val() != "S"){
				$content.find('#time1').trigger( "click" );
				$content.find("#singleFilter").trigger("click");
				$content.find("#searchOption2").trigger("click");
				//$content.find("#machineType1").trigger("click");
			}

    });
    // 로그 상세 조회
    function getLogDetail<c:out value="${param.uuid }" />(addQuery, thisRowIndex, thisCellIdx){    	
    	var url = "<c:url value='/totNew/ajax/getCarrierElapsed.do' />";	 
		var rowIdx = thisRowIndex;
		console.log("<spring:message code="site.totalNewLogList" text="default text" /> Click Event");
    	$.ajax({
	            url: url,
	            type:'post',
	            data:{"addQuery":addQuery},
	            async:false,
	            success:function(result){
	            	var parent = grid<c:out value="${param.uuid }" />.getDataItem(rowIdx);
    				var parentId = "#"+parent.CARRIER + parent.TOTAL_ELAPSED;
    				unfoldIdsChild<c:out value="${param.uuid }" />[parentId] = result.list.length;
	            	dataView<c:out value="${param.uuid }" />.setItems([]);
	            	for(var i=0;i<unfoldIds<c:out value="${param.uuid }" />.length;i++){
	            		if(unfoldIds<c:out value="${param.uuid }" />[i] > thisRowIndex){
	            			unfoldIds<c:out value="${param.uuid }" />[i] = unfoldIds<c:out value="${param.uuid }" />[i] + result.list.length;
	            		}
	            	}
	            	if(result != null  && result.list != null){
            			$.each(result.list, function(index, value){
	            			value.key = thisRowIndex+'detail';
            				data<c:out value="${param.uuid }" />.splice((rowIdx+1), 0, value);
	            			rowIdx++;
            			});
						dataView<c:out value="${param.uuid }" />.setItems(data<c:out value="${param.uuid }" />);
	            	}
	            	
	            	var columns = [
						{id: "BUTTON", name: "", field: "", width: 25, minWidth: 25, cssClass: "cell-title", sortable: true, formatter:buttonFormatter},
						{id: "TIME_EX", name: "TIME", field: "TIME_EX", width: 85, minWidth: 85, cssClass: "cell-title", sortable: true},
						{id: "FROM", defaultSortAsc: false, name: "FROM", field: "FROM", width: 45, sortable: true},
						{id: "TO", defaultSortAsc: false, name: "TO", field: "TO", width: 45, sortable: true},
						{id: "CARRIER", defaultSortAsc: false, name: "CARRIER", field: "CARRIER", width: 45, sortable: true},
						{id: "LOCATION_ID", defaultSortAsc: false, name: "LOCATION", field: "LOCATION_ID", width: 45, sortable: true},
						{id: "TOTAL_ELAPSED", name: "TOTAL_ELAPSED", field: "TOTAL_ELAPSED", width : 50, minWidth: 50,  sortable: true, formatter:timeCssFormatter},
						{id: "ELAPSED", name: "ELAPSED", field: "ELAPSED", width: 60, minWidth: 60, sortable: true, formatter:timeCssFormatter},
						{id: "SOURCE_ID", name: "SOURCE_ID", field: "SOURCE_ID", width: 50, sortable: true},
						{id: "SOURCE_TYPE", name: "SOURCE_TYPE", field: "SOURCE_TYPE", width: 30, sortable: true},
						{id: "DESTINATION_ID", name: "DESTINATION_ID", field: "DESTINATION_ID", width: 50, sortable: true},
						{id: "DESTINATION_TYPE", name: "DESTINATION_TYPE", field: "DESTINATION_TYPE", width: 30, sortable: true},
						{id: "MES-MCS MESSAGE", name: "COMMAND", field: "COMMAND", width : 145, minWidth: 145, sortable: true},
						{id: "MCS-MCP MESSAGE", name: "MESSAGENAME", field: "MESSAGENAME", width: 105, minWidth: 105, sortable: true},
						{id: "PROCESS", name: "PROCESS", field: "PROCESS", width: 25, minWidth: 25, sortable: true},
						{id: "TRANSACTIONID", name: "TRANSACTIONID", field: "TRANSACTIONID", width: 80, minWidth: 80, sortable: true},
						{id: "COMMANDID", name: "COM MANDID", field: "COMMANDID", width: 100, minWidth: 100, sortable: true},
	            	];
	            	var options = {
	            			enableCellNavigation: true,   // 대량 데이터 속도 개선
	            			forceFitColumns: false,        // 그리드 가로 스크롤 유무  
	            			autoExpandColumns : true,  // 그리드 사이즈 변경시, 스크롤 생성 유무
	            			topPanelHeight: 30,              // 헤더 높이 값
	            			enableColumnReorder: true  // 
	           			};
					grid<c:out value="${param.uuid }" />.setData(data<c:out value="${param.uuid }" />);
					grid<c:out value="${param.uuid }" />.render();
					loadingbarFadeOut();
	            }
        });
    };
	
 	// 20220621	X0122410	fabSite 추가
	// 초기화
	function init<c:out value="${param.uuid }" />(){
		init();
		setDatepicker('<c:out value="${param.uuid }" />');				
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
		var url = "<c:url value='/totNew/ajax/totalNewLogList.do' />";
		$.ajax({
	            url: url,
	            type:'post',
	            data: param,
	            traditional: true,
	            success:function(result){
	            	console.dir(result);
	            	dataView<c:out value="${param.uuid }" />.setItems([]);
	            	if(result != null  && result.rows != null){
	            		if($content.find("#reload").val() == "01"){
	            			data<c:out value="${param.uuid }" /> = result.rows;
	            		}else{
	            			data<c:out value="${param.uuid }" /> = data<c:out value="${param.uuid }" />.concat(result.rows);
	            		}
						dataView<c:out value="${param.uuid }" />.setItems(data<c:out value="${param.uuid }" />);
						grid<c:out value="${param.uuid }" />.setData(data<c:out value="${param.uuid }" />);
						grid<c:out value="${param.uuid }" />.render();
						if(result.rows.length <= 0){							
							grid<c:out value="${param.uuid }" />.invalidateAllRows();
							$content.find('.grid-canvas').html('<div class="alert-info-grid">No Record(s) Found</div>');
						}
						setPagerState(result.rows);
	            	}
	            	else
            		{
						grid<c:out value="${param.uuid }" />.invalidateAllRows();
						$content.find('.grid-canvas').html('<div class="alert-info-grid">No Record(s) Found</div>');
            		}
	            	
					loadingbarFadeOut();
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
	function timeCssFormatter(row, cell, value, columnDef, dataContext) {
		if(value == undefined){
			return "<span style='color:blue;font-weight:bold;'></span>"
		}else{
			return "<span style='color:blue;font-weight:bold;'>"+value+"</span>"
		}
	}
	
	function buttonFormatter(row, cell, value, columnDef, dataContext) {
		for(var i=0;i<unfoldIds<c:out value="${param.uuid }" />.length;i++){

			if(Number(row) === Number(unfoldIds<c:out value="${param.uuid }" />[i]) ){
				return "<input type='hidden' id='hidden"+row+"' value='minus'/><input type='hidden' id='"+dataContext.CARRIER+dataContext.TOTAL_ELAPSED+"' value='0'/><i style='margin-left:8px;' class='elapsed minus icon' id="+row+"></i>";
			}else if(dataContext.TOTAL_ELAPSED == null || dataContext.TOTAL_ELAPSED == ''){
				return "<input type='hidden'/>";
			}
		}
		return "<input type='hidden' id='hidden"+row+"' value='plus'/><input type='hidden' id='"+dataContext.CARRIER+dataContext.TOTAL_ELAPSED+"' value='0'/><i style='margin-left:8px;' class='elapsed plus icon' id="+row+"></i>";
	}
	var clickCount = 0;
	var beforeSecond = 0;
	// 테이블  생성
	function drawGrid<c:out value="${param.uuid }" />(){
		var columns = [
		  {id: "BUTTON", name: "", field: "", width: 25, minWidth: 25, cssClass: "cell-title", sortable: true, formatter:buttonFormatter},
		  {id: "TIME_EX", name: "TIME", field: "TIME_EX", width: 85, minWidth: 85, cssClass: "cell-title", sortable: true},
		  {id: "FROM", defaultSortAsc: false, name: "FROM", field: "FROM", width: 45, sortable: true},
		  {id: "TO", defaultSortAsc: false, name: "TO", field: "TO", width: 45, sortable: true},
		  {id: "CARRIER", defaultSortAsc: false, name: "CARRIER", field: "CARRIER", width: 45, sortable: true},
		  {id: "LOCATION_ID", defaultSortAsc: false, name: "LOCATION", field: "LOCATION_ID", width: 45, sortable: true},
		  {id: "TOTAL_ELAPSED", name: "TOTAL_ELAPSED", field: "TOTAL_ELAPSED", width:50, minWidth: 50,  sortable: true, formatter:timeCssFormatter},
		  {id: "ELAPSED", name: "ELAPSED", field: "ELAPSED", width:60, minWidth: 60, sortable: true, formatter:timeCssFormatter},
		  {id: "SOURCE_ID", name: "SOURCE_ID", field: "SOURCE_ID", width: 50, sortable: true},
		  {id: "SOURCE_TYPE", name: "SOURCE_TYPE", field: "SOURCE_TYPE", width: 30, sortable: true},
		  {id: "DESTINATION_ID", name: "DESTINATION_ID", field: "DESTINATION_ID", width: 50, sortable: true},
		  {id: "DESTINATION_TYPE", name: "DESTINATION_TYPE", field: "DESTINATION_TYPE", width: 30, sortable: true},
		  {id: "MES-MCS MESSAGE", name: "COMMAND", field: "COMMAND", width:145, minWidth: 145, sortable: true},
		  {id: "MCS-MCP MESSAGE", name: "MESSAGENAME", field: "MESSAGENAME", width: 105, minWidth: 105, sortable: true},
		  {id: "PROCESS", name: "PROCESS", field: "PROCESS", width: 25, minWidth: 25, sortable: true},
		  {id: "TRANSACTIONID", name: "TRANSACTIONID", field: "TRANSACTIONID", width:80, minWidth: 80, sortable: true},
		  {id: "COMMANDID", name: "COMMANDID", field: "COMMANDID", width: 100, minWidth: 80, sortable: true},
		];
		var options = {
			enableCellNavigation: true,   // 대량 데이터 속도 개선
   			forceFitColumns: false,        // 그리드 가로 스크롤 유무  
   			autoExpandColumns : true,  // 그리드 사이즈 변경시, 스크롤 생성 유무
   			topPanelHeight: 30,              // 헤더 높이 값
   			rowHeight: 21,
   			enableColumnReorder: true  // 
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
		grid<c:out value="${param.uuid }" />.onClick.subscribe(function(e, args) {

			var cellIdx = args.cell;
			var rowIdx = args.row;
			var rowHiddenId = '#hidden'+rowIdx;
			var row = data<c:out value="${param.uuid }" />[rowIdx];
			var field = grid<c:out value="${param.uuid }" />.getColumns()[cellIdx].field;
			var value = row[field];
			var ADDQUERY = row["ADDQUERY"];
			if(row["LOCATION_ID"] != null){
     			showLoadingbar($("#list<c:out value="${param.uuid }" />")); // 로딩바 보이는 부분
     //			console.log(" undefined ");
			}
			if($(rowHiddenId).val()==='plus'){
				
				$(rowHiddenId).val('minus');
				unfoldIds<c:out value="${param.uuid }" />.push(rowIdx);
				grid<c:out value="${param.uuid }" />.getDataItem(rowIdx)				
				getLogDetail<c:out value="${param.uuid }" />(ADDQUERY, rowIdx, cellIdx);
			}else if($(rowHiddenId).val()==='minus'){
				for(var i=0;i<unfoldIds<c:out value="${param.uuid }" />.length;i++){
					if(Number(unfoldIds<c:out value="${param.uuid }" />[i]) === Number(rowIdx)){
						unfoldIds<c:out value="${param.uuid }" />.splice(i, 1);
					}
				}
				$(rowHiddenId).val('plus');
				var hiddenChildId = '#hiddenChild'+rowIdx;
				var parent = grid<c:out value="${param.uuid }" />.getDataItem(rowIdx);
   				var parentId = "#"+parent.CARRIER + parent.TOTAL_ELAPSED;
				var totalChildCount = unfoldIdsChild<c:out value="${param.uuid }" />[parentId];
				data<c:out value="${param.uuid }" />.splice((rowIdx+1), Number(totalChildCount));
				var rowCnt =  $content.find("#rowCount").text();
				rowCnt = Number(rowCnt) - Number(totalChildCount);
				$content.find("#rowCount").text(rowCnt);
				for(var i=0;i<unfoldIds<c:out value="${param.uuid }" />.length;i++){
					if(Number(unfoldIds<c:out value="${param.uuid }" />[i]) > Number(rowIdx)){
						unfoldIds<c:out value="${param.uuid }" />[i] = unfoldIds<c:out value="${param.uuid }" />[i] - Number(totalChildCount);
					}
				}
				grid<c:out value="${param.uuid }" />.setData(data<c:out value="${param.uuid }" />);
				grid<c:out value="${param.uuid }" />.render();
				loadingbarFadeOut();
			}
		});
		grid<c:out value="${param.uuid }" />.onDblClick.subscribe(function(e, args) {
			var cell = args.cell;
		    var rowIdx = args.row;
		    var row = grid<c:out value="${param.uuid }" />.getDataItem(rowIdx);
		    $content.find("input[name=carrier]").val(row.CARRIER);
		});
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