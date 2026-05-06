/*
 * Copyright (c) SK Hynix Inc.
 * All right reserved.
 *
 * This software is the confidential and proprietary information of SK Hynix.
 * You shall not disclose such Confidential Information and
 * shall use it only in accordance with the terms of the license agreement
 * you entered into with SK Hynix Inc.
 */
package com.skhynix.smartatlas.environment;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.nio.file.attribute.FileTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

import com.skhynix.smartatlas.environment.type.FunctionItem;
import com.skhynix.smartatlas.util.FilePathUtil;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.environment.type.DbProperties;
import com.skhynix.smartatlas.environment.type.SmsProperties;
import com.skhynix.smartatlas.util.CryptoUtil;
import com.skhynix.smartatlas.util.ParseUtil;

/**
 * A class to manage the environment.
 * <pre>
 * com.skhynix.smartatlas.util|Env.java
 * </pre>
 *
 * @author	: dongkun.yoo@partner.sk.com
 * @since	: 2020. 7. 23. 오전 10:55:00
 */
public class Env {
	private static final Logger logger = LoggerFactory.getLogger(Env.class);

	private static final String _SettingsPropertiesPath
			= String.format("%s/Settings.properties", FilePathUtil.REPOSITORY_PATH);

	private static final Map<String, DbProperties> _LogpressoPropertiesMap 	= new LinkedHashMap<>();
	private static final Map<String, DbProperties> _MongodbPropertiesMap 	= new LinkedHashMap<>();
	private static final String _LogpressoDecryptKey 	= "Logpresso.Password";
	private static final String _MongodbDecryptKey 		= "Mongodb.Password";
	private static SmsProperties _SmsProperties;

	private static String env = "";
	private static final int atlasThreadPoolSize = 48;

	private static FileTime lastModifiedTime 		= null;		// FabSet.properties 파일의 마지막 수정 시간
	private static FileTime resetLastModifiedTime 	= null;		// Reset.properties 파일의 마지막 수정 시간
	private static final Map<String, FileTime> variableDataModifiedTime = new HashMap<>();

	//	┌─ inactive(lanecut), layout, station, mcp75cfg 의 마지막 수정 날짜를 기록
	//	├─ key: {fabId}:{mcpName}	/ value: {key1: fileName / value1: modifiedDatetime}
	private static ConcurrentMap<String, Map<String, Long>> mapFileLastModifiedTime = new ConcurrentHashMap<>();

	// 기능 동작 여부
	//	┌─ key: {fabId}:{mcpName}
	//	├─ fab 별 switch 설정 및 조작
	private static final ConcurrentMap<String, FunctionItem> switchMap = new ConcurrentHashMap<>();

	/**
	 * Loads the properties from a file 'Settings.properties'
	 * @return boolean
	 */
	public static boolean initialize() {
		Properties properties = new Properties();
		FileInputStream stream = null;

		try {
			stream = new FileInputStream(_SettingsPropertiesPath);
			properties.load(stream);
			loadPropertiesProgram(properties);
			loadPropertiesLogpresso(properties);
			loadPropertiesMongodb(properties);
		} catch (IOException e) {
			logger.error("", e);

			return false;
		} finally {
			if (stream != null) {
				try {
					stream.close();
				} catch(Exception e) {
					logger.error("", e);
				}
			}
		}

		return true;
	}

	/**
	 * Loads the properties for Program.
	 * @param properties a Properties object to load properties.
	 */
	private static void loadPropertiesProgram(final Properties properties) {
		_SmsProperties = new SmsProperties(
				ParseUtil.parseIntOrDefault(properties.getProperty("Sms.MemoryUsageLimit", "-1").trim(), -1),
				ParseUtil.parseIntOrDefault(properties.getProperty("Sms.CpuUsageLimit", "-1").trim(), -1),
				ParseUtil.parseIntOrDefault(properties.getProperty("Sms.DiskUsageLimit", "-1").trim(), -1),
				ParseUtil.parseIntOrDefault(properties.getProperty("Sms.QueueWarningCount", "-1").trim(), -1),
				ParseUtil.parseIntOrDefault(properties.getProperty("Sms.QueueFailoverCount", "-1").trim(), -1),
				properties.getProperty("Sms.Receivers", "01097795551").trim().split(","));
	}

