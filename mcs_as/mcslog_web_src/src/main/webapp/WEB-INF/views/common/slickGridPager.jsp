<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<div id="pager" style="width:100%;height:20px;">
		<div class="slick-pager">
			<span class="slick-pager-nav">
				<span class="ui-state-default ui-corner-all ui-icon-container">
					<span class="ui-icon ui-icon-seek-prev ui-state-disabled">
					</span>
				</span>
				<span class="ui-state-default ui-corner-all ui-icon-container">
					<span class="ui-icon ui-icon-seek-next ui-state-disabled">
					</span>
				</span>
			</span>
			<span class="slick-pager-settings">
				<%-- <input id="searchDelay" name="searchDelay" class="onlynum" value="15<c:out value="${param.searchDelay }" />" title=" Search Response Time (sec) "  style="width:30px" maxlength="2" /> --%>
				<span class="slick-pager-settings-expanded" style="">
					<select id="reload"  >
						<option value="01" >refresh</option>
						<option value="02" selected >append</option>
					</select>
				</span>
				<span class="slick-pager-settings-expanded" style="">
					<select id="rows" name="rows">
						<option value="200">200</option>
						<option value="500">500</option>
						<option value="1000" selected>1000</option>
						<option value="2000">2000</option>
						<option value="5000">5000</option>
					</select>
				</span>
			</span>
			<span class="slick-pager-status"><spring:message code="site.common.page" text="default text" />[<span id="pageTxt">1</span>]&nbsp;&nbsp;<spring:message code="site.common.count" text="default text" />[<span id="rowCount" >0</span>]&nbsp;&nbsp;Retrieving Time[<span id="laptime">0</span>]ms</span>
	</div>
</div>