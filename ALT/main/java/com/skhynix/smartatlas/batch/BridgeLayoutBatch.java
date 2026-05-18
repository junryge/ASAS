package com.skhynix.smartatlas.batch;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.Map.Entry;
import java.util.function.Function;
import java.util.stream.Collectors;

import com.skhynix.smartatlas.util.Util;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.util.FilePathUtil;
import com.skhynix.smartatlas.util.XmlUtil;


public class BridgeLayoutBatch implements Job{
	private final Logger logger 	= LoggerFactory.getLogger(getClass());
	private final int DELAYED_TIME	= 1000 * 60;

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
			//예약쿼리로 적재되는 데이터 조회
			List<Map<String, Object>> dataList = this._getBridgeLayoutList();

			//판단 테이블 범위 비교
			List<Map<String, Object>> detectData = this._detectAnomaly(dataList);

			//OFS ,HUBROOM 추가
			List<Map<String, Object>> topBarData = _getBridgeLayoutTopbarList();

			detectData.addAll(topBarData);

			Map<Object, List<Map<String, Object>>> groupData = detectData.stream()
					.collect(
							Collectors.groupingBy(row -> row.get("EVENT_DT") + "|"
									+ row.get("FR_FAB_ID") + "|"
									+ row.get("TO_FAB_ID") + "|"
									+ row.get("IDC_NM")
							));

			for (Entry<Object, List<Map<String, Object>>> entry : groupData.entrySet()) {
				List<Map<String, Object>> groupRows = entry.getValue();

				for(Map<String, Object> row : groupRows) {
					try {
						if(row.get("WARN_YN").toString().equals("Y")) { // 판단값 Y 일 경우
							String sigmaStr = XmlUtil.getVariableEnv("LAYOUT_SIGMA", (Object) null);

							if(sigmaStr.contains(XmlUtil.DEFAULT_VALUE)) {
								sigmaStr = "3";
							}

							String alarmText = XmlUtil.getMessage(
									"LAYOUT_ALARM",
									row.get("FR_FAB_ID").toString(),
									row.get("TO_FAB_ID").toString(),
									sigmaStr
							);

							row.put("ALARM_MSG", alarmText);
						} else {
							row.put("ALARM_MSG", "");
						}
					} catch (Exception e) {
						logger.error("", e);
					}
				}
			}

			LocalDateTime now 			= LocalDateTime.now();
			DateTimeFormatter formatter	= DateTimeFormatter.ofPattern("yyyyMMddHHmm");
			String eventDt 				= now.format(formatter);

			for (Map<String, Object> row :  detectData) {
				// EVENT_DT 값 동기화
				row.put("EVENT_DT", eventDt);
			}

			List<Tuple> logpressoData = XmlUtil.convert(detectData);

