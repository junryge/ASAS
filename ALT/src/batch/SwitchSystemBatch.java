public class SwitchSystemBatch implements Job{
	private final Logger logger 	= LoggerFactory.getLogger(getClass());
	private final int DELAYED_TIME 	= 1000 * 60;

	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		if (Util.isCurrentIC()) {
			long timer = System.currentTimeMillis();

			this._run();

			long checkTimer = System.currentTimeMillis() - timer;

			if (checkTimer >= DELAYED_TIME) {
				// 스팸 로그를 우려해 처리가 늦어진 경우에만 로그를 표시
				logger.error("... !!!DELAYED!!! `{}` has finished. but it's too late [elapsed time: {}m ({}ms)]", this.getClass().getSimpleName(), checkTimer / (60 * 1000), checkTimer);
			}
		}
	}

	/*
	 * 두 가지 properties 문서의 `마지막으로 수정된 날짜`를 통해 해당 문서의 수정 여부를 판단 후 데이터화 시켜 저장하거나 기능을 동작시킴
	 */
	private void _run() {
		this._readRevisedDocument();
		this._readRevisedResetDocument();
		this._readRevisedVariableData();
	}

	/**
	 * read by variable.xml / customQuery.xml / alarm_message.xml ...
	 */
	private void _readRevisedVariableData() {
		Map<String, FileTime> variableDataModifiedTime = Env.getVariableDataModifiedTime();

		if (variableDataModifiedTime.isEmpty()) return;

		for (Map.Entry<String, FileTime> entry : variableDataModifiedTime.entrySet()) {
			String directory 				= entry.getKey();
			FileTime lastModifiedTime 		= entry.getValue();
			FileTime currentModifiedTime	= this._confirmFileChanged(directory, lastModifiedTime);

			if (currentModifiedTime != null) {
				long timer = System.currentTimeMillis();

				if (directory.equals(FilePathUtil.VARIABLE_ENV_PATH)) {
					// #1 variable.xml
					XmlUtil.loadVariableEnv();
				} else if (directory.equals(FilePathUtil.LOGPRESSO_CUSTOM_QUERY)) {
					// #2 customQuery.xml
					XmlUtil.loadLogpressoParm(FilePathUtil.LOGPRESSO_CUSTOM_QUERY);
				} else if (directory.equals(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2)) {
					// #3 customQuery2.xml
					XmlUtil.loadLogpressoParm(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2);
				} else if (directory.equals(FilePathUtil.ALARM_MESSAGE_PATH)) {
					// #4 alarm_message.xml
					XmlUtil.loadAlarmMessage();
				} else if (directory.equals(FilePathUtil.OHT_ALARM_MESSAGE_PATH)) {
					// #5 oht_alarm_message.xml
					XmlUtil.loadOhtAlarmMessage();
				}

				Env.setVariableDataModifiedTime(directory, currentModifiedTime);

				logger.info("... applying content of directory ({}) is done [elapsed time: {}ms]", directory, System.currentTimeMillis() - timer);
			}
		}
	}

	/**
	 * read by Reset.properties
	 */
	private void _readRevisedResetDocument() {
		FileTime time = Env.getResetLastModifiedTime();

		if (time == null) return;

		String path = FilePathUtil.RESET_PROPERTIES_PATH;
		FileTime currentModifiedTime = this._confirmFileChanged(path,time);

		if (currentModifiedTime != null) {
			long timer = System.currentTimeMillis();
			Properties properties = Env.loadResetDocument();

			currentModifiedTime = this._resetByProperties(properties, path);

			Env.setResetLastModifiedTime(currentModifiedTime);

			logger.info("... applying the contents of the revised <Reset> document to the server completely [elapsed time: {}ms]", System.currentTimeMillis() - timer);
		}
	}

	/**
	 * read by FabSet.properties
	 */
	private void _readRevisedDocument () {
		FileTime time = Env.getLastModifiedTime();

		if (time == null) return;

		String path = FilePathUtil.FAB_SET_PROPERTIES_PATH;
		FileTime currentModifiedTime = this._confirmFileChanged(path, time);

		if (currentModifiedTime != null) {
			long timer = System.currentTimeMillis();
			Properties properties = Env.loadFabSetDocument();

			this._setFunctionByProperties(properties);

			Env.setLastModifiedTime(currentModifiedTime);

			logger.info("... applying the contents of the revised <FabSet> document to the server completely [elapsed time: {}ms]", System.currentTimeMillis() - timer);
		}
	}

	/**
	 * compare the 'last modified date' of file to the value already saved in server
	 *
	 * @param directory location of file to compare
	 * @param lastModifiedTime it's recorded in server memory
	 * @return true::file changed | false::file not changed
	 */
	private FileTime _confirmFileChanged(String directory, FileTime lastModifiedTime) {
		FileTime currentModifiedTime = null;
		Path path = Paths.get(directory);

		if (Files.exists(path)) {
			BasicFileAttributes basicFileAttributes = null;

			try {
				basicFileAttributes = Files.readAttributes(path, BasicFileAttributes.class);
			} catch (Exception e) {
				logger.error("", e);
			}

			if (basicFileAttributes != null) {
				currentModifiedTime = basicFileAttributes.lastModifiedTime();
			}

			if (lastModifiedTime == null || !lastModifiedTime.equals(currentModifiedTime)) {
				return currentModifiedTime;
			}
		} else {
			logger.warn("... the properties file does not exist [path: {}]", path.toAbsolutePath());
		}

		return null;
	}

	/**
	 * Reset.properties 사용에 따른 초기화 작업, 각 항목의 속성 값에 따라 작업 수행
	 * DONE		---	작업 완료
	 * TRY		---	해당 fab 의 특정 기능의 보유 중인 전체 데이터를 NORMAL 상태 값을 송신 후 삭제
	 * {value}	---	해당 fab 의 특정 기능의 입력한 device name 을 기준으로 logpresso 데이터를 참고하여 NORMAL 상태 값을 송신. 해당 데이터를 보유하고 있는 경우에는 삭제도 진행
	 * (20250924) 현재 사용 가능한 초기화 작업의 대상은 HID OFF, VHL OFF, RAIL CUT
	 * @param properties Reset.properties 데이터
	 * @param directory Reset.properties 파일의 위치
	 * @return 초기화 작업을 완료한 뒤 파일 갱신 시간
	 */
	private FileTime _resetByProperties(Properties properties, String directory) {
		//	┌─ 'TRY' 로 변경한 기능의 키 값 수집 :: {fabId}.{mcpName}.{function}
		List<String> selectedKeyByFunction = new ArrayList<>();
		//	┌─ device name 을 입력한 기능의 키 값 수집 :: {fabId}.{mcpName}.{function}.{deviceName}
//		List<String> selectedKeyByDeviceName = new ArrayList<>();

		for (FabProperties fabProperties : DataService.getInstance().getFabPropertiesMap().values()) {
			String fabId = fabProperties.getFabId();

			for (String mcpName : fabProperties.getMcpName2OhtNameMap().keySet()) {
				String prefix = fabId + "." + mcpName;

				for (FunctionType functionType : FunctionType.values()) {
					String key = prefix + "." + functionType.getKey();
					String value = properties.getProperty(key, null);

					if (value != null && !value.trim().isEmpty()) {
						switch (value) {
							case "TRY": {
								selectedKeyByFunction.add(key);

								properties.setProperty(key, "TRY<ONGOING..>");
							} break;
							case "FAIL":
							case "DONE": {
								// nothing ...
							} break;
//							default: {
//								selectedKeyByDeviceName.add(key + "." + value);
//
//								properties.setProperty(key, "TRY<ONGOING BY " + value + "..>");
//							}
						}
					}
				}
			}
		}

		if (
				!selectedKeyByFunction.isEmpty()
//						|| !selectedKeyByDeviceName.isEmpty()
		) {
			this._storeProperties(properties, directory);	// 앞서 설정한 내용을 파일에 적용 후 저장하여 표시

//			if (!selectedKeyByFunction.isEmpty()) {
			for (String key : selectedKeyByFunction) {
				try {
					String[] split = key.split("\\.");
					String fabId = split[0];
					String mcpName = split[1];
					FunctionType functionType = FunctionType.valueOf(split[2]);

					this._resetFunction(fabId, mcpName, functionType);

					properties.setProperty(key, "DONE");
				} catch (Exception e) {
					properties.setProperty(key, "FAIL");
				}
			}
//			}

//			if (!selectedKeyByDeviceName.isEmpty()) {
//				for (String key : selectedKeyByDeviceName) {
//					String settingKey = "";
//
//					try {
//						String[] split = key.split("\\.");
//						String fabId = split[0];
//						String mcpName = split[1];
//						FunctionType functionType = FunctionType.valueOf(split[2]);
//						String deviceName = split[3];
//						settingKey = fabId + "." + mcpName + "." + functionType.getKey();
//
//						if (this._resetFunctionByDeviceName(fabId, mcpName, functionType, deviceName)) {
//							properties.setProperty(settingKey, "DONE");
//						} else {
//							properties.setProperty(settingKey, "FAIL");
//						}
//					} catch (Exception e) {
//						if (!settingKey.isEmpty()) {
//							properties.setProperty(settingKey, "FAIL");
//						}
//					}
//				}
//			}

			this._storeProperties(properties, directory);	// 모든 과정이 완료되었음을 파일에 적용 후 저장하여 표시
		}

		BasicFileAttributes basicFileAttributes = null;
		Path path = Paths.get(directory);

		try {
			basicFileAttributes = Files.readAttributes(path, BasicFileAttributes.class);
		} catch (Exception e) {
			logger.error("", e);
		}

		if (basicFileAttributes != null) {
			return basicFileAttributes.lastModifiedTime();
		}

		return null;
	}

	/**
	 * properties 문서를 덮어쓰거나 저장
	 * @param properties 저장할 내용의 바탕이 되는 문서
	 * @param directory 덮어쓰거나 저장할 위치
	 */
	private void _storeProperties(Properties properties, String directory) {
		try (FileOutputStream fileOutputStream = new FileOutputStream(directory)){
			properties.store(fileOutputStream, null);
		} catch (Exception e) {
			logger.error("", e);
		}
	}

	/**
	 * @param functionType function type (VHL_OFF etc)
	 */
	private void _resetFunction(String fabId, String mcpName, FunctionType functionType) {
		/*
		 * 공통 절차
		 * 1. 비정상(`ABNORMAL`) 상태의 데이터를 정상(`NORMAL`) 상태로 변환, 해당 데이터 삭제(`vehicle 재석수` 제외)
		 * 2. tib/rv message 를 송신하는 대기열에 적재
		 * + 차후 tib/rv message 유실될 경우, logpresso 에 적재하는 보완책 구상
		 */
		long time = System.currentTimeMillis();
		String compareKey = fabId + ":" + mcpName;
		List<Map<String, String>> messageDataList = new ArrayList<>();

		switch (functionType) {
			case HID_OFF: {
				for (Map.Entry<String, HidOffRecordItem> entry : DataService.getDataSet().getHidOffRecordMap().entrySet()) {
					String key = entry.getKey();

					if (key.startsWith(compareKey)) {
						HidOffRecordItem value = entry.getValue();

						if (value.getState().equals(OHT_TIB_STATE.ABNORMAL)) {
							value.setState(OHT_TIB_STATE.NORMAL);
//							value.setEventDateTime(time);

							Map<String, String> messageData = LayoutUtil.buildLayoutMessageDataMap(value);

							if (!messageData.isEmpty()) {
								messageDataList.add(messageData);

								DataService.getDataSet().getHidOffRecordMap().remove(key);
							}
						}
					}
				}
			} break;
			case VHL_OFF: {
				ConcurrentMap<String, VhlOffRecordItem> recordMap = DataService.getDataSet().getVhlOffRecordMap();

				for (Map.Entry<String, VhlOffRecordItem> entry : recordMap.entrySet()) {
					String key = entry.getKey();

					if (key.startsWith(compareKey)) {
						VhlOffRecordItem value = entry.getValue();

						if (value.getState().equals(OHT_TIB_STATE.ABNORMAL)) {
							value.setState(OHT_TIB_STATE.NORMAL);
							value.setEventDateTime(time);

							Map<String, String> messageData = LayoutUtil.buildLayoutMessageDataMap(value);

							if (!messageData.isEmpty()) {
								messageDataList.add(messageData);

								DataService.getDataSet().getVhlOffRecordMap().remove(key);
							}

							ConcurrentMap<String, VhlOffRecordItem> recordOnlyMap = DataService.getDataSet().getVhlOffMonitoringMap();

							if (recordOnlyMap.containsKey(key)) {
								VhlOffRecordItem item = recordOnlyMap.get(key);

								item.setState(OHT_TIB_STATE.NORMAL);
								item.setEventDateTime(time);
							}
						}
					}
				}
			} break;
			case RAIL_CUT: {
//				DataService.getInstance().updateRailCut(true, fabId, mcpName);

				for (Map.Entry<String, RailCutRecordItem> entry : DataService.getDataSet().getRailCutRecordMap().entrySet()) {
					String key = entry.getKey();

					if (key.startsWith(compareKey)) {
						RailCutRecordItem value = entry.getValue();
						Map<String, String> messageData = LayoutUtil.buildLayoutMessageDataMap(value);

						if (!messageData.isEmpty()) {
							messageDataList.add(messageData);

							DataService.getDataSet().getRailCutRecordMap().remove(key);
						}
					}
				}
			} break;
			case VHL_CNT: {

			}
			default:
				break;
		}

		if (messageDataList.isEmpty()) return;

		for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:").keySet()) {
			for (Map<String, String> messageData : messageDataList) {
				String layoutType = messageData.get(LayoutUtil.LAYOUT_MEMBER.DEVICE_TYPE);

				DataService.getInstance().addTibrvMessageQueue(tibrvKey, layoutType, messageData);
			}
		}
	}

	/**
	 * @see Util > reflectSwitch()
	 */
	private void _setFunctionByProperties(Properties properties) {
		try {
			Util.reflectSwitch(properties);
		} catch (NullPointerException e) {
			logger.error("", e);
		}

		// switching listener port (UDP)
		this._switchUdp(properties);
	}

	// UDP 포트 수정 혹은 동작 여부
	private void _switchUdp (Properties properties) {
		ConcurrentHashMap<String, OhtUdpListener> listenerMap = DataService.getInstance().getOhtUdpListenerMap();
		ConcurrentMap<String, FabProperties> fabPropertiesMap = DataService.getInstance().getFabPropertiesMap();	// * 필터링 된 이후의 값을 넣을 것
		Set<String> previousKeys = listenerMap.keySet();
		Set<String> currentKeys = new HashSet<>();

		for (FabProperties fabProperties : fabPropertiesMap.values()) {
			String fabId = fabProperties.getFabId();

			for (String mcpName : fabProperties.getMcpName2OhtNameMap().keySet()) {
				String key = fabId + "." + mcpName;

				currentKeys.add(key);
			}
		}

		// 1. UDP 추가
		Set<String> onlyCurrentKeys = new HashSet<>(currentKeys);

		onlyCurrentKeys.removeAll(previousKeys);

		for (String listenerKey : onlyCurrentKeys) {
			String[] splitListenerKey = listenerKey.split("\\.");

			if (splitListenerKey.length > 1) {
				String fabId = splitListenerKey[0];
				String mcpName = splitListenerKey[1];
				String key	= fabId + ".oht." + mcpName + ".port";
				int currentPort	= Util.getIntOrZero(properties.getProperty(key, "0").trim());

				listenerMap.put(listenerKey, new OhtUdpListener(fabId, mcpName, currentPort));
				listenerMap.get(listenerKey).start();
			}
		}

		// 2. UDP 삭제
		Set<String> onlyPreviousKeys = new HashSet<>(previousKeys);

		onlyPreviousKeys.removeAll(currentKeys);

		for (String listenerKey : onlyPreviousKeys) {
			OhtUdpListener listener = listenerMap.get(listenerKey);

			listener.stop();
			listenerMap.remove(listenerKey);
		}

		// 3. UDP 유지 혹은 수정(port)
		Set<String> inBoth = new HashSet<>(previousKeys);

		inBoth.retainAll(currentKeys);

		for (String listenerKey : inBoth) {
			OhtUdpListener listener = listenerMap.get(listenerKey);
			String fabId = listener.getFabId();
			String mcpName = listener.getMcpName();
			String key = fabId + ".oht." + mcpName + ".port";
			int previousPort = listener.getPort();
			int currentPort	= Util.getIntOrZero(properties.getProperty(key, "0").trim());

			if (previousPort != currentPort) {
				listener.stop();
				listener.setPort(currentPort);
				listener.start();
			}
		}
	}
}
