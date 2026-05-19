$(function(){
	
	$(document).on('mouseenter','.tabHeader',function(){
	      $('.statTabClass.item').tab({cache : true});
	});
	
	$(document).on('click', '#searchButton', function(){
		var now = new Date();
		var nowTime = now.getTime();
		console.log('nowMilliseconds : ' + nowTime);
		var afterTime;
		$('#firstTab').empty();
		$.ajax({
			url: "test/getList",
			type: "post",
			dataType: "json",
			contentType: "application/x-www-form-urlencoded; charset=UTF-8",
			success: function(json){
				
				$('#firstTab').append("" +
						 "<table class='ui blue striped table' id='logListTable'>"+
				         " <tr>"+
				         "   <th class='tableHead'>No</th>"+
				         "   <th class='tableHead'>Text</th>"+
				         " </tr>"+
						 "</table>");
				var max = 200;
				for(var i=0;i<max;i++){
					$('#logListTable').append("" +
							" <tr>"+
							"   <td>"+(i+1)+"</td>"+
							"   <td>"+json[i]+"</td>"+
					" </tr>");
				}
				var after = new Date();
				afterTime = after.getTime();
				console.log('afterTime : '+ afterTime);
				console.log('time difference : ' +((afterTime -nowTime)/1000)+"초");
			},
			error: function(xhr, textStatus) {
				alert("error : " + xhr.readyState + " : " + xhr.status);
			}
		});
	});

    $(document).on('click','.filterOption',function(){
      if($(this).children().eq(0).attr('class') === 'caret right icon'){
        $(this).children().eq(0).attr('class', 'caret down icon');
      }else{
        $(this).children().eq(0).attr('class', 'caret right icon');
      }

      $(this).next().transition('slide down');
    });

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
});
