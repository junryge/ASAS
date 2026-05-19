<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ include file="/WEB-INF/views/common-header.jspf"%>
<link rel="stylesheet" type="text/css" href="${pageContext.request.contextPath }/styles/css/popup.css"/>
<%@ include file="/WEB-INF/views/common-taglib.jspf"%>
<div id="popup14" class="pop_window">
    <div class="pop_tit_wrap">
        <h2 class="pop_tit">Setting</h2>
        <a href="#" class="close_area">
            <span class="pop_btn pop_btn_close">
                <span class="blind"><spring:message code="site.common.button.popupclose" text="default text" /></span>
            </span>
        </a>
    </div>
    <div class="pop_con_fix pop_con_fix_scroll">
        <div class="pop_con_area" style="height:140px">
        <!-- 팝업 - 검색 + 보드 리스트(왼) + 보드리스트(오) -->
            <!-- Search Type01 -->
            <div class="srch_type01">
                <div class="condition_area">
                    <table class="condition_table" summary="검색조건 테이블">
                        <tbody>
                            <tr>
                                <th scope="col" class="condition_t_head">Line</th>
                                <td class="condition_t_data">
                                    <select class="jqForm"  id="machineType" name="machineType" onchange="" >
                                        <option value="M14FAB" selected="selected" >M14FAB</option>
                                        <option value="M14AFAB">M14AFAB</option>
                                        <option value="M14BFAB">M14BFAB</option>
                                    </select>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="opt_tit_right">
                <div class="elmt" style="margin-top:40px;">
					 <div class="mini ui primary button"  onclick="window.close();" style="width:75px;margin-left:195px;">
						<i class="remove icon"></i><spring:message code="site.common.button.close" text="default text" />
					</div>
					 <div class="mini ui primary button"  onclick="apply();" style="width:75px;margin-left:10px;">
						<i class="checkmark icon"></i><spring:message code="site.common.button.apply" text="default text" />
					</div>
                </div>
            </div>
        </div>
    </div>
</div>
<script type="text/javascript">
	var callback = null;
	$(document).ready(function() {
		$("#chkAll").click(function(){
			 if( $(this).is(':checked') ){
				 $("#machineTable2").find(":checkbox").prop("checked", true);
			 }else{
				 $("#machineTable2").find(":checkbox").prop("checked", false);
			 }
		});
		
		getMachineNameList();
	});
	
	// machineName 목록조회
	function getMachineNameList(){
		$("#machineTableList1").empty();
		var url = "<c:url value='/tot/ajax/getMachineList.do' />";	 
		var machineType = $("#machineType").val();
		$.ajax({
	            url: url,
	            type:'post',
	            data:{"machineType":machineType},
	            success:function(data){
	            	var machineNameList = data.list;
	            	for ( var i in machineNameList) {
						console.log(machineNameList[i].MACHINENAME);
						var machineName = machineNameList[i].MACHINENAME;
						addMachineName(machineName);
					}
	            }
	     });
	}
	
	// machineName List 추가
	function addMachineName(machineName){
		var $tr = $('<tr data-machineName="" ></tr>');
		$tr.attr("data-machineName",machineName);
        var $td = $('<td class="default_list_data"></td>');
        var $chk = $('<input type="checkbox" class="" name="mChk1" id="mChk1" >');
        var $td2 = $('<td class="default_list_data align_left"></td>');
        $tr.attr("data-machineName",machineName);
        $td2.text(machineName);
        $td.append($chk);
        $tr.append( $td).append($td2);
        $("#machineTableList1").append($tr);
	}

	// 선택 machineName 목록 조회
	function getMachineNameToString(){
		var machineNames = "";
		var $tr = $("#machineTable2").find("tr:gt(0)");
		$tr.each(function (index, item) {
			var machineName = $(this).attr("data-machineName");
			if(index == ($tr.length - 1)){  // 마지막
				machineNames += 	machineName;
			}else{	// 기타
				machineNames += 	machineName + ",";
			}
		});
		return machineNames;
	}
	
	// 확인 버튼
	function apply(){
		var machineNames = getMachineNameToString();
		
		window.console.log(machineNames); 
		callback = opener.callback;
		if(callback){
			callback(machineNames);
		}
		window.close();
	}
	
	// 삭제 버튼
	function delItems(){
		var $selChks = $(":checkbox[name=mChk2]:checked");
		$selChks.each(function (index, item) {
			var $seTr = $(this).parent().parent();
			$seTr.remove();
		});
	}
	
	// MachineName 선택
	function setMachineName(){
		var machineNames = getMachineNameToString();
		var $selChks1 = $(":checkbox[name=mChk1]:checked");
		$selChks1.each(function (index, item) {
			var machineName = $(this).parent().parent().attr("data-machineName");
			console.log("11"+machineName);
			if(machineNames.indexOf(machineName) == -1){
				addMachineName2(machineName);
			}
		});
	}
	
	// machineName Row 생성
	function addMachineName2(machineName){
		console.log(machineName);
		var $machineTableList2 = $("#machineTableList2:last");
		var html =  '<tr class="board_list_row" data-machineName="'+machineName+'">'
		+ '<td class="board_list_data" style="width:40px">'
		+ '<input type="checkbox" class="jqForm" name="mChk2" id="mChk2" />'
		+ '<td class="board_list_data" style="width:527px">'+machineName+'</td>'
		+' </td></tr>';
		window.console.log(html);
		$machineTableList2.append(html);
	}
</script>