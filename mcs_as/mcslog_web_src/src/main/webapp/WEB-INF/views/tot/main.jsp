<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ include file="/WEB-INF/views/common-taglib.jspf"%>
	<div id="lay_container">
		<div id="lay_contents">
            <!-- Tab master -->
            <div class="tab_master" style="display:">
				<div class="tab_master_wrap">
					<div class="tab_right">
						<a class="btn_txt btn_tab" id="dropDownBtn" style="display: none">
							 <span class="txt">>></span>
						</a>
						 <div class="dropdown-content" id="dropdownArea">
						 </div>
						 <a class="btn_tab btn_tab_left">
							<span class="tab_ico tab_ico_left"></span>
						</a>
						<a class="btn_tab btn_tab_right">
							<span class="tab_ico tab_ico_right"></span>
						</a>
						<a class="btn_txt btn_tab" id="tabCloseAll">
							<span class="txt">Close All</span>
						</a>
						<a class="btn_txt btn_tabLangFlag" id="" href="/tot/main?lang=ko">
							<img src="/styles/images/flag/korea_flag_30_20.png" style="<c:if test="${fn:indexOf(location,'zh')>-1}">opacity: 0.3; filter: alpha(opacity=30);</c:if>"/>
						</a>
						<!--<a class="btn_txt btn_tabLangFlag" id="" href="/tot/main?lang=en">
							<img src="/styles/images/flag/usa_flag_30_20.png" style="<c:if test="${fn:indexOf(location,'en')==-1}">opacity: 0.3; filter: alpha(opacity=30);</c:if>"/>
						</a>-->
						<a class="btn_txt btn_tabLangFlag" id="" href="/tot/main?lang=zh">
							<img src="/styles/images/flag/china_flag_30_20.png" style="<c:if test="${fn:indexOf(location,'zh')==-1}">opacity: 0.3; filter: alpha(opacity=30);</c:if>"/>
						</a>
						<!-- <a href="javascript:openSetting();" style="color:#ffffff">
							<i class="setting icon"></i>
						</a> -->
						<%-- <select class="jqForm"  id="fabType" name="fabType" onchange="location = this.value;" >
                            <option value="javascript:movePage('<c:url value="/totFAB/totalM14FabLogList.do" />');" >M14</option>
                            <option value="javascript:movePage('<c:url value="/tot/totalLogList.do" />');" selected="selected">M14A</option>
                            <option value="#">M14B</option>
                        </select> --%>
					</div>
					<div class="tab_list_wrap">
                        <ul class="tab_list" id="tabList">
                        </ul>
                    </div>
                </div>
            </div>
			<!--// Tab master -->
			<div id="contentList">
			</div>
    </div>
</div>
<div id="contextMenu" class="dropdown-content" style="display:none;position:absolute">						 
  <a href="#" data="01" style="font-size: 13px">Copy selected items to clipboard</a>
  <a href="#" data="02" style="font-size: 13px">Copy checked items to clipboard</a>
  <a id="copyGridColumn" href="#" data="03" style="font-size: 13px">Copy selected column</a>