	/**
	 * Loads the properties for Logpresso.
	 * @param properties a Properties object to load properties.
	 */
	private static void loadPropertiesLogpresso(final Properties properties) {
		String useFabs = properties.getProperty("Logpresso.Use", "");

		if (StringUtils.isBlank(useFabs)) {
			return;
		}

		for (String fab : useFabs.split(",")) {
			String baseName	= String.format("Logpresso.%s.", fab);
			String hosts 	= properties.getProperty(baseName + "Hosts");
			String port 	= properties.getProperty(baseName + "Port");
			String id 		= properties.getProperty(baseName + "Id");
			String password	= properties.getProperty(baseName + "Password");

			if (StringUtils.isAnyBlank(hosts, port, id, password)) {
				continue;
			}

			if (CryptoUtil.decrypt(password, Env.getLogpressoDecryptKey()) == null) {
				password = CryptoUtil.encrypt(password, Env.getLogpressoDecryptKey());
				writeProperty(baseName + "Password", password);
			}

			_LogpressoPropertiesMap.put(
					fab,
					new DbProperties(
							hosts.split(","),
							ParseUtil.parseIntOrDefault(port, 8888),
							id,
							password,
							""
					)
			);
		}
	}

	/**
	 * Loads the properties for MongoDB.
	 * @param properties a Properties object to load properties.
	 */
	private static void loadPropertiesMongodb(final Properties properties) {
		String useFabs = properties.getProperty("Mongodb.Use", "");

		if (StringUtils.isBlank(useFabs)) {
			return;
		}

		for (String fab : useFabs.split(",")) {
			String baseName	= String.format("Mongodb.%s.", fab);
			String hosts 	= properties.getProperty(baseName + "Hosts");
			String port		= properties.getProperty(baseName + "Port");
			String id 		= properties.getProperty(baseName + "Id");
			String password	= properties.getProperty(baseName + "Password");
			String database	= properties.getProperty(baseName + "Database");

			if (StringUtils.isAnyBlank(hosts, port, id, password)) {
				continue;
			}

			if (CryptoUtil.decrypt(password, Env.getMongodbDecryptKey()) == null) {
				password = CryptoUtil.encrypt(password, Env.getMongodbDecryptKey());
				writeProperty(baseName + "Password", password);
			}

			_MongodbPropertiesMap.put(fab, new DbProperties(hosts.split(","), ParseUtil.parseIntOrDefault(port, 27020), id, password, database));
		}
	}

	/**
	 * Writes Property to 'Settings.properties'
	 */
	private static void writeProperty(String property, String value) {
		try {
			Path path = Paths.get(_SettingsPropertiesPath);
			var propertyFileLines = Files.readAllLines(path);
			var lineIndex = 0;

			for (String line : propertyFileLines) {
				if (line.contains(String.format("%s=", property))) {
					propertyFileLines.set(lineIndex, String.format("%s=%s", property, value));
					break;
				}

				lineIndex++;
			}

			Files.writeString(path, String.join("\n", propertyFileLines), StandardOpenOption.WRITE);
		} catch (Exception e) {
			logger.error("", e);
		}
	}

	/**
	 * 특정 디렉터리의 properties 문서를 확인 후 데이터로 생성
	 * @param directory properties 문서가 위치한 디렉터리
	 * @return null::문서가 존재하지 않는 경우|not null::문서에 기재된 정보를 데이터로 반환
	 */
	private static Properties _loadProperties(String directory) {
		Properties prop = null;
		FileInputStream fileInputStream = null;

		try {
			File file = new File(directory);

			if (file.exists()) {
				prop = new Properties();

				fileInputStream = new FileInputStream(directory);

				prop.load(fileInputStream);
			} else {
				String exceptionMessage = "... properties document is not exist [directory: " + directory + "]";

				throw new FileNotFoundException(exceptionMessage);
			}
		} catch (Exception e) {
			logger.error("", e);
		} finally {
			if (fileInputStream != null) {
				try {
					fileInputStream.close();
				} catch (IOException e) {
					logger.error("", e);
				}
			}
		}

		return prop;
	}

	/**
	 * 초기화 기능, 특정 디렉터리의 파일을 확인 후 `마지막으로 수정된 날짜`를 반환
	 * @param directory 대상인 파일이 위치한 디렉터리
	 * @return null::해당 디렉터리에 파일이 존재하지 않는 경우|not null::`마지막으로 수정된 날짜`를 반환
	 */
	private FileTime _initializedLastModifiedTime(String directory) {
		BasicFileAttributes basicFileAttributes = null;

		try {
			File file = new File(directory);

			if (file.exists()) {
				basicFileAttributes = Files.readAttributes(Paths.get(directory), BasicFileAttributes.class);
			} else {
				logger.error("... properties document is not exist [directory: {}]", directory);
			}
		} catch (IOException e) {
			logger.error("", e);
		}

		if (basicFileAttributes == null) {
			logger.error("... it's unable to read the attributes of file directory: {}]", directory);

			return null;
		} else {
			return basicFileAttributes.lastModifiedTime();
		}
	}

	public static Properties loadFabSetDocument() {
		return _loadProperties(FilePathUtil.FAB_SET_PROPERTIES_PATH);
	}

