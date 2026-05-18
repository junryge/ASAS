package com.skhynix.smartatlas.batch;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.data.*;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.environment.type.FunctionItem;
import com.skhynix.smartatlas.process.OhtMsgWorkerRunnable.OHT_TIB_STATE;
import com.skhynix.smartatlas.util.*;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentMap;

public class MonitoringControlBatch implements Job{
	private final Logger logger = LoggerFactory.getLogger(getClass());
	private final int DELAYED_TIME = 1000 * 60;

	// 현재 해당 파일에 취합된 기능
	// ~ 1분 주기로 데이터 저장 혹은 표시
	// 1. VHL OFF
	// 2. Stage Command Monitoring
	// 3. UDP Message Monitoring
	@Override
	public void execute(JobExecutionContext arg0) throws JobExecutionException {
		if (Util.isCurrentIC()) {
			ConcurrentMap<String, FunctionItem> switchMap = Env.getSwitchMap();

			new Thread("MonitoringControlBatch") {
				@Override
				public void run() {
					for (FabProperties fabProperties : DataService.getInstance().getFabPropertiesMap().values()) {
						String fabId = fabProperties.getFabId();

						for (String mcpName : fabProperties.getMcpName2OhtNameMap().keySet()) {
							String key = fabId + ":" + mcpName;
							FunctionItem functionItem = switchMap.get(key);

							_processVhlOff(functionItem);
							_processStageCommandMonitoring(functionItem);
						}
					}

					_processUdpMessageMonitoring();
				}
			}.start();
		}
	}

	/**
	 * VHL OFF
	 */
	private void _processVhlOff(FunctionItem functionItem) {
		if (functionItem.isUseVhlOff()) {
			logger.info("... process of `VhlOff` has started in `MonitoringControlBatch`");

			long timer = System.currentTimeMillis();

			this._processVhlOffHandler(functionItem);

			long checkTimer = System.currentTimeMillis() - timer;

			if (checkTimer >= DELAYED_TIME) {
				logger.error("... !!!DELAYED!!! process of `VhlOff` has finished in `MonitoringControlBatch` [elapsed time: {}m ({}ms)]", checkTimer / (60 * 1000), checkTimer);
			} else {
				logger.info("... process of `VhlOff` has finished in `MonitoringControlBatch` [elapsed time: {}ms]", checkTimer);
			}
		}
	}

	/**
	 * Stage Command Monitoring
	 */
	private void _processStageCommandMonitoring(FunctionItem functionItem) {
		if (functionItem.isUseStageCommandMonitoring()) {
			logger.info("... process of `StageCommandMonitoring` has started in `MonitoringControlBatch`");

			long timer = System.currentTimeMillis();

			this._processStageCommandMonitoringHandler(functionItem);

			long checkTimer = System.currentTimeMillis() - timer;

			if (checkTimer >= DELAYED_TIME) {
				logger.error("... !!!DELAYED!!! process of `StageCommandMonitoring` has finished in `MonitoringControlBatch` [elapsed time: {}m ({}ms)]", checkTimer / (60 * 1000), checkTimer);
			} else {
				logger.info("... process of `StageCommandMonitoring` has finished in `MonitoringControlBatch` [elapsed time: {}ms]", checkTimer);
			}
		}
	}

	/**
	 * UDP Message Monitoring
	 */
	private void _processUdpMessageMonitoring() {
		if ("TRUE".equals(Env.getFabsetProperties().getProperty("CMN.CMN.UDP_MESSAGE_MONITORING"))) {
			var copyMap = new ArrayList<Msg>();
			
			DataService.getInstance().recordQueue.forEach(v -> copyMap.add(v));
			DataService.getInstance().recordQueue.clear();
			
			logger.info("... process of `UdpMessageMonitoring` has started in `MonitoringControlBatch`");

			long timer = System.currentTimeMillis();

			this._processUdpMessageMonitoringHandler(copyMap);

			long checkTimer = System.currentTimeMillis() - timer;

			if (checkTimer >= DELAYED_TIME) {
				logger.error("... !!!DELAYED!!! process of `UdpMessageMonitoring` has finished in `MonitoringControlBatch` [elapsed time: {}m ({}ms)]", checkTimer / (60 * 1000), checkTimer);
			} else {
				logger.info("... process of `UdpMessageMonitoring` has finished in `MonitoringControlBatch` [elapsed time: {}ms]", checkTimer);
			}
		} else {
			DataService.getInstance().recordQueue.clear();
		}
	}

