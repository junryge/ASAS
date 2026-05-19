(function() {
    app.register.controller('HelloAppController', function HelloAppController($scope, serviceLogdb, $compile) {
        var pid = 9999;
        var pid2 = 8888;
        var pid3 = 7777;
        var instance1;
        var instance2;
        var rowSkipCount = 0;
        var rowViewCount = 50;
        var LimitPhrase = " | limit " +rowSkipCount+" "+rowViewCount+"";
        var queryBeforeLimitPhrase = "table phase2Line | parse phase2Line | sort -Date | eval Unit = right(Unit, 2) | eval no = seq()";
        var initialQuery = "table phase2Line | parse phase2Line | sort -Date | eval Unit = right(Unit, 2)  | eval no = seq() | limit 50";
        var query = "table phase2Line | parse phase2Line | sort -Date | eval Unit = right(Unit, 2) | eval no = seq()";
        var queryForCountInit = "table phase2Line | parse phase2Line | sort -Date | eval Unit = right(Unit, 2) | eval no = seq()"
        var queryForCount = queryForCountInit + " | stats count";
        var queryForCountAfter = query + " | stats count";
        var rowViewCountInit = 0;
        var listCount;
        var pageNum = 1;
        var pageSize = rowViewCount;  /*한 페이지당 몇개의 행을 보여주는 것에 관한 변수*/
        var pageGroupSize = 10;
        var maxPage;
        var numPageGroup;
        var startPage;
        var endPage;
        var searchQueryBoolean = 0;
        var getChartValQuery = "table phase2Line | parse phase2Line | search RTN_VAL == "+'"'+"ERROR"+'"'+" | stats count(RTN_VAL) as ERROR by Machine | join type=full Machine [table phase2Line | parse phase2Line | search RTN_VAL == "+'"'+"WARNING"+'"'+" | stats count(RTN_VAL) as WARING by Machine] | join type=full Machine [table phase2Line | parse phase2Line | search RTN_VAL == "+'"'+"NG"+'"'+"  | stats count(RTN_VAL) as NG by Machine] | join type=full Machine [table phase2Line | parse phase2Line | search RTN_VAL == "+'"'+"BM"+'"'+" | stats count(RTN_VAL) as BM by Machine] | join type=full Machine [table phase2Line | parse phase2Line | search RTN_VAL == "+'"'+"OK"+'"'+"  | stats count(RTN_VAL) as OK by Machine]"
        var chartValues;

        $scope.xAxis=[];
        $scope.result=[];
        $scope.myArray=[];
        $scope.fromDate = '';
        $scope.toDate = '';
        /*$scope.tableName='sys_cpu_logs';
        var tbname = $scope.tableName; */

        $scope.init = function() {
            getResult(initialQuery, queryForCount);
            getChartValues(getChartValQuery);
        };

        $scope.init();

        function getResult(query, queryForCount) {
            console.log('getResult function query : ' + query);
            console.log('getResult function queryForCount : ' + queryForCount);
            if(instance1 != undefined) {
                serviceLogdb.remove(instance1);
            }

            instance1 = undefined;

            if(instance2 != undefined) {
                serviceLogdb.remove(instance2);
            }

            instance2 = undefined;
            instance3 = undefined;
            //로그 쿼리 인스턴스 생성
            if(query != ""){
                instance1 = serviceLogdb.create(pid);
                var q1 = instance1.query(query, 300);
                console.log('query executed');
                q1.created(function (m) {
                    console.log('created.body', m.body);
                    $scope.result = [];
                    $scope.count = [];
                }).onTail(function (helper) {
                    helper.getResult(function (m) {
                        $scope.result = m.body.result;
                        console.log('result?', $scope.result);
                        $scope.$apply();

                       /* if(searchQueryBoolean == 0){
                           getResult("", queryForCount);
                        }*/

                    });


                    //쿼리 종료후 인스턴스 삭제
                    serviceLogdb.remove(instance1);

                }).failed(function (m, raw) {
                    console.log('failed', m, raw);
                });


            }

            if(queryForCount != ""){
                instance2 = serviceLogdb.create(pid2);
                var q2 = instance2.query(queryForCount, 300);
                console.log('queryForCount executed');
                q2.created(function (m) {
                    console.log('created', m);
                    $scope.count = [];
                }).onTail(function (helper) {
                    helper.getResult(function (m) {
                        $scope.count = m.body.result[0].count;
                        console.log(' $scope.count : ' +  $scope.count);
                        listCount = $scope.count;
                        $scope.$apply();
                        $('#rowCount').text($scope.count+' 건 검색됨');

                        maxPage = Math.floor($scope.count / pageSize) + ($scope.count % pageSize == 0 ? 0 : 1);
                        numPageGroup = Math.ceil (pageNum / pageGroupSize);
                        startPage = (numPageGroup - 1)*pageGroupSize + 1;
                        endPage = startPage + pageGroupSize - 1;
                        if(endPage>maxPage){
                            endPage = maxPage;
                        }
                        console.log('startPage : ' + startPage +', endPage : ' + endPage + ', maxPage : ' + maxPage +', numPageGroup : ' + numPageGroup);
                        $('#pagingButtonGroup').empty();
                        $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage(1)'>처음</div>");
                        if((Number(startPage) - Number(pageGroupSize)) < 1){
                            $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage(1)'>이전</div>");
                        }else{
                            $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+(Number(startPage) - Number(pageGroupSize))+")'>이전</div>");
                        }
                        for(i=startPage;i<=endPage;i++){
                            $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+i+")'>"+i+"</div>");
                        }
                        console.log('pageGroupSize : ' + pageGroupSize);
                        console.log('endPage : ' + endPage);
                        console.log('endPage + pageGroupSize : ' + (Number(endPage) + Number(pageGroupSize)));
                        if(Number(endPage) + Number(pageGroupSize) > maxPage){
                            $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+maxPage+")'>다음</div>");
                        }else{
                            $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+(Number(endPage) +1)+")'>다음</div>");
                        }
                        $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+maxPage+")'>마지막</div>");
                    });
                    searchQueryBoolean == 0;
                    //쿼리 종료후 인스턴스 삭제
                    serviceLogdb.remove(instance2);

                }).failed(function (m, raw) {
                    console.log('failed', m, raw);
                });
            }


        }

        function getChartValues(getChartValQuery){
            console.log('getUnitQuery : ' + getChartValQuery);
            instance3 = serviceLogdb.create(pid3);
            var q3 = instance3.query(getChartValQuery, 300);
            q3.created(function (m) {
                $scope.xAxis=[];
            }).onTail(function (helper) {
                helper.getResult(function (m) {
                    console.log('created', m);
                    $scope.xAxis = m.body.result;
                    chartValues =  $scope.xAxis;
                    console.log('m.body.result : ' + m.body.result[0]);
                    console.log('$scope.xAxis : ' + $scope.xAxis);
                    $scope.$apply();

                   /* if(searchQueryBoolean == 0){
                       getResult("", queryForCount);
                    }*/

                });
                serviceLogdb.remove(instance3);

            }).failed(function (m, raw) {
                console.log('failed', m, raw);
            });
        }
        /*function getResultCount(queryForCount) {
            console.log('getResultCount function query : ' + queryForCount);

            if(instance != undefined) {
                serviceLogdb.remove(instance);
            }

            instance = undefined;

            //로그 쿼리 인스턴스 생성
            instance = serviceLogdb.create(pid);
            var q = instance.query(queryForCount, 5000);

            q.created(function (m) {
                console.log('created', m);
                $scope.count = [];
            }).onTail(function (helper) {
                helper.getResult(function (m) {
                    $scope.count = m.body.result[0].count;
                    console.log(' $scope.count : ' +  $scope.count);
                    listCount = $scope.count;
                    $scope.$apply();
                    $('#rowCount').text($scope.count+' 건 검색됨');

                    maxPage = Math.floor($scope.count / pageSize) + ($scope.count % pageSize == 0 ? 0 : 1);
                    numPageGroup = Math.ceil (pageNum / pageGroupSize);
                    startPage = (numPageGroup - 1)*pageGroupSize + 1;
                    endPage = startPage + pageGroupSize - 1;
                    if(endPage>maxPage){
                        endPage = maxPage;
                    }
                    console.log('startPage : ' + startPage +', endPage : ' + endPage + ', maxPage : ' + maxPage +', numPageGroup : ' + numPageGroup);
                    $('#pagingButtonGroup').empty();
                    $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage($event)'>처음</div>");
                    if((startPage - pageGroupSize) < 1){
                        $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage(1)'>이전</div>");
                    }else{
                        $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+(Number(startPage) - Number(pageGroupSize))+")'>이전</div>");
                    }
                    for(i=startPage;i<=endPage;i++){
                        $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+i+")'>"+i+"</div>");
                    }
                    if(endPage + pageGroupSize > maxPage){
                        $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+maxPage+")'>다음</div>");
                    }else{
                        $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+(Number(endPage) + Number(pageGroupSize))+")'>다음</div>");
                    }
                    $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+maxPage+")'>마지막</div>");
                });
                searchQueryBoolean == 0;
                //쿼리 종료후 인스턴스 삭제
                serviceLogdb.remove(instance);

            }).failed(function (m, raw) {
                console.log('failed', m, raw);
            });
        }*/

        $(document).on('click','.pageButton',function(){
            $scope.getThisPage($(this).text());
        })

        $scope.getRawData =  function($event){
            console.log('clicked');
            console.log($event.currentTarget.id);
            var queryForRaw = 'table phase2Line | search _id ==' + $event.currentTarget.id + '| fields line';

            if(instance1 != undefined) {
                serviceLogdb.remove(instance1);
            }

            instance1 = undefined;

            instance1 = serviceLogdb.create(pid);
            var q = instance1.query(queryForRaw, 1);

            q.created(function (m) {
                console.log('created', m);
                $scope.rawData = [];
            }).onTail(function (helper) {
                helper.getResult(function (m) {
                    $scope.rawData = m.body.result[0].line;
                    $scope.$apply();
                    $('#rawDataWrite').text($scope.rawData);
                   /* $('#rawDataModal').modal('show');*/
                });

                //쿼리 종료후 인스턴스 삭제
                serviceLogdb.remove(instance1);

            }).failed(function (m, raw) {
                console.log('failed', m, raw);
            });
        }

        $scope.getThisPage = function(clickedPageNum){
            var beforeNextCheck = clickedPageNum;
            console.log('clickedPageNum : ' + clickedPageNum);
            if(clickedPageNum === '처음'){
                clickedPageNum = 1;
                console.log('clickedPageNum : ' + clickedPageNum);
            }else if(clickedPageNum === '이전'){
                if(Number(startPage) - Number(pageGroupSize) >= 1){
                    clickedPageNum = Number(startPage) - Number(pageGroupSize);
                }else{
                    clickedPageNum = 1;
                }
                console.log('clickedPageNum : ' + clickedPageNum);
            }else if(clickedPageNum === '다음'){
                if(Number(endPage) + Number(pageGroupSize) <= maxPage){
                    clickedPageNum = Number(endPage) + 1;
                }else{
                    clickedPageNum = maxPage;
                }
                console.log('clickedPageNum : ' + clickedPageNum);
            }else if(clickedPageNum === '마지막'){
                clickedPageNum = maxPage;
                console.log('clickedPageNum : ' + clickedPageNum);
            }
            rowSkipCount = Number(clickedPageNum-1)*rowViewCount;
            LimitPhrase = " | limit " +rowSkipCount+" "+rowViewCount+"";
            var tmpQuery = query;

          /*  maxPage = Math.floor(listCount / pageSize) + (listCount % pageSize == 0 ? 0 : 1);
            numPageGroup = Math.ceil (pageNum / pageGroupSize);
            startPage = (numPageGroup - 1)*pageGroupSize + 1;
            endPage = startPage + pageGroupSize - 1;
            if(endPage>maxPage){
                endPage = maxPage;
            }*/
            if(beforeNextCheck === '이전' | beforeNextCheck ==='다음' | beforeNextCheck ==='처음'| beforeNextCheck ==='마지막'){
                maxPage = Math.floor(listCount / pageSize) + (listCount % pageSize == 0 ? 0 : 1);
                numPageGroup = Math.ceil (clickedPageNum / pageGroupSize);
                startPage = (numPageGroup - 1)*pageGroupSize + 1;
                endPage = startPage + pageGroupSize - 1;
                if(endPage>maxPage){
                    endPage = maxPage;
                }
                console.log('startPage : ' + startPage +', endPage : ' + endPage + ', maxPage : ' + maxPage +', numPageGroup : ' + numPageGroup);
                $('#pagingButtonGroup').empty();
                $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage(1)'>처음</div>");
                if((Number(startPage) - Number(pageGroupSize)) < 1){
                    $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage(1)'>이전</div>");
                }else{
                    $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+(Number(startPage) - Number(pageGroupSize))+")'>이전</div>");
                }
                for(i=startPage;i<=endPage;i++){
                    $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+i+")'>"+i+"</div>");
                }
                console.log('pageGroupSize : ' + pageGroupSize);
                console.log('endPage : ' + endPage);
                console.log('endPage + pageGroupSize : ' + (Number(endPage) + Number(pageGroupSize)));
                if(Number(endPage) + Number(pageGroupSize) > maxPage){
                    $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+maxPage+")'>다음</div>");
                }else{
                    $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+(Number(endPage) +1)+")'>다음</div>");
                }
                $('#pagingButtonGroup').append("<div class='ui button pageButton' ng-click='getThisPage("+maxPage+")'>마지막</div>");
            }

            queryBeforeLimitPhrase = query + LimitPhrase;
            getResult(queryBeforeLimitPhrase, "");
            query = tmpQuery;

            if(instance1 != undefined) {
                serviceLogdb.remove(instance1);
            }

            instance1 = undefined;

            instance1 = serviceLogdb.create(pid);
            var q = instance1.query(query, 1);

            q.created(function (m) {
                console.log('created', m);
                $scope.rawData = [];
            }).onTail(function (helper) {
                helper.getResult(function (m) {
                    $scope.rawData = m.body.result[0].line;
                    $scope.$apply();
                    $('#rawDataWrite').text($scope.rawData);
                    $('#rawDataModal').modal('show');
                });

                //쿼리 종료후 인스턴스 삭제
                serviceLogdb.remove(instance1);

            }).failed(function (m, raw) {
                console.log('failed', m, raw);
            });
        }

        $scope.search =  function($event){
            pageNum = 1;
            searchQueryBoolean = 1;
            $scope.rawData = '';
            query = 'table';
            var fromDate = '"'+$('#fromDate').val()+'"';
            var toDate = '"'+$('#toDate').val()+'"';
            var message_id = $('#message_id').val();
            var facility = $(':radio[name="facility"]:checked').next().text();
            var machine = $(':radio[name="machine"]:checked').next().text();

            var checkedCount = $(':checkbox[name="unit"]:checked').next().text().length / 2 ;
            var checkedValArray = [];

            for(i=0;i<checkedCount;i++){
                checkedValArray.push($(':checkbox[name="unit"]:checked').next().text().substring(i*2,i*2+2));
            }

            if(fromDate != '""'){
                var fromDateArray = fromDate.split('-');
                var fromDateTrans = '';
                for(i=0;i<fromDateArray.length;i++){
                    fromDateTrans += fromDateArray[i];
                }
                query += ' from='+ fromDateTrans;
            }

            if(toDate != '""'){
                var toDateArray = toDate.split('-');
                var toDateTrans = '';
                for(i=0;i<toDateArray.length;i++){
                    toDateTrans += toDateArray[i];
                }
                query += ' to='+ toDateTrans;
            }

            query += ' phase2Line | parse phase2Line | sort -Date | eval Unit = right(Unit, 2)';

            if(message_id != ''){
                if(message_id != 'ALL'){
                    query += ' | search Message_id=="' +message_id+'"';
                }
            }

            if(facility != ''){
                if(facility != 'ALL'){
                    query += ' | search Facility=="' +facility+'"';
                }
            }

            if(machine != ''){
                query += ' | search Machine=="' +machine+'"';
            }

            if(checkedValArray.length != 0 ){
                for(i=0;i<checkedValArray.length;i++){
                    if(i==0){
                        query += ' | search Unit=="' +checkedValArray[i]+'"';
                    }else{
                        query += ' or Unit=="'+checkedValArray[i]+'"';
                    }
                }
            }
            var tmpPageSize = $('#rowViewCount').dropdown('get value') + '';
            var tmpQuery = query;
            var tmpQueryForCount = query + " | stats count";
            query += '| eval no = seq() | limit 0 '+tmpPageSize;
            console.log('query : ' + query);

            getResult(query, tmpQueryForCount);
            query = tmpQuery + '| eval no = seq()' ;
        }

        $('#rowViewCount').change(function(){
            pageSize = $('#rowViewCount').dropdown('get value');
            rowSkipCount = 0;
            rowViewCount = pageSize;
            console.log('pageSize :' + pageSize);
            maxPage = Math.floor(listCount / pageSize) + (listCount % pageSize == 0 ? 0 : 1);
            numPageGroup = Math.ceil (pageNum / pageGroupSize);
            startPage = (numPageGroup - 1)*pageGroupSize + 1;
            endPage = startPage + pageGroupSize - 1;
            if(endPage>maxPage){
                endPage = maxPage;
            }
            console.log('다시 계산한 maxPage : ' + maxPage);
            queryBeforeLimitPhrase = query;
            LimitPhrase = " | limit " +rowSkipCount+" "+rowViewCount+"";
            var queryBeforeLimitPhraseCount = queryBeforeLimitPhrase + "| stats count"
            console.log("드가기 전 query count : "+ queryBeforeLimitPhraseCount);
            queryBeforeLimitPhrase = queryBeforeLimitPhrase + LimitPhrase;
            if(rowViewCountInit != 0){
                getResult(queryBeforeLimitPhrase, queryBeforeLimitPhraseCount);
                queryBeforeLimitPhrase = query;
            }
            rowViewCountInit++;
        });

        $(document).on('click','.historySearch',function(){
          var tmpContent = $(this).text();
          var itemName = $(this).attr('id');
          var tabName = Math.floor(Math.random() * (1000 - 1 + 1)) + 1 +"";
          $('.statTabClass').each(function(){
            $(this).removeClass('active');
          });
          $('.tabContent').each(function(){
            $(this).removeClass('active');
          });
          $('.tabHeader').append(""+
          "<div class='ui bottom attached tab segment tabContent active' data-tab='"+tabName+"'>"+$(this).text()+"</div>");
          $('.tabIconWrapper').append("<a class='statTabClass teal item active' data-tab='"+tabName+"'>"+$(this).text()+
          "&nbsp;&nbsp;&nbsp;"+
          " <i class='large remove circle icon tabRemove'></i>"+
          "</a>");
          // topMenu.historyMenu(itemName, tabName);

          if(itemName === 'history4'){
            $('.tabContent').each(function(){
              if($(this).attr('data-tab') === tabName){
                $(this).empty();
                $(this).append($compile(
                  "<div class='ui column tableHeaderWrapper'>"+
                  "<table class='ui table tableHeader'>"+
                  " <tr>"+
                  "   <th class='tableHead tableHeadNo'>No</th>"+
                  "   <th class='tableHead tableHeadLong'>Date</th>"+
                  "   <th class='tableHead tableHeadShort'>Message_id</th>"+
                  "   <th class='tableHead tableHeadShort'>Facility</th>"+
                  "   <th class='tableHead tableHeadShort'>Machine</th>"+
                  "   <th class='tableHead tableHeadShort'>Unit</th>"+
                  "   <th class='tableHead tableHeadShort'>RTN_CODE</th>"+
                  "   <th class='tableHead tableHeadShort'>RTN_VAL</th>"+
                  " </tr>"+
                  "</table>"+
                  "</div>"+
                  "<div class='ui column tableBodyWrapper'>"+
                  "<table class='ui blue striped selectable table tableBody'>"+
                  " <tr ng-repeat='row in result'>"+
                  "   <td class='tableBodyNo'>{{row.no}}</td>"+
                  "   <td class='tableBodyLong'>{{row.Date}}</td>"+
                  "   <td class='tableBodyShort'>{{row.Message_id}}</td>"+
                  "   <td class='tableBodyShort'>{{row.Facility}}</td>"+
                  "   <td class='tableBodyShort'>{{row.Machine}}</td>"+
                  "   <td class='tableBodyShort'>{{row.Unit}}</td>"+
                  "   <td class='tableBodyShort'>{{row.RTN_CODE}}</td>"+
                  "   <td class='tableBodyShort'>{{row.RTN_VAL}}</td>"+
                  " </tr>"+
                  "</table>"+
                  "</div>"+
                  ""+
                  ""+
                  "")($scope));
                  getResult(query, queryForCount);
                }
              });
          }else if(itemName === ''){

          }else if(itemName === ''){

          }else if(itemName === ''){

          }else if(itemName === ''){

          }else{
            $('.tabContent').each(function(){
              if($(this).attr('data-tab') === tabName){
                $(this).empty();
                $(this).append(tmpContent);
                }
            });
          }
        });

        $(document).on('click', '.chartButton', function(){
            var xAxis = [];
            var yAxis = [];
            var result = chartValues;
            var error = new Array();
            var bm = [];
            var ng = [];
            var ok = [];
            var warning = [];

            for(i=0;i<result.length;i++){
                xAxis.push(result[i].Machine);
                error.push(result[i].ERROR);
                bm.push(result[i].BM);
                ng.push(result[i].NG);
                ok.push(result[i].OK);
                warning.push(result[i].WARING);
                console.log('result[i].ERROR : ' + result[i].ERROR);
            }
            yAxis.push({name : 'ERROR', data : error});
            yAxis.push({name : 'BM', data : bm});
            yAxis.push({name : 'NG', data : ng});
            yAxis.push({name : 'OK', data : ok});
            yAxis.push({name : 'WARNING', data : warning});
            console.log('yAxis[0].name : ' +yAxis[1].name + ", "+yAxis[1].data[0]);
            console.log('xAxis : ' + xAxis);
            drawChart(xAxis, yAxis);
            $('#chartModal').modal('show');
        });

        function drawChart(xAxis, yAxis) {
            Highcharts.chart('chartBody', {
                chart: {
                    type: 'column',
                    width: 1200,
                },
                title: {
                    text: '설비별 누적 Status'
                },
                xAxis: {
                    categories : xAxis
                    /*categories: ['Apples', 'Oranges', 'Pears', 'Grapes', 'Bananas']*/
                },
                yAxis: {
                    min: 0,
                    title: {
                        text: 'Total fruit consumption'
                    },
                    stackLabels: {
                        enabled: true,
                        style: {
                            fontWeight: 'bold',
                            color: (Highcharts.theme && Highcharts.theme.textColor) || 'gray'
                        }
                    }
                },
                legend: {
                    align: 'right',
                    x: -30,
                    verticalAlign: 'top',
                    y: 25,
                    floating: true,
                    backgroundColor: (Highcharts.theme && Highcharts.theme.background2) || 'white',
                    borderColor: '#CCC',
                    borderWidth: 1,
                    shadow: false
                },
                tooltip: {
                    headerFormat: '<b>{point.x}</b><br/>',
                    pointFormat: '{series.name}: {point.y}<br/>Total: {point.stackTotal}'
                },
                plotOptions: {
                    column: {
                        stacking: 'normal',
                        dataLabels: {
                            enabled: true,
                            color: (Highcharts.theme && Highcharts.theme.dataLabelsColor) || 'white'
                        }
                    }
                },
                series: yAxis
            });
        }
    });
})();
