public class FilePathUtil {
	private static final Logger logger 					= LoggerFactory.getLogger(FilePathUtil.class);
	public static final String REPOSITORY_PATH 			= System.getProperty("SMARTFX_REPOSITORY");
	private static final String dataaccessfxPath 		= REPOSITORY_PATH + "/dataaccessfx/";
	public static final String PYTHON_FILE_PATH 		= REPOSITORY_PATH + "/python";
	public static final String RECORD_FILE_PATH 		= REPOSITORY_PATH + "/document";

	// extra xml file
	public static final String LOGPRESSO_CUSTOM_QUERY 	= REPOSITORY_PATH + "/customQuery.xml";
	public static final String LOGPRESSO_CUSTOM_QUERY2 	= REPOSITORY_PATH + "/customQuery2.xml";
	public static final String ALARM_MESSAGE_PATH 		= REPOSITORY_PATH + "/alarm_message.xml";
	public static final String VARIABLE_ENV_PATH 		= REPOSITORY_PATH + "/variable.xml";
	public static final String OHT_ALARM_MESSAGE_PATH	= REPOSITORY_PATH + "/oht_alarm_message.xml";

	// environment setting file
	public static final String FAB_SET_PROPERTIES_PATH	= REPOSITORY_PATH + "/FabSet.properties";
	public static final String RESET_PROPERTIES_PATH 	= REPOSITORY_PATH + "/Reset.properties";

	// alarm format file
	private static final String CMESSAGE_FORMAT_PATH	= "cmessage/cfg/dataformat";
	public static final String COMMON_ALARM_FORMAT 		= CMESSAGE_FORMAT_PATH + "/CMESSAGE_CMN_FORMAT.xml";
	public static final String LAYOUT_DATA_FORMAT 		= CMESSAGE_FORMAT_PATH + "/CMESSAGE_LAYOUT_DATA.xml";

	// map file(*.layout.zip, *.lanecut.dat, *.mcp75.cfg, *.station.dat)
	private static final String MAP_ROOT_DIRECTORY 		= "map";


	private FilePathUtil() {}

	public static String factoryPath(String connectionId) {
		try {
			ENUM_DBCONNECTION_ID connId = ENUM_DBCONNECTION_ID.fromString(connectionId);
			String path = dataaccessfxPath + connId.fileName();

			if (path.equals("NODATA")) {
				return null;
			}

			return path;
		} catch (Exception e) {
			logger.error("", e);

			return null;
		}
	}

	public static String getMapRootDirectoryPath () {
		return MAP_ROOT_DIRECTORY;
	}

	public static String getOhtAlarmCodeCsvFilePath (String fileName) {
		return String.format("%s\\%s", REPOSITORY_PATH, fileName);
	}

	public static String getUdpMessagePath() {
		return String.format("%s/udp_message", REPOSITORY_PATH);
	}
}
