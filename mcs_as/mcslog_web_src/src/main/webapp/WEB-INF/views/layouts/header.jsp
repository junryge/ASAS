<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ include file="/WEB-INF/views/common-taglib.jspf"%>
<%@ include file="/WEB-INF/views/common-header.jspf"%>
<div id="lay_header">
	<div class="gnb_top_basic">
	    <div class="gnb_top">
	        <div class="gnb_top_wrap">
	            <div class="gnb_left" >
	            	<img src="<c:url value="/styles/images/icon/top_logo.png" />" style="position:absolute; left:9px; top:-3px;width: 100px;height:52px" />
	                <h1>
	                    <a href="javascript:refresh();" >
							<span class="logo_txt" style="position:absolute; left:112px; top:16px; color: #fff;font-family:'arial black','Malgun Gothic' !important; font-weight:bold; font-size:27px; line-height:1.33em; display:inline-block; vertical-align:middle;">MCSLOG</span>
	                    </a>
	                </h1>
	                <b style="position: absolute; left: 250px; top: 35px; color: rgb(255, 255, 255);">Web</b>
	            </div>
	            <ul class="gnb">
	                <li class="gnb_list">
	                    <a href="javascript:movePage('<c:url value="/alarm/alarmReportLogList.do" />');" class="gnb_link"><span class="name">Alarm</span></a>
	                    <!-- GNB Sub -->
	                    <div class="gnb_sub_3depth_full_dark gnb_sub">
	                        <div class="gnb_sub_wrap">
	                            <div class="menu_tit"> 
	                                <div class="tit">Alarm</div>
	                                <div class="desc"></div>
	                            </div>
	                            <ul class="gnb_2depth">				
	                                <li class="gnb_2depth_list" style="width:20%">
	                                    <div class="gnb_2depth_box">
	                                        <a href="javascript:movePage('<c:url value="/alarm/alarmReportLogList.do" />');" class="gnb_2depth_link">
	                                            <span class="name">Alarm</span>
	                                        </a>
	                                        <ul class="gnb_3depth">
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/alarm/alarmReportLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.alarmReportLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                        </ul>
	                                    </div>	
	                                </li>
	                            </ul>
	                        </div>
	                    </div>
	                    <!-- //GNB Sub -->
	                </li>
	                <li class="gnb_list">
	                    <a href="javascript:movePage('<c:url value="/res/machineLogList.do" />');" class="gnb_link"><span class="name">Resource</span></a>
	                    <!-- GNB Sub -->
	                    <div class="gnb_sub_3depth_full_dark gnb_sub">
	                        <div class="gnb_sub_wrap">
	                            <div class="menu_tit"> 
	                                <div class="tit">Resource</div>
	                                <div class="desc"></div>
	                            </div>
	                            <ul class="gnb_2depth">				
	                                <li class="gnb_2depth_list" style="width:20%">
	                                    <div class="gnb_2depth_box">
	                                        <a href="javascript:movePage('<c:url value="/res/machineLogList.do" />');" class="gnb_2depth_link">
	                                            <span class="name">Resource</span>
	                                        </a>
	                                        <ul class="gnb_3depth">
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/res/machineLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.machineLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/res/portLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.portLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/res/shelfLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.shelfLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/res/craneLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.craneLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/res/vehicleLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.vehicleLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/res/storageLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.storageLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                        </ul>
	                                    </div>	
	                                </li>
	                            </ul>
	                        </div>
	                    </div>
	                    <!-- //GNB Sub -->
	                </li>
	                <li class="gnb_list">
	                    <a href="javascript:movePage('<c:url value="/mat/carrierLocLogList.do" />');" class="gnb_link"><span class="name">Material</span></a>
	                    <div class="gnb_sub_3depth_full_dark gnb_sub">
	                        <div class="gnb_sub_wrap">
	                            <div class="menu_tit"> 
	                                <div class="tit">Material</div>
	                                <div class="desc"></div>
	                            </div>
	                            <ul class="gnb_2depth">				
	                                <li class="gnb_2depth_list" style="width:20%">
	                                    <div class="gnb_2depth_box">
	                                        <a href="javascript:movePage('<c:url value="/mat/carrierLocLogList.do" />');" class="gnb_2depth_link">
	                                            <span class="name">Material</span>
	                                        </a>
	                                        <ul class="gnb_3depth">
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/mat/carrierLocLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.carrierLocLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                        </ul>
	                                    </div>	
	                                </li>
	                            </ul>
	                        </div>
	                    </div>
	                </li>
	                <li class="gnb_list">
	                    <a href="javascript:movePage('<c:url value="/tran/returnLogList.do" />')" class="gnb_link"><span class="name">Transport</span></a>
	                    <div class="gnb_sub_3depth_full_dark gnb_sub">
	                        <div class="gnb_sub_wrap">
	                            <div class="menu_tit"> 
	                                <div class="tit">Transport</div>
	                                <div class="desc"></div>
	                            </div>
	                            <ul class="gnb_2depth">				
	                                <li class="gnb_2depth_list" style="width:20%">
	                                    <div class="gnb_2depth_box">
	                                        <a href="javascript:movePage('<c:url value="/tran/returnLogList.do" />')" class="gnb_2depth_link">
	                                            <span class="name">Transport</span>
	                                        </a>
	                                        <ul class="gnb_3depth">
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/tran/returnLogList.do" />')" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.returnLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/tran/returnJobLogList.do" />')" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.returnJobLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/tran/returnCmdLogList.do" />')" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.returnCmdLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/tran/returnJobFailLogList.do" />')" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.returnJobFailLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/tran/returnCmdFailLogList.do" />')" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.returnCmdFailLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/totNew/totalNewLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.totalNewLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                        </ul>
	                                    </div>	
	                                </li>
	                            </ul>
	                        </div>
	                    </div>
	                </li>
	                <%-- <li class="gnb_list">
	                	<a href="javascript:movePage('<c:url value="/tot/dashboard/elapsedAnalysis.do" />');" class="gnb_link"><span class="name"><spring:message code="site.header.dashboard" text="default text" /></span></a>
	                    <div class="gnb_sub_3depth_full_dark gnb_sub">
	                        <div class="gnb_sub_wrap">
	                            <div class="menu_tit"> 
	                                <div class="tit"><spring:message code="site.header.dashboard" text="default text" /></div>
	                                <div class="desc"></div>
	                            </div>
	                            <ul class="gnb_2depth">				
	                                <li class="gnb_2depth_list" style="width:20%">
	                                    <div class="gnb_2depth_box">
	                                        <a href="javascript:movePage('<c:url value="/tot/dashboard/elapsedAnalysis.do" />');" class="gnb_2depth_link">
	                                            <span class="name"><spring:message code="site.header.dashboard" text="default text" /></span>
	                                        </a>
	                                        <ul class="gnb_3depth">
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/tot/dashboard/elapsedAnalysis.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.header.dashboard.elapsedAnalysis" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/tot/dashboard/compressAnalysis.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.header.dashboard.compressAnalysis" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/tot/dashboard/monitor.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.header.dashboard.monitor" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                        </ul>
	                                    </div>	
	                                </li>
	                            </ul>
	                        </div>
	                    </div>
	                </li> --%>
	                <li class="gnb_list">
	                    <a href="javascript:movePage('<c:url value="/tot/totalLogList.do" />');" class="gnb_link"><span class="name"><spring:message code="site.logList" text="default text" /></span></a>
	                    <div class="gnb_sub_3depth_full_dark gnb_sub">
	                        <div class="gnb_sub_wrap">
	                            <div class="menu_tit"> 
	                                <div class="tit"><spring:message code="site.logList" text="default text" /></div>
	                                <div class="desc"></div>
	                            </div>
	                            <ul class="gnb_2depth">				
	                                <li class="gnb_2depth_list" style="width:20%">
	                                    <div class="gnb_2depth_box">
	                                        <a href="javascript:movePage('<c:url value="/tot/totalLogList.do" />');" class="gnb_2depth_link">
	                                            <span class="name"><spring:message code="site.logList" text="default text" /></span>
	                                        </a>
	                                        <ul class="gnb_3depth">
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/tot/totalLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.header.tot.totalLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/secs/secsLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.secsLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                            <li class="gnb_3depth_list">
	                                                <a href="javascript:movePage('<c:url value="/ei/eiLogList.do" />');" class="gnb_3depth_link">
	                                                    <span class="gnb_basic_bu gnb_basic_bu_01"></span>
	                                                    <span class="name"><spring:message code="site.eiLogList" text="default text" /></span>
	                                                </a>
	                                            </li>
	                                        </ul>
	                                    </div>	
	                                </li>
	                            </ul>
	                        </div>
	                    </div>
	                </li>
	            </ul>
	        </div>
	    </div>
	</div>
