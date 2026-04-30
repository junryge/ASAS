public class QTransferPredictBatch implements Job{
	private final Logger logger 	= LoggerFactory.getLogger(getClass());
	private final String folderPath	= FilePathUtil.PYTHON_FILE_PATH;
	private final String fileName 	= "data/QTRANSFER.csv";
	private final String directory 	= folderPath + File.separator + fileName;
	private final int DELAYED_TIME 	= 1000 * 60;
	private LocalDateTime eventDataTime = null;

	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		if (Util.isCurrentIC()) {
			logger.info("... `{}` has started", this.getClass().getSimpleName());

			long timer = System.currentTimeMillis();

			this._run();

			long checkTimer = System.currentTimeMillis() - timer;

			if (checkTimer >= DELAYED_TIME) {
				logger.error("... !!!DELAYED!!! `{}` has finished [elapsed time: {}m ({}ms)]", this.getClass().getSimpleName(), checkTimer / (60 * 1000), checkTimer);
			} else {
				logger.info("... `{}` has finished [elapsed time: {}ms]", this.getClass().getSimpleName(), checkTimer);
			}
		}
	}

	private void _init() {
		this.eventDataTime = LocalDateTime.now();
	}

	private void _run() {
		// 결과 데이터 가공
		List<String> desiredOrder = Arrays.asList(
				"TIME",
				"IDCCOL",
				"IDCVAL",
				"IQR_Q1",
				"IQR_Q2",
				"IQR_LOWER",
				"IQR_UPPER",
				"IQR_JUDGE",
				"AVERAGE",
				"STANDARDDEVIATION",
				"SD_LOWER",
				"SD_UPPER",
				"SD_JUDGE",
				"LSTM",
				"LSTM_JUDGE",
				"ALARM_CD",
				"ALARM_CMT",
				"ALARM_DESC",
				"ALARM_MSG_CTN",
				"ALARM_YN"
		);

		// 예측 결과 값 과 예측값의 상태 값 다른 테이블 적재이기에, 분리 적용
		Map<String, Object> predictionStateMap 	= new HashMap<>();		// 상태 값만 취급
		Map<String, Object> predictionMap 		= new HashMap<>();
		double prediction = -1;
//----------------------------------------------------------------------------------------------------------------------
		this._init();

		List<Map<String, Object>> monitoringAlarmList = this._buildTransportAlarm();

		this._createInputData();

		try {
			File file = new File(this.directory);

			if (file.exists()) {
				predictionMap = this._predictor();
				Object predictionObject = predictionMap.get("LSTM");

				if (predictionObject == null) {
					String exceptionMessage = "... q-transfer prediction is null value, so process exited";

					throw new NullPointerException(exceptionMessage);
				} else {
					try {
						prediction = Double.parseDouble(predictionObject.toString());
					} catch (NumberFormatException e) {
						String exceptionMessage = "... q-transfer prediction is invalid value, it's mismatched numerical format, so process exited";

						throw new NumberFormatException(exceptionMessage);
					}
				}

				predictionStateMap.put("STATE", predictionMap.get("STATE"));
				predictionStateMap.put("STATE_PER", predictionMap.get("STATE_PER"));

				// 상태값 저장 ---> dash board 에 저장
				this._insertPredictionState(predictionStateMap);

				// 기존 예측 값 & 알람 내용 병합
				List<Map<String, Object>> resPivotData = this._getPivotData(prediction);

				monitoringAlarmList.addAll(resPivotData);
			} else {
				String exceptionMessage = "... csv file for q-transfer prediction input data is not found, and this process exited [directory: " + directory + "]";

				throw new FileNotFoundException(exceptionMessage);
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		// 컬럼 순서 강제 정렬
		List<Map<String, Object>> reorderedList = new ArrayList<>();

		for (Map<String, Object> entry : monitoringAlarmList) {
			Map<String, Object> reorderedEntry = new LinkedHashMap<>();

			for (String key : desiredOrder) {
				Object value = entry.get(key);

				reorderedEntry.put(key, value);
			}

			reorderedList.add(reorderedEntry);
		}

		try {
			// 예측값 최종 결과 리스트 합치기
			for (int i = 0; i < reorderedList.size(); i++) {
				Map<String, Object> data = reorderedList.get(i);
				Object idcColObject = data.get("IDCCOL");

				if (idcColObject == null) {
					logger.error("... `IDCCOL` field is null value [index: {}] [t: {}]", i, data);
					continue;
				}

				if ("TOTALCNT".equals(idcColObject.toString())) {
					// IDCVAL 값을 가져옴
					String idcValString = data.get("IDCVAL") == null ? null : data.get("IDCVAL").toString();
					double idcVal;

					if (idcValString == null) {
						logger.error("... `IDCVAL` field is null value [index: {}] [t: {}]", i, data);
						continue;
					} else {
						try {
							idcVal = Double.parseDouble(idcValString);
						} catch (NumberFormatException e) {
							logger.error("", e);
							continue;
						}
					}

					// 10% 이상 차이가 나면 LSTM_JUDGE = Y
					double percentageDifference = Math.abs((idcVal - prediction) / idcVal) * 100;

					if (percentageDifference >= 10) {
						data.put("LSTM_JUDGE", "Y");
					} else {
						data.put("LSTM_JUDGE", "N");
					}

					data.putAll(predictionMap);
				} else {
					Map<String, Object> emptyVal = new HashMap<>();

					emptyVal.put("LSTM", "");
					emptyVal.put("LSTM_JUDGE", "N");

					data.putAll(emptyVal);
				}
			}

			// 최종 데이터 소수점 처리
			for (Map<String, Object> map : reorderedList) {
				for (String key : map.keySet()) {
					Object value = map.get(key);

					if (value instanceof Double) {
						double roundedValue = Math.round(((Double) value) * 100.0) / 100.0;

						map.put(key, roundedValue);
					}
				}
			}

			DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMddHHmm");
			String eventDt = this.eventDataTime.format(formatter);

			for (Map<String, Object> row : reorderedList) {
				// EVENT_DT 값 동기화
				row.put("TIME", eventDt);
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		if (!reorderedList.isEmpty()) {
			List<Tuple> logpressoData = XmlUtil.convert(reorderedList);

			Util.insertInLogpressoDatabase(
					logpressoData,
					"test_currentjob_predict",
					this.getClass().getSimpleName()
			);
		}
	}

	private void _createInputData() {
		try {
			List<Map<String, Object>> queryData = XmlUtil.selectLogpressoQuery("Q_TRANSFER_INPUT_DATA");

			String csvData = Util.composeCsvFileContent(queryData);

			Util.createAndOverwriteFile(folderPath, fileName, csvData);
		} catch (Exception e) {
			logger.error("", e);
		}
	}

	/*
	 * calculating the prediction
	 */
	private List<Map<String, String>> _preparePredictor() {
		try {
			String temp = XmlUtil.getVariableEnv("Q_TRANSFER_MODEL_MAPPER", (Object) null);

			if (temp.contains(XmlUtil.DEFAULT_VALUE)) {
				List<Map<String, String>> defaultFileList = new ArrayList<>();
				List<String> list = new ArrayList<>();

				list.add("Q_TRANSFER_PREDICTOR_10m");
				list.add("Q_TRANSFER_PREDICTOR_15m");
				list.add("Q_TRANSFER_PREDICTOR_20m");
				list.add("Q_TRANSFER_PREDICTOR_25m");
				list.add("Q_TRANSFER_PREDICTOR_30m");
				list.add("Q_TRANSFER_PREDICTOR_35m");

				for (String item : list) {
					Map<String, String> map = new HashMap<>();

					map.put("FILE_NM", item);

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

	private String _selectDisplayedPrediction() {
		String result = "Q_TRANSFER_PREDICTOR_10m.py";

		try {
			String temp = XmlUtil.getVariableEnv("Q_TRANSFER_MODEL_MAPPER_DEFAULT");

			if (!temp.contains(XmlUtil.DEFAULT_VALUE) && !temp.trim().isEmpty()) {
				result = temp.trim();
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		return result;
	}

	/**
	 * {@link HubroomTransPredictBatch}
	 */
	private Map<String, Object> _predictor() {
		logger.info("[PREDICT] calculating q-transfer prediction has started");

		List<Map<String, String>> pyInfoList = this._preparePredictor();
		String selectedKey 			= this._selectDisplayedPrediction();
		List<String> logContent 	= new ArrayList<>();
		Map<String, Object> result 	= new HashMap<>();
		Map<String, List<Map<String, Object>>> predictionMap = new HashMap<>();

		logContent.add("<Q_TRANSFER PREDICTION>");

		for (Map<String, String> info : pyInfoList) {
			long timer = System.currentTimeMillis();
			String log;
			String fileName = info.get("FILE_NM");
			List<Map<String, Object>> prediction = PythonUtil.executeWithParam(fileName, false);

			if (prediction == null) {
				log = fileName + ": - [elapsed time: -ms] [NO MODEL]";

				predictionMap.put(fileName, new ArrayList<>());
			} else {
				long checkTimer = System.currentTimeMillis() - timer;
				log = fileName + ": " + prediction.size() + " [elapsed time: " + checkTimer + "ms]";

				predictionMap.put(fileName, prediction);
			}

			logContent.add(log);
		}
//----------------------------------------------------------------------------------------------------------------------
		// print
		Util.printHelper(logContent);
//----------------------------------------------------------------------------------------------------------------------
		// logpresso (temp)
		List<Tuple> logpressoData = this._buildLogpressoDataWithPrediction(predictionMap);

		Util.insertInLogpressoDatabase(logpressoData, "ATLAS_TS_PREDICT", this.getClass().getSimpleName());

		// 차후 UI 상 다른 모델의 예측 값도 포함될 경우, 새로운 데이터에 맞게 해당 로직의 수정이 필요
		if (predictionMap.get(selectedKey) != null && !predictionMap.get(selectedKey).isEmpty()) {
			result = predictionMap.get(selectedKey).get(0);
		}

		return result;
	}

	private List<Tuple> _buildLogpressoDataWithPrediction(Map<String, List<Map<String, Object>>> predictionMap) {
		List<Tuple> logpressoData = new ArrayList<>();

		for (Map.Entry<String, List<Map<String, Object>>> entry : predictionMap.entrySet()) {
			String fileName = entry.getKey();
			List<Map<String, Object>> rows = entry.getValue();

			if (rows != null && !rows.isEmpty()) {
				Map<String, Object> row = rows.get(0);	// 예측 값은 한 줄만 취급
				Tuple tuple = new Tuple();

				tuple.put("FILE_NM", fileName);

				for (Map.Entry<String, Object> entry1 : row.entrySet()) {
					String columnName = entry1.getKey();
					Object value = entry1.getValue();

					tuple.put(columnName, value);
				}

				logpressoData.add(tuple);
			}
		}
		return logpressoData;
	}

	private void _insertPredictionState(Map<String, Object> prediction) {
		logger.info("... saving validation data of `QTransferPredictBatch` has started");

		final List<Tuple> resultList = new ArrayList<>();

		String state = prediction.get("STATE") == null ? null : prediction.get("STATE").toString();
		String currentState;

		if (state == null) {
			logger.error("... value of `STATE` is null, so process exit");

			return;
		}

		Object occurrencePercentageObject = prediction.get("STATE_PER") == null ? null : prediction.get("STATE_PER");
		double occurrencePercentage;

		if (occurrencePercentageObject == null) {
			logger.error("... value of `STATE_PER` is null, so process exit");

			return;
		} else {
			try {
				occurrencePercentage = Double.parseDouble(occurrencePercentageObject.toString());
			} catch (NumberFormatException e) {
				logger.error("... an exception occurred [value={}]", occurrencePercentageObject, e);

				return;
			}
		}

		switch (state) {
			case "NORMAL":
				currentState = "정상";
				break;
			case "CAUTION":
				currentState = "주의";
				break;
			case "CRITICAL":
				currentState = "심각";
				break;
			default:
				currentState = state;
		}
// ---------------------------------------------------------------------------------------------------------------------
		Map<String, Object> data = new HashMap<>();

		data.put("OPER_ACT_CTN", currentState);
		data.put("VAL", occurrencePercentage);
		data.put("TYP", "STATE");
		data.put("JOB_STAT", "");
		data.put("JOB_TYP", "");
		data.put("DUE_GBN_CD", "");
		data.put("ADMIN_USER_ID", "");
		data.put("DEPT_NM", "");
		data.put("JOB_SYS_ID", "");

		try {
			DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMddHHmm");
			String eventDateTimeString = this.eventDataTime.format(formatter);

			data.put("EVENT_DT", eventDateTimeString);
			data.put("DUE_GBN_CD", eventDateTimeString);
// ---------------------------------------------------------------------------------------------------------------------
			final Tuple predictMapSet = new Tuple();

			XmlUtil.mapToTplConvert(data, predictMapSet);

			resultList.add(predictMapSet);

			QTransferDashBoardItemBatch.insertLogpressoData(resultList);
		} catch (Exception e) {
			logger.error("", e);
		}
	}

	/**
	 * pivot 데이터를 구성
	 * @param prediction 예측 값
	 * @apiNote 실측 데이터와 예측 데이터는 기본이 되는 데이터는 서로 다른 시간 범위를 취할 수도 있다. 예를 들어 실측 데이터는 100분 분량의 데이터를 통해 총합 등의 계산을 진행하고 예측 데이터는 280분 분량의 데이터를 통해 데이터를 예측한다.
	 */
	private List<Map<String, Object>> _getPivotData(double prediction) {
		List<Map<String, Object>> result = new ArrayList<>();
		List<Map<String, Object>> alarmList, queryData;
		final String QUERY_ID = "qTransferGroupData";

		try {
			queryData = XmlUtil.selectLogpressoQuery2(QUERY_ID);
		} catch (Exception e) {
			logger.error("... an exception occurred with query, so process exit [query id={}]", QUERY_ID, e);

			return new ArrayList<>();
		}

		if (queryData == null || queryData.isEmpty()) {
			logger.error("... selected query data is null or empty, so process exit [query id={}]", QUERY_ID);

			return new ArrayList<>();
		}

		Map<String, Object> latestRow = queryData.get(0);

		try {
			for (Map.Entry<String, Object> entry : latestRow.entrySet()) {
				String idcCol = entry.getKey();

				if (
						idcCol.equalsIgnoreCase("CURRTIME")
								|| idcCol.equalsIgnoreCase("TIME")
								|| idcCol.equalsIgnoreCase("UID")
				) {
					continue;
				}

				Object idcVal = entry.getValue();
				double average = _calculateAverage(queryData, idcCol);

				Map<String, Object> newRow = new HashMap<>();

				newRow.put("TIME", latestRow.get("TIME"));
				newRow.put("IDCCOL", idcCol);
				newRow.put("IDCVAL", idcVal);
				newRow.put("AVERAGE", average);
// ---------------------------------------------------------------------------------------------------------------------
				// 사분위 수
				double iqrLower = _calculateIQR_Lower(queryData, idcCol);
				double iqrUpper = _calculateIQR_Upper(queryData, idcCol);
				String iqrJudge = (
						Double.parseDouble(idcVal.toString()) < iqrLower
								|| Double.parseDouble(idcVal.toString()) > iqrUpper
				) ? "T" : "F";

				newRow.put("IQR_Q1", _calculateIQR_Q1(queryData, idcCol));
				newRow.put("IQR_Q2", _calculateIQR_Q3(queryData, idcCol));
				newRow.put("IQR_LOWER", iqrLower);
				newRow.put("IQR_UPPER", iqrUpper);
				newRow.put("IQR_JUDGE", iqrJudge);
// ---------------------------------------------------------------------------------------------------------------------
				// 표준 편차
				double standardDeviation = _calculateStandardDeviation(queryData, idcCol);
				double sdLower = average - 3 * standardDeviation;
				double sdUpper = average + 3 * standardDeviation;
				String sdJudge = (
						Double.parseDouble(idcVal.toString()) < sdLower
								|| Double.parseDouble(idcVal.toString()) > sdUpper
				) ? "T" : "F";

				newRow.put("STANDARDDEVIATION", standardDeviation);
				newRow.put("SD_LOWER", sdLower);
				newRow.put("SD_UPPER", sdUpper);
				newRow.put("SD_JUDGE", sdJudge);
// ---------------------------------------------------------------------------------------------------------------------
				result.add(newRow);
			}

			//alarm 기능 추가
			alarmList = this._alarmValid(result, prediction);

			if (!alarmList.isEmpty()) {
				result.addAll(alarmList);
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		return result;
	}

	private List<Map<String, Object>> _alarmValid(List<Map<String, Object>> originValue, double prediction) {
		List<Map<String, Object>> result = new ArrayList<>();
		List<Map<String, Object>> queryResForVhlRate;
		List<Map<String, Object>> queryResFor10m;
		List<Map<String, Object>> queryResFor24h;
		List<Map<String, Object>> queryResCompletedJobCnt;
		List<Map<String, Object>> queryResCurrJobCntFor10m;
		List<Map<String, Object>> queryResCurrJobCntFor24h;
		List<Map<String, Object>> queryResCnvPortDownRate;
		List<Map<String, Object>> queryResAltJobCnt;
		List<Map<String, Object>> queryResAltJobMachineRate;

		//	알람 발생상황 체크
		//	1. M14A 반송큐 예측값이 지정개수(1700)를 초과한 경우
		double reqLimit = this._findValueByCode("QTRANSFER_LIMIT", 1700);

		//	증가 값 기준
		double increaseRate = this._findValueByCode("QTRANSFER_INCREASE_RATE", 10);

		//	VHL 가동률 기준
		double vhlRunRateLimit = this._findValueByCode("VHL_RATE_LIMIT", 95);
		double cnvPortDownRateLimit = this._findValueByCode("QTRANSFER_CNV_PORT_DOWN_RATE", 10);

		//M14 - M10 반송 LFT PORT DOWN RATE 기준
		double m10PortDownRate = this._findValueByCode("QTRANSFER_M14TOM10_PORT_DOWN_RATE", 25);

		//M14A - M14B LFT PORT DOWN RATE 기준
		double m14LftDownRate = this._findValueByCode("QTRANSFER_M14LFT_PORT_DOWN_RATE", 10);

		//ALT 반송 중복 발생 MACHINE 기준치
		double altJobLimit = this._findValueByCode("QTRANSFER_ALT_JOB_LIMIT", 50);

		//ALT 반송 중복 발생 MACHINE 기준치
		double altJobMachineRate = this._findValueByCode("QTRANSFER_ALT_JOB_MACHINE_RATE", 50);

		String currentTotalCnt = this._collectIdcValue(originValue, "TOTALCNT");

		//M14A 반송큐 예측 값
		int m14ATotalCntValue = (int) prediction;

		if (m14ATotalCntValue <= reqLimit) {
			// 임계치(1700)를 초과하지 않은 경우
			return new ArrayList<>();
		}

		try {
			// # 알람 발생 상황 - M14A 반송큐 예측값이 지정된 개수(기본 1700) 를 초과
			// 알람 #1 - VHL 가동률 95% 이상 & 10분간 MES 반송 큐 (MHSMCS_TRANSPORT_JOB_SCHEDULE_REQ) 수가 평시보다(전일기준 24시간) 10% 증가시 =========== START
			// # 가동률 조회
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "vhlRunRate");
			queryResForVhlRate = LogpressoAPI.responseResult(strQuery);

			String ohtRunRate = queryResForVhlRate.stream()
					.filter(map -> "FOUP".equals(map.get("CARRIERTYPE")))
					.map(map -> map.get("VHLOPERRATE").toString())
					.collect(Collectors.joining(", "));

			double ohtRunRateValue = Double.parseDouble(ohtRunRate.split(", ")[0]);
			boolean vhlRateFlag = ohtRunRateValue >= vhlRunRateLimit;

			String strQuery2 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "mesOHTQCntAlarmValid");
			strQuery2 = strQuery2.replace("duration=1m","duration=24h");
			queryResFor24h =  LogpressoAPI.responseResult(strQuery2);

			strQuery2 = strQuery2.replace("duration=24h","duration=10m");
			queryResFor10m =  LogpressoAPI.responseResult(strQuery2);

			//#10분 completed job 수
			String strQuery3 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "completedTsJobCountPerMin");
			queryResCompletedJobCnt = LogpressoAPI.responseResult(strQuery3);

			String queryResCompletedJobCntVal = queryResCompletedJobCnt.get(0).get("MINPER_CNT").toString();

			int queryResFor24hVal = Integer.parseInt(queryResFor24h.get(0).get("MESSAGE_COUNT").toString());
			int queryResFor10mVal = Integer.parseInt(queryResFor10m.get(0).get("MESSAGE_COUNT").toString());

			double percentageIncrease = ((double) (queryResFor10mVal - queryResFor24hVal) / queryResFor24hVal) * 100;

			boolean mesQTransFlag = percentageIncrease > increaseRate;
			//#알람1-VHL 가동률 95% 이상 & 10분간 MES 반송 큐 (MHSMCS_TRANSPORT_JOB_SCHEDULE_REQ) 수가 평시보다(전일기준 24시간) 10% 증가시 =========== END

			//#알람2-10분간 CNV 반송(M14A <-> M16) 개수가 평시보다(전일 24시간 기준) 10% 증가시
			// & CNV PORT(BRIDGE DETAIL | M14AAIㆍAO , M16AAIㆍAO) DOWN RATE 가 10% 미만인 경우 ============================================ START
			//10분 데이터 조회 [M14AM16SUM / M16M14A / M14AM16]
			String strQuery4 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "transferCountPerMin");
			queryResCurrJobCntFor10m = LogpressoAPI.responseResult(strQuery4);

			//24시간 데이터 조회 [M14AM16SUM / M16M14A / M14AM16]
			strQuery4 = strQuery4.replace("duration=10m", "duration=24h");
			queryResCurrJobCntFor24h = LogpressoAPI.responseResult(strQuery4);

			//#CNV PORT DOWN RATE
			String strQuery5 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "bridgeDetailCnvPortDownRate");
			queryResCnvPortDownRate = LogpressoAPI.responseResult(strQuery5);

			String m14aTotalCnt10m = this._collectIdcValue(queryResCurrJobCntFor10m, "M14AM16SUM");
			String m14aTotalCnt24h = this._collectIdcValue(queryResCurrJobCntFor24h, "M14AM16SUM");

			String m14aToM16a10m = this._collectIdcValue(queryResCurrJobCntFor10m, "M14AM16");
			String m14aToM16a24h = this._collectIdcValue(queryResCurrJobCntFor24h, "M14AM16");

			String m16aToM14a10m = this._collectIdcValue(queryResCurrJobCntFor10m, "M16M14A");
			String m16aToM14a24h = this._collectIdcValue(queryResCurrJobCntFor24h, "M16M14A");

			String m14CnvPortDownRate = queryResCnvPortDownRate.get(0).get("PORT_DOWN_RATE").toString();

			int m14aTotalCnt10mVal = Integer.parseInt(m14aTotalCnt10m.split(", ")[0]);
			int m14aTotalCnt24hVal = Integer.parseInt(m14aTotalCnt24h.split(", ")[0]);

			double percentageIncrease2 =  ((double)(m14aTotalCnt10mVal - m14aTotalCnt24hVal)/m14aTotalCnt24hVal) * 100;
			boolean m14CnvCntFlag = percentageIncrease2 > increaseRate;

			double m14CnvPortDownRateVal =  Double.parseDouble(m14CnvPortDownRate); // 현재 port down rate

			// port down 기준치
			boolean m14CnvPortDownFlag = m14CnvPortDownRateVal < cnvPortDownRateLimit;

			//#알람2-10분간 CNV 반송(M14A <-> M16) 개수가 평시보다(전일 24시간 기준) 10% 증가시
			// & CNV PORT(BRIDGE DETAIL | M14AAIㆍAO , M16AAIㆍAO) DOWN RATE 가 10% 미만인 경우 ============================================ END

			//#알람3-10분간 M14-M10A LFT 반송(M14A <-> M10A) 개수가 평시보다(전일 24시간 기준) 10% 증가시
			// & LFT 장비 혹은 AI/AO PORT DOWN 이 25% 미만 인경우 ================================================================================= START
			String m10aTotalCnt10m = this._collectIdcValue(queryResCurrJobCntFor10m, "M14AM10ASUM");
			String m10aTotalCnt24h = this._collectIdcValue(queryResCurrJobCntFor24h, "M14AM10ASUM");

			String m14aToM10a10m = this._collectIdcValue(queryResCurrJobCntFor10m, "M14AM10A");
			String m14aToM10a24h = this._collectIdcValue(queryResCurrJobCntFor24h, "M14AM10A");

			String m10aToM14a10m = this._collectIdcValue(queryResCurrJobCntFor10m, "M10AM14A");
			String m10aToM14a24h = this._collectIdcValue(queryResCurrJobCntFor24h, "M10AM14A");

			//PORT DOWN RATE 표기 필요
			//M14<->M10 4ABL33 LFT 장비 PORT DOWN RATE (25% 미만)
			String m14bToM10DownRate = "";
			String m14aToM14bDownRate = "";

			try {
				for (String fab : new String[] { "M14B","M14A"}) {
					String xmlPath;
					String dynamicQuery;
					String xmlPath2;
					String dynamicQuery2;

					switch (fab) {
						case "M14A":
							var factory = QueryExecutorFactory.getQueryExecutor(fab);
							xmlPath = FilePathUtil.factoryPath(factory.getConnectionId());
							dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_M14TOM10LFT_DOWN_RATE");
							List<Map<String, Object>> downRateList = factory.selectList(dynamicQuery);

							if(!downRateList.isEmpty()) {
								m14bToM10DownRate = downRateList.get(0).get("PORT_DOWN_RATE") == null ? "" : downRateList.get(0).get("PORT_DOWN_RATE").toString();
							}

							factory.close();
							break;
						case "M14B":
							var factory2 = QueryExecutorFactory.getQueryExecutor(fab);
							xmlPath2 = FilePathUtil.factoryPath(factory2.getConnectionId());
							dynamicQuery2 = XmlUtil.loadQuery(xmlPath2 , "SELECT_M14LFT_DOWN_RATE");
							List<Map<String, Object>> downRateList2 = factory2.selectList(dynamicQuery2);

							if(!downRateList2.isEmpty()) {
								m14aToM14bDownRate = downRateList2.get(0).get("PORT_DOWN_RATE") == null ? "" : downRateList2.get(0).get("PORT_DOWN_RATE").toString();
							}
							factory2.close();
							break;

						default:
					}
				}
			} catch (Exception e) {
				logger.error("", e);
			}

			//사용 가능 포틋 수
			String m14ToM10InserviceRate = String.valueOf((100.0 - Double.parseDouble(m14bToM10DownRate)));

			int m10aTotalCnt10mVal = Integer.parseInt(m10aTotalCnt10m.split(", ")[0]);
			int m10aTotalCnt24hVal = Integer.parseInt(m10aTotalCnt24h.split(", ")[0]);
			double percentageIncrease3 = ((double) (m10aTotalCnt10mVal - m10aTotalCnt24hVal) / m10aTotalCnt24hVal) * 100;

			//10% 이상인 경우  true
			boolean m14ToM10Flag = percentageIncrease3 > increaseRate;

			//25% 미만인 경우 true
			boolean m10DownFlag = Double.parseDouble(m14bToM10DownRate) <  m10PortDownRate;

			//#알람3-10분간 M14-M10A LFT 반송(M14A <-> M10A) 개수가 평시보다(전일 24시간 기준) 10% 증가시
			// & LFT 장비 혹은 AI/AO PORT DOWN 이 25% 미만 인경우 ================================================================================= END

			//#알람4-10분간 M14-M14B LFT 반송(M14A <-> M14B) 개수가 평시보다(전일 24시간 기준) 10% 증가시
			// & LFT 장비 혹은 AI/AO PORT DOWN 이 10% 미만 인경우 ================================================================================= START

			String m14aToM14bTotalCnt10m = this._collectIdcValue(queryResCurrJobCntFor10m, "M14AM14BSUM");
			String m14aToM14bTotalCnt24h = this._collectIdcValue(queryResCurrJobCntFor24h, "M14AM14BSUM");

			String m14aToM14b10m = this._collectIdcValue(queryResCurrJobCntFor10m, "M14AM14B");
			String m14aToM14b24h = this._collectIdcValue(queryResCurrJobCntFor24h, "M14AM14B");

			String m14bTom14a10m = this._collectIdcValue(queryResCurrJobCntFor10m, "M14BM14A");
			String m14bTom14a24h = this._collectIdcValue(queryResCurrJobCntFor24h, "M14BM14A");

			String m14aToM14bInserviceRate = String.valueOf((100.0 - Double.parseDouble(m14aToM14bDownRate)));

			int m14aToM14bTotalCnt10mVal = Integer.parseInt(m14aToM14bTotalCnt10m.split(", ")[0]);
			int m14aToM14bTotalCnt24hVal = Integer.parseInt(m14aToM14bTotalCnt24h.split(", ")[0]);
			double percentageIncrease4
					= ((double) (m14aToM14bTotalCnt10mVal - m14aToM14bTotalCnt24hVal) / m14aToM14bTotalCnt24hVal) * 100;

			// 10% 이상인 경우 true
			boolean m14aToM14bFlag = percentageIncrease4 > increaseRate;

			// 10% 미만인 경우 true
			boolean m14aToM14bDownFlag = Double.parseDouble(m14aToM14bDownRate) <  m14LftDownRate;

			// #알람4-10분간 M14-M14B LFT 반송(M14A <-> M14B) 개수가 평시보다(전일 24시간 기준) 10% 증가시
			// & LFT 장비 혹은 AI/AO PORT DOWN 이 10% 미만 인경우
			// ================================================================================= END

			// #알람5-JOB STATE 가 ERROR OR ALT 인 이력의 전일 24시간 대비 최근 1시간 평균이 50% 이상 증가시 & 첫번째 조건의 JOB중 동일 장비명이 50% 이상 발생하는 경우 == START
			String strQuery6 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "qtransferAltJobCnt");

			LocalDateTime yesterday = this.eventDataTime.minusDays(1);
			String todayStr 	= this.eventDataTime.format(DateTimeFormatter.ofPattern("yyyyMMdd"));
			String yesterdayStr	= yesterday.format(DateTimeFormatter.ofPattern("yyyyMMdd"));

			strQuery6 = strQuery6.replace("START_DT", yesterdayStr);
			strQuery6 = strQuery6.replace("END_DT", todayStr);

			queryResAltJobCnt 				= LogpressoAPI.responseResult(strQuery6);
			int altJobIncreaseRate
					= Integer.parseInt(queryResAltJobCnt.get(0).get("INCREASE_RATE").toString());

			boolean altJobLimitFlag 		= altJobIncreaseRate > altJobLimit;
			boolean altJobMachineStateFlag 	= false;

			//상태 기준 반송큐 수 메세지 동적생성
			StringBuilder stateRateMsg		= new StringBuilder();

			//장비 기준 반송큐 수 메세지 동적생성
			StringBuilder machineRateMsg 	= new StringBuilder();

			//상태별 장비 메세지 매핑 동적생성
			String stateMappingMachine 		= "";
			String altJobStateList 			= "";
			String altJobMachineList 		= "";

			//50% 이상 증가 시 TRUE -> 알람발생 상황
			if (altJobLimitFlag) {
				//이상 발생 1시간 이내에 동일 장비 50% 이상 발생 체크
				String strQuery7 			= XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "altJobMachineRate");
				queryResAltJobMachineRate 	= LogpressoAPI.responseResult(strQuery7);

				//이상 반송 전체 장비 중 동일 장비 발생 비율이 50% 이상인 데이터만 조회
				List<Map<String, Object>> filteredData = queryResAltJobMachineRate.stream()
						.filter(map -> (Double) map.get("RATE_DT") >= altJobMachineRate)
						.collect(Collectors.toList());

				if (!filteredData.isEmpty()) {
					//동일 장비 발생 비율 50%이상인 MACHINENAME LIST
					Set<String> filteredMachineNames = queryResAltJobMachineRate.stream()
							.filter(map -> (Double) map.get("RATE_DT") >= altJobMachineRate)
							.map(map -> (String) map.get("MACHINENAME"))
							.collect(Collectors.toSet());

					//동일 장비 발생 비율50%이상인 STATE LIST
					Set<String> filteredStateNames = queryResAltJobMachineRate.stream()
							.filter(map -> (Double) map.get("RATE_DT") >= altJobMachineRate)
							.map(map -> (String) map.get("STATE"))
							.collect(Collectors.toSet());


					//장비 기준 1시간 반송 수량 <- 50% 이상 동일 장비 데이터로 조회
					List<Map<String,Object>> machineCntSum = queryResAltJobMachineRate.stream()
							.collect(Collectors.groupingBy(
									map -> (String) map.get("MACHINENAME"),
									Collectors.summingInt(map -> Integer.parseInt(map.get("CNT").toString()))
							))
							.entrySet().stream()
							.filter(entry -> filteredMachineNames.contains(entry.getKey()))
							.map(entry -> {
								Map<String, Object> res = new HashMap<>();
								res.put("MACHINENAME", entry.getKey());
								res.put("CNT", entry.getValue());
								return res;
							})
							.collect(Collectors.toList());


					//장비 기준 1시간 반송 수량 <- 50% 이상 동일 상태 데이터로 조회 7
					List<Map<String,Object>> stateCntSum = queryResAltJobMachineRate.stream()
							.collect(Collectors.groupingBy(
									map -> (String) map.get("STATE"),
									Collectors.summingInt(map -> Integer.parseInt(map.get("CNT").toString()))
							))
							.entrySet().stream()
							.filter(entry -> filteredStateNames.contains(entry.getKey()))
							.map(entry -> {
								Map<String, Object> res = new HashMap<>();
								res.put("STATE", entry.getKey());
								res.put("CNT", entry.getValue());
								return res;
							})
							.collect(Collectors.toList());


					//STATE / MACHINE 두개로 그룹 STATE[MACHINENAME] 메세지 생성을 위함
					List<Map<String, Object>> stateAndMachineSum = queryResAltJobMachineRate.stream()
							.collect(Collectors.groupingBy(
									map -> Map.of("STATE", map.get("STATE"), "MACHINENAME", map.get("MACHINENAME")),
									Collectors.summingInt(map -> Integer.parseInt(map.get("CNT").toString()))
							))
							.entrySet().stream()
							.filter(entry -> filteredStateNames.contains((String) entry.getKey().get("STATE")))
							.filter(entry -> filteredMachineNames.contains((String) entry.getKey().get("MACHINENAME")))
							.map(entry -> {
								Map<String, Object> res = new HashMap<>();
								res.put("STATE", entry.getKey().get("STATE"));
								res.put("MACHINENAME", entry.getKey().get("MACHINENAME"));
								res.put("CNT", entry.getValue());
								return res;
							})
							.collect(Collectors.toList());

					System.out.println(stateAndMachineSum);

					Map<String, List<String>> stateMachineMap = stateAndMachineSum.stream()
							.collect(Collectors.groupingBy(
									map -> (String) map.get("STATE"),
									Collectors.mapping(map -> (String) map.get("MACHINENAME"), Collectors.toList())
							));

					stateMappingMachine = stateMachineMap.entrySet().stream()
							.map(entry -> entry.getKey() + "[" + String.join(",", entry.getValue()) + "]")
							.collect(Collectors.joining(","));

					String searchMachineVal = machineCntSum.stream()
							.map(map -> (String) map.get("MACHINENAME"))
							.collect(Collectors.joining("\",\"", "\"", "\""));
					altJobMachineList = searchMachineVal;
					String searchStateeVal = stateCntSum.stream()
							.map(map -> (String) map.get("STATE"))
							.collect(Collectors.joining("\",\"", "\"", "\""));

					altJobStateList = searchStateeVal;

					//전일 24시간 기준, 장비별 시간당 평균 반송수량
					String strQuery7_2 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "altJobMachineRate24h");

					strQuery7_2 = strQuery7_2.replace("START_DT", yesterdayStr);
					strQuery7_2 = strQuery7_2.replace("END_DT", todayStr);
					strQuery7_2 = strQuery7_2.replace("MACHINELIST", searchMachineVal);

					List<Map<String,Object>> queryResAltJobMachineRateBy24 = LogpressoAPI.responseResult(strQuery7_2);
					machineCntSum.forEach(machine -> machine.put("DAY_CNT", queryResAltJobMachineRateBy24.stream()
							.filter(rate -> rate.get("MACHINENAME").equals(machine.get("MACHINENAME")))
							.findFirst()
							.map(rate -> rate.get("DAY_CNT"))
							.orElse(null)));

					//전일 24시간 기준, 상태별 시간당 평균 반송수량
					String strQuery7_3 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "qtransferAltJobCnt24h");

					strQuery7_3 = strQuery7_3.replace("START_DT", yesterdayStr);
					strQuery7_3 = strQuery7_3.replace("END_DT", todayStr);
					strQuery7_3 = strQuery7_3.replace("STATELIST", searchStateeVal);

					List<Map<String,Object>> queryResAltJobStateRateBy24 = LogpressoAPI.responseResult(strQuery7_3);
					stateCntSum.forEach(state -> state.put("AVG_VAL", queryResAltJobStateRateBy24.stream()
							.filter(rate -> rate.get("STATE").equals(state.get("STATE")))
							.findFirst()
							.map(rate -> rate.get("AVG_VAL"))
							.orElse(null)));

					int msgIdx = 2;

					for(Map<String, Object> map : stateCntSum) {
						stateRateMsg.append(msgIdx)
								.append(". 1시간 ")
								.append(map.get("STATE").toString())
								.append(" 상태 반송큐 수: ")
								.append(map.get("CNT").toString())
								.append("개 (전일 평균 ")
								.append(map.get("AVG_VAL").toString())
								.append("개)\\n \n");
						msgIdx += 1;
					}
					for(Map<String, Object> map : machineCntSum) {
						machineRateMsg.append(msgIdx)
								.append(". 1시간 ")
								.append(map.get("MACHINENAME").toString())
								.append(" 장비 반송큐 수: ")
								.append(map.get("CNT").toString())
								.append("개 (전일 평균 ")
								.append(map.get("DAY_CNT").toString())
								.append("개)\\n \n");
						msgIdx += 1;
					}
				}

				altJobMachineStateFlag = true;
			}

			//#알람5-JOB STATE 가 ERROR OR ALT 인 이력의 전일 24시간 대비 최근 1시간 평균이 50% 이상 증가시 & 첫번째 조건의 JOB중 동일 장비명이 50% 이상 발생하는 경우 == END
//----------------------------------------------------------------------------------------------------------------------
			if (vhlRateFlag && mesQTransFlag) {
				// 알람 #1
				Map<String, Object> alarmMap = this._buildAlarm1(
						m14ATotalCntValue,
						reqLimit,
						ohtRunRate,
						queryResFor10mVal,
						queryResFor24hVal,
						currentTotalCnt,
						queryResCompletedJobCntVal
				);

				result.add(alarmMap);
			}

			if (m14CnvCntFlag && m14CnvPortDownFlag) {
				// 알람 #2
				Map<String, Object> alarmMap = this._buildAlarm2(
						m14ATotalCntValue,
						reqLimit,
						m14aToM16a10m,
						m14aToM16a24h,
						m16aToM14a10m,
						m16aToM14a24h,
						currentTotalCnt,
						ohtRunRate
				);

				result.add(alarmMap);
			}

			if (m14ToM10Flag && m10DownFlag) {
				//알람 #3
				Map<String, Object> alarmRow = new HashMap<>();

				//필수 컬럼
				alarmRow.put("TIME", originValue.get(originValue.size()-1).get("TIME"));
				alarmRow.put("IDCCOL", "QTRANSFER_ALARM3");
				alarmRow.put("IDCVAL", "0");
				alarmRow.put("AVERAGE", "0");

				alarmRow.put("SD_LOWER", "0");
				alarmRow.put("SD_UPPER", "0");
				alarmRow.put("SD_JUDGE", "F");
				alarmRow.put("STANDARDDEVIATION", "0");

				alarmRow.put("IQR_Q1", "0");
				alarmRow.put("IQR_Q2", "0");
				alarmRow.put("IQR_LOWER", "0");
				alarmRow.put("IQR_UPPER", "0");
				alarmRow.put("IQR_JUDGE", "0");

				//알람 컬럼
				alarmRow.put("ALARM_CD", "");
				alarmRow.put("ALARM_CMT", "- M14A 반송 큐 개수 예측치가 임계치를 초과 했습니다."); //BOLD 체
				alarmRow.put("ALARM_DESC", "M10A ↔ M14A FAB간 반송 큐 개수 다량 증가"); // 알람영

				String storageUtil = "";

				try {
					var factory 		= QueryExecutorFactory.getQueryExecutor("M16A");
					String xmlPath 		= FilePathUtil.factoryPath(factory.getConnectionId());
					String dynamicQuery	= XmlUtil.loadQuery(xmlPath , "SELECT_M16A_STORAGE_UTIL");
					List<Map<String, Object>> m16a_detailList = factory.selectList(dynamicQuery);
					storageUtil 		= m16a_detailList.get(0).get("CURR_VAL").toString();

					factory.close();
				} catch (Exception e) {
					logger.error("",e);
				}

				//예측 범위 - ##나중에 variable에 구현할 수 있도록
				String predictOutput = "10";
				String alarmText = XmlUtil.getMessage("QTRANSFER_M14TOM10_LFT"
						,predictOutput
						,m14ATotalCntValue
						,reqLimit

						,m10aToM14a10m
						,m10aToM14a24h
						,m14aToM10a10m
						,m14aToM10a24h

						,m14bToM10DownRate

						,currentTotalCnt
						,storageUtil
						,ohtRunRate
						,m14ToM10InserviceRate
				);

				System.out.println(alarmText);

				alarmRow.put("ALARM_MSG_CTN", alarmText); // 알람내용
				alarmRow.put("ALARM_YN", "Y");

				result.add(alarmRow);
			}

			if (m14aToM14bFlag && m14aToM14bDownFlag) {
				// 알람 #4
				Map<String, Object> alarmRow = new HashMap<>();

				//필수 컬럼
				alarmRow.put("TIME", originValue.get(originValue.size()-1).get("TIME"));
				alarmRow.put("IDCCOL", "QTRANSFER_ALARM4");
				alarmRow.put("IDCVAL", "0");
				alarmRow.put("AVERAGE", "0");

				alarmRow.put("SD_LOWER", "0");
				alarmRow.put("SD_UPPER", "0");
				alarmRow.put("SD_JUDGE", "F");
				alarmRow.put("STANDARDDEVIATION", "0");

				alarmRow.put("IQR_Q1", "0");
				alarmRow.put("IQR_Q2", "0");
				alarmRow.put("IQR_LOWER", "0");
				alarmRow.put("IQR_UPPER", "0");
				alarmRow.put("IQR_JUDGE", "0");

				//알람 컬럼
				alarmRow.put("ALARM_CD", "");
				alarmRow.put("ALARM_CMT", "- M14A 반송 큐 개수 예측치가 임계치를 초과 했습니다."); //BOLD 체
				alarmRow.put("ALARM_DESC", "M14A ↔ M14B FAB간 반송 큐 개수 다량 증가"); // 알람영

				String storageUtil = "";

				try {
					var factory 		= QueryExecutorFactory.getQueryExecutor("M16A");
					String xmlPath 		= FilePathUtil.factoryPath(factory.getConnectionId());
					String dynamicQuery	= XmlUtil.loadQuery(xmlPath , "SELECT_M16A_STORAGE_UTIL");
					List<Map<String, Object>> m16a_detailList = factory.selectList(dynamicQuery);
					storageUtil 		= m16a_detailList.get(0).get("CURR_VAL").toString();

					factory.close();
				} catch (Exception e) {
					logger.error("", e);
				}

				//예측 범위 - ##나중에 variable에 구현할 수 있도록
				String predictOutput = "10";
				String alarmText = XmlUtil.getMessage("QTRANSFER_M14ATOM14B_LFT"
						,predictOutput
						,m14ATotalCntValue
						,reqLimit

						,m14aToM14b10m
						,m14aToM14b24h
						,m14bTom14a10m
						,m14bTom14a24h

						,m14aToM14bDownRate

						,currentTotalCnt
						,storageUtil
						,ohtRunRate
						,m14aToM14bInserviceRate
				);

				alarmRow.put("ALARM_MSG_CTN", alarmText); // 알람내용
				alarmRow.put("ALARM_YN", "Y");

				result.add(alarmRow);
			}

			if(altJobMachineStateFlag) {
				Map<String, Object> alarmRow = new HashMap<>();

				//필수 컬럼
				alarmRow.put("TIME", originValue.get(originValue.size()-1).get("TIME"));
				alarmRow.put("IDCCOL", "QTRANSFER_ALARM5");
				alarmRow.put("IDCVAL", "0");
				alarmRow.put("AVERAGE", "0");

				alarmRow.put("SD_LOWER", "0");
				alarmRow.put("SD_UPPER", "0");
				alarmRow.put("SD_JUDGE", "F");
				alarmRow.put("STANDARDDEVIATION", "0");

				alarmRow.put("IQR_Q1", "0");
				alarmRow.put("IQR_Q2", "0");
				alarmRow.put("IQR_LOWER", "0");
				alarmRow.put("IQR_UPPER", "0");
				alarmRow.put("IQR_JUDGE", "0");


				String predictOutput = "10";
				String alarmText = XmlUtil.getMessage("QTRANSFER_ALT_JOB"
						,predictOutput
						,m14ATotalCntValue
						,reqLimit
						, stateRateMsg.toString()
						, machineRateMsg.toString()
						,currentTotalCnt
						,stateMappingMachine
						,ohtRunRate
						,altJobStateList
						,altJobMachineList
				);

				//알람 컬럼
				alarmRow.put("ALARM_CD", "");
				alarmRow.put("ALARM_CMT", "- M14A 반송 큐 개수 예측치가 임계치를 초과 했습니다."); //BOLD 체
				alarmRow.put("ALARM_DESC", "ERROR 혹은 ALT인 반송큐 개수 다량 증가"); // 알람영
				alarmRow.put("ALARM_MSG_CTN", alarmText); // 알람내용
				alarmRow.put("ALARM_YN", "Y");

				result.add(alarmRow);
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		return result;
	}

	private static double _calculateAverage(List<Map<String, Object>> data, String column) {
		double sum 	= 0.0;
		int count 	= 0;

		for (Map<String, Object> row : data) {
			Object value = row.get(column);

			if (value instanceof Number) {
				sum += ((Number) value).doubleValue();
				count++;
			}
		}

		return count > 0 ? sum / count : 0.0;
	}

	// IQR_Q1 계산
	private double _calculateIQR_Q1(List<Map<String, Object>> data, String column) {
		List<Double> values = _extractColumnValues(data, column);

		if (values.isEmpty()) return 0.0;

		Collections.sort(values);

		return _getQuantile(values, 0.25);
	}

	//3분위 수
	private double _calculateIQR_Q3(List<Map<String, Object>> data, String column) {
		List<Double> values = _extractColumnValues(data, column);

		if (values.isEmpty()) return 0.0;

		Collections.sort(values);

		return _getQuantile(values, 0.75);
	}

	// IQR_Lower 계산 (Q1 - 1.5 * IQR)
	private double _calculateIQR_Lower(List<Map<String, Object>> data, String column) {
		double Q1 = _calculateIQR_Q1(data, column);
		double Q3 = _calculateIQR_Q3(data, column);
		double IQR = Q3 - Q1;

		return Q1 - 1.5 * IQR;
	}

	// IQR_Upper 계산 (Q3 + 1.5 * IQR)
	private double _calculateIQR_Upper(List<Map<String, Object>> data, String column) {
		double Q1 	= _calculateIQR_Q1(data, column);
		double Q3 	= _calculateIQR_Q3(data, column);
		double IQR 	= Q3 - Q1;

		return Q3 + 1.5 * IQR;
	}

	private double _getQuantile(List<Double> sortedValues, double quantile) {
		int n = sortedValues.size();

		if (n == 0) return 0.0;

		double index = (quantile * (n - 1));  //인덱스 계산

		return sortedValues.get((int)Math.floor(index));
	}

	// 표준편차 계산 메서드
	private double _calculateStandardDeviation(List<Map<String, Object>> data, String column) {
		double mean = _calculateAverage(data, column);
		double sumSquaredDifferences = 0.0;

		for (Map<String, Object> row : data) {
			double difference = Double.parseDouble(row.get(column).toString()) - mean;

			sumSquaredDifferences += difference * difference;
		}

		return Math.sqrt(sumSquaredDifferences / data.size());
	}

	private List<Double> _extractColumnValues(List<Map<String, Object>> data, String column) {
		List<Double> values = new ArrayList<>();

		for (Map<String, Object> row : data) {
			Object value = row.get(column);

			if (value instanceof Number) {
				values.add(((Number) value).doubleValue());
			}
		}

		return values;
	}
//======================================================================================================================
	// 2025-12-03 신규 추가된 알람에 대한 데이터 구성 후 점검
	// 해당 기능에는 반송 큐의 예측 값없이 M14 의 반송 큐로만 계산
	private List<Map<String, Object>> _buildTransportAlarm() {
		List<Map<String, Object>> result 		= new ArrayList<>();
		ConcurrentMap<String, Double> mapping 	= new ConcurrentHashMap<>();
		final String IDC_HIS_QUERY_ID 			= "SELECT_AWS_IDC_HISTORY";

		try {
			List<Map<String, Object>> queryData = XmlUtil.selectLogpressoQuery(IDC_HIS_QUERY_ID);

			if (queryData.isEmpty()) {
				String exceptionMessage = "... an exception occurred with query, and process is exist [id=" + IDC_HIS_QUERY_ID + "]";

				throw new Exception(exceptionMessage);
			} else {
				for (Map.Entry<String, Object> entry : queryData.get(0).entrySet()) {
					String fieldName 		= entry.getKey();
					Object averageObject 	= entry.getValue();

					if (averageObject == null || averageObject.toString().isEmpty()) {
						mapping.put(fieldName, 0.0);	// M14.QUE.ALL.CURRENTQCOUNT 대응
					} else {
						try {
							double average = Double.parseDouble(averageObject.toString());

							mapping.put(fieldName, average);
						} catch (NumberFormatException e) {
							// 발생 가능성 낮음
							String exceptionMessage = "... an exception occurred because of invalid value [value=" + averageObject + "]";

							throw new NumberFormatException(exceptionMessage);
						}
					}
				}
			}
		} catch (Exception e) {
			logger.error("", e);
			return new ArrayList<>();
		}

		for (Map.Entry<String, Double> entry : mapping.entrySet()) {
			Map<String, Object> bundle = new HashMap<>();
			String fieldName 	= entry.getKey();
			double average 		= entry.getValue();
			String idcCol 		= null;

			switch (fieldName) {
				case "M14.STRATE.NONN2.STORAGERATIO": {
					bundle = this._buildAlarm6(average);

					if (!bundle.isEmpty()) {
						idcCol = "QTRANSFER_ALARM6";
					}
				} break;
				case "M14.SORTER.ABN.SORTERWAITCOUNTOVER": {
					bundle = this._buildAlarm7(average);

					if (!bundle.isEmpty()) {
						idcCol = "QTRANSFER_ALARM7";
					}
				} break;
				case "M14.SORTER.ABN.CUSORTERWAITCOUNTOVER": {
					bundle = this._buildAlarm8(average);

					if (!bundle.isEmpty()) {
						idcCol = "QTRANSFER_ALARM8";
					}
				} break;
				case "M14.QUE.ALL.CURRENTQCOUNT": {
					bundle = this._buildAlarm9(average);

					if (!bundle.isEmpty()) {
						idcCol = "QTRANSFER_ALARM9";
					}
				} break;
				case "M14.QUE.ALL.CURRENTQCNT": {
					double value1 = mapping.get("M14.QUE.STK.MANUALOUTCOUNT");
					bundle = this._buildAlarm10(average, value1);

					if (!bundle.isEmpty()) {
						idcCol = "QTRANSFER_ALARM10";
					}
				} break;
				case "M14.QUE.SENDFAB.VERTICALQUEUECOUNT": {
					double value1 = mapping.get("M14.STRATE.STB.NONN2STORAGERATIO");
					bundle = this._buildAlarm11(average, value1);

					if (!bundle.isEmpty()) {
						idcCol = "QTRANSFER_ALARM11";
					}
				} break;
			}

			if (idcCol != null) {
				bundle.put("IDCCOL", idcCol);
				bundle.put("IDCVAL", "0");
				bundle.put("AVERAGE", "0");
				bundle.put("SD_LOWER", "0");
				bundle.put("SD_UPPER", "0");
				bundle.put("SD_JUDGE", "F");
				bundle.put("STANDARDDEVIATION", "0");
				bundle.put("IQR_Q1", "0");
				bundle.put("IQR_Q2", "0");
				bundle.put("IQR_LOWER", "0");
				bundle.put("IQR_UPPER", "0");
				bundle.put("IQR_JUDGE", "0");

				//알람 컬럼
				bundle.put("ALARM_CD", "");
				bundle.put("ALARM_YN", "Y");

				result.add(bundle);
			}
		}
//----------------------------------------------------------------------------------------------------------------------
		return result;
	}
	//======================================================================================================================
	// 알람 구성
	// 2025-12-03 알람 #6 ~ 11 추가
	// 참고) ...afpjs_doc\ATLAS 분석 산출물\인수인계 자료\ATLAS_과제별 알람내용.pptx
	private Map<String, Object> _buildAlarmBase() {
		Map<String, Object> result = new HashMap<>();

		result.put("IDCVAL", "0");
		result.put("AVERAGE", "0");

		result.put("SD_LOWER", "0");
		result.put("SD_UPPER", "0");
		result.put("SD_JUDGE", "F");
		result.put("STANDARDDEVIATION", "0");

		result.put("IQR_Q1", "0");
		result.put("IQR_Q2", "0");
		result.put("IQR_LOWER", "0");
		result.put("IQR_UPPER", "0");
		result.put("IQR_JUDGE", "0");

		//알람 컬럼
		result.put("ALARM_CD", "");
		result.put("ALARM_YN", "Y");

		return result;
	}

	/**
	 * 알람 #1
	 * @return 알람 내용
	 */
	private Map<String, Object> _buildAlarm1(
			double m14ATotalCntValue,
			double reqLimit,
			String ohtRunRate,
			double queryResFor10mVal,
			double queryResFor24hVal,
			String currentTotalCnt,
			String queryResCompletedJobCntVal
	) {
		Map<String, Object> result = this._buildAlarmBase();

		//필수 컬럼
//		alarmRow.put("TIME", originValue.get(originValue.size()-1).get("TIME"));

		//알람 컬럼
		String title 	= XmlUtil.getMessage("QTRANSFER_REQ_TITLE");
		String subTitle	= XmlUtil.getMessage("QTRANSFER_REQ_SUB_TITLE");

		String content 	= XmlUtil.getMessage(
				"QTRANSFER_REQ_CONTENT",
				m14ATotalCntValue,			// 0
				reqLimit,					// 1
				ohtRunRate,					// 2
				queryResFor10mVal,			// 3
				queryResFor24hVal,			// 4
				currentTotalCnt,			// 5
				queryResCompletedJobCntVal	// 6
		);

		result.put("IDCCOL", "QTRANSFER_ALARM1");
		result.put("ALARM_DESC", title);
		result.put("ALARM_CMT", subTitle);
		result.put("ALARM_MSG_CTN", content);

		return result;
	}

	/**
	 * 알람 #2
	 * @return 알람 내용
	 */
	private Map<String, Object> _buildAlarm2(
			double m14ATotalCntValue,
			double reqLimit,
			String m14aToM16a10m,
			String m14aToM16a24h,
			String m16aToM14a10m,
			String m16aToM14a24h,
			String currentTotalCnt,
			String ohtRunRate
	) {
		Map<String, Object> result = this._buildAlarmBase();

		String storageUtil = "";

		try {
			var factory 		= QueryExecutorFactory.getQueryExecutor("M16A");
			String xmlPath 		= FilePathUtil.factoryPath(factory.getConnectionId());
			String dynamicQuery	= XmlUtil.loadQuery(xmlPath , "SELECT_M16A_STORAGE_UTIL");
			List<Map<String, Object>> m16a_detailList = factory.selectList(dynamicQuery);
			storageUtil 		= m16a_detailList.get(0).get("CURR_VAL").toString();

			factory.close();
		} catch (Exception e) {
			logger.error("", e);
		}

		//알람 컬럼
		String title 	= XmlUtil.getMessage("QTRANSFER_CNV_TITLE");
		String subTitle	= XmlUtil.getMessage("QTRANSFER_CNV_SUB_TITLE");

		String content 	= XmlUtil.getMessage(
				"QTRANSFER_CNV_CONTENT",
				m14ATotalCntValue,	// 0
				reqLimit,			// 1
				m14aToM16a10m,		// 2
				m14aToM16a24h,		// 3
				m16aToM14a10m,		// 4
				m16aToM14a24h,		// 5
				currentTotalCnt,	// 6
				storageUtil,		// 7
				ohtRunRate			// 8
		);

		result.put("IDCCOL", "QTRANSFER_ALARM2");
		result.put("ALARM_DESC", title);
		result.put("ALARM_CMT", subTitle);
		result.put("ALARM_MSG_CTN", content);

		return result;
	}

	/**
	 * 알람 #6 --- Normal STB Storage 부하 10분 평균 95% 이상
	 * @param currentPercentage 비교 값::10분 간 Normal STB Storage 평균 부하 값
	 * @return 알람 내용
	 */
	private Map<String, Object> _buildAlarm6(double currentPercentage) {
		double boundaryPercentage = this._findValueByCode("Q_TRANSFER_BOUNDARY_DEFAULT_6", 95);

		// 비교 값이 조건 값의 이상인 경우 알람 발생
		if (boundaryPercentage <= currentPercentage) {
			Map<String, Object> result = new HashMap<>();

			String title = XmlUtil.getMessage(
					"NORMAL_STB_STORAGE_LOAD_TITLE",
					boundaryPercentage    	// 0
			);

			String subTitle = XmlUtil.getMessage(
					"NORMAL_STB_STORAGE_LOAD_SUB_TITLE",
					boundaryPercentage    	// 0
			);

			String content = XmlUtil.getMessage(
					"NORMAL_STB_STORAGE_LOAD_CONTENT",
					boundaryPercentage,    	// 0
					currentPercentage    	// 1
			);

			result.put("ALARM_DESC", title);
			result.put("ALARM_CMT", subTitle);
			result.put("ALARM_MSG_CTN", content);

			return result;
		} else {
			return new HashMap<>();
		}
	}

	/**
	 * 알람 #7 --- Sorter Wait Count Over 10분 평균 100개 이상
	 * @param currentPercentage 비교 값::10분 간 Sorter Wait Count Over 평균 값
	 * @return 알람 내용
	 */
	private Map<String, Object> _buildAlarm7(double currentPercentage) {
		double boundaryPercentage = this._findValueByCode("Q_TRANSFER_BOUNDARY_DEFAULT_7", 100);

		// 비교 값이 조건 값의 이상인 경우 알람 발생
		if (boundaryPercentage <= currentPercentage) {
			Map<String, Object> result = new HashMap<>();

			String title = XmlUtil.getMessage(
					"SORTER_WAIT_COUNT_OVER_TITLE",
					boundaryPercentage    	// 0
			);

			String subTitle = XmlUtil.getMessage(
					"SORTER_WAIT_COUNT_OVER_SUB_TITLE",
					boundaryPercentage    	// 0
			);

			String content = XmlUtil.getMessage(
					"SORTER_WAIT_COUNT_OVER_CONTENT",
					boundaryPercentage,    	// 0
					currentPercentage    	// 1
			);

			result.put("ALARM_DESC", title);
			result.put("ALARM_CMT", subTitle);
			result.put("ALARM_MSG_CTN", content);

			return result;
		} else {
			return new HashMap<>();
		}
	}

	/**
	 * 알람 #8 --- Cu Sorter Wait Count Over 10분 평균 100개 이상
	 * @param currentCount 비교 값::10분 간 Cu Sorter Wait Count Over 평균 값
	 * @return 알람 내용
	 */
	private Map<String, Object> _buildAlarm8(double currentCount) {
		double boundaryCount = this._findValueByCode("Q_TRANSFER_BOUNDARY_DEFAULT_8", 100);

		// 비교 값이 조건 값의 이상인 경우 알람 발생
		if (boundaryCount <= currentCount) {
			Map<String, Object> result = new HashMap<>();

			String title = XmlUtil.getMessage(
					"CU_SORTER_WAIT_COUNT_OVER_TITLE",
					boundaryCount    		// 0
			);

			String subTitle = XmlUtil.getMessage(
					"CU_SORTER_WAIT_COUNT_OVER_SUB_TITLE",
					boundaryCount    		// 0
			);

			String content = XmlUtil.getMessage(
					"CU_SORTER_WAIT_COUNT_OVER_CONTENT",
					boundaryCount,   		// 0
					currentCount    		// 1
			);

			result.put("ALARM_DESC", title);
			result.put("ALARM_CMT", subTitle);
			result.put("ALARM_MSG_CTN", content);

			return result;
		} else {
			return new HashMap<>();
		}
	}

	/**
	 * 알람 #9 --- Q-COMPLETED 10분 평균 2700개 이하
	 * @param currentCount 비교 값::10분 간 Q-COMPLETED 평균 값
	 * @return 알람 내용
	 */
	private Map<String, Object> _buildAlarm9(double currentCount) {
		double boundaryCount = this._findValueByCode("Q_TRANSFER_BOUNDARY_DEFAULT_9", 2700);

		// 비교 값이 조건 값의 이상인 경우 알람 발생
		if (boundaryCount <= currentCount) {
			Map<String, Object> result = new HashMap<>();

			String title = XmlUtil.getMessage(
					"Q_COMPLETED_UNDER_AVERAGE_TITLE",
					boundaryCount	// 0
			);

			String subTitle = XmlUtil.getMessage(
					"Q_COMPLETED_UNDER_AVERAGE_SUB_TITLE",
					boundaryCount	// 0
			);

			String content = XmlUtil.getMessage(
					"Q_COMPLETED_UNDER_AVERAGE_CONTENT",
					boundaryCount,	// 0
					currentCount	// 1
			);

			result.put("ALARM_DESC", title);
			result.put("ALARM_CMT", subTitle);
			result.put("ALARM_MSG_CTN", content);

			return result;
		} else {
			return new HashMap<>();
		}
	}

	/**
	 * 알람 #10 --- 10분 평균 Total Que 1,700 개 이상 & Manual Out Que 200 개 이하
	 * @param currentCount1	비교 값1::10분 간 Total Que 평균 값
	 * @param currentCount2	비교 값2::10분 간 Manual Out Que 평균 값
	 * @return 알람 내용
	 */
	private Map<String, Object> _buildAlarm10(double currentCount1, double currentCount2) {
		double boundaryCount1 = this._findValueByCode("Q_TRANSFER_BOUNDARY_DEFAULT_10_1", 1700);
		double boundaryCount2 = this._findValueByCode("Q_TRANSFER_BOUNDARY_DEFAULT_10_2", 200);

		// 비교 값이 조건 값의 이상인 경우 알람 발생
		if (boundaryCount1 <= currentCount1 && boundaryCount2 <= currentCount2) {
			Map<String, Object> result = new HashMap<>();

			String title = XmlUtil.getMessage(
					"TOTAL_QUE_INCREASED_N_MANUAL_OUT_QUE_DECREASED_TITLE",
					boundaryCount1	// 0
			);

			String subTitle = XmlUtil.getMessage(
					"TOTAL_QUE_INCREASED_N_MANUAL_OUT_QUE_DECREASED_SUB_TITLE",
					boundaryCount1,	// 0
					boundaryCount2	// 1
			);

			String content = XmlUtil.getMessage(
					"TOTAL_QUE_INCREASED_N_MANUAL_OUT_QUE_DECREASED_CONTENT",
					boundaryCount1,	// 0
					boundaryCount2,	// 1
					currentCount1,	// 2
					currentCount2	// 3
			);

			result.put("ALARM_DESC", title);
			result.put("ALARM_CMT", subTitle);
			result.put("ALARM_MSG_CTN", content);

			return result;
		} else {
			return new HashMap<>();
		}
	}

	/**
	 * 알람 #11 --- 10분 평균 층간 대기 QUE 500개 이상, Normal STB Storage 부하 97% 이상
	 * @param currentCount       비교 값1::10분 간 층간 대기 QUE 평균 값
	 * @param currentPercentage  비교 값2::10분 간 Normal STB Storage 부하 평균 값
	 * @return 알람 내용
	 */
	private Map<String, Object> _buildAlarm11(double currentCount, double currentPercentage) {
		double boundaryCount = this._findValueByCode("Q_TRANSFER_BOUNDARY_DEFAULT_11_1", 500);
		double boundaryPercentage = this._findValueByCode("Q_TRANSFER_BOUNDARY_DEFAULT_11_2", 97);

		// 비교 값이 조건 값의 이상인 경우 알람 발생
		if (boundaryCount <= currentCount && boundaryPercentage <= currentPercentage) {
			Map<String, Object> result = new HashMap<>();

			String title = XmlUtil.getMessage(
					"WAITING_QUE_INCREASED_N_STB_STORAGE_LOAD_TITLE",
					boundaryCount    		// 0
			);

			String subTitle = XmlUtil.getMessage(
					"WAITING_QUE_INCREASED_N_STB_STORAGE_LOAD_SUB_TITLE",
					boundaryCount,    		// 0
					boundaryPercentage		// 1
			);

			String content = XmlUtil.getMessage(
					"WAITING_QUE_INCREASED_N_STB_STORAGE_LOAD_CONTENT",
					boundaryCount,   		// 0
					boundaryPercentage,		// 1
					currentCount,    		// 2
					currentPercentage		// 3
			);

			result.put("ALARM_DESC", title);
			result.put("ALARM_CMT", subTitle);
			result.put("ALARM_MSG_CTN", content);

			return result;
		} else {
			return new HashMap<>();
		}
	}
//======================================================================================================================
	/**
	 * @param code variable.xml 에서 조회할 값의 code 값
	 * @param defaultValue 조회에 실패한 경우 대체할 기본 값
	 */
	private double _findValueByCode(String code, double defaultValue) {
		try {
			String temp = XmlUtil.getVariableEnv(code, (Object) null);

			if (!temp.contains(XmlUtil.DEFAULT_VALUE)) {
				try {
					return Double.parseDouble(temp);
				} catch (NumberFormatException e) {
					throw new NumberFormatException(e.getMessage());
				}
			}
		} catch (Exception e) {
			logger.error("... an exception occurred [t={}] [code={}]", e.getMessage(), code, e);
		}

		return defaultValue;
	}

	private String _collectIdcValue(List<Map<String, Object>> list, String idcKey) {
		List<String> bundle = new ArrayList<>();

		for (int i = 0; i < list.size(); i++) {
			Map<String, Object> item = list.get(i);

			if (item.get("IDCCOL").equals(idcKey)) {
				Object idcValObject = item.get("IDCVAL");

				if (idcValObject == null) {
					logger.error("... an context contains invalid value, `IDCVAL` field is null [index: {}] [t: {}]", i, item);
				} else {
					String idcVal = idcValObject.toString();

					bundle.add(idcVal);
				}
			}
		}

		return String.join(", ", bundle);
	}
}
