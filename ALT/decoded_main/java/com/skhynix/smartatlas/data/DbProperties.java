package com.skhynix.smartatlas.data;

public class DbProperties {
	String[] _Hosts = new String[0];
	String _Port = "";
	String _Id = "";
	String _Password = "";
	String _Database = "";
	
	public DbProperties(String[] hosts, String port, String id, String password, String database) {
		_Hosts = hosts;
		_Port = port;
		_Id = id;
		_Password = password;
		_Database = database;
	}
	
	public String[] getHosts() {
		return _Hosts;
	}
	
	public String getPort() {
		return _Port;
	}
	
	public String getId() {
		return _Id;
	}
	
	public String getPassword() {
		return _Password;
	}
	
	public String getDatabase() {
		return _Database;
	}
}
