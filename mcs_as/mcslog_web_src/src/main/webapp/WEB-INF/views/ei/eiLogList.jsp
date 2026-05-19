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
                <a href="#" class="location"><spring:message code="site.eiLogList" text="default text" /></a>
            </span>
            <span class="loc_info_ico loc_info_ico_arr_depth"></span>
            <span class="location_box">
                <a href="#" class="location"><spring:message code="site.eiLogList" text="default text" /></a>
            </span>
        </div>
        <!-- //Location Information -->
        <!-- Page Title -->
        <table class="page_tit">
            <tr>
                <td class="tit_area">
                    <div class="tit"><spring:message code="site.eiLogList" text="default text" /></div>
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
						                                    	<input type="checkbox" class="jqForm" id="eiFab1" name="eiFab1" value="ALL"><label for="eiFab1">ALL</label><BR>
						                                    	<!-- 2021. 4. 5, X0122410 : Fabs 리스트 이용 -->
		                                            			<c:forEach  items="${fabs}" var="fab" varStatus="status">
															 		<c:set var="num" value="${status.index + 2}"/>
															 		<c:set var="isVal" value="F" />
																	<c:forEach var="item" items="${params.fab}">																			
																	  <c:if test="${item eq fab}">																			  	
																	    <c:set var="isVal" value="T" />
																	  </c:if>																			  
																	</c:forEach>
																	<input type="checkbox" class="jqForm" id="eiFab<c:out value="${num}"/>" name="eiFab<c:out value="${num}"/>" <c:if test="${isVal eq 'T'}">checked="checked"</c:if> value="<c:out value="${fab}"/>" ><label for="eiFab<c:out value="${num}"/>"><c:out value="${fab}"/></label><BR>
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
					                                         <input type="checkbox" class="jqForm" id="level3" name="level3"  <c:if test="${param.level2 == 'INFO' }" >checked="checked"</c:if> value="INFO" ><label for="level3">INFO</label><BR>
					                                         <input type="checkbox" class="jqForm" id="level4" name="level4"  <c:if test="${param.level2 == 'FINE' }" >checked="checked"</c:if> value="FINE" ><label for="level4">FINE</label><BR>
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
					                                    <td class="condition_t_head_top" colspan="3">
					                                    	<i class="minus square icon"></i>
					                                    	<span>LOG</span>
					                                    </td>
					                                </tr>
					                                <tr>
					                                	<th scope="col" class="condition_t_head">Type</th>
					                                    <td class="condition_t_data">
					                                         <%-- <input type="checkbox" class="jqForm" id="logType1" name="logType1" <c:if test="${param.logType1 == 'ALL' }" >checked="checked"</c:if> value="ALL"  ><label for="logType1">ALL</label><BR> --%>
					                                         <input type="checkbox" class="jqForm" id="logType2" name="logType2"  checked value="TS" ><label for="logType2">TS</label><BR>
					                                         <input type="checkbox" class="jqForm" id="logType3" name="logType3"  <c:if test="${param.logType3 == 'EI' }" >checked="checked"</c:if> value="EI" ><label for="logType3">EI</label><BR>
					                                    </td>
					                                    <td class="condition_t_data">
					                                         
					                                         <input type="checkbox" class="jqForm" id="logType4" name="logType4"  <c:if test="${param.logType4 == 'CS' }" >checked="checked"</c:if> value="CS" ><label for="logType3">CS</label><BR>
					                                         <input type="checkbox" class="jqForm" id="logType5" name="logType5"  <c:if test="${param.logType5 == 'DS' }" >checked="checked"</c:if> value="DS" ><label for="logType4">DS</label><BR>
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
					                                	<th scope="col" class="condition_t_head">PROCESS</th>
					                                    <td class="condition_t_data">
					                                         <select class="eiProcessList" id="eiProcessList" name="eiProcessList" style="width:158px;margin-bottom: 5px">
					                                         	<option value='ALL' selected='selected' >ALL</option>
					                                        </select>
					                                        	<input type="text" id="inputProcessName" name="process" title="Multi Condition Search &#10;ex) Process1, Process2, Process3" value="" />
					                                    </td>
					                                </tr>
					                                <tr>
					                                	<th scope="col" class="condition_t_head" style="width:200px">Host</th>
					                                    <td class="condition_t_data">
					                                    	 <input type="checkbox" class="jqForm" id="host1" name="host1" checked value="primary"><label for="host1">Primary</label>
					                                    	 <input type="checkbox" class="jqForm" id="host2" name="host2" checked value="secondary"><label for="host2">Secondary</label>
					                                    </td>
					                                </tr>
					                                <tr>
					                                	<th scope="col" class="condition_t_head">Text
					                                	<input type="hidden" name="eiTextConditionCheckBox" value="and"/>
					                                		<input type="checkbox" class="jqForm" id="eiTextConditionCheckBox" name="eiTextConditionCheckBox" checked value="or" style="margin-left: 50px;"><label id="AndOr_selectLabel">or</label>
					                                	</th>
					                                    <td class="condition_t_data">
					                                         <input type="text" id="ei_text" name="text" title="Multi Condition Search &#10;ex) 4PDN6591, 4AFZ41-418, 4PTI4101_3" value="<c:out value="${param.text }" />" />
					                                         <!-- <input type="hidden" id="ei_text_helper" title="how to know search a text!!" /> -->
					                                         <!-- <a rel="tooltip" title="{{ tool_tip_message, tool_tip_message, tool_tip_message, tool_tip_message, tool_tip_message,tool_tip_message }}"> m </a> -->
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
                                  <!-- <i id="foldTableBtn11" class="minus square icon large" style="color:#ccd2de"></i> -->
                                  <span class="txt">LIST
                                  </span>
                              </div>
                          </div>
                          <div class="opt_tit_right">
                             	<div class="elmt">
                             		<!-- <a id="ei_sideNav_view" class="btn_fix btn_arr_left " style="float:right; margin-left: 10px;" onclick="openNavEI()"></a> -->
                                     <div id="downloadLink" onclick="downloadExcel(data<c:out value="${param.uuid }" />);" class="mini ui primary button" style="width:85px;float: right;margin-left: 4px;white-space:nowrap;">
												<i class="file excel outline icon"></i>Excel
									 </div>
									 <!-- <div id="textDetailBtn" class="mini ui primary button" style="width:77px;float: right;margin-left: 4px;white-space:nowrap;">
										<i class="cocktail icon"></i>Detail
									</div> -->
                                </div>
                           </div>
                   		</div>
                      <!-- //Option Title -->
                      	<div id="grid_container<c:out value="${param.uuid }" />">
                          <div id="list<c:out value="${param.uuid }" />" class="gridForResize_ei" style="width:100%;height:565px; background: white; outline: 0; border: 1px solid gray;"></div>
                      		<c:import url="/WEB-INF/views/common/slickGridPager.jsp" charEncoding="utf-8" />
              			</div>
           		</div>
           		
           		<div id="sideDetail_view_EI<c:out value="${param.uuid }" />" class="lay_item_right" style="width:2px">
					<div id="Sidenav_EI" class="sidenav1">
						<div>
							<a href="javascript:void(0)" class="closebtn" onclick="closeNavEI()">
								<i class="minus circle icon small" style="color:#ccd2de"></i>
							</a>
						</div>
						<div style="border: 1px solid #111;">
							<pre class="prettyprint" id="LogDetail_EI" style="white-space: pre-wrap; "></pre>	
						</div>
					</div>		
				 </div>
                 <%-- <div id="detail_view_secs<c:out value="${param.uuid }" />" class="lay_item_right" style="width:550px">
					
					<div id="gridDetailListSecs" class="tbl_hori" style="margin-left:10px">
                        <table class="tbl_hori_inside" summary="해당 표에 대한 설명을 적어주세요.">
                             <caption><spring:message code="site.common.summary.desc01" text="default text" /></caption>
                             <colgroup>
                                 <col width="120"/>
                             </colgroup>
                             <tbody>
                                 <tr class="hori_t_row">
                                     <td class=""><textarea class="grid_detail_list" id="SECSII_List" readOnly style=" width: 100%; height: 820px; -webkit-box-sizing: border-box; /* Safari/Chrome, other WebKit */ -moz-box-sizing: border-box;    /* Firefox, other Gecko */  box-sizing: border-box;         /* Opera/IE 8+ */" ></textarea></td>
                                 </tr>
                             </tbody>
                        </table>
                    </div>
					
                 </div> --%>
        	</div>
        </form>
    	</div>
		</div>

