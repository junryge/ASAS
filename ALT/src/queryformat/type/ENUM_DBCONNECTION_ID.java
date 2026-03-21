public enum ENUM_DBCONNECTION_ID {
	M16A("mcs_m16a.xml"),
	M14A("mcs_m14a.xml"),
	M14B("mcs_m14b.xml"),
	M14APM("apm_m14.xml"),
	DEFAULT("NODATA")
	;

	private final String connectionId;
	
	ENUM_DBCONNECTION_ID(String connectionId) {
		this.connectionId = connectionId;
	}

	public String fileName() {
		return connectionId;
	}
	
	public static ENUM_DBCONNECTION_ID fromString(String id) {
		for(ENUM_DBCONNECTION_ID conn : values()) {
			if(conn.name().equalsIgnoreCase(id)) {
				return conn;
			}
		}
		return DEFAULT;
	}
	
}
