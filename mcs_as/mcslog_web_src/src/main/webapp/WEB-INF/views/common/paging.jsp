<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ taglib prefix="c" uri="http://java.sun.com/jsp/jstl/core" %>
<script type="text/javascript">
</script>
<div class="nav_paging">
		<div class="nav_paging_right">
            <!-- Selector : 10 페이지씩 이동 -->
            <div class="elmt">
                <select class="jqForm pct" id="rowNum" name="rowNum" >
                    <option value="100"   <c:if test="${param.rowNum == 100 }" >selected="selected"</c:if> >100</option>
                    <option value="200"   <c:if test="${param.rowNum == 100 }" >selected="selected"</c:if> >200</option>
                    <option value="500"   <c:if test="${param.rowNum == 500 }" >selected="selected"</c:if> >500</option>
                    <option value="1000" <c:if test="${param.rowNum == 1000 }" >selected="selected"</c:if>  >1000</option>
                </select>
            </div>
            <!-- //Selector : 10 페이지씩 이동 -->
        </div>
       <div class="nav_paging_wrap">
           <a href="javascript:<c:out value='${param.searchFunc}' />(<c:out value='${param.prevPageNo}' />)" class="nav_paging_btn nav_paging_btn_prev"><span class="blind"><spring:message code="site.common.button.prev" text="default text" /></span></a>
           <a href="javascript:<c:out value='${param.searchFunc}' />(<c:out value='${param.nextPageNo}' />)" class="nav_paging_btn nav_paging_btn_next"><span class="blind"><spring:message code="site.common.button.next" text="default text" /></span></a>
       </div>
</div>

