<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<%@ taglib uri="http://www.springframework.org/tags" prefix="spring" %>
<!DOCTYPE html>
	<head>
		<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
		<title><spring:message code="site.title" text="스프링 테스트 사이트 - default" /></title>
	</head>
	<body>
		<p>
			<a href="<c:url value="/i18n.do?lang=ko" />">ko-KR</a>
			<a href="<c:url value="/i18n.do?lang=en" />">en-US</a>
			<a href="<c:url value="/i18n.do?lang=jp" />">ja-JP</a>
			<a href="<c:url value="/i18n.do?lang=zh" />">zh-CN</a>
		</p>
		<p>site.lang : ${siteLang}</p>
		<p>site.title : <spring:message code="site.title" text="default text" /></p>
		<p>site.count : <spring:message code="site.count" arguments="첫번째" text="default text" /></p>
		<p>site.count using EL : <spring:message code="site.count" arguments="${siteCount}" text="default text" /></p>
		<p>not.exist : <spring:message code="not.exist" text="default text" /></p>
		<%-- <p>not.exist 기본값 없음 : <spring:message code="not.exist" /></p> --%>
		<p>site.title : <spring:message code="site.errorPage.title01" text="default text" /></p> 
	</body>
</html>
<script type="text/javascript">
	//alert("victory : <spring:message code="site.alarmReportLogList" text="default text" />");
</script>