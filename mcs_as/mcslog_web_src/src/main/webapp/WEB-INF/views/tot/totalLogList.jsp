<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ include file="/WEB-INF/views/common-taglib.jspf"%>


<!-- sideNav style 시작,,, -->
<style>
.sidenav1 {
    height: 100%;
    width: 0;
    position: absolute;
    z-index: 10000;
    top: 0;
    right: 0;
    background-color: #fff;
    overflow-x: hidden;
    transition: 0.5s;
    padding-top: 40px;
    margin-top: 30px;
}

.sidenav1 a {
    padding: 8px 8px 8px 18px;
    text-decoration: none;
    font-size: 25px;
    color: #818181;
    display: block;
    transition: 0.3s;
}

.sidenav1 a:hover {
    color: #f1f1f1;
}

.sidenav1 .closebtn {
    position: absolute;
    top: 0;
    right: 490px;
    font-size: 36px;
    margin-left: 10px; 
}

.sidenav1 pre{
	resize:none;
	padding: 5px;
	width: 100%; 
	height : 400px;
	font-size: 9pt; 
	font-weight:bold;
/* 	font-weight: bold; */
	/* margin: 5px; */
}
@media screen and (max-height: 450px) {
  .sidenav1 {padding-top: 15px;}
  .sidenav1 a {font-size: 18px;}
}
/* 201106 hgJeon object.css 로 이동위해 주석처리 */
/* #cancelBtn{margin-top:0px;margin-left:12px;padding-top:4px;width:315px;height:33px;font-size:25px} */
</style>
<!-- sideNav style 끝,,, -->



