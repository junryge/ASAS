package com.skhynix.smartatlas.util;

public class ReflectionUtil {
	public static String getCurrentMethodName() {
		return new Throwable().getStackTrace()[1].getMethodName();
	}
}
