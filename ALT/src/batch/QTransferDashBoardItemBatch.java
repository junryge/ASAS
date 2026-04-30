public class QTransferDashBoardItemBatch implements Job{
	private final Logger logger = LoggerFactory.getLogger(getClass());
	private LocalDateTime eventDateTime;

	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		final int DELAYED_TIME = 1000 * 60;

		if (Util.isCurrentIC()) {
			logger.info("... `QTransferDashBoardItemBatch` has started");

			long timer = System.currentTimeMillis();

			this._run();

			long checkTimer = System.currentTimeMillis() - timer;

			if (checkTimer >= DELAYED_TIME) {
				logger.error("... !!!DELAYED!!! `QTransferDashBoardItemBatch` has finished [elapsed time: {}m ({}ms)]", checkTimer / (60 * 1000), checkTimer);
			} else {
				logger.info("... `QTransferDashBoardItemBatch` has finished [elapsed time: {}ms]", checkTimer);
			}
		}
	}

	private void _init() {
		this.eventDateTime = LocalDateTime.now();
	}

	private void _run() {
		this._init();
		List<Map<String, Object>> finalList = new ArrayList<>();

		try {
			// 1. MES 반송지시 Req 비율
			List<Map<String, Object>> requestorList = _buildRequestor();

			// 2. MCS ERROR LOG
			List<Map<String, Object>> errorLogList = _buildMcsErrorLogCount();

			// 3. 예측값 오차 계산
			List<Map<String, Object>> quePredictErrorList = _buildTransQuePredictError();

			finalList.addAll(requestorList);
			finalList.addAll(errorLogList);
			finalList.addAll(quePredictErrorList);

			DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMddHHmm");
			String eventDateTimeString = this.eventDateTime.format(formatter);

			if (finalList.isEmpty()) {
				logger.error("... built data with `QTransferDashBoardItemBatch` is empty");

				return;
			}

			for (Map<String, Object> row :  finalList) {
				// EVENT_DT 값 동기화
				row.put("EVENT_DT", eventDateTimeString);
				row.put("DUE_GBN_CD", eventDateTimeString);
			}

			List<Tuple> logpressoData = XmlUtil.convert(finalList);

			QTransferDashBoardItemBatch.insertLogpressoData(logpressoData);
		} catch (Exception e) {
			logger.error("", e);
		}
	}

	public static void insertLogpressoData(List<Tuple> list) {
		final String tableName = "qtransfer_dashboard";
		final Logger logger = LoggerFactory.getLogger(QTransferDashBoardItemBatch.class);

		if (list.isEmpty()) {
			logger.error("... selected data is empty [table={}]", tableName);
		} else {
			if (LogpressoAPI.setInsertTuples(tableName, list, 15)) {
				logger.info("... selected data has been inserted in logpresso database [size: {}] [table={}]", list.size(), tableName);
			} else {
				logger.error("... selected data is not inserted in logpresso database [size: {}] [table={}]", list.size(), tableName);
			}
		}
	}

	private List<Map<String,Object>> _buildRequestor(){
		List<Map<String, Object>> queryData;

		try {
			String requestorList = XmlUtil.getVariableEnv("QTRANSFER_REQUESTOR_LIST", (Object) null);

			if (requestorList.contains(XmlUtil.DEFAULT_VALUE)) {
				requestorList = "\"MHS\",\"RTD/RTS\",\"EIS\"";
			}

			//도넛 차트 REQUEST 수량
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "requestorCount");
			strQuery = strQuery.replace("SEARCHSYSTEM", requestorList);
			queryData = LogpressoAPI.responseResult(strQuery);
		} catch (Exception e) {
			logger.error("", e);

			return new ArrayList<>();
		}

		return this._buildMap("REQUESTOR", "REQUESTOR_CNT", "REQUESTOR", queryData);
// [{REQUESTOR=EIS, REQUESTOR_CNT=186}, {REQUESTOR=ETC, REQUESTOR_CNT=10}, {REQUESTOR=MHS, REQUESTOR_CNT=21}, {REQUESTOR=RTD/RTS, REQUESTOR_CNT=29}]
// 테이블 파싱 기능 추가 필요
	}

	private List<Map<String,Object>> _buildMcsErrorLogCount() {
		List<Map<String, Object>> queryData;

		try {
			queryData = XmlUtil.selectLogpressoQuery2("mcsErrorLogCnt");
		} catch (Exception e) {
			logger.error("", e);

			return new ArrayList<>();
		}

		return this._buildMap("LEVEL", "CNT", "WARNINGLOG", queryData);
	}

	private List<Map<String, Object>> _buildTransQuePredictError() {
		List<Map<String, Object>> queryData;

		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, "quePredictError");
			queryData = LogpressoAPI.responseResult(strQuery);
		} catch (Exception e) {
			logger.error("", e);

			return new ArrayList<>();
		}

		return this._buildMap("ERROR", queryData);
	}
	// =====================================================================================================================
	private List<Map<String, Object>> _buildMap(String type, List<Map<String, Object>> queryData) {
		List<Map<String, Object>> result = new ArrayList<>();

		for (Map<String, Object> row : queryData) {
			for (Map.Entry<String, Object> entry : row.entrySet()) {
				Map<String, Object> data = this._getMapData(entry.getKey(), entry.getValue(), type);

				result.add(data);
			}
		}

		return result;
	}

	private List<Map<String, Object>> _buildMap(
			String contentFieldName,
			String valueFieldName,
			String type,
			List<Map<String, Object>> queryData
	) {
		List<Map<String, Object>> result = new ArrayList<>();

		for (Map<String, Object> row : queryData) {
			String operatorActionContent
					= row.get(contentFieldName) == null ? null : row.get(contentFieldName).toString();

			String value = row.get(valueFieldName) == null ? null : row.get(valueFieldName).toString();

			if (operatorActionContent == null || value == null) {
				return new ArrayList<>();
			}

			Map<String, Object> data = this._getMapData(operatorActionContent, value, type);

			result.add(data);
		}

		return result;
	}

	private Map<String, Object> _getMapData(String operatorActionContent, Object value, String type) {
		Map<String, Object> result = new HashMap<>();

		result.put("OPER_ACT_CTN", operatorActionContent);
		result.put("VAL", value);
		result.put("TYP", type);
		result.put("JOB_STAT", "");
		result.put("JOB_TYP", "");
		result.put("DUE_GBN_CD", "");
		result.put("ADMIN_USER_ID", "");
		result.put("DEPT_NM", "");
		result.put("JOB_SYS_ID", "");

		return result;
	}
}
