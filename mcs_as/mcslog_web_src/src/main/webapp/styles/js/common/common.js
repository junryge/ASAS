function resizedw(){
		$(".tree_wrap").css("height",$(window).height()-180+"px"); // filterView 사이즈 재설정
		$(".gridForResize").css("height",$(window).height()-420+"px");
		$(".gridForResize_secs").css("height",$(window).height()-174+"px");
		$(".gridForResize_ei").css("height",$(window).height()-174+"px");
		$(".gridForResize_single").css("height",$(window).height()-180+"px");
		$(".gridForResize_triple").css("height",$(window).height()-530+"px");
		//$("#SECSII_List").css("height",$(window).height()-120+"px");
		}
// lpad 
function leadingZeros(n, digits) {
  var zero = '';
  n = n.toString();
  if (n.length < digits) {
    for (i = 0; i < digits - n.length; i++)
      zero += '0';							//digit(자리수)보다 n의 자리수가 작으면 해당 자리수만큼 0을 zero문자열에 append
  }
  return zero + n;
}

// 년월일 포멧 변경 date -> string (ex  2014-04-27 )
function getDate(d,liter){
	var s =
	    leadingZeros(d.getFullYear(), 4) + liter +
	    leadingZeros(d.getMonth() + 1, 2) + liter +
	    leadingZeros(d.getDate(), 2);
	return s;
}

// 시간 포멧 변경 date -> string (ex 13:10:50)
function getTimeStamp(d,liter) {
  var s =
    leadingZeros(d.getHours(), 2) + liter +
    leadingZeros(d.getMinutes(), 2) + liter +
    leadingZeros(d.getSeconds(), 2);
  return s;
}

var callback = null;  //콜백 함수
// 윈도우 팝업 오픈 
function openPopup(url , cw , ch,_callback){
	var sw=screen.availWidth;  // 모니터 가로 사이즈
	var sh=screen.availHeight;  // 모니터 세로 사이즈
	//팝업 창의 포지션 ( 모니터 정 중앙 ) 
	px=(sw-cw)/2;   // left
	py=(sh-ch)/2;    // top
	var win = window.open(url,'machinePopup', 'left='+px+',top='+py+',width='+cw+',height='+ch+',toolbar=no,location=no,menubar=no');
	if(_callback){  // 콜백 함수 존재시, 실행
		callback = _callback;
	}
}

// 쿠키 값 생성
function setCookie (name,value,expires,path,domain,secure) 
{
	  document.cookie = name + "=" + escape (value) +
	    ((expires) ? "; expires=" + expires.toGMTString() : "") +
	    ((path) ? "; path=" + path : "") +
	    ((domain) ? "; domain=" + domain : "") +
	    ((secure) ? "; secure" : "");
}

// 쿠키값 가져오기
function getCookieval(offset) {
	   var endstr = document.cookie.indexOf (";", offset);
	   if (endstr == -1)
	      endstr = document.cookie.length;
	   return unescape(document.cookie.substring(offset, endstr));
}

// 쿠키값 조회
function getCookie(name) 
{
	 var arg = name + "=";
	 var alen = arg.length;
	 var clen = document.cookie.length;
	 var i = 0;

	 while (i < clen) {
	  var j = i + alen;
	      if (document.cookie.substring(i, j) == arg)
	         return getCookieval (j);
	      i = document.cookie.indexOf(" ", i) + 1;
	      if (i == 0) break; 
	 }
	 return null;
}

// 시간 포멧 터 변경 date -> string ( 2017-04-27 03:23:55:234 ) 
function getTime(time){
	var tranTime = time.getFullYear()+'-'+leadingZeros(time.getMonth(),2)+'-'+leadingZeros(time.getDate(),2)+' '+
	leadingZeros(time.getHours(),2)+':'+leadingZeros(time.getMinutes(),2)+':'+leadingZeros(time.getSeconds(),2)+':'+time.getMilliseconds();
	console.log("before["+time+"],after["+tranTime+"]");
	return tranTime;
}

function getFabFromFabSite(menu, fabSite, target_control, target_td){
	var _fab = $content.find(":checkbox[name^="+target_control+"]:checked").map(function(){return $(this).val(); }).get();
	console.log("fab : " + _fab);
	var param = { "menu":menu, "fabSite":fabSite }; // 파라메터
	console.log(param);	
	var url = "/tot/ajax/getFabFromFabSite.do";	 
	$.ajax({
            url: url,
            type:'post',
            data: param,
            async: false,
            traditional: true,
            success:function(data){            	
            	console.dir(data);	
            	console.log(data.list.length);            	
            	var $td = $content.find("#" + target_td);
            	//$targetControl.remove();
            	$td.empty();
            	
            	$td.append("<input type=\"checkbox\" class=\"jqForm\" id=\""+target_control+"1\" name=\""+target_control+"1\" value=\"ALL\"><label for=\""+target_control+"1\">ALL</label><BR>");
            	
            	if(data == null || data.list == null || data.list.length == 0) return;
            	
            	for(var i in data.list){
            		$idx = parseInt(i) + 2;
        			$val = data.list[i];
        			$sChecked = "";
        			//basic_list
        			if(data.basic_list.length > 0 && data.basic_list.includes($val))
    				{
        				$sChecked="checked";
    				}
       			        			
        			$td.append("<input type=\"checkbox\" class=\"jqForm\" id=\""+target_control+$idx + "\" name=\""+target_control+$idx + "\" value=\"" + $val + "\" " + $sChecked +"><label for=\""+target_control+$idx + "\">" + $val + "</label><BR>");
            	}
            }
     });
}

