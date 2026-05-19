var topMenu = topMenu || {};
topMenu.historyMenu = function(itemName, tabName){
  'use strict';
  switch (itemName) {
    case 'history4':
      topMenu.historyMenu.getAlarmHistory(tabName);
      break;

    case '2':

      break;
  }
}

// topMenu.historyMenu.getAlarmHistory = function(tabName){
//   'use strict';
//   $('.tabContent').each(function(){
//     if($(this).attr('data-tab') === tabName){
//       $(this).empty();
//       $(this).append(
//         "<table class='ui blue striped table'>"+
//         " <tr>"+
//         "   <th class='tableHead'>No</th>"+
//         "   <th class='tableHead'>Date</th>"+
//         "   <th class='tableHead'>Message_id</th>"+
//         "   <th class='tableHead'>Facility</th>"+
//         "   <th class='tableHead'>Machine</th>"+
//         "   <th class='tableHead'>Unit</th>"+
//         "   <th class='tableHead'>RTN_CODE</th>"+
//         "   <th class='tableHead'>RTN_VAL</th>"+
//         " </tr>"+
//         " <tr ng-repeat='row in result'>"+
//         "   <td>{{row.no}}</td>"+
//         "   <td>{{row.Date}}</td>"+
//         "   <td>{{row.Message_id}}</td>"+
//         "   <td>{{row.Facility}}</td>"+
//         "   <td>{{row.Machine}}</td>"+
//         "   <td>{{row.Unit}}</td>"+
//         "   <td>{{row.RTN_CODE}}</td>"+
//         "   <td>{{row.RTN_VAL}}</td>"+
//         " </tr>"+
//         "</table>");
//     }
//   });
// }

$(function(){

    $(document).on('mouseenter','.tabHeader',function(){
      $('.statTabClass.item').tab({cache : true});
    });

   /* $(document).on('click','.filterOption',function(){
      if($(this).children().eq(0).attr('class') === 'caret right icon'){
        $(this).children().eq(0).attr('class', 'caret down icon');
      }else{
        $(this).children().eq(0).attr('class', 'caret right icon');
      }

      $(this).next().transition('slide down');
    });*/

    $('.ui.radio.checkbox').checkbox();

    $('.specifiedFromTime').css('display','none');
    $('.specifiedToTime').css('display','none');
    $(document).on('click','.timeChk',function(){
      if($('.specifiedChk').checkbox('is checked')===true){
        $('.specifiedFromTime').css('display','');
        $('.specifiedToTime').css('display','');
      }else{
        $('.specifiedFromTime').css('display','none');
        $('.specifiedToTime').css('display','none');
      }
    });

    $(document).on('click','.transHistory',function(){

    });

    $('.dropdown').dropdown();
    $(document).on('click','.tabRemove',function(){
      var tabIconPos = $(this).parent().attr('data-tab');
      var nextTabName;
      $('.tabContent').each(function(){
        if($(this).attr('data-tab')=== tabIconPos){
          if($(this).next().attr('data-tab') === undefined || $(this).next().attr('data-tab') === ""){
            nextTabName = $(this).parent().children().children().eq(0).attr('data-tab');
          }else{
            nextTabName = $(this).next().attr('data-tab');
          }
          $(this).remove();
        }
      });
      $(this).parent().tab('change tab', nextTabName);
      $(this).parent().remove();
    });

    $(document).on('click', '.bar.chart.icon.menuIcon', function(){
      $('#chartModal').modal('show');
    });

    $(document).on('click', '#chartModalClose', function(){
      $('#chartModal').modal('hide');
    });

    /*$('#fromDate').datepicker({
        dateFormat : "yy-mm-dd",
        showOn: "both",
        showAnim: "slide",
        nextText: '다음 달',
        prevText: '이전 달',
        buttonImageOnly: true,
        buttonImage: "http://192.168.0.217:8080/Board/img/bookingImg/datePicker.png"
    });

    $('#toDate').datepicker({
        dateFormat : "yy-mm-dd",
        showOn: "both",
        showAnim: "slide",
        nextText: '다음 달',
        prevText: '이전 달',

    });

    $('.ui.radio.checkbox').checkbox();
    $('.ui.checkbox').checkbox();
    $(document).on('click','.chk1',function(){
        console.log("$(this).checkbox('set checked') : " + $(this).checkbox('is checked'));
        $('.chk1').checkbox('set unchecked');
        $(this).checkbox('set checked');
        if($(this).children().eq(1).text() === 'ALL'){
        	console.log('all clicked');
        	$('#machineCheck').checkbox('set unchecked');
        }

    });

    $(document).on('click','.chk2',function(){
        $('.chk2').checkbox('set unchecked');
        $(this).checkbox('set checked');
    });

    $(document).on('click','.chk3',function(){
        $('.chk3').checkbox('set unchecked');
        $(this).checkbox('set checked');
    });

    $(document).on('click','#machineCheck',function(){
        console.log("$('#machineCheck').checkbox('is checked') : " + $('#machineCheck').checkbox('is checked'));
        if($('#machineCheck').checkbox('is checked') === true){
            $('.machineDetail').attr('disabled', false);
            $('.unitCheckInput').attr('disabled', false);
        }else{
            $('.machineDetail').attr('disabled', true);
            $('.unitCheckInput').attr('disabled', true);
            $('.chk2').checkbox('set unchecked');
            $('.unitDetailCheck').checkbox('set unchecked');
            $('#unitCheck').checkbox('set unchecked');
            $('.unitDetail').attr('disabled', true);
        }
    });

    $(document).on('click','#unitCheck',function(){
        if($('#unitCheck').checkbox('is checked') === true){
            $('.unitDetail').attr('disabled', false);
        }else{
            $('.unitDetail').attr('disabled', true);
            $('.unitDetailCheck').checkbox('set unchecked');
        }
    });

    $(document).on('click','.gridTr',function(){
        console.log('$("#rawDataText").val() : ' + $('#rawDataText').val())
        $('#rawDataModalTextWrite').text($('#rawDataText').val());
        $('#rawDataModal').modal('show');
    });

    $(document).on('click','#rawDataModalBack',function(){
        $('#rawDataModal').modal('hide');
    });
    $(document).on('click','#searchButton',function(){
        $('#rawDataText').text('');
    });
    $('#rowViewCount').dropdown('set value',50) ;
    $(document).on('click','#rowViewCount',function(){
        console.log("$('#rowViewCount').dropdown('get value') : "+$('#rowViewCount').dropdown('get value'));
    });

    $('#rowViewCount').dropdown();

    Highcharts.chart('chartSegment', {
        chart: {
            type: 'line'
        },
        title: {
            text: 'Monthly Average Temperature'
        },
        subtitle: {

        },
        xAxis: {
            categories: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        },
        yAxis: {
            title: {
                text: 'Temperature (°C)'
            }
        },
        plotOptions: {
            line: {
                dataLabels: {
                    enabled: true
                },
                enableMouseTracking: false
            }
        },
        series: [{
            name: 'Tokyo',
            data: [7.0, 6.9, 9.5, 14.5, 18.4, 21.5, 25.2, 26.5, 23.3, 18.3, 13.9, 9.6]
        }, {
            name: 'London',
            data: [3.9, 4.2, 5.7, 8.5, 11.9, 15.2, 17.0, 16.6, 14.2, 10.3, 6.6, 4.8]
        }]
    });



    $(document).on('click','#chartModalBack',function(){
    	$('#chartModal').modal('hide');
    });
*/

});
