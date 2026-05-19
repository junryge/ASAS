<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ include file="/WEB-INF/views/common-header.jspf"%>
<link rel="stylesheet" type="text/css" href="${pageContext.request.contextPath }/styles/css/popup.css"/>
<%@ include file="/WEB-INF/views/common-taglib.jspf"%>

<style>
	.grid_detail_list {
    line-height: 20px;
  }
</style>
		<input type="hidden" id="focusValue" name="focusValue" value="1" />
		<div class="lay_item vert">
                <div class="lay_item_box">
                    <div class="lay_item_center">
                    <!-- Sub Title -->
                    <!-- <div class="opt_tit">
                        <div class="opt_tit_right">
                            <div class="elmt" id="filtericon">
	                            <div id="Sidenav_EI" class="sidenav1" style="width: 780px;">
									<div class="Resize_detailPopup" style="border: 1px solid #111;height: 580px;margin-left: 10px;margin-top: 6px;">
										<pre class="prettyprint" id="popupLogDetail_EI" style="white-space: pre-wrap;"></pre>	
									</div>
								</div>	
                                 <div class="hover_btn"  onclick="closePop();" style="width:75px;float: right;margin-right: 10px;float:right">
                                 <div class="mini ui primary button"  onclick="closePop();" style="width:75px;float: right;margin-right: 10px;float:right">
									<i class="remove icon"></i><spring:message code="site.common.button.close" text="default text" />
								</div>
                            </div>
                        </div>
                    </div> -->
                    <div id="popUp_EI" class="cPopUp_EI" style="width: 780px; margin-left: 6px;">
                        <table class="tbl_hori_inside" summary="해당 표에 대한 설명을 적어주세요.">
                             <!-- <caption><spring:message code="site.common.summary.desc01" text="default text" /></caption>
                             <colgroup>
                                 <col width="120"/>
                             </colgroup> -->
                             <tbody>
                                 <tr class="hori_t_row">
                                     <td class=""><textarea class="grid_detail_list" id="popupLogDetail_EI" readOnly style=" width: 100%; height: 580px; -webkit-box-sizing: border-box; /* Safari/Chrome, other WebKit */ -moz-box-sizing: border-box;    /* Firefox, other Gecko */  box-sizing: border-box;         /* Opera/IE 8+ */" ></textarea></td>
                                 </tr>
                             </tbody>
                        </table>
                    </div>
                    </div>
                </div>
            </div>

<script>
		// 닫기
		/* function closePop(){
			callback = opener.callback;
			if(callback){
				callback({});
			}
			window.close();
		} */
		$(document).ready(function() {
			
		});
		
		var doit;
		window.onresize = function(){
		  clearTimeout(doit);
		  doit = setTimeout(resizedwEI, 500);
		};
		
		function resizedwEI(){
 			$(".cPopUp_EI").css("width",$(window).width()-10+"px");
 			$(".grid_detail_list").css("height",$(window).height()-20+"px");
		}

		function detailTextFindFocus(popOption) {
			var find_string = $("#focusValue").val();
				
			var posi =  $("#popupLogDetail_EI").val().indexOf(find_string);
			
			var popOptionVal = popOption;
			console.log("popOptionVal : ", popOptionVal);
			
			if (posi != -1) {
				//console.log("position : ", posi);
				var target = document.getElementById("popupLogDetail_EI");
				
					if (target.setSelectionRange) {
						console.log("AA");
						target.focus();
						target.setSelectionRange(posi, posi+find_string.length);	// selection 범위 설정
					}else {
						console.log("BB");
						var r = target.createTextRange();
						r.collapse(true);
						r.moveEnd('character',  posi+find_string);
			            r.moveStart('character', posi);
			            r.select();
					}
					
					var objDiv = document.getElementById("popupLogDetail_EI");
					var sh = objDiv.scrollHeight; //height in pixel of the textarea (n_rows*line_height)
					//console.log("sh : ", sh);
					var line_ht = $('#popupLogDetail_EI').css('line-height').replace('px',''); //height in pixel of each row
					//console.log("line_ht : ", line_ht);
					var n_lines = sh/line_ht;
					console.log("n_lines : ", n_lines);
					var char_in_line = $('#popupLogDetail_EI').val().length / n_lines; 
					console.log("char_in_line : ", char_in_line);
					var height = Math.floor(posi/char_in_line);
					console.log("posi : ", posi);
					console.log("height : ", height);
					
					if(popOptionVal ==1) {
						console.log("secs");
						$('#popupLogDetail_EI').scrollTop((height*line_ht)-(height*0.1)); // scroll to the selected line	
					}else {
						console.log("ei");
						$('#popupLogDetail_EI').scrollTop((height*line_ht)-(line_ht*0.06)); // scroll to the selected line	
					}
					
					
					 
			}else{
				alert('<spring:message code="site.common.error.msg01" text="default text" />'); // alert word not found
			}
		}
		
		
		
</script>