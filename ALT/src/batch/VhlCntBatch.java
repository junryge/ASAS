public class VhlCntBatch implements Job{
	private final Logger logger = LoggerFactory.getLogger(getClass());
	private final int DELAYED_TIME = 1000 * 60;

	@Override
	public void execute(JobExecutionContext arg0) throws JobExecutionException {
		if (Util.isCurrentIC()) {
			for (Map.Entry<String, FunctionItem> functionItemEntry : Env.getSwitchMap().entrySet()) {
				FunctionItem functionItem = functionItemEntry.getValue();

				if (functionItem != null && functionItem.isUseVhlCnt()) {
					String fabId 	= functionItem.getFabId();
					String mcpName 	= functionItem.getMcpName();
					long timer 		= System.currentTimeMillis();

					// 다른 주기의 동일한 기능(VHL_CNT)이 동작 중인 경우 ---> 동작 취소
					if (functionItem.isUseVhlCnt10() || functionItem.isUseVhlCnt30() || functionItem.isUseVhlCnt60()) {
						List<String> t = new ArrayList<>();

						t.add(functionItem.isUseVhlCnt10() ? FunctionType.VHL_CNT_10.getKey() : "");
						t.add(functionItem.isUseVhlCnt30() ? FunctionType.VHL_CNT_30.getKey() : "");
						t.add(functionItem.isUseVhlCnt60() ? FunctionType.VHL_CNT_60.getKey() : "");

						String context = t.stream()
								.filter(_t -> !_t.isEmpty())
								.collect(Collectors.joining(", "));

						logger.error("... `{}` function at different timings is allowed [fab: {} | mcp: {}]\n>> {}", this.getClass().getSimpleName(), fabId, mcpName, context);

						return;
					}

					logger.info("... `{}` has started [fab: {} | mcp: {}]", this.getClass().getSimpleName(), fabId, mcpName);

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
		final ConcurrentMap<String, Integer> recordMap = DataService.getDataSet().getHidVehicleCountMap();

		List<Tuple> logpressoData	= new ArrayList<>();
		List<String> hid2VhlCntList	= new ArrayList<>();
		final String compareKey 	= fabId + ":" + mcpName;

		if (recordMap.isEmpty()) return;

		List<String> sortedKeys = recordMap.keySet().stream().sorted().collect(Collectors.toList());

		for (String key : sortedKeys) {
			String regex 	= "^(" + Pattern.quote(compareKey) + "):(.*)$";
			Pattern pattern	= Pattern.compile(regex);
			Matcher matcher	= pattern.matcher(key);

			if (matcher.matches()) {
				String extract 	= matcher.group(2);
				int hidId 		= Integer.parseInt(extract);
				int count 		= recordMap.get(key);

				hid2VhlCntList.add(hidId + ":" + count);

				logpressoData.add(this._getVhlCntTuple(fabId, mcpName, hidId, count));
			}
		}

		Util.insertInLogpressoDatabase(logpressoData, "ATLAS_OHT_VHL_CNT", this.getClass().getSimpleName());

		String facId = "";

		if (fabId.startsWith("M14") || fabId.contains("M14")) {
			facId = "M14";
		} else if (fabId.startsWith("M16") || fabId.contains("M16")) {
			facId = "M16";
		}

		Map<String, String> dataMap = LayoutUtil.buildLayoutMessageDataMap(
				SEND_SUB_SUBJECT.VHL_CNT,
				fabId,
				"VHLCNT",
				OHT_TIB_STATE.NORMAL,
				null,
				String.join(",", hid2VhlCntList),
				null,
				null,
				facId,
				null,
				null,
				false
		);

		this._addTibSenderWaiting(fabId, dataMap);
	}

	private Tuple _getVhlCntTuple(String fabId, String mcpName, int hidId, int count) {
		Tuple tuple = new Tuple();

		tuple.put("FAB_ID", fabId);
		tuple.put("HID_ID", hidId);
		tuple.put("MACHINE_CNT", count);
		tuple.put("MCP_NM", mcpName);

		return tuple;
	}

	private void _addTibSenderWaiting(String fabId, Map<String, String> dataMap) {
		for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:").keySet()) {
			DataService.getInstance().addTibrvMessageQueue(
					tibrvKey,
					SEND_SUB_SUBJECT.VHL_CNT,
					dataMap
			);
		}
	}
}