</div>
<form id="movePageForm" name="movePageForm" method="post" >
</form>
<script type="text/javascript">
	// 2021.03.25	X0122410 : FabCode를 com.skhynix.supply.common.Common.sFAB_SITE 를 이용해서 렌더링
	// var FabCode = 'IC';		// 200506 hgJeon FAB 설정 추가 ex) M15, M11, C2 등...
	var FabCode = '<%=com.skhynix.supply.common.Common.sFAB_SITE%>';
	
	//20220727	X0122410	FAB통합작업으로 FAB을 노출하지 않음, site.logList -> site.header.tot.totalLogList
	//var tabTitle = {"totalLogList": FabCode + " <spring:message code="site.logList" text="default text" />"
	var tabTitle = {"totalLogList":"<spring:message code="site.header.tot.totalLogList" text="default text" />" 
			               ,"carrierLocLogList":"<spring:message code="site.carrierLocLogList" text="default text" />"
			               ,"returnLogList":"<spring:message code="site.returnLogList" text="default text" />"
			               ,"returnJobLogList":"<spring:message code="site.returnJobLogList" text="default text" />"
			               ,"returnCmdLogList":"<spring:message code="site.returnCmdLogList" text="default text" />"
			               ,"returnJobFailLogList":"<spring:message code="site.returnJobFailLogList" text="default text" />"
			               ,"returnCmdFailLogList":"<spring:message code="site.returnCmdFailLogList" text="default text" />"
			               ,"alarmReportLogList":"<spring:message code="site.alarmReportLogList" text="default text" />"
			               ,"machineLogList" : "<spring:message code="site.machineLogList" text="default text" />"
			               ,"portLogList":"<spring:message code="site.portLogList" text="default text" />"
			               ,"shelfLogList":"<spring:message code="site.shelfLogList" text="default text" />"
			               ,"craneLogList":"<spring:message code="site.craneLogList" text="default text" />"
			               ,"vehicleLogList":"<spring:message code="site.vehicleLogList" text="default text" />"
			               ,"storageLogList":"<spring:message code="site.storageLogList" text="default text" />"
			               ,"totalNewLogList":"<spring:message code="site.totalNewLogList" text="default text" />"
			               ,"elapsedAnalysis":"<spring:message code="site.header.dashboard.elapsedAnalysis" text="default text" />"
			               ,"compressAnalysis":"<spring:message code="site.header.dashboard.compressAnalysis" text="default text" />"
			               ,"undefined":"undefined"
			               ,"secsLogList":"<spring:message code="site.secsLogList" text="default text" />" // 170817 페이지탭 추가
			               ,"eiLogList":"<spring:message code="site.eiLogList" text="default text" />" // 200324 페이지탭 추가
						  };
	
	var $content = $('.contents_wrap:visible');
	
	var popupURL = "<c:url value='/ei/pop/textAreaPop.do' />";		// 200506 hgJeon popup URL 전역변수 설정
	var popupFlag = false;
	//화면별 고유 ID 부여
	$.guid = 0;
	
	// 탭생성
	function createTab(title){
		var uuid = $.guid++;				//Tab 생성시, 고유 uuid 부여
		var tabHtml =drawTab(uuid,title);	//html 형태의 Tab 할당
		$("#tabList").append(tabHtml);		//Tab 삽입
		return uuid;						//uuid 리턴
	}
	
	// 탭 그리기
	function drawTab(uuid , title){
		var tabHtml = '<li class="tab_item" id="tab_'+uuid+'">';
		tabHtml += '<a href="#" class="tab_link">'+title+'</a>';
		tabHtml += '<a href="#" class="tab_close">';
		tabHtml += '   <span class="blind"><spring:message code="site.common.button.close" text="default text" /></span>';
		tabHtml += '</a>';
		tabHtml += '</li> ';
		return tabHtml;
	}
	
	// 페이지 이동
	function movePage(url){
		//console.log("url : " , url);
		var lastItem = url.split("/").pop(-1);
		var key = lastItem.substr(0,lastItem.indexOf(".do"));		
		var title = tabTitle[key];							//tabTitle 가져오기
		var start = url.indexOf("?carrier=");				//carrier를 추출하기 위한 index 추출
		if(start != -1){
			var end = url.indexOf("&");						
			var carrier = url.substring(start+9 , end);		//carrier 추출
			title = carrier+"-"+title;						//title : carrier-title 형태 	
		}
		if(title == undefined ){
			title = key;
		}
		//console.log(title);		
		console.log("url : " + url + " , title : " + title);
		var uuid = createTab(getTitle(title));
		$.ajax({
	            url: url,
	            type:'post',
	            dataType : 'html' ,							//html형태로 데이터를 가져옴, 페이지 전환없이 ajax로 화면 처리
	            data:{"uuid":uuid},							//전송시 uuid를 param에 담아 송부, uuid가 리턴될 jsp페이지내 c: 태그로 출력되어 페이지 고유번호 지정됨(controller를 거쳐서 돌아오게 됨)
	            success:function(data){
	            	//console.log("data_server : ", data);
	            	$("#contentList").append(data);			//전송되어 온 data를 main.jsp에 #contentList에 삽입
	            	moveTab(uuid);							//moveTab(uuid) 함수를 통해 #contentList(div 태그) 담긴 모든 다른 페이지들을 숨기고, uuid를 가진 페이지를 보여주고, 그 페이지로 이동
	            }
	     });
		setTimeout(function() {
			resizedw();
			}, 2500);
	}
	
	// title 생성
	function getTitle(title){
		var i = 0;											//tabTitle(i)의 형태로 tabTitle이 생성되므로 i를 serial 하게 구해서 tabTitle을 부여
		$("#tabList .tab_item").each(function(){			//모든 탭을 돌면서
			var curTitle = $(this).find(".tab_link").text();
			if(curTitle.indexOf(title) != -1){				//해당 title명을 가진 탭이 존재한다면
				if(curTitle.indexOf("(") != -1){			//title명에 "("를 포함하고 있다면
					var nSeq = Number(curTitle.substring(curTitle.indexOf("(")+1,curTitle.length-1)); // "tabTitle(nSeq)" 에 탭의 일련번호를 가져옴
					if(nSeq >= i)							//nSeq > 0 이면
						i = nSeq;							
				}else{										//title명에 "("를 포함하지 않는다면	
					i++;
				}
			}
		});
		if(i!=0){
			i++;											//기존 tabTitle에 동일 tabTitle을 가질 경우, 시리얼 번호를 찾아서 그것보다 하나 더해진 시리얼 번호 부여
			title = title +"("+i+")";						
		}	
		return title;
	}
</script>