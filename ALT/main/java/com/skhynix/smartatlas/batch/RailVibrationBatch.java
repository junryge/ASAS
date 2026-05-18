package com.skhynix.smartatlas.batch;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentMap;

import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.data.RailVibrationRecordItem;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.process.OhtMsgWorkerRunnable.OHT_TIB_STATE;
import com.skhynix.smartatlas.service.TibrvService.SEND_SUB_SUBJECT;
import com.skhynix.smartatlas.util.DataService;
import com.skhynix.smartatlas.util.LayoutUtil;
import com.skhynix.smartatlas.util.Util;
import com.skhynix.smartfx.dataaccessfx.DataRow;
import com.skhynix.smartfx.dataaccessfx.DataTable;
import com.skhynix.smartfx.dataaccessfx.QueryExecutor;
import com.skhynix.smartfx.dataaccessfx.QueryExecutorFactory;

public class RailVibrationBatch implements Job{
	private final Logger logger = LoggerFactory.getLogger(getClass());

	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		final int DELAYED_TIME = 1000 * 60;

		if (Util.isCurrentIC()) {
			var appProperties = Env.getFabsetProperties();

			if ("TRUE".equals(appProperties.getProperty("CMN.CMN.RAIL_VIBRATION"))) {
				logger.info("... `RailVibrationBatch` has started");

				long timer = System.currentTimeMillis();

				this._run();

				long checkTimer = System.currentTimeMillis() - timer;

				if (checkTimer >= DELAYED_TIME) {
					logger.error("... !!!DELAYED!!! `RailVibrationBatch` has finished [elapsed time: {}m ({}ms)]", checkTimer / (60 * 1000), checkTimer);
				} else {
					logger.info("... `RailVibrationBatch` has finished [elapsed time: {}ms]", checkTimer);
				}
			}
		}
	}

	/*
	 * 기능 동작 이후 테스트 코드를 실행해 해당 기능이 정상 동작 중인지 확인
	 *  ### 사용 가능한 factory ###
	 *	#	M15 3F (M15A)		#
	 *	#	M16 6F(M16A)		#
	 *	#	M16 EUV(M16E)		#
	 *	#	M16 Bri(M16 HUB)	#
	 *	#	M16 10F(M16B)		#
	 *	#	M15 7F(M15B)		#
	 *	#########################
	 */
	private void _run() {
		/*
		해당 배치는 사용 가능한 factory 가 한정되어 있기 때문에 `FabSet.properties` 에 정의된 factory 가 아닌 별도의 값을 요구

			_run() -> _selectQuery() -> _parsing() -> _checkNormalState() -> <logpressoApi> -> _sendMessage()
		 */
//		for (FabProperties fabProperties : DataService.getInstance().getFabPropertiesMap().values()) {
//			String facId = fabProperties.getFacId();
//			String mcpName = fabProperties.getMcpName();
		List<RailVibrationRecordItem> dataList = this._selectQuery();

		if (dataList != null && !dataList.isEmpty()) {
			Map<String, RailVibrationRecordItem> dataMap = new HashMap<>();

			for (RailVibrationRecordItem item : dataList) {
				String key = item.getId();

				dataMap.put(key, item);
			}

			List<RailVibrationRecordItem> normalDataList = this._checkNormalState(dataMap.keySet());

			dataList.addAll(normalDataList);

			if (this._insertLogpresso(dataList)) {
				logger.info("... vibration logpresso insert success");
			} else {
				logger.warn("... vibration logpresso insert fail !");
			}

			for (RailVibrationRecordItem item : dataList) {
				Map<String, String> _t = LayoutUtil.buildLayoutMessageDataMap(item);

				if (this._sendMessage(_t)) {
					DataService.getDataSet().getRailVibrationRecordMap().remove(item.getId());
				}
			}
		} else {
			this._insertLogpresso(null);
		}
//		}
	}

	//	private List<RailVibrationRecordItem> _selectQuery (String facId, String mcpName) {
	private List<RailVibrationRecordItem> _selectQuery () {
//		String fabId = facId + mcpName;

//		try (QueryExecutor executor = QueryExecutorFactory.build("IOT_" + (fabId))) {
		try (QueryExecutor executor = QueryExecutorFactory.build("IOT_M16A")) {
			Map<String, String> parameter = new HashMap<>();

//			parameter.put(FAB_ID, fabId);
//			parameter.put(FAC_ID, facId);
			parameter.put(FAB_ID, "M16A");
			parameter.put(FAC_ID, "M16");

			DataTable queryData = executor.selectDataTable("SELECT_VIBRATION", parameter);

			return _parsing(queryData);
		} catch (Exception e) {
			logger.error("... An error occurred while searching query of vibration !!!", e);
		}

		return null;
	}

	// parsing the query data
	private List<RailVibrationRecordItem> _parsing(DataTable dataTable) {
		List<RailVibrationRecordItem> result = new ArrayList<>();

		for (DataRow dataRow : dataTable.getRows()) {
			Map<String, Object> row = new HashMap<>();

			for (int i = 0; i < dataTable.columnCount(); i++) {
				String columnName = dataTable.getColumn(i).getName();

				row.put(columnName, dataRow.get(i));
			}

			String fabId = row.getOrDefault(FAB_ID, "").toString();
			String address = row.getOrDefault(ADDRESS, "").toString();
			String key = fabId + ":" + address;
			String dir = row.getOrDefault(DIR, "").toString();
			List<String> directory = Arrays.asList(dir.split(","));

			RailVibrationRecordItem item = new RailVibrationRecordItem(
					key,
					fabId,
					row.getOrDefault(FAC_ID, "").toString(),
					Integer.parseInt(row.getOrDefault(ADDRESS, "-1").toString()),
					_parseDouble(row.getOrDefault(X, "-1")),
					_parseDouble(row.getOrDefault(Y, "-1")),
					_parseDouble(row.getOrDefault(Z, "-1")),
					_parseDouble(row.getOrDefault(AVG_X, "-1")),
					_parseDouble(row.getOrDefault(AVG_Y, "-1")),
					_parseDouble(row.getOrDefault(AVG_Z, "-1")),
					_parseDouble(row.getOrDefault(TERM1, "-1")),
					_parseDouble(row.getOrDefault(TERM2, "-1")),
					directory,
					row.getOrDefault(STATE, OHT_TIB_STATE.ABNORMAL).toString()
			);

			result.add(item);
		}

		return result;
	}

	private double _parseDouble(Object obj) {
		try {
			return Double.parseDouble(obj.toString());
		} catch (NumberFormatException e) {
			return -1;
		}
	}

	/**
	 *
	 * @param keys key of query data
	 * @return normal state data
	 */
	private List<RailVibrationRecordItem> _checkNormalState(Set<String> keys) {
		List<RailVibrationRecordItem> result = new ArrayList<>();
		ConcurrentMap<String, RailVibrationRecordItem> recordMap = DataService.getDataSet().getRailVibrationRecordMap();

		if (!recordMap.isEmpty()) {
			Set<String> recordKeys = recordMap.keySet();

			for (String key : recordKeys) {
				if (!keys.contains(key)) {
					// normal 로 전환 ---> 마지막 과정(데이터 저장) 이후 normal 인 데이터는 삭제
					recordMap.get(key).setState(OHT_TIB_STATE.NORMAL);

					result.add(recordMap.get(key));
				}
			}
		}

		return result;
	}

	// send tib/rv message
	private <T> boolean _sendMessage (Map<String, T> dataMap) {
//		String fabId = dataMap.get("FAB_ID").toString();
		String fabId = "M14A";

		for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:").keySet()) {
			try {
				DataService.getInstance().addTibrvMessageQueue(tibrvKey, SEND_SUB_SUBJECT.RAIL_VIBRATION, dataMap);
			} catch (Exception e) {
				logger.error("... An error occurred while adding message queue !!!", e);

				return false;
			}
		}

		return true;
	}

	/**
	 * save normal/abnormal data with logpresso database
	 * @param list parsed the data
	 */
	private boolean _insertLogpresso(List<RailVibrationRecordItem> list) {
		if (list != null && !list.isEmpty()) {
			List<Tuple> logpressoData = this._getTupleList(list);

			if (!logpressoData.isEmpty()) {
				try {
					LogpressoAPI.setInsertTuples("ATLAS_OHT_RAIL_VIBRATION", logpressoData, 20);

					return true;
				} catch (Exception e) {
					logger.error("... An error occurred while inserting logpresso data !!!", e);
				}
			}
		} else {
			LogpressoAPI.setInsertTuples("ATLAS_OHT_RAIL_VIBRATION", this._getTupleList(null), 20);
		}

		return false;
	}

	private List<Tuple> _getTupleList(List<RailVibrationRecordItem> list) {
		List<Tuple> result = new ArrayList<>();

		if (list != null && !list.isEmpty()) {
			for (RailVibrationRecordItem data : list) {
				Tuple tuple = new Tuple();

				tuple.put(FAB_ID, data.getFabId());
				tuple.put(ADDRESS, data.getAddress());
				tuple.put(DIR, String.join(",", data.getDirectory()));
				tuple.put(X, data.getX());
				tuple.put(Y, data.getY());
				tuple.put(Z, data.getZ());
				tuple.put(AVG_X, data.getAvgX());
				tuple.put(AVG_Y, data.getAvgY());
				tuple.put(AVG_Z, data.getAvgZ());
				tuple.put(TERM1, data.getTerm1());
				tuple.put(TERM2, data.getTerm2());
				tuple.put(STATE, data.getState());

				result.add(tuple);
			}
		} else {
			Tuple tuple = new Tuple();

			tuple.put(FAB_ID, "");
			tuple.put(ADDRESS, "");
			tuple.put(DIR, "");
			tuple.put(X, "");
			tuple.put(Y, "");
			tuple.put(Z, "");
			tuple.put(AVG_X, "");
			tuple.put(AVG_Y, "");
			tuple.put(AVG_Z, "");
			tuple.put(TERM1, "");
			tuple.put(TERM2, "");
			tuple.put(STATE, "");

			return List.of(tuple);
		}

		return result;
	}

	// dataTable column key
	private final String FAB_ID = "FAB_ID";
	private final String FAC_ID = "FAC_ID";
	private final String ADDRESS = "ADDRESS";
	private final String X = "X";
	private final String Y = "Y";
	private final String Z = "Z";
	private final String TERM1 = "TERM1";
	private final String TERM2 = "TERM2";
	private final String AVG_X = "AVG_X";
	private final String AVG_Y = "AVG_Y";
	private final String AVG_Z = "AVG_Z";
	private final String DIR = "DIR";
	private final String STATE = "STATE";
}