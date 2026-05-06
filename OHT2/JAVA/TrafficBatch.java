/**
 * develop history
 * ...
 * 2025-11-27 변수 추가(absoluteVelocity, maxVelocity, passCnt, vhlCnt) {@link SwitchSystemBatch}
 */
public class TrafficBatch implements Job{
	private final Logger logger 				= LoggerFactory.getLogger(getClass());
	private long currentDateTime 				= -1;
	private List<Integer> rangeOfM14ACenter 	= new ArrayList<>();
	private final int DELAYED_TIME 				= 1000 * 60;
	private static ConcurrentMap<String, Long> lastHisCntMap = new ConcurrentHashMap<>();

	@Override
	public void execute(JobExecutionContext arg0) throws JobExecutionException {
		if (Util.isCurrentIC()) {
			this.currentDateTime = System.currentTimeMillis();

			for (Map.Entry<String, FunctionItem> functionItemEntry : Env.getSwitchMap().entrySet()) {
				String key = functionItemEntry.getKey();	// {fabId}:{mcpName}
				FunctionItem functionItem = functionItemEntry.getValue();

				if (functionItem != null && functionItem.isUseRailTraffic()) {
					String fabId 	= functionItem.getFabId();
					String mcpName 	= functionItem.getMcpName();

					// ▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼▼ M14A 이외 factory 에도 해당 로직을 적용 및 추가할 경우 수정 필수
					if (key.equals("M14A:A")) {
						this._preprocess();
					}

					logger.info("... `TrafficBatch` has started [fab: {} | mcp: {}]", fabId, mcpName);

					long timer = System.currentTimeMillis();

					this._run(fabId, mcpName, functionItem);

					long checkTimer = System.currentTimeMillis() - timer;

					if (checkTimer >= DELAYED_TIME) {
						logger.error("... !!!DELAYED!!! `TrafficBatch` has finished [fab: {} | mcp: {}] [elapsed time: {}m ({}ms)]", fabId, mcpName, checkTimer / (60 * 1000), checkTimer);
					} else {
						logger.info("... `TrafficBatch` has finished [fab: {} | mcp: {}] [elapsed time: {}ms]", fabId, mcpName, checkTimer);
					}
				}
			}
		}
	}

	// run 진행 전 선행 처리(전처리) --- 현재는 M14A 에 한정(20251023)
	private void _preprocess() {
		try {
			String variableString = XmlUtil.getVariableEnv("M14A_CENTER_FROM_NODE", "");

			if (variableString.isEmpty() || variableString.contains("Unknown ALARM CODE")) {
				this.rangeOfM14ACenter = new ArrayList<>();
			} else {
				List<Integer> result = new ArrayList<>();
				String[] list = variableString.split(",");

				for (String s : list) {
					if (s == null || s.trim().isEmpty()) continue;

					if (s.contains("-")) {
						String[] between = s.split("-");

						if (between.length == 2) {
							int toAddress, fromAddress;

							try {
								fromAddress	= Integer.parseInt(between[0]);
								toAddress 	= Integer.parseInt(between[1]);

								if (toAddress <= fromAddress) {
									logger.error("... it's invalid value. from value must not be greater than to value[from < to] [from: {} | to: {}]", fromAddress, toAddress);
									continue;
								}

								for (int i = fromAddress; i <= toAddress; i++) {
									result.add(i);
								}
							} catch (NumberFormatException e) {
								logger.error("... !!!NumberFormatException!!! it's invalid value [input: {}]", s, e);
							}
						} else {
							logger.error("... it's invalid value. '-' If the symbol is included, it must be in `from-to` format [input: {}]", s);
						}
					} else {
						try {
							int address = Integer.parseInt(s);

							result.add(address);
						} catch (NumberFormatException e) {
							logger.error("... !!!NumberFormatException!!! it's invalid value [input: {}]", s, e);
						}
					}
				}

				this.rangeOfM14ACenter = result;
			}
		} catch (Exception e) {
			logger.error("", e);
		}
	}

