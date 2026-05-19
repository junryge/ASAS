package com.skhynix.supply.common.connection;

import java.io.FileInputStream;
import java.util.Enumeration;
import java.util.HashMap;
import java.util.Properties;

import org.jasypt.encryption.pbe.StandardPBEStringEncryptor;
import org.jasypt.properties.EncryptableProperties;

import com.skhynix.supply.common.Common;

public class ConnectionInfoPool {
	private static String ENCRYPT_KEY;
	private static Properties Property = null;
	private static HashMap<String, ConnectionInfo> Connections = new HashMap<String, ConnectionInfo>();

	static {
		try {
			String path = ConnectionInfoPool.class.getResource("/").getPath();
			Properties props = new Properties();

			path = path.substring(0, path.indexOf("classes")) + "prop/connectionInfo.properties";
			props.load(new FileInputStream(path));
			ENCRYPT_KEY = props.getProperty("db.encrypt_key");

			StandardPBEStringEncryptor encryptor = new StandardPBEStringEncryptor();

			encryptor.setAlgorithm("PBEWithMD5AndDES"); // 암-복호화 알고리즘 선택
			encryptor.setPassword(ENCRYPT_KEY);
			Property = new EncryptableProperties(encryptor);
			Property.load(new FileInputStream(path));
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	public static ConnectionInfo getConnectionInfo(String fabSite) {
		if (Connections.containsKey(fabSite) == false) {
			Connections.put(fabSite, createConnectionInfo(fabSite));
		}

		return Connections.get(fabSite);
	}

	private static ConnectionInfo createConnectionInfo(String fabSite) {
		ConnectionInfo connectionInfo = new ConnectionInfo();
		String[] targetpropertyNames = getPropertyNames(fabSite);

		try {
			Enumeration<?> filePropertyNames = Property.propertyNames();

			connectionInfo.setLogpressoPort(8888);
			connectionInfo.setLogpressoID("mcslogApp");

			while (filePropertyNames.hasMoreElements()) {
				String propertyName = filePropertyNames.nextElement().toString();

				if (propertyName.equals(targetpropertyNames[0])) {
					connectionInfo.setHostPrimary(Property.getProperty(propertyName));
				} else if (propertyName.equals(targetpropertyNames[1])) {
					connectionInfo.setHostSecondary(Property.getProperty(propertyName));
				} else if (propertyName.equals("db.pw")) {
					connectionInfo.setLogpressoPW(Property.getProperty(propertyName));
				}
			}
		} catch (Exception e) {
			e.printStackTrace();
		}

		return connectionInfo;
	}

	private static String[] getPropertyNames(String fabSite) {
		switch (fabSite) {
		case Common.sFABSITE_IC:
			return new String[] { "db.host_primary_ic", "db.host_secondary_ic" };
		case Common.sFABSITE_M11:
			return new String[] { "db.host_primary_m11", "db.host_secondary_m11" };
		case Common.sFABSITE_M15:
			return new String[] { "db.host_primary_m15", "db.host_secondary_m15" };
		case Common.sFABSITE_C2:
			// FabSite = C2이며, 실제서버눈 C2가 아닌경우, IC,M15,M11 통합 MCSLOG 섭에서 C2접근시 방화벽 문제로
			// host_third_c2 를 사용
			if (Common.sSERVER != Common.sFABSITE_C2) {
				return new String[] { "db.host_third_c2", "db.host_third_c2" };
			} else {
				return new String[] { "db.host_primary_c2", "db.host_secondary_c2" };
			}
		default:
			return new String[] {};
		}
	}
}