// machine name list 조회
function getMachineNameList(fabSite, fab, areaName, bayName, machineType, control){
	var area = $content.find("#"+areaName).val(); // areaName 값
	var bay = $content.find("#"+bayName).val();   // bayName 값
	var type =  $content.find(":checkbox[name^="+machineType+"]:checked").map(function(){return $(this).val(); }).get(); // machine Type 값
	var fab = $content.find(":checkbox[name^="+fab+"]:checked").map(function(){return $(this).val(); }).get(); // fab Type 값
	var param = {"fabSite":fabSite, "areaName":area , "bayName":bay , "machineType" : type, "selectFab":fab}; // 파라메터
/*	console.log("machineType["+type+"]");
	console.log(JSON.stringify("param["+param+"]"));*/
	var url = "ajax/getMachineList.do";	 
	$.ajax({
            url: url,
            type:'post',
            data: param,
            async: false,
            traditional: true,
            success:function(data){
				var $select = $content.find("#"+control);
				$select.empty();
            	$select.append("<option value='' >NOTDESIGNATED</option>");
            	for(var i in data.list){ // machine name list  셀렉트 생성
					var $opt = $("<option value=''></option>");  
					$opt.attr("value" , data.list[i].MACHINENAME);
					$opt.text(data.list[i].MACHINENAME);
					$select.append($opt);
            	}
            }
     });
}

function getMachineNameListMachineTypeNotNull(fabSite, fab, areaName, bayName, machineType, control){
	var area = $content.find("#"+areaName).val(); // areaName 값
	var bay = $content.find("#"+bayName).val();   // bayName 값
	var type =  $content.find(":checkbox[name^="+machineType+"]:checked").map(function(){return $(this).val(); }).get(); // machine Type 값
	var fab = $content.find(":checkbox[name^="+fab+"]:checked").map(function(){return $(this).val(); }).get(); // fab Type 값
	var param = {"fabSite":fabSite, "areaName":area , "bayName":bay , "machineType" : type, "selectFab":fab}; // 파라메터
/*	console.log("machineType["+type+"]");
	console.log(JSON.stringify("param["+param+"]"));*/
	var url = "ajax/getMachineListMachineTypeNotNull.do";	 
	$.ajax({
            url: url,
            type:'post',
            data: param,
            async: false,
            traditional: true,
            success:function(data){
            	console.log(data);
				var $select = $content.find("#"+control);
				$select.empty();
            	$select.append("<option value='' >NOTDESIGNATED</option>");
            	for(var i in data.list){ // machine name list  셀렉트 생성
					var $opt = $("<option value=''></option>");  
					$opt.attr("value" , data.list[i].MACHINENAME);
					$opt.text(data.list[i].MACHINENAME);
					$select.append($opt);
            	}
            }
     });
}

function getMachineNameList2(fabSite, fab, controls){	
	var fab = $content.find(":checkbox[name^="+fab+"]:checked").map(function(){return $(this).val(); }).get(); // fab Type 값
	var param = {"fabSite":fabSite, "selectFab":fab, "areaName":"ALL" , "bayName":"ALL" , "machineType" : "ALL" }; // 파라메터
/*	console.log("machineType["+type+"]");
	console.log(JSON.stringify("param["+param+"]"));*/
	var url = "ajax/getMachineList.do";	 
	$.ajax({
            url: url,
            type:'post',
            data: param,
            async: false,
            traditional: true,
            success:function(data){
            	var splits = controls.split(['|']);        	
            	for(n=0;n<splits.length;n++)
        		{
            		var $select = $content.find("#"+splits[n]);
    				$select.empty();
                	$select.append("<option value='' >NOTDESIGNATED</option>");
                	for(var i in data.list){ // machine name list  셀렉트 생성
    					var $opt = $("<option value=''></option>");  
    					$opt.attr("value" , data.list[i].MACHINENAME);
    					$opt.text(data.list[i].MACHINENAME);
    					$select.append($opt);
                	}
        		}				
            }
     });
}

function getMachineNameList2MachineTypeNotNull(fabSite, fab, controls){	
	var fab = $content.find(":checkbox[name^="+fab+"]:checked").map(function(){return $(this).val(); }).get(); // fab Type 값
	var param = {"fabSite":fabSite, "selectFab":fab, "areaName":"ALL" , "bayName":"ALL" , "machineType" : "ALL" }; // 파라메터
/*	console.log("machineType["+type+"]");
	console.log(JSON.stringify("param["+param+"]"));*/
	var url = "ajax/getMachineListMachineTypeNotNull.do";	 
	$.ajax({
            url: url,
            type:'post',
            data: param,
            async: false,
            traditional: true,
            success:function(data){
            	console.log(data);
            	var splits = controls.split(['|']);        	
            	for(n=0;n<splits.length;n++)
        		{
            		var $select = $content.find("#"+splits[n]);
    				$select.empty();
                	$select.append("<option value='' >NOTDESIGNATED</option>");
                	for(var i in data.list){ // machine name list  셀렉트 생성
    					var $opt = $("<option value=''></option>");  
    					$opt.attr("value" , data.list[i].MACHINENAME);
    					$opt.text(data.list[i].MACHINENAME);
    					$select.append($opt);
                	}
        		}				
            }
     });
}

//200826 hgJeon fab, area 별 bayList
function getBayFromArea(fabSite, fab, areaName, control){
	var area = $content.find("#"+areaName).val(); // areaName 값		
	var fab = $content.find(":checkbox[name^="+fab+"]:checked").map(function(){return $(this).val(); }).get(); // fab Type 값
	var param = {"fabSite":fabSite, "areaName":area , "selectFab":fab}; // 파라메터	
	var urlBayAjax = "ajax/getBayFromArea.do";	 
	$.ajax({
        url: urlBayAjax,
        type:'post',
        data: param,
        async: false,
        traditional: true,
        success:function(data){        	
        	var $select = $content.find("#" + control);
			$select.empty();
        	$select.append("<option value='ALL' selected='selected'>ALL</option>");
        	for(var i in data.list){ // bay list  셀렉트 생성
				var $opt = $("<option value=''></option>");  
				$opt.attr("value" , data.list[i].BAYNAME);
				$opt.text(data.list[i].BAYNAME);
				$select.append($opt);
        	}
        }
    });
}