</div>
<script type="text/javascript">
	var selRow = null;  //  선택한 그리드 row 인덱스
	var curUuid = null; //  현재 탭 id
	$(document).ready(function(){
	     
		// 탭 드롭다운 이벤트 ( 탭 표시 공간 초과시 탭 선택 메뉴 )
	    $("#dropDownBtn").click(function(e){
    		if($("#dropdownArea").is(":visible")){   				// 숨김
	    		$("#dropdownArea").hide();
	    	}else{												    // 보임
	    		drawDropDown();
	     		$("#dropdownArea").show();
	    	}
	    });
		
		// 페이징 reload type 값 변경 이벤트(reload/append)
		// slickGridPager.jsp 
		$("body").on("click","#reload",function(){
			var value = $(this).val();
			var page = $content.find('#page').val();
			if(value == "01"){  		// 01 : reload, 02 : append
				if( page != 1 )         // 첫번째 페이지에서는 이전페이지 버튼 비활성
					$content.find(".ui-icon-seek-prev").removeClass("ui-state-disabled");
			}else{					    // append
				$content.find(".ui-icon-seek-prev").addClass("ui-state-disabled");
			}
		});
		
	     // 탭선택 드롭다운 메뉴클릭 이벤트
	     $("#dropdownArea").on("click","a" ,function(){
	    	$("#dropdownArea").hide();
			var title = $("#tab_"+$(this).attr("data-uuid")).find(".tab_link").text();
	    	$("#tab_"+$(this).attr("data-uuid")).remove();
	    	var tabHtml = drawTab($(this).attr("data-uuid") , title);
	    	$("#tabList").prepend(tabHtml);
	    	 moveTab($(this).attr("data-uuid"));
	     });

	     // 메인 페이지 GNB / TAB 관련 공통
	     gnbmenuSet('.gnb_top_basic');
	     gnbmenuSet('.gnb_top_basic_light');
	     tabMove('.tab_master');
	     tab_view('.tab_master', false, false);
	     tab_view('#tree_set_tab', true, false);
	     
	     // 탭 클릭 이벤트
	     $('body').on('click', '.tab_list_wrap .tab_list .tab_item', function() {
	    	 console.log("탭이벤트 !!"+$(this).attr("id"));
	    	 moveTab($(this).attr("id").substring(4));
	     });
	     
	     // reset 버튼 클릭 이벤트
	     $("body").on("click","#resetBtn",function(){
	    	 reset();
	     });
	     
	     // 라벨 클릭 이벤트(필터에 라벨 클릭시 해당 체크박스 객체 클릭 이벤트 바인딩)
	     $("body").on("click","label",function(e){
	    	 console.log("label");
	    	 var $target = $(this).prev(); // 체크박스 객체..
	    	 if($target.is(":checkbox , :radio")){ 
	    	 	e.preventDefault();  			  		// 이벤트 중복 방지
	    	 	$target.click();        			    // 체크박스 클릭 이벤트
	    	 }
	     });
	     
	     // 검색 조건 fold / open
	     $("body").on("click",".add.square.icon , .minus.square.icon",function(){
	    	 if(!$(this).hasClass("fixed")){
				if($(this).hasClass('add')){	// folder close
					$(this).parent().parent().parent().find("tr:gt(0)").slideDown("slow");
					$(this).removeClass("add").addClass("minus");
				}else{									// folder open
					$(this).parent().parent().parent().find("tr:gt(0)").slideUp("slow");
					$(this).removeClass("minus").addClass("add");
				}
	    	 }
		 });
	     
	     // contextMenu 메뉴 클릭 이벤트(클립보드에 해당 데이터 적재를 위한 메뉴/그리드에서 우클릭시 활성화/활성화 뒤 해당 메뉴에서 클릭 이벤트 발생시)
	     // copyToClipboard(text)에 전달할 text 생성작업함수
	     $("#contextMenu").click(function (e) {
			    if (!$(e.target).is("a")) {  
			      return;
			    }
			    var row = $(this).data("row");
			    var grid = eval("grid"+curUuid);
			    var isSel = grid.getColumns()[0].field;
			    var selMenu = $(e.target).attr("data");
			    var selectedIndexes = [];
			    if(selMenu == "01"){   			  // 한개 행 선택(01 : Copy selected items to clipboard, 02 : Copy checked items to clipboard)
			    	selectedIndexes.push(selRow); // selRow(그리드내에서 해당 행 선택시 할당되는 전역변수)
			    }else{						      // 다수 행 선택
			    	selectedIndexes = eval("grid"+curUuid).getSelectedRows();	//slickGrid 내장함수
			    	
			    	if(selectedIndexes.length == 0){
			    		selectedIndexes.push(selRow);
			    	}
			    	
			    }
			    
			    var text = "";		    
			    if(isSel == "sel"){   // 멀티행 선택 그리드 ( 로그조회 )
					 var keys = [];
					 for(i=0 ; i < selectedIndexes.length ; i++){  // 선택된 row의 key값 배열 생성 ex : [key1 , key2 , ...]
					 	var idx = selectedIndexes[i];
					 	var data = eval("data"+curUuid)[idx];
					 	keys.push(data["key"]);					   // data["key"]는 그리드내에 Hidden Value
					 }
					 var tempMap = {};
					 getLogDetailGroup(keys,function(result){      // XML , SECSII 상세조회 ajax 호출
					 	console.log("result : "+result.list.length);
					 	for(var idx in result.list){						   // temp map 생성 {  key : key , value : {XML , SECSII} }
					 		var row = result.list[idx];
					 		var info = {"XML" : "" ,"SECSII":"" };
					 		if(row != null ){
					 			if(row.key != null && row.key != ""){
					 				info.XML = (row.XML==null?"":row.XML);
					 				info.SECSII = (row.SECSII==null?"":row.SECSII);
					 				tempMap[row.key] = info;
					 			}
					 		}
					 	}
					 	
					 	for(i=0 ; i < selectedIndexes.length ; i++){ // 선택된 row data 에 XML , SECSII 값 append 및 plain text 생성
					 		var idx = selectedIndexes[i];
							var data = eval("data"+curUuid)[idx];
							var skey = tempMap[data["key"]];
							data["XML"] = "";
							data["SECSII"] ="";
							if(skey != null && skey != ""){  // temp map 과 row data 의 key 값 매칭 시 XML , SECSII append
								data["XML"] = skey.XML;
								data["SECSII"] = skey.SECSII;
							}
							var tranData = "";
							for (var key in data) {	
					    		if(key != "key" && key != "_time"){  // row data 에 불필요 값 삭제 
					    	    	var value = data[key];
					    	    	tranData += key+"="+value+", ";
					    		}
					    	}
					    	text += "log{"+tranData+"}\r\n";  // plain text 생성
						}
					 });
			    }else{  // 단일행 선택 그리드 ( 로그조회제외 )
			    	for(i=0 ; i < selectedIndexes.length ; i++){  // 선택된 row data plain text 생성
						var idx = selectedIndexes[i];
						var data = eval("data"+curUuid)[idx];  // 선택된 row data 
						var tranData = "";
						for (var key in data) {
				    		if(key != "key" && key != "_time"){ // row data 에 불필요한(key, _time) field값 제외
				    	    	var value = data[key];
				    	    	tranData += key+"="+value+", ";
				    		}
				    	}
				    	text += "log{"+tranData+"}\r\n"; // plain text 생성
					}
			    }
			    console.log("text["+text+"]");
			   	copyToClipboard(text);  // 클립보드 복사
		 });
	     
	     // 탭 종료 버튼 클릭 이벤트
	   	 $('body').on('click', '.tab_close' , function(event) {
	   		event.preventDefault();
	    	var nextTabId = $(this).parent().next().attr("id");  // 다음탭 id
	    	var prevTabId = $(this).parent().prev().attr("id");  // 이전탭 id
	    	console.log("탭종료 이벤트 next["+nextTabId+"] , prevTabId["+prevTabId+"]")
	    	var contentId = "body_"+$(this).parent().attr("id").substring(4); // 현재 탭 content id 가져오기
	     	if (nextTabId !== undefined){    // 다음 탭 존재시, 다음탭 으로 이동 ( 1순위)
	     		moveTab(nextTabId.substring(4));
	     	}else{
	     		if(prevTabId !== undefined){ // 이전탭 존재시, 이전 탭으로 이동 ( 2순위)
	     			moveTab(prevTabId.substring(4));
	     		}
	     	}
	     	
	    	$("#"+contentId).remove();   // 현재탭 content body 삭제
	     	$(this).parent().remove();   // 현재탭 삭제
	     	eval("destroy"+$(this).parent().attr("id").substring(4))(); // global 변수 memory 회수
	     });
	     
	     // 이전 탭 이동
	     $(".btn_tab_left").click(function(){
	    	 var contentId = $content.attr("id").substring(5);
	    	 var $tabId = $("#tab_"+contentId);
	    	 var prevTabId = $tabId.prev().attr("id");
	    	 if (prevTabId !== undefined){ // 이전탭으로 이동
	    	 	moveTab(prevTabId.substring(4));
	    	 }
	     });
	     
	     // 다음 탭 이동
	     $(".tab_ico_right").click(function(){
	    	 var contentId = $content.attr("id").substring(5);
	    	 var $tabId = $("#tab_"+contentId); 
	    	 var nextTabId = $tabId.next().attr("id");
	    	 if (nextTabId !== undefined){ // 다음 탭으로 이동
		    	 	moveTab(nextTabId.substring(4));
		     }
	     });
	     
	     //모든탭 종료
	     $("#tabCloseAll").click(function(){
    		$(".contents_wrap").each(function(){ // 모든 content body 삭제
				var contentId = this.id;	    
				$("#"+contentId).remove();
		     	eval("destroy"+contentId.substring(5))();
    		});
			$('.tab_item').remove(); // 모든 탭 삭제
			dropDownMenu(); 
	     });
	     
	     // 엔터키 이벤트
	     $("body").on("keypress",":text",function(e){
			console.log(e.which);
			if (e.which == 13) {/* 13 == enter key@ascii */
				$content.find("#searchBtn").trigger("click");
			}
		 });
	     // 페이지 오픈
	     movePage("<c:url value="/tot/totalLogList.do" />");
	});
	
	// Time Range > prev 클릭
	$(document).on("click",".prevTime",function(){
		var interval = getTimeRangeDiff();   //  시작시간 , 종료시간 시간차이
		console.log("시간차이  "+ interval);
		
		setTimeRange("prev" , interval);     //  시간차 만큼 전으로 이동
	});
	
	// Time Range > next 클릭
	$(document).on("click",".nextTime",function(){
		var interval = getTimeRangeDiff();   //  시작시간 , 종료시간 시간차이
		setTimeRange("next" , interval);     //  시간차 만큼 후로 이동
	});
	
	// 로그조회 XML , SECSII  상세조회
	function getLogDetailGroup(key,func){
		var url = "<c:url value='/tot/ajax/getLogDetailGroup.do' />";	 
		$.ajax({
	          url: url,
	          type:'post',
	          data:{"key":key},
	          async:false,       // 비동기 비활성
	          traditional: true, // 배열전송 활성
	          success:function(result){
	           	if(func) func(result);
	       	  }
		});
	}
	
	// 탭 이동
    function moveTab(tabId){
		
		var contentId = "body_"+tabId  // content id 
		var $body = $("#"+contentId); // 탭 body 객체
		if($body.length){ // 존재시,
			curUuid = tabId;
			$('.contents_wrap').hide(); // 모든 탭 body 숨김
			$("#"+contentId).show();  //  선택한 탭만 보임
			$('.tab_item').removeClass("selected");  // 모든 탭 선택 해제
			$("#tab_"+tabId).addClass("selected");  // 선택한 탭만 선택
			$content = $body;   
			dropDownMenu(); 
			//var tabLeft = $("#tab_"+tabId).offset().left;
		}
	}
	
   // 환경설정 팝업
    function openSetting(){
    	var url = "<c:url value='/common/pop/settingPop.do' />";
    	openPopup(url , 600 , 200,function(param){
    	});				
    }
   
    /* var doit;		200721 hgJeon resize function 통합기능 
	window.onresize = function(){
	  clearTimeout(doit);
	  doit = setTimeout(resizedw, 1000);
	  console.log("main.jsp");
	  console.log("uuid : ", curUuid);
	  //grid+curUuid.resizeCanvas();
	}; */
	
   
</script>