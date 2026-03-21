public class DataSetRefreshBatch implements Job{
	private final Logger logger 	= LoggerFactory.getLogger(getClass());
	private final int DELAYED_TIME 	= 1000 * 60;

	@Override
	public void execute(JobExecutionContext arg0) throws JobExecutionException {
		if (Util.isCurrentIC()) {
			for (Map.Entry<String, FunctionItem> functionItemEntry : Env.getSwitchMap().entrySet()) {
				FunctionItem functionItem = functionItemEntry.getValue();

				if (functionItem != null && functionItem.isUseMapFileRefresh()) {
					String fabId 	= functionItem.getFabId();
					String mcpName 	= functionItem.getMcpName();

					logger.info("... `{}` has started [fab: {} | mcp: {}]", this.getClass().getSimpleName(), fabId, mcpName);

					long timer = System.currentTimeMillis();

					this._run(fabId, mcpName);

					long checkTimer = System.currentTimeMillis() - timer;

					if (checkTimer >= DELAYED_TIME) {
						logger.error("... !!!DELAYED!!! `{}` has finished [fab: {} | mcp: {}] [elapsed time: {}m ({}ms)]", this.getClass().getSimpleName(), fabId, mcpName, checkTimer / (60 * 1000), checkTimer);
					} else {
						logger.info("... `{}` has finished [fab: {} | mcp: {}] [elapsed time: {}ms]", this.getClass().getSimpleName(), fabId, mcpName, checkTimer);
					}
				}
			}
		}
	}

	private void _run(String fabId, String mcpName) {
		List<Integer> downloadFileMap = this._downloader(fabId, mcpName);

		// 데이터 갱신 및 적용
		if (!downloadFileMap.isEmpty()) {
			DataService.getInstance().newMapLoad();

			this._update(downloadFileMap, fabId);

			logger.info("... applicative for new map file completely");
		}
	}

	private List<Integer> _downloader(String fabId, String mcpName) {
		String key = fabId + ":" + mcpName;

		logger.info("check the railcut file and start downloading [{}]", key);

		return Util.getAllOhtLayoutFileOverFtp(
				fabId,
				mcpName,
				false,
				true,
				true,
				true,
				true
		);
	}

	// 다운로드 받은 맵 파일 중 수정된 내용이 존재할 경우, 기존의 이상 현상(HID OFF, VHL OFF, RAIL CUT)에 대해 서버에 저장한 값을 수정
	// 기존 값이 ABNORMAL 인 경우, 해당 값을 NORMAL 상태로 송신 후 수정한 값으로 재송신 (이때 수정한 값은 원래 상태인 ABNORMAL 상태로 송신)
	private void _update (List<Integer> downloadFileMap, String fabId) {
		List<Map<String, String>> messageDataList = new ArrayList<>();

		if (!downloadFileMap.isEmpty()) {
			messageDataList.addAll(this._updateHidOff(fabId, downloadFileMap));
			messageDataList.addAll(this._updateVhlOff(fabId, downloadFileMap));
			messageDataList.addAll(this._updateRailCut(fabId, downloadFileMap));
		}

		for (Map<String, String> messageData : messageDataList) {
			if (messageData.isEmpty()) continue;

			for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:").keySet()) {
				String layoutType = messageData.get(LAYOUT_MEMBER.DEVICE_TYPE);

				DataService.getInstance().addTibrvMessageQueue(tibrvKey, layoutType, messageData);
			}
		}
	}

	private List<Map<String, String>> _updateHidOff (String fabId, List<Integer> fileList) {
		List<Map<String, String>> messageDataList 				= new ArrayList<>();
		ConcurrentMap<String, HidOffRecordItem> recordItemMap 	= DataService.getDataSet().getHidOffRecordMap();

		if (!(fileList.contains(DOWNLOAD_MAP_FILE_TYPE.MCP75CFG)) || fileList.contains(DOWNLOAD_MAP_FILE_TYPE.STATION)) {
			return messageDataList;
		}

		for (String key : recordItemMap.keySet()) {	// key: {fabId}:{hidId}:{address}
			HidOffRecordItem recordItem = recordItemMap.get(key);

			if (recordItem.getFabId().equals(fabId)) {
				RailEdge railEdge = recordItem.getRailEdge();

				if (railEdge == null) {
					logger.warn("Revised RailEdge Is Not Matched With Current HidOff Data. (Fab: {}) ", fabId);
					continue;
				}

				// ##1 기존 값
				Map<String, String> originalDataMap = LayoutUtil.buildLayoutMessageDataMap(
						recordItem.getAlarmType(),
						recordItem.getFabId(),
						recordItem.getHidIdString(),
						OHT_TIB_STATE.NORMAL,
						recordItem.getHidAreaAddressString(),
						recordItem.getAffectedPortString(),
						"",
						recordItem.getAlarmCode(),
						recordItem.getFacId(),
						"",
						"",
						false
				);

				// ##2 수정된 값
				final ConcurrentMap<String, RailEdge> railEdgeMap = DataService.getDataSet().getRailEdgeMap();
				String mapKey = String.format("%s:%d", fabId, railEdge.getHIDId());

				Map<String, String> newDataMap = new HashMap<>(originalDataMap);
				String code = String.format("HID%03d", recordItem.getHidId());
				String alarmDescription = XmlUtil.getMessage("OHT_LAYOUT_HID_OFF_DESC", fabId, code);
				String alarmTitle = XmlUtil.getMessage("OHT_LAYOUT_HID_OFF_TITLE", fabId, code);
				String alarmMessageContents = XmlUtil.getMessage("OHT_LAYOUT_HID_OFF_CONTENTS", recordItem.getAffectedPortString());

				newDataMap.put(LAYOUT_MEMBER.LAYOUT_STATE, OHT_TIB_STATE.ABNORMAL);
				newDataMap.put(LAYOUT_MEMBER.ALARM_DESCRIPTION, alarmDescription);
				newDataMap.put(LAYOUT_MEMBER.ALARM_COMMENT, alarmTitle);
				newDataMap.put(LAYOUT_MEMBER.ALARM_MESSAGE_CONTENTS, alarmMessageContents);
				newDataMap.put(LAYOUT_MEMBER.ALARM_YN, "Y");

				// ## 2-1 mcp75.cfg 파일이 수정된 경우
				if (fileList.contains(DOWNLOAD_MAP_FILE_TYPE.MCP75CFG)) {
					Set<String> addressRevised = new HashSet<>();
					List<String> railEdgeIdList = DataService.getDataSet().getRailEdge4HidMap().get(mapKey);

					for (String railEdgeId : railEdgeIdList) {
						RailEdge re = railEdgeMap.get(railEdgeId);
						addressRevised.add(re.getAddress());
					}

					recordItem.setHidAreaAddress(addressRevised);
					newDataMap.put(LAYOUT_MEMBER.ADDRESS_LIST, recordItem.getHidAreaAddressString());
				}

				// ## 2-2 station.dat 파일이 수정된 경우
				if (fileList.contains(DOWNLOAD_MAP_FILE_TYPE.STATION)) {
					List<String> portIdRevised = DataService.getDataSet().getHid2PortMap().get(mapKey);
					recordItem.setAffectedPort(portIdRevised);
					newDataMap.put(LAYOUT_MEMBER.PORT_LIST, recordItem.getAffectedPortString());

				}

				// ##0 수정된 값에 대한 메세지 적재
				messageDataList.add(originalDataMap);
				messageDataList.add(newDataMap);
			}
		}

		return messageDataList;
	}

	private List<Map<String, String>> _updateVhlOff (
			String fabId,
			List<Integer> fileList
	) {
		List<Map<String, String>> messageDataList = new ArrayList<>();
		ConcurrentMap<String, VhlOffRecordItem> recordItemMap = DataService.getDataSet().getVhlOffRecordMap();

		if (!(fileList.contains(DOWNLOAD_MAP_FILE_TYPE.LAYOUT) || fileList.contains(DOWNLOAD_MAP_FILE_TYPE.STATION))) {
			return messageDataList;
		}

		for (String key : recordItemMap.keySet()) {	// key : {fabId}:{vhlName}
			VhlOffRecordItem recordItem = recordItemMap.get(key);

			if (recordItem.getFabId().equals(fabId)) {
				RailEdge railEdge = recordItem.getRailEdge();

				if (railEdge == null) {
					logger.warn("Revised railEdge is not matched with current VhlOff Data (fab: {}) !", fabId);
					continue;
				}

				// ##1 기존 값
				Map<String, String> originalDataMap = LayoutUtil.buildLayoutMessageDataMap(
						recordItem.getAlarmType(),
						recordItem.getFabId(),
						recordItem.getDeviceId(),
						OHT_TIB_STATE.NORMAL,
						recordItem.getAffectedAddressString(),
						recordItem.getAffectedPortString(),
						"",
						recordItem.getErrorCode(),
						recordItem.getFacId(),
						"",
						"",
						false
				);

				// ##2 수정된 값
				Navigator navigator = new Navigator(railEdge);
				Map<String, String> newDataMap = new HashMap<>(originalDataMap);
				String alarmDescription = XmlUtil.getMessage("OHT_LAYOUT_VHL_OFF_DESC", fabId, recordItem.getMachineId());
				String alarmTitle = XmlUtil.getMessage("OHT_LAYOUT_VHL_OFF_TITLE", fabId, recordItem.getStoppedFromAddress() + ":" + recordItem.getStoppedToAddress());
				String alarmMessageContents = XmlUtil.getMessage("OHT_LAYOUT_VHL_OFF_CONTENTS", recordItem.getAffectedPortString());
				newDataMap.put(LAYOUT_MEMBER.LAYOUT_STATE, OHT_TIB_STATE.ABNORMAL);
				newDataMap.put(LAYOUT_MEMBER.ALARM_DESCRIPTION, alarmDescription);
				newDataMap.put(LAYOUT_MEMBER.ALARM_COMMENT, alarmTitle);
				newDataMap.put(LAYOUT_MEMBER.ALARM_MESSAGE_CONTENTS, alarmMessageContents);
				newDataMap.put(LAYOUT_MEMBER.ALARM_YN, "Y");

				// ## 2-1 layout.zip 파일이 수정된 경우
				if (fileList.contains(DOWNLOAD_MAP_FILE_TYPE.LAYOUT)) {
					Set<String >addressSet = navigator.getAffectedRailSet();
					recordItem.setAffectedAddress(addressSet);
					newDataMap.put(LAYOUT_MEMBER.ADDRESS_LIST, recordItem.getAffectedAddressString());
				}

				// ## 2-2 station.dat 파일이 수정된 경우
				if (fileList.contains(DOWNLOAD_MAP_FILE_TYPE.STATION)) {
					List<String> portList = navigator.getAffectedPortSortedList();
					recordItem.setAffectedPort(portList);
					newDataMap.put(LAYOUT_MEMBER.PORT_LIST, recordItem.getAffectedPortString());
				}

				// ##0 수정된 값에 대한 메세지 적재
				messageDataList.add(originalDataMap);
				messageDataList.add(newDataMap);
			}
		}
		return messageDataList;
	}

	private List<Map<String, String>> _updateRailCut (
			String fabId,
			List<Integer> fileList
	) {
		List<Map<String, String>> messageDataList = new ArrayList<>();
		final ConcurrentMap<String, RailCutRecordItem> recordItemMap = DataService.getDataSet().getRailCutRecordMap();

		if (!(fileList.contains(DOWNLOAD_MAP_FILE_TYPE.LAYOUT) || fileList.contains(DOWNLOAD_MAP_FILE_TYPE.STATION))) {
			return messageDataList;
		}

		for (Map.Entry<String, RailCutRecordItem> entry : recordItemMap.entrySet()) {	// key : {fabId}:{mcpName}
			if (!entry.getKey().startsWith("M14A:A")) continue; //*

			String[] splitKey = entry.getKey().split(":");

			if (splitKey.length < 3) continue;

			RailCutRecordItem recordItem = entry.getValue();

			if (recordItem.getFabId().equals(fabId)) {
				RailEdge railEdge = recordItem.getRailEdge();

				if (railEdge == null) {
					logger.warn("Revised railEdge is not matched with current RailCut data (fab: {}) !", fabId);
					continue;
				}

				// ##1 기존 값
				Map<String, String> originalDataMap = LayoutUtil.buildLayoutMessageDataMap(
						recordItem.getAlarmType(),
						recordItem.getFabId(),
						recordItem.getDeviceId(),
						OHT_TIB_STATE.NORMAL,
						recordItem.getAffectedAddressString(),
						recordItem.getAffectedPortString(),
						"",
						"",
						recordItem.getFacId(),
						"",
						"",
						false
				);

				// ##2 수정된 값
				Navigator navigator = new Navigator(railEdge);
				Map<String, String> newDataMap = new HashMap<>(originalDataMap);
				String alarmDescription = XmlUtil.getMessage("OHT_LAYOUT_RAIL_CUT_DESC", fabId, recordItem.getDeviceId());
				String alarmTitle = XmlUtil.getMessage("OHT_LAYOUT_RAIL_CUT_TITLE", fabId, recordItem.getRailCutFromAddress() + ":" + recordItem.getRailCutToAddress());
				String alarmMessageContents = XmlUtil.getMessage("OHT_LAYOUT_RAIL_CUT_CONTENTS", recordItem.getAffectedPortString());
				newDataMap.put(LAYOUT_MEMBER.LAYOUT_STATE, OHT_TIB_STATE.ABNORMAL);
				newDataMap.put(LAYOUT_MEMBER.ALARM_DESCRIPTION, alarmDescription);
				newDataMap.put(LAYOUT_MEMBER.ALARM_COMMENT, alarmTitle);
				newDataMap.put(LAYOUT_MEMBER.ALARM_MESSAGE_CONTENTS, alarmMessageContents);
				newDataMap.put(LAYOUT_MEMBER.ALARM_YN, "Y");

				// ## 2-1 layout.zip 파일이 수정된 경우
				if (fileList.contains(DOWNLOAD_MAP_FILE_TYPE.LAYOUT)) {
					Set<String> addressSet = navigator.getAffectedRailSet();
					recordItem.setAffectedAddress(addressSet);
					newDataMap.put(LAYOUT_MEMBER.ADDRESS_LIST, recordItem.getAffectedAddressString());
				}

				// ## 2-2 station.dat 파일이 수정된 경우
				if (fileList.contains(DOWNLOAD_MAP_FILE_TYPE.STATION)) {
					List<String> portIdList = navigator.getAffectedPortSortedList();
					recordItem.setAffectedPort(portIdList);
					newDataMap.put(LAYOUT_MEMBER.PORT_LIST, recordItem.getAffectedPortString());
				}

				// ##0 수정된 값에 대한 메세지 적재
				messageDataList.add(originalDataMap);
				messageDataList.add(newDataMap);
			}
		}

		return messageDataList;
	}
}