function getBayFromArea2(fabSite, fab, controls){		
	var fab = $content.find(":checkbox[name^="+fab+"]:checked").map(function(){return $(this).val(); }).get(); // fab Type 값
	var param = {"fabSite":fabSite, "areaName":"ALL" , "selectFab":fab}; // 파라메터	
	var urlBayAjax = "ajax/getBayFromArea.do";	 
	$.ajax({
        url: urlBayAjax,
        type:'post',
        data: param,
        async: false,
        traditional: true,
        success:function(data){        	
        	var splits = controls.split(['|']);        	
        	for(n=0;n<splits.length;n++)
        	{
        		var $select = $content.find("#" + splits[n]);
    			$select.empty();
            	$select.append("<option value='ALL' selected='selected'>ALL</option>");
            	for(var i in data.list){ // bay list  셀렉트 생성
    				var $opt = $("<option value=''></option>");  
    				$opt.attr("value" , data.list[i].BAYNAME);
    				$opt.text(data.list[i].BAYNAME);
    				$select.append($opt);
            	}	
        	}
        }
    });
}

// 200827 hgJeon fab, area 별 bayList
function getAreaFromFab(fabSite,fab,control){
	var fab = $content.find(":checkbox[name^="+fab+"]:checked").map(function(){return $(this).val(); }).get(); // fab Type 값
	var param = {"fabSite":fabSite, "selectFab":fab}; // 파라메터
	var urlAreaAjax = "ajax/getAreaFromFab.do";	 
	$.ajax({
        url: urlAreaAjax,
        type:'post',
        data: param,
        async: false,
        traditional: true,
        success:function(data){        	
        	var $select = $content.find("#"+control);
			$select.empty();
        	$select.append("<option value='ALL' selected='selected'>ALL</option>");
        	for(var i in data.list){ // bay list  셀렉트 생성
				var $opt = $("<option value=''></option>");  
				$opt.attr("value" , data.list[i].AREANAME);
				$opt.text(data.list[i].AREANAME);
				$select.append($opt);
        	}
        }
    });
}

//200827 hgJeon fab, area 별 bayList
function getAreaFromFab2(fabSite, fab, controls){
	var fab = $content.find(":checkbox[name^="+fab+"]:checked").map(function(){return $(this).val(); }).get(); // fab Type 값
	var param = {"fabSite":fabSite, "selectFab":fab}; // 파라메터
	var urlAreaAjax = "ajax/getAreaFromFab.do";	 
	$.ajax({
        url: urlAreaAjax,
        type:'post',
        data: param,
        async: false,
        traditional: true,
        success:function(data){        	
        	var splits = controls.split(['|']);        	
        	for(n=0;n<splits.length;n++)
    		{
        		var $select = $content.find("#" + splits[n]);
    			$select.empty();
            	$select.append("<option value='ALL' selected='selected'>ALL</option>");
            	for(var i in data.list){ // bay list  셀렉트 생성
    				var $opt = $("<option value=''></option>");  
    				$opt.attr("value" , data.list[i].AREANAME);
    				$opt.text(data.list[i].AREANAME);
    				$select.append($opt);
            	}
    		}
        	
        }
    });
}

// 2021. 03. 31. X0122410. FAB별 machinetype list 가져오기
function getMachineTypeFromFab(fabSite, fab, machineControlName, control){
	var _fab = $content.find(":checkbox[name^="+fab+"]:checked").map(function(){return $(this).val(); }).get(); // fab Type 값
	var param = { "fabSite":fabSite, "selectFab":_fab }; // 파라메터
	var url = "ajax/getMachineTypeFromFab.do";	 
	$.ajax({
            url: url,
            type:'post',
            data: param,
            async: false,
            traditional: true,
            success:function(data){
            	//console.dir(data);	
            	//console.log(data.list.length);
            	var $targetControl = $content.find("#" + control);
            	$targetControl.find("td").remove();
            	//$targetControl.empty();
            	
            	if(data == null || data.list == null || data.list.length == 0) return;
            	
            	$td = $("<td class=\"condition_t_data\"></td>");
            	$td.append("<input type=\"checkbox\" class=\"jqForm\" id=\""+machineControlName+"1\" name=\""+machineControlName+"1\" value=\"ALL\" checked><label for=\""+machineControlName+"1\">ALL</label><BR>");
            	for(var i in data.list){ // machine name list  셀렉트 생성
            		if( i % 2 == 1)
        			{
            			$idx = parseInt(i) + 2;
            			$val = data.list[i].TYPE;
            			$td.append("<input type=\"checkbox\" class=\"jqForm\" id=\""+machineControlName+$idx + "\" name=\""+machineControlName+$idx + "\" value=\"" + $val + "\"><label for=\""+machineControlName+$idx + "\">" + $val + "</label><BR>");
        			}
            	}
        		$targetControl.append($td);
        		
        		$td = $("<td class=\"condition_t_data\"></td>");
            	for(var i in data.list){ // machine name list  셀렉트 생성
            		if( i % 2 == 0)
        			{
            			$idx = parseInt(i) + 2;
            			$val = data.list[i].TYPE;
            			$td.append("<input type=\"checkbox\" class=\"jqForm\" id=\""+machineControlName+$idx + "\" name=\""+machineControlName+$idx + "\" value=\"" + $val + "\"><label for=\""+machineControlName+$idx + "\">" + $val + "</label><BR>");           			
        			}
            	}
        		$targetControl.append($td);
            }
     });
}