<script type="text/javascript">
	
	//sideNav 관련 스크립트 추가
	function openNavEI() {
		document.getElementById("Sidenav_EI").style.width = "550px";
    	//$content.find("#gridDetailAreaSecs").hide();
    	//$("#list<c:out value="${param.uuid }" />").css("height",$(window).height()-200+"px");
    	$(".gridForResize_ei").css("height",$(window).height()-200+"px");
		document.getElementById("sideDetail_view_EI${param.uuid }").style.width = "550px";
		$(".sidenav1 pre").css("height",$(window).height()-150+"px");
		grid<c:out value="${param.uuid }" />.resizeCanvas();
		
	}
	function closeNavEI() {
		document.getElementById("Sidenav_EI").style.width = "0";
	    //$content.find("#gridDetailAreaSecs").show();
		document.getElementById("sideDetail_view_EI${param.uuid }").style.width = "2px";
		$(".gridForResize_ei").css("height",$(window).height()-200+"px");
		//$("#list<c:out value="${param.uuid }" />").css("height",$(window).height()-($("#SECS_II").height()*2.5)+"px");
		grid<c:out value="${param.uuid }" />.resizeCanvas();
	}

	$content = $("#body_${param.uuid }");
	$(document).ready(function(){
		$content.find('#logInfo').hide();
		init<c:out value="${param.uuid }" />();
		
		//secsLog 화면 resize 1초 이벤트
 		function resizedwEI(){
 			console.log("resizedwEI!! ");
			$(".tree_wrap").css("height",$(window).height()-180+"px"); // filterView 사이즈 재설정
			//$("#SECSII_List").css("height",$(window).height()-120+"px");
 			$(".gridForResize_ei").css("height",$(window).height()-174+"px");
 			grid<c:out value="${param.uuid }" />.resizeCanvas();
		}
 		
		var doit;
		window.onresize = function(){
		  clearTimeout(doit);
		  doit = setTimeout(resizedwEI, 1000);
		};
		
		// 200507 hgJeon Fab 기준정보에 따른 Naming 변경
 		/* switch(FabCode) 
 		{
 		case 'M14' :
 			{console.log('FAB 확인 : ' , FabCode);}
 			$("label[for = 'eiFab2' ]").text('M14')
 			$("label[for = 'eiFab3' ]").text('M16')
 			$("#eiFab3").hide();
 			$("label[for = 'eiFab3' ]").hide();
 			break;
 		case 'M15' :
			{console.log('FAB 확인 : ' , FabCode);}
			$("label[for = 'eiFab2' ]").text('M15A')
 			//$("label[for = 'fab3' ]").text('M15B')
 			$("#eiFab3").hide();
 			$("label[for = 'eiFab3' ]").hide();
			break;
 		case 'M11' :
			{console.log('FAB 확인 : ' , FabCode);}
			$("label[for = 'eiFab2' ]").text('M11A')
 			$("label[for = 'eiFab3' ]").text('M11B')
			break;
 		case 'C2' :
			{console.log('FAB 확인 : ' , FabCode);}
			$("label[for = 'eiFab2' ]").text('C2')
 			$("label[for = 'eiFab3' ]").text('C2F')
			break;
 		case 'IC' :
			{console.log('FAB 확인 : ' , FabCode);}
	 		$("label[for = 'eiFab2' ]").text('M14A');
	 		$("label[for = 'eiFab3' ]").text('M14B');
	 		$("label[for = 'eiFab4' ]").text('M16');			
			break;
 		} */
		
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
			
			getFabFromFabSite("ei", _fabSite, "eiFab", "tdFab");
			//getMachineTypeFromFab(_fabSite,"eiFab", "machineType", "singleFilterChkBoxFab");				
			//getAreaFromFab(_fabSite,"eiFab", "areaName"); 
			//getBayFromArea(_fabSite,"eiFab", "areaName", "bayName");
			//getMachineNameList(_fabSite,"eiFab", "areaName","bayName","machineType","machineName1");
		});
		
		// 20180615 FAB 클릭 이벤트
		$content.on("click", ":checkbox[name^=eiFab]", function(){
			var val = $(this).val();
			if(val == "ALL"){ // ALL 체크시, 다른 체크 박스 해제
				$content.find(":checkbox[name^=eiFab]:gt(0)").prop("checked",false);
				$content.find(":checkbox[name^=eiFab]:eq(0)").prop("checked",true);
			}else{  // 다른 체크박스 체크시 , ALL 체크박스 해제
				var tmpChk = 0;
				$content.find(":checkbox[name^=eiFab]:checked").each(function(){
					tmpChk += 1;
				});
				if( tmpChk > 0){
					$content.find(":checkbox[name^=eiFab]:eq(0)").prop("checked",false);
				}else{
					$content.find(":checkbox[name^=eiFab]:eq(0)").prop("checked",true);
				}
			}
			getSelectProcessList();
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
		
		// LogType 클릭 이벤트
		$content.find(":checkbox[name^=logType]").click(function(){
			var val = $(this).val();
			if(val == "TS"){ // TS 체크시, 다른 체크 박스 해제
				$content.find(":checkbox[name^=logType]:gt(0)").prop("checked",false);
			}else{  // 다른 체크박스 체크시 , ALL 체크박스 해제
				$content.find(":checkbox[name^=logType]:eq(0)").prop("checked",false);
			}
			getSelectProcessList();
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
		// 최소버튼 클릭
		$content.find("#cancelBtn").click(function(){
			
			var url = "<c:url value='/ei/ajax/getEiQueryStop.do' />"; 
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
		
		/* $content.find("#machineBtn").click(function(){
			if($(this).hasClass("disabled")){
				return false;					
			}
			var url = "<c:url value='/secs/ajax/getsecsLogList.do' />";
			openPopup(url , 600 , 610,function(data){
				console.log(JSON.stringify(data));
				$content.find("#machineName2").val(data);
			});
		}); */
			
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
     
  	// PROCESS 키 입력 이벤트
	$("#inputProcessName").keyup(function(e){
		if($(this).val() == ""){ // ALL
			$content.find("#eiProcessList").val("").prop("selected", true);
		}
		else{ // 직접입력
			$content.find("#eiProcessList").val("write").prop("selected", true);
		}
	});
  	
	// PROCESS 셀렉트 값 변경
	/* 	$("#eiProcessList").change(function(e){
		var val = $(this).val();
		if(val == "write") val = "";
		$content.find("#inputProcessName").val(val);
	}); */
	$content.find("#eiProcessList").change(function(){
		var val = $(this).val();
		if(val == "write") val = "";
		$content.find("#inputProcessName").val(val);
	});
     
     // 초기화
	function init<c:out value="${param.uuid }" />(){
		
		init();
		setDatepicker('<c:out value="${param.uuid }" />');
		// 검색 시간 ( Last 10 Minute )
		drawGrid<c:out value="${param.uuid }" />();
		//필터 리스트 적용
		// 20220621	X0122410	fabSite 추가
		//getFilterList($content.find('input[name="rdoFabSite"]:checked').val());
		//processList 적용
		// 20220621	X0122410	fabSite 추가
		getProcessList($content.find('input[name="rdoFabSite"]:checked').val());
	}
	
	var dataView<c:out value="${param.uuid }" />;
	var grid<c:out value="${param.uuid }" />;
	var data<c:out value="${param.uuid }" /> = [];
	var textDetailPopup = null;	// 200331 hgJeon popup window 변수 추가
	// 테이블  생성
	function drawGrid<c:out value="${param.uuid }" />(){
		var columns = [
				//{name: "row", minWidth: 40, width: 40, formatter: function(row){return row+1}},
			  {id: "No", name: "No.", field: "No", width: 15, minWidth: 15, cssClass:"rowNum" },
			  {id: "TIME", name: "TIME", field: "TIME_EX", width: 60, minWidth: 60, cssClass: "cell-title", sortable: true},
			  {id: "FAB", name: "FAB", field: "FAB" , width: 24 , minWidth: 20, sortable: true},
			  {id: "LOG", name: "LOG", field: "LOG" , width: 24 , minWidth: 20, sortable: true},
			  {id: "HOST", name: "HOST", field: "HOST" , width: 30 , minWidth: 30, sortable: true},
			  {id: "LEVEL", name: "LEVEL", field: "LEVEL" , width: 30 , minWidth: 20, sortable: true},
			  {id: "PROCESS", name: "PROCESS", field: "PROCESS" , width: 40 , minWidth: 30, sortable: true},
			  {id: "THREAD", name: "THREAD", field: "THREAD" , width: 60 , minWidth: 30, sortable: true},
			  {id: "CLASS", name: "CLASS", field: "CLASS" , width: 100 , minWidth: 60, sortable: true},
			  {id: "DATA", name: "TEXT", field: "TEXT_XML", width: 360, minWidth: 200, sortable: true},
			  {id: "TEXT", name: "TEXT", field: "TEXT", width: 0, minWidth: 0, maxWidth: 0, cssClass: "reallyHidden", headerCssClass: "reallyHidden" },
			  /* {id: "SKEY", name: "SKEY", field: "SKEY", width: 0, minWidth: 0, maxWidth: 0, cssClass: "reallyHidden", headerCssClass: "reallyHidden" } */
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
			  
			// 셀 포인터 변경
			grid<c:out value="${param.uuid }" />.onActiveCellChanged.subscribe(function (e, args) {
				var cell = args.cell;
			    var rowIdx = args.row;
			    if(rowIdx === undefined) return; // 선택된 row 없을시 return 
			    var row = data<c:out value="${param.uuid }" />[rowIdx]; // 전체 row 데이터 
			    var field = grid<c:out value="${param.uuid }" />.getColumns()[cell].field; // 선택한 필드 명
			    var value = row[field]; // 선택한 cell value
			    getDetailInfo(row); // 상세조회 정보 보임
	     		//$content.find("#SECS_II").text(row.TEXT);
			    
			  	//var url = "<c:url value='/ei/pop/textDetailPop.do' />";
  				var url = "<c:url value='/ei/pop/textAreaPop.do' />";		// test
				var gridCount = $content.find("#rowCount").text();
  				
  				var popupKey = $content.find("#fromDt<c:out value="${param.uuid }" />").val().replace(/\./g, "") + $content.find("#fromHour").val() +$content.find("#fromMin").val()+$content.find("#fromSec").val();
  				
  				//Data Map 생성
				var textMap = new Map();
				
			    for (i=0; i< gridCount; i++){
			    	textMap.put(i, data<c:out value="${param.uuid }" />[i].TEXT);
			    }
			    
			 	// 200701 hgJeon popup window 기능 수정
				if(textDetailPopup == null || (textDetailPopup.closed)) {
 					
					textDetailPopup = window.open(popupURL, "wFormx", "width=1200,height=800,location=no,menubar=no,status=no,titilebar=no,scrollbars=yes");
				    
					textDetailPopup.focus();
					
					var popupData = function(){
				        var mon = textDetailPopup.document.getElementById("popupTextArea");
				        if(typeof(mon)!="undefined"){
				        	
				        	textDetailPopup.detailTextArea(textMap, gridCount, rowIdx, popupKey);
				            clearInterval(delay);	// 즉시 종료
				        }
				    }
				    var delay = setInterval(popupData, 600);	// 주시적으로 실행
					
  				}else{
					textDetailPopup.focus();
				    textDetailPopup.detailTextFindFocus(textMap, gridCount, rowIdx, popupKey, popupFlag);	// popup 이 이미 열려있을때
				    popupFlag = false;	// 초기화
  				}
  				
				/* 200401 hgJeon popup window start */
				/* if(textDetailPopup == null || (textDetailPopup.closed)) {
					
					textDetailPopup = window.open(url, "wFormx", "width=800,height=600,location=no,menubar=no,status=no,titilebar=no,scrollbars=yes");
					
					var gridCount = $content.find("#rowCount").text();
					var tList = "";
				    for (i=0; i<gridCount; i++){
				    	tList += data<c:out value="${param.uuid }" />[i].TEXT +"\n"
				    }
				    
				    tList = tList.replace(/&/gi, "&amp;");
				    tList = tList.replace(/</gi, "&lt;");
					
				    var teste = function(){
				        var mon = textDetailPopup.document.getElementById("popupLogDetail_EI");
				        if(typeof(mon)!="undefined"){
				            var h = textDetailPopup.innerHeight;
				            var strh = String(h - 40 - 30)+'px';
				            textDetailPopup.document.getElementById("popupLogDetail_EI").innerHTML = tList;
				            clearInterval(id);
				        }
				    }
				    var id = setInterval(teste, 800);
				    
				}else{
					textDetailPopup.focus();
					
					var find_string = row.TEXT; // the searched word
					
					var eiPopOption = 2;
					textDetailPopup.document.getElementById("focusValue").value = find_string;
					textDetailPopup.detailTextFindFocus(eiPopOption);	// child window function
				} */
				// 200401 hgJeon popup window end
				
			});
			
			  
			  // 마우스 오른쪽 버튼 클릭
			  grid<c:out value="${param.uuid }" />.onContextMenu.subscribe(function (e) {
			  	e.preventDefault();
			  	var cell = grid<c:out value="${param.uuid }" />.getCellFromEvent(e);
			  	selRow = cell.row;
			  	$("#contextMenu a:eq(1)").hide();
			  	$("#contextMenu a:eq(2)").hide();
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
				$content.find("#rowCount").text(args.current);
			    //grid<c:out value="${param.uuid }" />.updateRowCount();
			    grid<c:out value="${param.uuid }" />.render();
			  });
			// 로우 카운트 변경
			  dataView<c:out value="${param.uuid }" />.onRowsChanged.subscribe(function(e,args) {
				  grid<c:out value="${param.uuid }" />.invalidateRows(args.rows);
			      grid<c:out value="${param.uuid }" />.render();
			  });
			  dataView<c:out value="${param.uuid }" />.onPagingInfoChanged.subscribe(function (e, pagingInfo) {
				  //console.log("onPagingInfoChanged :"+JSON.stringify(pagingInfo));
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
		console.log(colValue);
		switch(colName) {
			case "HOST":
		    	$content.find("input[name=host]").val(colValue);
		        break;
		    case "PROCESS":
		    	$content.find("#eiProcessList").val(colValue).prop("selected", true);
		    	$content.find("#inputProcessName").val(colValue);
		        break;
		    default:
		}
	}
	
	// 201228 hgJeon FAB, LogType 별 ProcessList 기능 추가
	function getSelectProcessList() {

		var selLogType = $content.find(":checkbox[name^=logType]:checked").map(function(){return $(this).val(); }).get();
		var selFabType = $content.find(":checkbox[name^=eiFab]:checked").map(function(){return $(this).val(); }).get();
		
		/* console.log("selLogType", selLogType);
		console.log("selFabType", selFabType); */
		
		var param = {"selectType":selLogType, "selectFab": selFabType};
		var urlProcessName = "filter/ajax/getSelectProcessList.do";	 
		
		$.ajax({
            url: urlProcessName,
            type:'post',
            data: param,
            traditional: true,
            success:function(data){
            	var $select = $content.find(".eiProcessList");
            	$select.empty();
            	$select.append("<option value='ALL' selected='selected' >ALL</option>");
            	for(var i in data.list){ // machine name list  셀렉트 생성
					var $opt = $("<option value=''></option>");  
					$opt.attr("value" , data.list[i].PROCESS);
					$opt.text(data.list[i].PROCESS);
					$select.append($opt);
            	}
            	$content.find(".eiProcessList").append("<option value='write'>직접입력</option>");
            }
	    });
	}
	// 20220621	X0122410	fabSite 추가
	function getProcessList(fabSite){
		
		setTimeout(function(){
			var urlProcessName = "filter/ajax/getProcessList.do";	 
			var param = { "fabSite":fabSite }; // 파라메터
			$.ajax({
	            url: urlProcessName,
	            type:'get',
	            data: param,
	            dataType: 'json',
	            success:function(data){
	            	var result = data[0];
	            	$.each(result, function(index, value){
	            		$content.find(".eiProcessList").append(""+
	            		"<option value='"+value.PROCESS+"'>"+value.PROCESS+"</option>"); 
	            	}); 
	            	$content.find(".eiProcessList").append("<option value='write'>직접입력</option>"); 
	            }
		    });
		}, 1200);
	}
	
	// 조회
	function getLogList<c:out value="${param.uuid }" />(page){
		if(!chkValidate()) return;
		popupFlag = false;
		$content.find("#searchBtn").addClass('disabled');
		$content.find("#searchBtn").parent().css('display','none');
		$content.find("#cancelBtn").parent().css('display','block');
		showLoadingbar($("#list<c:out value="${param.uuid }" />"));
		//$content.find("#SECSII_List").empty(); //secsList 비우기
		//$content.find("#SECS_II").empty(); //secsTextarea 비우기
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
		
		if(textDetailPopup == null || (textDetailPopup.closed)){	}
		else{popupFlag = true;}	// 200714 hgJeon 설정 변경 시 popup data reload flag 추가
		$content.find("#fabSite").val($content.find('input[name="rdoFabSite"]:checked').val());
		var param = $content.find("#searchForm").serializeObject();
		console.log("param : ", param);
		var url = "<c:url value='/ei/ajax/getEiLogList.do' />";
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
							
							setPagerState(result.rows);
							loadingbarFadeOut();
							grid<c:out value="${param.uuid }" />.resizeCanvas();
							$content.find("#cancelBtn").parent().css('display','none');
							$content.find("#searchBtn").parent().css('display','block');
								
							$content.find("#searchBtn").removeClass('disabled');
		            	}else{ // 20180712 data 없을때 loadingbar 수정
		            		loadingbarFadeOut(); // 로딩바 숨김
		            		
		            		$content.find("#cancelBtn").parent().css('display','none');
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
		grid<c:out value="${param.uuid }" />.resizeCanvas();
	});
	
	// Filter View 보이기
	$content.find("#unfold_filter_view").click(function(){
		$content.find("#unfold_filter_view_wrap").css("display", "none");
		$content.find("#filter_view").css("display", "");
		grid<c:out value="${param.uuid }" />.resizeCanvas();
	});
	
	// 200305 hgJeon TEXT 검색시 and, or 선택적용
	$content.find("#eiTextConditionCheckBox").click(function(){
		var textCondition = document.getElementById("eiTextConditionCheckBox");
		if(textCondition.checked) {
			$content.find("#AndOr_selectLabel").text("or");
		}else{
			$content.find("#AndOr_selectLabel").text("and");
		}
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