	private void _run(String fabId, String mcpName, FunctionItem functionItem) {
//		if (Env.getEnv().equals("TEST")) {
//			int max = 200;
//			int min = 100;
//			double random1 = Math.random() * (max - min) + min;
//			double random2 = Math.random() * (max - min) + min;
//
//			this._addTibSenderWaiting(fabId, random1, random2);
//		} else {
			List<Tuple> logpressoData = new ArrayList<>();
			// `... NotIncludeInit` 는 서버가 구동 후 속력 값이 변화없이 초기 값을 유지 중인 값을 배제한 값만을 취급
			double totalNotIncludeInitVal = 0.0;
			double totalOnlyInitVal 	= 0.0;
			int countNotIncludeInitVal 	= 0;
			int countOnlyInitVal 		= 0;

			// -----------M14A(center)-----------
			int centerTotalCount 		= 0;
			double centerTotalVelocity 	= 0;
			// ----------------------------------

			try {
				for (RailEdge railEdge : DataService.getDataSet().getRailEdgeMap().values()) {
					if (!railEdge.getFabId().equals(fabId)) continue;

					String railEdgeId = railEdge.getId();
					double velocity = railEdge.getVelocity();

					lastHisCntMap.putIfAbsent(railEdgeId, 0L);

					// -------------------------M14A(center)-------------------------
					if (fabId.equals("M14A") && mcpName.equals("A")) {
						// M14A center 에 한정된 평균 속력 계산
						if (this.rangeOfM14ACenter.contains(railEdge.getFromAddress())) {
							centerTotalVelocity += velocity;
							centerTotalCount++;
						}
					}
					// --------------------------------------------------------------

					// 초기화 이후 속력 값 변동이 있는 값 구분
					if (railEdge.isChangedVelocity()) {
						totalNotIncludeInitVal += velocity;
						countNotIncludeInitVal++;
					} else {
						totalOnlyInitVal += velocity;
						countOnlyInitVal++;
					}

					if (functionItem.isUseRailTrafficSub()) {
						Tuple tuple = this._buildBase(railEdge, functionItem);

						if (tuple != null) {
							logpressoData.add(tuple);
						}
					}

					// _buildBase() 에 영향을 미칠 수 있기 때문에 후순위 적재
					lastHisCntMap.put(railEdgeId, railEdge.getHisCnt());
				}

				double averageNotIncludeInit = Math.round((totalNotIncludeInitVal / countNotIncludeInitVal) * 10) / 10.0;
				double averageForTotal = Math.round(((totalNotIncludeInitVal + totalOnlyInitVal) / (countNotIncludeInitVal + countOnlyInitVal)) * 10) / 10.0;

				// -------------------------M14A(center)-------------------------
				double centerVelocityAverage = Math.round((centerTotalVelocity / centerTotalCount) * 10) / 10.0;
				// --------------------------------------------------------------

				logpressoData.add(this._buildHeaderBase(
						fabId,
						mcpName,
						averageNotIncludeInit,
						"AVERAGE_PER_1MINUTES"
				));

				logpressoData.add(this._buildHeaderBase(
						fabId,
						mcpName,
						averageForTotal,
						"AVERAGE_PER_1MINUTES_INCLUDE_INITIALIZATION"
				));

				this._addTibSenderWaiting(fabId, averageNotIncludeInit, centerVelocityAverage);

				Util.insertInLogpressoDatabase(logpressoData, "ATLAS_RAIL_TRAFFIC", this.getClass().getSimpleName());
			} catch (Exception e) {
				logger.error("", e);
			}
//		}
	}

	private Tuple _buildHeaderBase(
			String fabId,
			String mcpName,
			double velocity,
			String railEdgeId
	) {
		Tuple result = new Tuple();

		result.put("fabId", fabId);
		result.put("mcpName", mcpName);

		if (railEdgeId != null) {
			result.put("railEdgeId", railEdgeId);
		}

		result.put("velocity", velocity);
		result.put("vhlStageWaitCnt", 0);

		return result;
	}

	/**
	 * 
	 * @param fabId factory ID
	 * @param averageVelocity 송신할 평균 속력 값
	 * @param specificallyVelocity 송신할 특정 레일의 평균 속력 값 --- M14A(center) 평균 속력 (20251023)
	 */
	private void _addTibSenderWaiting(String fabId, double averageVelocity, double specificallyVelocity) {
		if (!fabId.equals("M14A")) return;	// M14A 에 한정

		FabProperties fabProperties = DataService.getInstance().getFabPropertiesMap().get(fabId);
		String facId = fabProperties.getFacId();

		Map<String, String> dataMap = LayoutUtil.buildLayoutMessageDataMap(
				TibrvService.SEND_SUB_SUBJECT.VHL_AVG_SPEED,
				fabId,
				"AVG",
				OhtMsgWorkerRunnable.OHT_TIB_STATE.NORMAL,
				null,
				averageVelocity + "," + specificallyVelocity,
				null,
				null,
				facId,
				null,
				null,
				false
		);

		for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:").keySet()) {
			DataService.getInstance().addTibrvMessageQueue(
					tibrvKey,
					TibrvService.SEND_SUB_SUBJECT.VHL_AVG_SPEED,
					dataMap
			);
		}
	}

	private Tuple _buildBase(RailEdge railEdge, FunctionItem functionItem) {
		Tuple result = new Tuple();
		String fabId, mcpName;
		fabId 	= functionItem.getFabId();
		mcpName	= functionItem.getMcpName();

		try {
			String railEdgeId 	= railEdge.getId();
			double velocity 	= railEdge.getVelocity();
			double maxVelocity 	= railEdge.getMaxVelocity();

			result.put("createTime", this.currentDateTime);
			result.put("railEdgeId", railEdgeId);
			result.put("fabId", fabId);
			result.put("mcpName", mcpName);
			result.put("HID_ID", railEdge.getHIDId());    // HID 구간 별 속력 값을 계산을 위해 추가

			result.put("velocity", velocity);

			if (functionItem.isUseRailTrafficMaxVelocity()) {
				result.put("maxVelocity", maxVelocity);
			}

			if (functionItem.isUseRailTrafficAbsoluteVelocity()) {
				result.put("absoluteVelocity", velocity / maxVelocity);
			}

			if (functionItem.isUseRailTrafficVhlCnt()) {
				result.put("vhlCnt", railEdge.getVhlIdMap().size());
			}

			if (functionItem.isUseRailTrafficPassCnt()) {
				long passedCount = railEdge.getHisCnt();
				long lastPassedCount = lastHisCntMap.get(railEdgeId);
				long passingCount = passedCount - lastPassedCount;

				if (passingCount < 0) {
					passingCount = 0;

					lastHisCntMap.put(railEdgeId, 0L);
				}

				result.put("passCnt", passingCount);
			}

			result.put("vhlStageWaitCnt", 0);
			result.put("vhlStageWaitList", ""); // 테스트 용으로 추가 (port 값을 갖지 않을 것으로 예상)

			result.put("is_initialized", railEdge.isChangedVelocity()); // 테스트 용으로 추가 (port 값을 갖지 않을 것으로 예상)
		} catch (Exception e) {
			return null;
		}

		return result;
	}
}