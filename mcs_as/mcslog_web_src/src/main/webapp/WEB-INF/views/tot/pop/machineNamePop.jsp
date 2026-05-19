<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ include file="/WEB-INF/views/common-header.jspf"%>
<link rel="stylesheet" type="text/css" href="${pageContext.request.contextPath }/styles/css/popup.css"/>
<%@ include file="/WEB-INF/views/common-taglib.jspf"%>
<div id="popup14" class="pop_window">
    <div class="pop_tit_wrap">
        <h2 class="pop_tit">Machine Name</h2>
        <a href="#" class="close_area">
            <span class="pop_btn pop_btn_close">
                <span class="blind"><spring:message code="site.common.button.popupclose" text="팝업 닫기" /></span>
            </span>
        </a>
    </div>
    <div class="pop_con_fix pop_con_fix_scroll">
        <div class="pop_con_area">
        <!-- 팝업 - 검색 + 보드 리스트(왼) + 보드리스트(오) -->
            <!-- Search Type01 -->
            <div class="srch_type01">
                <div class="condition_area">
                    <table class="condition_table" summary="검색조건 테이블">
                        <caption><spring:message code="site.common.filter" text="default text" /></caption>
                        <tbody>
                            <tr>
                                <th scope="col" class="condition_t_head">Machine Type</th>
                                <td class="condition_t_data">
                                    <select class="jqForm"  id="machineType" name="machineType" onchange="getMachineNameList();" >
                                        <!-- <option value="CONVEYOR">CONVEYOR</option>
                                        <option value="LIFTER">LIFTER</option>
                                        <option value="PROCESS">PROCESS</option>
                                        <option value="STB">STB</option>
                                        <option value="STOCKER">STOCKER</option>
                                        <option value="OHT">OHT</option>
                                        <option value="INTERLAYER">INTERLAYER</option>
                                        <option value="RETICLE">RETICLE</option>
                                        <option value="PODZIPTOWER">PODZIPTOWER</option>
                                        <option value="ZIPTOWER">ZIPTOWER</option>
                                        <option value="INTERAILSEMITS">INTERAILSEMITS</option> -->
                                        <!-- 2021.03.22	X0122410 machinetype 리스트를 서버에서 가져와서 보여준다 -->
                                        <c:forEach  items="${machineTypeInfoList}" var="row" varStatus="status"  >									 		
											<option value="<c:out value="${row.TYPE}"/>"><c:out value="${row.TYPE}"/></option>																		
										</c:forEach>
                                        <option value="">N/A</option>
                                    </select>
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head" style="width:90px">Machine Name</th>
                                <td class="condition_t_data">
                                <div class="lay_item">
                                 <div class="opt_tit">
                                	 <div class="opt_tit_right">
			                            <div class="elmt">
			                                 <div class="mini ui primary button"  onclick="setMachineName();" style="width:75px;float: right;margin-right: 10px;float:right">
												<i class="check square icon"></i>선택
											</div>
			                            </div>
			                        </div>
			                        </div>
                                    <div class="list_box">
			                                <table id="machineTable1" class="default_list">
			                                    <colgroup>
			                                        <col width="25" />
			                                        <col width="" />
			                                    </colgroup>
			                                    <thead>
			                                        <tr>
			                                            <th class="default_list_head"></th>
			                                            <th class="default_list_head"></th>
			                                        </tr>
			                                    </thead>
			                                    <tbody id="machineTableList1">
			                                    </tbody>
			                                </table>
			                       </div>
			                   </div>
			                   </td>
			                   </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <!-- //Search Type01 -->
            <!-- Item Layout -->
            <div class="lay_item vert">
                <div class="lay_item_box">
                    <div class="lay_item_center">
                    <!-- Sub Title -->
                    <div class="opt_tit">
                        <div class="opt_tit_left">
                            <div class="elmt">
                                <i id="foldTableBtn1" class="minus square icon large" style="color:#ccd2de"></i>
                                <span class="txt">목록</span>
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
                                 <div class="mini ui primary button"  onclick="delItems();" style="width:75px;float: right;margin-right: 10px;float:right">
									<i class="trash outline icon"></i>삭제
								</div>
                            </div>
                        </div>
                    </div>
                    <!-- //Sub Title -->
                        <!-- Board List -->
						<div class="scroll_box" style="height:200px;">
							<div class="board_list" style="height:190px">
								<table id="machineTable2" class="board_list_table" summary="해당 표에 대한 설명을 적어주세요." style="border-collapse: collapse;">
									<caption><spring:message code="site.common.summary.desc01" text="Write a description." /></caption>
									<thead style="width:527px;float:left">
										<tr class="board_list_row">
											<th class="board_list_head" scope="col" style="width:40px">
												<input type="checkbox" class="" name="chkAll" id="chkAll"/>
											</th>
											<th class="board_list_head" scope="col" style="width:510px">Machine Name</th>
										</tr>
									</thead>
									<tbody id="machineTableList2" style="width:527px;height:190px;overflow: auto;display: block;float:left" >
									</tbody>
								</table>
							</div>
						</div>
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
		
		// 라벨 클릭 이벤트
		$("body").on("click",".board_list_data , .default_list_data",function(){
			if($(this).prev().children().is(":checkbox")){
				$(this).prev().children().trigger("click");
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
		+ '<input type="checkbox" class="jqForm" name="mChk2" id="sel_'+machineName+'" />'
		+ '<td class="board_list_data" style="width:527px">'+machineName+'</td>'
		+' </td></tr>';
		window.console.log(html);
		$machineTableList2.append(html);
	}
</script>