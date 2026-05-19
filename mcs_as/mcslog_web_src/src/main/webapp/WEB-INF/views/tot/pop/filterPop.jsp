<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ include file="/WEB-INF/views/common-header.jspf"%>
<link rel="stylesheet" type="text/css" href="${pageContext.request.contextPath }/styles/css/popup.css"/>
<%@ include file="/WEB-INF/views/common-taglib.jspf"%>
<style>
  .ui-tooltip, .arrow:after {
    background: black;
    border: 2px solid white;
  }
  .ui-tooltip {
    padding: 10px 20px;
    color: white;
    border-radius: 20px;
    font: bold 14px "Helvetica Neue", Sans-Serif;
    text-transform: uppercase;
    box-shadow: 0 0 7px black;
    width:400px
  }
  .arrow {
    width: 70px;
    height: 16px;
    overflow: hidden;
    position: absolute;
    left: 50%;
    margin-left: -35px;
    bottom: -16px;
  }
  .arrow.top {
    top: -16px;
    bottom: auto;
  }
  .arrow.left {
    left: 20%;
  }
  .arrow:after {
    content: "";
    position: absolute;
    left: 20px;
    top: -20px;
    width: 25px;
    height: 25px;
    box-shadow: 6px 5px 9px -9px black;
    -webkit-transform: rotate(45deg);
    -ms-transform: rotate(45deg);
    transform: rotate(45deg);
  }
  .arrow.top:after {
    bottom: -20px;
    top: auto;
  }
  .hover_btn:HOVER {
	cursor: pointer;
	background-color: #1A355A;
}
 .hover_btn{
 	background-color: #27518B;
 	font-weight : bold;
 	
 	color :white;
 	border: 2px solid;
    border-radius: 5px;
    padding-left: 15px;
    padding-top: 10px;
    padding-bottom: 10px;
 }
  </style>
<div id="popup14" class="pop_window">
    <div class="pop_tit_wrap">
        <h2 class="pop_tit" >Filter Setting</h2>
        <a href="#" class="close_area">
            <span class="pop_btn pop_btn_close">
                <span class="blind"><spring:message code="site.common.button.popupclose" text="팝업 닫기" /></span>
            </span>
        </a>
    </div>
    <div class="pop_con_fix pop_con_fix_scroll">
    <form id="searchForm" name="searchForm" >
        <div class="pop_con_area">
        <!-- 팝업 - 검색 + 보드 리스트(왼) + 보드리스트(오) -->
            <!-- Search Type01 -->
            <div class="srch_type01">
                <div class="condition_area">
                    <table class="condition_table" summary="검색조건 테이블">
                        <caption><spring:message code="site.common.filter" text="default text" /></caption>
                        <tbody>
                            <tr>
                                <th scope="col" class="condition_t_head" style="width:145px">Search Condition</th>
                                <td class="condition_t_data">
                                    <input type="radio" id="searchOption1" name="searchOption" checked="checked" value="AND"/><label for="searchOption1" >AND</label>
                                    <input type="radio" id="searchOption2" name="searchOption" value="OR" /><label for="searchOption2" >OR</label>
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head" style="width:145px"><input type="checkbox" id="timeChk" checked="checked" ><label for="timeChk" >TIME</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="time" name="TIME_EX" style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="levelChk" checked="checked" ><label for="levelChk">LEVEL</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="level" name="LEVEL" style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="carrierChk" checked="checked" ><label for="carrierChk">CARRIER</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="carrier" name="CARRIER" style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="machine"  checked="checked" ><label for="machine">MACHINE</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="machine" name=MACHINENAME style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="unitChk" checked="checked" ><label for="unitChk">UNIT</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="unit" name="UNITNAME" style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="commandIdChk" checked="checked" ><label for="commandIdChk">COMMANDID</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="commandId" name="COMMANDID" style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="comMsgNameChk" checked="checked" ><label for="comMsgNameChk">COMM.MSG NAME</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="comMsgName" name="COMMAND" style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="operationNameChk" checked="checked" ><label for="operationNameChk">OPERATION NAME</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="operationName" name="OPERATION_NAME" style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="messageNameChk" checked="checked" ><label for="messageNameChk">MESSAGE NAME</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="messageName" name="MESSAGENAME" style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="processChk" checked="checked" ><label for="processChk">PROCESS</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="process" name="PROCESS" style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="transactionIdChk" checked="checked" ><label for="transactionIdChk">TRANSACTIONID</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="transactionId" name="TRANSACTIONID" style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="textChk" checked="checked" ><label for="textChk">TEXT</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="text" name="TEXT" style="width:370px" />
                                </td>
                            </tr>
                            <tr>
                                <th scope="col" class="condition_t_head"><input type="checkbox" id="threadChk" checked="checked" ><label for="threadChk">THREAD</label></th>
                                <td class="condition_t_data">
                                    <input type="text" id="thread" name="THREAD" style="width:370px" />
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
            <!-- span class="tooltip_custom" title="custom tooltip 입니다.">툴팁 커스텀</span -->            
            <!-- //Search Type01 -->
            <!-- Item Layout -->
            <div class="lay_item vert">
                <div class="lay_item_box">
                    <div class="lay_item_center">
                    <!-- Sub Title -->
                    <div class="opt_tit">
                        <div class="opt_tit_right">
                            <div class="elmt" id="filtericon">
                                 <div class="hover_btn"  onclick="closePop();" style="width:75px;float: right;margin-right: 10px;float:right">
