var StringBuffer = function(){
	this.buffer = new Array();
}

StringBuffer.prototype.append = function(obj){
	this.buffer.push(obj);	
}

StringBuffer.prototype.toString = function(){
	return this.buffer.join("");	
}

var commonWord = {
	space : ' ',
	equal : '=',
	pipe : ' | ',
	and : ' and ',
	or : ' or ',
	doubleQ : '\"',
	fulltext : 'fulltext',
	from : ' from',
	to : ' to',
	limit : ' limit'
}

function filterOptionParser(serializedArgs){
	
	var argsArray = serializedArgs.split('&');
	var fromDate = argsArray[0].replace('fromDate=','').replace('.','');
	var fromTime = argsArray[1].replace('fromTime=','').replace('%3A','');
	var toDate = argsArray[2].replace('toDate=','').replace('.','');
	var toTime = argsArray[3].replace('toTime=','').replace('%3A','');
	var interval = argsArray[4].replace('interval=','');
	var system = argsArray[5].replace('system=','');
	var fab = argsArray[6].replace('fab=','');
	var keyword = argsArray[7].replace('keyword=',''); //keyword 형태(keyword=field1=value1;field2=value2;field3=value3)
	var rowNum = argsArray[8];
	var pageNum = argsArray[9];
	var keywordArray = keyword.split(';');	
	var fromMergedTime;
	var toMergedTime;
	
	if(fromDate=='' || fromTime==''){
		var time = new Date();
		fromMergedTime = time.getFullYear()+time.getHours()+time.getMinutes()+time.getSeconds();
	}else{
		fromMergedTime = fromDate + fromTime;
	}
	
	if(toDate=='' || toTime==''){
		var time = new Date();
		if(Number(time.getMinutes())>=10){
			toMergedTime = time.getFullYear()+time.getHours()+(Number(time.getMinutes())-10)+time.getSeconds();
		}else{
			toMergedTime = time.getFullYear()+(time.getHours()-1)+(60+Number(time.getMinutes())-10)+time.getSeconds();
		}
	}else{
		toMergedTime = toDate + toTime;
	}
	
	// ''일 경우 system default를 apc로 설정, 
	if(system=''){
		system = 'apc_data';
	}else{
		system += '_data';
	}
	
	var parsedArgs = {
		argsArray :	argsArray,
		fromTime : fromMergedTime,
		toTime : toMergedTime,
		interval : interval,
		system : system,
		fab : fab,
		keyword : keywordArray,
		rowNum : rowNum,
		pageNum : pageNum
	}
	
	return parsedArgs;
}

function queryManager(args){
	
	var parsedArgs = filterOptionParser(args);
	var query = commonWord.fulltext;
	var strBuffer = new StringBuffer();
	
	//time 설정
	strBuffer.append(commonWord.space);
	strBuffer.append(commonWord.from);
	strBuffer.append(commonWord.equal);
	strBuffer.append(parsedArgs.fromTime);
	strBuffer.append(commonWord.space);
	strBuffer.append(commonWord.to);
	strBuffer.append(commonWord.equal);
	strBuffer.append(parsedArgs.toTime);
	
	//keyword 설정
	var keywordArraySize = parsedArgs.keyword.length;
	var keywordArray = parsedArgs.keyword;
	var tmpArray = new Array();
	for(var i=0;i<keywordArraySize;i++){
		tmpArray = keywordArray[i].split('=');
		if(i==0){
			strBuffer.append(commonWord.space);
			strBuffer.append(tmpArray[0]);
			strBuffer.append(commonWord.equal);
			strBuffer.append(commonWord.doubleQ);
			strBuffer.append(tmpArray[1]);
			strBuffer.append(commonWord.doubleQ);
			strBuffer.append(commonWord.and);
		}else if(i==(keywordArraySize-1)){
			strBuffer.append(tmpArray[0]);
			strBuffer.append(commonWord.equal);
			strBuffer.append(commonWord.doubleQ);
			strBuffer.append(tmpArray[1]);
			strBuffer.append(commonWord.doubleQ);
		}else{
			strBuffer.append(tmpArray[0]);
			strBuffer.append(commonWord.equal);
			strBuffer.append(commonWord.doubleQ);
			strBuffer.append(tmpArray[1]);
			strBuffer.append(commonWord.doubleQ);
			strBuffer.append(commonWord.and);
		}
	}
	
	//table 설정
	strBuffer.append(commonWord.from);
	strBuffer.append(commonWord.space);
	strBuffer.append(parsedArgs.system);
	
	//limit 설정
	if(parsedArgs.pageNum=='1'){
		strBuffer.append(commonWord.pipe);
		strBuffer.append(commonWord.limit);
		strBuffer.append(parsedArgs.rowNum);
	}else{
		var offset = ""+(Number(parsedArgs.rowNum)*Number(parsedArgs.pageNum));
		strBuffer.append(commonWord.pipe);
		strBuffer.append(commonWord.limit);
		strBuffer.append(offset);
		strBuffer.append(commonWord.space);
		strBuffer.append(parsedArgs.rowNum);
	}
	
	query += strBuffer.toString();
	
	console.log('query(queryManager) : ' + query);
	return query;
}

var instance;	//serviceLogdb 인스턴스
var pid = Math.floor(Math.random() * 1000) + 1;
function getResult(query){
	
	if(instance != undefined) {
        serviceLogdb.remove(instance);
    }
	
	instance = undefined;
	
	if(query != ''){
		instance = serviceLogdb.create(pid);
		var q = instance.query(query, 300);
		q.created(function (m){
			
		}).onTail(function (helper){
			helper.getResult(function (m){
				$scope.result = m.body.result;
				console.log('query result : ' + $scope.result);
				$scope.$apply();
			});
		}).failed(function (m, raw){
			console.log('query failed', m, raw);
		});
	}
	
}