//2021. 03. 31. X0122410. FAB별 machinetype list 가져오기
function getMachineTypeFromFab2(fabSite, fab, machineControlNames,controls){
	var _fab = $content.find(":checkbox[name^="+fab+"]:checked").map(function(){return $(this).val(); }).get(); // fab Type 값
	var param = { "fabSite":fabSite, "selectFab":_fab }; // 파라메터
	var url = "ajax/getMachineTypeFromFab.do";	 
	$.ajax({
         url: url,
         type:'post',
         data: param,
         async: false,
         traditional: true,
         success:function(data){
         	//console.dir(data);	
         	//console.log(data.list.length);
        	
        	var splitMachineNames = machineControlNames.split(['|']);
        	var splits = controls.split(['|']);        	        	
        	for(n=0;n<splits.length;n++)
        	{
        		var $targetControl = $content.find("#" + splits[n]);
             	$targetControl.find("td").remove();
             	//$targetControl.empty();
             	
             	if(data == null || data.list == null || data.list.length == 0) return;
             	
             	$td = $("<td class=\"condition_t_data\"></td>");
             	$td.append("<input type=\"checkbox\" class=\"jqForm\" id=\""+splitMachineNames[n]+"1\" name=\""+splitMachineNames[n]+"1\" value=\"ALL\" checked><label for=\""+splitMachineNames[n]+"1\">ALL</label><BR>");
             	for(var i in data.list){ // machine name list  셀렉트 생성
             		if( i % 2 == 1)
         			{
             			$idx = parseInt(i) + 2;
             			$val = data.list[i].TYPE;
             			$td.append("<input type=\"checkbox\" class=\"jqForm\" id=\""+splitMachineNames[n]+$idx + "\" name=\""+splitMachineNames[n]+$idx + "\" value=\"" + $val + "\"><label for=\""+splitMachineNames[n]+$idx + "\">" + $val + "</label><BR>");
         			}
             	}
         		$targetControl.append($td);
         		
         		$td = $("<td class=\"condition_t_data\"></td>");
             	for(var i in data.list){ // machine name list  셀렉트 생성
             		if( i % 2 == 0)
         			{
             			$idx = parseInt(i) + 2;
             			$val = data.list[i].TYPE;
             			$td.append("<input type=\"checkbox\" class=\"jqForm\" id=\""+splitMachineNames[n]+$idx + "\" name=\""+splitMachineNames[n]+$idx + "\" value=\"" + $val + "\"><label for=\""+splitMachineNames[n]+$idx + "\">" + $val + "</label><BR>");           			
         			}
             	}
         		$targetControl.append($td);	
        	}	
         }
  });
}

// 달력 컨트롤러 초기화
function setDatepicker(uuid){
	// 달력 초기화(시작일)
	$content.find( "#fromDt"+uuid ).datepicker({
           showOn: "button",
           buttonImage: "../styles/images/form/calendar.jpg",
           buttonImageOnly: true,
           buttonText: "Select date",
           dateFormat: "yy.mm.dd",
           changeMonth: true,
           changeYear: true,
           showButtonPanel: true
    });
	// 달력 초기화(종료일)
	$content.find( "#toDt"+uuid ).datepicker({
         showOn: "button",
         buttonImage: "../styles/images/form/calendar.jpg",
         buttonImageOnly: true,
         buttonText: "Select date",
         dateFormat: "yy.mm.dd",
         changeMonth: true,
         changeYear: true,
         showButtonPanel: true
     });
}

// 공통 초기화
function init(){
	// Time Range spinner 초기화
	$content.find("#fromHour" ).spinner({ numberFormat: "n2" , min: 0, max: 23 });
	$content.find("#fromMin" ).spinner({ numberFormat: "d2" , min: 0, max: 59 });
	$content.find("#fromSec" ).spinner({ numberFormat: "d2" , min: 0, max: 59 });
	$content.find("#toHour" ).spinner({ numberFormat: "d2" , min: 0, max: 23 });
	$content.find("#toMin" ).spinner({ numberFormat: "d2", min: 0, max: 59 });
	$content.find("#toSec" ).spinner({ numberFormat: "d2", min: 0, max: 59 });
	$content.find("#searchDelay" ).spinner({ numberFormat: "d2", min: 10, max: 90 });	// 200601 hgJeon search Delay Time Option 추가
	// 검색조건 fold ( add square icon ) 
	$content.find(".add.square.icon").parent().parent().parent().find("tr:gt(0)").slideUp("slow");
}

// 검색 필드 변수 초기화
function reset(){
	$content.find("#filter").val("01"); // single filter 선택
	$content.find("#searchForm")[0].reset(); // form 변수 초기화
	$content.find(":radio[name=time]:eq(0)").trigger("click"); // Time Range 첫번째 값 선택
	if($content.find("#machineName2").length > 0 )  // multi filter 존재시
		$content.find("#machineName2").prop('disabled',true); // multi filter 비활성
	setFilter();  // 필터 세팅
	$content.find("#AndOr_selectLabel").text("or");		//201109 hgJeon end or label 초기화
}

// 로딩 바 보이기
var startTime = null; // 조회 시작 시간
function showLoadingbar($g){
	startTime = new Date().getTime();
	var loadingIndicator = $("<span class='loading-indicator' ></span>");  // 로딩바 객체 생성
	loadingIndicator.appendTo(document.body);  
    loadingIndicator.css("position", "absolute")
    .css("top", $g.position().top + $g.height() / 2 + 40 ) // 그리드 세로 위치
    .css("left", $g.position().left + $g.width() / 2 - loadingIndicator.width() / 2);  // 그리드 가로 위치
    loadingIndicator.show();  // 그리드 정중앙 로딩바 보임
    return loadingIndicator;
}

// 로딩바 숨김
function loadingbarFadeOut(){
	var stopTime = new Date().getTime(); // 조회 종료 시간
	$content.find("#laptime").text((stopTime - startTime)); // laptime 표시
	console.log("lap:"+$content.find("#laptime").text());
	$(".loading-indicator").fadeOut(function(){ $(this).remove(); }); // 로딩바 숨김
}

