public class HubroomTransPredictBatch implements Job{
	private final Logger logger 	= LoggerFactory.getLogger(getClass());
	private final int DELAYED_TIME 	= 1000 * 60;
	private final String folderPath	= FilePathUtil.PYTHON_FILE_PATH;
	private final String fileName 	= "data/HUBROOM_PIVOT_DATA.csv";
	private final String directory 	= folderPath + File.separator + fileName;
	private String errorVhlState;

	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		if (Util.isCurrentIC()) {
			logger.info("... `{}` has started", this.getClass().getSimpleName());

			long timer = System.currentTimeMillis();

			this._run();

			long checkTimer = System.currentTimeMillis() - timer;

			if (checkTimer >= DELAYED_TIME) {
				logger.warn("... !!!DELAYED!!! `{}` has finished [elapsed time: {}m ({}ms)]", this.getClass().getSimpleName(), checkTimer / (60 * 1000), checkTimer);
			} else {
				logger.info("... `{}` has finished [elapsed time: {}ms]", this.getClass().getSimpleName(), checkTimer);
			}
		}
	}

	private void _init() {
		this.errorVhlState = "0";
	}

	private void _run() {
		this._init();

		try {
			// 1. creating input data for hub-room
			this._createInputData();

			File file = new File(directory);

			if (file.exists()) {
				// 2. calculating the prediction of hub-room
				List<Map<String, Object>> prediction = this._predictor();

				// 3. insert in logpresso database
				List<Tuple> logpressoData = XmlUtil.convert(prediction);

				Util.insertInLogpressoDatabase(logpressoData, "test_hubroom_predict", this.getClass().getSimpleName());
			} else {
				logger.error("... csv file that input data of hub-room prediction is not exist [directory: {}]", directory);
			}
		} catch (Exception e) {
			logger.error("", e);
		}
	}

	public void _createInputData() {
		final String INPUT_QUERY_CODE = "HUB_ROOM_INPUT_DATA";
		List<Map<String, Object>> queryData = new ArrayList<>();

		try {
			queryData = XmlUtil.selectLogpressoQuery(INPUT_QUERY_CODE);
		} catch (Exception e) {
			logger.error("... an exception occurred, check an query in `customQuery.xml` [id={}]: {}", INPUT_QUERY_CODE, e.getMessage(), e);
		}

		try {
			List<Map<String, Object>> queryRes = XmlUtil.selectLogpressoQuery("errorVhlVal");

			if (!queryRes.isEmpty() && queryRes.get(0).get("JUDGE_VAL").toString().equals("1")) {
				// VHL OFF 발생 상황
				errorVhlState = "1";
			}
		} catch (Exception e) {
			logger.error("", e);
		}
//----------------------------------------------------------------------------------------------------------------------
		// Convert list of maps to CSV format
		try {
			String csvData = Util.composeCsvFileContent(queryData);

			// CSV 파일(HUBROOM_PIVOT_DATA.csv)로 저장 --- 해당 과정이 선행되어야 hub-room 예측 값에 대한 데이터 수집이 가능
			// ※만약 (smartSTAR)hub-room layout 화면이 동작하지 않는 경우, 예측 값의 부재로 인한 가능성도 검토할 것
			Util.createAndOverwriteFile(folderPath, fileName, csvData);
		} catch (Exception e) {
			logger.error("", e);
		}
//----------------------------------------------------------------------------------------------------------------------
	}

	/**
	 *
	 * @param resData inquired prediction data
	 * @param flow `FLOW` field name
	 * @param pythonFileName python file name ---> for the debugging
	 * @return row data added `WARN_YN` and `JUDGEVAL`
	 */
	private List<Map<String, Object>> _validWarnYN(
			List<Map<String, Object>> resData,
			String flow,
			String pythonFileName
	){
		if (resData == null) {
			// no model
			return new ArrayList<>();
		} else if (resData.isEmpty()) {
			logger.error("... hub-room prediction is empty, it's not applied model or failed to calculate prediction [file={}]", pythonFileName);

			return new ArrayList<>();
		}

		List<Map<String, Object>> result = new ArrayList<>();

		resData.get(0).put("WARN_YN", "N");
		resData.get(0).put("FLOW", flow);

		try {
			List<Map<String, Object>> queryData = XmlUtil.selectLogpressoQuery("hubroomPredict");

			LocalDateTime now 			= LocalDateTime.now().withSecond(0).withNano(0);
			DateTimeFormatter formatter	= DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:00");
			String formattedDateTime 	= now.format(formatter);

			resData.get(0).put("EVENT_DT", formattedDateTime);

			// 최초 등록
			if (!queryData.isEmpty() && queryData.get(0).get("JUDGEVAL") != null) {
				Object judgeValueObject = queryData.get(0).get("JUDGEVAL");

				if (judgeValueObject instanceof Integer) {
					int judgeValue = Integer.parseInt(queryData.get(0).get("JUDGEVAL").toString());

					if (judgeValue < 2) {
						// 0, 1 이외 제외
						switch (judgeValue) {
							case 0:
								resData.get(0).put("JUDGEVAL", resData.get(0).get("JUDGEVAL").toString());
								break;
							case 1:
								if (resData.get(0).get("JUDGEVAL").toString().equals("0")) {
									// PREVAL 1 && CURRENT 0
									resData.get(0).put("JUDGEVAL", resData.get(0).get("JUDGEVAL").toString());
								} else {
									// PREVAL 1 && CURRENT 1
									resData.get(0).put("JUDGEVAL", resData.get(0).get("JUDGEVAL").toString());
									resData.get(0).put("WARN_YN", "Y");
								}
								break;
							default:
						}
					}
				}
			}

			result.addAll(resData);
		} catch (Exception e) {
			logger.error("", e);
		}

		return result;
	}

	private List<Map<String, String>> _preparePredictor() {
		try {
			String temp = XmlUtil.getVariableEnv("HUB_ROOM_MODEL_MAPPER", (Object) null);

			if (temp.contains(XmlUtil.DEFAULT_VALUE)) {
				List<Map<String, String>> defaultFileList = new ArrayList<>();
				List<String> list = new ArrayList<>();
				List<String> flowList = new ArrayList<>();

				list.add("HUB_ROOM_PREDICTOR_10m");
				list.add("HUB_ROOM_PREDICTOR_15m");
				list.add("HUB_ROOM_PREDICTOR_20m");
				list.add("HUB_ROOM_PREDICTOR_25m");
				list.add("HUB_ROOM_PREDICTOR_30m");
				list.add("HUB_ROOM_PREDICTOR_35m");
				flowList.add("HUBROOM_PREDICT");
				flowList.add("HUBROOM_PREDICT_15MIN");
				flowList.add("HUBROOM_PREDICT_20MIN");
				flowList.add("HUBROOM_PREDICT_25MIN");
				flowList.add("HUBROOM_PREDICT_30MIN");
				flowList.add("HUBROOM_PREDICT_35MIN");

				for (int i = 0; i < list.size(); i++) {
					String fileName = list.get(i);
					String flowName = flowList.get(i);
					Map<String, String> map = new HashMap<>();

					map.put("FILE_NM", fileName);
					map.put("FLOW", flowName);

					defaultFileList.add(map);
				}

				return defaultFileList;
			} else {
				return ParseUtil.parseStringToMap(temp);
			}
		} catch (Exception e) {
			logger.error("", e);

			return new ArrayList<>();
		}
	}

	/**
	 * {@link QTransferPredictBatch}
	 */
	private List<Map<String, Object>> _predictor() {
		logger.info("[PREDICT] calculating hub-room prediction has started");

		List<Map<String, String>> pyInfoList= this._preparePredictor();
		List<Map<String, Object>> result 	= new ArrayList<>();
		List<String> logContent 			= new ArrayList<>();
		String errorAddData 				= "30";

		logContent.add("<HUB_ROOM PREDICTION>");

		try {
			errorAddData = XmlUtil.getVariableEnv("VHL_OFF_PLUS_DATA", (Object) null);
		} catch (Exception e) {
			logger.error("", e);
		}

		long totalTimer = System.currentTimeMillis();

		for (Map<String, String> info : pyInfoList) {
			long timer = System.currentTimeMillis();
			String log;
			String fileName = info.get("FILE_NM");
			String flowName = info.get("FLOW");
			List<Map<String, Object>> prediction = PythonUtil.executeWithParam(
					fileName,
					false,
					errorVhlState,
					errorAddData
			);

			if (prediction == null) {
				log = fileName + ": - [elapsed time: -ms] [NO MODEL]";
			} else {
				long checkTimer = System.currentTimeMillis() - timer;
				log = fileName + ": " + prediction.size() + " [elapsed time: " + checkTimer + "ms]";
				List<Map<String, Object>> refinedPrediction = this._validWarnYN(prediction, flowName, fileName);

				result.addAll(refinedPrediction);
			}

			logContent.add(log);
		}
//----------------------------------------------------------------------------------------------------------------------
		// print
		Util.printHelper(logContent);
//----------------------------------------------------------------------------------------------------------------------
		long totalCheckTimer = System.currentTimeMillis() - totalTimer;

		if (totalCheckTimer >= DELAYED_TIME) {
			logger.error("... !!!DELAYED!!! calculating the prediction data of hub-room has finished [elapsed time: {}m ({}ms)]", totalCheckTimer / (60 * 1000), totalCheckTimer);
		} else {
			logger.info("... calculating the prediction data of hub-room has finished [elapsed time: {}ms]", totalCheckTimer);
		}

		return result;
	}
}
