<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ include file="/WEB-INF/views/common-header.jspf"%>
<link rel="stylesheet" type="text/css" href="${pageContext.request.contextPath }/styles/css/popup.css"/>
<%@ include file="/WEB-INF/views/common-taglib.jspf"%>
<div id="popup14" class="pop_window">
    <div class="pop_tit_wrap">
        <h2 class="pop_tit">Reason</h2>
        <a href="#" class="close_area">
            <span class="pop_btn pop_btn_close">
                <span class="blind"><spring:message code="site.common.button.popupclose" text="팝업 닫기" /></span>
            </span>
        </a>
    </div>
    <div class="tab_contents_wrap" rel="contentsTab">
    <div class="tab_contents" id="contentsTab_01">
        <div class="section_margin_s">
        <div class="lay_item vert">
            <div class="lay_item_box">
                <div class="lay_item_left">
                    <!-- Sub Title -->
                    <div class="opt_tit" style="padding: 7px 7px">
                        <div class="opt_tit_left">
                            <div class="elmt">
                                <span class="opt_tit_bu opt_tit_bu_01"></span>
                                <span class="txt">Reason</span>
                            </div>
                        </div>
                    </div>
                    <div class="scroll_box" style="padding:10px 10px">
                        <div class="board_list">
                            <table class="board_list_table fixedHeader" id="reasonTable" summary="해당 표에 대한 설명을 적어주세요.">
                                <caption><spring:message code="site.common.summary.desc01" text="Write a description." /></caption>
                                <colgroup>
                                    <col width="40"/>
                                    <col width="500"/>
                                </colgroup>
                                <thead style="float: left">
                                    <tr class="board_list_row">
                                        <th class="board_list_head" scope="col" style="width:40px">
                                            <input type="checkbox" class="jqForm" name="chkAll" id="chkAll" />
                                        </th>
                                        <th class="board_list_head" scope="col" style="width:540px">reason</th>
                                    </tr>
                                </thead>
                                <tbody id="reasonList" style="float: left">
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <!-- //Vertical Table -->
                </div>
                <div class="lay_item_btn"><!-- 해당 기능이 필요없을 경우 삭제 -->
                    <div class="lay_item_group">
                        <a href="#" class="btn_fix btn_arr_left"><span class="blind">arrow left</span></a>
                        <a href="#" class="btn_fix btn_arr_right"><span class="blind">arrow right</span></a>
                    </div>
                </div>
                <div class="lay_item_right">
                 <!-- Sub Title -->
                <div class="opt_tit" style="padding: 7px 7px">
                    <div class="opt_tit_left">
                        <div class="elmt">
                            <span class="opt_tit_bu opt_tit_bu_01"></span>
                            <span class="txt">Selected</span>
                        </div>
                    </div>
                </div>
                <!-- //Sub Title -->
                    <!-- Board List -->
                    <div class="scroll_box" style="padding:10px 10px">
                        <div class="board_list" >
                            <table class="board_list_table fixedHeader" id="reasonTable2" summary="해당 표에 대한 설명을 적어주세요.">
                                <thead  style="float: left">
                                    <tr class="board_list_row">
                                        <th class="board_list_head" scope="col" style="width: 40px">
                                            <input type="checkbox" class="jqForm" name="chkAll2" id="chkAll2"/>
                                        </th>
                                        <th class="board_list_head" scope="col" style="width: 540px">reason</th>
                                    </tr>
                                </thead>
                                <tbody id="reasonList2" style="float: left">
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <!-- //Vertical Table -->
                </div>
            </div>
            <div class="opt_tit_right">
                 <div class="elmt">
                     <div class="mini ui primary button"  onclick="window.close();" style="width:75px;float: right;margin-right: 10px;float:right">
						<i class="remove icon"></i><spring:message code="site.common.button.close" text="닫기" />
					</div>
					<div class="mini ui primary button"  onclick="apply();" style="width:75px;float: right;margin-right: 10px;float:right">
						<i class="checkmark icon"></i><spring:message code="site.common.button.apply" text="apply" />
					</div>
                 </div>
             </div>
        </div>
        <!-- //Item Layout -->
    </div>