<div class="contents_wrap" id="body_<c:out value="${param.uuid }" />">
	<!-- <script>alert('ABC') </script> XSS 취약점 test code -->
                <!-- Location Information -->
                <div class="loc_info_basic">
                    <span class="location_box">
                        <a href="#" class="location"><span class="loc_info_ico loc_info_ico_home"></span>Home</a>
                    </span>
                    <span class="loc_info_ico loc_info_ico_arr_depth"></span>
                    <span class="location_box">
                        <a href="#" class="location"><spring:message code="site.totalLogList" text="default text" /></a>
                    </span>
                    <span class="loc_info_ico loc_info_ico_arr_depth"></span>
                    <span class="location_box">
                        <a href="#" class="location"><spring:message code="site.totalLogList" text="default text" /></a>
                    </span>
                </div>
                <!-- //Location Information -->
                <!-- Page Title -->
                <table class="page_tit">
                    <tr>
                        <td class="tit_area">
                            <div class="tit"><spring:message code="site.totalLogList" text="default text" /></div>
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
                                                        <div id="resetBtn" class="mini ui primary button" style="width:75px;float: right;margin-right: 10px;float:right;white-space:nowrap;">
															<i class="erase icon" ></i>reset
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
                                                    <!-- 180615 fab 선택box -->
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
																			<!-- 2021. 04. 02. X0122410 : Fabs 리스트 이용 -->																		
								                                    	 	<%-- <input type="checkbox" class="jqForm" id="fab2" name="fab2" <c:if test="${param.fab2 == 'FAB_A' }" >checked="checked"</c:if> checked value="FAB_A" ><label for="fab2">M14A</label><BR> --%>
							                                         		<%-- <input type="checkbox" class="jqForm" id="fab3" name="fab3" <c:if test="${param.fab3 == 'FAB_B' }" >checked="checked"</c:if> checked value="FAB_B" ><label for="fab3">M14B</label><BR> --%>
								                                         	<!-- 200827 hgJeon M16 fab 선택 추가 -->
								                                         	<%-- <input type="checkbox" class="jqForm" id="fab4" name="fab4" <c:if test="${param.fab4 == 'FAB_C' }" >checked="checked"</c:if> value="FAB_C" ><label for="fab4">M16</label><BR> --%>
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
                   								<!-- 180615 fab 선택box -->
                                                    <div class="srch_type01">
                									<div class="condition_area">
                                                        <table class="condition_table" summary="검색조건 테이블">
							                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
							                            <tbody id="test">
							                                <tr>
							                                    <td class="condition_t_head_top" colspan="3">
							                                    	<i class="add square icon"></i>
							                                    	<span>Machine</span>
							                                    </td>
							                                </tr>
							                                <tr>
							                                    <td class="condition_t_data" colspan="3">
							                                    	<input type="checkbox" class="jqForm" id="singleFilter" name="singleFilter" value="01" checked ><label for="singleFilter">Single Filter</label>
							                                    </td>
							                                </tr>
							                                <tr class="singleFilter">
							                                    <th scope="col" class="condition_t_head">AREA</th>
							                                    <td class="condition_t_data" colspan="2">
							                                        <select class="areaName_machine" id="areaName" name="areaName" style="width: 143px" >
							                                            <option value="ALL" <c:if test="${param.areaName == 'ALL' }" >selected="selected"</c:if>>ALL</option>							                                            
							                                            <%-- <option value="CLEAN" <c:if test="${param.fromAreaName == 'CLEAN' }" >selected="selected"</c:if>>CLEAN</option>
							                                            <option value="CMP" <c:if test="${param.fromAreaName == 'CMP' }" >selected="selected"</c:if>>CMP</option>
							                                            <option value="CU" <c:if test="${param.fromAreaName == 'CU' }" >selected="selected"</c:if>>CU</option>
							                                            <option value="DIFF" <c:if test="${param.fromAreaName == 'DIFF' }" >selected="selected"</c:if>>DIFF</option>
							                                            <option value="ETCH" <c:if test="${param.fromAreaName == 'ETCH' }" >selected="selected"</c:if>>ETCH</option>
							                                            <option value="F/C" <c:if test="${param.fromAreaName == 'F/C' }" >selected="selected"</c:if>>F/C</option>
							                                            <option value="FIO" <c:if test="${param.fromAreaName == 'FIO' }" >selected="selected"</c:if>>FIO</option>
							                                            <option value="IMP" <c:if test="${param.fromAreaName == 'IMP' }" >selected="selected"</c:if>>IMP</option>
							                                            <option value="INV" <c:if test="${param.fromAreaName == 'INV' }" >selected="selected"</c:if>>INV</option>
							                                            <option value="LIFTER" <c:if test="${param.fromAreaName == 'LIFTER' }" >selected="selected"</c:if>>LIFTER</option>
							                                            <option value="PHOTO" <c:if test="${param.fromAreaName == 'PHOTO' }" >selected="selected"</c:if>>PHOTO</option>
							                                            <option value="T/F" <c:if test="${param.fromAreaName == 'T/F' }" >selected="selected"</c:if>>T/F</option>
							                                            <option value="반송" <c:if test="${param.fromAreaName == '반송' }" >selected="selected"</c:if>>반송</option> --%>
							                                        </select>
							                                    </td>
							                                </tr>
							                                <tr class="singleFilter">
							                                    <th scope="col" class="condition_t_head">BAY</th>
							                                    <td class="condition_t_data" colspan="2" >
							                                         <select class="bayName" id="bayName" name="bayName" style="width: 143px" >
							                                            <option value="ALL" selected="selected">ALL</option>
							                                        </select>
							                                    </td>
							                                </tr>
							                                <tr  id="singleFilterChkBoxFab" class="singleFilter" >
							                                    <th scope="col" class="condition_t_head">Type</th>
							                                    <!-- 2021.03.22	X0122410	:	machinetype 리스트를 서버에서 가져와서 보여준다 -->
							                                    <%-- <td class="condition_t_data" >
							                                         <input type="checkbox" class="jqForm" id="machineType1" name="machineType1" value="ALL" checked ><label for="machineType1">ALL</label><BR>
							                                         <input type="checkbox" class="jqForm" id="machineType2" name="machineType2" value="STOCKER" <c:if test="${param.machineType2 == 'STOCKER' }" >checked="checked"</c:if>><label for="machineType2">STOCKER</label><BR>
							                                         <input type="checkbox" class="jqForm" id="machineType3" name="machineType3" value="STB" <c:if test="${param.machineType3 == 'STB' }" >checked="checked"</c:if>><label for="machineType3">STB</label><BR>
							                                         <input type="checkbox" class="jqForm" id="machineType4" name="machineType4" value="LIFTER" <c:if test="${param.machineType4 == 'LIFTER' }" >checked="checked"</c:if>><label for="machineType4">LIFTER</label><BR>
							                                    </td>
							                                    <td class="condition_t_data" id="singleFilterChkBox" >
							                                         <input type="checkbox" class="jqForm" id="machineType5" name="machineType5" value="CONVEYOR" <c:if test="${param.machineType5 == 'CONVEYOR' }" >checked="checked"</c:if>><label for="machineType5">CONVEYOR</label><BR>
							                                         <input type="checkbox" class="jqForm" id="machineType6" name="machineType6" value="PROCESS" <c:if test="${param.machineType6 == 'PROCESS' }" >checked="checked"</c:if>><label for="machineType6">PROCESS</label><BR>
							                                         <input type="checkbox" class="jqForm" id="machineType7" name="machineType7" value="OHT" <c:if test="${param.machineType7 == 'OHT' }" >checked="checked"</c:if>><label for="machineType7">OHT</label><BR>							                                         
							                                    </td> --%>
							                                    <%-- <td class="condition_t_data" >
						                                         	<input type="checkbox" class="jqForm" id="machineType1" name="machineType1" value="ALL" checked ><label for="machineType1">ALL</label><BR>
						                                         	<c:forEach  items="${machineTypeInfoList}" var="row" varStatus="status"  >
																	 	<c:if test="${status.index%2 eq 1}">
																	 		<c:set var="num" value="${status.index + 2}"/>
																	 		<c:set var="isVal" value="F" />
																			<c:forEach var="item" items="${machineTypes}">																			
																			  <c:if test="${item eq row.TYPE}">																			  	
																			    <c:set var="isVal" value="T" />
																			  </c:if>																			  
																			</c:forEach>																											
																			<input type="checkbox" class="jqForm" id="machineType<c:out value="${num}"/>" name="machineType<c:out value="${num}"/>" value="<c:out value="${row.TYPE}"/>" <c:if test="${isVal eq 'T'}">checked="checked"</c:if>><label for="machineType<c:out value="${num}"/>"><c:out value="${row.TYPE}"/></label><BR>																			
																		</c:if>				                                            	
				                                            		</c:forEach>
							                                    </td>
							                                    <td class="condition_t_data" id="singleFilterChkBox" >
							                                       	<c:forEach  items="${machineTypeInfoList}" var="row" varStatus="status"  >
																	 	<c:if test="${status.index%2 eq 0}">
																	 		<c:set var="num" value="${status.index + 2}"/>
																	 		<c:set var="isVal" value="F" />
																			<c:forEach var="item" items="${machineTypes}">																			
																			  <c:if test="${item eq row.TYPE}">																			  	
																			    <c:set var="isVal" value="T" />
																			  </c:if>																			  
																			</c:forEach>																											
																			<input type="checkbox" class="jqForm" id="machineType<c:out value="${num}"/>" name="machineType<c:out value="${num}"/>" value="<c:out value="${row.TYPE}"/>" <c:if test="${isVal eq 'T'}">checked="checked"</c:if>><label for="machineType<c:out value="${num}"/>"><c:out value="${row.TYPE}"/></label><BR>																			
																		</c:if>				                                            	
				                                            		</c:forEach>					                                         
							                                    </td> --%>
							                                </tr>
							                                <tr class="singleFilter">
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
							                                <tr class="multiFilter">
							                                 	<td class="condition_t_data" colspan="3">
							                                    	 <input type="text" id="machineName2" name="machineName2"  style="width:163px" value="" disabled />
					                                                    <div id="machineBtn" class="mini ui primary button" style="width:93px;float: right;margin-left: 4px;white-space:nowrap;">
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
							                                    <td class="condition_t_head_top" colspan="3">
							                                    	<i class="add square icon"></i>
							                                    	<span>Level</span>
							                                    </td>
							                                </tr>
							                                <tr>
							                                	<th scope="col" class="condition_t_head">Type</th>
							                                	<%-- <td class="condition_t_data">
							                                         <input type="checkbox" class="jqForm" id="level1" name="level1" <c:if test="${param.level1 == 'ALL' }" >checked="checked"</c:if> value="ALL"  ><label for="level1">ALL</label><BR>
							                                         <input type="checkbox" class="jqForm" id="level2" name="level2" <c:if test="${param.level2 == 'DEBUG' }" >checked="checked"</c:if> value="DEBUG" ><label for="level2">DEBUG</label><BR>
							                                         <input type="checkbox" class="jqForm" id="level3" name="level3" <c:if test="${param.level3 == 'INFO' }" >checked="checked"</c:if> value="INFO" ><label for="level3">INFO</label><BR>
							                                         <input type="checkbox" class="jqForm" id="level4" name="level4" <c:if test="${param.level4 == 'FINE' }" >checked="checked"</c:if> value="FINE" ><label for="level4">FINE</label><BR>
							                                    </td>
							                                    <td class="condition_t_data">
							                                         <input type="checkbox" class="jqForm" id="level5" name="level5"  checked value="WELL" ><label for="level5">WELL</label><BR>
							                                         <input type="checkbox" class="jqForm" id="level6" name="level6"  checked value="WARN" ><label for="level6">WARN</label><BR>
							                                         <input type="checkbox" class="jqForm" id="level7" name="level7"  checked value="ERROR" ><label for="level7">ERROR</label><BR>
							                                         <input type="checkbox" class="jqForm" id="level8" name="level8"  checked value="FATAL" ><label for="level8">FATAL</label><BR>
							                                    </td> --%>
							                                    <td class="condition_t_data">
							                                         <input type="checkbox" class="jqForm" id="level1" name="level1" <c:if test="${params.level.contains('ALL')}" >checked="checked"</c:if> value="ALL"  ><label for="level1">ALL</label><BR>
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
							                                	<th scope="col" class="condition_t_head" style="width:300px">condition</th>
							                                    <td class="condition_t_data">
							                                         <input type="radio" class="jqForm" id="searchOption1" name="searchOption" value="AND" ><label for="srch_radio00">AND</label>
							                                         <input type="radio" class="jqForm" id="searchOption2" name="searchOption" value="OR" checked ><label for="srch_radio00">OR</label>
							                                    </td>
							                                </tr>
							                                <tr>
							                                	<th scope="col" class="condition_t_head">Process Name</th>
							                                    <td class="condition_t_data">
							                                        <input type="text" id="process" name="process" value="<c:out value="${param.process }" />" />
							                                    </td>
							                                </tr>
							                                <tr>
							                                	<th scope="col" class="condition_t_head">Thread Name</th>
							                                    <td class="condition_t_data">
							                                         <input type="text" id="thread" name="thread" value="<c:out value="${param.thread }" />" />
							                                    </td>
							                                </tr>
							                                <tr>
							                                	<th scope="col" class="condition_t_head">GlobalTXN ID</th>
							                                    <td class="condition_t_data">
							                                         <input type="text" id="gtxnId" name="gtxnId" value="<c:out value="${param.gtxnId }" />" />
							                                    </td>
							                                </tr>
							                                <tr>
							                                	<th scope="col" class="condition_t_head">Transaction ID</th>
							                                    <td class="condition_t_data">
							                                         <input type="text" id="transactionId" name="transactionId" value="<c:out value="${param.transactionId }" />" />
							                                    </td>
							                                </tr>
							                                <tr>
							                                	<th scope="col" class="condition_t_head">Com Msg Name</th>
							                                    <td class="condition_t_data">
							                                         <select class="comMsgName" id="comMsgName1" name="comMsgName1" style="width:158px;margin-bottom: 2px">
							                                         	<option value='ALL' selected='selected' >ALL</option>
							                                        </select>
							                                        <input type="text" id="comMsgName" name="comMsgName" value="" />
							                                    </td>
							                                </tr>
							                                <tr>
							                                	<th scope="col" class="condition_t_head">Operation Name</th>
							                                    <td class="condition_t_data">
							                                         <select class="operationName" id="operationName1" name="operationName1" style="width:158px;margin-bottom: 2px">
							                                            <option value='ALL' selected='selected' >ALL</option>
							                                        </select>
							                                        <input type="text" id="operationName" name="operationName" value="" />
							                                    </td>
							                                </tr>
							                                <tr>
							                                	<th scope="col" class="condition_t_head">Bpel Name</th>
							                                    <td class="condition_t_data">
							                                         <select class="messageName" id="messageName1" name="messageName1" style="width:158px;margin-bottom: 2px">
							                                            <option value='ALL' selected='selected' >ALL</option>
							                                        </select>
							                                        <input type="text" id="messageName" name="messageName" value="" />
							                                    </td>
							                                </tr>
							                                <tr>
							                                	<th scope="col" class="condition_t_head">Carrier Name</th>
							                                    <td class="condition_t_data">
							                                         <input type="text" id="carrier" name="carrier" title="Multi Condition Search &#10;ex) Carrier1, Carrier2, Carrier3" value="<c:out value="${param.carrier }" />" />
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
							                                <tr>
							                                	<th scope="col" class="condition_t_head">Text</th>
							                                    <td class="condition_t_data">
							                                         <input type="text" id="text" name="text" title=". -_ =&#34; Only special characters are allowed &#10;ex) RESULT_CODE=&#34;0&#34; &#10;ex) text1, text2, text3 " value="<c:out value="${param.text }" />" />
							                                    </td>
							                                </tr>
							                            </tbody>
							                        </table>
							                        </div>
                   								</div>
                   								<!-- 180622 fulltext 검색 -->
	                   								<div class="srch_type01">
	                									<div class="condition_area">
	                                                        <table class="condition_table" summary="검색조건 테이블">
								                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
								                            <tbody>
								                                <tr>
								                                    <td class="condition_t_head_top" colspan="3">
								                                    	<i class="minus square icon"></i>
								                                    	<span>FullText</span>
								                                    </td>
								                                </tr>
								                                <tr>
							                                	<th scope="col" class="condition_t_head" style="width:128px">FullText</th>
								                                    <td class="condition_t_data">
								                                         <input type="text" id="fulltext" name="fulltext" title="Search all special characters &#10;ex) A,23 [COMMANDID] 'M4PDN797520200331133309' &#10;ex) CDATA[RECV S6F11:CarrierInstallRemoveEventReportSend " value="<c:out value="${param.text }" />" />
								                                    </td>
							                                	</tr>
								                            </tbody>
								                        </table>
								                        </div>
	                   								</div>
                   								<!-- 180622 fulltext 검색 -->
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
							                                    	<input type="radio" class="jqForm" id="time4<c:out value="${param.uuid }" />" name="time" value="04" <c:if test="${param.time == '04' }" >checked="checked"</c:if> ><label for="time4<c:out value="${param.uuid }" />">Last 1 Minutes</label>
							                                    	
					                                                <div id="pasteBtn" class="mini ui primary button" style="width:65px;float: right;margin-left: 4px;padding-left: 10px;" title="paste">
																	  <i class="paste icon"></i>Paste
																	</div>
					                                                <div id="copyBtn" class="mini ui primary button" style="width:65px;float: right;margin-left: 4px;padding-left: 10px;" title="copy">
																	  <i class="copy icon"></i>Copy
																	</div>
							                                    	<br>
							                                    	<input type="radio" class="jqForm" id="time1<c:out value="${param.uuid }" />" name="time" value="01" <c:if test="${param.time == '01' }" >checked="checked"</c:if> ><label for="time1<c:out value="${param.uuid }" />">Last 10 Minutes</label><br>
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
							                                          &nbsp;<input id="fromHour" name="fromHour" class="onlynum" value="<c:out value="${param.fromHour }" />"  style="width:30px" maxlength="2" />:<input type="" id="fromMin" name="fromMin" class="onlynum" value="<c:out value="${param.fromMin }" />" style="width:30px" maxlength="2" />:<input type="" id="fromSec" name="fromSec" class="onlynum" value="<c:out value="${param.fromSec }" />" style="width:30px" maxlength="2" /><br>
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
                   								<!-- 200602 TimeOut Option 추가 -->
                   								<div class="srch_type01">
                									<div class="condition_area">
                                                        <table class="condition_table" summary="검색조건 테이블">
							                            <caption><spring:message code="site.common.filter" text="default text" /></caption>
							                            <tbody>
							                                <tr>
							                                    <td class="condition_t_head_top" colspan="3">
							                                    	<i class="add square icon"></i>
							                                    	<span>Inquiry Option</span>
							                                    </td>
							                                </tr>
							                                <tr>
						                                	<th scope="col" class="condition_t_head" style="width:128px">Timeout (sec)</th>
							                                    <td class="condition_t_data">
							                                         <input id="searchDelay" name="searchDelay" class="onlynum" value="15" title=" Search Response Time (sec) "  maxlength="2" />
							                                    </td>
						                                	</tr>
							                            </tbody>
							                        </table>
							                        </div>
                   								</div>
                   								<!-- 200602 TimeOut Option 추가 -->
                                            </div>
                                            <div>
                                            	<div style="padding: 10px 2px;">
			                                    	<div  class="ui primary button" id="searchBtn" >
			                                    		<i class="search icon"></i>Search
			                                    	</div>			
			                                    </div>
			                                    <div style="padding: 10px 2px; display:none;">
			                                    	<div  class="ui primary button" id="cancelBtn" >
			                                    		<i class="stop icon"></i>Cancel
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
                                    			<!-- <i id="foldTableBtn1" class="minus square icon large" style="color:#ccd2de"></i> -->
                                                <span class="txt">LIST
                                                </span>
                                            </div>
                                            <!-- <div id="testBtn" class="mini ui primary button" style="width:77px;float: right;margin-left: 4px;white-space:nowrap;">
												<i class="cocktail icon"></i>TEST
											</div> -->
                                        </div>
                                        <div class="opt_tit_right">
	                                        <div class="elmt">
	                                        	<a id="sideNav_view" class="btn_fix btn_arr_left " style="float:right; margin-left: 10px;" onclick="openNav()"></a>
	                                            <div id="downloadLink" class="mini ui primary button" style="width:85px;float: right;margin-left: 4px;white-space:nowrap;">
													<i class="file excel outline icon"></i>Excel
												</div>
	                                            <div id="filterBtn" class="mini ui primary button" style="width:77px;float: right;margin-left: 4px;white-space:nowrap;">
													<i class="cocktail icon"></i>Filter
												</div>
	                                        </div>
                                    	</div>
                                    </div>
                                    <!-- //Option Title -->
                                    <div id="grid_container<c:out value="${param.uuid }" />">
                                    	<div id="list<c:out value="${param.uuid }" />" class="gridForResize" style="width:100%;height:570px; background: white; outline: 0; border: 1px solid gray;"></div>
                            			<c:import url="/WEB-INF/views/common/slickGridPager.jsp" charEncoding="utf-8" />
								    </div>
		                         <div class="" style="height:100%;padding:12px 0px">
		                         <div class="opt_tit">
	                                 <div class="opt_tit_left" id="logInfo" style="display: none;" >
	                                     <div class="elmt">
	                                         <!-- <i id="foldTableBtn2" class="minus square icon large" style="color:#ccd2de"></i> -->
	                                         <span class="txt elmtTit">Message : </span><span id="titMessageName" class="elmtDesc" ></span>
	                                         <span class="txt elmtTit">Operation : </span><span id="titOperationName" class="elmtDesc" ></span>
	                                         <span class="txt elmtTit">carrier : </span><span id="titCarrier" class="elmtDesc" ></span>
	                                         <span class="txt elmtTit">CommandID : </span><span id="titTransportCommandId" class="elmtDesc" ></span>
	                                         <span class="txt elmtTit">Machine : </span><span id="titMachineName" class="elmtDesc" ></span>
	                                     </div>
	                                 </div>
	                             </div>
                               <div id="gridDetailArea" class="tbl_hori">
                                    <table class="tbl_hori_inside" summary="해당 표에 대한 설명을 적어주세요.">
                                        <caption><spring:message code="site.common.summary.desc01" text="Write a description." /></caption>
                                        <colgroup>
                                            <col width="120"/>
                                            <col width="120"/>
                                        </colgroup>
                                        <tbody>
                                            <tr class="hori_t_row">
                                                <td class=""><textarea class="grid_detail" id="XML" readOnly style=" width: 100%;-webkit-box-sizing: border-box; /* Safari/Chrome, other WebKit */ -moz-box-sizing: border-box;    /* Firefox, other Gecko */  box-sizing: border-box;         /* Opera/IE 8+ */" ></textarea></td>
                                                <td class=""><textarea class="grid_detail" id="SECSII" readOnly style=" width: 100%;-webkit-box-sizing: border-box; /* Safari/Chrome, other WebKit */ -moz-box-sizing: border-box;    /* Firefox, other Gecko */  box-sizing: border-box;         /* Opera/IE 8+ */" ></textarea></td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>       	      
	                         </div>
                         </div>
                         <div id="sideDetail_view" class="lay_item_right" style="width:2px">
							<div id="mySidenav01" class="sidenav1">
								<div>
									<a href="javascript:void(0)" class="closebtn" onclick="closeNav()">
								<i class="minus circle icon small" style="color:#ccd2de"></i>
									</a>
								</div>
							
								<div style="border: 1px solid #111;">
									<pre class="prettyprint" id="myTotDetail" style="white-space: pre-wrap; "></pre>	
								</div>
							</div>		
						 </div>
                	</div>
                </form>
            </div>
        </div>