	// handler
	// 각 handler 에 logpressoData 가 있다면 logpresso 데이터 에 적재 하는 기능이 존재
	private void _processVhlOffHandler(FunctionItem functionItem) {
		List<Tuple> logpressoData = new ArrayList<>();

		final ConcurrentMap<String, VhlOffRecordItem> record = DataService.getDataSet().getVhlOffMonitoringMap();
		String fabId = functionItem.getFabId();
		String mcpName = functionItem.getMcpName();
		String compareKey = fabId + ":" + mcpName;

		if (!record.isEmpty()) {
			for (Map.Entry<String, VhlOffRecordItem> entry : record.entrySet()) {
				String key = entry.getKey();
				//	└─ {fabId}:{mcpName}:{machineId}

				if (key.startsWith(compareKey)) {
					VhlOffRecordItem recordItem = entry.getValue();
					Tuple tuple = this._getVhlOffTuple(recordItem);

					if (tuple != null) {
						logpressoData.add(tuple);
					}

					if (recordItem.getState().equals(OHT_TIB_STATE.NORMAL)) {
						DataService.getDataSet().getVhlOffMonitoringMap().remove(key);
					}
				}
			}
		}

		if (logpressoData.isEmpty()) {
			// 기록된 데이터가 존재하지 않는 경우
			VhlOffRecordItem temp = new VhlOffRecordItem(
					null,
					null,
					fabId,
					null,
					mcpName,
					null,
					-1,
					-1,
					null,
					null,
					null,
					null,
					System.currentTimeMillis()
			);

			Tuple tuple = this._getVhlOffTuple(temp);

			if (tuple != null) {
				logpressoData.add(tuple);
			}
		}

		Util.insertInLogpressoDatabase(logpressoData, "ATLAS_OHT_VHL_OFF_ONLY", "VhlOffMonitoring");
	}

	private void _processStageCommandMonitoringHandler(FunctionItem functionItem) {
		List<Tuple> logpressoData = new ArrayList<>();
		Map<String, StageCommandItem> dataMap = new HashMap<>();

		final ConcurrentMap<String, StageCommandRecordItem> recordMap = DataService.getDataSet().getStageCommandMap();
		String fabId = functionItem.getFabId();
		String mcpName = functionItem.getMcpName();

		// #1. 데이터 구분
		for (StageCommandRecordItem recordItem : recordMap.values()) {
			if (
					recordItem.getFabId().equals(fabId)
							&& recordItem.getMcpName().equals(mcpName)
							&& OHT_TIB_STATE.ABNORMAL.equals(recordItem.getState())
			) {
				this._stageCommandItemBuild(dataMap, recordItem);
			}
		}

		// #2. tuple 데이터 형성
		if (dataMap.isEmpty()) { // #2-1. 데이터 가 존재하지 않는 경우 (NORMAL 제외)
			Tuple data = this._getStageCommandTuple(new StageCommandItem(fabId, null, null));

			if (data != null && !data.toMap().isEmpty()) {
				logpressoData.add(data);
			}
		} else { // #2-2. 데이터 가 존재 하는 경우 (NORMAL 제외)
			for (StageCommandItem item: dataMap.values()) {
				Tuple tuple = this._getStageCommandTuple(item);

				if (tuple != null && !tuple.toMap().isEmpty()) {
					logpressoData.add(tuple);
				}
			}
		}

		// #3. logpresso 데이터 저장
		Util.insertInLogpressoDatabase(logpressoData, "ATLAS_OHT_STG_CMD_MNT", "StageCommandMonitoring");
	}

	private void _stageCommandItemBuild(Map<String, StageCommandItem> dataMap, StageCommandRecordItem recordItem) {
		String fabId = recordItem.getFabId();
		String destinationPortId = recordItem.getDestinationPortId();
		String machineId = recordItem.getMachineId();
		String key = fabId + ":" + destinationPortId;

		if (dataMap.containsKey(key)) {
			StageCommandItem item = dataMap.get(key);

			item.addMachineId(machineId);
		} else {
			dataMap.put(
					key,	// 데이터 구분을 위한 장치, 실제 logpresso 데이터 에 저장 되는 값이 아님
					new StageCommandItem(fabId, destinationPortId, machineId)
			);
		}
	}

