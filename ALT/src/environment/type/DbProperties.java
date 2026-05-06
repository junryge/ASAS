public class DbProperties {
	String[] _Hosts = new String[0];
	int _Port = -1;
	String _Id = "";
	String _Password = "";
	String _Database = "";
	
	public DbProperties(String[] hosts, int port, String id, String password, String database) {
		_Hosts = hosts;
		_Port = port;
		_Id = id;
		_Password = password;
		_Database = database;
	}
	
	public String[] getHosts() {
		return _Hosts;
	}
	
	public int getPort() {
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