// 필터 리스트
// 20220621	X0122410	fabSite 추가
function getFilterList(fabSite){
	
	setTimeout(function(){
		var url = "filter/ajax/getAreaList.do";
		var param = { "fabSite":fabSite }; // 파라메터
		$.ajax({
            url: url,
            type:'get',
            data: param,
            dataType: 'json',
            success:function(data){
            	var result = data[0];
            	$.each(result, function(index, value){
            		$content.find(".areaName_machine").append(""+
            		"<option value='"+value.AREANAME+"'>"+value.AREANAME+"</option>"); 
            	}); 
            }
	    });
	}, 650);
	
	setTimeout(function(){
		var url = "filter/ajax/getBayList.do";	 
		var param = { "fabSite":fabSite }; // 파라메터
		$.ajax({
            url: url,
            type:'get',
            data: param,
            dataType: 'json',
            success:function(data){
            	var result = data[0];
            	$.each(result, function(index, value){
            		//console.log("getFilter=== "+value.BAYNAME);
            		$content.find(".bayName").append(""+
            		"<option value='"+value.BAYNAME+"'>"+value.BAYNAME+"</option>"); 
            	}); 
            }
	    });
	}, 500);
	
	setTimeout(function(){
		var url = "filter/ajax/getMachineNameList.do";	 
		var param = { "fabSite":fabSite }; // 파라메터
		$.ajax({
            url: url,
            type:'get',
            data: param,
            dataType: 'json',
            success:function(data){
            	var result = data[0];
            	$.each(result, function(index, value){
            		$content.find(".machineName1").append(""+
            		"<option value='"+value.MACHINENAME+"'>"+value.MACHINENAME+"</option>");
            	});
            }
	    });
	}, 800);	
}

// 그리드 페이징 상태변경
function setPagerState(list){
	var rows = $content.find("#rows").val();  // 조회 row 사이즈
	var reload = $content.find("#reload").val(); // 조회 타입 ( 01 : refresh , 02 : append )
	var page = $content.find('#page').val(); // 현재 페이지
	if( list == null || list.length <= 0 || list.length < rows ){ // next 페이지 없을시,
		if(page == 1){  // 첫 페이지 시, prev 페이지 버튼 비활성
			$content.find(".ui-icon-seek-prev").addClass("ui-state-disabled");
		}else{ // 첫 페이지가 아닐 시, 조회 타입이 refresh 인경우, prev 페이지버튼 활성
			if(reload != "02"){ 
				$content.find(".ui-icon-seek-prev").removeClass("ui-state-disabled");
			}
		}
	    $content.find(".ui-icon-seek-next").addClass("ui-state-disabled"); // 다음 페이지 버튼 비활성
	}else{ // next 페이지 존재시,
		if(reload != "02"){ //조회 타입이 refresh 이고 첫페이지가 아닌경우 , prev 페이지 버튼 활성 
			if(page != 1){
				$content.find(".ui-icon-seek-prev").removeClass("ui-state-disabled");
			}
		}
		$content.find(".ui-icon-seek-next").removeClass("ui-state-disabled"); // next 페이지 버튼 활성
    }
}

// Time Range 시간 , 분 , 초 세팅
function setSearchTime(from,to){
	$content.find("#fromHour").val(from.substr(0,2));
	$content.find("#fromMin").val(from.substr(2,2));
	$content.find("#fromSec").val(from.substr(4,2));
	$content.find("#toHour").val(to.substr(0,2));
	$content.find("#toMin").val(to.substr(2,2));
	$content.find("#toSec").val(to.substr(4,2));
}

// Time Range 시,분,초 ReadOnly 설정
function setSearchTimeReadOnly(readOnly){
	$content.find("#fromHour").attr("readOnly",readOnly);
	$content.find("#fromMin").attr("readOnly",readOnly);
	$content.find("#fromSec").attr("readOnly",readOnly);
	$content.find("#toHour").attr("readOnly",readOnly);
	$content.find("#toMin").attr("readOnly",readOnly);
	$content.find("#toSec").attr("readOnly",readOnly);
	// Specified Range 아닐시
	if(readOnly == "readOnly"){
		$content.find("input[name=fromDt],input[name=toDt]").prop('disabled', true); // 시작일 , 종료일 비활성
		$content.find("input[name=fromDt],input[name=toDt]").datepicker('disable');   // datepicker 비활성
		$content.find("#fromHour , #fromMin ,#fromSec ,#toHour , #toMin ,#toSec" ).spinner("disable"); // 시,분,초 입력 폼 비활성
	}else{  // Specified Range
		$content.find("input[name=fromDt],input[name=toDt]").prop('disabled', false); // 시작일, 종료일 활성
		$content.find("input[name=fromDt],input[name=toDt]").datepicker('enable');  // datepicker 활성
		$content.find("#fromHour , #fromMin ,#fromSec ,#toHour , #toMin ,#toSec" ).spinner("enable"); // 시,분,초 입력 폼 활성
	}
}

// 조회시 , 유효성 체크
function chkValidate(){
	if($content.find("input[name=fromDt]").length >= 1){ // Time Range 시작일이 종료일보다 큰경우
		var isPass = true;
		var startDt = getFromDate();
		var endDt = getToDate();
		if(startDt > endDt){
			alert("시작일이 종료일보다 큽니다. 다시 설정해 주십시오.");
			isPass = false;
		}
	}
	return isPass;
}

// 종료일 시작일 차이 조회
function getTimeRangeDiff(){
	var startDt = getFromDate();
	var endDt = getToDate();
	
	if(startDt > endDt){
		alert("시작일이 종료일보다 큽니다. 다시 설정해 주십시오.");
		return;
	}
	return endDt.getTime() -startDt.getTime();
}

