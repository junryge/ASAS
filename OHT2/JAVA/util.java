public class Util {
	static private final Logger logger = LoggerFactory.getLogger(Util.class);
	static ConcurrentMap<String, Map<String, Long>> mapFileLastModifiedTimeMap;
	static private final int RETRY_LIMIT_COUNT = 2;
	static private final int RETRY_DELAY_MINUTES = 1;

	/*
	 * 청주와 이천을 분리하기 위한 로직
	 */
	public static boolean isCurrentIC() {
		if (DataService.getInstance() != null && DataService.getInstance().getInitialized()) {
			Collection<String> fabIds = DataService.getInstance().getFabPropertiesMap().keySet();

			return (fabIds.contains("M14A") || fabIds.contains("M14B") || fabIds.contains("M16A") || fabIds.contains("M16B"));
		}

		return false;
	}

	/**
	 * NullPointerException 을 피해 안전하게 토큰 값을 할당
	 * @param tokens 토큰 값
	 * @param index 토큰 값 중 사용 하려는 내용의 인덱스
	 * @param defaultValue 검색 내용이 비유효한 경우에 할당되는 기본 값
	 */
	public static String getTokenSafely(String[] tokens, int index, String defaultValue) {
		return (tokens != null && tokens.length > index) ? tokens[index] : defaultValue;
	}

	public static int maxLength(List<String> list) {
		int max = -1;

		if (list.isEmpty()) {
			logger.error("... list is empty");

			return 0;
		} else {
			for (String s : list) {
				if (s != null && s.length() > max) {
					max = s.length();
				}
			}

			if (max == -1) {
				logger.error("... all item of list received value is null, then it's returned to '0'");

				return 0;
			}
		}

		return max;
	}

	/**
	 * 문자열 값을 Integer 로 변환
	 */
	public static int getIntOrZero(String content) {
		try {
			if (content == null) {
				throw new Exception();
			}

			return Integer.parseInt(content);
		} catch (Exception e) {
			return 0;
		}
	}

	/**
	 * 문자열 값을 double 로 변환
	 */
	public static double getDoubleOrZero(String content) {
		try {
			if (content == null) {
				throw new Exception();
			}

			return Double.parseDouble(content);
		} catch (Exception e) {
			return 0;
		}
	}

	/*
	 * 바이너리 스트링을 바이트로 변환
	 */
	public static byte binaryStringToByte(String s) {
		byte ret, total = 0;

		for (int i = 0; i < 8; ++i) {
			ret = (s.charAt(7 - i) == '1') ? (byte) (1 << i) : 0;
			total = (byte) (ret | total);
		}

		return total;
	}

	public static String getSingleNodeValue(Node n, String key) {
		if (n == null)
			return null;

		Element e = (Element) n.selectSingleNode(key);

		if (e == null)
			return null;

		return e.attributeValue("value");
	}

	public static String readFileString(String filePath) {
		try {
			var path = Paths.get(filePath).toAbsolutePath();

            return Files.readString(path);
		} catch (Exception e) {
			logger.error("", e);

			return "";
		}
	}

	public static boolean writeFileString(String filePath, String content) {
		try {
			var path = Paths.get(filePath).toAbsolutePath();

			String directory = path.getParent().toString();

			File file = new File(directory);

			if (file.mkdir()) {
				logger.info("... file has been created successfully [directory: {}]", directory);
			} else {
				logger.error("... file is not created [directory: {}]", directory);
			}

			Files.writeString(path, content, StandardOpenOption.WRITE, StandardOpenOption.TRUNCATE_EXISTING);

			return true;
		} catch (Exception e) {
			logger.error("", e);

			return false;
		}
	}

	/**
	 * {@link DataService} 초기화 완료 이후에 사용 가능한 기능
	 * @param fabId factory ID (ex. M14A, M16A ...) ---> fabPropertiesMap 의 key 값
	 * @param mcpName mcp name (ex. A, B, E, BR ...) ---> (fabPropertiesMap 에 속한) mcpNamePropertiesMap 의 key 값
	 * @param procLaneCut lanecut.dat(=inactive_SCH_1.dat) 파일 사용 및 다운로드 수행 여부
	 * @param procLayout layout.zip 파일 사용 및 다운로드 수행 여부
	 * @param procMcp75Cfg mcp75.cfg 파일 사용 및 다운로드 수행 여부
	 * @param procStation station.dat 파일 사용 및 다운로드 수행 여부
	 * @param checkingModifiedTime true::'마지막으로 수정한 날짜'를 기준으로 파일 다운로드 여부 결정|false::무조건 다운로드
	 * @return 다운로드 받은 항목 {@link DOWNLOAD_MAP_FILE_TYPE}
	 */
	public static List<Integer> getAllOhtLayoutFileOverFtp(
			String fabId,
			String mcpName,
			boolean procLaneCut,
			boolean procLayout,
			boolean procMcp75Cfg,
			boolean procStation,
			boolean checkingModifiedTime
	) {
		try {
			FabProperties fabProperties = DataService.getInstance().getFabPropertiesMap().get(fabId);

			return getAllOhtLayoutFileOverFtp(
					fabProperties,
					mcpName,
					procLaneCut,
					procLayout,
					procMcp75Cfg,
					procStation,
					checkingModifiedTime
			);
		} catch (RuntimeException e) {
			logger.error("", e);
		}

		return new ArrayList<>();
	}

	/**
	 * @param fabProperties 초기화 중 형성한 factory 기초 정보
	 * @param procLaneCut lanecut.dat(=inactive_SCH_1.dat) 파일 사용 및 다운로드 수행 여부
	 * @param procLayout layout.zip 파일 사용 및 다운로드 수행 여부
	 * @param procMcp75Cfg mcp75.cfg 파일 사용 및 다운로드 수행 여부
	 * @param procStation station.dat 파일 사용 및 다운로드 수행 여부
	 * @param checkingModifiedTime true::'마지막으로 수정한 날짜'를 기준으로 파일 다운로드 여부 결정|false::무조건 다운로드
	 * @return 다운로드 받은 항목 {@link DOWNLOAD_MAP_FILE_TYPE}
	 */
	public static List<Integer> getAllOhtLayoutFileOverFtp(
			FabProperties fabProperties,
			String mcpName,
			boolean procLaneCut,
			boolean procLayout,
			boolean procMcp75Cfg,
			boolean procStation,
			boolean checkingModifiedTime
	) {
		List<Integer> downloadFileList = new ArrayList<>();
		List<String> resultContext = new ArrayList<>();
		FTPClient client = new FTPClient();

		String localMapRoot = FilePathUtil.getMapRootDirectoryPath();
		McpProperties mcpProperties = fabProperties.getMcpPropertiesMap().get(mcpName);

		String fabId = fabProperties.getFabId();
		mapFileLastModifiedTimeMap = Env.getMapFileLastModifiedTime();
// ---------------------------------------------------------------------------------------------------------------------
		if (_connectFtpServer(client, fabProperties, fabId, mcpName)) {
			logger.info("... FTP server connection successful [fab: {} | mcp: {}]", fabId, mcpName);

			// 파일 전송간 접속 딜레이 설정 (1ms 단위기 때문에 1000이면 1초)
			try {
				client.setSoTimeout(3000);
				client.setBufferSize(1024 * 1024); // 전송 속도 향상
			} catch (Exception e) {
				logger.error("", e);
			}

			boolean loginResult = _loginFtp(client, fabProperties, fabId, mcpName); // step#2 ftp 서버 로그인 (접속 선행)
// ---------------------------------------------------------------------------------------------------------------------
			if (loginResult) {
				// 로컬 환경의 맵 파일 유무 확인 후 디렉터리 생성
				File mapDir = new File(localMapRoot);

				if (!mapDir.exists()) {
					if (mapDir.mkdir()) {
						logger.info("... map directory created successfully [directory: {} | fab: {}]", mapDir.getName(), fabId);
					} else {
						logger.error("... creating map directory is failed [directory: {}]", mapDir.getAbsolutePath());
					}
				}
// ---------------------------------------------------------------------------------------------------------------------
				File rootDir = new File(localMapRoot, fabId);
				// 맵 파일의 하위 디렉터리(fabId) 확인 후 생성
				if (!rootDir.exists()) {
					if (rootDir.mkdir()) {
						logger.info("... fab directory created successfully [path: {} | fab: {} | mcp: {}]", mapDir.getName(), fabId, mcpName);
					} else {
						logger.error("... creating fab directory is failed [path: {}]", rootDir.getAbsolutePath());
					}
				}

				File file;

				// 파일 별 FTP 경로
				String laneCutFtpPath = null;
				String layoutFtpPath = null;
				String mcp75FtpPath = null;
				String stationFtpPath = null;

				// layout, station 파일은 무조건 다운로드(백업 용도), 해당 파일의 (다른 파일과 마찬가지로)수정 여부 확인
				boolean confLayout = false;
				boolean confStation = false;
// ---------------------------------------------------------------------------------------------------------------------
				// 할당
				if (procLaneCut) {
					laneCutFtpPath = _checkFtpDirectory(
							mcpProperties.getFtpLaneCutPath(),
							DOWNLOAD_MAP_FILE_TYPE.RAILCUT,
							fabProperties,
							client,
							fabId,
							mcpName
					);

					if (laneCutFtpPath == null || laneCutFtpPath.isEmpty())
						procLaneCut = false;
				}

				if (procLayout) {
					layoutFtpPath = _checkFtpDirectory(
							mcpProperties.getFtpLayoutPath(),
							DOWNLOAD_MAP_FILE_TYPE.LAYOUT,
							fabProperties,
							client,
							fabId,
							mcpName
					);

					if (layoutFtpPath == null || layoutFtpPath.isEmpty())
						procLayout = false;
				}

				if (procMcp75Cfg) {
					mcp75FtpPath = _checkFtpDirectory(
							mcpProperties.getFtpMcp75Path(),
							DOWNLOAD_MAP_FILE_TYPE.MCP75CFG,
							fabProperties,
							client,
							fabId,
							mcpName
					);

					if (mcp75FtpPath == null || mcp75FtpPath.isEmpty())
						procMcp75Cfg = false;
				}

				if (procStation) {
					stationFtpPath = _checkFtpDirectory(
							mcpProperties.getFtpStationPath(),
							DOWNLOAD_MAP_FILE_TYPE.STATION,
							fabProperties,
							client,
							fabId,
							mcpName
					);

					if (stationFtpPath == null || stationFtpPath.isEmpty())
						procStation = false;
				}

				// + FTP 서버 내 파일 확인
				if (checkingModifiedTime) {
					String key 		= fabId + ":" + mcpName;
					procLaneCut 	= _comparisonOfModifiedTimes(laneCutFtpPath, key, procLaneCut, client);
					confLayout 		= _comparisonOfModifiedTimes(layoutFtpPath, key, procLayout, client);
					procMcp75Cfg 	= _comparisonOfModifiedTimes(mcp75FtpPath, key, procMcp75Cfg, client);
					confStation 	= _comparisonOfModifiedTimes(stationFtpPath, key, procStation, client);
				}
// ---------------------------------------------------------------------------------------------------------------------
				String localMapDirectory = rootDir.getAbsolutePath();

				// 1. railCut(inactive_sch)
				if (procLaneCut) {
					file = new File(localMapDirectory, mcpName + ".lanecut.dat");
					boolean result = _searchAndDownloadFile(laneCutFtpPath, fabId, file, FTP.ASCII_FILE_TYPE, client);

					if (result) {
						downloadFileList.add(DOWNLOAD_MAP_FILE_TYPE.RAILCUT);
					}

					resultContext.add(String.format("%15s : %-10s", file.getName(), result ? "complete" : "exception"));
				}

				// 2. layout (무조건 다운로드 --- 파일 backup 목적)
				if (procLayout) {
					file = new File(localMapDirectory, mcpName + ".layout.zip");
					boolean result = _searchAndDownloadFile(layoutFtpPath, fabId, file, FTP.BINARY_FILE_TYPE, client);

					if (result && confLayout) {
						downloadFileList.add(DOWNLOAD_MAP_FILE_TYPE.LAYOUT);
					}

					resultContext.add(String.format("%15s : %-10s", file.getName(), result ? "complete" : "exception"));
				}

				// 3. MCP75
				if (procMcp75Cfg) {
					file = new File(localMapDirectory, mcpName + ".mcp75.cfg");
					boolean result = _searchAndDownloadFile(mcp75FtpPath, fabId, file, FTP.BINARY_FILE_TYPE, client);

					if (result) {
						downloadFileList.add(DOWNLOAD_MAP_FILE_TYPE.MCP75CFG);
					}

					resultContext.add(String.format("%15s : %-10s", file.getName(), result ? "complete" : "exception"));
				}

				// 4. station (무조건 다운로드 --- 파일 backup 목적)
				if (procStation) {
					file = new File(localMapDirectory, mcpName + ".station.dat");
					boolean result = _searchAndDownloadFile(stationFtpPath, fabId, file, FTP.ASCII_FILE_TYPE, client);

					if (result && confStation) {
						downloadFileList.add(DOWNLOAD_MAP_FILE_TYPE.STATION);
					}

					resultContext.add(String.format("%15s : %-10s", file.getName(), result ? "complete" : "exception"));
				}

				logger.info("... map file has been downloaded completely [directory: {} | fab: {}]", rootDir.getName(), fabId);
			}

			try {
				client.logout();

				if (client.isConnected()) {
					client.disconnect();
				}
			} catch (Exception e) {
				logger.error("... an error occurred while logout or disconnect FTP server", e);
			}
		}
// ---------------------------------------------------------------------------------------------------------------------
		String logTitle = "<DOWNLOAD MAP FILE [" + fabId + "]>";
		List<String> finishComment = new ArrayList<>();

		finishComment.add(logTitle);

		if (resultContext.isEmpty()) {
			String text = "no files downloaded";

			finishComment.add(text);
		} else {
			Env.setMapFileLastModifiedTime(mapFileLastModifiedTimeMap);

			finishComment.addAll(resultContext);
		}

		printHelper(finishComment);
// ---------------------------------------------------------------------------------------------------------------------
		return downloadFileList;
	}

	// FTP 서버 접속 시작
	private static boolean _connectFtpServer(
			FTPClient ftpClient,
			FabProperties fabProperties,
			String fabId,
			String mcpName
	) {
		logger.info("... FTP server has connecting [fab: {} | mcp: {}]", fabId, mcpName);

		Map<String, McpProperties> mcpPropertiesMap = fabProperties.getMcpPropertiesMap();

		if (ftpClient == null) {
			logger.error("... FTP client is null [fab: {} | mcp: {}]", fabId, mcpName);

			return false;
		}

		ftpClient.setControlEncoding("UTF-8"); // encoding

		String target = fabId + ".oht." + mcpName + ".ftp.ip";
		McpProperties mcpProperties = mcpPropertiesMap.get(mcpName);
		String hostName = mcpProperties.getFtpIp();
		int retryCnt = 0;
		boolean isConnected = false;

		do {
			try {
				ftpClient.connect(hostName, 21); // 접속 시도

				int resultCode = ftpClient.getReplyCode(); // 접속 확인
				isConnected = FTPReply.isPositiveCompletion(resultCode);
			} catch (Exception e) {
				logger.error("... @ftp connection is fail !!!", e);
			}

			if (isConnected) {
				logger.info("... @ftp server connection complete [connection successful]");

				return true;
			} else {
				logger.warn(
						"... @invalid ftp connection information ! please modify {}, try to connect ftp server again after {} minutes (remaining retry: {}) !",
						target,
						RETRY_DELAY_MINUTES,
						RETRY_LIMIT_COUNT - retryCnt
				);
				logger.info("---> entered ftp ip({}): {}", target, hostName);

				try {
					TimeUnit.MINUTES.sleep(RETRY_DELAY_MINUTES);
				} catch (InterruptedException e) {
					logger.error("... an error occurred while waiting for thread to terminate !!!", e);
				}

				Map<String, Object> temp = _reflect(1, 0, fabId, mcpName, mcpProperties);
				hostName = (String) temp.get("HOST_NAME");

				retryCnt ++;
			}
		} while (retryCnt < RETRY_LIMIT_COUNT);

		logger.error("... FTP server connection complete [connection failed]");

		return false;
	}

	private static boolean _loginFtp(
			FTPClient client,
			FabProperties fabProperties,
			String fabId,
			String mcpName
	) {
		logger.info("... login to FTP server [fab: {} | mcp: {}]", fabId, mcpName);

		if (client == null) {
			logger.error("... FTP client is null [fab: {} | mcp: {}]", fabId, mcpName);

			return false;
		}

		long timer = System.currentTimeMillis();

		Map<String, McpProperties> mcpPropertiesMap = fabProperties.getMcpPropertiesMap();
		McpProperties mcpProperties = mcpPropertiesMap.get(mcpName);
		int retryCnt = 0;
		boolean isLogin = false;
		String ftpUserKey = fabId + ".oht." + mcpName + ".ftp.user";
		String ftpPasswordKey = fabId + ".oht." + mcpName + ".ftp.password";
		String ftpUserId = mcpProperties.getFtpUser();
		String ftpPassword = mcpProperties.getFtpPassword();

		do {
			try {
				String decryptPassword = Util.decrypt(ftpPassword, ftpPasswordKey);
				isLogin = client.login(ftpUserId, decryptPassword);
			} catch (Exception e) {
				logger.error("... failed to login to FTP server [fab: {} | mcp: {}]", fabId, mcpName, e);
			}

			if (isLogin) {
				// login completed
				logger.info("... login completed to FTP server [fab: {} | mcp: {}] [elapsed time: {}ms]", fabId, mcpName, System.currentTimeMillis() - timer);

				return true;
			} else {
				// login failed
				logger.error(
						"... invalid FTP login information ! please correct {} and {}, try logging back into the FTP server in {} minutes (remaining retry: {})",
						ftpPasswordKey,
						ftpUserKey,
						RETRY_DELAY_MINUTES,
						RETRY_LIMIT_COUNT - retryCnt
				);
				logger.info("---> entered FTP user({}): {}", ftpUserKey, ftpUserId);

				try {
					TimeUnit.MINUTES.sleep(RETRY_DELAY_MINUTES);
				} catch (InterruptedException e) {
					logger.error("... an error occurred while waiting for thread to terminate", e);
				}

				Map<String, Object> temp = _reflect(2, 1, fabId, mcpName, mcpProperties);
				ftpUserId = temp.get("USER_ID").toString();
				ftpPassword = temp.get("PASSWORD").toString();

				retryCnt++;
			}
		} while (retryCnt < RETRY_LIMIT_COUNT);

		logger.error("... failed to login to FTP server [fab: {} | mcp: {}]", fabId, mcpName);

		return false;
	}

	private static String _checkFtpDirectory(
			String ftpDirectory,
			int fileType,
			FabProperties fabProperties,
			FTPClient client,
			String fabId,
			String mcpName
	) {
		if (ftpDirectory == null || ftpDirectory.isEmpty()) {
			logger.error("... FTP directory entered is invalid [fab: {} | mcp: {}]", fabId, mcpName);

			return null;
		}

		String target = fabId + ".oht." + mcpName + ".ftp";
		McpProperties mcpProperties = fabProperties.getMcpPropertiesMap().get(mcpName);
		int retryCnt = 0;
		FTPFile[] files = null;

		switch (fileType) {
			case DOWNLOAD_MAP_FILE_TYPE.RAILCUT:
				target += ".lanecut";

				break;
			case DOWNLOAD_MAP_FILE_TYPE.LAYOUT:
				target += ".layout";

				break;
			case DOWNLOAD_MAP_FILE_TYPE.MCP75CFG:
				target += ".mcp75";

				break;
			case DOWNLOAD_MAP_FILE_TYPE.STATION:
				target += ".station";

				break;
			default:
				logger.error("... invalid file type !!!");

				return null;
		}

		do {
			try {
				files = client.listFiles(ftpDirectory);
			} catch (IOException e) {
				logger.error("", e);
			}

			if (files == null || files.length == 0) {
				logger.warn(
						"... @invalid ftp directory ! please modify {}, try to search directory of ftp server again after {} minutes (remaining retry: {})",
						target,
						RETRY_DELAY_MINUTES,
						RETRY_LIMIT_COUNT - retryCnt
				);
				logger.info("---> entered FTP directory({}): {}", target, ftpDirectory);

				try {
					TimeUnit.MINUTES.sleep(RETRY_DELAY_MINUTES);
				} catch (InterruptedException e) {
					logger.error("... an error occurred while waiting for thread to terminate !!!", e);
				}

				Map<String, Object> temp = _reflect(3, fileType, fabId, mcpName, mcpProperties);
				ftpDirectory = temp.get("DIRECTORY").toString();

				retryCnt ++;
			} else {
				return ftpDirectory;
			}
		} while (retryCnt < RETRY_LIMIT_COUNT);

		return null;
	}

	private static long _searchLastModifiedTimeOfFtpFile(
			String ftpDirectory, 	// FTP 서버 주소 및 경로
			String ftpFileName, 	// FTP 서버 내 파일명
			FTPClient ftpClient
	) {
		FTPFile file = null;
		FTPFile[] files = null;

		try {
			files = ftpClient.listFiles(ftpDirectory);
		} catch (IOException e) {
			logger.error("", e);
		}

		if (files != null && files.length > 0) {
			for (FTPFile ftpFile : files) {
				if (ftpFile.getName().equals(ftpFileName) && ftpFile.isFile()) {
					file = ftpFile;

					break;
				}
			}
		} else {
			logger.warn("... file not found in ftp directory (path: {}) !", ftpDirectory);
		}

		if (file != null) {
			long timer = file.getTimestamp().getTimeInMillis();
			Date lastModifiedTime = new Date(timer);

			return lastModifiedTime.getTime();
		}

		return -1;
	}

	// FTP 서버의 파일의 '마지막으로 수정한 날짜' 를 최근(혹은 초기화 당시)에 저장한 날짜 및 시간과 비교
	// 두 날짜가 서로 동일한 경우 해당 파일 및 과정은 생략. 다를 경우 파일 다운로드 후 (저장한)날짜 갱신
	private static boolean _comparisonOfModifiedTimes(
			String ftpDirectory,
			String key,
			boolean procCondition,
			FTPClient ftpClient
	) {
		if (procCondition) {
			String ftpFileName = ftpDirectory.substring(ftpDirectory.lastIndexOf("/") + 1);
			long currentTime = _searchLastModifiedTimeOfFtpFile(ftpDirectory, ftpFileName, ftpClient);

			if (currentTime == -1) {
				return false;
			}

			if (!mapFileLastModifiedTimeMap.containsKey(key)) {
				mapFileLastModifiedTimeMap.put(key, new HashMap<>());
			}

			if (!mapFileLastModifiedTimeMap.get(key).containsKey(ftpFileName)) {
				mapFileLastModifiedTimeMap.get(key).put(ftpFileName, currentTime);

				return false;
			} else {
				long previousTime = mapFileLastModifiedTimeMap.get(key).get(ftpFileName);
				long diffInMillisecond = currentTime - previousTime;

				if (diffInMillisecond == 0) {
					logger.warn("... @file has not been modified [file name: {}]", ftpFileName);

					return false;
				} else {
					mapFileLastModifiedTimeMap.get(key).put(ftpFileName, currentTime);

					return true;
				}
			}
		}

		return false;
	}

	// 다운로드 할 수 있는 파일 여부를 확인
	private static boolean _searchAndDownloadFile(String ftpDirectory, // ftp 서버 주소 및 경로
												  String fabId, File localFile, int fileType, FTPClient ftpClient) {
		String localFileName = localFile.getName();

		logger.info("[---] Check the local `{}` file before proceeding with the download (fab: {}) ...", localFileName,
				fabId);
		logger.info(">>> ftp({}) path: {} / local path: {} (fab: {})", ftpClient.getRemoteAddress(), ftpDirectory,
				localFile.getPath(), fabId);
		logger.info("[=--] Check and overwrite local file ...");

		if (localFile.exists()) {
			if (localFile.delete()) {
				logger.info("... File deleted because `{}` is exists local", localFileName);
			} else {
				logger.warn("... Failed to delete local file `{}` !", localFileName);
			}
		}

		try {
			if (localFile.createNewFile()) {
				logger.info("... New `{}` file created", localFileName);
			} else {
				logger.warn("... Failed to create new `{}` file !", localFileName);
			}
		} catch (IOException e) {
			logger.error("", e);
		}

		logger.info("[#=-] Ready to download `{}` file ...", localFileName);

		try (FileOutputStream fileOutputStream = new FileOutputStream(localFile)) {
			ftpClient.setFileType(fileType);

			if (ftpClient.retrieveFile(ftpDirectory, fileOutputStream)) {
				logger.info("[##-] ... `{}` file downloaded local from ftp server", localFileName);
			} else {
				logger.info("[##-] ... `{}` file does not need to be downloaded", localFileName);
			}
		} catch (IOException e) {
			logger.error("", e);
			return false;
		}

		logger.info("[###] ... `{}` file download process completed", localFileName);

		return true;
	}

	private static Map<String, Object> _reflect(
			int processSequence,
			int fileTypeSequence,
			String fabId,
			String mcpName,
			McpProperties mcpProperties
	){
		try {
			TimeUnit.MINUTES.sleep(RETRY_DELAY_MINUTES);
		} catch (InterruptedException e) {
			logger.error("... an error occurred while waiting for thread to terminate !!!", e);
		}

		Map<String, Object> result = new HashMap<>();
		Properties properties = Env.loadFabSetDocument();
		String target;

		switch (processSequence) {
			case 0:
			case 1:
				target = fabId + ".oht." + mcpName + ".ftp.ip";
				String hostName = properties.getProperty(target, "").trim();

				mcpProperties.setFtpIp(hostName);

				if (processSequence == 1) {
					result.put("HOST_NAME", hostName);
				}
			case 2:
				String ftpUserKey = fabId + ".oht." + mcpName + ".ftp.user";
				String ftpPasswordKey = fabId + ".oht." + mcpName + ".ftp.password";
				String ftpUserId = properties.getProperty(ftpUserKey, "").trim();
				String ftpPassword = properties.getProperty(ftpPasswordKey, "").trim();

				mcpProperties.setFtpUser(ftpUserId);
				mcpProperties.setFtpPassword(ftpPassword);

				if (processSequence == 2) {
					result.put("USER_ID", ftpUserId);
					result.put("PASSWORD", ftpPassword);
				}
			case 3:
				target = fabId + ".oht." + mcpName + ".ftp";
				String directory = "";

				switch (fileTypeSequence) {
					case 0:
					case DOWNLOAD_MAP_FILE_TYPE.RAILCUT:
						directory = properties.getProperty(target + ".lanecut", "").trim();

						mcpProperties.setFtpLaneCutPath(directory);
					case DOWNLOAD_MAP_FILE_TYPE.LAYOUT:
						directory = properties.getProperty(target + ".layout", "").trim();

						mcpProperties.setFtpLayoutPath(directory);
					case DOWNLOAD_MAP_FILE_TYPE.MCP75CFG:
						directory = properties.getProperty(target + ".mcp75", "").trim();

						mcpProperties.setFtpMcp75Path(directory);
					case DOWNLOAD_MAP_FILE_TYPE.STATION:
						directory = properties.getProperty(target + ".station", "").trim();

						mcpProperties.setFtpStationPath(directory);

						break;
				}

				if (processSequence == 3) {
					result.put("DIRECTORY", directory);
				}
		}

		return result;
	}

	static public boolean isContentsEqualsCollection(Collection<?> a, Collection<?> b) {
		// 동시성 문제 방지를 위해 불변 컬렉션으로 변환
		if (a == b)
			return true; // 동일한 객체 또는 둘 다 null

		if (a == null || b == null)
			return false; // 하나만 null 일 경우

		if (a.size() != b.size())
			return false; // 크기 다른 경우 빠르게 탈락

		// 성능 최적화를 위해 HashSet 사용
		return new HashSet<>(a).equals(new HashSet<>(b));
	}

	static {
		Security.addProvider(new BouncyCastleProvider());
	}

	// decoder
	static public String decrypt(String target, String key) {
		return _transformer(target, key, false);
	}

	// encoder
	static public String encrypt(String target, String key) {
		return _transformer(target, key, true);
	}

	/**
	 * @param target password etc
	 * @param key selected key in document
	 * @param j true::encode|false::decode
	 */
	@Nullable
	private static String _transformer(String target, String key, boolean j) {
		SecretKeySpec keySpec;
		StringBuilder newKey = new StringBuilder();
		final int MODE = j ? Cipher.ENCRYPT_MODE : Cipher.DECRYPT_MODE;

		while (newKey.toString().getBytes().length < 32) {
			newKey.append(key);
		}

		byte[] k = newKey.substring(0, 32).getBytes();
		keySpec = new SecretKeySpec(k, "AES");
		Cipher cipher;

		try {
			cipher = Cipher.getInstance("AES/GCM/NoPadding", "BC");

			cipher.init(MODE, keySpec, new IvParameterSpec(newKey.substring(0, 32).getBytes()));

			try {
				if (j) {
					Base64.Encoder encoder = Base64.getEncoder();

					return new String(encoder.encode(cipher.doFinal(target.getBytes())));
				} else {
					Decoder encoder = Base64.getDecoder();

					return new String(cipher.doFinal(encoder.decode(target.getBytes())));
				}

				// ---> doFinal() throws each of exception
			} catch (IllegalBlockSizeException e) {
				logger.error("... illegal block size exception occurred during a {}", j ? "encoding" : "decoding", e);
			} catch (BadPaddingException e) {
				logger.error("... bad padding exception occurred during a {}", j ? "encoding" : "decoding", e);
			}
		} catch (Exception e) {
			logger.error("... an exception occurred during a {}", j ? "encoding" : "decoding", e);
		}

		return null;
	}

	/**
	 * 로그, 포맷 공통화
	 * @param list logpresso 에 적재할 데이터
	 * @param tableName logpresso 테이블 명칭
	 * @param className 데이터를 가공한 클래스 명칭
	 */
	public static void insertInLogpressoDatabase(List<Tuple> list, String tableName, String className) {
		// 적재할 데이터가 없음에도 LogpressoAPI 로직을 경유하는 경우, traffic jam 우려
		if (!list.isEmpty()) {
			if (LogpressoAPI.setInsertTuples(tableName, list,15)) {
				logger.info("... `{}` data has been inserted in logpresso database [size: {}] [table={}]", className, list.size(), tableName);
			} else {
				logger.error("... `{}` data is not inserted in logpresso database [size: {}] [table={}]", className, list.size(), tableName);
			}
		}
	}


	/**
	 * there is make an content with csv file
	 * @param data csv file content
	 */
	@NonNull
	public static <T> String composeCsvFileContent(List<Map<String, T>> data) throws Exception {
		if (data.isEmpty()) {
			String exceptionMessage = "... data is empty, so formatting an csv context is canceled";

			throw new Exception(exceptionMessage);
		}

		List<String> csvContent = new ArrayList<>();

		for (int i = 0; i < data.size(); i++) {
			Map<String, T> line = data.get(i);

			if (i == 0) {
				String t = String.join(",", line.keySet());

				csvContent.add(t);
			}

			Collection<T> items = line.values();
			List<String> bundle = new ArrayList<>();

			for (T v : items) {
				if (v == null) {
					// skipped ...
					String nullPointLine = items.stream()
							.map(_i -> _i == null ? "null" : _i.toString())
							.collect(Collectors.joining(","));
					String exceptionMessage = "... content contains null value, so formatting an csv context is canceled  [index: " + i + "] [t: " + nullPointLine + "]";

					throw new NullPointerException(exceptionMessage);
				} else {
					String s = v.toString();

					if (s.contains(",") || s.contains("\"")) {
						s = "\"" + s.replace("\"", "\"\"") + "\"";
					}

					bundle.add(s);
				}
			}

			csvContent.add(String.join(",", bundle));
		}

		return String.join("\n", csvContent);
	}

	/**
	 * 지정한 파일 명으로 저장하거나 덮어쓰기
	 * @param directory 지정한 파일 명을 기준으로 상위 디렉터리. 예시) python/data/save.txt -> directory=python/data
	 * @param fileName 지정할 파일 명 + 확장자 명 포함. 예시) save.txt
	 * @param content 파일의 내용 (※csv 파일 형식을 유지할 것)
	 * @throws Exception 파일 저장 전, 일련의 과정 중 예외 발생
	 * @throws FileNotFoundException 내용을 파일 형태로 저장하거나 덮어쓰기 할 때, 해당 위치가 존재하지 않는 경우
	 */
	@NonNull
	public static void createAndOverwriteFile(String directory, String fileName, String content) throws Exception {
		File folder 	= new File(directory);
		String filePath	= directory + File.separator + fileName;
		File file 		= new File(filePath);
		String exceptionMessage;

		logger.info("[@--] check the folder [directory: {}]", directory);

		if (folder.exists()) {
			logger.info("[#--] folder is exist [directory: {}]", directory);
		} else {
			if (folder.mkdirs()) {
				logger.info("[#--] folder has been created [directory: {}]", directory);
			} else {
				exceptionMessage = MessageFormat.format("[*--] folder is not created, so process exit [directory: {0}]", directory);

				throw new Exception(exceptionMessage);
			}
		}

		logger.info("[#@-] check the file [directory: {}]", filePath);

		if (file.exists()) {
			if (file.delete()) {
				logger.info("[##-] file was deleted [directory: {}]", filePath);
			} else {
				exceptionMessage = MessageFormat.format("[#*-] file is not deleted, so process exit [directory: {0}", filePath);

				throw new Exception(exceptionMessage);
			}
		} else {
			logger.info("[##-] file does not exist [directory: {}]", directory);
		}

		logger.info("[##@] writing file content [directory: {}]", filePath);

		try (FileWriter fileWriter = new FileWriter(filePath)) {
			fileWriter.write(content);
			fileWriter.flush();

			logger.info("[###] file has been overwritten at that directory [directory: {}]", filePath);
		} catch (Exception e) {
			exceptionMessage = MessageFormat.format("[##*] file is not overwritten at that directory [t={0}] [directory: {1}]", e.getMessage(), filePath);

			throw new FileNotFoundException(exceptionMessage);
		}
	}

	/*
	 * 로그에 표시되는 내용 중 포괄적인 정보나 강조가 필요한 정보에 테두리를 걸쳐 표시
	 * example)
	 * ################
	 * # context      #
	 * ################
	 */
	public static void printHelper(List<String> context) {
		StringBuilder content = new StringBuilder();
		int maxLength = 0;

		// calculating maximum
		for (String text : context) {
			if (text.length() > maxLength) {
				maxLength = text.length();
			}
		}

		content.append("\n").append("#".repeat(maxLength + 4));

		// formatting text
		for (String text : context) {
			String line = String.format("# %-" + maxLength + "s #", text);

			content.append("\n").append(line);
		}

		content.append("\n").append("#".repeat(maxLength + 4));

		logger.info(content.toString());
	}

	/**
	 * FabSet.properties 문서의 정보를 바탕으로 각 기능의 스위치 동작 여부를 변경 혹은 초기화
	 */
	public static void reflectSwitch(Properties properties) throws NullPointerException {
		ConcurrentMap<String, FabProperties> fabPropertiesMap = DataService.getInstance().getFabPropertiesMap();

		List<String> logs = new ArrayList<>(List.of("<FUNCTION SWITCH STATUS>"));

		if (fabPropertiesMap == null) {
			throw new NullPointerException("... initialized factory property is null value [fabPropertiesMap=null]");
		}

		// #1 factory 구분이 없는 공톤된(CMN) switch 기능 구성
		List<String> t = _setFunctionItem("CMN", "CMN", properties);

		logs.addAll(t);

		// #2 factory 별로 구분된 switch 기능 구성
		for (FabProperties fabProperties : fabPropertiesMap.values()) {
			String fabId = fabProperties.getFabId();
			Collection<String> mcpNames = fabProperties.getMcpName2OhtNameMap().keySet();

			if (mcpNames.isEmpty()) {
				logger.error("... mcp information in factory is not exist or initialized [fab: {}]", fabId);
			} else {
				for (String mcpName : mcpNames) {
					List<String> context = _setFunctionItem(fabId, mcpName, properties);

					logs.addAll(context);
				}
			}
		}

		printHelper(logs);
	}

	/**
	 * @param properties FabSet.properties 정보
	 * @return 스위치 적용 및 결과 반영에 대한 log 내용
	 * @throws NullPointerException 잘못된 factory 정보에 대한 예외 처리
	 */
	private static List<String> _setFunctionItem(
			String fabId,
			String mcpName,
			Properties properties
	) throws NullPointerException {
		if (fabId == null || mcpName == null) {
			throw new NullPointerException("... factory information is null value [fabId=null or mcpName=null] [fab: " + fabId + " | mcp: " + mcpName + "]");
		}

		ConcurrentMap<String, FunctionItem> switchMap	= Env.getSwitchMap();
		final FunctionItem.FunctionType[] functionTypes	= FunctionItem.FunctionType.values();
		String switchKey 								= fabId + ":" + mcpName;
		FunctionItem previousFunctionItem 				= switchMap.get(switchKey);

		List<String> bundleLogs		= new ArrayList<>();
		List<String> logs			= new ArrayList<>();
		final String logLineFormat	= "%-30s : %-10s";
		final int logLineLength		= String.format(logLineFormat, "", "").length();
		final String changedLogLineFormat = "%-4s-> %-3s"; // in logLineFormat

		logs.add("=".repeat(logLineLength));
		logs.add("[" + switchKey + "]");
		logs.add("-".repeat(logLineLength));

		if (previousFunctionItem == null) {
			// initialization
			Map<FunctionItem.FunctionType, Boolean> mapper = new HashMap<>();

			for (FunctionItem.FunctionType functionType : functionTypes) {
				Boolean using = _getFunctionProperty(functionType, fabId, mcpName, properties);

				if (using != null) {
					// add log
					String log = String.format(
							logLineFormat,
							functionType.getKey(),
							using ? "ON" : "OFF"
					);

					// add environment
					mapper.put(functionType, using);

					bundleLogs.add(log);
				}
			}

			// setter --- reference
			FunctionItem functionItem = new FunctionItem(fabId, mcpName, mapper);

			Env.getSwitchMap().put(switchKey, functionItem);
		} else {
			// switching
			for (FunctionItem.FunctionType functionType : functionTypes) {
				Boolean using			= _getFunctionProperty(functionType, fabId, mcpName, properties);
				Boolean previousUsed	= previousFunctionItem.getUseFunction(functionType, true);
				String tUsing 			= using == null ? "NA" : (using ? "ON" : "OFF");
				String tPreviousUsed 	= previousUsed == null ? "NA" : (previousUsed ? "ON" : "OFF");
				String log;

				if (using == null && previousUsed == null) {
					continue;
				} else if (using != null && previousUsed == using) {
					// retained
					log = String.format(
							logLineFormat,
							functionType.getKey(),
							using ? "ON" : "OFF"
					);
				} else {
					String t = String.format(changedLogLineFormat, tPreviousUsed, tUsing);
					log = String.format(logLineFormat, functionType.getKey(), t);
				}

				previousFunctionItem.setUseFunction(functionType, using);

				bundleLogs.add(log);
			}
		}

		if (bundleLogs.isEmpty()) {
			logs.add("... ENTERED SWITCH IS NOT EXIST");
		} else {
			logs.addAll(bundleLogs);
		}

		return logs;
	}

	private static Boolean _getFunctionProperty(
			FunctionItem.FunctionType functionType,
			String fabId,
			String mcpName,
			Properties properties
	) {
		// property ===> {fabId}.{mcpName}.{functionType}=TRUE
		String property	= fabId + "." + mcpName + "." + functionType.getKey();
		String value	= properties.getProperty(property, null);

		if (value == null) {
			return null;
		} else {
			return value.trim().equalsIgnoreCase("TRUE");
		}
	}

	public static class DOWNLOAD_MAP_FILE_TYPE {
		public static final int RAILCUT 	= 1;	// inactive_SCH_1.dat
		public static final int LAYOUT		= 2;	// layout.zip
		public static final int MCP75CFG 	= 3;	// mcp75.cfg
		public static final int STATION 	= 4;	// station.dat
	}
}
