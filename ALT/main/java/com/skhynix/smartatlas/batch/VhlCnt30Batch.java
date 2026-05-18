package com.skhynix.smartatlas.batch;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.data.FabProperties;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.environment.type.FunctionItem;
import com.skhynix.smartatlas.process.OhtMsgWorkerRunnable.OHT_TIB_STATE;
import com.skhynix.smartatlas.service.TibrvService.SEND_SUB_SUBJECT;
import com.skhynix.smartatlas.util.DataService;
import com.skhynix.smartatlas.util.LayoutUtil;
import com.skhynix.smartatlas.util.Util;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

public class VhlCnt30Batch implements Job{
	Logger logger = LoggerFactory.getLogger(getClass());

	@Override
	public void execute(JobExecutionContext arg0) throws JobExecutionException {
//		if (DataService.getInstance() != null && DataService.getInstance().getInitialized()) {
		if (Util.isCurrentIC()) {
			for (FabProperties fabProperties : DataService.getInstance().getFabPropertiesMap().values()) {
				String fabId = fabProperties.getFabId();

				for (String mcpName : fabProperties.getMcpName2OhtNameMap().keySet()) {
					String key = fabId + ":" + mcpName;
					FunctionItem item = Env.getSwitchMap().get(key);

					if (item.isUseVhlCnt30()) {
						if (item.isUseVhlCnt() || item.isUseVhlCnt10() || item.isUseVhlCnt60()) {
							logger.warn("... `VhlCnt` at different timings of this fab information is allowed [fab: {} | mcp: {}]", fabId, mcpName);

							return;
						}

						logger.info("... `VhlCntBatch` has started [fab: {} | mcp: {}]", fabId, mcpName);

						long timer = System.currentTimeMillis();

						this._run(fabId, mcpName);

						logger.info("... `VhlCntBatch` has finished [fab: {} | mcp: {}] [elapsed time: {}ms]", fabId, mcpName, System.currentTimeMillis() - timer);
					}
				}
			}
		}
	}

	private void _run(String fabId, String mcpName) {
		final ConcurrentMap<String, Integer> recordMap = DataService.getDataSet().getHidVehicleCountMap();
		
		List<Tuple> logpressoData = new ArrayList<>();
		List<String> hid2VhlCntList = new ArrayList<>();
		String compareKey = fabId + ":" + mcpName;

		if (recordMap.isEmpty()) return;

		List<String> sortedKeys = recordMap.keySet().stream().sorted().collect(Collectors.toList());

		for (String key : sortedKeys) {
			String regex = "^(" + Pattern.quote(compareKey) + "):(.*)$";
			Pattern pattern = Pattern.compile(regex);
			Matcher matcher = pattern.matcher(key);

			if (matcher.matches()) {
				String extract = matcher.group(2);
				int hidId = Integer.parseInt(extract);
				int count = recordMap.get(key);

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
