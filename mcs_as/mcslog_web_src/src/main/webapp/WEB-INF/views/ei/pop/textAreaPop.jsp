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
                    <div class="lay_item_center" style="padding-left: 10px;">
	                    <div id="popupTextArea" class="cPopUp_EI" style="width: 1180px; margin-left: 6px;">
	                       	<!-- <textarea class="grid_detail_list" id="popupLogDetail_EI" readOnly style=" width: 100%; height: 580px; -webkit-box-sizing: border-box; /* Safari/Chrome, other WebKit */ -moz-box-sizing: border-box;    /* Firefox, other Gecko */  box-sizing: border-box;         /* Opera/IE 8+ */" ></textarea> -->
	                    </div>
                    </div>
                </div>
            </div>

<script>
		
		$(document).ready(function() {
			
		});
		
		var doit;
		window.onresize = function(){
		  clearTimeout(doit);
		  doit = setTimeout(resizedwEI, 500);
		};
		
		function resizedwEI(){
 			$(".cPopUp_EI").css("width",$(window).width()-10+"px");
 			//$(".grid_detail_list").css("height",$(window).height()-20+"px");
 			/* console.log("textAreaCount : " + textAreaCount);
 			for (var i = 0; i < textAreaCount; i++) {
				setHeight(i);
				//console.log("Count : " + i);
		    } */
		}
		
		var popupKeyNum;
		var textAreaCount;

		function detailTextArea(textMap, gridCount, rowIdx, popupKey) {
			
			//console.log("count : " , gridCount);
			//console.log("mapSize : " , textMap.size());
			
			popupKeyNum = popupKey;
			textAreaCount = gridCount;
			
			var layout = $("#popupTextArea");
			
			for (var i = 0; i < gridCount; i++) {
				layout.append('<textarea id="grid_detail'+i+'" readOnly style="width: 98%; -webkit-box-sizing: border-box; -moz-box-sizing: border-box; box-sizing: border-box;" >'+textMap.get(i)+'</textarea ><br/>')
				setHeight(i);
		    }
			
			$('html, body').animate({	// 선택한 위치로 이동
                scrollTop: $("#grid_detail"+rowIdx).position().top}, 'slow');
			
			var target = document.getElementById("grid_detail"+rowIdx);
			
			if (target.setSelectionRange) {
				target.focus();
				target.setSelectionRange(0, textMap.get(rowIdx).length);	// selection 범위 설정
			}else {	console.log(" missing SelectionRange!! ");}
			
		}
		
		function detailTextFindFocus(textMap, gridCount, rowIdx, popupKey, popupFlag) {
			
		    if(popupKeyNum != popupKey || textAreaCount != gridCount || popupFlag) {	// 설정이 바뀐경우
		    	
		    	// layout 초기화 후 다시 append
		    	var layout = $("#popupTextArea");
				layout.empty();
				
				for (var i = 0; i < gridCount; i++) {
					layout.append('<textarea id="grid_detail'+i+'" readOnly style="width: 100%; -webkit-box-sizing: border-box; -moz-box-sizing: border-box; box-sizing: border-box;" >'+textMap.get(i)+'</textarea ><br/>')
					setHeight(i);
			    }
				// 변수 초기화
				popupKeyNum = popupKey;
				textAreaCount = gridCount;	
		    }
		    
			$('html, body').animate({	// 선택한 위치로 이동
                scrollTop: $("#grid_detail"+rowIdx).offset().top}, 'slow');
			
			var target = document.getElementById("grid_detail"+rowIdx);
			
			if (target.setSelectionRange) {
				target.focus();
				target.setSelectionRange(0, textMap.get(rowIdx).length);	// selection 범위 설정
			}else {	console.log(" missing SelectionRange!! ");}
		}
		
		function setHeight(rowIdx) {
			  var textEle = $('#grid_detail'+rowIdx);
			  textEle[0].style.height = 'auto';
			  var textEleHeight = textEle.prop('scrollHeight');
			  //textEle.css('height', textEleHeight+10);
			  textEle.css('height', textEleHeight+2);
			};
			
</script>