<script type="text/javascript">
 		
 	/**
 	* sidenav 관련 스크립트
 	*/ 	

 	function openSideView() {
 		var tabId = curUuid;
 		tabId < 100 ? openNav() : openNavSecs();
 	}
 	
 	function closeSideView() {
 		var tabId = curUuid;
 		tabId < 100 ? closeNav() : closeNavSecs();
 	}
 	
 	function openNav() {
 		document.getElementById("mySidenav01").style.width = "550px";
    	$content.find("#gridDetailArea").hide();
    	$(".gridForResize").css("height",$(window).height()-200+"px");
		document.getElementById("sideDetail_view").style.width = "550px";
		$(".sidenav1 pre").css("height",$(window).height()-150+"px");
		grid<c:out value="${param.uuid }" />.resizeCanvas();
		console.log("윈도우:"+$(window).height());
	}
	
	function closeNav() {
	    document.getElementById("mySidenav01").style.width = "0";
	    $content.find("#gridDetailArea").show();
		document.getElementById("sideDetail_view").style.width = "2px";
		$(".gridForResize").css("height",$(window).height()-420+"px");
		grid<c:out value="${param.uuid }" />.resizeCanvas();
		console.log("윈도우:"+$(window).height());
		console.log("detail:"+$(".grid_detail").height());
	}
 	
	/********************
	*  url get function START
	********************/
	
	var _global_count_value = 0; //global value
	var _url_get_function = function(_url_string_){
		if(_url_string_ == undefined || _url_string_ == "") return;
		if(_url_string_.indexOf("#") != -1 && _url_string_.substring(_url_string_.length - 1) == "#") return;
		if(_global_count_value <= 0 ){
			_url_string_ = decodeURI(_url_string_);
			
			console.log("_url_get_function_start");
			console.log("URL : " + _url_string_);
			
			var _urlStringTMP = _url_string_.split("/");
			var query = _urlStringTMP[4].split("&");
			
			if(query.length == 0) return;
			_urlStringTMP = query[0].split("?");			
			if(_urlStringTMP.length == 2)	//main? 포함시 제거
			{
				query[0] = _urlStringTMP[1];	
			}
			
			if(query[0].split("=").length < 2) return;
			
			var _isFab = false;
			
			try 
			{
				showLoadingbar($("#list<c:out value="${param.uuid }" />")); // 로딩바 활성
				for(var _key in query) {
					var paramKey = query[_key].split("=")[0];
					var paramValue = query[_key].substring(query[_key].indexOf("=") + 1);
					
					switch (paramKey) {
						case "fab":
							_isFab = true;
							var _temp_fabInfo = query[_key].split("=")[1];
							console.log(_temp_fabInfo);
							if(_temp_fabInfo == "m15" || _temp_fabInfo == "m15a"  || _temp_fabInfo == "m15b") {
								if(_temp_fabInfo == "m15") _temp_fabInfo = "m15a";
								
								//fabSite
								$content.find(":radio[name=rdoFabSite]:eq(1)").prop("checked",true);
							}
							else if(_temp_fabInfo == "m11" || _temp_fabInfo == "m11a"  || _temp_fabInfo == "m11b") {
								if(_temp_fabInfo == "m11") _temp_fabInfo = "m11a";
								
								//fabSite
								$content.find(":radio[name=rdoFabSite]:eq(2)").prop("checked",true);
							}
							else if(_temp_fabInfo == "c2" || _temp_fabInfo == "c2f") {
								
								//fabSite
								$content.find(":radio[name=rdoFabSite]:eq(3)").prop("checked",true);
							}
							else {
								//_temp_fabInfo == "m14" || _temp_fabInfo == "m14a"  || _temp_fabInfo == "m14b" || _temp_fabInfo == "m16" || _temp_fabInfo == "m16a" || _temp_fabInfo == "m16b"						
								if(_temp_fabInfo == "m14") _temp_fabInfo = "m14a";
								if(_temp_fabInfo == "m16") _temp_fabInfo = "m16a";
								
								//fabSite
								$content.find(":radio[name=rdoFabSite]:eq(0)").prop("checked",true);
							}
							
							var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
							getFabFromFabSite("tot", _fabSite, "fab", "tdFab");
							
							//fab
							$content.find(":checkbox[name^=fab]").each(function(){
								this.checked = false;
							});
							$content.find(":checkbox[name^=fab][value=" + _temp_fabInfo.toUpperCase() + "]").prop("checked",true);
							
							getMachineTypeFromFab(_fabSite,"fab", "machineType", "singleFilterChkBoxFab");				
							getAreaFromFab(_fabSite,"fab", "areaName");
							getBayFromArea(_fabSite,"fab", "areaName", "bayName");
							getMachineNameList(_fabSite,"fab", "areaName","bayName","machineType","machineName1");
						break;
						case "machine":
							var _local_machineName = paramValue;
							$content.find("input[name=machineName2]").val(_local_machineName);
							$content.find("#filter").val("02");
							setFilter(); // single / multi 폼 활성 / 비활성 
						break;
						case "condition":
							var _local_condition = paramValue;
							if (_local_condition == "and") {
								$content.find("#searchOption1").prop("checked", true);	
							} else {
								$content.find("#searchOption2").prop("checked", true);
							}
						break;
						case "process":
							var _local_process = paramValue;
							$content.find("#process").val(_local_process);
						break;
						case "thread":
							var _local_thread = paramValue;
							$content.find("#thread").val(_local_thread);
						break;
						case "gtxnid":
							var _local_gtxnId = paramValue;
							$content.find("#gtxnId").val(_local_gtxnId);
						break;
						case "transaction":
							var _local_transaction = paramValue;
							$content.find("#transactionId").val(_local_transaction);
						break;
						case "commsg":
							var _local_comMsgName = paramValue;
							$content.find("#comMsgName").val(_local_comMsgName);
						break;
						case "operation":
							var _local_operationName = paramValue;
							$content.find("#operationName").val(_local_operationName);
						break;
						case "bpel":
							var _local_messageName = paramValue;
							$content.find("#messageName").val(_local_messageName);
						break;
						case "carrierid":
							var _local_carrierID = paramValue;
							$content.find("#carrier").val(_local_carrierID);
						break;
						case "commandid":
							var _local_commandId = paramValue;
							$content.find("#commandId").val(_local_commandId);
						break;
						case "unit":
							var _local_unit = paramValue;
							$content.find("#unit").val(_local_unit);
						break;
						case "text":
							var _local_text = query[_key].split("=");
							var _temp_textVal = "";
							for(var _text_val in _local_text){
								if( _text_val != 0 ){
									_temp_textVal += _local_text[_text_val] + "=";
								}
							}
							_temp_textVal = _temp_textVal.slice(0, -1);
							_temp_textVal = _temp_textVal.replace(/%22/gi,"\"" );
							_temp_textVal = _temp_textVal.replace(/%20/gi," " );
							
							$content.find("input[name=text]").val(_temp_textVal);
						break;
					}
					
					if (query[_key].substring(0,2) == "fr") {
						console.log("key fr : ", query[_key]);
						var _temp_fromDt = query[_key].split("=")[1].substring(0,8);
						var _temp_fromTime=query[_key].split("=")[1].substring(8);
						var _fromDt = _temp_fromDt.substring(0,4) + ".";
							 _fromDt += _temp_fromDt.substring(4,6) +".";
							 _fromDt += _temp_fromDt.substring(6,8);

						$content.find("input[name=fromDt]").val(_fromDt);
						$content.find("input[name=fromHour]").val(_temp_fromTime.substring(0,2));
						$content.find("input[name=fromMin]").val(_temp_fromTime.substring(2,4));
						$content.find("input[name=fromSec]").val(_temp_fromTime.substring(4,6));
					} else if(query[_key].substring(0,2) == "to" && query[_key] != "tot") {	// 200702 hgJeon tot 인 경우 제외
						
						var _temp_toDt = query[_key].split("=")[1].substring(0,8);
						var _temp_toTime = query[_key].split("=")[1].substring(8);
						var _toDt = _temp_toDt.substring(0,4) + ".";
						     _toDt += _temp_toDt.substring(4,6) +".";
						     _toDt += _temp_toDt.substring(6,8);
						     
					    $content.find("input[name=toDt]").val(_toDt);
						$content.find("input[name=toHour]").val(_temp_toTime.substring(0,2));
						$content.find("input[name=toMin]").val(_temp_toTime.substring(2,4));
						$content.find("input[name=toSec]").val(_temp_toTime.substring(4,6));
						
						$content.find("input[name=time]").val();
					}
				}
			} catch (exceptionVar) {
				
			} finally {
				loadingbarFadeOut(); // 로딩바 숨김
			}
			
			$content.find("#searchBtn").trigger("click"); // FAB 명이 있을때 조회 버튼 클릭
			location.href = location.href + "#";
		}
		_global_count_value++;
		console.log("_url_get_function_end");	
	};
	/********************
	*  url get function END
	********************/
	
	$(document).ready(function(){
		prettyPrint();
		
		$(document).keypress(function(e){
			if(e.which == 78 || e.which == 110){  // n 키 입력 이벤트
				var tabId = curUuid;
				console.log(tabId);
				$(window).bind('hashchange', function() {
					console.log("바뀜");
				});
				if(e.target.type == "text"){
 					return;
 				}else{
					
					if($("#mySidenav01").width() >= 50){
						$("#myTotDetail").html("");
						$("#myTotDetail").removeClass('prettyprinted');
 						prettyPrint();
 						closeNav();
 					}else{
 						var textVal = $("#XML").val();
 						/* if(textVal.length > 5000){
 							textVal = "Rendering Exception, Too Many String,";
 						} */
	 					    textVal = textVal.replace(/&/gi, " &amp; ");
	 						textVal = textVal.replace(/</gi, " &lt;");
	 						textVal = textVal.replace(/>/gi, "&gt; ");
 						
							$("#myTotDetail").html(textVal);
		    				$("#myTotDetail").removeClass('prettyprinted');	
		    				openNav();
 						prettyPrint();
 						
 					}
 				}
				
 			}
		});
		
		
	});
	/*	  sidenav 영역 끝........	*/

	$content = $("#body_${param.uuid }");
 	$(document).ready(function(){
 		
	 		// 200507 hgJeon Fab 기준정보에 따른 Naming 변경
	 		// 2021. 04. 02 X0122410 Fabs 가져오는 로직으로 변경, 사용안함
	 		/* switch(FabCode) 
	 		{
		 		case 'M14' :
		 			{console.log('FAB 확인 : ' , FabCode);}
		 			$("label[for = 'fab2' ]").text('M14A')
		 			$("label[for = 'fab3' ]").text('M14B')
		 			$("label[for = 'fab4' ]").text('M16')
		 			$("#fab4").hide();
	 				$("label[for = 'fab4' ]").hide();
		 			break;
		 		case 'M15' :
					{console.log('FAB 확인 : ' , FabCode);}
					$("label[for = 'fab2' ]").text('M15A')
		 			//$("label[for = 'fab3' ]").text('M15B')
		 			$("#fab3").hide();
		 			$("label[for = 'fab3' ]").hide();
		 			$("#fab4").hide();
		 			$("label[for = 'fab4' ]").hide();
					break;
		 		case 'M11' :
					{console.log('FAB 확인 : ' , FabCode);}
					$("label[for = 'fab2' ]").text('M11A')
		 			$("label[for = 'fab3' ]").text('M11B')
		 			$("#fab4").hide();
		 			$("label[for = 'fab4' ]").hide();
					break;
		 		case 'C2' :
					{console.log('FAB 확인 : ' , FabCode);}
					$("label[for = 'fab2' ]").text('C2')
		 			$("label[for = 'fab3' ]").text('C2F')
		 			$("#fab4").hide();
		 			$("label[for = 'fab4' ]").hide();
					break;
		 		case 'IC' :
		 			{console.log('FAB 확인 : ' , FabCode);}
		 			$("label[for = 'fab2' ]").text('M14A')
		 			$("label[for = 'fab3' ]").text('M14B')
		 			$("label[for = 'fab4' ]").text('M16')
		 			//$("#fab4").hide();
					//$("label[for = 'fab4' ]").hide();
	 			break;
	 		} */
	 		
	 		$('#fromMin').spinner().change(function () {
	 			
	 	        var min = + this.value;
	 	        if (min > 59) {
	 	            this.value = min % 60;
	 	            $('#fromHour').val(function (_, oldValue) {
	 	            	if($(this).val() < 10) {
	 	            		
	 	            		console.log("선택");
	 	            	}else if($(this).val() >=23){
	 	            		return +oldValue
	 	            	}else {
	 	            		return +oldValue + Math.floor(min / 60);
	 	            	}
	 	            })
	 	        	$(event.currentTarget).trigger('click');
	 	        }
	 	       console.log($(event.currentTarget).hasClass('ui-spinner-down'));
	 	    });
 		
	 		/* $("#fromMin").on( "spin", function( event, ui ) { 
	 		    //console.log(ui.value)
	 		    var min = + ui.value;
	 	        if (min > 59) {
	 	            this.value = min % 60;
	 	            $('#fromHour').val(function (_, oldValue) {
	 	                return +oldValue + Math.floor(min / 60);
	 	            })
	 	        }
	 		}); */
	 		$('.ui-spinner-button').keyup(function() {
	  		   $(this).siblings('input').change();
	  		});
	 		
	 		$('.ui-spinner-button').click(function() {
	 		   $(this).siblings('input').change();
	 		});
 		
	 		//totalLogList 화면 resize 1초 이벤트
	 		function resizedwLog(){
	 			console.log("resizedwLog : <c:out value="${param.uuid }" />");
	 			$(".tree_wrap").css("height",$(window).height()-180+"px"); // filterView 사이즈 재설정
	 			$(".gridForResize").css("height",$(window).height()-420+"px");
	 			grid<c:out value="${param.uuid }" />.resizeCanvas();
	 				}
	 		
			var doit;
			window.onresize = function(){
			  clearTimeout(doit);
			  doit = setTimeout(resizedwLog, 1000);
			};
		
			init<c:out value="${param.uuid }" />();
			
			// comMsgName 키 입력 이벤트
			$("#comMsgName").keyup(function(e){
				if($(this).val() == ""){ // ALL
					$content.find("#comMsgName1").val("").prop("selected", true);
				}
				else{ // 직접입력
					$content.find("#comMsgName1").val("write").prop("selected", true);
				}
			});
			
			// operationName 키 입력 이벤트
			$("#operationName").keyup(function(e){
				if($(this).val() == ""){ // ALL
					$content.find("#operationName1").val("").prop("selected", true);
				}
				else{ // 직접입력
					$content.find("#operationName1").val("write").prop("selected", true);
				}
			});
			
			// messageName 키 입력 이벤트
			$("#messageName").keyup(function(e){
				if($(this).val() == ""){ // ALL
					$content.find("#messageName1").val("").prop("selected", true);
				}
				else{ // 직접입력
					$content.find("#messageName1").val("write").prop("selected", true);
				}
			});
			
			// comMsgName 셀렉트 값 변경
			/* $("#comMsgName1").change(function(e){
				var val = $(this).val();
				if(val == "write") val = "";
				$content.find("#comMsgName").val(val);
			}); */
			$content.find("#comMsgName1").change(function(){
				var val = $(this).val();
				if(val == "write") val = "";
				$content.find("#comMsgName").val(val);
			});
			
			// operationName 셀렉트 값 변경
			/* $("#operationName1").change(function(e){
				var val = $(this).val();
				if(val == "write") val = "";
				$content.find("#operationName").val(val);
			}); */
			$content.find("#operationName1").change(function(){
				var val = $(this).val();
				if(val == "write") val = "";
				$content.find("#operationName").val(val);
			});
			
			// messageName1 셀렉트 값 변경
			/* $("#messageName1").change(function(e){
				var val = $(this).val();
				if(val == "write") val = "";
				$content.find("#messageName").val(val);
			}); */
			$content.find("#messageName1").change(function(){
				var val = $(this).val();
				if(val == "write") val = "";
				$content.find("#messageName").val(val);
			});
			
			// filterBtn 클릭 이벤트 ( 팝업 종료시, Filter 해제..)
			$("#filterBtn").click(function(){
				var url = "<c:url value='/tot/pop/filterPop.do' />";
				openPopup(url , 600 , 610,function(param){
					 searchParam = param;
					 dataView<c:out value="${param.uuid }" />.beginUpdate();
				     dataView<c:out value="${param.uuid }" />.setItems(data<c:out value="${param.uuid }" />);
					 dataView<c:out value="${param.uuid }" />.setFilterArgs({param:param});
					 dataView<c:out value="${param.uuid }" />.setFilter(procFilter);
				     dataView<c:out value="${param.uuid }" />.endUpdate();
				     updateFilter();
				});				
			});
			
			// 페이징 마우스 over 효과
			$content.find(".ui-icon-container")
			.hover(function () {
			  $(this).toggleClass("ui-state-hover");
			});
			
			// 이전 페이지 조회
			$content.find(".ui-icon-seek-prev").click(function(){
				var page = Number($content.find("#page").val())- 1; // 이전 페이지 
				if(page < 1){  // 최소 값 = 1
					page = 1;
				}
				$content.find("#page").val(page); // 이전 페이지
				$content.find("#pageTxt").text(page); // 이전 페이지 표시
				getLogList<c:out value="${param.uuid }" />(page); // 이전 페이지 조회
				
			});
			
			// 다음 페이지 조회
			$content.find(".ui-icon-seek-next").click(function(){
				var page = Number($content.find("#page").val()) + 1;  // 다음 페이지 
				$content.find("#page").val(page); // 다음 페이지
				$content.find("#pageTxt").text(page); // 다음 페이지 표시
				getLogList<c:out value="${param.uuid }" />(page); // 다음 페이지 조회
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
								
				getFabFromFabSite("tot", _fabSite, "fab", "tdFab");
				getMachineTypeFromFab(_fabSite,"fab", "machineType", "singleFilterChkBoxFab");				
				getAreaFromFab(_fabSite,"fab", "areaName");
				getBayFromArea(_fabSite,"fab", "areaName", "bayName");
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
			
			// copy 버튼 클릭 ( 현재 값 쿠키에 저장 )
			$content.find("#copyBtn").click(function(){
				var from = $content.find("#fromDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#fromHour").val() +$content.find("#fromMin").val()+$content.find("#fromSec").val();
				var to = $content.find("#toDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#toHour").val() +$content.find("#toMin").val()+$content.find("#toSec").val();
				setCookie("mcsLogFromDt",from,null,"/",null);
				setCookie("mcsLogToDt",to,null,"/",null);
			});
			
			// paste 버튼 클릭 ( 쿠키에 저장된 값 가져오기)
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
			
			$content.find("#testBtn").click(function(){
				//$content.find(".slick-header-columns").children().find("TIME").onDblClick();
				//$content.find('.slick-header-columns').children().eq(3).trigger('click');
				$content.find('.slick-header-columns').children().eq(2).trigger('dblclick');
			});
			
			// 조회 버튼 클릭 
			$content.find("#searchBtn").click(function(){
				
				data<c:out value="${param.uuid }" /> = [];
				getLogList<c:out value="${param.uuid }" />(1);
			});
			//20180705 최소버튼 클릭
			$content.find("#cancelBtn").click(function(){
				var url = "<c:url value='/tot/ajax/getTotalLogListStop.do' />"; 
				$.ajax({
		            url: url,
		            type:'post',
		            //data:param,
		            success:function(){
		            }  
		     	});
				
				loadingbarFadeOut(); // 로딩바 숨김
				$content.find("#cancelBtn").parent().css('display','none');
				$content.find("#searchBtn").parent().css('display','block');
			});
			
			// machine 버튼 클릭 
			$content.find("#machineBtn").click(function(){
				if($(this).hasClass("disabled")){ // 비활성 시, return 처리
					return false;					
				}
				var url = "<c:url value='/tot/pop/machineNamePop.do' />";
				openPopup(url , 600 , 610,function(data){ // 팝업 종료시, 값 세팅
					$content.find("#machineName2").val(data);
				});
			});
			
			// single filter 클릭 이벤트)
			$content.find("#singleFilter").click(function(){
				var filter = $content.find("#filter").val();
				if(filter == "02"){ // multi filter
					$content.find("#filter").val("01");
				}else{ // single filter
					$content.find("#filter").val("02");
				}
				setFilter(); // single / multi 폼 활성 / 비활성 
			});
 	
			// multi filter 클릭 이벤트
			$content.find("#multiFilter").click(function(){
				var filter = $content.find("#filter").val();
				if(filter == "02"){ // multi filter
					$content.find("#filter").val("01");
				}else{ // single filter
					$content.find("#filter").val("02");
				}
				setFilter(); // single / multi 폼 활성 / 비활성 
			});
		    
			// Time Range 클릭 이벤트
			$content.find(":radio[name=time]").click(function(){
				var val = $(this).val();
					switch(val) {
				    case "01":  // last 10 minute
				    	var d = new Date();
						var curTime = getTimeStamp(d,"");
						var beForeTenMin = getTimeStamp(new Date(Date.parse(d) + 1000 * 60 * -10),"");
						//console.log(beForeTenMin);
						setSearchTime(beForeTenMin,curTime);
						$content.find("#fromDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
						$content.find("#toDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
						setSearchTimeReadOnly(false);
				        break;
				    case "02": // last 1 hour
				    	var d = new Date();
						var curTime = getTimeStamp(d,"");
						var beForeOneHour = getTimeStamp(new Date(Date.parse(d) + 1000 * 60 * -60),"");
						setSearchTime(beForeOneHour,curTime);
						$content.find("#fromDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
						$content.find("#toDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
						setSearchTimeReadOnly(false);
				        break;
				    case "03": // last 1 day
				    	var d = new Date();
						var curTime = getTimeStamp(d,"");
						setSearchTime(curTime,curTime);
						$content.find("#fromDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date(Date.parse(d) - 1 * 1000 * 60 * 60 * 24)));
						$content.find("#toDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
						setSearchTimeReadOnly(false);
				        break;
				    case "04":  // last 1 minute
				    	var d = new Date();
						var curTime = getTimeStamp(d,"");
						var beForeTenMin = getTimeStamp(new Date(Date.parse(d) + 1000 * 60 * -1),"");
						//console.log(beForeTenMin);
						setSearchTime(beForeTenMin,curTime);
						$content.find("#fromDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
						$content.find("#toDt<c:out value="${param.uuid }" />").val($.datepicker.formatDate('yy.mm.dd', new Date()));
						setSearchTimeReadOnly(false);
				        break;
				    /* case "04": // 직접입력
				    	setSearchTimeReadOnly(false);
				        break; */
				    default:
				}
			});
			
			setFilter();
			
 	});
     
     // 필터 정의
     function procFilter(item, args){
    	 var param = args.param;
    	 var searchOption = param.searchOption;
    	 var isPass = true;
    	 for(var key in param){
    		 var cell = (item[key]==null?"":item[key]) ;
    		 var value = param[key];
	    	 if(value != null && value != "" && key !="searchOption"){
	    		 value = value.replace(/^\s*/,"");  // 앞 공백 제거
	    		 if(value.indexOf("!") == 0){  // not equal
	    			 var notEqualMark = value.indexOf("!");
	    			 value = value.substring(notEqualMark+1);  // not equal 제거
	    			 value = value.replace(/^\s*/,"");  // 앞 공백 제거
	    			 value = value.replace(/\s*$/,"");  // 뒷공백 제거
	    			 if(value.indexOf("(") == 0){ // 앞괄호 ( 멀티 검색어 )
	    				 if(value.indexOf(")") == value.length - 1){ //뒷 괄호 
	    				 	value=value.substring(1,value.length-1)  // 괄호 제거
	    				 	var searchWords = value.split("+");
	    				 	for(var idx in searchWords){
	    				 		isPass = true;
	    				 		var searchWord = searchWords[idx];
	    				 		searchWord = searchWord.replace(/^\s*/,"");  // 앞 공백 제거
	    				    	searchWord = searchWord.replace(/\s*$/,"");  // 뒷공백 제거
	    				    	if(searchWord != ""){
		    				    	if(searchWord.startsWith("%")){  
		    				    		if(searchWord.endsWith("%")){ // 포함된 값 조회
		    				    			 if(cell.indexOf(searchWord.substring(1,searchWord.length-1)) != -1){  // FOUND
		    		    				 			isPass = false;
		    		    				 		 	break;
		    		    				 		 }
		    				    		}else{                //  끝나는 값 조회
		    				    			if(cell.endsWith(searchWord.substring(1))){  // FOUND
		    				    				isPass = false;
		    				    				break;
		    				    			}
		    				    		}
		    				    	}else if(searchWord.endsWith("%")){  // ~로 시작되는 값 조회
		    				    		if(cell.startsWith(searchWord.substring(0,searchWord.length-1))){  // FOUND
	    				    				isPass = false;
	    				    				break;
	    				    			}
		    				    	}else{  // equal 조회
		    				    		if(cell == searchWord){
		    				    			isPass = false;
		    				    			break;
		    				    		}
		    				    	}
	    				    	}
	    				 	}
	    			 	}else{  // 앞 뒤 괄호 체크 실패
	    			 		console.log("문법 오류 뒷괄호 체크 실패");
	    			 	}
	    			 }else{ // 단일검색어
	    				 var searchWord = value;
	    				 searchWord = searchWord.replace(/^\s*/,"");  // 앞 공백 제거
    				     searchWord = searchWord.replace(/\s*$/,"");  // 뒷공백 제거
	    			     if(searchWord != ""){
	    				 	if(searchWord.startsWith("%")){  
	    				 		if(searchWord.endsWith("%")){ // 포함된 값 조회
	    				 			 if(cell.indexOf(searchWord.substring(1,searchWord.length-1)) != -1){  // FOUND
	    		    	 		 			isPass = false;
	    		    	 		 		 	break;
	    		    	 		 		 }
	    				 		}else{                //  끝나는 값 조회
	    				 			if(cell.endsWith(searchWord.substring(1))){  // FOUND
	    				 				isPass = false;
	    				 				break;
	    				 			}
	    				 		}
	    				 	}else if(searchWord.endsWith("%")){  // ~로 시작되는 값 조회
	    				 		if(cell.startsWith(searchWord.substring(0,searchWord.length-1))){  // FOUND
    				     			isPass = false;
    				     			break;
    				     		}
	    				 	}else{  // equal 조회
	    				 		if(cell == searchWord){
	    				 			isPass = false;
	    				 			break;
	    				 		}
	    				 	}
    				     }
	    			 }
	    		 }else{
				    var searchWords = value.split("+");
				    for(var idx in searchWords){
				    	var searchWord = searchWords[idx];
				    	searchWord = searchWord.replace(/^\s*/,"");  // 앞 공백 제거
				    	searchWord = searchWord.replace(/\s*$/,"");  // 뒷공백 제거
				    	isPass = false;
				    	if(searchWord != ""){
				    		if(searchWord.startsWith("%")){  
    				    		if(searchWord.endsWith("%")){ // 포함된 값 조회
    				    			 if(cell.indexOf(searchWord.substring(1,searchWord.length-1)) != -1){  // FOUND
    		    				 			isPass = true;
    		    				 		 	break;
    		    				 		 }
    				    		}else{                //  끝나는 값 조회
    				    			if(cell.endsWith(searchWord.substring(1))){  // FOUND
    				    				isPass = true;
    				    				break;
    				    			}
    				    		}
    				    	}else if(searchWord.endsWith("%")){  // ~로 시작되는 값 조회
    				    		if(cell.startsWith(searchWord.substring(0,searchWord.length-1))){  // FOUND
				    				isPass = true;
				    				break;
				    			}
    				    	}else{  // equal 조회
    				    		if(cell == searchWord){
    				    			isPass = true;
    				    			break;
    				    		}
    				    	}
				    	}
				    }
	    		 }
	    	 if(searchOption == "AND" && !isPass) break;
	    	 if(searchOption == "OR" && isPass) break;
	    	 }
    	 }
    	 return isPass;
     }
     
     // 필터 실행
    function updateFilter() {
   		dataView<c:out value="${param.uuid }" />.setFilterArgs({
    		param: searchParam
    	});
    	dataView<c:out value="${param.uuid }" />.refresh();
    	grid<c:out value="${param.uuid }" />.invalidate();
		grid<c:out value="${param.uuid }" />.render();
    }
     
  // 테이블 컬럼 더블클릭 이벤트
	function setSearchOption<c:out value="${param.uuid }" />(colName , colValue){
		switch(colName) {
		    case "LEVEL":
		    	$content.find(":checkbox[name^=level][value="+colValue+"]").trigger("click");
		        break;
		    case "CARRIER":
		    	$content.find("input[name=carrier]").val(colValue);
		        break;
		    case "MACHINENAME":
		    	$content.find("#machineName1").val(colValue).prop("selected", true);
		        break;
		    case "UNITNAME":
		    	$content.find("#unit").val(colValue);
		        break;
		    case "COMMANDID":
		    	$content.find("#commandId").val(colValue);
		        break;
		    case "COMMAND":
		    	$content.find("#comMsgName1").val(colValue).prop("selected", true);
		    	$content.find("#comMsgName").val(colValue);
		        break;
		    case "MESSAGENAME":
		    	$content.find("#messageName1").val(colValue).prop("selected", true);
		    	$content.find("#messageName").val(colValue);
		        break;
		    case "OPERATION_NAME":
		    	$content.find("#operationName1").val(colValue).prop("selected", true);
		    	$content.find("#operationName").val(colValue);
		        break;
		    case "PROCESS":
		    	$content.find("#process").val(colValue);
		        break;
		    case "TRANSACTIONID":
		    	$content.find("#transactionId").val(colValue);
		        break;
		    case "THREAD":
		    	$content.find("#thread").val(colValue);
		        break;
		    default:
		}
	}
		
    // 로그 상세( XML , SECSII ) 조회	사용안함
    /* function getLogDetail<c:out value="${param.uuid }" />(key){
    	if($content.find("#XML").is(":visible")){ // 로그상세 조회 영역 보임시,
    		showLoadingbar($content.find("#XML"));
    		showLoadingbar($content.find("#SECSII"));
    	}
    	var url = "<c:url value='/tot/ajax/getLogDetail.do' />";	 
		$.ajax({
	            url: url,
	            type:'post',
	            data:{"key":key},
	            success:function(data){
	            	$content.find("#XML").text("");
             		$content.find("#SECSII").text("");
	            	for(var i in data.list){
	            		var logDetail = data.list[i];
	            		$content.find("#XML").text(logDetail.XML);
	             		$content.find("#SECSII").text(logDetail.SECSII);
	            	}
	            	loadingbarFadeOut();
	            }
	     });
    } */
    
	// 초기화
	function init<c:out value="${param.uuid }" />(){
		$content.find('#logInfo').hide(); // 상세 정보영역 숨김
		setDatepicker('<c:out value="${param.uuid }" />'); // datepicker 초기화
		init(); // 공통 초기화 
		drawGrid<c:out value="${param.uuid }" />(); // 그리드 초기화
		// 20220621	X0122410	fabSite 추가		
		getFilterList($content.find('input[name="rdoFabSite"]:checked').val()); //필터 리스트 적용
		// 20220621	X0122410	fabSite 추가
		getCommOpMessageList($content.find('input[name="rdoFabSite"]:checked').val()); // commopMessage 적용
		
		// 2021. 03. 31. X0122410.	fab별로 machinetype list 가져오기
		setTimeout(function(){	
			var _fabSite = $content.find('input[name="rdoFabSite"]:checked').val();
			getMachineTypeFromFab(_fabSite,"fab", "machineType", "singleFilterChkBoxFab");		
		}, 800);
	}
	
	var dataView<c:out value="${param.uuid }" />; 
	var grid<c:out value="${param.uuid }" />;
	var data<c:out value="${param.uuid }" /> = [];
	var searchParam = {};
	
	// COMM.MSG NAME , MESSAGE NAME 병합
	function CommMsgFormatter(row, cell, value, columnDef, dataContext) {
		if(dataContext.COMMAND==='' || dataContext.COMMAND===null){
			return dataContext.MESSAGENAME
		}
		return dataContext.COMMAND;
	}
	
	// 테이블  생성
    //console.log(JSON.stringify(chkboxCol));
	function drawGrid<c:out value="${param.uuid }" />(){		
		
		var checkboxSelector = new Slick.CheckboxSelectColumn({ // 멀티 셀렉트 활성
		      cssClass: "slick-cell-checkboxsel"
		    });
		var normalHeight = 21;
		var expandedHeight = 100;
	
		var columns = [ // 컬럼 생성
			checkboxSelector.getColumnDefinition(),
		  //{name: "row", minWidth: 30, width: 30, formatter: function(row){return row+1}},
		  {id: "No", name: "No.", field: "No", width: 25, minWidth: 25, cssClass:"rowNum", sortable: true },
		  {id: "TIME", name: "TIME", field: "TIME_EX", width: 160, minWidth: 120, cssClass: "cell-title", sortable: true },
		  {id: "LEVEL", name: "LEVEL", field: "LEVEL",  sortable: true , width: 50, minWidth: 40},
		  {id: "CARRIER", defaultSortAsc: false, name: "CARRIER", field: "CARRIER",minWidth: 60, width: 100, sortable: true},
		  {id: "MACHINE", name: "MACHINE", field: "MACHINENAME", width: 80 ,  minWidth: 60,  sortable: true},
		  {id: "MACHINETYPE", name: "MACHINETYPE", field: "MACHINETYPE", minWidth: 60, sortable: true},
		  {id: "UNIT", name: "UNIT", field: "UNITNAME", width: 80,minWidth: 60, sortable: true},
		  {id: "COMMANDID", name: "COMMANDID", field: "COMMANDID",width: 130, minWidth: 60, sortable: true},
		  {id: "COMM.MSG NAME", name: "COMM.MSG NAME", field: "COMMAND",width: 300, minWidth: 200, sortable: true, formatter:CommMsgFormatter},
		  {id: "OPERATION NAME", name: "OPERATION NAME", field: "OPERATION_NAME", width: 150, minWidth: 60, sortable: true},
		  {id: "MESSAGE NAME", name: "BPEL", field: "MESSAGENAME", width: 80, minWidth: 60, sortable: true},
		  {id: "PROCESS", name: "PROCESS", field: "PROCESS",width: 60, minWidth: 30, sortable: true},
		  {id: "TRANSACTIONID", name: "TRANSACTIONID", field: "TRANSACTIONID", minWidth: 30, sortable: true},
		  {id: "TEXT", name: "TEXT", field: "TEXT", minWidth: 30, sortable: true},
		  {id: "THREAD", name: "THREAD", field: "THREAD", minWidth: 30, sortable: true},
		  {id: "RESULTCODE", name: "RESULTCODE", field: "RESULTCODE", minWidth: 30, sortable: true},// 숨김시 reallyHidden 옵션 추가
		  {id: "XML", name: "XML", field: "XML", width: 0, minWidth: 0, maxWidth: 0, cssClass: "reallyHidden", headerCssClass: "reallyHidden" },
		  {id: "SECSII", name: "SECSII", field: "SECSII", width: 0, minWidth: 0, maxWidth: 0, cssClass: "reallyHidden", headerCssClass: "reallyHidden" }
		];
		var options = {
		  enableCellNavigation: true,   // 대량 데이터 속도 개선
		  forceFitColumns: true,        // 그리드 가로 스크롤 유무  
		  autoExpandColumns : true,  // 그리드 사이즈 변경시, 스크롤 생성 유무
		  topPanelHeight: 30,              // 헤더 높이 값
		  enableColumnReorder: true, 
		  rowHeight: normalHeight
		};
		$content.find("#fabSite").val($content.find('input[name="rdoFabSite"]:checked').val());
		var param = $content.find("#searchForm").serializeObject();
		console.log("param : ", param);
		var url = "<c:url value='/mat/ajax/getCarrierLocLogList.do' />";
		  dataView<c:out value="${param.uuid }" /> = new Slick.Data.DataView({ inlineFilters: true }); 
		  grid<c:out value="${param.uuid }" /> = new Slick.Grid("#list<c:out value="${param.uuid }" />", dataView<c:out value="${param.uuid }" />, columns, options); // 그리드 생성
		  grid<c:out value="${param.uuid }" />.setSelectionModel(new Slick.RowSelectionModel({selectActiveRow: false}));
		  grid<c:out value="${param.uuid }" />.registerPlugin(checkboxSelector);  // 멀티 셀렉트 설정
		  dataView<c:out value="${param.uuid }" />.getItemMetadata = metadata(dataView<c:out value="${param.uuid }" />.getItemMetadata);  // row 색 변경 설정
		  var columnpicker = new Slick.Controls.ColumnPicker(columns, grid<c:out value="${param.uuid }" />, options); 
		  
		  //20180618 그리드 height 조절
			grid<c:out value="${param.uuid }" />.updateOptions = function(expanded){
			   var columns = grid.getColumns();
			   if(!expanded){
			       options['rowHeight'] = normalHeight;
			       columns[0]['expanded'] = false;
			   }else{
			       options['rowHeight'] = expandedHeight;
			       columns[0]['expanded'] = true;
			   }
			   grid<c:out value="${param.uuid }" />.setOptions(options);
			   grid<c:out value="${param.uuid }" />.setColumns(columns);
			   grid<c:out value="${param.uuid }" />.invalidate();
			   grid<c:out value="${param.uuid }" />.render();
			}
			
		  // 헤더 클릭 이벤트 그리드 정렬 
		  grid<c:out value="${param.uuid }" />.onSort.subscribe(function(e, args) {
			  var field = args.sortCol.field;
		      var sign = args.sortAsc ? 1: -1;
		      dataView<c:out value="${param.uuid }" />.sort(function (dataRow1, dataRow2) { // 그리드 데이터 비교
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
		  // 마우스 오른쪽 버튼 클릭 ( context 메뉴)
		  grid<c:out value="${param.uuid }" />.onContextMenu.subscribe(function (e) {
		  	e.preventDefault();
		  	var cell = grid<c:out value="${param.uuid }" />.getCellFromEvent(e);
		  	selRow = cell.row;
		  	$("#contextMenu a:eq(0)").hide(); // 첫번째 메뉴 숨김
		  	$("#contextMenu a:eq(1)").hide(); // 두번째 메뉴 숨김
		  	$("#contextMenu").data("row", cell.row).css("top", e.pageY).css("left", e.pageX) .show(); // 메뉴 위치
		  	$("body").one("click", function () { // 마우스 클릭시 메뉴 숨김
		  		$("#contextMenu").hide();
		  	});
		});
		// 마우스 클릭 
		var copyGridColumnValue = '';
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
			    //	event.stopImmediatePropagation();
			    //	copyToClipboard();
			    //	event.stopPropagation(); //상위DOM 으로 이벤트 전파 중지			    	
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
		// 마우스 더블 클릭
		grid<c:out value="${param.uuid }" />.onDblClick .subscribe(function(e, args) {			
         	var cell = args.cell;
		    var rowIdx = args.row;
		    var row = grid<c:out value="${param.uuid }" />.getDataItem(rowIdx);
		    var field = grid<c:out value="${param.uuid }" />.getColumns()[cell].field;
		    var value = row[field];
		    if(field == "COMMAND" && (value==null || value=="")){ // COMM.MSG NAME , MESSAGE NAME 값 병합
		    	value = row["MESSAGENAME"];
		    }		    
		    console.log("onDblClick{"+rowIdx+"},{"+cell+"},{"+value+"}");
         	setSearchOption<c:out value="${param.uuid }" />(field,value);
		});
		 // 셀 포인터 변경
		grid<c:out value="${param.uuid }" />.onActiveCellChanged.subscribe(function (e, args) {			
			var cell = args.cell;
		    var rowIdx = args.row;
		    if(rowIdx === undefined) return; // 선택된 row 없을시 return 
		    var row = data<c:out value="${param.uuid }" />[rowIdx]; // 전체 row 데이터 
		    var field = grid<c:out value="${param.uuid }" />.getColumns()[cell].field; // 선택한 필드 명
		    var value = row[field]; // 선택한 cell value
		    var key = row["key"]; // key 값
		    /* getLogDetail<c:out value="${param.uuid }" />(key); // 상세조회 */
		    getDetailInfo(row); // 상세조회 정보 보임
		    $content.find("#XML").text(row.XML);
		    $content.find("#SECSII").text(row.SECSII);
		    
		    /* pretty code print start */
		    if($("#mySidenav01").width() >= 50){
			    var textVal = row.XML;
			    if(textVal.length > 5000){
				    textVal = textVal.replace(/&/gi, " &amp; ");
					textVal = textVal.replace(/</gi, " &lt;");
					textVal = textVal.replace(/>/gi, "&gt; ");
					
				    $("#myTotDetail").html(textVal);
				    $("#myTotDetail").removeClass('prettyprinted');
			    }else if(textVal.length <=5000){
			    	textVal = textVal.replace(/&/gi, " &amp; ");
					textVal = textVal.replace(/</gi, " &lt;");
					textVal = textVal.replace(/>/gi, "&gt; ");
					
				    $("#myTotDetail").html(textVal);
				    $("#myTotDetail").removeClass('prettyprinted');
				    prettyPrint();
			    }
			    
			}else{
			    $("#myTotDetail").html("");
			    $("#myTotDetail").removeClass('prettyprinted');				
			}
			/* prettyPrint(); */
		    /* pretty code print end */
		    
		});
		  // 그리드 조회 완료 이벤트
		  dataView<c:out value="${param.uuid }" />.onRowCountChanged.subscribe(function (e, args) {
			$content.find("#rowCount").text(args.current);
		    //grid<c:out value="${param.uuid }" />.updateRowCount(); //go to top rows
		    grid<c:out value="${param.uuid }" />.render();
		  });
		  // 로우 카운트 변경
		  dataView<c:out value="${param.uuid }" />.onRowsChanged.subscribe(function(e,args) {
			  grid<c:out value="${param.uuid }" />.invalidateRows(args.rows);
		      grid<c:out value="${param.uuid }" />.render();
		  });
		  // 페이징 info 변경		  
		  dataView<c:out value="${param.uuid }" />.onPagingInfoChanged.subscribe(function (e, pagingInfo) {
		       grid<c:out value="${param.uuid }" />.render();
		  });
		  // no record display . . . 
		  if( data<c:out value="${param.uuid }" /> == null || data<c:out value="${param.uuid }" />.length <= 0){
		 	 grid<c:out value="${param.uuid }" />.invalidateAllRows();
		 	 $content.find('.grid-canvas').html('<div class="alert-info-grid">No Record(s) Found</div>');
		  }
		  
		  
	}
		
	// 조회
	function getLogList<c:out value="${param.uuid }" />(page){
		
		if(!chkValidate()) return;  // 유효성 체크
		$content.find("#searchBtn").addClass('disabled'); // 조회 버튼 비활성 (중복 조회 방지)
		$content.find("#searchBtn").parent().css('display','none');
		$content.find("#cancelBtn").parent().css('display','block');
		showLoadingbar($("#list<c:out value="${param.uuid }" />")); // 로딩바 활성
		$content.find('#page').val(page); // 현재 페이지 
		$content.find("#pageTxt").text(page); // 현재 페이지 표시
		$content.find(".ui-icon-seek-prev , .ui-icon-seek-next").addClass("ui-state-disabled"); // prev , next 버튼 비활성
		//==== 조회 파라메터 설정 START =====
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
		//==== 조회 파라메터 설정 END ========
		$content.find("#fabSite").val($content.find('input[name="rdoFabSite"]:checked').val());
		var param = $content.find("#searchForm").serializeObject();		
		console.log("param : ", param);	
		
		//2021.03.24	X0122410 : machineTypes parameter 추가
		var machineTypes = $content.find(":checkbox[name^=machineType]:checked").map(function(){return $(this).val(); }).get().join();
		param['machineTypes'] = machineTypes;
		console.dir(param);
		var url = "<c:url value='/tot/ajax/getTotalLogList.do' />";
		$.ajax({
	            url: url,
	            type:'post',
	            data: param,
	            success:function(result){ 
	            	dataView<c:out value="${param.uuid }" />.setItems([]);
	            	if(result != null  && result.rows != null){ // 조회된 데이터 존재시, 그리드에 표시
	            		if($content.find("#reload").val() == "01"){ // refresh
	            			data<c:out value="${param.uuid }" /> = result.rows;
	            		}else{	// append
	            			data<c:out value="${param.uuid }" /> = data<c:out value="${param.uuid }" />.concat(result.rows);
	            		}
						dataView<c:out value="${param.uuid }" />.setItems(data<c:out value="${param.uuid }" />); 
						setPagerState(result.rows); // 페이징 설정
						loadingbarFadeOut(); // 로딩바 숨김
						grid<c:out value="${param.uuid }" />.resizeCanvas();
						$content.find("#cancelBtn").parent().css('display','none');
						$content.find("#searchBtn").parent().css('display','block');
						
						$content.find("#searchBtn").removeClass('disabled'); // 조회 버튼 활성
	            	}else{ // 20180712 data 없을때 loadingbar 수정
						loadingbarFadeOut(); // 로딩바 숨김
						console.log("Data is null!!");
						$content.find("#cancelBtn").parent().css('display','none');		// 200508 hgJeon Data 없을 시 Cacel 버튼 숨김
						$content.find("#searchBtn").parent().css('display','block');
						
						if($content.find("#laptime").text() > 15100 && data<c:out value="${param.uuid }" />.length <= 0){ 
								console.log("길이:"+data<c:out value="${param.uuid }" />.length);
								grid<c:out value="${param.uuid }" />.invalidateAllRows();
								$content.find('.grid-canvas').html('<div class="alert-info-grid">TimeOut Error</div>');
							}else /* if(dataView<c:out value="${param.uuid }" />.length <= 0) */ { // 조회된 데이터 없을 시, no Recorod 표시
								console.log("11");
								grid<c:out value="${param.uuid }" />.invalidateAllRows();
								$content.find('.grid-canvas').html('<div class="alert-info-grid">No Record(s) Found</div>');
							}
						$content.find("#searchBtn").removeClass('disabled'); // 조회 버튼 활성
	            	}
	            }
		});
		
	}
	
	// Filter View 숨기기
	$content.find("#fold_filter_view").click(function(){
		$content.find("#filter_view").css("display", "none");
		$content.find("#unfold_filter_view_wrap").css("display", "");
		grid<c:out value="${param.uuid }" />.resizeCanvas(); // 그리드 가로사이즈 변경
	});
	
	// Filter View 보이기
	$content.find("#unfold_filter_view").click(function(){
		$content.find("#unfold_filter_view_wrap").css("display", "none");
		$content.find("#filter_view").css("display", "");
		grid<c:out value="${param.uuid }" />.resizeCanvas(); // 그리드 가로사이즈 변경
	});
	
	//상세 타이틀 정보 표시
	function getDetailInfo(row){
            $content.find('#logInfo').show(); // 상세정보 표시 보임
    		var selMessageName = row["MESSAGENAME"];	
    		var selOperationName =  row["OPERATION_NAME"];	
    		var selCarrier =  row["CARRIER"];
    		var selTransportCommandId =  row["COMMANDID"];
    		var selMachineName =  row["MACHINENAME"];
    		if(selMessageName == ''){
    			$content.find("#titMessageName").prev().hide();
    		}else{
    			$content.find("#titMessageName").prev().show();
    		}
    		if(selOperationName == ''){
    			$content.find("#titOperationName").prev().hide();
    		}else{
    			$content.find("#titOperationName").prev().show();
    		}
    		if(selCarrier == ''){
    			$content.find("#titCarrier").prev().hide();
    		}else{
    			$content.find("#titCarrier").prev().show();
    		}
    		if(selTransportCommandId == ''){
    			$content.find("#titTransportCommandId").prev().hide();
    		}else{
    			$content.find("#titTransportCommandId").prev().show();
    		}
    		if(selMachineName == ''){
    			$content.find("#titMachineName").prev().hide();
    		}else{
    			$content.find("#titMachineName").prev().show();
    		}
    		$content.find('#titMessageName').text(selMessageName);
    		$content.find('#titOperationName').text(selOperationName);
    		$content.find('#titCarrier').text(selCarrier);
    		$content.find('#titTransportCommandId').text(selTransportCommandId);
    		$content.find('#titMachineName').text(selMachineName);
    		

	}
	
	// Global 변수 메모리 해제..
	function destroy<c:out value="${param.uuid }" />(){
		delete dataView<c:out value="${param.uuid }" />;
		delete grid<c:out value="${param.uuid }" />;
		delete data<c:out value="${param.uuid }" />;
		delete getLogList<c:out value="${param.uuid }" />;
		delete drawGrid<c:out value="${param.uuid }" />;
		delete init<c:out value="${param.uuid }" />;
		console.log("delete memory done..");
	}
	
	//필터 리스트(Comm Msg, Operation_name, Message : 로그조회 화면 전용)
	// 20220621	X0122410	fabSite 추가
	function getCommOpMessageList(fabSite){		
		setTimeout(function(){
			console.log('getCommMsgNameList');
			var urlCommName = "filter/ajax/getCommMsgNameList.do";	 
			var param = { "fabSite":fabSite }; // 파라메터
			$.ajax({
	            url: urlCommName,
	            type:'get',
	            data: param,
	            dataType: 'json',
	            success:function(data){
	            	var result = data[0];
	            	console.log(result);
	            	$.each(result, function(index, value){
	            		$content.find(".comMsgName").append(""+
	            		"<option value='"+value.COMM_MSG+"'>"+value.COMM_MSG+"</option>"); 
	            	}); 
	            	$content.find(".comMsgName").append("<option value='write'>직접입력</option>"); 
	            }
		    });
		}, 1200);
		
		setTimeout(function(){
			console.log('getOperationNameList');
			var urlOpName = "filter/ajax/getOperationNameList.do";	 
			var param = { "fabSite":fabSite }; // 파라메터
			$.ajax({
	            url: urlOpName,
	            type:'get',
	            data: param,
	            dataType: 'json',
	            success:function(data){
	            	var result = data[0];
	            	console.log(result);
	            	$.each(result, function(index, value){
	            		$content.find(".operationName").append(""+
	            		"<option value='"+value.OPERATION+"'>"+value.OPERATION+"</option>"); 
	            	}); 
	            	$content.find(".operationName").append("<option value='write'>직접입력</option>"); 
	            }
		    });
		}, 1400);
		
		setTimeout(function(){
			console.log('getMessageNameList');
			var urlMessage = "filter/ajax/getMessageNameList.do";	 
			var param = { "fabSite":fabSite }; // 파라메터
			$.ajax({
	            url: urlMessage,
	            type:'get',
	            data: param,
	            dataType: 'json',
	            success:function(data){
	            	var result = data[0];
	            	console.log(result);
	            	$.each(result, function(index, value){
	            		$content.find(".messageName").append(""+
	            		"<option value='"+value.MESSAGE+"'>"+value.MESSAGE+"</option>");
	            	});
	            	$content.find(".messageName").append("<option value='write'>직접입력</option>");
	            	
	            	/*
	            	* url info input START
	            	*/
	            	
	            	
	            	_url_get_function(location.href.toString());
	            	//_url_get_function(window.location.search);
	            	/**
	            	* url info input END
	            	*/
	            	
	            }
		    });
		}, 1600);
	
	}
	
	// ERROR , FATAL 일경우 , row 붉은색 으로 변경., WARN 일경우 , row 노란색으로
	// RESULTCODE 0 or 4 가 아닐경우 row 붉은색으로
	function metadata(old_metadata_provider) {
		//console.log(old_metadata_provider);
		  return function(row) {
		    var item = this.getItem(row);
		    var RESCODE = item.RESULTCODE;
		    var ret  = (old_metadata_provider(row) || {});
		    if (item) {
		      ret.cssClasses = (ret.cssClasses || '');
		      if ( item.LEVEL == "ERROR" || item.LEVEL == "FATAL" ) {
		        ret.cssClasses += ' errorRow';
		      }
		      else if( item.LEVEL == "WARN" ){
		    	 ret.cssClasses += ' warnRow';
		      }
//		      else if( item.RESULTCODE != "4" || item.RESULTCODE != "0" ){ //171011 resultcode color 표시
//			    	 ret.cssClasses += ' errorRow';
//			      } // 171011 수정 전
				else if ( RESCODE != null  ){
					if ( !(item.RESULTCODE == "4" || item.RESULTCODE =="0") ){
						ret.cssClasses += ' errorRow';
					}	
				} // 171011 수정 후
		    }
		    return ret;
		  }
	 }
	
	reset(); 
	
	// 그리드  fold / open
	$content.find("#downloadLink").click(function(){
		console.log("down");
		var modifiedData = [];
		var j = data<c:out value="${param.uuid }" />.length;
		for(var i=0;i<j;i++){
			var temp = {
				COMMANDID : data<c:out value="${param.uuid }" />[i].COMMANDID,
				MESSAGENAME : data<c:out value="${param.uuid }" />[i].MESSAGENAME,
				TEXT : data<c:out value="${param.uuid }" />[i].TEXT,
				LEVEL : data<c:out value="${param.uuid }" />[i].LEVEL,
				MACHINENAME : data<c:out value="${param.uuid }" />[i].MACHINENAME,
				TRANSACTIONID : data<c:out value="${param.uuid }" />[i].TRANSACTIONID,
				CARRIER : data<c:out value="${param.uuid }" />[i].CARRIER,
				UNITNAME : data<c:out value="${param.uuid }" />[i].UNITNAME,
				PROCESS : data<c:out value="${param.uuid }" />[i].PROCESS,
				OPERATION_NAME : data<c:out value="${param.uuid }" />[i].OPERATION_NAME,
				_time : data<c:out value="${param.uuid }" />[i]._time,
				TIME_EX : data<c:out value="${param.uuid }" />[i].TIME_EX,
				THREAD : data<c:out value="${param.uuid }" />[i].THREAD,
				COMMAND : data<c:out value="${param.uuid }" />[i].COMMAND
			}
			modifiedData[i] = temp;
		}
		downloadExcel(modifiedData);
	});
	
	// carrier 파라메터 존재시 carrier 명으로 조회 (Transprot 에서 그리드 더블 클릭으로 넘어온 경우..)
	if("<c:out value="${param.carrier }" />" != ""){
	    var from = '${param.from}'; // 시작일
	    var to = '${param.to}';  // 종료일
		if(from != ""){ // 시작일 변수 세팅
			var fromDt = from.substr(0,4)+"."+from.substr(4,2)+"."+from.substr(6,2);
			var fromHour = from.substr(8,2);
			var fromMin = from.substr(10,2);
			var fromSec = from.substr(12,2);
			$content.find("#fromDt<c:out value="${param.uuid }" />").val(fromDt);
			$content.find("#fromHour").val(fromHour);
			$content.find("#fromMin").val(fromMin);
			$content.find("#fromSec").val(fromSec);
		}
		if(to != ""){ // 종료일 변수 세팅
			var toDt = to.substr(0,4)+"."+to.substr(4,2)+"."+to.substr(6,2);
			var toHour = to.substr(8,2);
			var toMin = to.substr(10,2);
			var toSec = to.substr(12,2);
			$content.find("#toDt<c:out value="${param.uuid }" />").val(toDt);
			$content.find("#toHour").val(toHour);
			$content.find("#toMin").val(toMin);
			$content.find("#toSec").val(toSec);
		}
		$content.find("#searchBtn").trigger("click"); // 조회 버튼 클릭 
	}
	
	
	
</script>