// Time Range 시작일 종료일 설정( prev / next 클릭시 시간 재설정 )
function setTimeRange(btn , time){
	console.log("시간차이 설정 버튼 클릭 이벤트");
	
	var fromTime = getFromDate().getTime();
	var toTime = getToDate().getTime();
	if(btn == "prev"){  // prev 시 , 시작시간 종료시간 차이만큼 차감
		fromTime -= time;
		toTime -= time;
	}else if(btn == "next"){ // next 시, 시작시간 종료시간 차이만큼 증가
		fromTime += time;
		toTime += time;
	}
	// date -> string 후 time range 폼에 세팅..
	var fromDate = new Date(fromTime);
	var toDate = new Date(toTime);
	
	var _fromMon = fromDate.getMonth() +1;
	var _toMon = toDate.getMonth() +1;
	console.log(_fromMon);
	
	var from = fromDate.getFullYear()+	
	leadingZeros(_fromMon, 2 )
//	leadingZeros(fromDate.getMonth(),2)
	+leadingZeros(fromDate.getDate(),2)+
	leadingZeros(fromDate.getHours(),2)+leadingZeros(fromDate.getMinutes(),2)+leadingZeros(fromDate.getSeconds(),2);
	var to = toDate.getFullYear()+
	leadingZeros(_toMon ,2)
//	leadingZeros(toDate.getMonth(),2)
	+leadingZeros(toDate.getDate(),2)+
	leadingZeros(toDate.getHours(),2)+leadingZeros(toDate.getMinutes(),2)+leadingZeros(toDate.getSeconds(),2);
	setSearchTime(from.substring(8) , to.substring(8));
	var fromDt = from.substr(0,4)+"."+from.substr(4,2)+"."+from.substr(6,2);
	console.log(fromDt);
	$content.find("#fromDt"+curUuid).val(fromDt);
	var toDt = to.substr(0,4)+"."+to.substr(4,2)+"."+to.substr(6,2);
	$content.find("#toDt"+curUuid).val(toDt);
}

// Time Range 시작일 가져오기 convert string to date
function getFromDate(){
	var fromDt  = $content.find("input[name=fromDt]").val().toString().replace(/\./g, "");
	var fromYear = fromDt.substr(0,4);
	var fromMon = fromDt.substr(4,2);
	var fromDay = fromDt.substr(6,2);
	
	fromMon = parseInt(fromMon) - 1 ; 
	
	var fromHour = $content.find("#fromHour").val();
	var fromMin = $content.find("#fromMin").val();
	var fromSec = $content.find("#fromSec").val();
	return  new Date(fromYear,fromMon,fromDay,fromHour,fromMin,fromSec);
}

// Time Range 종료일 가져오기 convert string to date
function getToDate(){
	var toDt  = $content.find("input[name=toDt]").val().replace(/\./g, "");
	var toYear = toDt.substr(0,4);
	var toMon = toDt.substr(4,2);
	var toDay = toDt.substr(6,2);
	
	toMon = parseInt(toMon) - 1; 
	
	var toHour = $content.find("#toHour").val();
	var toMin = $content.find("#toMin").val();
	var toSec = $content.find("#toSec").val();
	return new Date(toYear,toMon ,toDay,toHour,toMin,toSec);
}

// 클립 보드 복사 하기..
function copyToClipboard(val) {
	 var hiddenClipboard = $('#_hiddenClipboard_');
	 if(!hiddenClipboard.length){
	     $('body').append('<textarea style="position:absolute;top: -9999px;" id="_hiddenClipboard_"></textarea>');
	     hiddenClipboard = $('#_hiddenClipboard_');
	 }
	 hiddenClipboard.html(val);
	 hiddenClipboard.select();
	 document.execCommand('copy');
	 document.getSelection().removeAllRanges();
}

// 그리드 cell font 색상 설정 (사용 안 함 )
function setCellColor(row, cell, value, columnDef, dataContext) {
	if( value == "ERROR" || value == "FATAL" ){
		return "<span class='level_red'>" + value + "</span>";
	}else{
		return value;
	}
}

// 그리드 마우스 오른버튼 클릭시 드롭다운 메뉴 생성
function drawDropDown(){
	$("#dropdownArea").empty(); // 드롭다운 초기화
	$("#tabList .tab_item").each(function(){ // 탭 갯수 만큼 드롭다운 메뉴 생성
		var $a = $("<a data-uuid='"+(this.id).substring(4)+"'></a>"); 
		var title = $(this).find(".tab_link").text(); // 탭 이름과 동일하게 메뉴 명 생성
		$a.text(title);
		$("#dropdownArea").append($a);
	})
}

// 드롭다운 메뉴 보임 / 숨김
function dropDownMenu(){
	var wTabMaster = $(".tab_master").width(); // 탭 표시 영역 가로 사이즈
	var wTabList = $("#tabList").width(); // 탭 생성 영역 가로 사이즈 
	if(wTabList > wTabMaster - 50){ // 실제 탭사이즈가 탭 표시 영역을 초과 할경우, 드롭다운 메뉴 표시
		$("#dropDownBtn").show();
	}else{
		$("#dropDownBtn").hide();
	}
}

// 화면 초기화 ( 리로드 )
function refresh(){
	location.reload();
}

// 검색옵션 Single Filter  / multi Filter설정
function setFilter(){
	var filter = $content.find("#filter").val();
	//console.log(filter);
	if(filter == "01"){ // Single Filter 입력폼 활성 / Multi Filter 입력폼 비활성
		$content.find("#singleFilter").prop("checked",true); 
		$content.find("#multiFilter").prop("checked",false);
		$content.find(".singleFilter").find(":checkbox").prop('checked',false);
		$content.find(".singleFilter").find("#machineType1").prop('checked',true);
		$content.find(".singleFilter").find("select , :checkbox").prop('disabled',false);
		$content.find(".multiFilter").find(":text").prop('disabled',true);
		$content.find("#machineBtn").addClass('disabled');
	}else{ // Single Filter 입력폼 비활성 / Multi Filter 입력폼 활성
		$content.find("#singleFilter").prop("checked",false);
		$content.find("#multiFilter").prop("checked",true);
		$content.find(".singleFilter").find(":checkbox").prop('checked',false);
		$content.find(".singleFilter").find("#machineType1").prop('checked',true);
		$content.find(".singleFilter").find("select , :checkbox").prop('disabled',true);
		$content.find(".multiFilter").find(":text").prop('disabled',false);
		$content.find("#machineBtn").removeClass('disabled');
	}
}