<!--                                  <div class="mini ui primary button"  onclick="closePop();" style="width:75px;float: right;margin-right: 10px;float:right"> -->
									<!-- <i class="remove icon"></i> --><spring:message code="site.common.button.close" text="닫기" />
								</div>
                                <div class="hover_btn" onclick="apply();" style="width:75px;float: right;margin-right: 10px;float:right;">
<!--                                 <div class="mini ui primary button" onclick="apply();" style="width:75px;float: right;margin-right: 10px;float:right"> -->
									<!-- <i class="checkmark icon"></i> --><spring:message code="site.common.button.apply" text="apply" />
								</div>
                                <div id="help" class="hover_btn" style="width:95px;float: right;margin-right: 10px;float:right">
<!--                                 <div id="help" class="mini ui primary button trigger" style="width:83px;float: right;margin-right: 10px;float:right"> -->
									<!-- <i class="help icon"></i> -->? <spring:message code="site.common.button.help" text="도움말" />
								</div> 
                            </div>
                        </div>
                    </div>
                    </div>
                </div>
            </div>
        </div>
        </form>
    </div>
</div>
<script type="text/javascript">
	var callback = null;
	/* Tooltip	
	$(document).ready(function(){
        //tooltip custom tag
        var tooltipHtml = [];
        
        tooltipHtml.push("<div class='tooltip'>");
        tooltipHtml.push("    <div class='tooltip-arrow'></div>");
        tooltipHtml.push("    <h3> Tooltip Title</h3>");
        tooltipHtml.push("    <div class='tooltip-head'></div>");
        tooltipHtml.push("    <div class='tooltip-inner'></div>");
        tooltipHtml.push("</div>");
        
        //커스텀 Tooltip
        $(".tooltip_custom").tooltip({
            template: tooltipHtml.join("")
        });
    }); 
	*/
	$(document).ready(function() {
		/* var innerHtmlCode = '<div class="mini ui primary button"  onclick="closePop();" style="width:75px;float: right;margin-right: 10px;float:right">'
			innerHtmlCode  += '<i class="remove icon"></i><spring:message code="site.common.button.close" text="닫기" />'
			innerHtmlCode  +='</div>'
			innerHtmlCode  +='<div class="mini ui primary button" onclick="apply();" style="width:75px;float: right;margin-right: 10px;float:right">'
			innerHtmlCode  +='<i class="checkmark icon"></i><spring:message code="site.common.button.apply" text="apply" />'
			innerHtmlCode  +='</div>'
			innerHtmlCode  +='<div id="help" class="mini ui primary button trigger" style="width:83px;float: right;margin-right: 10px;float:right">				<i class="help icon"></i><spring:message code="site.common.button.help" text="도움말" />'
			innerHtmlCode  +='</div>'
		$("#filtericon").html(innerHtmlCode); */
		
		
		$("filtericon").html();
		
		// 체크박스 선택
		$(":checkbox").click(function(){
			if($(this).is(":checked")){
				$(this).parent().parent().find(":text").prop('disabled',false);			
			}else{
				$(this).parent().parent().find(":text").prop('disabled',true);					
			}
		});
		
		// 도움말
		 var content = "VALUE1 + VALUE2 : VALUE1 또는 VALUE2를 포함한 데이터 조회<br>";
		 content += "!VALUE1 : VALUE1이 아닌 데이터 조회<br>";
		 content += "!(VALUE1 + VALUE2) : VALUE1과 VALUE2를 모두 포함하지 않는 데이터 조회<br>";
		 content += "VALUE1%    : VALUE1으로 시작하는 데이터 조회<br>";
		 content += "%VALUE1    : VALUE1으로 끝나는 데이터 조회<br>";
		 content += "%VALUE1% : VALUE1이 포함된 데이터 조회<br>";
		 
		 $(document).on('click', '.trigger', function () {
			 $(this).addClass("on");
		     $(this).tooltip({
		            items: '.trigger.on',
		            position: {
		            	my: "center bottom-20",
				        at: "center top",
		                collision: "flip"
		            }
		     		,"content" : content
		     });
		     $(this).trigger('mouseenter');
		 });
		 
		 $(document).on('click', '.trigger.on', function () {
		    $(this).tooltip('close');
		 	$(this).removeClass("on");
		 });
		 
		 $(".trigger").on('mouseout', function (e) {
		 	e.stopImmediatePropagation();
		  });
		 
		 // enter key 이벤트 ..
		 $(":text").keypress(function(e){
			console.log(e.which);
			if (e.which == 13) {/* 13 == enter key@ascii */
				apply();
			}
		 });
	});
	
	// 확인 버튼
	function apply(){		
		var param = $("#searchForm").serializeObject();
		window.console.log(param); 
		callback = opener.callback;
		if(callback){
			callback(param);
		}
		//window.close();
	}
	
	// 닫기
	function closePop(){
		callback = opener.callback;
		if(callback){
			callback({});
		}
		window.close();
	}
</script>