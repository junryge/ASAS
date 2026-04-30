public class ServerResourceApmBatch implements Job{
	private final Logger logger = LoggerFactory.getLogger(getClass());

	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		final int DELAYED_TIME = 1000 * 60;

		if (Util.isCurrentIC()) {
			logger.info("... `ServerResourceApmBatch` has started");

			long timer = System.currentTimeMillis();

			this._run();

			long checkTimer = System.currentTimeMillis() - timer;

			if (checkTimer >= DELAYED_TIME) {
				logger.error("... !!!DELAYED!!! `ServerResourceApmBatch` has finished [elapsed time: {}m ({}ms)]", checkTimer / (60 * 1000), checkTimer);
			} else {
				logger.info("... `ServerResourceApmBatch` has finished [elapsed time: {}ms]", checkTimer);
			}
		}
	}

	private void _run() {
		final List<Tuple> countList = new ArrayList<>();

		try {
			List<Map<String, Object>> dataList = getApmDataByOracle();

			for(Map<String, Object> map : dataList) {
				final Tuple countMapSet = new Tuple();

				mapToTplConvert(map, countMapSet);
				countList.add(countMapSet);
			}

			//전일 1일치 Oracle 조회 데이터 삽입
			LogpressoAPI.setInsertTuples("server_resource_apm", countList,15);

			dataList = getAlarmText(dataList,"MEAS");

			//Logpresso 7일치 데이터 조회
			List<Map<String, Object>> serverResourceList =  getResourceDataList();

			if(serverResourceList.size() > 0) {
				int weeksLength = serverResourceList.size()/480;
				//7일치 데이터를 갖고 있는 경우에만 예측 실행

				//입력 값 7일치 데이터 범위 동적으로 관리
				String inputRangeStr = XmlUtil.getVariableEnv("APM_PREDICT_INPUT_RANGE",null);

				if(inputRangeStr.contains("Unknown ALARM CODE")) {
					inputRangeStr = "60";
				}
				int inputRange = Integer.parseInt(inputRangeStr);

				if(weeksLength  >=  inputRange ) {
					exectePredictData(serverResourceList);
				}
			}
		}catch (Exception e) {
			logger.error("",e);
		}
	}


	public List<Map<String,Object>> getApmDataByOracle(){
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();

		try {
			for (String fab : new String[] { "M14APM" }) {
				String xmlPath = "";
				String dynamicQuery = "";
				switch (fab) {
					case "M14APM":
						var factory = QueryExecutorFactory.getQueryExecutor(fab);
						xmlPath = FilePathUtil.factoryPath(factory.getConnectionId());
						dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_APM_RESOURCE_LIST");
						List<Map<String, Object>> m14b_detailList = factory.selectList(dynamicQuery);
						result.addAll(m14b_detailList);
						factory.close();
					default:
						continue;
				}
			}


		}catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}

	List<Map<String, Object>> getResourceDataList(){
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String,Object>>();
		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "apmDataValid");

			sQuery.append(strQuery);
			result = LogpressoAPI.responseResult(sQuery.toString());
		}catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}
	public List<Map<String,Object>> getAlarmText(List<Map<String, Object>> dataList,String type) {
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();

		try {

			String typStr = type.equals("MEAS") ? " 측정치가 " : " 예측치가 ";

			Map<Object, List<Map<String, Object>>> groupData = new HashMap<Object, List<Map<String,Object>>>();
			if(type.equals("MEAS")) {
				groupData = dataList.stream().collect(Collectors
						.groupingBy(row -> row.get("MEAS_TM") + "|" + row.get("FAB_ID") + "|" + row.get("SVR_NM")));
			} else {
				groupData = dataList.stream().collect(Collectors
						.groupingBy(row -> row.get("MEAS_TM") + "|" + row.get("FCAST_TM") + "|" + row.get("FAB_ID") + "|" + row.get("SVR_NM")));
			}

			String cpuOsLimit = XmlUtil.getVariableEnv("CPU_OS_LIMIT",null);
			if(cpuOsLimit.contains("Unkown ALARM CODE")) {
				cpuOsLimit = "30";
			}
			String cpuUserLimit = XmlUtil.getVariableEnv("CPU_USER_LIMIT",null);
			if(cpuUserLimit.contains("Unkown ALARM CODE")) {
				cpuUserLimit = "10";
			}
			String jvmCpuLimit = XmlUtil.getVariableEnv("JVM_CPU_LIMIT",null);
			if(jvmCpuLimit.contains("Unkown ALARM CODE")) {
				jvmCpuLimit = "1";
			}
			String jvmHeapLimit = XmlUtil.getVariableEnv("JVM_HEAP_LIMIT",null);
			if(jvmHeapLimit.contains("Unkown ALARM CODE")) {
				jvmHeapLimit = "400";
			}
			String jvmHeapLimit2 = XmlUtil.getVariableEnv("JVM_HEAP_LIMIT2",null);
			if(jvmHeapLimit2.contains("Unkown ALARM CODE")) {
				jvmHeapLimit2 = "800";
			}
			String jvmThreadLimit = XmlUtil.getVariableEnv("JVM_THREAD_LIMIT",null);
			if(jvmThreadLimit.contains("Unkown ALARM CODE")) {
				jvmThreadLimit = "1000";
			}
			String txnTimeLimit = XmlUtil.getVariableEnv("TXN_TIME_LIMIT",null);
			if(txnTimeLimit.contains("Unkown ALARM CODE")) {
				txnTimeLimit = "1";
			}

			String alarmDesc = XmlUtil.getMessage("SERVER_RESOURCE_DESC");
			String alarmCmt = XmlUtil.getMessage("SERVER_RESOURCE_CMT",typStr);


			double cpuOsLimitVal = Double.parseDouble(cpuOsLimit);
			double cpuUserLimitVal = Double.parseDouble(cpuUserLimit);
			double jvmCpuLimitVal = Double.parseDouble(jvmCpuLimit);
			double jvmHeapLimitVal = Double.parseDouble(jvmHeapLimit);
			double jvmHeapLimitVal2 = Double.parseDouble(jvmHeapLimit2);
			double jvmThreadLimitVal = Double.parseDouble(jvmThreadLimit);
			double txnTimeLimitVal = Double.parseDouble(txnTimeLimit);



			Map<String, StringBuilder> alarmMap = new HashMap();
			for (Entry<Object, List<Map<String, Object>>> entry : groupData.entrySet()) {
				String key = entry.getKey().toString();
				List<Map<String, Object>> groupRows = entry.getValue();
				for (Map<String, Object> row : groupRows) {
					try {
						String idcNm = row.get("IDC_NM").toString();
						String svrNm = row.get("SVR_NM").toString();
						String procNm = row.get("PROC_NM").toString();
						String rowVal = "0";
						if(type.equals("MEAS")) {
							rowVal = row.get("MEAS_VAL").toString();
						}else {
							rowVal = row.get("FCAST_VAL").toString();
						}
						double rowValue = Double.parseDouble(rowVal);
						if (svrNm.equals("m14mcsapp01") || svrNm.equals("m14mcsapp02")) {
							switch (idcNm) {
								case "CPU_OS":
									if (rowValue > cpuOsLimitVal) {
										StringBuilder alarmTxt = alarmMap.getOrDefault(svrNm, new StringBuilder());
										alarmTxt.append(svrNm +" "+ procNm + " " + idcNm).append(typStr).append(rowValue)
												.append("으로 기준치 "+cpuOsLimit+"을 초과하였습니다.\\n\n");
										alarmMap.put(svrNm, alarmTxt);
									}
									break;
								case "CPU_USER":
									if (rowValue > cpuUserLimitVal) {
										StringBuilder alarmTxt = alarmMap.getOrDefault(svrNm, new StringBuilder());
										alarmTxt.append(svrNm +" "+ procNm + " " + idcNm).append(typStr).append(rowValue)
												.append("으로 기준치 "+cpuUserLimit+"을 초과하였습니다.\\n\n");
										alarmMap.put(svrNm, alarmTxt);
									}
									break;
								case "JVM_CPU":
									if (rowValue > jvmCpuLimitVal) {
										StringBuilder alarmTxt = alarmMap.getOrDefault(svrNm, new StringBuilder());
										alarmTxt.append(svrNm +" "+ procNm + " " + idcNm).append(typStr).append(rowValue)
												.append("으로 기준치 "+jvmCpuLimit+"을 초과하였습니다.\\n\n");
										alarmMap.put(svrNm, alarmTxt);
									}
									break;
								case "JVM_HEAP":
									double heapLimit = jvmHeapLimitVal;
									if (procNm.contains("TS")) {
										heapLimit = jvmHeapLimitVal2;
									}
									if (rowValue > heapLimit) {
										StringBuilder alarmTxt = alarmMap.getOrDefault(svrNm, new StringBuilder());
										alarmTxt.append(svrNm +" "+ procNm + " " + idcNm).append(typStr).append(rowValue)
												.append("으로 기준치 "+heapLimit+"을 초과하였습니다.\\n\n");
										alarmMap.put(svrNm, alarmTxt);
									}
									break;
								case "JVM_THREAD":
									if (rowValue > jvmThreadLimitVal) {
										StringBuilder alarmTxt = alarmMap.getOrDefault(svrNm, new StringBuilder());
										alarmTxt.append(svrNm +" "+ procNm + " " + idcNm).append(typStr).append(rowValue)
												.append("으로 기준치 "+jvmThreadLimit+"을 초과하였습니다.\\n\n");
										alarmMap.put(svrNm, alarmTxt);
									}
									break;
								case "TXN_TIME":
									if (rowValue > txnTimeLimitVal) {
										StringBuilder alarmTxt = alarmMap.getOrDefault(svrNm, new StringBuilder());
										alarmTxt.append(svrNm +" "+ procNm + " " + idcNm).append(typStr).append(rowValue)
												.append("으로 기준치 "+txnTimeLimit+"을 초과하였습니다.\\n\n");
										alarmMap.put(svrNm, alarmTxt);
									}
									break;
								default:
									break;
							}
						}
					} catch (Exception e) {
						logger.error("",e);
					}
				}
			}

			for (Map.Entry<String, StringBuilder> entry : alarmMap.entrySet()) {

				String svrNm = entry.getKey();
				Map<String, Object> alarmData = new HashMap<String, Object>();
				if(type.equals("MEAS")) {//측정치 
					alarmData.put("MEAS_TM", dataList.get(0).get("MEAS_TM"));
					alarmData.put("FAB_ID", dataList.get(0).get("FAB_ID"));
					alarmData.put("SVR_NM", svrNm.toUpperCase());
					alarmData.put("PROC_NM", "ALARM");
					alarmData.put("IDC_NM", "ALL");
					alarmData.put("MEAS_VAL", 0);
					alarmData.put("ALARM_MSG_CTN", entry.getValue());
					alarmData.put("ALARM_DESC", alarmDesc);
					alarmData.put("ALARM_CMT", alarmCmt);
					alarmData.put("ALARM_YN", "Y");
				}else { // 예측치
					alarmData.put("MEAS_TM", dataList.get(0).get("MEAS_TM"));
					alarmData.put("FCAST_TM", dataList.get(dataList.size()-1).get("FCAST_TM"));
					alarmData.put("FAB_ID", dataList.get(0).get("FAB_ID"));
					alarmData.put("SVR_NM", svrNm.toUpperCase());
					alarmData.put("PROC_NM", "ALARM");
					alarmData.put("IDC_NM", "ALL");
					alarmData.put("FCAST_VAL", 0);
					alarmData.put("MODEL_NM", "Prophet");
					alarmData.put("ALARM_MSG_CTN", entry.getValue());
					alarmData.put("ALARM_DESC", alarmDesc);
					alarmData.put("ALARM_CMT", alarmCmt);
					alarmData.put("ALARM_YN", "Y");
				}
				dataList.add(alarmData);
			}


			result = dataList;
		} catch (Exception e) {
			logger.error("",e);
		}

		return result;
	}


	void exectePredictData(List<Map<String, Object>> serverResourceList) {
		try {
			ObjectMapper mapper = new ObjectMapper();

			// Convert list of maps to CSV format
			StringBuilder csvData = new StringBuilder();
			if (!serverResourceList.isEmpty()) {
				// Add header
				Map<String, Object> firstRecord = serverResourceList.get(0);
				csvData.append(String.join(",", firstRecord.keySet())).append("\n");

				// Add rows
				for (Map<String, Object> record : serverResourceList) {
					List<String> values = new ArrayList<>();
					for (Object value : record.values()) {
						// Convert each value to string and handle commas and quotes
						String strValue = value.toString();
						if (strValue.contains(",") || strValue.contains("\"")) {
							strValue = "\"" + strValue.replace("\"", "\"\"") + "\"";
						}
						values.add(strValue);
					}
					csvData.append(String.join(",", values)).append("\n");
				}
			}

			// Save CSV data to file
			File folder = new File(FilePathUtil.PYTHON_FILE_PATH);
			if (!folder.exists()) {
				folder.mkdirs();
			}
			String fileName = "data/APMWEEKDATA.csv";
			String filePath = FilePathUtil.PYTHON_FILE_PATH + File.separator + fileName;
			File file = new File(filePath);
			if (file.exists()) {
				file.delete();
			}
			FileWriter fileWriter = new FileWriter(filePath);
			fileWriter.write(csvData.toString());
			fileWriter.flush();
		}catch (Exception e) {
			e.printStackTrace();
		}finally {
			try {
				String outputRangeStr = XmlUtil.getVariableEnv("APM_PREDICT_OUTPUT_RANGE",null);

				if(outputRangeStr.contains("Unknown ALARM CODE")) {
					outputRangeStr = "7";
				}

				logger.info("Start Server Resource APM Prediction");

				final List<Tuple> predictList = new ArrayList<Tuple>();

				List<Map<String, Object>> result = PythonUtil.executeWithParam("SERVER_RESOURCE_MODEL.py", false,outputRangeStr);

				//예측값 알람 추가 
				result = getAlarmText(result,"PREDICT");

				logger.info("End Server Resource APM Prediction List Size : " + result.size());
				if(result.size() > 0) {
					for (Map<String, Object> map : result) {
						final Tuple predictMapSet = new Tuple();
						mapToTplConvert(map, predictMapSet);
						predictList.add(predictMapSet);
					}
					LogpressoAPI.setInsertTuples("server_resource_predict", predictList,15);
				}

			}catch (Exception e) {
				e.printStackTrace();
			}
		}
	}

	public static void mapToTplConvert(final Map<String, Object> obj, final Tuple mapDataSet) {
		if (obj == null)
			return;
		for (Map.Entry<String, Object> entry : obj.entrySet()) {
			try {
				mapDataSet.put(entry.getKey(), entry.getValue().toString());
			} catch (Exception e) {
				e.printStackTrace();
			}
		}
	}
}