			Util.insertInLogpressoDatabase(logpressoData, "bridge_layout_test", this.getClass().getSimpleName());
		} catch (Exception e) {
			logger.error("", e);
		}
	}

	private List<Map<String, Object>> _getBridgeLayoutList(){
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<>();

		try {
			//조회 시점 개선
			Thread.sleep(1000);

			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "bridgeLayout");

			sQuery.append(strQuery);

			result = LogpressoAPI.responseResult(sQuery.toString());

			//조회 시점에 데이터 없을 경우 개선
			if (result.size() < 27) { // 지표 27개 이하인 경우 재조회
				result = new ArrayList<>();//초기화
				result = LogpressoAPI.responseResult(sQuery.toString());
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info("Search Result Size : {}", result.size());

		return result;
	}

	private List<Map<String, Object>> _getBridgeLayoutTopbarList(){
		List<Map<String, Object>> result = new ArrayList<>();

		try {
			List<Map<String, Object>> resVal = XmlUtil.selectLogpressoQuery("bridgeLayout2");

			logger.info("Bridge TopBar List Size : {}" , resVal.size());

			for (Map<String, Object> data : resVal) {
				String flow = data.get("FLOW") == null ? "" : data.get("FLOW").toString().trim();

				if (flow.isEmpty()) continue;

				if (flow.contains("CURRENT_M16A_3F_JOB")) {
					HashMap<String, Object> cloneMap = new HashMap<>(data);

					//14->16
					data.put("FR_FAB_ID", "M14");
					data.put("FR_LOC_NM", "M14");
					data.put("TO_FAB_ID", "M16");
					data.put("TO_LOC_NM", "M16");
					data.put("IDC_NM", "CD_HUBROOM");

					data.remove("FLOW");

					result.add(data);

					//16->14
					cloneMap.put("FR_FAB_ID", "M16");
					cloneMap.put("FR_LOC_NM", "M16");
					cloneMap.put("TO_FAB_ID", "M14");
					cloneMap.put("TO_LOC_NM", "M14");
					cloneMap.put("IDC_NM", "CD_HUBROOM");

					cloneMap.remove("FLOW");

					result.add(cloneMap);
				} else if (
						flow.contains("M16_TO_M14_OFS")
								|| flow.contains("M14_TO_M16_OFS")
				) {
					// OFS
					if (flow.startsWith("M14")) {
						data.put("FR_FAB_ID", "M14");
						data.put("FR_LOC_NM", "M14");
						data.put("TO_FAB_ID", "M16");
						data.put("TO_LOC_NM", "M16");
						data.put("IDC_NM", "CD_OFS");

						data.remove("FLOW");

						result.add(data);
					} else {
						data.put("FR_FAB_ID", "M16");
						data.put("FR_LOC_NM", "M16");
						data.put("TO_FAB_ID", "M14");
						data.put("TO_LOC_NM", "M14");
						data.put("IDC_NM", "CD_OFS");

						data.remove("FLOW");

						result.add(data);
					}
				} else if (flow.contains("OFS_TOTAL_LIMIT_CNT")) { //OFS LIMIT COUNT
					String[] fabFlow = flow.split("_");

					if (flow.startsWith("M16")) {
						data.put("FR_FAB_ID", "M16");
						data.put("FR_LOC_NM", "M16");
						data.put("TO_FAB_ID", fabFlow[1]);
						data.put("TO_LOC_NM", fabFlow[1]);
						data.put("IDC_NM", "CD_OFS_TOTAL_LIMIT_CNT");

						data.remove("FLOW");

						result.add(data);
					} else {
						data.put("FR_FAB_ID", fabFlow[0]);
						data.put("FR_LOC_NM", fabFlow[0]);
						data.put("TO_FAB_ID", "M16");
						data.put("TO_LOC_NM", "M16");
						data.put("IDC_NM", "CD_OFS_TOTAL_LIMIT_CNT");

						data.remove("FLOW");

						result.add(data);
					}
				} else if (flow.contains("HUBROOM_PREDICT")){
// ---------------------------------------------------------------------------------------------------------------------
					// hub-room prediction
					HashMap<String, Object> cloneMap = new HashMap<>(data);

					switch (flow) {
						case "HUBROOM_PREDICT": {
							result.addAll(this._buildRow("CD_HUBROOM_P", data, cloneMap));
						} break;
						case "HUBROOM_PREDICT_15MIN": {
							result.addAll(this._buildRow("CD_HUBROOM_P15", data, cloneMap));
						} break;
						case "HUBROOM_PREDICT_20MIN": {
							result.addAll(this._buildRow("CD_HUBROOM_P20", data, cloneMap));
						} break;
						case "HUBROOM_PREDICT_25MIN": {
							result.addAll(this._buildRow("CD_HUBROOM_P25", data, cloneMap));
						} break;
						case "HUBROOM_PREDICT_30MIN": {
							result.addAll(this._buildRow("CD_HUBROOM_P30", data, cloneMap));
						} break;
						case "HUBROOM_PREDICT_35MIN": {
							result.addAll(this._buildRow("CD_HUBROOM_P35", data, cloneMap));
						} break;
					}
// ---------------------------------------------------------------------------------------------------------------------
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		return result;
	}

	private List<Map<String, Object>> _buildRow(
			String flow,
			Map<String, Object> data,
			Map<String, Object> cloneMap
	) {
		List<Map<String, Object>> result = new ArrayList<>();

		//14->16
		data.put("FR_FAB_ID", "M14");
		data.put("FR_LOC_NM", "M14");
		data.put("TO_FAB_ID", "M16");
		data.put("TO_LOC_NM", "M16");
		data.put("IDC_NM", flow);

		data.remove("FLOW");

		result.add(data);

		//16->14
		cloneMap.put("FR_FAB_ID", "M16");
		cloneMap.put("FR_LOC_NM", "M16");
		cloneMap.put("TO_FAB_ID", "M14");
		cloneMap.put("TO_LOC_NM", "M14");
		cloneMap.put("IDC_NM", flow);

		cloneMap.remove("FLOW");

		result.add(cloneMap);

		return result;
	}

	private List<Map<String,Object>> _detectAnomaly(List<Map<String,Object>> dataList){
		List<Map<String, Object>> result = new ArrayList<>();

		try {
			List<Map<String, Object>> judgeRange;

			try {
				judgeRange = XmlUtil.selectLogpressoQuery("bridgeJudgeRange");
			} catch (Exception e) {
				logger.error("Error loading judge range data", e);

				return result;
			}

			// judgeRange 를 Map 으로 변환하여 빠른 조회 가능하도록 함
			Map<String, Map<String, Object>> judgeRangeMap = judgeRange.stream()
					.collect(Collectors.toMap(
							row -> row.get("FR_FAB_ID") + "|" + row.get("TO_FAB_ID") + "|"
									+ row.get("IDC_NM") + "|" + row.get("FR_LOC_NM") + "|" + row.get("TO_LOC_NM"),
							Function.identity()
					));

			for (Map<String, Object> data : dataList) {
				String idcNm = data.get("IDC_NM").toString();
				// IDC_NM 이 "STORAGE" 또는 "CPT"를 포함하는 경우 건너뛰기
				if (idcNm.contains("STORAGE") || idcNm.contains("CPT")) {
					data.put("WARN_YN", "N");
//	            	 data.put("ALARM_YN", "N");
					result.add(data);
					continue;
				}

				String key = data.get("FR_FAB_ID") + "|" + data.get("TO_FAB_ID") + "|"
						+ data.get("IDC_NM") + "|" + data.get("FR_LOC_NM") + "|" + data.get("TO_LOC_NM");
				Map<String, Object> range = judgeRangeMap.get(key);

				if (range != null) {
					double currVal = Double.parseDouble(data.get("CURR_VAL").toString());
					double lowerVal = Double.parseDouble(range.get("LOWER_VAL").toString());
					double upperVal = Double.parseDouble(range.get("UPPER_VAL").toString());

					if (currVal < lowerVal || currVal > upperVal) {
						data.put("WARN_YN", "Y");
//	                    data.put("ALARM_YN", "Y");
					} else {
						data.put("WARN_YN", "N");
//	                    data.put("ALARM_YN", "N");
					}
				} else {
					// judgeRange에 해당하는 데이터가 없을 경우 WARN_YN 을 N으로 설정
					data.put("WARN_YN", "N");
//	                data.put("ALARM_YN", "N");
				}
				result.add(data);
			}
		} catch (Exception e) {
			logger.error("Error detecting anomaly", e);
		}

		return result;
	}
}
