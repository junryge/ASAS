public class OhtPerformanceTimeHourBatch implements Job{
	private final Logger logger = LoggerFactory.getLogger(getClass());

	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		final int DELAYED_TIME = 1000 * 60;

		if (Util.isCurrentIC()) {
			logger.info("... `OhtPerformanceTimeHourBatch` has started");

			long timer = System.currentTimeMillis();

			this._run();

			long checkTimer = System.currentTimeMillis() - timer;

			if (checkTimer >= DELAYED_TIME) {
				logger.error("... !!!DELAYED!!! `OhtPerformanceTimeHourBatch` has finished [elapsed time: {}m ({}ms)]", checkTimer / (60 * 1000), checkTimer);
			} else {
				logger.info("... `OhtPerformanceTimeHourBatch` has finished [elapsed time: {}ms]", checkTimer);
			}
		}
	}

	private void _run() {
		try {
			//Oht Performance Time 매시간 1분 마다 적재 하는 데이터
			//4. 시간당 메세지 수
			List<Map<String, Object>> messageCountHourList = getMessageCountHourList();

			//5. 시간당 메세지 시간
			List<Map<String, Object>> getMessageTimeHourList = getMessageTimeHourList();


			LocalDateTime now = LocalDateTime.now();
			DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:00");
			String formattedDateTime = now.format(formatter);

			for(Map<String,Object> map : messageCountHourList) {
				map.put("TIME", formattedDateTime);
			}
			for(Map<String,Object> map : getMessageTimeHourList) {
				map.put("TIME", formattedDateTime);
			}

			insertListData(messageCountHourList, "oht_cmd_count");
			insertListData(getMessageTimeHourList, "oht_time_avg");
		}catch (Exception e) {
			logger.error("",e);
		}
	}

	public List<Map<String, Object>> getMessageCountHourList(){
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String,Object>>();
		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "msgCountPerHour");

			sQuery.append(strQuery);
			result = LogpressoAPI.responseResult(strQuery.toString());
		}catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}

	public List<Map<String, Object>> getMessageTimeHourList(){
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String,Object>>();

		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "msgTimePerHour");

			sQuery.append(strQuery);
			result = LogpressoAPI.responseResult(strQuery.toString());


			Map<String, Object> resMap = new HashMap<String, Object>();
			String[] strArr = {"REP","ASSIGN","ACQUIRED","TRANSFERRING","DESPOSITED","COMPLETED"};
			Set<String> requiredTypes = new HashSet<>(Arrays.asList(strArr));
			Set<String> foundTypes = new HashSet<>();

			if(result.size() > 0) {
				if(result.size() < 6) {
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
							newMap.put("IDC_NM","HOUR");
							result.add(newMap);
						}
					}
				}
			}
		}catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}

	public void insertListData(List<Map<String, Object>> dataList, String logpressoTable) {
		try {
			if(dataList.size() > 0) {
				final List<Tuple> countList = new ArrayList<Tuple>();

				for(Map<String, Object> map : dataList) {
					final Tuple countMapSet = new Tuple();

					mapToTplConvert(map, countMapSet);
					countList.add(countMapSet);
				}
				LogpressoAPI.setInsertTuples(logpressoTable, countList,15);
			}
		}catch (Exception e) {
			logger.error("",e);
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