</div>
</div>
</div>
<script type="text/javascript">
	var callback = null;
	$(document).ready(function() {
		// 체크박스 전체 선택
		$("#chkAll").click(function(){
			 if( $(this).is(':checked') ){
				 $("#reasonTable").find(":checkbox").prop("checked", true);
			 }else{
				 $("#reasonTable").find(":checkbox").prop("checked", false);
			 }
		});
		// 체크박스 전체 선택
		$("#chkAll2").click(function(){
			 if( $(this).is(':checked') ){
				 $("#reasonTable2").find(":checkbox").prop("checked", true);
			 }else{
				 $("#reasonTable2").find(":checkbox").prop("checked", false);
			 }
		});
		
		// 오른쪽 화살표 선택
		$(".btn_arr_right").click(function(){
			leftBtn();
		});
		
		// 왼쪽 화살표 선택
		$(".btn_arr_left").click(function(){
			rightBtn();
		});
		
		// 라벨 클릭 이벤트
		$("body").on("click",".board_list_data ",function(){
			if($(this).prev().children().is(":checkbox")){
				$(this).prev().children().trigger("click");
			}	
		});
		getReasonList();
	});
	
	// machineName 목록조회
	function getReasonList(){
		$("#machineTableList1").empty();
		var url = "<c:url value='/tran/ajax/getReasonList.do' />";	 
		$.ajax({
	            url: url,
	            type:'post',
	            data:{},
	            success:function(data){
	            	$("#reasonList").empty();
	            	var reasonList = data.list;
	            	for ( var i in reasonList) {
						console.log(reasonList[i].REASON);
						var reason = reasonList[i].REASON;
						addLeftReason(reason);
					}
	            }
	     });
	}
	
	// left button 클릭
	function leftBtn(){
		var $selChks = $(":checkbox[name=rChk1]:checked");	
		$selChks.each(function (index, item) {
			var $seTr = $(this).parent().parent();
			$seTr.remove();
			var reason = $(this).val();
			addRightReason(reason);
		});
	}
	
	// right button 클릭
	function rightBtn(){
		var $selChks = $(":checkbox[name=rChk2]:checked");	
		$selChks.each(function (index, item) {
			var $seTr = $(this).parent().parent();
			$seTr.remove();
			var reason = $(this).val();
			addLeftReason(reason);
		});
	}
	
	// reason List 추가(left )
	function addLeftReason(reason){
		var $reason = $("#reasonList:last");
		var html =  '<tr class="board_list_row" data-reason="'+reason+'">'
		+ '<td class="board_list_data" style="width:40px">'
		+ '<input type="checkbox" class="jqForm" name="rChk1" id="rChk1" value="'+reason+'"/>'
		+ '<td class="board_list_data" style="width:540px">'+reason+'</td>'
		+' </td></tr>';
		$reason.append(html);
	}
	
	// reason List 추가(right )
	function addRightReason(reason){
		var $reason = $("#reasonList2:last");
		var html =  '<tr class="board_list_row" data-reason="'+reason+'">'
		+ '<td class="board_list_data" style="width:40px">'
		+ '<input type="checkbox" class="jqForm" name="rChk2" id="rChk2" value="'+reason+'"/>'
		+ '<td class="board_list_data" style="width:540px">'+reason+'</td>'
		+' </td></tr>';
		$reason.append(html);
	}
	
	// 선택 machineName 목록 조회
	function getReasonListToString(){
		var reasons = "";
		var $tr = $("#reasonList2").find(":checkbox[name=rChk2]");
		$tr.each(function (index, item) {
			var reason = $(this).val();
			if(index == ($tr.length - 1)){  // 마지막
				reasons += 	reason;
			}else{	// 기타
				reasons += 	reason + ",";
			}
		});
		return reasons;
	}
	
	// 확인 버튼
	function apply(){
		var reasons = getReasonListToString();
		callback = opener.callback;
		if(callback){
			callback(reasons);
		}
		window.close();
	}
</script>