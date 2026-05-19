<%@ page language="java" contentType="text/html; charset=UTF-8" pageEncoding="UTF-8"%>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c"%>
<%@ taglib uri="http://java.sun.com/jsp/jstl/functions" prefix="fn"%>
<%@ taglib uri="http://java.sun.com/jsp/jstl/fmt" prefix="fmt"%>

<%@ page import="java.lang.management.ManagementFactory"%>
<%@ page import="java.lang.management.MemoryMXBean"%>

<%
    pageContext.setAttribute("memoryBean", ManagementFactory.getMemoryMXBean());
    pageContext.setAttribute("poolBeans", ManagementFactory.getMemoryPoolMXBeans());
%>

<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
    <title>JVM Memory Monitor</title>
 
    <style type="text/css">
        body{ font-family:"Myriad Pro","Myriad Web","Tahoma","Helvetica","Arial",sans-serif; }
        table{ border-collapse: collapse; }
        td,th{ padding: 5px; }
        th { background-color: navy; color: #fff; font-weight: bold; }
        td { text-align: right; }
    </style>
</head>
 
<body>
    <h1>TOTAL</h1>
     
    <table border="1" width="100%">
        <colgroup>
            <col width="20%"/>
            <col width="20%"/>
            <col width="20%"/>
            <col width="20%"/>
            <col width="20%"/>
        </colgroup>
        <tr>
            <th>Usage</th>
            <th>Max</th>
            <th>Init</th>
            <th>Used</th>
            <th>Committed</th>
        </tr>
        <tr>
            <td style="text-align: left">Heap Memory Usage</td>
            <td><fmt:formatNumber value="${memoryBean.heapMemoryUsage.max/(1024 * 1024)}"
                    maxFractionDigits="1" />MB</td>
            <td><fmt:formatNumber value="${memoryBean.heapMemoryUsage.init/(1024 * 1024)}"
                    maxFractionDigits="1" />MB</td>
            <td><fmt:formatNumber value="${memoryBean.heapMemoryUsage.used/(1024 * 1024)}"
                    maxFractionDigits="1" />MB</td>
            <td><fmt:formatNumber value="${memoryBean.heapMemoryUsage.committed/(1024 * 1024)}"
                    maxFractionDigits="1" />MB</td>
        </tr>
        <tr>
            <td style="text-align: left">Non-heap Memory Usage</td>
            <td><fmt:formatNumber value="${memoryBean.nonHeapMemoryUsage.max/(1024 * 1024)}"
                    maxFractionDigits="1" />MB</td>
            <td><fmt:formatNumber value="${memoryBean.nonHeapMemoryUsage.init/(1024 * 1024)}"
                    maxFractionDigits="1" />MB</td>
            <td><fmt:formatNumber value="${memoryBean.nonHeapMemoryUsage.used/(1024 * 1024)}"
                    maxFractionDigits="1" />MB</td>
            <td><fmt:formatNumber value="${memoryBean.nonHeapMemoryUsage.committed/(1024 * 1024)}"
                    maxFractionDigits="1" />MB</td>
        </tr>
    </table>
 
    <hr/>
    <h1>Memory Pools</h1>
     
    <c:forEach var="bean" items="${poolBeans}">
        <h2>${bean.name}(${bean.type})</h2>
        <table border="1" width="100%">
            <colgroup>
                <col width="20%"/>
                <col width="20%"/>
                <col width="20%"/>
                <col width="20%"/>
                <col width="20%"/>
            </colgroup>
            <tr>
                <th>Usage</th>
                <th>Max</th>
                <th>Init</th>
                <th>Used</th>
                <th>Committed</th>
            </tr>
            <tr>
                <td style="text-align: left">Memory Usage</td>
                <td><fmt:formatNumber value="${bean.usage.max/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
                <td><fmt:formatNumber value="${bean.usage.init/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
                <td><fmt:formatNumber value="${bean.usage.used/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
                <td><fmt:formatNumber value="${bean.usage.committed/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
            </tr>
            <tr>
                <td style="text-align: left">Peak Usage</td>
                <td><fmt:formatNumber value="${bean.peakUsage.max/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
                <td><fmt:formatNumber value="${bean.peakUsage.init/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
                <td><fmt:formatNumber value="${bean.peakUsage.used/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
                <td><fmt:formatNumber value="${bean.peakUsage.committed/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
            </tr>
            <tr>
                <td style="text-align: left">Collection Usage</td>
                <td><fmt:formatNumber value="${bean.collectionUsage.max/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
                <td><fmt:formatNumber value="${bean.collectionUsage.init/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
                <td><fmt:formatNumber value="${bean.collectionUsage.used/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
                <td><fmt:formatNumber value="${bean.collectionUsage.committed/(1024 * 1024)}"
                        maxFractionDigits="1" />MB</td>
            </tr>
        </table>
    </c:forEach>
</body>
</html>