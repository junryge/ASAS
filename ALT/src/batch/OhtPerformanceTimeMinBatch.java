public class OhtPerformanceTimeMinBatch implements Job{
	private final Logger logger = LoggerFactory.getLogger(getClass());
	
	public static final String ALARM_MESSAGE_PATH
			= String.format("%s/oht_alarm_message.xml", System.getProperty("SMARTFX_REPOSITORY"));
	
	private final int DELAYED_TIME = 1000 * 60;

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

	private void _run() {
		try {
//			XmlUtil.loadLogpressoParm(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2);
//			XmlUtil.loadAlarmMessage(ALARM_MESSAGE_PATH);
//			XmlUtil.loadVariableEnv();
			//Oht Performance Time 매분 적재 하는 데이터
			//1. OHT 분당 가동률
			List<Map<String, Object>> ohtRunRateList
					= XmlUtil.selectLogpressoQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "vhlRunRate");

			//2. 분당 메세지 수
			List<Map<String, Object>> messageCountMinList = _getMessageCountMinList(ohtRunRateList);

			ohtRunRateList.addAll(messageCountMinList);

			//3. 분당 메세지 시간
			List<Map<String, Object>> getMessageTimeMinList = _getMessageTimeMinList(ohtRunRateList);

			LocalDateTime now 			= LocalDateTime.now();
			DateTimeFormatter formatter	= DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");
			String formattedDateTime 	= now.format(formatter);

			for (Map<String,Object> map : ohtRunRateList) {
				map.put("TIME", formattedDateTime);
			}

			for (Map<String,Object> map : getMessageTimeMinList) {
				map.put("TIME", formattedDateTime);
			}

			insertListData(ohtRunRateList, "oht_cmd_count");
			insertListData(getMessageTimeMinList, "oht_time_avg");
		} catch (Exception e) {
			logger.error("", e);
		}
	}

	private List<Map<String, Object>> _getMessageCountMinList(List<Map<String, Object>> ohtRunRateList){
		List<Map<String, Object>> result = new ArrayList<>();
		List<Map<String, Object>> result2;
		List<Map<String, Object>> result3;

		try {
			//입력 변수 추가
			String reqLimit = XmlUtil.getVariableEnv("REQ_LIMIT",(Object) null);

			if (reqLimit.contains("Unknown ALARM CODE")) {
				reqLimit = "50";
			}

			String reqLimit2 = XmlUtil.getVariableEnv("REQ_LIMIT2",(Object) null);

			if (reqLimit2.contains("Unknown ALARM CODE")) {
				reqLimit2 = "50";
			}

			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "msgCountPerMin");
			result = LogpressoAPI.responseResult(strQuery);

			//1시간 분당 메세지 수
			String strQuery2 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "searchOHTCNTHour");
			result2 =  LogpressoAPI.responseResult(strQuery2);

			//MES 분당 Q 개수
			String strQuery3 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "mesOHTQCntAlarmValid");
			result3 =  LogpressoAPI.responseResult(strQuery3);

			Map<Object, List<Map<String, Object>>> groupData = result.stream()
					.collect(
							Collectors.groupingBy(
									row -> row.get("TIME") + "|"
											+ row.get("MACHINENAME") + "|"
											+ row.get("MESSAGE_TYPE") + "|"
											+ row.get("MESSAGE_COUNT") + "|"
											+ row.get("ALARM") + "|"
											+ row.get("IDC_NM")
							));

			for (Map.Entry<Object, List<Map<String, Object>>> entry : groupData.entrySet()) {
				List<Map<String, Object>> groupRows = entry.getValue();

				for (Map<String, Object> row : groupRows) {
					try {
						String msgType = row.get("MESSAGE_TYPE").toString();

						if (msgType.equals("REP")) {
							// 알람 발생 검증 로직
							// 조건 1 - 1시간 평균 REPLY COUNT 비교
							// 현재 REPLY 값
							String currentRepData = result.stream()
									.filter(map -> "REP".equals(map.get("MESSAGE_TYPE")))
									.map(map -> map.get("MESSAGE_COUNT").toString())
									.collect(Collectors.joining(", "));

							// 1시간 기준 MCS 값
							String mcsCountPerHourRepData = result2.stream()
									.filter(map -> "REP".equals(map.get("IDC_NM")))
									.map(map -> map.get("IDC_VAL").toString())
									.collect(Collectors.joining(", "));

							// 매분 MES 반송큐 CNT
							String mesCountPerMinData = result3.stream()
									.filter(map -> "M_MES".equals(map.get("TX")))
									.map(map -> map.get("MESSAGE_COUNT").toString())
									.collect(Collectors.joining(", "));

							String ohtRunRate = ohtRunRateList.stream()
									.filter(map -> "FOUP".equals(map.get("CARRIERTYPE")))
									.map(map -> map.get("VHLOPERRATE").toString())
									.collect(Collectors.joining(", "));

							String alarmDesc = "";
							String alarmCmt = "";
							String alarmText = "";
							String alarmYn = "N";

							if (!currentRepData.isEmpty() && !mcsCountPerHourRepData.isEmpty() && !mesCountPerMinData.isEmpty()) {
								double currentRepValue = Double.parseDouble(currentRepData.split(", ")[0]);
								double mcsCountPerHourRepValue = Double.parseDouble(mcsCountPerHourRepData.split(", ")[0]);
								double mesCountPerMinValue = Double.parseDouble(mesCountPerMinData.split(", ")[0]);
//								double ohtRunRateValue = Double.parseDouble(ohtRunRate.split(", ")[0]);

								double reqLimitValue = Double.parseDouble(String.valueOf(Double.parseDouble(reqLimit)/100));
								double reqLimit2Value = Double.parseDouble(String.valueOf(Double.parseDouble(reqLimit2)/100));

								double validValue = mcsCountPerHourRepValue * reqLimitValue;
								double validValue2 = mcsCountPerHourRepValue * reqLimit2Value;

								boolean condition1 = currentRepValue <= validValue;
								boolean condition2 = mesCountPerMinValue <= validValue2;

								if (condition1 && condition2) {
									String reqAlarmName = XmlUtil.getOhtMessage("REP_ALARM_NAME", (Object) null);

									if (reqAlarmName.contains("Unknown ALARM CODE")) {
										reqAlarmName = "반송 명령에 대한 OHT 응답 메세지 수 적음";
									}

									alarmDesc = reqAlarmName;
									String reqAlarmBold = XmlUtil.getOhtMessage("REP_ALARM_BOLD", (Object) null);

									if (reqAlarmBold.contains("Unknown ALARM CODE")) {
										reqAlarmBold = "-MES ▶ MCS 반송 Q개수 이상이 감지 되었습니다.";
									}

									alarmCmt = reqAlarmBold;
									alarmYn = "Y";
									alarmText = XmlUtil.getOhtMessage("REQ_ALARM"
											,currentRepData
											,reqLimit
											,mesCountPerMinData
											,ohtRunRate);
								} else if (condition1) {
									String reqAlarmName = XmlUtil.getOhtMessage("REP_ALARM_NAME", (Object) null);

									if (reqAlarmName.contains("Unknown ALARM CODE")) {
										reqAlarmName = "반송 명령에 대한 OHT 응답 메세지 수 적음";
									}

									alarmDesc = reqAlarmName;
									String reqAlarmBold = XmlUtil.getOhtMessage("REP_ALARM_BOLD2", (Object) null);

									if (reqAlarmBold.contains("Unknown ALARM CODE")) {
										reqAlarmBold = "-OHT ▶ MCS로 응답하는 반송 CMD Q개수 이상이 감지 되었습니다.";
									}

									alarmCmt = reqAlarmBold;
									alarmYn = "Y";
									alarmText = XmlUtil.getOhtMessage("REQ_ALARM"
											,currentRepData
											,reqLimit
											,mesCountPerMinData
											,ohtRunRate);
								}
							}

							row.put("ALARM_DESC", alarmDesc);
							row.put("ALARM_CMT", alarmCmt);
							row.put("ALARM_MSG_CTN", alarmText);
							row.put("ALARM",alarmYn);
						}
					} catch (Exception e) {
						logger.error("", e);
					}
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		return result;
	}

	private List<Map<String, Object>> _getMessageTimeMinList(List<Map<String, Object>> ohtRunRateList){
		List<Map<String, Object>> result = new ArrayList<>();
		List<Map<String, Object>> result2;
		List<Map<String, Object>> result3;
		List<Map<String, Object>> result4;

		try {
			String assignLimit = XmlUtil.getVariableEnv("ASSIGN_LIMIT", (Object) null);

			if (assignLimit.contains("Unknown ALARM CODE")) {
				assignLimit = "100";
			}

			String transferringLimit = XmlUtil.getVariableEnv("TRANSFERRING_LIMIT", (Object) null);

			if (transferringLimit.contains("Unknown ALARM CODE")) {
				transferringLimit = "100";
			}

			String vhlRunRateLimit = XmlUtil.getVariableEnv("VHL_RATE_LIMIT", (Object) null);

			if (vhlRunRateLimit.contains("Unknown ALARM CODE")) {
				vhlRunRateLimit = "95";
			}

			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "msgTimePerMin");
			result = LogpressoAPI.responseResult(strQuery);

			// 1시간 기준 분당 응답시간차
			String strQuery2 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "msgTimePerHour");
			result2 = LogpressoAPI.responseResult(strQuery2);

			// MES 분당 Q 개수
			String strQuery3 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "mesOHTQCntAlarmValid");
			result3 =  LogpressoAPI.responseResult(strQuery3);

			// MES 분당 Q 개수
			String strQuery4 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "searchOHTCNT10Min");
			result4 =  LogpressoAPI.responseResult(strQuery4);

