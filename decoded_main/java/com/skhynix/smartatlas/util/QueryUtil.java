package com.skhynix.smartatlas.util;

import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.Calendar;
import java.util.Date;
import java.util.TimeZone;

public class QueryUtil {
	public static String replaceDummy(String query) {
		return query.replace("| search (1) and ", "| search ")
				.replace("| search (1) or ", "| search ")
				.replace("| search (1)", "");
	}

	/**
	 * Convert To Query String
	 * 
	 * @param date
	 * @return yyyyMMddHHmmss
	 */
	public static String convertToQueryString(Date date) {
		SimpleDateFormat queryDateFormat = new SimpleDateFormat("yyyyMMddHHmmss");
		
		return queryDateFormat.format(date);
	}
	
	/**
	 * Convert to Date
	 * 
	 * dateTimeString : yyyyMMddHHmmssSSS
	 * 
	 * @param dateTimeString
	 * @return
	 * @throws ParseException
	 */
	public static Date convertToDate(String dateTimeString) throws ParseException {
		dateTimeString = String.format("%-17s", dateTimeString).replace(" ", "0");
		
		SimpleDateFormat queryDateFormat = new SimpleDateFormat("yyyyMMddHHmmssSSS");
		
		queryDateFormat.setTimeZone(TimeZone.getDefault());
		
		return queryDateFormat.parse(dateTimeString);
	}
	
	/**
	 * Convert to yyyy-MM-ddTHH:mm:ss.SSSZ (System Timezone)
	 * 
	 * dateTimeString : yyyyMMddHHmmssSSS
	 * 
	 * @param dateTimeString
	 * @return
	 */
	public static String convertToUtcTimezone(String dateTimeString) {
		SimpleDateFormat normalDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
		
		normalDateFormat.setTimeZone(TimeZone.getTimeZone("utc"));
		
		try {
			Date date = convertToDate(dateTimeString);
			
			return normalDateFormat.format(date)
					.replace(" ", "T") + "Z";
		} catch (ParseException e) {
			e.printStackTrace();
			
			return "";
		}
	}

	/**
	 * Convert to MongoDB ObjectID
	 * 
	 * dateTimeString : yyyyMMddHHmmssSSS
	 * 
	 * @param dateTimeString
	 * @return
	 */
	public static String convertToObjectId(String dateTimeString) {
		try {
			Date date = convertToDate(dateTimeString);
			Calendar timestamp = Calendar.getInstance();		
			
			timestamp.setTimeZone(TimeZone.getTimeZone("utc"));
			timestamp.setTime(date);
			
			var hex = Long.toHexString(timestamp.getTimeInMillis() / 1000);
			hex = String.format("%-24s", hex).replace(" ", "0");
			
			return hex;
		} catch (Exception e) {
			e.printStackTrace();
			
			return "";
		}
	}
	
	/**
	 * Convert to yyyy-MM-dd HH:mm:ss.SSS
	 * 
	 * dateTimeString : yyyyMMddHHmmssSSS
	 * 
	 * @param dateTimeString
	 * @return
	 */
	public static String convertToCommonDateFormat(String dateTimeString) {
		try {
			Date date = convertToDate(dateTimeString);
			SimpleDateFormat normalDateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
			
			return normalDateFormat.format(date);
		} catch (Exception e) {
			e.printStackTrace();
			
			return "";
		}
	}
	
	/**
	 * Get the name of Partitioning TS collection
	 * 
	 * @param collection
	 * @param from
	 * @param to
	 * @return
	 */
	public static String getTsViewPartitionCollection(String collection, Date from, Date to) {
		var calendarFrom = Calendar.getInstance();
		var calendarTo = Calendar.getInstance();
		
		calendarFrom.setTime(from);
		calendarTo.setTime(to);
		
		try {
			var day = calendarFrom.get(Calendar.DATE);
			var base = day / 3;
			base = day % 3 == 0 ? base - 1 : base;
			
			if (day == 31) {
				base--;
			}
			
			return collection + "_" + (base + 1);
		} catch (Exception e) {}

		return collection;
	}
}
