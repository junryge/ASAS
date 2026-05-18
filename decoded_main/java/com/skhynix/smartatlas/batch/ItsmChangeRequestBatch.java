package com.skhynix.smartatlas.batch;

import java.io.FileInputStream;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.regex.Pattern;

import com.skhynix.smartatlas.util.Util;
import org.apache.commons.lang3.StringUtils;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.service.HttpService;
import com.skhynix.smartatlas.util.XmlUtil;

public class ItsmChangeRequestBatch implements Job {
	private final Logger logger = LoggerFactory.getLogger(getClass());

	private static final String _SettingsPropertiesPath = String.format(
			"%s/Settings.properties",
			System.getProperty("SMARTFX_REPOSITORY")
	);

	private static String ITSM_POST_URL = "";
	private static String ITSM_POST_ID = "";
	private static String ITSM_POST_PW = "";
	private LocalDateTime eventDateTime = null;

	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		final int DELAYED_TIME = 1000 * 60;

		if (Util.isCurrentIC()) {
			logger.info("... `ItsmChangeRequestBatch` has started");

			long timer = System.currentTimeMillis();

			this._run();

			long checkTimer = System.currentTimeMillis() - timer;

			if (checkTimer >= DELAYED_TIME) {
				logger.error("... !!!DELAYED!!! `ItsmChangeRequestBatch` has finished [elapsed time: {}m ({}ms)]", checkTimer / (60 * 1000), checkTimer);
			} else {
				logger.info("... `ItsmChangeRequestBatch` has finished [elapsed time: {}ms]", checkTimer);
			}
		}
	}

	private void _int() {
		this.eventDateTime = LocalDateTime.now();
	}

	private void _run() {
		this._int();

		try {
			List<Map<String, Object>> itemList = _getParseITSMValue();

			if (!itemList.isEmpty()) {
				List<Tuple> logpressoData = XmlUtil.convert(itemList);

				QTransferDashBoardItemBatch.insertLogpressoData(logpressoData);
			}
		} catch (Exception e) {
			logger.error("",e);
		}
	}

	private List<Map<String, Object>> _getParseITSMValue() {
		List<Map<String, Object>> result = new ArrayList<>();
		Properties properties = new Properties();
		FileInputStream stream;

		try {
			stream = new FileInputStream(_SettingsPropertiesPath);

			properties.load(stream);

			this._loadProperties(properties);
// ---------------------------------------------------------------------------------------------------------------------
			Map<String, Object> payload = new HashMap<>();
			DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd");
			String nowDateTime = this.eventDateTime.format(formatter);

			payload.put("table_name", "change_request");
			payload.put("search_type", "build");
			payload.put("date_from", nowDateTime);
			payload.put("date_to", nowDateTime);
			payload.put("cloumn",
					"business_service,short_description,state,u_change_type,u_system_admin,u_system_admin,u_expected_due_date,u_workforce_dept");
// ---------------------------------------------------------------------------------------------------------------------
			Map<String, Object> header = new HashMap<>();

			// Base64 인코딩
			String authString = ITSM_POST_ID + ":" + ITSM_POST_PW;
			String encodedAuthString = Base64.getEncoder().encodeToString(authString.getBytes());

			header.put("Authorization", "Basic " + encodedAuthString);
			header.put("Content-Type", "application/json");
// ---------------------------------------------------------------------------------------------------------------------
			Map<String, Object> response	= HttpService.post(ITSM_POST_URL, payload, header);
			Map<String, Object> resultData	= (Map<String, Object>) response.get("result");
			List<Map<String, Object>> data	= (List<Map<String, Object>>) resultData.get("data");

			// 시스템 필터 동적 관리
			String checkSystemList = XmlUtil.getVariableEnv("ITSM_CHANGE_SYSTEM_NAME",(Object) null);

			if (checkSystemList.contains("Unknown ALARM CODE")) {
				checkSystemList = "MCS|MES|MCP|RTD|RTS";
			}

			Pattern pattern = Pattern.compile(checkSystemList);

			if (!data.isEmpty()) {
				for (Map<String, Object> map : data) {
					Map<String, Object> changeRequest = new HashMap<>();
					String systemName = map.get("business_service").toString();

					if (pattern.matcher(systemName).find()) {
						String operActCtn = map.get("short_description").equals("null") ? ""
								: map.get("short_description").toString();

						String jobStat = map.get("state").equals("null") ? "" : map.get("state").toString();

						String jobTyp = map.get("u_change_type").equals("null") ? "" : map.get("u_change_type").toString();

						String dueGbnCd = map.get("u_expected_due_date").equals("null") ? ""
								: map.get("u_expected_due_date").toString();

						String adminUserId = map.get("u_system_admin").equals("null") ? ""
								: map.get("u_system_admin").toString();

						String deptNm = map.get("u_workforce_dept").equals("null") ? ""
								: map.get("u_workforce_dept").toString();

						changeRequest.put("JOB_SYS_ID", systemName);
						changeRequest.put("TYP", "WORKLOG");
						changeRequest.put("OPER_ACT_CTN", "[" + systemName + "] " + operActCtn);
						changeRequest.put("VAL", 0);
						changeRequest.put("JOB_STAT", jobStat);
						changeRequest.put("JOB_TYP", jobTyp);
						changeRequest.put("DUE_GBN_CD", dueGbnCd);
						changeRequest.put("ADMIN_USER_ID", adminUserId);
						changeRequest.put("DEPT_NM", deptNm);

						result.add(changeRequest);
					}
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		if (!result.isEmpty()) {
			DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd");
			String eventDt = this.eventDateTime.format(formatter) + "0000";

			for (Map<String, Object> row : result) {
				// EVENT_DT 값 동기화
				row.put("EVENT_DT", eventDt);

				// REST APP 에서 EXPECTED DATE 값 없이 와서 오늘 날짜로 넣을 수 있도록 수정
				row.put("DUE_GBN_CD", eventDt);
			}
		}

		return result;
	}

	private void _loadProperties(final Properties properties) {
		String baseName		= "ITSM.POST";
		String url 			= properties.getProperty(baseName + ".Url");
		String id 			= properties.getProperty(baseName + ".Id");
		String password 	= properties.getProperty(baseName + ".Password");

		if (!StringUtils.isAnyBlank(url, id, password)) {
			ITSM_POST_URL 	= url;
			ITSM_POST_ID 	= id;
			ITSM_POST_PW 	= password;
		}
	}
}