$(function(){
	$(document).ready(function() {
		// 숫자만 입력
		$(".onlynum").blur(function(){$(this).val( $(this).val().replace(/[^0-9]/g,"") );} );
		$(".onlynum").keyup(function(){$(this).val( $(this).val().replace(/[^0-9]/g,"") );} );
		// 영문만 입력
		$(".onlyeng").keyup(function(){$(this).val( $(this).val().replace(/[^\!-z]/g,"") );} );
	});
});

// form data 를 json object 형태로 가져오기
jQuery.fn.serializeObject = function() {
	  var obj = null;
	  try {
	    if ( this[0].tagName && this[0].tagName.toUpperCase() == "FORM" ) {
	      var arr = this.serializeArray();
	      if ( arr ) {
	        obj = {};
	        jQuery.each(arr, function() {
	          obj[this.name] = this.value;
	        });				
	      }//if ( arr ) {
	 	}
	  }
	  catch(e) {alert(e.message);}
	  finally  {}
	  return obj;
};
/*2021.03.24	X0122410 :	동일한 이름의 elements를 object형태로 변환*/
$.fn.serializeObject2 = function() {
	  "use strict"
	  var result = {}
	  var extend = function(i, element) {
	    var node = result[element.name]
	    if ("undefined" !== typeof node && node !== null) {
	      if ($.isArray(node)) {
	        node.push(element.value)
	      } else {
	        result[element.name] = [node, element.value]
	      }
	    } else {
	      result[element.name] = element.value
	    }
	  }
	
	  $.each(this.serializeArray(), extend)
	  return result
}

$(function(){
	// 	spinner numberFormat 사용시, 정의 필요
	if (!window.Globalize) window.Globalize = {
	        format: function(number, format) {
	                number = String(this.parseFloat(number, 10) * 1);
	                format = (m = String(format).match(/^[nd](\d+)$/)) ? m[1] : 2;
	                for (i = 0; i < format - number.length; i++)
	                        number = '0'+number;
	                return number;
	        },
	        parseFloat: function(number, radix) {
	                return parseFloat(number, radix || 10);
	        }
	}
	
	// startsWith 함수 정의
	if (!String.prototype.startsWith) {
	    String.prototype.startsWith = function(searchString, position){
	      position = position || 0;
	      return this.substr(position, searchString.length) === searchString;
	  };
	}
	
	// endsWith 함수 정의
	if (!String.prototype.endsWith) {
		  String.prototype.endsWith = function(searchString, position) {
		      var subjectString = this.toString();
		      if (typeof position !== 'number' || !isFinite(position) || Math.floor(position) !== position || position > subjectString.length) {
		        position = subjectString.length;
		      }
		      position -= searchString.length;
		      var lastIndex = subjectString.indexOf(searchString, position);
		      return lastIndex !== -1 && lastIndex === position;
		  };
	}
});

// Internet Explorer 체크
function isMsie() {
	var isIE = true;
    var ua = window.navigator.userAgent;
    var msie = ua.indexOf("MSIE ");

    if (msie > 0 || !!navigator.userAgent.match(/Trident.*rv\:11\./))  // If Internet Explorer, return version number
    {
        console.log(parseInt(ua.substring(msie + 5, ua.indexOf(".", msie))));
        isIE=true;
    }
    else  // If another browser, return 0
    {
    	console.log('otherbrowser');
        isIE = false;
    }
    return isIE;
}

//엑셀 다운로드
function downloadExcel(data){
	var date = new Date();
	var today = date.getFullYear()+""+leadingZeros((date.getMonth()+1),2)+""+date.getDate();
	JSONToCSVConvertor(data, today+"_log_exported", true,["key","_time"]);
}