//			Map<String, Object> resMap = new HashMap<String, Object>();
			String[] strArr = {"REP","ASSIGN","ACQUIRED","TRANSFERRING","DESPOSITED","COMPLETED"};
			Set<String> requiredTypes = new HashSet<>(Arrays.asList(strArr));
			Set<String> foundTypes = new HashSet<>();

			Map<Object, List<Map<String, Object>>> groupData = result.stream().collect(Collectors
					.groupingBy(
							row -> row.get("TIME") + "|"
									+ row.get("MACHINENAME") + "|"
									+ row.get("MESSAGE_TYPE") + "|"
									+ row.get("MESSAGE_TIME") + "|"
									+ row.get("ALARM") + "|"
									+ row.get("IDC_NM")
					));

			for (Map.Entry<Object, List<Map<String, Object>>> entry : groupData.entrySet()) {
				List<Map<String, Object>> groupRows = entry.getValue();

				for (Map<String, Object> row : groupRows) {
					try {
						String msgType = row.get("MESSAGE_TYP").toString();

						if (msgType.equals("ASSIGN")) {
							//알람 발생 검증 로직
							//조건 1 - 1시간 평균 ASSIGN TIME 비교

							//매분 ASSIGNED TIME 평균
							String currentAssignData = result.stream().filter(map -> "ASSIGN".equals(map.get("MESSAGE_TYP"))).map(map -> map.get("MESSAGE_TIME").toString()).collect(Collectors.joining(", "));

							//1시간 기준 분당 ASSIGNED TIME 평균
							String mcsTimePerHour = result2.stream().filter(map -> "ASSIGN".equals(map.get("MESSAGE_TYP"))).map(map -> map.get("MESSAGE_TIME").toString()).collect(Collectors.joining(", "));
							String ohtRunRate = ohtRunRateList.stream().filter(map -> "FOUP".equals(map.get("CARRIERTYPE"))).map(map -> map.get("VHLOPERRATE").toString()).collect(Collectors.joining(", "));

							//매분 MES 반송큐 CNT
							String mesCountPerMinData = result3.stream().filter(map -> "M_MES".equals(map.get("TX"))).map(map -> map.get("MESSAGE_COUNT").toString()).collect(Collectors.joining(", "));
							String assignCountPer10MinData = result4.stream().filter(map -> "ASSIGN".equals(map.get("MESSAGE_TYPE"))).map(map -> map.get("CNT").toString()).collect(Collectors.joining(", "));

							String alarmDesc = "";
							String alarmCmt = "";
							String alarmText = "";
							String alarmYn = "N";

							if (!currentAssignData.isEmpty() && !mcsTimePerHour.isEmpty()) {
								double currentAssignValue = Double.parseDouble(currentAssignData.split(", ")[0]);
								double mcsTimePerHourRepValue = Double.parseDouble(mcsTimePerHour.split(", ")[0]);
								double ohtRunRateValue = Double.parseDouble(ohtRunRate.split(", ")[0]);

								double assignLimitValue = Double.parseDouble(assignLimit)/100;

								double validValue = mcsTimePerHourRepValue * assignLimitValue;
								double vhlRunRateLimitValue = Double.parseDouble(vhlRunRateLimit);

								// 1시간 평균과 현재값 차 계산
								double diffValue = ((currentAssignValue-mcsTimePerHourRepValue)/currentAssignValue)*100;

								boolean condition1 = currentAssignValue >= validValue;
								boolean condition2 = ohtRunRateValue >= vhlRunRateLimitValue;

								if (condition1 && condition2) {
									// 입력 변수 추가
									String ohtTimeAlarmName = XmlUtil.getOhtMessage("ASSIGN_TIME_ALARM_NAME", (Object) null);

									if (ohtTimeAlarmName.contains("Unknown ALARM CODE")) {
										ohtTimeAlarmName = "OHT에서 VHL 선정 시간 증가";
									}

									alarmDesc = ohtTimeAlarmName;
									String reqAlarmBold = XmlUtil.getOhtMessage("ASSIGN_TIME_ALARM_BOLD", (Object) null);

									if (reqAlarmBold.contains("Unknown ALARM CODE")) {
										reqAlarmBold = "-OHT에서 VHL을 선정하는 시간 증가가 감지되었습니다.";
									}

									alarmCmt = reqAlarmBold;
									alarmYn = "Y";
									alarmText = XmlUtil.getOhtMessage("ASSIGN_ALARM"
											,currentAssignData
											,assignLimit
											,ohtRunRateValue
											,vhlRunRateLimitValue
											,mesCountPerMinData
											,assignCountPer10MinData
											,mcsTimePerHour
											,diffValue
									);

//									System.out.println(alarmText);
								} else if (condition1) {
									// 입력 변수 추가
									String ohtTimeAlarmName = XmlUtil.getOhtMessage("ASSIGN_TIME_ALARM_NAME", (Object) null);

									if (ohtTimeAlarmName.contains("Unknown ALARM CODE")) {
										ohtTimeAlarmName = "OHT에서 VHL 선정 시간 증가";
									}

									alarmDesc = ohtTimeAlarmName;
									String reqAlarmBold = XmlUtil.getOhtMessage("ASSIGN_TIME_ALARM_BOLD2", (Object) null);

									if (reqAlarmBold.contains("Unknown ALARM CODE")) {
										reqAlarmBold = "-OHT에서 VHL을 선정하는 시간 증가가 감지되었습니다.";
									}

									alarmCmt = reqAlarmBold;
									alarmYn = "Y";
									alarmText = XmlUtil.getOhtMessage("ASSIGN_ALARM2"
											,currentAssignData
											,assignLimit
											,ohtRunRateValue
											,vhlRunRateLimitValue
											,mesCountPerMinData
											,assignCountPer10MinData
									);

//									System.out.println(alarmText);
								}
							}

							row.put("ALARM_DESC", alarmDesc);
							row.put("ALARM_CMT", alarmCmt);
							row.put("ALARM_MSG_CTN", alarmText);
							row.put("ALARM",alarmYn);
						} else if (msgType.equals("TRANSFERRING")) {
							//매분 TRANSFERRING TIME 평균
							String currentTransferringData = result.stream().filter(map -> "TRANSFERRING".equals(map.get("MESSAGE_TYP"))).map(map -> map.get("MESSAGE_TIME").toString()).collect(Collectors.joining(", "));
							//1시간 기준 분당 TRANSFERRING TIME 평균
							String mcsTimePerHour = result2.stream().filter(map -> "TRANSFERRING".equals(map.get("MESSAGE_TYP"))).map(map -> map.get("MESSAGE_TIME").toString()).collect(Collectors.joining(", "));
							String ohtRunRate = ohtRunRateList.stream().filter(map -> "FOUP".equals(map.get("CARRIERTYPE"))).map(map -> map.get("VHLOPERRATE").toString()).collect(Collectors.joining(", "));
							//매분 MES 반송큐 CNT
							String mesCountPerMinData = result3.stream().filter(map -> "M_MES".equals(map.get("TX"))).map(map -> map.get("MESSAGE_COUNT").toString()).collect(Collectors.joining(", "));
							String transferringCountPer10MinData = result4.stream().filter(map -> "TRANSFERRING".equals(map.get("MESSAGE_TYPE"))).map(map -> map.get("CNT").toString()).collect(Collectors.joining(", "));

							String alarmDesc = "";
							String alarmCmt = "";
							String alarmText = "";
							String alarmYn = "N";
							if (!currentTransferringData.isEmpty() && !mcsTimePerHour.isEmpty()) {
								double currentTransferringValue = Double.parseDouble(currentTransferringData.split(", ")[0]);
								double mcsTimePerHourRepValue = Double.parseDouble(mcsTimePerHour.split(", ")[0]);
								double ohtRunRateValue = Double.parseDouble(ohtRunRate.split(", ")[0]);

								double transferringLimitValue = Double.parseDouble(transferringLimit)/100;
								double validValue = mcsTimePerHourRepValue * transferringLimitValue;
								double vhlRunRateLimitValue = Double.parseDouble(vhlRunRateLimit);

								//1시간 평균과 현재값 차 계산
								double diffValue = ((currentTransferringValue-mcsTimePerHourRepValue)/currentTransferringValue)*100;
								boolean condition1 = currentTransferringValue >= validValue;
								boolean condition2 = ohtRunRateValue >= vhlRunRateLimitValue;
								if (condition1 && condition2) {

									//입력 변수 추가
									String ohtTimeAlarmName = XmlUtil.getOhtMessage("TRANSFERRING_TIME_ALARM_NAME", (Object) null);
									if(ohtTimeAlarmName.contains("Unknown ALARM CODE")) {
										ohtTimeAlarmName = "OHT의 반송 Time 증가";
									}
									alarmDesc = ohtTimeAlarmName;

									String reqAlarmBold = XmlUtil.getOhtMessage("TRANSFERRING_TIME_ALARM_BOLD", (Object) null);
									if(reqAlarmBold.contains("Unknown ALARM CODE")) {
										reqAlarmBold = "-OHT의 반송 Time 증가가 감지 되었습니다.";
									}
									alarmCmt = reqAlarmBold;

									alarmYn = "Y";

									alarmText = XmlUtil.getOhtMessage("TRANSFERRING_ALARM"
											,currentTransferringValue
											,transferringLimit
											,ohtRunRateValue
											,vhlRunRateLimitValue
											,mesCountPerMinData
											,transferringCountPer10MinData
											,mcsTimePerHour
											,diffValue
									);
								}else if(condition1){
									String ohtTimeAlarmName = XmlUtil.getOhtMessage("TRANSFERRING_TIME_ALARM_NAME", (Object) null);
									if(ohtTimeAlarmName.contains("Unknown ALARM CODE")) {
										ohtTimeAlarmName = "OHT의 반송 Time 증가";
									}
									alarmDesc = ohtTimeAlarmName;

									String reqAlarmBold = XmlUtil.getOhtMessage("TRANSFERRING_TIME_ALARM_BOLD2", (Object) null);
									if(reqAlarmBold.contains("Unknown ALARM CODE")) {
										reqAlarmBold = "-OHT의 반송 Time 증가가 감지 되었습니다.";
									}
									alarmCmt = reqAlarmBold;

									alarmYn = "Y";

									alarmText = XmlUtil.getOhtMessage("TRANSFERRING_ALARM2"
											,currentTransferringValue
											,transferringLimit
											,ohtRunRateValue
											,vhlRunRateLimitValue
											,mesCountPerMinData
											,transferringCountPer10MinData
									);
								}
							}
							row.put("ALARM_DESC", alarmDesc);
							row.put("ALARM_CMT", alarmCmt);
							row.put("ALARM_MSG_CTN", alarmText);
							row.put("ALARM",alarmYn);
						}
					} catch (Exception e) {
						logger.error("", e);
					}
				}
			}

			//누락 값 하드코딩으로 넣을 수 있도록 추가
			if (!result.isEmpty() && result.size() < 6) {
				for (Map<String, Object> map : result) {
					String msgTyp = map.get("MESSAGE_TYP").toString();

					foundTypes.add(msgTyp);
				}

				for (String requiredType : requiredTypes) {
					if (!foundTypes.contains(requiredType)) {
						Map<String, Object> newMap = new HashMap<>();

						newMap.put("MESSAGE_TYP", requiredType);
						newMap.put("TIME", result.get(0).get("TIME").toString());
						newMap.put("MACHINENAME", result.get(0).get("MACHINENAME").toString());
						newMap.put("MESSAGE_TIME", 0);
						newMap.put("ALARM", "N");
						newMap.put("IDC_NM","MIN");

						result.add(newMap);
					}
				}
			}

			//VHL 가동률 알람
		}catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}

	private void insertListData(List<Map<String, Object>> dataList, String logpressoTable) {
		if (dataList.isEmpty()) return;

		try {
			final List<Tuple> countList = new ArrayList<>();

			for(Map<String, Object> map : dataList) {
				final Tuple countMapSet = new Tuple();

				mapToTplConvert(map, countMapSet);
				countList.add(countMapSet);
			}
			LogpressoAPI.setInsertTuples(logpressoTable, countList,15);
		}catch (Exception e) {
			logger.error("",e);
		}
	}

	private void mapToTplConvert(final Map<String, Object> obj, final Tuple mapDataSet) {
		if (obj == null) return;

		for (Map.Entry<String, Object> entry : obj.entrySet()) {
			try {
				mapDataSet.put(entry.getKey(), entry.getValue().toString());
			} catch (Exception e) {
				logger.error("", e);
			}
		}
	}
}