	private void _processUdpMessageMonitoringHandler(List<Msg> recordQueue) {
		// queue data monitoring ---> 임계치 이상인 경우, 경고 문구 표시
		BlockingQueue<Msg> queue = DataService.getInstance().queue;

		if (queue == null) {
			logger.error("... queue is null. Please check the code !");

			return;
		}

		int currentQueueSize = queue.size();
		int remainingCapacity = queue.remainingCapacity();
		int totalCapacity = remainingCapacity + currentQueueSize;
		int warningThreshold = (int) (totalCapacity * 0.8);    // 임계치 - 전체 queue 크기의 80%

		if (recordQueue == null) {
			logger.error("... queue for recording is null. Please check the code");

			return;
		}

		logger.info("\n[###SYSTEM###] processed queue: {}", recordQueue.size());
		logger.info("\n[###SYSTEM###] current queue capacity: {} / {} ({}){}", queue.size(), totalCapacity, remainingCapacity, queue.size() >= warningThreshold ? "\n##### WARNING: Queue is full! (Remaining Capacity: " + remainingCapacity + ") #####" : "");

		// udp message 를 file 로 저장
		String outputDirectory = FilePathUtil.getUdpMessagePath();    // 저장할 경로
		File targetFile = null;

		try {
			File[] files = _getExistingFiles(outputDirectory);

			if (files == null || files.length == 0) {
				logger.warn("... No existing files found in directory: {} !", outputDirectory);

				files = new File[0];
			}

			if (files.length < 3) {
				targetFile = new File(outputDirectory, "udp_message_record_" + (files.length + 1) + ".txt");
			} else {
				targetFile = Arrays.stream(files)
						.max(Comparator.comparingLong(File::lastModified))
						.orElseThrow(() -> new IOException("No files found in the specified directory"));
			}

			try (BufferedWriter writer = new BufferedWriter(new FileWriter(targetFile))) {
				for (Msg record : recordQueue) {
					writer.write(record.getMessage());
					writer.newLine();
				}
			}
		} catch (IOException e) {
			logger.error("udp message record file write error [directory: {}] {}", targetFile != null ? targetFile.getAbsolutePath() : "Na", e.getMessage());
		}
	}

	private File[] _getExistingFiles(String path) {
		File directory = new File(path);

		if (!directory.exists() && directory.mkdirs()) {
			logger.info("created directory: {}", path);
		}

		// udp_message_record_X.txt 형태의 파일만 필터링
		return directory.listFiles((dir, name) -> name.matches("udp_message_record_\\d+\\.txt"));
	}
	//~handler

	// build tuple for logpresso
	private Tuple _getStageCommandTuple(StageCommandItem item) {
		Tuple tuple = new Tuple();

		try {
			tuple.put("FAB_ID", item.getFabId());
			tuple.put("DEST_PORT", item.getDestinationPortId());
			tuple.put("MACHINE_LST", item.getMachineIdListString());
			tuple.put("MACHINE_CNT", item.getMachineIdList().size());
		} catch (Exception e) {
			logger.error("", e);

			return null;
		}

		return tuple;
	}

	// fabId, mcpName, ?eventDateTime, error code, ?recoveryDateTime
	private Tuple _getVhlOffTuple(VhlOffRecordItem recordItem) {
		long currentDateTime 		= System.currentTimeMillis();
		LocalDateTime dateTime 		= LocalDateTime.ofInstant(Instant.ofEpochMilli(currentDateTime), ZoneId.systemDefault());
		DateTimeFormatter formatter	= DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");
		String formattedDateTime 	= dateTime.format(formatter);

		Tuple tuple = new Tuple();

		try {
			tuple.put("ENV", Env.getEnv());
			tuple.put("SAVE_DT", formattedDateTime);
			tuple.put("FAB_ID", recordItem.getFabId());
			tuple.put("MCP_NM", recordItem.getMcpName());
			tuple.put("EVENT_DT", recordItem.getEventDateTimeString());
			tuple.put("ERR_CD", recordItem.getErrorCode());
			tuple.put("MACHINE_ID", recordItem.getMachineId());

			if (recordItem.getState() == null) {
				tuple.put("RECOVERY_DT", "");
				tuple.put("JUDGE_VAL", 0);
			} else {
				boolean isAbnormal = recordItem.getState().equals(OHT_TIB_STATE.ABNORMAL);

				tuple.put("RECOVERY_DT", isAbnormal ? "" : recordItem.getRecoveryDateTimeString());
				tuple.put("JUDGE_VAL", isAbnormal ? 1 : 0);
			}
		} catch (Exception e) {
			logger.error("", e);

			return null;
		}

		return tuple;
	}
	//~build tuple for logpresso

	private static class StageCommandItem {
		private final String fabId;
		private final String destinationPortId;
		private final List<String> machineIdList = new ArrayList<>();

		public StageCommandItem(String fabId, String destinationPortId, String machineId) {
			this.fabId = fabId;
			this.destinationPortId = destinationPortId == null ? "" : destinationPortId;

			this.addMachineId(machineId);
		}

		public String getFabId() {
			return fabId;
		}

		public String getDestinationPortId() {
			return destinationPortId;
		}

		public List<String> getMachineIdList() {
			return machineIdList;
		}

		public String getMachineIdListString() {
			return String.join(",", this.machineIdList);
		}

		public void addMachineId(String machineId) {
			if (machineId == null || (machineId.trim()).isEmpty()) return;

			this.machineIdList.add(machineId);
		}
	}
}
