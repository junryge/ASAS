package com.skhynix.smartatlas.util;

import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartfx.dataaccessfx.QueryExecutor;
import com.skhynix.smartfx.dataaccessfx.QueryExecutorFactory;

public class SmsUtil {
	private static final Logger logger = LoggerFactory.getLogger(SmsUtil.class);
	
	public static void sendSMS(String receiver, String message) {
		var queryParameter = Map.of("TEL_NO", receiver, "CTN", message);
		var factory = QueryExecutorFactory.getQueryExecutor("stasms");
		
		try {
			factory.insert("INSERT_STA_SMS_HIS", queryParameter);
			factory.commit();
			
			logger.info(String.format("SMS Sent : %s => %s", receiver, message));
		} catch (Exception e) {
			logger.error("", e);
			factory.rollback();
		} finally {
			if (factory != null) {
				factory.close();
			}
		}
	}
	
	public static int getLast5MinCountSMS(String receiver, String message) {
		var queryParameter = Map.of("TEL_NO", receiver, "MSG_TYP", message);
		
		try (QueryExecutor qe = QueryExecutorFactory.build("stasms")) {
			return qe.selectInt("SELECT_STA_SMS_HIS", queryParameter);
		} catch(Exception e) {
			logger.error("",e);
		}
		
		return -1;
	}
	
}
