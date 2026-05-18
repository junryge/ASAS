package com.skhynix.smartatlas.util;

import java.util.regex.Pattern;

import org.apache.commons.lang3.ObjectUtils;

import com.skhynix.smartfx.security.exception.RestrictedAccessException;
import com.skhynix.smartfx.server.api.BizExecutionContext;

public class SecurityUtil {
	public enum AccessLevel {
		Disabled(0),
		SuperAdministrator(10),
		SystemAdministrator(20),
		Developer(30),
		User(40),
		Guest(50);
		
		int levelNumber;
		
		AccessLevel(int levelNumber) {
			this.levelNumber = levelNumber;
		}
		
		public int getLevelNumber() {
			return this.levelNumber;
		}
	};
	
	/**
	 * Throwing AssertionErrorException if there is <<null>> in objects
	 * 
	 * @param assertObjects
	 */
	public static void assertNull(final Object... assertObjects) {
		if (ObjectUtils.allNotNull(assertObjects) == false) {
			throw new AssertionError("Assertion-null : Required variables are missing");
		}
	}
	
	/**
	 * Throwing RestrictedAccessException if a user doesn't have permission
	 * 
	 * @param allowAccessLevels
	 * @return
	 */
	public static void assertAccessLevel(AccessLevel allowMinimumLevel) {
		int currentAccessLevel = BizExecutionContext.securityContext().getAccessLevel(); 
		
		if (currentAccessLevel > allowMinimumLevel.getLevelNumber()) {
			throw new RestrictedAccessException("");
		}
	}
	
	/**
	 * Return User's id who called method
	 * 
	 * @return
	 */
	public static String getCurrentUserId() {
		try {
			return BizExecutionContext.securityContext().getUserId();
		} catch (Exception e) {
			return "";
		}
	}
	
	/**
	 * Prevent to use reserved characters on 'Filter' class
	 * @param filter
	 * @return
	 */
	public static Pattern safePatternInternal(String filter) {
		if (filter == null) {
			return null;
		}
		
		filter = filter
			.replace("\\", "\\\\")
			.replace("-", "\\-")
			.replace("$", "\\$")
			.replace("^", "\\^")
			.replace("+", "\\+")
			.replace("*", "\\*")
			.replace("(", "\\(")
			.replace("{", "\\{")
			.replace("[", "\\[")
			.replace(")", "\\)")
			.replace("}", "\\}")
			.replace("]", "\\]");
		
		return Pattern.compile(filter);
	}
	
	/**
	 * Prevent to use reserved characters on the name
	 * @param fileName
	 * @return
	 */
	public static String safeFileName(String fileName) {
		if (fileName == null) {
			return null;
		}
		
		fileName = fileName
			.replace("\\", "")
			.replace("..", "");
			
		return fileName;
	}
}
