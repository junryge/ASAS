<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<!DOCTYPE HTML>
<html xmlns="http://www.w3.org/1999/xhtml" lang="ko">
<head>
<meta http-equiv="Content-Type" content="txt/html; charset=utf-8" />
<meta http-equiv="X-UA-Compatible" content="IE=edge" />
<%@ taglib uri="http://tiles.apache.org/tags-tiles" prefix="tiles"%>
</head>
<body>
	<div id="lay_wrap" class="lay_col2">
		<!-- top menu 시작 -->
		<tiles:insertAttribute name="header" /> 
		<!-- top menu 끝 -->
		<!-- body 시작 -->
		<tiles:insertAttribute name="body" />
		<!-- body 끝 -->
		<!-- footer 시작 -->
		<tiles:insertAttribute name="footer" />
		<!-- footer 끝 -->
	</div>
</body>
</html>