//엑셀다운로드
function JSONToCSVConvertor(JSONData, ReportTitle, ShowLabel,exclude) {
    var arrData = typeof JSONData != 'object' ? JSON.parse(JSONData) : JSONData;
    
    var tempJson_text = '';
    var tempJson_time = '';

    var exportGrid;
    var columnInfo = '';
//    columnInfo = '<?xml version="1.0" encoding="UTF-8"?><?mso-application progid="Excel.Sheet"?>';
//    columnInfo +=' <Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" ';
//    columnInfo +=' xmlns:x="urn:schemas-microsoft-com:office:excel" ';
//    columnInfo +=' xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet" ';
//    columnInfo +=' xmlns:html="http://www.w3.org/TR/REC-html40">';
    if (ShowLabel) {
    	columnInfo += '<table border="1px" style="font-size:11px"><tr bgcolor="#DFDFDF">';
        var row = "";
        for (var index in arrData[0]) {
        	if($.inArray( index, exclude ) == -1){
        		
        		columnInfo += '<th>'+index+'</th>';        					 
        	}
        }
        columnInfo += '</tr>';
     }
//    console.log(columnInfo);

    for (var i = 0; i < arrData.length ; i++) {
        var row = "";
        columnInfo += "<tbody><tr style='table-layout:fixed; height: 15px'>";
        var time_ex_temp = '';
        var text_temp = '';
        if(arrData[i].TEXT !=null){
//        	console.log(arrData[i].TEXT + "\n");
	        	arrData[i].TEXT = arrData[i].TEXT.replace(/\</g,' < ');
	            arrData[i].TEXT = arrData[i].TEXT.replace(/\>/g,' > ');
	            arrData[i].TEXT = arrData[i].TEXT.replace(/\@+/g,'');
	            arrData[i].TEXT = arrData[i].TEXT.replace(/\r+/g,'');        		
	            arrData[i].TEXT = arrData[i].TEXT.replace(/\n+/g,'');        		
	            arrData[i].TEXT = arrData[i].TEXT.replace(/\t+/g,'');        		
	            arrData[i].TEXT = arrData[i].TEXT.replace(/\,+/g,'\.');
            }
        
        if(arrData[i].TIME_EX != null){
	        arrData[i].TIME_EX = "@"+arrData[i].TIME_EX+"$";
	        arrData[i].TIME_EX = arrData[i].TIME_EX.replace(/@+/g,'\[');
	        arrData[i].TIME_EX = arrData[i].TIME_EX.replace(/\$+/g,'\]');
        }
        if(arrData[i].TRANSACTIONID != null){
        	arrData[i].TRANSACTIONID = arrData[i].TRANSACTIONID != null ? "@"+arrData[i].TRANSACTIONID : null ;
        	arrData[i].TRANSACTIONID ="@" + arrData[i].TRANSACTIONID;
        }
        for (var index in arrData[i]) {        	
        	if($.inArray( index, exclude ) == -1){
        		columnInfo +="<td>" + (arrData[i][index]==null?'':arrData[i][index]) +"</td>";
        	}
        }
        columnInfo +="</tr>";
        columnInfo = columnInfo.replace(/@+/g,'\'');
    }
    columnInfo +="</tbody></table>";
    
    var fileName = "";
    fileName += ReportTitle.replace(/ /g,"_");   
    if (isMsie()) { // 인터넷 익스플로러
    	var IEwindow = window.open("", "_blank", "left="+(screen.width*2)+",top=0, width=1,height=1");
    	IEwindow.document.write(columnInfo);
    	IEwindow.document.close();
    	IEwindow.document.execCommand('SaveAs', true, fileName + ".xls");
    	IEwindow.close();
    }else{	// 기타 브라우저 ( 크롬 , 파이어폭스 등.. )
    	var uri = 'data:text/csv;charset=ansi,' + escape(columnInfo);
    	var link = document.createElement("a");    
    	link.href = uri;
    	link.style = "visibility:hidden";
    	link.download = fileName + ".xls";
    	document.body.appendChild(link);
    	link.click();
    	document.body.removeChild(link);
    }
}

	// 200625 hgJeon Javascript Map 구조 구현 code 추가
	Map = function(){
	  this.map = new Object();
	 };   
	 Map.prototype = {   
	     put : function(key, value){   
	         this.map[key] = value;
	     },   
	     get : function(key){   
	         return this.map[key];
	     },
	     containsKey : function(key){    
	      return key in this.map;
	     },
	     containsValue : function(value){    
	      for(var prop in this.map){
	       if(this.map[prop] == value) return true;
	      }
	      return false;
	     },
	     isEmpty : function(key){    
	      return (this.size() == 0);
	     },
	     clear : function(){   
	      for(var prop in this.map){
	       delete this.map[prop];
	      }
	     },
	     remove : function(key){    
	      delete this.map[key];
	     },
	     keys : function(){   
	         var keys = new Array();   
	         for(var prop in this.map){   
	             keys.push(prop);
	         }   
	         return keys;
	     },
	     values : function(){   
	      var values = new Array();   
	         for(var prop in this.map){   
	          values.push(this.map[prop]);
	         }   
	         return values;
	     },
	     size : function(){
	       var count = 0;
	       for (var prop in this.map) {
	         count++;
	       }
	       return count;
	     }
	 };

	 // 200702 hgJeon resize 기능 통합위해 js 추가
	 /*var doit;
		window.onresize = function(){
		  clearTimeout(doit);
		  doit = setTimeout(resizedw, 1000);
		  console.log("common.js");
	};*/


// 엑셀다운로드
//function JSONToCSVConvertor(JSONData, ReportTitle, ShowLabel,exclude) {
//    var arrData = typeof JSONData != 'object' ? JSON.parse(JSONData) : JSONData;
//    var CSV = '';    
//
//    CSV += ReportTitle + '\r\n\n';
//
//    if (ShowLabel) {
//        var row = "";
//
//        for (var index in arrData[0]) {
//        	if($.inArray( index, exclude ) == -1){
//        		row += index + ',';
//        	}
//        }
//
//        row = row.slice(0, -1);
//        CSV += row + '\r\n';
//    }
//
//    for (var i = 0; i < arrData.length; i++) {
//        var row = "";
//
//        for (var index in arrData[i]) {
//        	if($.inArray( index, exclude ) == -1){
//        		row += '" ' + (arrData[i][index]==null?'':arrData[i][index])+ ' ",';
//        	}
//        }
//
//        row.slice(0, row.length - 1);
//        CSV += row + '\r\n';
//    }
//
//    if (CSV == '') {        
//        alert("Invalid data");
//        return;
//    }   
//
//    var fileName = "";
//    fileName += ReportTitle.replace(/ /g,"_");   
//    if (isMsie()) { // 인터넷 익스플로러
//    	var IEwindow = window.open("", "_blank", "left="+(screen.width*2)+",top=0, width=1,height=1");
//    	IEwindow.document.write('sep=,\r\n' + CSV);
//    	IEwindow.document.close();
//    	IEwindow.document.execCommand('SaveAs', true, fileName + ".csv");
//    	IEwindow.close();
//    }else{	// 기타 브라우저 ( 크롬 , 파이어폭스 등.. )
//    	var uri = 'data:text/csv;charset=utf-8,' + escape(CSV);
//    	var link = document.createElement("a");    
//    	link.href = uri;
//    	link.style = "visibility:hidden";
//    	link.download = fileName + ".csv";
//    	document.body.appendChild(link);
//    	link.click();
//    	document.body.removeChild(link);
//    }
//}