	public static Properties loadResetDocument() {
		return _loadProperties(FilePathUtil.RESET_PROPERTIES_PATH);
	}

	public static SmsProperties getSmsProperties() {
		return _SmsProperties;
	}

	public static Map<String, DbProperties> getMongodbPropertiesMap() {
		return _MongodbPropertiesMap;
	}

	public static String getMongodbDecryptKey() {
		return _MongodbDecryptKey;
	}

	public static Map<String, DbProperties> getLogpressoPropertiesMap() {
		return _LogpressoPropertiesMap;
	}

	public static String getLogpressoDecryptKey() {
		return _LogpressoDecryptKey;
	}

	/**
	 * 초기화 기능
	 * 1. FabSet.properties 정보를 바탕으로 데이터 생성
	 * 2. `env` 변수 값 할당 및 초기화
	 * 3. 맵 파일, reset.xml 등 파일의 `마지막으로 수정된 날짜`를 초기화
	 * @return properties 데이터를 반환
	 */
	public Properties getFabProp() {
		Properties properties = loadFabSetDocument();

		if (properties == null || properties.isEmpty()) {
			env = "NA";
		} else {
			env = properties.getProperty("Env", "TEST").trim();
			String variableXmlPath 		= FilePathUtil.VARIABLE_ENV_PATH;
			String custQueryXmlPath 	= FilePathUtil.LOGPRESSO_CUSTOM_QUERY;
			String custQuery2XmlPath 	= FilePathUtil.LOGPRESSO_CUSTOM_QUERY2;
			String alarmMessageXmlPath 	= FilePathUtil.ALARM_MESSAGE_PATH;
			String ohtAlarmMessageXmlPath = FilePathUtil.OHT_ALARM_MESSAGE_PATH;
			lastModifiedTime 		= this._initializedLastModifiedTime(FilePathUtil.FAB_SET_PROPERTIES_PATH);
			resetLastModifiedTime 	= this._initializedLastModifiedTime(FilePathUtil.RESET_PROPERTIES_PATH);

			variableDataModifiedTime.put(variableXmlPath, this._initializedLastModifiedTime(variableXmlPath));
			variableDataModifiedTime.put(custQueryXmlPath, this._initializedLastModifiedTime(custQueryXmlPath));
			variableDataModifiedTime.put(custQuery2XmlPath, this._initializedLastModifiedTime(custQuery2XmlPath));
			variableDataModifiedTime.put(alarmMessageXmlPath, this._initializedLastModifiedTime(alarmMessageXmlPath));
			variableDataModifiedTime.put(ohtAlarmMessageXmlPath, this._initializedLastModifiedTime(ohtAlarmMessageXmlPath));
		}

		return properties;
	}

	public static int getAtlasThreadPoolSize() {
		return atlasThreadPoolSize;
	}

	public static String getEnv() {
		return env;
	}

	// 특정 파일의 마지막 수정 시간 설정 및 변경
	public static void setLastModifiedTime (FileTime lastModifiedTime) {
		Env.lastModifiedTime = lastModifiedTime;
	}

	public static void setResetLastModifiedTime (FileTime lastModifiedTime) {
		Env.resetLastModifiedTime = lastModifiedTime;
	}

	public static void setMapFileLastModifiedTime (ConcurrentMap<String, Map<String, Long>> mapFileLastModifiedTime) {
		Env.mapFileLastModifiedTime = mapFileLastModifiedTime;
	}

	public static void setVariableDataModifiedTime(String directory, FileTime lastModifiedTime) {
		if (Env.variableDataModifiedTime.containsKey(directory)) {
			Env.variableDataModifiedTime.put(directory, lastModifiedTime);
		} else {
			logger.error("... it's not exist in dictionary [dictionary entered: {}]", directory);
		}
	}
	//~특정 파일의 마지막 수정 시간 설정 및 변경

	// 특정 파일의 마지막 수정 시간 호출
	public static FileTime getLastModifiedTime () {
		return lastModifiedTime;
	}

	public static FileTime getResetLastModifiedTime () {
		return resetLastModifiedTime;
	}

	public static Map<String, FileTime> getVariableDataModifiedTime () {
		return variableDataModifiedTime;
	}

	public static ConcurrentMap<String, Map<String, Long>> getMapFileLastModifiedTime () {
		return mapFileLastModifiedTime;
	}
	//~특정 파일의 마지막 수정 시간 호출

	public static ConcurrentMap<String, FunctionItem> getSwitchMap() {
		return switchMap;
	}

	public static FunctionItem getSwitchMap(String key) {
		if (switchMap.containsKey(key) && switchMap.get(key) != null) {
			return switchMap.get(key);
		} else {
			return null;
		}
	}
}
