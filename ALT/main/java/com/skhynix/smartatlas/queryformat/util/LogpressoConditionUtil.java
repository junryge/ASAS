package com.skhynix.smartatlas.queryformat.util;

import java.util.List;
import java.util.Map;

import org.apache.commons.lang3.StringUtils;

import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.queryformat.type.ENUM_RANGE_SEARCH_OPTION;

public class LogpressoConditionUtil {
	/**
	 * Create the condition string to query via a comma separator
	 * 
	 * @param columnName
	 * @param condition
	 * @param isRangeSearch
	 * @param isNot
	 * @return
	 */
	public static String createQueryCondition(final String columnName, final String condition,
			final ENUM_RANGE_SEARCH_OPTION isRangeSearch, final String isNot) {
		StringBuilder query = new StringBuilder();
		
		if (StringUtils.isEmpty(columnName) == true) {
			return "";
		}
		
		query.append(String.format("in(%s", columnName));
		
		if (StringUtils.isEmpty(condition) == true) {
			query.append(",\"" + condition + "\"");
		} else {
			String[] conditions = condition.split(",");
			for (String eachCondition : conditions) {
				if (isRangeSearch == ENUM_RANGE_SEARCH_OPTION.RANGE) {
					eachCondition = "*" + eachCondition.trim() + "*";
				}
				
				query.append(String.format(",\"%s\"", eachCondition.trim()));
			}
		}
		
		query.append(")");
		query.append(String.format(" == %s", "TRUE".equalsIgnoreCase(isNot) ? "false" : "true"));

		return query.toString();
	}
	
	/**
	 * 조건식 쿼리 문자열을 생성합니다. (컬럼이 배열 타입인 경우)
	 * 
	 * @param columnName
	 * @param condition
	 * @param isRangeSearch
	 * @param isNot
	 * @return
	 */
	public static String createQueryConditionArray(final String columnName, final String condition,
			final ENUM_RANGE_SEARCH_OPTION isRangeSearch, final String isNot) {
		StringBuilder query = new StringBuilder();
		
		if (StringUtils.isEmpty(columnName) == true) {
			return "";
		}
		
		query.append(String.format("in(strjoin(\",\", %s)", columnName));
		
		if (StringUtils.isEmpty(condition) == true) {
			query.append(",\"" + condition + "\"");
		} else {
			String[] conditions = condition.split(",");
			
			for (String eachCondition : conditions) {
				if (isRangeSearch == ENUM_RANGE_SEARCH_OPTION.RANGE) {
					eachCondition = "*" + eachCondition.trim() + "*";
				}
				
				query.append(String.format(",\"%s\"", eachCondition.trim()));
			}
		}
		
		query.append(")");
		query.append(String.format(" == %s", "TRUE".equalsIgnoreCase(isNot) ? "false" : "true"));

		return query.toString();
	}
	
	/**
	 * And 조건문을 생성합니다.
	 * 
	 * <pre>
	 * (columnName == condition1 and columnName == condition2 and ..)
	 * </pre>
	 * 
	 * @param columnName 컬럼 이름
	 * @param conditions 비교 문자열 목록
	 * @param isRangeSearch 문자열 비교방식 '문자열 일치(EXACT)' 혹은 '문자열 포함(RANGE)' 옵션
	 * @param isEqual 문자열 동등 비교 옵션 (true : ==, false : !=)
	 * @return
	 */
	public static String createQueryConditionAnd(final String columnName, final List<String> conditions,
			ENUM_RANGE_SEARCH_OPTION isRangeSearch, final boolean isEqual) {
		StringBuilder query = new StringBuilder();
		
		if (StringUtils.isEmpty(columnName) || conditions.size() == 0) {
			return "";
		}
		
		String operator = isEqual ? "==" : "!="; 
		
		for (String condition : conditions) {
			if (StringUtils.isNotEmpty(query.toString())) {
				query.append(" and ");
			}
			
			if (isRangeSearch == ENUM_RANGE_SEARCH_OPTION.EXACT) {
				query.append(String.format("%s %s \"%s\"", columnName, operator, condition.trim()));
			} else if (isRangeSearch == ENUM_RANGE_SEARCH_OPTION.RANGE) {
				query.append(String.format("%s %s \"*%s*\"", columnName, operator, condition.trim()));
			}
		}
		
		return String.format("(%s)", query.toString());
	}
	
	/**
	 * Or 조건문을 생성합니다.
	 * 
	 * <pre>
	 * (columnName == condition1 or columnName == condition2 or ..)
	 * </pre>
	 * 
	 * @param columnName 컬럼 이름
	 * @param conditions 비교 문자열 목록
	 * @param isRangeSearch 문자열 비교방식 '문자열 일치(EXACT)' 혹은 '문자열 포함(RANGE)' 옵션
	 * @param isEqual 문자열 동등 비교 옵션 (true : ==, false : !=)
	 * @return
	 */
	public static String createQueryConditionOr(final String columnName, final List<String> conditions,
			ENUM_RANGE_SEARCH_OPTION isRangeSearch, final boolean isEqual) {
		StringBuilder query = new StringBuilder();
		
		if (StringUtils.isEmpty(columnName) || conditions.size() == 0) {
			return "";
		}
		
		String operator = isEqual ? "==" : "!="; 
		
		for (String condition : conditions) {
			if (StringUtils.isNotEmpty(query.toString())) {
				query.append(" or ");
			}
			
			if (isRangeSearch == ENUM_RANGE_SEARCH_OPTION.EXACT) {
				query.append(String.format("%s %s \"%s\"", columnName, operator, condition.trim()));
			} else if (isRangeSearch == ENUM_RANGE_SEARCH_OPTION.RANGE) {
				query.append(String.format("%s %s \"*%s*\"", columnName, operator, condition.trim()));
			}
		}
		
		return String.format("(%s)", query.toString());
	}
	
	
	/**
	 * In 조건문을 생성합니다.
	 * 
	 * <pre>
	 * in(columnName, condition1, condition2, ..)
	 * </pre>
	 *  
	 * @param columnName 컬럼 이름
	 * @param conditions 비교 문자열 목록
	 * @return
	 */
	public static String createQueryConditionIn(final String columnName, final List<String> conditions) {
		StringBuilder query = new StringBuilder();
		
		if (StringUtils.isEmpty(columnName) || conditions.size() == 0) {
			return "";
		}
		
		for (String condition : conditions) {
			if (StringUtils.isNotEmpty(query.toString())) {
				query.append(", ");
			}
			
			query.append(String.format("\"%s\"", condition.trim()));
		}
		
		return String.format("in(%s, %s)", columnName, query.toString());
	}
	
	
	public static Long getQueryTotalCount(String fabSite, String queryStr) {
		StringBuilder query4Logprs = new StringBuilder(queryStr);
		query4Logprs.append(" | stats count as totalCount");

		List<Map<String, Object>> resultList = fabSite == null ? LogpressoAPI.responseResult(query4Logprs.toString()) : LogpressoAPI.responseResult(fabSite, query4Logprs.toString());

		return (Long)resultList.get(0).get("totalCount");
	}
}
