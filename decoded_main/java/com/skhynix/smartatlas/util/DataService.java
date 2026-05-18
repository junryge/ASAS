package com.skhynix.smartatlas.util;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Objects;
import java.util.Properties;
import java.util.Queue;
import java.util.Set;
import java.util.Stack;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ForkJoinPool;
import java.util.concurrent.Future;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;
import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.comm.OracleAPI;
import com.skhynix.smartatlas.data.Area;
import com.skhynix.smartatlas.data.Bay;
import com.skhynix.smartatlas.data.Carrier.PROCESS_TYPE;
import com.skhynix.smartatlas.data.DataSet;
import com.skhynix.smartatlas.data.FabProperties;
import com.skhynix.smartatlas.data.FirstEdgeInfo;
import com.skhynix.smartatlas.data.McpProperties;
import com.skhynix.smartatlas.data.Msg;
import com.skhynix.smartatlas.data.Msg.MSG_TYP;
import com.skhynix.smartatlas.data.RailCutRecordItem;
import com.skhynix.smartatlas.data.TibrvSendMsg;
import com.skhynix.smartatlas.data.TibrvSendMsg.SEND_MSG_FORMAT;
import com.skhynix.smartatlas.data.eq.AmpUnit;
import com.skhynix.smartatlas.data.eq.Conveyor;
import com.skhynix.smartatlas.data.eq.Eqp;
import com.skhynix.smartatlas.data.eq.Eqp.EQP_TYPE;
import com.skhynix.smartatlas.data.eq.Fio;
import com.skhynix.smartatlas.data.eq.Oht;
import com.skhynix.smartatlas.data.eq.StbGroup;
import com.skhynix.smartatlas.data.eq.Stocker;
import com.skhynix.smartatlas.data.eq.Stocker.STK_TYPE;
import com.skhynix.smartatlas.data.raw.LoopEntry;
import com.skhynix.smartatlas.data.raw.Mcp75Config;
import com.skhynix.smartatlas.data.raw.RawBay.RawBayPort;
import com.skhynix.smartatlas.data.raw.RawCnvZone;
import com.skhynix.smartatlas.data.raw.RawEdge;
import com.skhynix.smartatlas.data.raw.RawHid;
import com.skhynix.smartatlas.data.raw.RawLabel;
import com.skhynix.smartatlas.data.raw.RawLoop;
import com.skhynix.smartatlas.data.raw.RawPoint;
import com.skhynix.smartatlas.data.raw.RawStation;
import com.skhynix.smartatlas.data.raw.RawStation.STATION_LOCATION;
import com.skhynix.smartatlas.data.raw.RawStation.STATION_TYPE;
import com.skhynix.smartatlas.data.raw.RawVhl;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.environment.type.FunctionItem.FunctionType;
import com.skhynix.smartatlas.listener.CnvSocketIOListener;
import com.skhynix.smartatlas.listener.AmpListener;
import com.skhynix.smartatlas.listener.OhtUdpListener;
import com.skhynix.smartatlas.map.AbstractEdge;
import com.skhynix.smartatlas.map.AbstractEdge.EDGE_TYPE;
import com.skhynix.smartatlas.map.AbstractNode;
import com.skhynix.smartatlas.map.Label;
import com.skhynix.smartatlas.map.Vhl;
import com.skhynix.smartatlas.map.edge.AgvEdge;
import com.skhynix.smartatlas.map.edge.BranchJoinEdge;
import com.skhynix.smartatlas.map.edge.CnvEdge;
import com.skhynix.smartatlas.map.edge.LongEdge;
import com.skhynix.smartatlas.map.edge.RailEdge;
import com.skhynix.smartatlas.map.edge.RailEdge.RAIL_DIRECTION;
import com.skhynix.smartatlas.map.edge.Station;
import com.skhynix.smartatlas.map.edge.StkRmEdge;
import com.skhynix.smartatlas.map.edge.TransferEdge;
import com.skhynix.smartatlas.map.node.CnvPortNode;
import com.skhynix.smartatlas.map.node.CnvPortNode.CNV_NODE_TYPE;
import com.skhynix.smartatlas.map.node.CnvPortNode.CNV_REF_DIR;
import com.skhynix.smartatlas.map.node.EqpPortNode;
import com.skhynix.smartatlas.map.node.FioPortNode;
import com.skhynix.smartatlas.map.node.FioPortNode.FIO_PORT_INOUT_TYPE;
import com.skhynix.smartatlas.map.node.FioPortNode.FIO_SUB_PORT_ACCESSMODE;
import com.skhynix.smartatlas.map.node.FioPortNode.FIO_SUB_PORT_TYPE;
import com.skhynix.smartatlas.map.node.RailNode;
import com.skhynix.smartatlas.map.node.StbNode;
import com.skhynix.smartatlas.map.node.StkPortNode;
import com.skhynix.smartatlas.map.node.StkPortNode.STK_PORT_INOUT_TYPE;
import com.skhynix.smartatlas.map.node.StkPortNode.STK_SUB_PORT_TYPE;
import com.skhynix.smartatlas.map.node.StkRmNode;
import com.skhynix.smartatlas.map.node.StkShelfNode;
import com.skhynix.smartatlas.navi.Navigator;
import com.skhynix.smartatlas.process.OhtMsgWorkerRunnable.OHT_TIB_STATE;
import com.skhynix.smartatlas.service.TibrvService;
import com.skhynix.smartfx.dataaccessfx.DataRow;
import com.skhynix.smartfx.dataaccessfx.DataTable;

public class DataService {
	private final Logger logger = LoggerFactory.getLogger(getClass());
	final String EXCEPTION_LOG = "An error occurred STEP#{} !!";
	final String INTERRUPTED_EXCEPTION_LOG = EXCEPTION_LOG + " - Interrupted Exception";
	final String EXECUTION_EXCEPTION_LOG = EXCEPTION_LOG + " - Execution Exception";

	static public AtomicBoolean isBlocked = new AtomicBoolean(false);
	private static final ConcurrentMap<String, Integer> fabBitsMap = new ConcurrentHashMap<>();

	private static boolean isInitialized = false;

	Queue<DataSet> dataQ = new ConcurrentLinkedQueue<>();
	public BlockingQueue<Msg> queue = new LinkedBlockingQueue<>();
	public BlockingQueue<Msg> recordQueue = new LinkedBlockingQueue<>();
	public BlockingQueue<TibrvSendMsg> tibrvMessageQueue = new LinkedBlockingQueue<>();
	
	private boolean isRailCutInitialized = false;

	private final ConcurrentMap<String, FirstEdgeInfo> firstEdgeInfoMap = new ConcurrentHashMap<>();
	private final ConcurrentHashMap<String, TibrvService> tibrvSenderMap = new ConcurrentHashMap<>();    // key: facId, val: [TibrvReceiver ...]
	private final ConcurrentHashMap<String, TibrvService> tibrvReceiverMap = new ConcurrentHashMap<>();    // key: facId, val: [TibrvReceiver ...]
	private final ConcurrentMap<String, FabProperties> fabPropertiesMap = new ConcurrentHashMap<>();
	private ConcurrentHashMap<String, OhtUdpListener> ohtUdpListenerMap = new ConcurrentHashMap<>();
	private ConcurrentMap<String, List<String>> ohtAlarmCodeListMap = new ConcurrentHashMap<>();
	
	private boolean isTibrvSendRunning = false;
	private ConcurrentMap<String, Integer> curMaxLongEdgeDirMap = new ConcurrentHashMap<String, Integer>();
	
	private String ampUrl = "";
	private AmpListener ampListener;

	private void _START_PROCESS_LOG(int sequence, String processTitle) {
		final String content = String.format(
				"[START]STEP#%2d ========================[ %-30s]========================", sequence, processTitle
		);
		logger.info(content);
	}

	private void _ELAPSED_TIME_LOG(int sequence, long elapsedTime) {
		final String content = String.format(
				"STEP#%2d Elapse Time : %d ms", sequence, System.currentTimeMillis() - elapsedTime
		);
		logger.info(content);
	}

	private void _END_PROCESS_LOG(int sequence, String processTitle) {
		final String content = String.format(
				"[END  ]STEP#%2d ========================[ %-30s]========================", sequence, processTitle
		);

		logger.info(content);
	}

	private static class Singleton {
		private static final DataService instance = new DataService();
	}

	static public DataSet getDataSet() {
		_blocked();

		return Singleton.instance.dataQ.peek();
	}

	static public DataService getInstance() {
		_blocked();

		return Singleton.instance;
	}

	private static void _blocked() {
		Logger logger = LoggerFactory.getLogger(DataService.class);

		if (isBlocked.get()) {
			logger.warn("... Initialization of biz data system is blocking.");
		}

		while (isBlocked.get()) {
			try {
				Thread.sleep(10L);
			} catch (Exception e) {
				logger.error("... Blocking dataSet is fail !!!", e);
			}
		}
	}

	// tib/rv message
	private synchronized void _sendTibrvMessage() {
		if (isTibrvSendRunning == true) {
			return;
		}
		
		final var isRunning = new AtomicBoolean(true);
		final var threadPool = new ThreadPool("TibrvQueue", Env.getTibrvQThreadPoolSize());

		new Thread(() -> {
			while(isRunning.get()) {
				if (tibrvMessageQueue.isEmpty()) continue;

				var queuedItems = new ArrayList<TibrvSendMsg>(100);
				
				try {
					this.tibrvMessageQueue.drainTo(queuedItems, 100);
				} catch (Exception e) {
					logger.error("... It couldn't take a message from the queue !!!", e);
					continue;
				}
				
				try {
					queuedItems.forEach(msg -> {
						final TibrvSendMsg msgSafe = msg;
						
						try {
							threadPool.execute(() -> {
								var message = "";
								
								if (msgSafe.getFormat().equals(SEND_MSG_FORMAT.JSON)) {
									message = JsonUtil.getInstance().gson().toJson(msgSafe.getData());
								} else {
									message = XmlUtil.formatLayoutMessage(
											msgSafe.getKey(),
											msgSafe.getType(),
											msgSafe.getData()
									);	
								}

								this.tibrvSenderMap.get(msgSafe.getKey()).sendMessage(message, msgSafe.getType());
							});
						} catch (Exception e) {
							logger.error("... Couldn't send Tibrv Message", e);
						}
					});
				} catch (Exception e) {
					logger.error("... It couldn't send a message to the tibrv module !!!", e);

					break;
				}

				logger.debug("... Message processing completed [tibrv message queue size: {}]", this.tibrvMessageQueue.size());
			}
		}).start();
	}

	public boolean isDataServiceRunning() {
		return (!this.dataQ.isEmpty());
	}

	private boolean _isIC(String fabId){
		return (fabId.contains("M14A") || fabId.contains("M14B") || fabId.contains("M16A") || fabId.contains("M16B") || 
				fabId.contains("ICPKT") || fabId.contains("ICPNT") || fabId.contains("R3") || fabId.contains("TSV") || fabId.contains("DWT") || fabId.contains("WLP") || fabId.contains("ICPKG"));
	}

	/**
	 * @param properties `FabSet.properties`
	 */
	public void initialization(final Properties properties) {
		isInitialized = false;

		if (this._loadFabData(properties)) {
			if (!fabPropertiesMap.isEmpty()) {
				this._loadExtraXmlData();

				this.ohtAlarmCodeListMap = this._readAndParsingTxtFile();

				this._initializedVelocity();

				try {
					Util.reflectSwitch(properties);
				} catch (NullPointerException e) {
					logger.error("", e);
				}

				this.writeRecording();
			}

			isInitialized = true;
		} else {
			logger.error("... (2) biz data is not initialized.");
		}
	}

	/**
	 * call data from a modified and applicable xml document during service operation
	 * example) variable.xml, customQuery.xml, alarm_message.xml ...
	 */
	private void _loadExtraXmlData() {
		// extra xml data
		// # logpresso query
		XmlUtil.loadLogpressoParm(FilePathUtil.LOGPRESSO_CUSTOM_QUERY);
		XmlUtil.loadLogpressoParm(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2);
		// # alarm
		XmlUtil.loadAlarmMessage();
		XmlUtil.loadOhtAlarmMessage();
		// # 수식, 기준
		XmlUtil.loadVariableEnv();
	}

	private boolean _loadFabData(final Properties properties) {
		DataSet dataSet = null;

		if (properties == null) {
			logger.warn("... (1) properties is null");
		} else {
			this._loadFab(properties);

			if (fabPropertiesMap.isEmpty()) {
				logger.error("... (1) inquired factory property is empty, then building the initialization is skipped");

				return false;
			}

			try {
				// fabProperties 데이터의 구성이 선행되어야만 dataQ 의 초기값을 구성할 수 있음
				if (dataQ.isEmpty()) {
					for (String fabId : fabPropertiesMap.keySet()) {
						dataSet = _createNewDataSet(fabId, dataSet, false, 23);
					}
					
					if (dataSet != null) {
						this._inlineConnect(dataSet, false);
						this._fabConnect(dataSet, false);
						this._setSpnOhtFabId(dataSet);
						this._setNodeEdgeRef(dataSet);
						this._setRailEdgeRef(dataSet);

						for (Eqp eqp : dataSet.getAllEqpMap().values()) {							
							eqp.getMcpNameSet(dataSet);
							eqp.getConnectedFabMcpSet(dataSet);
							eqp.getFirstPortNodeId(dataSet);
						}
						updateEqpExtInfo(dataSet);
						dataQ.add(dataSet);

						this._setRailInfoAffectedForRailCut();
					}
				}

				return true;
			} catch (Exception e) {
				logger.error("... Error loading fab data !!!", e);

				return false;
			}
		}

		return true;
	}

	/*
	 * 초기화 혹은 데이터 업데이트시, Rail Cut 관련 port, address 조사 후 설정
	 */
	private void _setRailInfoAffectedForRailCut() {
		logger.info("... `RAIL CUT` data initialized has searching the affection [total: {}]", getDataSet().getRailCutRecordMap().size());

		long timer = System.currentTimeMillis();

		try {
			for (Map.Entry<String, RailCutRecordItem> dataMap : getDataSet().getRailCutRecordMap().entrySet()) {
				RailCutRecordItem item 	= dataMap.getValue();
				RailEdge railEdge 		= item.getRailEdge();

				if (railEdge != null) {
					Navigator navigator = new Navigator(railEdge);

					item.setAffectedAddress(navigator.getAffectedRailSet());
					item.setAffectedPort(navigator.getAffectedPortSortedList());
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info("... searching the affection for `RAIL CUT` has finished [elapsed time: {}ms]", System.currentTimeMillis() - timer);
	}

	private void _loadFab(final Properties properties) {
		String[] fabIdList = properties.getProperty("FabIdList", "").trim().split(",");
		ArrayList<String> fabIds = Arrays.stream(fabIdList)
				.filter(s -> !s.isEmpty())
				.collect(Collectors.toCollection(ArrayList::new));
		int fabBits = 1;

		if (fabIds.isEmpty()) {
			logger.error("... list of factory ID is empty");
		} else {
			for (String fabId : fabIds) {
				fabId = fabId.trim();

				try {
					if (this._isIC(fabId)) {
						logger.info("... the factory ID selected has setting property started [fab: {}]", fabId);

						fabBitsMap.put(fabId, fabBits);

						fabBits *= 2;
						FabProperties fabProperties = new FabProperties();

						// #1 기본 정보 입력
						this._setFabPropertiesFoundation(fabId, fabProperties, properties);

						// #2 tibrv 정보 입력
						this._setTibrvInfo(fabProperties, properties, true);    // send target (ATLAS -> ?)
						this._setTibrvInfo(fabProperties, properties, false); // receive target (ATLAS <- ?)

						// #3
						this._setMcpName(fabId, fabProperties, properties);

						// #4
						this._setMcpInfo(fabId, fabProperties, properties);

						// #5
						this.fabPropertiesMap.put(fabId, fabProperties);

						// #6
						this._setConveyorToApiUrl(fabId, fabProperties, properties);
						
						// #7
						this._setMcp75Info(fabProperties);
						
						// #8
						this._setBridge(fabId, fabProperties, properties);	
						
						// #9
						this._setInlineConn(fabId, fabProperties, properties);
						
						// #10
						this._setTibrvDaemonInfo(fabId, fabProperties, properties);
						
					} else {
						logger.error("... the factory ID selected is not IC located [fab: {}]", fabId);
					}
				} catch (Exception e) {
					logger.error("... it couldn't load a factory properties from the redis", e);
				}
			}

			// #10
			this._setAmpUrl(properties);
		}
	}

	private void _setFabPropertiesFoundation(
			String fabId,
			FabProperties fabProperties,
			Properties properties
	) {
		try {
			fabProperties.setFabId(fabId);
			fabProperties.setFacId(properties.getProperty(fabId + ".FacId", "").trim());
			fabProperties.setMapDir(properties.getProperty(fabId + ".MapDir", "").trim());
		} catch (Exception e) {
			logger.error("", e);
		}
	}

	private void _setMcpName(String fabId, FabProperties fabProperties, Properties properties) {
		String[] mcpNamePairs = properties.getProperty(fabId + ".McpNamePairs", "").trim().split(",");

		for (String mcpNamePair : mcpNamePairs) {
			String[] temp = mcpNamePair.split("[|]");

			if (temp.length > 1) {
				String ohtName = temp[0].trim();
				String mcpName = temp[1].trim();

				fabProperties.getOhtName2McpNameMap().put(ohtName, mcpName);
				fabProperties.getMcpName2OhtNameMap().put(mcpName, ohtName);
			}
		}		
	}

	private void _setTibrvInfo(FabProperties fabProperties, Properties properties, boolean k) {
		String type = k ? "send" : "rev";

		try {
			String fabId = fabProperties.getFabId();
			String[] list = properties.getProperty(fabId + "." + type +".list", "").trim().split(",");
			List<String> targetList = new ArrayList<>(Arrays.asList(list));
			targetList.removeIf(target -> target.trim().isEmpty());

			if (targetList.isEmpty()) {
				logger.info("... there is no tibrv information to use and apply it");
			} else {
				for (String target : targetList) {
					String prefix = fabId + "." + type + "." + target;
					String middle = target.substring(0, 1).toUpperCase() + target.substring(1);
					String methodName = (k ? "setSend" : "setRev") + middle;
					int gid = Util.getIntOrZero(properties.getProperty(prefix + ".gid", "").trim());
					String subject = properties.getProperty(prefix + ".subject", "").trim();
					String daemon = properties.getProperty(prefix + ".daemon", "").trim();										
					
					if (subject.isEmpty() || daemon.isEmpty()) {
						continue;
					}

					this._dynamicMethod(fabProperties, methodName + "Gid", gid);
					this._dynamicMethod(fabProperties, methodName + "Subject", subject);
					this._dynamicMethod(fabProperties, methodName + "Daemon", daemon);

					if (gid == -1) {
						String service = properties.getProperty(prefix + ".service", "").trim();
						String network = properties.getProperty(prefix + ".network", "").trim();

//						if (service.isEmpty() || network.isEmpty()) {
//							continue;
//						}

						this._dynamicMethod(fabProperties, methodName + "Service", service);
						this._dynamicMethod(fabProperties, methodName + "Network", network);
					}

					// execute tib/rv listening
					this._executeTibrv(fabProperties, target, middle, k);
				}
			}
		} catch (Exception e) {
			logger.error("... Error setting tibrv information !!!", e);
		}
	}

	private void _executeTibrv (FabProperties fabProperties, String target, String middleName, boolean k) {
		TibrvService tibrvService;
		String fabId = fabProperties.getFabId();
		String facId = fabProperties.getFacId();
		String type = k ? "send" : "rev";
		String key = fabId + ":" + type + ":" + target;	// ex: M14A:send:star

		if ((k && this.tibrvSenderMap.containsKey(key)) || (!k && this.tibrvReceiverMap.containsKey(key))) {
			return;
		}

		String methodName = (k ? "getSend" : "getRev") + middleName;

		try {
			logger.info("Initiate initialization of the tib/rv module (fab: {}, key: {}) ...", fabId, key);

			Object gidResult = this._dynamicMethod(fabProperties, methodName + "Gid", null);
			Object subjectResult = this._dynamicMethod(fabProperties, methodName + "Subject", null);
			Object daemonResult = this._dynamicMethod(fabProperties, methodName + "Daemon", null);
			int gid = gidResult instanceof Integer ? (Integer) gidResult : -1;
			String subject = subjectResult instanceof String ? (String) subjectResult : "";
			String daemon = daemonResult instanceof String ? (String) daemonResult : "";

			if (gid > -1) {
				tibrvService = new TibrvService(fabId, facId, subject, daemon, gid);
			} else {
				Object serviceResult = this._dynamicMethod(fabProperties, methodName + "Service", null);
				Object networkResult = this._dynamicMethod(fabProperties, methodName + "Network", null);
				String service = serviceResult instanceof String ? (String) serviceResult : "";
				String network = networkResult instanceof String ? (String) networkResult : "";
				
				MSG_TYP msgTyp = MSG_TYP.fromString(target);

				tibrvService = new TibrvService(fabId, facId, daemon, subject, service, network, msgTyp);
			}

			if (k) {
				if (!isTibrvSendRunning) {
					this._sendTibrvMessage();

					this.isTibrvSendRunning = true;
				}

				this.tibrvSenderMap.put(key, tibrvService);
			} else {
				tibrvService.startListen();

				this.tibrvReceiverMap.put(key, tibrvService);
			}

			logger.info("... Completed initialization of tib/rv module (fab: {})", fabId);
		} catch (Exception e) {
			logger.error("... Error during initialization of tib/rv module (fab: {}) !!!", fabId, e);
		}
	}

	private Object _dynamicMethod(FabProperties fabProperties, String methodName, Object value) {
		try {
			if (value == null) {
				Method method = FabProperties.class.getMethod(methodName);

				return method.invoke(fabProperties);
			} else {
				Method method = FabProperties.class.getMethod(methodName, value.getClass());

				return method.invoke(fabProperties, value);
			}
		} catch (NoSuchMethodException e) {
			logger.error("... Method does not found (method name: {}) - NoSuchMethodException !!!", methodName, e);
		} catch (Exception e) {
			logger.error("... Failed to invoke method (method name: {}) !!!", methodName, e);
		}

		return null;
	}

	private void _setMcpInfo(String fabId, FabProperties fabProperties, Properties prop) {
		Map<String, McpProperties> mcpPropertiesMap = new HashMap<>();

		for (String mcpName : fabProperties.getMcpName2OhtNameMap().keySet()) {
			McpProperties mcpProperties = new McpProperties();
			String target = fabId + ".oht." + mcpName;

			mcpProperties.setMcpName(mcpName);
			mcpProperties.setDaemon(prop.getProperty(target + ".daemon", "").trim());
			mcpProperties.setSubject(prop.getProperty(target + ".subject", "").trim());
			mcpProperties.setIp(prop.getProperty(target + ".ip", "").trim());
			mcpProperties.setPort(Util.getIntOrZero(prop.getProperty(target + ".port", "0").trim()));

			// FTP 정보 설정
			mcpProperties.setFtpIp(prop.getProperty(target + ".ftp.ip", "").trim());
			mcpProperties.setFtpUser(prop.getProperty(target + ".ftp.user", "").trim());
			mcpProperties.setFtpPassword(prop.getProperty(target + ".ftp.password", "").trim());
			mcpProperties.setFtpLaneCutPath(prop.getProperty(target + ".ftp.lanecut", "").trim());
			mcpProperties.setFtpMcp75Path(prop.getProperty(target + ".ftp.mcp75", "").trim());
			mcpProperties.setFtpStationPath(prop.getProperty(target + ".ftp.station", "").trim());
			mcpProperties.setFtpLayoutPath(prop.getProperty(target + ".ftp.layout", "").trim());

			mcpPropertiesMap.put(mcpName, mcpProperties);
		}

		fabProperties.setMcpPropertiesMap(mcpPropertiesMap);
	}

	private boolean _validFtpPropertyByFabSet(McpProperties mcpProperties) {
		return !mcpProperties.getFtpIp().isEmpty()
				|| !mcpProperties.getFtpUser().isEmpty()
				|| !mcpProperties.getFtpPassword().isEmpty()
				|| !mcpProperties.getFtpLaneCutPath().isEmpty()
				|| !mcpProperties.getFtpStationPath().isEmpty()
				|| !mcpProperties.getFtpLayoutPath().isEmpty()
				|| !mcpProperties.getFtpMcp75Path().isEmpty();
	}
	
	private void _setConveyorToApiUrl(String fabId, FabProperties fabProperties, Properties properties) {
		// cnv api 가져오기
		String conveyorStr = properties.getProperty(fabId+".conveyor","").trim();
		if(StringUtils.isNotEmpty(conveyorStr)) {
			JsonArray ja = JsonParser.parseString(conveyorStr).getAsJsonArray();
			for(JsonElement je : ja) {
				final String url = je.getAsJsonObject().get("mapUrl").getAsString().trim();
				final String eqpId = je.getAsJsonObject().get("eqpId").getAsString().trim();
				fabProperties.getConveyorToApiUrl().put(eqpId, url);
			}				
		}
		
		// CNV Listener			
		for(Map.Entry<String, String> entry : fabProperties.getConveyorToApiUrl().entrySet()) {
			CnvSocketIOListener cnvSocketIOListener = new CnvSocketIOListener(fabProperties.getFabId(), entry.getKey(), entry.getValue());
			fabProperties.getCnvSocketIOListenerMap().put(entry.getKey(), cnvSocketIOListener);
			cnvSocketIOListener.connectAndBuildCnvRawLayout();			
		}
	}

	/**
	 * 지정한 FTP 서버의 경로를 통해 map 파일을 다운로드
	 * @param fabProperties (선행)
	 */
	private void _setMcp75Info(FabProperties fabProperties) {
		Mcp75Config mcp75Config;
		String fabId = fabProperties.getFabId();
		String directory = fabProperties.getMapDir();

		// properties 에서 설정한 FTP 정보로 맵 데이터 download
		for (McpProperties mcpProperties : fabProperties.getMcpPropertiesMap().values()) {
			String mcpName = mcpProperties.getMcpName();

			if (_validFtpPropertyByFabSet(mcpProperties)) {
				Util.getAllOhtLayoutFileOverFtp(
						fabProperties,
						mcpName,
						true,
						true,
						true,
						true,
						false
				);

				mcp75Config = new Mcp75Config(directory, fabId, mcpName);

				fabProperties.getMcpPropertiesMap()
						.get(mcpName)
						.setMcp75Config(mcp75Config);
			}
		}

		logger.info("... layout(map) files load completely [fab: {}]", fabId);
	}

	private void _setBridge(String fabId, FabProperties fp, Properties prop) {
		String bridgeFromStr = prop.getProperty(fabId+".BridgeFrom","").trim();
		String fromFab = "";
		if(StringUtils.isNotEmpty(bridgeFromStr)) {
			JsonArray ja = JsonParser.parseString(bridgeFromStr).getAsJsonArray();
			
			for(JsonElement je : ja) {
				fromFab = je.getAsJsonObject().get("fabId").getAsString().trim();
				Set<String> eqpIdSet = new HashSet<String>();
				for(JsonElement jee : je.getAsJsonObject().get("eqpIdSet").getAsJsonArray()) {
					eqpIdSet.add(jee.getAsString().trim());
				}
				fp.getBridgeFromSet().put(fromFab, eqpIdSet);
			}				
		}
		String bridgeToStr = prop.getProperty(fabId+".BridgeTo","").trim();
		String toFab = "";
		if(StringUtils.isNotEmpty(bridgeToStr)) {
			JsonArray ja = JsonParser.parseString(bridgeToStr).getAsJsonArray();
			for(JsonElement je : ja) {
				toFab = je.getAsJsonObject().get("fabId").getAsString().trim();
				Set<String> eqpIdSet = new HashSet<String>();
				for(JsonElement jee : je.getAsJsonObject().get("eqpIdSet").getAsJsonArray()) {
					eqpIdSet.add(jee.getAsString().trim());
				}
				fp.getBridgeToSet().put(toFab, eqpIdSet);
			}				
		}
	}
	
	private void _setInlineConn(String fabId, FabProperties fp, Properties prop) {
		String inlineConnStr = prop.getProperty(fabId+".InlineConnection","").trim();
		String stkId = "";
		if(StringUtils.isNotEmpty(inlineConnStr)) {
			JsonArray ja = JsonParser.parseString(inlineConnStr).getAsJsonArray();
			for(JsonElement je : ja) {
				stkId = je.getAsJsonObject().get("stkId").getAsString().trim();
				Set<String> eqpPortIdSet = new HashSet<String>();
				for(JsonElement jee : je.getAsJsonObject().get("eqpPortIdSet").getAsJsonArray()) {
					eqpPortIdSet.add(jee.getAsString().trim());
				}
				fp.getInlineConnectSet().put(stkId, eqpPortIdSet);
			}				
		}
	}
	
	private void _setTibrvDaemonInfo(String fabId, FabProperties fp, Properties prop) {
		
		// CNV Tibrv
		fp.setConveyorDaemon(prop.getProperty(fabId + ".cnv.daemon", "").trim());
		fp.setConveyorSubject(prop.getProperty(fabId + ".cnv.subject", "").trim());
				
		// AGV Tibrv
		fp.setAgvDaemon(prop.getProperty(fabId + ".agv.daemon", "").trim());
		fp.setAgvSubject(prop.getProperty(fabId + ".agv.subject", "").trim());
	}
	
	private void _setAmpUrl(Properties properties) {
		String ampUrl = properties.getProperty("AMP.URL","").trim();
		if(StringUtils.isEmpty(ampUrl)) return;		
		
		setAmpUrl(ampUrl);
		AmpListener listener = new AmpListener(ampUrl);
		setAmpListener(listener);
		listener.start();
	}

	public DataSet _createNewDataSet(String fabId, DataSet dataSet, boolean isUpdate, int threadCnt) {
		ConcurrentMap<String, RailEdge> tmpRailEdgeMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, StkRmEdge> tmpStkRmEdgeMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, CnvEdge> tmpCnvEdgeMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, Station> tmpStationMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, TransferEdge> tmpTransferEdgeMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, AbstractNode> tmpNodeMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, LongEdge> tmpLongEdgeMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, Eqp> tmpEqpMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, Fio> tmpFioMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, Oht> tmpOhtMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, StbGroup> tmpStbGroupMap = new ConcurrentHashMap<>();    // not used
		ConcurrentMap<String, Stocker> tmpStockerMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, Conveyor> tmpConveyorMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, Vhl> tmpVhlMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, Label> tmpLabelMap = new ConcurrentHashMap<>();    // not used
		ConcurrentMap<String, Area> tmpAreaMap = new ConcurrentHashMap<>();    // not used
		ConcurrentMap<String, Bay> tmpBayMap = new ConcurrentHashMap<>();    // not used
		ConcurrentMap<String, Mcp75Config> mcp75ConfigMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, RailCutRecordItem> tmpRailCutMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, AgvEdge> tmpAgvEdgeMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, AmpUnit> tmpAmpAgvMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, CnvPortNode> tmpCnvPortNodeNoMap = new ConcurrentHashMap<String, CnvPortNode>();

		// fab 관련 정보
		final FabProperties fabProperties = fabPropertiesMap.get(fabId);
		String facId = fabProperties.getFacId();

		// 도구 및 장치
		ForkJoinPool pool = new ForkJoinPool(threadCnt);
		int sequence = 0;    // 각 단계를 표시
		long startBlock;    // 각 단계에 대한 시간 계산

		//
		this._START_PROCESS_LOG(++sequence, "Mcp75Cfg Parsing");
		startBlock = System.currentTimeMillis();

		try {
			String directory = fabProperties.getMapDir();

			pool.submit(() -> fabProperties.getMcpPropertiesMap().keySet()
					.parallelStream()
					.forEach(mcpName -> {
						if (isUpdate) {
							// mcp75cfg 파일 내용 초기화 및 데이터 파싱
							Mcp75Config mcp75Config = new Mcp75Config(directory, fabId, mcpName);

							mcp75ConfigMap.put(mcpName, mcp75Config);
							fabProperties.getMcpPropertiesMap().get(mcpName).setMcp75Config(mcp75Config);
						} else {
							McpProperties mcpInfo = fabProperties.getMcpPropertiesMap().get(mcpName);

							if (mcpInfo != null && mcpInfo.getMcp75Config() != null) {
								mcp75ConfigMap.put(mcpName, mcpInfo.getMcp75Config());
							}
						}
					})).get();
		} catch (InterruptedException e) {
			logger.error(INTERRUPTED_EXCEPTION_LOG, sequence, e);
		} catch (ExecutionException e) {
			logger.error(EXECUTION_EXCEPTION_LOG, sequence, e);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Mcp75Cfg Parsing");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "Raw Data Building");
		startBlock = System.currentTimeMillis();

		ConcurrentMap<String, ConcurrentLinkedQueue<RawPoint>> leftRawPointsMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, ConcurrentLinkedQueue<RawPoint>> rightRawPointsMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, ConcurrentMap<Integer, ConcurrentLinkedQueue<RawStation>>> mapStationOnLeftMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, ConcurrentMap<Integer, ConcurrentLinkedQueue<RawStation>>> mapStationOnRightMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, ConcurrentMap<Integer, ConcurrentLinkedQueue<RawEdge>>> mapFromNode2RawEdgeMap = new ConcurrentHashMap<>();

		for (String mcpName : mcp75ConfigMap.keySet()) {
			leftRawPointsMap.put(mcpName, new ConcurrentLinkedQueue<>());
			rightRawPointsMap.put(mcpName, new ConcurrentLinkedQueue<>());
			mapStationOnLeftMap.put(mcpName, new ConcurrentHashMap<>());
			mapStationOnRightMap.put(mcpName, new ConcurrentHashMap<>());
			mapFromNode2RawEdgeMap.put(mcpName, new ConcurrentHashMap<>());

			Collection<RawPoint> rawPoints = mcp75ConfigMap.get(mcpName).getRawPointMap().values();

			for (RawPoint rawPoint : rawPoints) {
				if (rawPoint.getLeftAddress() > 0) {
					leftRawPointsMap.get(mcpName).add(rawPoint);
				}

				if (rawPoint.getRightAddress() > 0) {
					rightRawPointsMap.get(mcpName).add(rawPoint);
				}
			}

			try {
				pool.submit(() -> mcp75ConfigMap.get(mcpName).getRawStationMap().values()
						.parallelStream()
						.forEach(rawStation -> {
							final ConcurrentMap<Integer, ConcurrentLinkedQueue<RawStation>> mapStation = (
									rawStation.getStationLocation() == STATION_LOCATION.RIGHT_BRANCH
											? mapStationOnRightMap.get(mcpName)
											: mapStationOnLeftMap.get(mcpName)
							);
							final int pointAddress = rawStation.getAddress_no();
							ConcurrentLinkedQueue<RawStation> stationsOnPoint
									= mapStation.computeIfAbsent(pointAddress, k -> new ConcurrentLinkedQueue<>());

							stationsOnPoint.add(rawStation);
						})).get();
			} catch (InterruptedException e) {
				logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
			} catch (ExecutionException e) {
				logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
			}
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Raw Data Building");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "RailEdge Building");
		startBlock = System.currentTimeMillis();

		ConcurrentMap<String, String> railNodeLeftEdgeIdMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, String> railNodeRightEdgeIdMap = new ConcurrentHashMap<>();

		for (String mcpName : leftRawPointsMap.keySet()) {
			try {
				pool.submit(() -> leftRawPointsMap.get(mcpName)
						.parallelStream()
						.forEach(rawPoint -> {
							final int fromAddr = rawPoint.getAddress();
							final int toAddr = rawPoint.getLeftAddress();
							final String rawEdgeId = String.format("%05d", fromAddr) + "-" + String.format("%05d", toAddr);
							final String fromNodeId = DataSet.address2RailNodeId(fabId, mcpName, fromAddr);
							final String toNodeId = DataSet.address2RailNodeId(fabId, mcpName, toAddr);

							//	lanecut(railCut) 반영
							final boolean isAvailable = this._getRailEdgeAvailableByRailCut(mcp75ConfigMap, mcpName, rawEdgeId);

							final String id = DataSet.address2RailEdgeId(fabId, mcpName, fromAddr, toAddr);
							final RailEdge railEdge = new RailEdge(
									fabId,
									id,
									facId,
									mcpName,
									fromNodeId,
									toNodeId,
									true,
									rawPoint.getLeftDistance(),
									isUpdate,
									RAIL_DIRECTION.LEFT,
									fromAddr,
									toAddr
							);

							// railCut
							if (!isAvailable) {
								String railCutKey = fabId + ":" + mcpName + ":" + rawEdgeId;
								RailCutRecordItem recordItem = new RailCutRecordItem(
										railCutKey,
										fabId,
										facId,
										mcpName,
										fromAddr + ":" + toAddr,
										id,
										fromAddr,
										toAddr,
										null,
										null,
										OHT_TIB_STATE.ABNORMAL,
										false
								);

								tmpRailCutMap.put(railCutKey, recordItem);
							}
							//~railCut

							railEdge.setMaxVelocity(
									mcp75ConfigMap.get(mcpName)
											.getRawVhlSpeedMap()
											.get(
													mcp75ConfigMap.get(mcpName)
															.getVhlSpeedType()
											).get(rawPoint.getLeftSpeed())
											.getSpeed()
							);
							railEdge.setVelocity(railEdge.getMaxVelocity());

							final ConcurrentLinkedQueue<RawStation> rawStations = mapStationOnLeftMap.get(mcpName).get(fromAddr);

							if (rawStations != null && !rawStations.isEmpty()) {
								List<String> portIdList = rawStations.stream()
										.map(RawStation::getPortId)
										.filter(portId -> (!portId.isEmpty()) && !(portId.startsWith("ST-") || portId.contains("-")))
										.collect(Collectors.toList());

								railEdge.setPortIdList(portIdList);
							}

							railEdge.setStationIdList(railEdge.getStationIdList());
							railEdge.setAvailable(isAvailable);

							tmpRailEdgeMap.put(id, railEdge);

							// Makes a map to search a RailEdge quickly with an address.
							ConcurrentLinkedQueue<RawEdge> rawEdges = mapFromNode2RawEdgeMap.get(mcpName).computeIfAbsent(fromAddr, k -> new ConcurrentLinkedQueue<>());

							rawEdges.add(new RawEdge(fromAddr, toAddr, id));
							//~

							railNodeLeftEdgeIdMap.put(fromNodeId, id);
						})).get();
			} catch (InterruptedException e) {
				logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
			} catch (ExecutionException e) {
				logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
			}
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "(Left) RailEdge Building");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "(Right) RailEdge Building");
		startBlock = System.currentTimeMillis();

		for (String mcpName : leftRawPointsMap.keySet()) {
			try {
				pool.submit(() -> rightRawPointsMap.get(mcpName)
						.parallelStream()
						.forEach(rawPoint -> {
							final int fromAddr = rawPoint.getAddress();
							final int toAddr = rawPoint.getRightAddress();
							final String rawEdgeId = String.format("%05d", fromAddr) + "-" + String.format("%05d", toAddr);
							final String fromNodeId = DataSet.address2RailNodeId(fabId, mcpName, fromAddr);
							final String toNodeId = DataSet.address2RailNodeId(fabId, mcpName, toAddr);

							//	lanecut(railCut) 반영
							final boolean isAvailable = this._getRailEdgeAvailableByRailCut(mcp75ConfigMap, mcpName, rawEdgeId);

							final String id = DataSet.address2RailEdgeId(fabId, mcpName, fromAddr, toAddr);
							final RailEdge railEdge = new RailEdge(
									fabId,
									id,
									facId,
									mcpName,
									fromNodeId,
									toNodeId,
									true,
									rawPoint.getRightDistance(),
									isUpdate,
									RAIL_DIRECTION.RIGHT,
									fromAddr,
									toAddr
							);

							// railCut
							if (!isAvailable) {
								String railCutKey = fabId + ":" + mcpName + ":" + rawEdgeId;
								RailCutRecordItem recordItem = new RailCutRecordItem(
										railCutKey,
										fabId,
										facId,
										mcpName,
										fromAddr + ":" + toAddr,
										id,
										fromAddr,
										toAddr,
										null,
										null,
										OHT_TIB_STATE.ABNORMAL,
										false
								);

								tmpRailCutMap.put(railCutKey, recordItem);
							}
							//~railCut

							railEdge.setMaxVelocity(
									mcp75ConfigMap.get(mcpName)
											.getRawVhlSpeedMap()
											.get(
													mcp75ConfigMap.get(mcpName)
															.getVhlSpeedType()
											)
											.get(rawPoint.getRightSpeed())
											.getSpeed()
							);

							railEdge.setVelocity(railEdge.getMaxVelocity());

							final ConcurrentLinkedQueue<RawStation> rawStations = mapStationOnRightMap.get(mcpName).get(fromAddr);

							if (rawStations != null && !rawStations.isEmpty()) {
								List<String> portIdList = rawStations.stream()
										.map(RawStation::getPortId)
										.filter(portId -> (!portId.isEmpty()) && !(portId.startsWith("ST-") || portId.contains("-")))
										.collect(Collectors.toList());

								railEdge.setPortIdList(portIdList);
							}

							railEdge.setStationIdList(railEdge.getStationIdList());
							railEdge.setAvailable(isAvailable);

							tmpRailEdgeMap.put(id, railEdge);

							// Makes a map to search a RailEdge quickly with an address.
							ConcurrentLinkedQueue<RawEdge> rawEdges = mapFromNode2RawEdgeMap.get(mcpName).computeIfAbsent(fromAddr, k -> new ConcurrentLinkedQueue<>());

							rawEdges.add(new RawEdge(fromAddr, toAddr, id));
							//~

							railNodeRightEdgeIdMap.put(fromNodeId, id);
						})).get();
			} catch (InterruptedException e) {
				logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
			} catch (ExecutionException e) {
				logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
			}
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "(Right) RailEdge Building");
		//~

		// ↓ (RailEdge) address 값을 통해 빠르게 조회할 수 있도록 map 데이터 구성
		this._START_PROCESS_LOG(++sequence, "Making RailEdge Map Data");
		startBlock = System.currentTimeMillis();

		final ConcurrentMap<String, List<RailEdge>> mapFromNode2RailEdge = new ConcurrentHashMap<>();
		final ConcurrentMap<String, List<RailEdge>> mapToNode2RailEdge = new ConcurrentHashMap<>();

		try {
			for (RailEdge railEdge : tmpRailEdgeMap.values()) {
				final String fromNode = railEdge.getFromNodeId();
				final String toNode = railEdge.getToNodeId();

				List<RailEdge> railEdges = mapFromNode2RailEdge.computeIfAbsent(fromNode, k -> new ArrayList<>());

				railEdges.add(railEdge);

				railEdges = mapToNode2RailEdge.computeIfAbsent(toNode, k -> new ArrayList<>());

				railEdges.add(railEdge);
			}
		} catch (Exception e) {
			logger.error(EXCEPTION_LOG, String.format("%02d", sequence), e);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Making RailEdge Map Data");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "RailNode Building");
		startBlock = System.currentTimeMillis();

		for (String mcpName : mcp75ConfigMap.keySet()) {
			try {
				pool.submit(() -> mcp75ConfigMap.get(mcpName).getRawPointMap().values()
						.parallelStream()
						.forEach(rawPort -> {
							int address = rawPort.getAddress();
							String railNodeId = DataSet.address2RailNodeId(fabId, mcpName, address);
							RailNode railNode = new RailNode(
									fabId,
									railNodeId,
									Integer.toString(address),
									mcpName,
									rawPort.getDrawX(),
									rawPort.getDrawY(),
									rawPort.getCadX(),
									rawPort.getCadY(),
									rawPort.getCadZ(),
									isUpdate,
									railNodeLeftEdgeIdMap.get(railNodeId),
									railNodeRightEdgeIdMap.get(railNodeId),
									address
							);
							List<RailEdge> railEdges = mapFromNode2RailEdge.get(railNodeId);

							if (railEdges != null) {
								railEdges.forEach(railEdge -> railNode.getToEdgeIds().add(railEdge.getId()));
							}

							railEdges = mapToNode2RailEdge.get(railNodeId);

							if (railEdges != null) {
								railEdges.forEach(railEdge -> railNode.getFromEdgeIds().add(railEdge.getId()));
							}

							boolean isBranch = railNode.getToEdgeIds().size() > 1;
							boolean isRailBranch = railNode.isBranch();
							boolean isJunction = railNode.getFromEdgeIds().size() > 1;
							boolean isRailJunction = railNode.isJunction();
							boolean isTerminal = (
									rawPort.getLeftAddress() == rawPort.getRightAddress()
											|| railNode.getFromEdgeIds().isEmpty()
											|| railNode.getToEdgeIds().isEmpty()
							);

							railNode.setBranch(isBranch);
							railNode.setRailBranch(isRailBranch);
							railNode.setJunction(isJunction);
							railNode.setRailJunction(isRailJunction);
							railNode.setTerminal(isTerminal);

							tmpNodeMap.put(railNodeId, railNode);
						})).get();
			} catch (InterruptedException e) {
				logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
			} catch (ExecutionException e) {
				logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
			}
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "RailNode Building");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "StkPortNode Building");
		startBlock = System.currentTimeMillis();
		
		try {			
			DataTable result = OracleAPI.select(fabId, "SELECT_STK_PORT_INF");
			if (result != null)
			{
				for (DataRow dataRow : result.getRows()) {
					boolean isBridgeFromEqp = false; // Bridge Owner(From) Fab 에서만 등록

					for (Set<String> stringSet : fabPropertiesMap.get(fabId).getBridgeFromSet().values()) {
						if (stringSet.contains(dataRow.getString("MACHINENAME"))) {
							isBridgeFromEqp = true;
							break;
						}
					}

					if (!isBridgeFromEqp) {
						String stkPortName = fabId + ":" + DataSet.STK_PORT_NODE_PREFIX + ":" + dataRow.getString("ZONENAME");
						StkPortNode stkPortNode = (StkPortNode) tmpNodeMap.get(stkPortName);

						if (stkPortNode == null) {
							stkPortNode = new StkPortNode(
									fabId,
									stkPortName,
									dataRow.getString("ZONENAME"),
									fabId + ":" + DataSet.STK_PREFIX + ":" + dataRow.getString("MACHINENAME"),
									dataRow.get("MAXCAPA", Integer.class),
									dataRow.get("FLOOR", Integer.class),
									STK_PORT_INOUT_TYPE.valueOf(dataRow.getString("INOUTTYPE")),
									"T".equals(dataRow.getString("AVAILABILITY")),
									isUpdate
							);
						}
						stkPortNode.getSubPortList().add(
								stkPortNode.new SubPort(
										STK_SUB_PORT_TYPE.valueOf(dataRow.getString("PORTTYPE")),
										dataRow.getString("PORTNAME")
								)
						);

						stkPortNode.setSubPortList(stkPortNode.getSubPortList());

						tmpNodeMap.put(stkPortNode.getId(), stkPortNode);
					}
				}
			}			
		}
		catch (Exception e) {
            logger.error("", e);
        }

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "StkPortNode Building");
		//~

		this._START_PROCESS_LOG(++sequence, "CnvPortNode Building");
		startBlock = System.currentTimeMillis();
		
		try {
			pool.submit(()->{
				fabProperties.getCnvSocketIOListenerMap().entrySet().parallelStream().forEach(entry ->{
					String eqpNm = entry.getKey();
					CnvSocketIOListener csil = entry.getValue();					
					for(RawCnvZone rcz : csil.getRawCnvZoneMap().values()) {
						try
						{
							String id = "";
							int zoneNo = rcz.zoneId;
							String currentNodeId = "";//rcz.currentNode;
							String prevNodeId = "";//rcz.prevNode;
							String groupId = "";    		
							int level = rcz.level;
							String displayFabId = "";
							String displayMcpName = "";
							// 일단 하드코딩....
							// Todo::ICPKT, ICPNT 추가해야 함 
							if( level == 0 ){
								displayFabId = "M14A";
								displayMcpName = "A";			    			
							}else{
								displayFabId = "M16A";
								displayMcpName = "BR";
							}
							String eqpId = fabId+":"+DataSet.CNV_PREFIX+":"+eqpNm;
							double drawX = rcz.posX;
							double drawY = rcz.posY;
							int zoneDrawCount = rcz.zoneDrawCount;
							String containingZoneId1 = "";
							String containingZoneId2 = "";
							CNV_NODE_TYPE type = CNV_NODE_TYPE.ZONE;
							CNV_REF_DIR dir = rcz.refDirection==0?CNV_REF_DIR.UP:rcz.refDirection==1?CNV_REF_DIR.DOWN:rcz.refDirection==2?CNV_REF_DIR.LEFT:CNV_REF_DIR.RIGHT;
							if(rcz.currentNode >=0) {
								RawCnvZone rpz = csil.getRawCnvZoneMap().get(rcz.currentNode);
								if(rpz != null)
								switch(rpz.physicalType) {
								case 0 : 
								case 1 :
								case 4 :
								case 5 :
									currentNodeId = fabId+":"+DataSet.CNV_PORT_NODE_PREFIX+":"+eqpNm+"_"+rpz.zoneId;
									break;
								default :
									currentNodeId = fabId+":"+DataSet.CNV_PORT_NODE_PREFIX+":"+rpz.displayName;
									break;
								}
							}
							if(rcz.prevNode >=0) {
								RawCnvZone rpz = csil.getRawCnvZoneMap().get(rcz.prevNode);
								if(rpz != null)
								switch(rpz.physicalType) {
								case 0 : 
								case 1 :
								case 4 :
								case 5 :
									prevNodeId = fabId+":"+DataSet.CNV_PORT_NODE_PREFIX+":"+eqpNm+"_"+rpz.zoneId;
									break;
								default :
									prevNodeId = fabId+":"+DataSet.CNV_PORT_NODE_PREFIX+":"+rpz.displayName;
									break;
								}
							}
							switch(rcz.physicalType) {
								//0: Zone
								//1: QS/Lifter bed
								//2: input
								//3: output
								//4: QS
								//5: lifter
								case 1 :
								{
									id = fabId+":"+DataSet.CNV_PORT_NODE_PREFIX+":"+eqpNm+"_"+rcz.zoneId;        		
									type = CNV_NODE_TYPE.BED;
									containingZoneId1 = fabId+":CPN:"+eqpNm+"_"+rcz.ldAttr.included;
								}break;
								case 2 :
								{
									id = fabId+":"+DataSet.CNV_PORT_NODE_PREFIX+":"+rcz.displayName;        		
									type = CNV_NODE_TYPE.INPUT;
								}break;
								case 3 :
								{
									id = fabId+":"+DataSet.CNV_PORT_NODE_PREFIX+":"+rcz.displayName;        		
									type = CNV_NODE_TYPE.OUTPUT;
								}break;
								case 4 :
								{
									id = fabId+":"+DataSet.CNV_PORT_NODE_PREFIX+":"+eqpNm+"_"+rcz.zoneId;        		
									type = CNV_NODE_TYPE.QS;
									containingZoneId1 = fabId+":CPN:"+eqpNm+"_"+rcz.qsAttr.included;
								}break;
								case 5 :
								{
									id = fabId+":"+DataSet.CNV_PORT_NODE_PREFIX+":"+eqpNm+"_"+rcz.zoneId;        		
									type = CNV_NODE_TYPE.LFT;
									containingZoneId1 = fabId+":CPN:"+eqpNm+"_"+rcz.lftAttr.inIncludeZoneId;
									containingZoneId2 = fabId+":CPN:"+eqpNm+"_"+rcz.lftAttr.outIncludeZoneId;
								}break;
								default :
								{
									id = fabId+":"+DataSet.CNV_PORT_NODE_PREFIX+":"+eqpNm+"_"+rcz.zoneId;        		
									type = CNV_NODE_TYPE.ZONE;
									
								}break;
							}
							if(type==CNV_NODE_TYPE.BED && rcz.ldAttr != null && csil.getRawCnvZoneMap().get(rcz.ldAttr.included) != null && csil.getRawCnvZoneMap().get(rcz.ldAttr.included).physicalType == 4) {
								// do nothing.
							}else {
								CnvPortNode cnp = new CnvPortNode(fabId, id, rcz.displayName, eqpId, zoneNo, 
										containingZoneId1, containingZoneId2, currentNodeId, prevNodeId, groupId, 
										level, displayFabId, displayMcpName, drawX, drawY, 
										type, dir, 1, rcz.state, true, isUpdate);
								if(StringUtils.isNotEmpty(id)) {
									tmpNodeMap.put(id, cnp);
									tmpCnvPortNodeNoMap.put(cnp.getEqpId()+":"+zoneNo, cnp);
								}else {
									logger.warn("Check RawCnvZone! physicalType : {}, zoneId : {}, displayName : {}", rcz.physicalType, rcz.zoneId, rcz.displayName);
								}
							}
						}
						catch(Exception _ex) {
							logger.error(":::::::::: rcz error : {}",_ex);
						}
					}
				});
			}).get();
		} catch (InterruptedException e1) {
			logger.error("",e1);
		} catch (ExecutionException e1) {
			logger.error("",e1);
		}
		ConcurrentMap<String, ConcurrentLinkedQueue<String>> cnvGroupNodeIdMap = new ConcurrentHashMap<String, ConcurrentLinkedQueue<String>>();
		try {			
            DataTable result = OracleAPI.select(fabId, "SELECT_CNV_PORT_GROUP_INF");
            if(result != null)
            {
            	for(DataRow dr : result.getRows()) {
                	String cnvPortNm = dr.getString("CNVPORTNAME");
                	String cnvPortGrpNm = dr.getString("CNVPORTGROUPNAME");
                	
        			if(cnvGroupNodeIdMap.containsKey(cnvPortGrpNm) == false) {
        				cnvGroupNodeIdMap.put(cnvPortGrpNm, new ConcurrentLinkedQueue<String>());
        			}
        			cnvGroupNodeIdMap.get(cnvPortGrpNm).add(cnvPortNm);
                }	
            }                                   
		}
		catch (Exception e1) {
			logger.error("",e1);
		}
		
		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "CnvPortNode Building");
		
		//
		this._START_PROCESS_LOG(++sequence, "StkRmNode Building");
		startBlock = System.currentTimeMillis();

		try {
			DataTable result = OracleAPI.select(fabId, "SELECT_STK_RM_INF");		
			if(result != null)
			{
				try {
					pool.submit(() -> result.getRows()
							.parallelStream()
							.forEach(dataRow -> {
								boolean isBridgeFromEqp = false; // Bridge Owner(From) Fab 에서만 등록
								String name = dataRow.getString("NAME");
								String machineName = dataRow.getString("MACHINENAME");

								for (Set<String> stringSet : fabPropertiesMap.get(fabId).getBridgeFromSet().values()) {
									if (stringSet.contains(machineName)) {
										isBridgeFromEqp = true;
										break;
									}
								}

								if (!isBridgeFromEqp) {
									String id = fabId + ":" + DataSet.STK_RM_NODE_PREFIX + ":" + name;
									StkRmNode stkRmNode = new StkRmNode(
											fabId,
											id,
											name,
											fabId + ":" + DataSet.STK_PREFIX + ":" + machineName,
											"T".equals(dataRow.getString("AVAILABLE")),
											dataRow.get("MAXCAPA", Integer.class),
											isUpdate
									);
									tmpNodeMap.put(id, stkRmNode);
								}
							})).get();
				} catch (InterruptedException e) {
					logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
				} catch (ExecutionException e) {
					logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
				}	
			}
		}
		catch (Exception e1) {
			logger.error("",e1);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "StkRmNode Building");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "StkShelfNode Building");
		startBlock = System.currentTimeMillis();

		try {
			DataTable result = OracleAPI.select(fabId, "SELECT_STK_SHELF_INF");
			if(result != null)
			{
				try {
					pool.submit(() -> result.getRows()
							.parallelStream()
							.forEach(dataRow -> {
								boolean isBridgeFromEqp = false;    //	Bridge Owner(From) Fab 에서만 등록
								String name = dataRow.getString("NAME");
								String machineName = dataRow.getString("MACHINENAME");

								for (Set<String> stringSet : fabPropertiesMap.get(fabId).getBridgeFromSet().values()) {
									if (stringSet.contains(machineName)) {
										isBridgeFromEqp = true;
										break;
									}
								}

								if (!isBridgeFromEqp) {
									String id = fabId + ":" + DataSet.STK_SHELF_NODE_PREFIX + ":" + name;
									StkShelfNode stkShelfNode = new StkShelfNode(
											fabId,
											id,
											name,
											fabId + ":" + DataSet.STK_PREFIX + ":" + machineName,
											dataRow.get("MAXCAPA", Integer.class),
											"T".equals(dataRow.getString("AVAILABLE")),
											isUpdate
									);

									for (String processType : dataRow.getString("PROCESSTYPELIST").split(",")) {
										try {
											stkShelfNode.getProcessTypeSet().add(PROCESS_TYPE.valueOf(processType));
										} catch (Exception e) {
											logger.error("[StkShelfNode Building] {} is not exists in Carrier.PROCESS_TYPE. Skip registering.", processType, e);
										}
									}

									stkShelfNode.setProcessTypeSet(stkShelfNode.getProcessTypeSet());

									tmpNodeMap.put(id, stkShelfNode);
								}
							})).get();
				} catch (InterruptedException e) {
					logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
				} catch (ExecutionException e) {
					logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
				}	
			}
		}
		catch (Exception e1) {
			logger.error("",e1);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "StkShelfNode Building");
		//~
		
		//
		this._START_PROCESS_LOG(++sequence, "StbNode building");
		startBlock = System.currentTimeMillis();
		
		try {
			DataTable result = OracleAPI.select(fabId, "SELECT_STB_PORT_INF");
			if(result != null)
			{
				try {
					pool.submit(() -> result.getRows()
							.parallelStream()
							.forEach(dataRow -> {
								String stbNodeName = fabId + ":"+ DataSet.STB_PORT_NODE_PREFIX+ ":" + dataRow.getString("NAME");
				            	StbNode sbn = new StbNode(fabId, 
				            			stbNodeName, 
				            			dataRow.getString("NAME"), 
				            			"T".equals(dataRow.getString("AVAILABILITY")), 
				            			"T".equals(dataRow.getString("ISN2")),
				            			fabId + ":"+ DataSet.STB_GROUP_PREFIX+ ":" + dataRow.getString("MACHINENAME"),
				            			"T".equals(dataRow.getString("ISREADER")), 
				            			isUpdate);        		
				        		tmpNodeMap.put(sbn.getId(),sbn);
							})).get();
				} catch (InterruptedException e) {
					logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
				} catch (ExecutionException e) {
					logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
				}	
			}
		}
		catch (Exception e1) {
			logger.error("",e1);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "StbNode Building");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "EqpPortNode Building");
		startBlock = System.currentTimeMillis();

		try {
			DataTable result = OracleAPI.select(fabId, "SELECT_EQP_PORT_INF");
			if(result != null)
			{
				try {
					pool.submit(() -> result.getRows()
							.parallelStream()
							.forEach(dataRow -> {
								String id = fabId + ":" + DataSet.EQP_PORT_NODE_PREFIX + ":" + dataRow.getString("NAME");
								EqpPortNode eqpPortNode = new EqpPortNode(
										fabId,    // fab id
										id,
										dataRow.getString("NAME"),    // name
										fabId + ":" + DataSet.EQP_PREFIX + ":" + dataRow.getString("MACHINENAME"),    // eqp id
										null,    // from edge ids
										null,    // to edge ids
										null,    // from long edge ids
										null,    // to long edge ids
										null,    // process type set
										"",        // carrier id
										"T".equals(dataRow.getString("AVAILABILITY")),    // available
										isUpdate    // is update
								);
								tmpNodeMap.put(id, eqpPortNode);
							})).get();
				} catch (InterruptedException e) {
					logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
				} catch (ExecutionException e) {
					logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
				}	
			}			
		}
		catch (Exception e1) {
			logger.error("",e1);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "EqpPortNode Building");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "FioPortNode Building");
		startBlock = System.currentTimeMillis();

		//	Perarell 처리시 subPort가 일부 누락될 가능성 있음.
		try {
			DataTable result = OracleAPI.select(fabId, "SELECT_FIO_PORT_INF");
			if(result != null)
			{
				for (DataRow dataRow : result.getRows()) {
					String portName = dataRow.getString("PORTNAME");
					String id = fabId + ":" + DataSet.FIO_PORT_NODE_PREFIX + ":" + portName;
					FioPortNode fioPortNode = (FioPortNode) tmpNodeMap.get(id);

					if (fioPortNode == null) {
						fioPortNode = new FioPortNode(
								fabId,
								id,
								portName,
								fabId + ":" + DataSet.FIO_PREFIX + ":" + dataRow.getString("MACHINENAME"),
								"T".equals(dataRow.getString("AVAILABLE")),
								FIO_PORT_INOUT_TYPE.valueOf(dataRow.getString("INOUTTYPE")),
								isUpdate
						);
						tmpNodeMap.put(id, fioPortNode);
					}

					fioPortNode.getSubPortList().add(
							fioPortNode.new SubPort(
									FIO_SUB_PORT_TYPE.valueOf(dataRow.getString("PORTTYPE")),
									dataRow.getString("SUBPORT"),
									FIO_SUB_PORT_ACCESSMODE.valueOf(dataRow.getString("ACCESSMODE"))
							)
					);
					fioPortNode.setSubPortList(fioPortNode.getSubPortList());
				}	
			}			
		}
		catch (Exception e1) {
			logger.error("",e1);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "FioPortNode Building");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "Setting Out/In Port");
		startBlock = System.currentTimeMillis();

		ConcurrentMap<String, AbstractNode> outPortNameNodeMap = new ConcurrentHashMap<>();
		ConcurrentMap<String, AbstractNode> inPortNameNodeMap = new ConcurrentHashMap<>();

		try {
			pool.submit(() -> tmpNodeMap.values()
					.parallelStream()
					.forEach(node -> {
						if (
								!(node instanceof RailNode)
										&& !(node instanceof StkPortNode)
										&& !(node instanceof FioPortNode)
										&& !(node instanceof CnvPortNode)
						) {
							outPortNameNodeMap.put(node.getName(), node);

							inPortNameNodeMap.put(node.getName(), node);
						} else if (node instanceof StkPortNode) {
							for (StkPortNode.SubPort subPort : ((StkPortNode) node).getSubPortList()) {
								String name = subPort.name;

								switch (((StkPortNode) node).getInOutType()) {
									case OUT: {
										outPortNameNodeMap.put(name, node);
									}
									break;
									case IN: {
										inPortNameNodeMap.put(name, node);
									}
									break;
								}
							}
						} else if (node instanceof FioPortNode) {
							for (FioPortNode.SubPort subPort : ((FioPortNode) node).getSubPortList()) {
								String name = subPort.name;

								switch (((FioPortNode) node).getInOutType()) {
									case OUT: {
										outPortNameNodeMap.put(name, node);
									}
									break;
									case IN: {
										inPortNameNodeMap.put(name, node);
									}
									break;
									case BOTH: {
										outPortNameNodeMap.put(name, node);

										inPortNameNodeMap.put(name, node);
									}
									break;
								}
							}
						}
					})).get();
		} catch (InterruptedException e) {
			logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
		} catch (ExecutionException e) {
			logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Setting Out/In Port");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "Station & TransferEdge Building");
		startBlock = System.currentTimeMillis();

		for (String mcpName : mcp75ConfigMap.keySet()) {
			try {
				pool.submit(() -> mcp75ConfigMap.get(mcpName).getRawStationMap().values()
						.parallelStream()
						.forEach(rawStation -> {
							try {
								String stationId = fabId + ":" + DataSet.STATION_PREFIX + ":" + mcpName + ":" + String.format("%05d", rawStation.getStNo());
								String railNodeId = DataSet.address2RailNodeId(fabId, mcpName, rawStation.getAddress_no());
								String portId = rawStation.getPortId();
								double offset = rawStation.getLeftDistance() + rawStation.getRightDistance();
								String railEdgeId = (
										rawStation.getStationLocation() == STATION_LOCATION.LEFT_BRANCH
												|| rawStation.getStationLocation() == STATION_LOCATION.NO_CONDITION
								) ? DataSet.address2RailEdgeId(
										fabId,
										mcpName,
										rawStation.getAddress_no(),
										mcp75ConfigMap.get(mcpName).getRawPointMap().get(rawStation.getAddress_no()).getLeftAddress()
								)
										: DataSet.address2RailEdgeId(
										fabId,
										mcpName,
										rawStation.getAddress_no(),
										mcp75ConfigMap.get(mcpName).getRawPointMap().get(rawStation.getAddress_no()).getRightAddress()
								);

								STATION_TYPE stationType = rawStation.getStationType();
								int carryType = rawStation.getTransportCarrierType();
								Station station = new Station(
										fabId,
										stationId,
										mcpName,
										railNodeId,
										carryType,
										offset,
										railEdgeId,
										stationType,
										portId,
										rawStation.getDrawX(),
										rawStation.getDrawY(),
										isUpdate
								);

								boolean isBridgeFromPort = false;    //	Bridge Owner(From) Fab 에서만 등록한다.

								if (portId.indexOf('_') > 0) {
									String tmpEqpId;

									if (portId.contains("A_")) {
										tmpEqpId = portId.substring(0, portId.indexOf('_') - 1);
									} else {
										tmpEqpId = portId.substring(0, portId.indexOf('_'));
									}

									for (Set<String> stringSet : fabPropertiesMap.get(fabId).getBridgeFromSet().values()) {
										isBridgeFromPort = (
												stringSet.contains(tmpEqpId)
														|| stringSet.contains(tmpEqpId.substring(0, tmpEqpId.length() - 1))
										);

										if (isBridgeFromPort) break;
									}
								}

								if (station.getStationType() != STATION_TYPE.DEPOSIT) {
									if (isBridgeFromPort) {
										//	Ziptower가 연결되는 경우 후속 Fab간 Connection 작업에서 TransferEdge를 마저 작업해준다.
										tmpStationMap.put(station.getId(), station);

										RailNode rn = (RailNode) tmpNodeMap.get(railNodeId);

										if (rn != null) {
											rn.setTeConnection(true);
										}
									} else {
										String fromNodeId = "";
										String toNodeId;
										String toStationId;
										AbstractNode node = outPortNameNodeMap.get(portId);

										if (node != null) {
											fromNodeId = node.getId();
										}

										toNodeId = railNodeId;
										toStationId = stationId;

										if (!StringUtils.isEmpty(fromNodeId) && !StringUtils.isEmpty(toNodeId)) {
											double telen;

											if (fromNodeId.contains(":" + DataSet.STK_PORT_NODE_PREFIX + ":")) {
												telen = 2000;
											} else if (fromNodeId.contains(":" + DataSet.STB_PORT_NODE_PREFIX + ":")) {
												telen = 1000;
											} else {
												telen = 4000;
											}

											TransferEdge transferEdge = new TransferEdge(
													fabId,
													fabId + ":" + DataSet.TRANS_EDGE_PREFIX + ":" + fromNodeId + "-" + toStationId,
													fromNodeId,
													toNodeId,
													"",
													stationId,
													7000,
													true,
													true,
													telen,
													isUpdate
											);

											tmpNodeMap.get(fromNodeId).setTeConnection(true);
											tmpNodeMap.get(toNodeId).setTeConnection(true);

											tmpTransferEdgeMap.put(transferEdge.getId(), transferEdge);

											tmpStationMap.put(station.getId(), station);

											station.setAcquireTransferEdgeId(transferEdge.getId());
										} else {
											RailEdge railEdge = tmpRailEdgeMap.get(station.getRailEdgeId());
											Queue<String> stationIdList = railEdge.getStationIdList();

											stationIdList.remove(stationId);

											tmpRailEdgeMap.get(station.getRailEdgeId()).setStationIdList(railEdge.getStationIdList());
										}
									}
									// edge설정 필요.
								}

								if (station.getStationType() == STATION_TYPE.DUAL_ACCESS || station.getStationType() == STATION_TYPE.DEPOSIT) {
									if (isBridgeFromPort) {
										// Ziptower가 연결되는 경우 후속 Fab간 Connection 작업에서 TransferEdge를 마저 작업해준다.
										tmpStationMap.put(station.getId(), station);

										RailNode railNode = (RailNode) tmpNodeMap.get(railNodeId);

										if (railNode != null) {
											railNode.setTeConnection(true);
										}
									} else {
										String fromNodeId;
										String toNodeId = "";
										AbstractNode node = inPortNameNodeMap.get(portId);

										if (node != null) {
											toNodeId = node.getId();
										}

										fromNodeId = railNodeId;

										if (!StringUtils.isEmpty(fromNodeId) && !StringUtils.isEmpty(toNodeId)) {
											double telen;

											if (toNodeId.contains(":" + DataSet.STK_PORT_NODE_PREFIX + ":")) {
												telen = 2000;
											} else if (toNodeId.contains(":" + DataSet.STB_PORT_NODE_PREFIX + ":")) {
												telen = 1000;
											} else {
												telen = 4000;
											}

											String transferEdgeId = fabId + ":" + DataSet.TRANS_EDGE_PREFIX + ":" + stationId + "-" + toNodeId;
											TransferEdge transferEdge = new TransferEdge(
													fabId,
													transferEdgeId,
													fromNodeId,
													toNodeId,
													stationId,
													"",
													7000,
													false,
													true,
													telen,
													isUpdate
											);

											transferEdge.setAcqEdge(false);

											tmpTransferEdgeMap.put(transferEdgeId, transferEdge);

											tmpStationMap.put(stationId, station);

											tmpNodeMap.get(fromNodeId).setTeConnection(true);
											tmpNodeMap.get(toNodeId).setTeConnection(true);

											station.setDepositTransferEdgeId(transferEdge.getId());
										} else {
											tmpRailEdgeMap.get(station.getRailEdgeId()).getStationIdList().remove(station.getId());
											tmpRailEdgeMap.get(station.getRailEdgeId())
													.setStationIdList(
															tmpRailEdgeMap.get(station.getRailEdgeId()).getStationIdList()
													);
										}
										// edge설정 필요.
									}
								}
							} catch (Exception e) {
								logger.error("{} {} Station building error RawStation : {}", fabId, mcpName, JsonUtil.convertJSON(rawStation), e);
							}
						})).get();
			} catch (InterruptedException e) {
				logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
			} catch (ExecutionException e) {
				logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
			}
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Station & TransferEdge Building");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "Eqps, StkRmEdge, Vhl Building");
		startBlock = System.currentTimeMillis();

		try {
			DataTable result = OracleAPI.select(fabId, "SELECT_EQP_INF");
			if(result != null)
			{
				try {
					pool.submit(() -> result.getRows()
							.parallelStream()
							.forEach(dataRow -> {
								try {
									String id = dataRow.getString("ID");
									boolean isBridgeFromEqp = false;    //	Bridge Owner(From) Fab 에서만 등록한다.

									for (Set<String> stringSet : fabPropertiesMap.get(fabId).getBridgeFromSet().values()) {
										if (stringSet.contains(id)) {
											isBridgeFromEqp = true;
											break;
										}
									}

									if (isBridgeFromEqp) return; // BridgeFrom에 등록된 장비인 경우 Skip

									boolean isN2 = "T".equals(dataRow.getString("ISN2"));
									Set<PROCESS_TYPE> processTypeSet = new HashSet<>();
									String processTypeList = dataRow.getString("PROCESSTYPELIST");
									boolean isAvailable = "T".equals(dataRow.getString("AVAILABLE"));
									String stkTyp = dataRow.getString("STK_TYP");
									EQP_TYPE eqpType = EQP_TYPE.valueOf(dataRow.getString("EQPTYPE"));

									if (StringUtils.isNotEmpty(processTypeList)) {
										for (String processType : processTypeList.split(",")) {
											processTypeSet.add(PROCESS_TYPE.valueOf(processType));
										}
									} else {
										processTypeSet.add(PROCESS_TYPE.FOUP);
									}

									if ("NORMAL".equalsIgnoreCase(stkTyp)) {
										stkTyp = "NA";
									}

									STK_TYPE stkType = STK_TYPE.valueOf(stkTyp);
									String mcsBayNm = dataRow.getString("MCSBAYNM");

									switch (eqpType) {
										case FIO: {
											String eqpId = fabId + ":" + DataSet.FIO_PREFIX + ":" + id;
											ConcurrentLinkedQueue<String> portList = new ConcurrentLinkedQueue<>();

											for (AbstractNode node : tmpNodeMap.values()) {
												if (eqpId.equals(node.getEqpId())) {
													portList.add(node.getId());
												}
											}

											boolean isVM = dataRow.getTable().getColumnCollection().contains("ISVM") && "T".equals(dataRow.getString("ISVM"));

											Fio fio = new Fio(
													fabId,
													eqpId,
													id,
													processTypeSet,
													portList,
													isAvailable,
													isUpdate,
													isVM,
													mcsBayNm
											);
											tmpFioMap.put(eqpId, fio);
										}
										break;
										case OHT: {    // vehicle & OHT 초기값을 모두 만듦
											String eqpId = fabId + ":" + DataSet.OHT_PREFIX + ":" + id;
											String mcpName = fabProperties.getOhtName2McpNameMap().get(id);

											logger.warn("eqpId : {}, mcpName : {}, id : {}", eqpId, mcpName, id);

											if (StringUtils.isNotEmpty(mcpName)) {
												for (RawVhl rawVhl : mcp75ConfigMap.get(mcpName).getRawVhlMap().values()) {
													String vhlId = fabId + ":" + DataSet.VHL_PREFIX + ":" + mcpName + ":" + rawVhl.getVhlId();
													Vhl vhl = new Vhl(
															vhlId,
															rawVhl.getVhlId(),
															mcpName,
															fabId,
															eqpId,
															rawVhl.getType(),
															isUpdate
													);

													tmpVhlMap.put(vhlId, vhl);
												}
												ConcurrentLinkedQueue<String> stationIdList = new ConcurrentLinkedQueue<>();

												for (String stId : tmpStationMap.keySet()) {
													if (stId.startsWith(fabId + ":" + DataSet.STATION_PREFIX + ":" + mcpName + ":")) {
														stationIdList.add(stId);
													}
												}

												ConcurrentLinkedQueue<String> vhlIdList = new ConcurrentLinkedQueue<>();

												for (String vId : tmpVhlMap.keySet()) {
													if (vId.startsWith(fabId + ":" + DataSet.VHL_PREFIX + ":" + mcpName + ":")) {
														vhlIdList.add(vId);
													}
												}

												Oht oht = new Oht(
														fabId,
														eqpId,
														id,
														mcpName,
														stationIdList,
														vhlIdList,
														true,
														isUpdate
												);
												tmpOhtMap.put(oht.getId(), oht);
											}
										}
										break;
										case STBGROUP :
						            	{
						            		String eqpId = fabId + ":"+ DataSet.STB_GROUP_PREFIX+ ":" + id;
						            		ConcurrentLinkedQueue<String> portList = new ConcurrentLinkedQueue<String>();
						            		for(AbstractNode an : tmpNodeMap.values()) {
						            			if(eqpId.equals(an.getEqpId()))
						            				portList.add(an.getId());
						            		}
						            		StbGroup sg = new StbGroup(fabId, eqpId, id, processTypeSet, portList, isN2, isAvailable, isUpdate, mcsBayNm);
						            		tmpStbGroupMap.put(eqpId, sg);
						            	}
					            		break;
										case STK: {
											String eqpId = fabId + ":" + DataSet.STK_PREFIX + ":" + id;
											ConcurrentLinkedQueue<String> portList = new ConcurrentLinkedQueue<>();

											for (AbstractNode node : tmpNodeMap.values()) {
												if (eqpId.equals(node.getEqpId()) && node instanceof StkPortNode) {
													portList.add(node.getId());
												}
											}

											String shelfNodeId = "";
											StkShelfNode shelfNode = null;

											for (AbstractNode an : tmpNodeMap.values()) {
												if (eqpId.equals(an.getEqpId()) && an instanceof StkShelfNode) {
													shelfNodeId = an.getId();
													shelfNode = (StkShelfNode) an;

													break;
												}
											}

											String rmId = "";

											for (AbstractNode an : tmpNodeMap.values()) {
												if (
														eqpId.equals(an.getEqpId())
																&& an instanceof StkRmNode
												) {
													rmId = an.getId();

													break;
												}
											}

											Stocker stk = new Stocker(
													fabId,
													eqpId,
													id,
													processTypeSet,
													portList,
													shelfNodeId,
													rmId,
													isN2,
													stkType,
													isAvailable,
													isUpdate,
													mcsBayNm
											);
											tmpStockerMap.put(eqpId, stk);

											//1. RM Edge 만들기.
											// 1. toRM
											// 2. fromRM
											// 3. shelf
											boolean isBridgeRm = (
													stk.getStkType() == STK_TYPE.ZIPTOWER
															|| stk.getStkType() == STK_TYPE.PODZIPTOWER
															|| stk.getStkType() == STK_TYPE.INTERLAYER
															|| stk.getStkType() == STK_TYPE.LIFTER
											);
											String stkRmEdgePrefixId = fabId + ":" + DataSet.STK_RM_EDGE_PREFIX;

											for (String portId : portList) {
												StkPortNode spn = (StkPortNode) tmpNodeMap.get(portId);

												if (spn.getInOutType() == STK_PORT_INOUT_TYPE.OUT) { // toRM
													String sreId = stkRmEdgePrefixId + ":" + rmId + "-" + spn.getId();
													StkRmEdge sre = new StkRmEdge(
															fabId,
															sreId,
															eqpId,
															rmId,
															spn.getId(),
															5000L,
															true,
															isBridgeRm ? 15000 : 4000,
															true,
															isBridgeRm,
															isUpdate
													);
													tmpStkRmEdgeMap.put(sreId, sre);
												} else if (spn.getInOutType() == STK_PORT_INOUT_TYPE.IN) { // toRM
													String sreId = stkRmEdgePrefixId + ":" + spn.getId() + "-" + rmId;
													StkRmEdge sre = new StkRmEdge(
															fabId,
															sreId,
															eqpId,
															spn.getId(),
															rmId,
															5000L,
															true,
															isBridgeRm ? 15000 : 4000,
															false,
															isBridgeRm,
															isUpdate
													);
													tmpStkRmEdgeMap.put(sreId, sre);
												}
											}

											if (shelfNode != null) {
												tmpStkRmEdgeMap.put(
														stkRmEdgePrefixId + ":" + rmId + "-" + shelfNodeId,
														new StkRmEdge(
																fabId,
																stkRmEdgePrefixId + rmId + "-" + shelfNodeId,
																eqpId,
																rmId,
																shelfNodeId,
																5000L,
																true,
																isBridgeRm ? 15000 : 4000,
																true,
																isBridgeRm,
																isUpdate
														)
												);
												tmpStkRmEdgeMap.put(
														stkRmEdgePrefixId + ":" + shelfNodeId + "-" + rmId,
														new StkRmEdge(
																fabId,
																stkRmEdgePrefixId + shelfNodeId + "-" + rmId,
																eqpId,
																shelfNodeId,
																rmId,
																5000L,
																true,
																isBridgeRm ? 15000 : 4000,
																false,
																isBridgeRm,
																isUpdate
														)
												);
											}
										}
										break;
										case CONVEYOR :
						            	{
//						            		final StringBuilder contentBuilder = new StringBuilder();
//						            		BufferedReader br = null;
//						            		File file = null;
//					            	        try{
//					            	        	String sLine = "";
//							            		file = new File(fabPropertiesMap.get(fabId).getMapDir() + "/" + id + ".conveyor.json");
//							            		br = new BufferedReader(new FileReader(file));
//							            		while((sLine = br.readLine())!=null) {
//							            			contentBuilder.append(sLine);
//							            		}					            		
//					            	        }
//						            		catch(Exception e) {
//												logger.error("",e);
//						            		}finally {
//						            			if(br!=null)
//						            				br.close();
//						            		}
						            		
						            		String eqpId = fabId + ":"+ DataSet.CNV_PREFIX+ ":" + id;
						            		Map<Integer,RawCnvZone> rawCnvZoneMap = fabProperties.getCnvSocketIOListenerMap().get(id).getRawCnvZoneMap();
						            		Set<String> noneedNodeNoSet = new HashSet<String>();
						                    Map<String,String[]> edgeIdMap = new ConcurrentHashMap<String, String[]>();
						                    //ConcurrentMap<String, ConcurrentLinkedQueue<String>> cnvGroupNodeIdMap = new ConcurrentHashMap<String, ConcurrentLinkedQueue<String>>();
						                    
						                    for(CnvPortNode cn : tmpCnvPortNodeNoMap.values().stream().filter(c->c.getEqpId().equals(eqpId)).collect(Collectors.toList())){				                    	
						                    	RawCnvZone rcz = rawCnvZoneMap.get(cn.getZoneNo());
						                    	CnvPortNode fcn = null;
						                    	CnvPortNode tcn = null;
						                    	
						                    	if(rcz == null) {
						                    		logger.warn("{} node {} zoneNo : {} rawCnvZoneMap is {}", eqpId, cn.getId(), cn.getZoneNo(), rcz);
						                    	}else {
						                    		logger.debug("RawCnvZone {} : {}", rcz.zoneId, JsonUtil.convertJSON(rcz));
						                    	}
						                    	if(rcz.prevZone > 0 && rcz.physicalType != 5 && rcz.physicalType != 4
						                    			&& (rcz.ldAttr == null || rcz.ldAttr.included < 0 || rawCnvZoneMap.get(rcz.ldAttr.included).physicalType != 5)) {
						                    		if(rawCnvZoneMap.get(rcz.prevZone) == null) {
							                    		logger.warn("{} node {} prevZone : {} rawCnvZoneMap.get(rcz.prevZone) is {}", eqpId, cn.getId(), rcz.prevZone, rcz);
							                    	}
						                    		if(rawCnvZoneMap.get(rcz.prevZone).physicalType == 5) {
						                    			fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.prevZone).lftAttr.outIncludeZoneId);
						                    			fcn.setType(CNV_NODE_TYPE.OUTLFT);
						                    			if(tmpCnvPortNodeNoMap.containsKey(cn.getEqpId()+":"+rcz.prevZone)) {
						                    				noneedNodeNoSet.add(cn.getEqpId()+":"+rcz.prevZone);
						                    			}        			
						                    		}else {
						                    			fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rcz.prevZone);
						                    			if(fcn==null) {
						                    				rcz.prevZone = rawCnvZoneMap.get(rcz.prevZone).ldAttr.included;
						                    				fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rcz.prevZone);
						                    			}
						                    		}
						                    		if(fcn.getId().equals(cn.getId()))
						                    			logger.warn("cnv edge equals {} and {}", fcn.getId(), cn.getId());
						                			String edgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + fcn.getId() + "-" + cn.getId();
						                			edgeIdMap.put(edgeId, new String[] {fcn.getId(), cn.getId()});
						                			if(cn.getFromEdgeIds().contains(edgeId) == false)
						                				cn.getFromEdgeIds().add(edgeId);
						                		}
						                    	if(rcz.nextZone > 0 && rcz.physicalType != 5 && rcz.physicalType != 4
						                    			&& (rcz.ldAttr == null || rcz.ldAttr.included < 0 || rawCnvZoneMap.get(rcz.ldAttr.included).physicalType != 5)) {
						                    		if(rawCnvZoneMap.get(rcz.nextZone).physicalType == 5) {
						                    			tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.nextZone).lftAttr.inIncludeZoneId);
						                    			tcn.setType(CNV_NODE_TYPE.INLFT);
						                    		}else {
						                    			tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rcz.nextZone);
						                    			if(tcn==null) {
						                    				rcz.nextZone = rawCnvZoneMap.get(rcz.nextZone).ldAttr.included;
						                    				tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rcz.nextZone);
						                    			}
						                    		}
						                    		if(cn.getId().equals(tcn.getId()))
						                    			logger.warn("cnv edge equals {} and {}", cn.getId(), tcn.getId());
						                			String edgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + cn.getId() + "-" + tcn.getId();
						                			edgeIdMap.put(edgeId, new String[] {cn.getId(), tcn.getId()});
						                			if(cn.getToEdgeIds().contains(edgeId) == false)
						                				cn.getToEdgeIds().add(edgeId);
						                		}
						                    	if(rcz.physicalType == 4) {//QS
						                    		if(rcz.qsAttr.east != null && rcz.qsAttr.east[1] == 0) {
						                    			fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.east[0]).zoneId);
						                    			if(fcn == null)
						                    				fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.east[0]).ldAttr.included);
						                    			if(fcn.getId().equals(cn.getId()))
							                    			logger.warn("cnv edge equals {} and {}", fcn.getId(), cn.getId());
							                			String edgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + fcn.getId() + "-" + cn.getId();
							                			edgeIdMap.put(edgeId, new String[] {fcn.getId(), cn.getId()});
							                			if(cn.getFromEdgeIds().contains(edgeId) == false)
							                				cn.getFromEdgeIds().add(edgeId);
							                			if(fcn.getToEdgeIds().contains(edgeId) == false)
							                				fcn.getToEdgeIds().add(edgeId);
						                    		}
						                    		if(rcz.qsAttr.west != null && rcz.qsAttr.west[1] == 0) {
						                    			fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.west[0]).zoneId);
						                    			if(fcn == null)
						                    				fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.west[0]).ldAttr.included);
						                    			if(fcn.getId().equals(cn.getId()))
							                    			logger.warn("cnv edge equals {} and {}", fcn.getId(), cn.getId());
							                			String edgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + fcn.getId() + "-" + cn.getId();
							                			edgeIdMap.put(edgeId, new String[] {fcn.getId(), cn.getId()});
							                			if(cn.getFromEdgeIds().contains(edgeId) == false)
							                				cn.getFromEdgeIds().add(edgeId);
							                			if(fcn.getToEdgeIds().contains(edgeId) == false)
							                				fcn.getToEdgeIds().add(edgeId);
						                    		}
						                    		if(rcz.qsAttr.north != null && rcz.qsAttr.north[1] == 0) {
						                    			fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.north[0]).zoneId);
						                    			if(fcn == null)
						                    				fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.north[0]).ldAttr.included);
						                    			if(fcn.getId().equals(cn.getId()))
							                    			logger.warn("cnv edge equals {} and {}", fcn.getId(), cn.getId());
							                			String edgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + fcn.getId() + "-" + cn.getId();
							                			edgeIdMap.put(edgeId, new String[] {fcn.getId(), cn.getId()});
							                			if(cn.getFromEdgeIds().contains(edgeId) == false)
							                				cn.getFromEdgeIds().add(edgeId);
							                			if(fcn.getToEdgeIds().contains(edgeId) == false)
							                				fcn.getToEdgeIds().add(edgeId);
						                    		}
						                    		if(rcz.qsAttr.south != null && rcz.qsAttr.south[1] == 0) {
						                    			fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.south[0]).zoneId);
						                    			if(fcn == null)
						                    				fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.south[0]).ldAttr.included);
						                    			if(fcn.getId().equals(cn.getId()))
							                    			logger.warn("cnv edge equals {} and {}", fcn.getId(), cn.getId());
							                			String edgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + fcn.getId() + "-" + cn.getId();
							                			edgeIdMap.put(edgeId, new String[] {fcn.getId(), cn.getId()});
							                			if(cn.getFromEdgeIds().contains(edgeId) == false)
							                				cn.getFromEdgeIds().add(edgeId);
							                			if(fcn.getToEdgeIds().contains(edgeId) == false)
							                				fcn.getToEdgeIds().add(edgeId);
						                    		}
						                    		if(rcz.qsAttr.east != null && rcz.qsAttr.east[1] == 1) {
						                    			tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.east[0]).zoneId);
						                    			if(tcn == null)
						                    				tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.east[0]).ldAttr.included);
						                    			if(tcn.getId().equals(cn.getId()))
							                    			logger.warn("cnv edge equals {} and {}", cn.getId(), tcn.getId());
							                			String edgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + cn.getId() + "-" + tcn.getId();
							                			edgeIdMap.put(edgeId, new String[] {cn.getId(), tcn.getId()});
							                			if(tcn.getFromEdgeIds().contains(edgeId) == false)
							                				tcn.getFromEdgeIds().add(edgeId);
							                			if(cn.getToEdgeIds().contains(edgeId) == false)
							                				cn.getToEdgeIds().add(edgeId);
						                    		}
						                    		if(rcz.qsAttr.west != null && rcz.qsAttr.west[1] == 1) {
						                    			tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.west[0]).zoneId);
						                    			if(tcn == null)
						                    				tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.west[0]).ldAttr.included);
						                    			if(tcn.getId().equals(cn.getId()))
							                    			logger.warn("cnv edge equals {} and {}", cn.getId(), tcn.getId());
							                			String edgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + cn.getId() + "-" + tcn.getId();
							                			edgeIdMap.put(edgeId, new String[] {cn.getId(), tcn.getId()});
							                			if(tcn.getFromEdgeIds().contains(edgeId) == false)
							                				tcn.getFromEdgeIds().add(edgeId);
							                			if(cn.getToEdgeIds().contains(edgeId) == false)
							                				cn.getToEdgeIds().add(edgeId);
						                    		}
						                    		if(rcz.qsAttr.north != null && rcz.qsAttr.north[1] == 1) {
						                    			tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.north[0]).zoneId);
						                    			if(tcn == null)
						                    				tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.north[0]).ldAttr.included);
						                    			if(tcn.getId().equals(cn.getId()))
							                    			logger.warn("cnv edge equals {} and {}", cn.getId(), tcn.getId());
							                			String edgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + cn.getId() + "-" + tcn.getId();
							                			edgeIdMap.put(edgeId, new String[] {cn.getId(), tcn.getId()});
							                			if(tcn.getFromEdgeIds().contains(edgeId) == false)
							                				tcn.getFromEdgeIds().add(edgeId);
							                			if(cn.getToEdgeIds().contains(edgeId) == false)
							                				cn.getToEdgeIds().add(edgeId);
						                    		}
						                    		if(rcz.qsAttr.south != null && rcz.qsAttr.south[1] == 1) {
						                    			tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.south[0]).zoneId);
						                    			if(tcn == null)
						                    				tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.qsAttr.south[0]).ldAttr.included);
						                    			if(tcn.getId().equals(cn.getId()))
							                    			logger.warn("cnv edge equals {} and {}", cn.getId(), tcn.getId());
							                			String edgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + cn.getId() + "-" + tcn.getId();
							                			edgeIdMap.put(edgeId, new String[] {cn.getId(), tcn.getId()});
							                			if(tcn.getFromEdgeIds().contains(edgeId) == false)
							                				tcn.getFromEdgeIds().add(edgeId);
							                			if(cn.getToEdgeIds().contains(edgeId) == false)
							                				cn.getToEdgeIds().add(edgeId);
						                    		}
						                    	}
						                    	if(rcz.physicalType == 5) {
						                    		CnvPortNode ffcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rcz.prevZone);
						                    		fcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rcz.lftAttr.inIncludeZoneId);
						                    		tcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rcz.lftAttr.outIncludeZoneId);
						                    		fcn.setType(CNV_NODE_TYPE.INLFT);
						                    		tcn.setType(CNV_NODE_TYPE.OUTLFT);
						                    		CnvPortNode ttcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rcz.nextZone);	
						                    		if(rcz.prevZone < 0) {
						                    			ffcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.lftAttr.inIncludeZoneId).prevZone);
						                    		}
						                    		if(rcz.nextZone < 0) {
						                    			ttcn = tmpCnvPortNodeNoMap.get(cn.getEqpId()+":"+rawCnvZoneMap.get(rcz.lftAttr.outIncludeZoneId).nextZone);
						                    		}
						                    		String fEdgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + ffcn.getId() + "-" + fcn.getId();
						                    		String edgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + fcn.getId() + "-" + tcn.getId();
						                    		String tEdgeId = fabId + ":" + DataSet.CNV_EDGE_PREFIX + ":" + tcn.getId() + "-" + ttcn.getId();
						                    		edgeIdMap.put(fEdgeId, new String[] {ffcn.getId(), fcn.getId()});
						                			edgeIdMap.put(edgeId, new String[] {fcn.getId(), tcn.getId()});
						                			edgeIdMap.put(tEdgeId, new String[] {tcn.getId(), ttcn.getId()});
						                			if(ffcn.getToEdgeIds().contains(fEdgeId) == false)
						                				ffcn.getToEdgeIds().add(fEdgeId);
						                			if(fcn.getFromEdgeIds().contains(fEdgeId) == false)
						                				fcn.getFromEdgeIds().add(fEdgeId);
						                			if(fcn.getToEdgeIds().contains(edgeId) == false)
						                				fcn.getToEdgeIds().add(edgeId);
						                			if(tcn.getFromEdgeIds().contains(edgeId) == false)
						                				tcn.getFromEdgeIds().add(edgeId);
						                			if(tcn.getToEdgeIds().contains(tEdgeId) == false)
						                				tcn.getToEdgeIds().add(tEdgeId);
						                			if(ttcn.getFromEdgeIds().contains(tEdgeId) == false)
						                				ttcn.getFromEdgeIds().add(tEdgeId);
						                    	}
						                    }
						                    
						                    for(String noneedNodeId : noneedNodeNoSet) {
						                    	CnvPortNode r = tmpCnvPortNodeNoMap.remove(noneedNodeId);
						                    	tmpNodeMap.remove(r.getId());
						                    }
						                    
						                    for(String edgeId : edgeIdMap.keySet()) {
						                    	CnvPortNode fromNode = (CnvPortNode)tmpNodeMap.get(edgeIdMap.get(edgeId)[0]);
						                    	CnvPortNode toNode = (CnvPortNode)tmpNodeMap.get(edgeIdMap.get(edgeId)[1]);
						                    	if(fromNode == null)
						                    		logger.warn("{} cpn building... {} is null", edgeId, edgeIdMap.get(edgeId)[0]);
						                    	if(toNode == null)
						                    		logger.warn("{} cpn building... {} is null", edgeId, edgeIdMap.get(edgeId)[1]);
						                    	if(fromNode == null || toNode == null) continue;
						                    	if(toNode.getType() != CNV_NODE_TYPE.ZONE) {
						                    		toNode.setTerminal(true);
						                    	}
						                    	CnvEdge ce = new CnvEdge(fabId, edgeId, fromNode.getId(), toNode.getId(), 300, true, 500, isUpdate);
						                    	tmpCnvEdgeMap.put(ce.getId(),ce);
						                    	if(fromNode.getToEdgeIds().contains(edgeId)==false)
						                    		fromNode.getToEdgeIds().add(edgeId);        		
						                    	if(toNode.getFromEdgeIds().contains(edgeId)==false)
						                    		toNode.getFromEdgeIds().add(edgeId);
						                    }
						                    
						                    for(CnvPortNode lcpn : tmpCnvPortNodeNoMap.values()) {
						                    	if(lcpn.getType() == CNV_NODE_TYPE.INLFT) {
						                    		CnvEdge fe = tmpCnvEdgeMap.get(lcpn.getFromEdgeIds().peek());
						                    		CnvPortNode fromNode = (CnvPortNode)tmpNodeMap.get(fe.getFromNodeId());
						                    		lcpn.setDisplayFabId(fromNode.getDisplayFabId());
						                    		lcpn.setDisplayMcpName(fromNode.getDisplayMcpName());
						                    	}else if(lcpn.getType() == CNV_NODE_TYPE.OUTLFT) {
						                    		CnvEdge te = tmpCnvEdgeMap.get(lcpn.getToEdgeIds().peek());
						                    		CnvPortNode toNode = (CnvPortNode)tmpNodeMap.get(te.getToNodeId());
						                    		lcpn.setDisplayFabId(toNode.getDisplayFabId());
						                    		lcpn.setDisplayMcpName(toNode.getDisplayMcpName());
						                    	}
						                    }
						                    
						                    ConcurrentLinkedQueue<String> portList = new ConcurrentLinkedQueue<String>();
						            		for(AbstractNode an : tmpNodeMap.values()) {
						            			if(eqpId.equals(an.getEqpId()) && an instanceof CnvPortNode) {
						            				portList.add(an.getId());
						            				CnvPortNode cpn = (CnvPortNode) an;
						            				if(cpn.getType() == CNV_NODE_TYPE.INPUT || cpn.getType() == CNV_NODE_TYPE.OUTPUT) {
						            					cpn.setTerminal(true);
						            					cpn.setTeConnection(true);
						            				}
						            			}
						            		}
						                    
						                    for(CnvPortNode cpn : tmpCnvPortNodeNoMap.values().stream().filter(c->c.getEqpId().equals(eqpId) && c.isTerminal()).collect(Collectors.toList())) {
						                    	String s = cpn.getId();
						                    	for(String edgeId : cpn.getToEdgeIds()) {
						                    		CnvEdge ce = tmpCnvEdgeMap.get(edgeId);
						                    		CnvPortNode tail = (CnvPortNode)tmpNodeMap.get(ce.getToNodeId());
						                    		int i = 1;
						                    		
						                    		while(i < 10 && tail.getToEdgeIds().size() > 0 && ((tail.getToEdgeIds().size()==1 && tail.getFromEdgeIds().size()==1) || tail.isTerminal() == false)) {
						                    			i++;
						                    			try {
						                    				ce = tmpCnvEdgeMap.get(tail.getToEdgeIds().peek());
						                    			}catch(Exception e) {
						                    				logger.error("tail : {}", tail);
						                    				logger.error("tail id : {}", ce.getToNodeId());
						                    				logger.error("tail.isTerminal : {}", tail.isTerminal());
						                    				logger.error("tail.getToEdgeIds size : {}", tail.getToEdgeIds().size(), e);
						                    			}
						                    			tail = (CnvPortNode)tmpNodeMap.get(ce.getToNodeId());
						                    			if(i==10) {
						                    				tail.setTerminal(true);
						                    				if(tail.getToEdgeIds().size()==1) {
							                    				ce = tmpCnvEdgeMap.get(tail.getToEdgeIds().peek());
							                    				tail = (CnvPortNode)tmpNodeMap.get(ce.getToNodeId());
							                    				i=1;
						                    				}else {
						                    					break;
						                    				}
						                    			}
						                    		}
//						                    		if(tail.getZoneNo() == 21522)
//							                    		logger.warn("{} longedge spliting... toNode is 21522", edgeId);			                    	
//						                    		tail.setTerminal(true);
						                    	}
						                    }
						                    
						                    //Map<String,Integer> rawHeadZoneIdMap = fabProperties.getCnvSocketIOListenerMap().get(id).getRawHeadZoneIdMap();
//						                    
//						                    Set<String> visitedNodes = new HashSet<String>();
//						                    for(Entry<String,Integer> entry : rawHeadZoneIdMap.entrySet()) {
//						                    	String gpn = entry.getKey();        	
//						                    	Stack<CnvPortNode> cs = new Stack<CnvPortNode>();
//						                    	CnvPortNode hpn = tmpCnvPortNodeNoMap.get(eqpId + ":" + entry.getValue());
//						                    	cs.push(hpn);   
//						                    	visitedNodes.add(hpn.getId());
//						                    	while(cs.isEmpty()==false) {
//						                    		CnvPortNode cpn = cs.pop();
//						                    		if(cpn.getType() == CNV_NODE_TYPE.OUTPUT) {
//						                    			cpn.setGroupId(gpn);
//						                    			ConcurrentLinkedQueue<String> groupNodeNames = cnvGroupNodeIdMap.get(gpn);
//						                    			if(groupNodeNames == null) {
//						                    				groupNodeNames = new ConcurrentLinkedQueue<String>();
//						                    				cnvGroupNodeIdMap.put(gpn, groupNodeNames);
//						                    			}
//						                    			if(groupNodeNames.contains(cpn.getName()) == false)
//						                    				groupNodeNames.add(cpn.getName());
//						                    		}
//						                    		for(String cnvEdgeId : cpn.getToEdgeIds()) {
//						                    			CnvEdge ce = tmpCnvEdgeMap.get(cnvEdgeId);
//						                    			CnvPortNode tcpn = (CnvPortNode)tmpNodeMap.get(ce.getToNodeId());
//						                    			if(visitedNodes.contains(tcpn.getId()) == false && rawHeadZoneIdMap.containsKey(tcpn.getName())== false)
//						                    				cs.push((CnvPortNode)tmpNodeMap.get(tcpn.getId()));
//						                    			visitedNodes.add(ce.getToNodeId());				                    				
//						                    		}
//						                    	}
//						                    }				                    
						                    
						            		
						                    ConcurrentMap <String,ConcurrentLinkedQueue<String>> cnvGroupNodeMap = new ConcurrentHashMap<>();
						                    for(ConcurrentMap.Entry<String,ConcurrentLinkedQueue<String>> entry : cnvGroupNodeIdMap.entrySet()) {
						                    	if(entry.getKey().contains(id)) {
						                    		cnvGroupNodeMap.put(entry.getKey(), entry.getValue());
						                    		for(String cpnNm : entry.getValue()) {
						                    			CnvPortNode cpn = (CnvPortNode)tmpNodeMap.get(fabId+":"+DataSet.CNV_PORT_NODE_PREFIX+":"+cpnNm);
						                    			if(cpn!=null)
						                    				cpn.setGroupId(entry.getKey());
						                    		}
						                    	}	
						                    }
						            		
						            		Conveyor cnv = new Conveyor(fabId, eqpId, id, processTypeSet, portList, isAvailable, isUpdate, 
						            				cnvGroupNodeMap
						            				, mcsBayNm);
						            		cnv.setConveyorLayout(fabProperties.getCnvSocketIOListenerMap().get(id).getLayoutStr());
//						            		if (0 < contentBuilder.length()) {
//												final String layout = "{ \"ZoneList\":" + contentBuilder.toString() + "}";
//						            			cnv.setConveyorLayout(layout);
//						            		}
						            		tmpConveyorMap.put(eqpId, cnv);
						            		
//						            		List<String> targetPortIdList = new ArrayList<String>();
//						            		for(String portId : portList) {
//						            			CnvPortNode cpn = (CnvPortNode)tmpNodeMap.get(portId);
//						            			if(cpn!=null && cpn.getInOutType() == CNV_PORT_INOUT_TYPE.OUT) {
//						            				targetPortIdList.add(portId);
//						            			}				            			
//						            		}
						            		//portList.stream().filter(x-> ((CnvPortNode)tmpNodeMap.get(x)).getInOutType() == CNV_PORT_INOUT_TYPE.OUT).collect(Collectors.toList());
						            		
//						            		for(String portId : portList) {
//						            			CnvPortNode cpn = (CnvPortNode)tmpNodeMap.get(portId);
//						            			if(cpn.getInOutType() == CNV_PORT_INOUT_TYPE.IN) { // toRM
//						            				String eId = fabId + ":"+ DataSet.CNV_EDGE_PREFIX+ ":" + portId+"-";
//						            				for(String targetPortId : targetPortIdList) {
//						            					CnvEdge ce = new CnvEdge(fabId, eId + targetPortId, portId, targetPortId, 15000L, true, 30000d, isUpdate);
//						            					tmpCnvEdgeMap.put(ce.getId(), ce);
//						            				}
//						            			}
//						            		}	            		
						            	}
					            		break;
										case AGV : {										
											String agvId = fabId + ":" + DataSet.AGV_PREFIX + ":" + id;
											logger.warn("agvId : {}, id : {}", agvId, id);
											
											//AgvEdge edge = new AgvEdge();
											//tmpAgvEdgeMap.put(edge.getId(), edge);
											AmpUnit car = new AmpUnit(
													fabId,
													agvId,
													id,
													true,
													isUpdate,
													mcsBayNm
											);
											tmpAmpAgvMap.put(car.getId(), car);
										}
										break;
										default: {
											String eqpId = fabId + ":" + DataSet.EQP_PREFIX + ":" + id;
											ConcurrentLinkedQueue<String> portList = new ConcurrentLinkedQueue<>();
											ConcurrentLinkedQueue<String> portListR = new ConcurrentLinkedQueue<>();

											for (AbstractNode node : tmpNodeMap.values()) {
												if (node.getEqpId().equals(eqpId) && node instanceof EqpPortNode) {
													portList.add(node.getId());
												}
											}

											String[] portArr = portList.toArray(new String[0]);

											Arrays.sort(portArr);

											for (int i = portArr.length - 1; i >= 0; i--) {
												portListR.add(portArr[i]);
											}

											Eqp eq = new Eqp(
													fabId,
													eqpId,
													id,
													eqpType,
													processTypeSet,
													portListR,
													isAvailable,
													isUpdate,
													mcsBayNm
											);
											tmpEqpMap.put(eqpId, eq);
										}
										break;
									}
								} catch (Exception e) {
									logger.error("An Error Occurred While Eqps, StkRmEdge, Vhl Building.\n dr : {}", dataRow, e);
								}
							})).get();
				} catch (InterruptedException e) {
					logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
				} catch (ExecutionException e) {
					logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
				}
			}			
		}
		catch (Exception e1) {
			logger.error("",e1);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Eqps, StkRmEdge, Vhl Building");
		//~

		// ↓ Edge 데이터를 address 값을 통해 빠르게 조회할 수 있도록 map 데이터 구성
		this._START_PROCESS_LOG(++sequence, "Making Edge Map Data");
		startBlock = System.currentTimeMillis();

		ConcurrentMap<String, AbstractEdge> tmpEdgeMap = new ConcurrentHashMap<>();
		tmpEdgeMap.putAll(tmpTransferEdgeMap);
		tmpEdgeMap.putAll(tmpRailEdgeMap);
		tmpEdgeMap.putAll(tmpStkRmEdgeMap);
		tmpEdgeMap.putAll(tmpCnvEdgeMap);

		// perallel 생성시 일부 노드에 대한 edge 미등록 현상
		final ConcurrentMap<String, List<AbstractEdge>> mapFromNode2Edge = new ConcurrentHashMap<>();
		final ConcurrentMap<String, List<AbstractEdge>> mapToNode2Edge = new ConcurrentHashMap<>();

		for (AbstractEdge edge : tmpEdgeMap.values()) {
			final String fromNodeId = edge.getFromNodeId();
			final String toNodeId = edge.getToNodeId();

			List<AbstractEdge> abstractEdgeList = mapFromNode2Edge.computeIfAbsent(fromNodeId, k -> new ArrayList<>());

			abstractEdgeList.add(edge);

			abstractEdgeList = mapToNode2Edge.computeIfAbsent(toNodeId, k -> new ArrayList<>());

			abstractEdgeList.add(edge);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Making Edge Map Data");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "Setting From/To Edges, Junction, Branch");
		startBlock = System.currentTimeMillis();

		try {
			pool.submit(() -> tmpNodeMap.values()
					.parallelStream()
					.forEach(an -> {
						List<AbstractEdge> aes = mapToNode2Edge.get(an.getId());

						if (aes != null) {
							for (AbstractEdge e : aes) {
								if (!an.getFromEdgeIds().contains(e.getId())) {
									an.getFromEdgeIds().add(e.getId());
									an.setFromEdgeIds(an.getFromEdgeIds());
								}
							}
						}

						aes = mapFromNode2Edge.get(an.getId());

						if (aes != null) {
							for (AbstractEdge e : aes) {
								if (!an.getToEdgeIds().contains(e.getId())) {
									an.getToEdgeIds().add(e.getId());
									an.setToEdgeIds(an.getToEdgeIds());
								}
							}
						}

						an.setJunction(an.getFromEdgeIds().size() > 1);
						an.setBranch(an.getToEdgeIds().size() > 1);
					})).get();
		} catch (InterruptedException e) {
			logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
		} catch (ExecutionException e) {
			logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Setting From/To Edges, Junction, Branch");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "Branch Join Edge Building");
		startBlock = System.currentTimeMillis();

		final ConcurrentMap<String, BranchJoinEdge> mapBranchJoinEdge = new ConcurrentHashMap<>();

		try {
			pool.submit(() -> tmpNodeMap.values()
					.parallelStream()
					.forEach(node -> {
						if (
								node instanceof RailNode
										&& (
										((RailNode) node).isRailBranch()
												|| ((RailNode) node).isRailJunction()
								)
						) {
							String startNodeId = node.getId();
							int direction = -1;

							for (String edgeId : node.getToEdgeIds()) {
								if (tmpRailEdgeMap.containsKey(edgeId)) {
									ConcurrentLinkedQueue<String> edgeIdList = new ConcurrentLinkedQueue<>();
									RailEdge e = tmpRailEdgeMap.get(edgeId);
									long length = 0;

									length += (long) e.getLength();

									edgeIdList.add(edgeId);

									direction++;

									while (
											!((RailNode) tmpNodeMap.get(e.getToNodeId())).isRailJunction()
													&& !((RailNode) tmpNodeMap.get(e.getToNodeId())).isRailBranch()
									) {
										Queue<String> toEdgeIds = new ConcurrentLinkedQueue<>();

										for (String toEdgeId : tmpNodeMap.get(e.getToNodeId()).getToEdgeIds()) {
											if (tmpRailEdgeMap.containsKey(toEdgeId)) {
												toEdgeIds.add(toEdgeId);
											}
										}

										if (toEdgeIds.isEmpty()) {    //	peek에서 Exception 발생할까봐
											e = tmpRailEdgeMap.get(null);

											edgeIdList.add(e.getId());

											length += (long) e.getLength();
										} else {
											break;
										}
									}

									FirstEdgeInfo fei = firstEdgeInfoMap.get(edgeId);
									String branchJoinEdgeId;

									if (
											fei != null
													&& startNodeId.equals(fei.getBranchJoinEdgeFromNodeId())
													&& e.getToNodeId().equals(fei.getBranchJoinEdgeToNodeId())
													&& StringUtils.isNotEmpty(fei.getBranchJoinEdgeId())
									) {
										branchJoinEdgeId = fei.getBranchJoinEdgeId();
										direction = fei.getBranchJoinEdgeDir();
									} else {
										branchJoinEdgeId = fabId + ":" + DataSet.BRANCHJOIN_EDGE_PREFIX + ":" + startNodeId + "-" + direction + "-" + e.getToNodeId();

										if (
												fei != null
														&& StringUtils.isEmpty(fei.getBranchJoinEdgeId())
										) {
											fei.setBranchJoinEdgeId(branchJoinEdgeId);
											fei.setBranchJoinEdgeDir(direction);
											fei.setBranchJoinEdgeFromNodeId(startNodeId);
											fei.setBranchJoinEdgeToNodeId(e.getToNodeId());
										} else {
											LongEdge tmpLe = null;
											AbstractEdge ae = tmpEdgeMap.get(edgeId);

											if (ae != null && StringUtils.isNotEmpty(ae.getLongEdgeId())) {
												tmpLe = tmpLongEdgeMap.get(ae.getLongEdgeId());
											}

											if (tmpLe != null) {
												fei = new FirstEdgeInfo(
														edgeId,
														tmpLe.getId(),
														branchJoinEdgeId,
														tmpLe.getDirection(),
														tmpLe.getFromNodeId(),
														tmpLe.getToNodeId(),
														startNodeId,
														e.getToNodeId(),
														direction
												);
											} else {
												fei = new FirstEdgeInfo(edgeId, "", branchJoinEdgeId, -1, "", "", startNodeId, e.getToNodeId(), direction);
											}

											firstEdgeInfoMap.put(fei.getFirstEdgeId(), fei);
										}
									}

									mapBranchJoinEdge.put(
											branchJoinEdgeId,
											new BranchJoinEdge(
													fabId,
													branchJoinEdgeId,
													startNodeId,
													e.getToNodeId(),
													EDGE_TYPE.BRANCHJOINEDGE,
													length,
													edgeIdList,
													isUpdate
											)
									);

									for (String railEdgeId : edgeIdList) {
										RailEdge railEdge = tmpRailEdgeMap.get(railEdgeId);

										railEdge.setBranchJoinEdgeId(branchJoinEdgeId);
									}
								}
							}
						}
					})).get();
		} catch (InterruptedException e) {
			logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
		} catch (ExecutionException e) {
			logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Branch Join Edge Building");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "Setting Stocker Port Node Terminal");
		startBlock = System.currentTimeMillis();

		try {
			pool.submit(() -> tmpStockerMap.values()
					.parallelStream()
					.forEach(stk -> {
						for (String spnId : stk.getPortNodeIdList()) {
							StkPortNode spn = (StkPortNode) tmpNodeMap.get(spnId);

							if (spn.getToEdgeIds().isEmpty() || spn.getFromEdgeIds().isEmpty()) {
								spn.setTerminal(true);
							}
						}
					})).get();
		} catch (InterruptedException e) {
			logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
		} catch (ExecutionException e) {
			logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Setting Stocker Port Node Terminal");
		//~

		//
		this._START_PROCESS_LOG(++sequence, "Setting Initial Loop On Entry/ExitSet(RailEdge)");
		startBlock = System.currentTimeMillis();

		ConcurrentLinkedQueue<RailEdge> entryRailEdgeList = new ConcurrentLinkedQueue<RailEdge>();
		for (String mcpName : mcp75ConfigMap.keySet()) {
			try {
				pool.submit(() -> mcp75ConfigMap.get(mcpName).getRawLoopMap().values()
						.parallelStream()
						.forEach(rl -> {
							for (Integer[] e : rl.getEntrySet()) {
								RailEdge railEdge = tmpRailEdgeMap.get(DataSet.address2RailEdgeId(fabId, mcpName, e[0], e[1]));
								railEdge.setLoopId(rl.getId());
								entryRailEdgeList.add(railEdge);
							}

							for (Integer[] e : rl.getExitSet()) {
								RailEdge railEdge = tmpRailEdgeMap.get(DataSet.address2RailEdgeId(fabId, mcpName, e[0], e[1]));

								if (railEdge == null) {
									logger.warn(DataSet.address2RailEdgeId(fabId, mcpName, e[0], e[1]));

									railEdge = tmpRailEdgeMap.get(DataSet.address2RailEdgeId(fabId, mcpName, e[1], e[0]));
								}

								railEdge.setLoopId(rl.getId());
							}
						})).get();
			} catch (InterruptedException e) {
				logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
			} catch (ExecutionException e) {
				logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
			}
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Setting Initial Loop On Entry/ExitSet(RailEdge)");
		//~
		
		//
		this._START_PROCESS_LOG(++sequence, "Setting All loop Info(RailEdge)");
		startBlock = System.currentTimeMillis();
		
		new RecursiveLoopNameSetter(tmpRailEdgeMap, tmpNodeMap, entryRailEdgeList, pool);
		resetLoopId(fabId, mcp75ConfigMap, tmpRailEdgeMap, mapFromNode2Edge);
		
		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Setting All loop Info(RailEdge)");
		//~
		
		//
		this._START_PROCESS_LOG(++sequence, "Setting initial Area(Edge, Station)");
		startBlock = System.currentTimeMillis();

		for (String mcpName : mcp75ConfigMap.keySet()) {
			try {
				pool.submit(() -> mcp75ConfigMap.get(mcpName).getRawLoopMap().values()
						.parallelStream()
						.forEach(rl -> {
							mcp75ConfigMap.get(mcpName).getRawAreaMap().values().parallelStream().forEach(ra ->{
								for( Integer[] e : ra.getEntrySet()) {
									RailEdge re = tmpRailEdgeMap.get(DataSet.address2RailEdgeId(fabId, mcpName, e[0], e[1]));
									if(re != null) {
										re.setAreaName(ra.getName());
										re.setAreaId(fabId+":"+DataSet.AREA_PREFIX+":"+ra.getName());
										for(String s : re.getStationIdList()) {
											Station st = tmpStationMap.get(s);
											if(st == null) {
												logger.warn("{} {} station {} is not registered. so could not set area!!!", fabId, mcpName, s);
											}else {
												st.setAreaName(ra.getName());
												st.setAreaId(fabId+":"+DataSet.AREA_PREFIX+":"+ra.getName());
											}
										}
										tmpNodeMap.get(re.getToNodeId()).setAreaName(ra.getName());
										tmpNodeMap.get(re.getToNodeId()).setAreaId(fabId+":"+DataSet.AREA_PREFIX+":"+ra.getName());
									}
								}
							});
						})).get();
			} catch (InterruptedException e) {
				logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
			} catch (ExecutionException e) {
				logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
			}
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Setting initial Area(Edge, Station)");
		//~
				
		//
		this._START_PROCESS_LOG(++sequence, "Setting initial Bay(Edge, Station)");
		startBlock = System.currentTimeMillis();

		for (String mcpName : mcp75ConfigMap.keySet()) {
			try {
				pool.submit(() -> mcp75ConfigMap.get(mcpName).getRawLoopMap().values()
						.parallelStream()
						.forEach(rl -> {
							mcp75ConfigMap.get(mcpName).getRawBayMap().values().parallelStream().forEach(rb ->{
								for( RawBayPort e : rb.getEntrySet()) {
									RailEdge re = tmpRailEdgeMap.get(DataSet.address2RailEdgeId(fabId, mcpName, e.startPoint, e.endPoint));
									if(re != null) {
										String bayId = fabId+":"+DataSet.BAY_PREFIX+":"+rb.getName();
										re.setBayName(rb.getName());
										re.setBayId(bayId);
										for(String s : re.getStationIdList()) {
											Station st = tmpStationMap.get(s);
											if(st == null) {
												logger.warn("{} {} station {} is not registered. so could not set bay!!!", fabId, mcpName, s);
											}else {
												st.setBayName(rb.getName());
												st.setBayId(bayId);
											}									
										}
										tmpNodeMap.get(re.getToNodeId()).setBayName(rb.getName());
										tmpNodeMap.get(re.getToNodeId()).setBayId(bayId);
									}
								}
							});
						})).get();
			} catch (InterruptedException e) {
				logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
			} catch (ExecutionException e) {
				logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
			}
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Setting initial Bay(Edge, Station)");
		//~
		
		//
		this._START_PROCESS_LOG(++sequence, "Setting All Area & Bay Info(Edge, Station)");
		startBlock = System.currentTimeMillis();
		
		new RecursiveRailAreaBayNameSetter(tmpRailEdgeMap, tmpEdgeMap, tmpNodeMap, tmpStationMap, pool);
		
		// InputPort 측 Area, Bay명 누락 현상 보완.
		try {
			pool.submit(()->{
				tmpEdgeMap.values().parallelStream().forEach(ae ->{
					if(StringUtils.isEmpty(ae.getAreaName())) {
						AbstractNode tn = tmpNodeMap.get(ae.getToNodeId());
						if(StringUtils.isNotEmpty(tn.getAreaName())) {
							ae.setAreaName(tn.getAreaName());
							ae.setBayName(tn.getBayName());
							ae.setAreaId(tn.getAreaId());
							ae.setBayId(tn.getBayId());
						}else {
							String nextEdgeId = tn.getToEdgeIds().peek();
							if(StringUtils.isNotEmpty(nextEdgeId)) {
								AbstractEdge ne = tmpEdgeMap.get(nextEdgeId);
								if(ne != null && StringUtils.isNotEmpty(ne.getAreaId())) {
									tn.setAreaName(ne.getAreaName());
									tn.setBayName(ne.getBayName());
									ae.setAreaName(ne.getAreaName());
									ae.setBayName(ne.getBayName());
									tn.setAreaId(ne.getAreaId());
									tn.setBayId(ne.getBayId());
									ae.setAreaId(ne.getAreaId());
									ae.setBayId(ne.getBayId());
								}else {
									AbstractNode fn = tmpNodeMap.get(ae.getFromNodeId());
									if(StringUtils.isNotEmpty(fn.getAreaId())) {
										tn.setAreaId(fn.getAreaId());
										tn.setAreaName(fn.getAreaName());
										tn.setBayId(fn.getBayId());
										tn.setBayName(fn.getBayName());
										ae.setAreaName(fn.getAreaName());
										ae.setBayName(fn.getBayName());
										ae.setAreaId(fn.getAreaId());
										ae.setBayId(fn.getBayId());
									}
								}
							}					
						}
						AbstractNode fn =  tmpNodeMap.get(ae.getFromNodeId());
						if(StringUtils.isEmpty(fn.getAreaName())) {
							fn.setAreaName(ae.getAreaName());
							fn.setBayName(ae.getBayName());
							fn.setAreaId(ae.getAreaId());
							fn.setBayId(ae.getBayId());
						}
					}
				});
			}).get();
		} catch (InterruptedException e1) {
			logger.error("",e1);
		} catch (ExecutionException e1) {
			logger.error("",e1);
		}		
				
		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Setting All Area & Bay Info(Edge, Station)");
		//~
		
		//
		this._START_PROCESS_LOG(++sequence, "Setting Initial HID");
		startBlock = System.currentTimeMillis();
		ConcurrentMap<String, Integer> tmpVhlCntMap = new ConcurrentHashMap<>();
		//	┌─ key: {fabId}:{mcpName}:{hidId} | value: {address list}
		Map<String, List<String>> tmpHidMap = new HashMap<>();

		try {
			for (String mcpName : mcp75ConfigMap.keySet()) {
				final Map<String, RawHid> mapHid = mcp75ConfigMap.get(mcpName).getRawHidMap();

				pool.submit(() -> mapHid.values()
						.parallelStream()
						.forEach(rawHid -> {
							final Set<String> mapRailEdgeId = new HashSet<>();
							final Set<LoopEntry> entries = rawHid.getLoopEntrySet();
							final int hidId = rawHid.getId();
							String key = fabId + ":" + mcpName + ":" + String.format("%03d", hidId);
							List<String> bundleList = new ArrayList<>();

							if (!tmpVhlCntMap.containsKey(key)) {
								tmpVhlCntMap.put(key, 0);
								tmpHidMap.put(key, new ArrayList<>());
							}

							for (LoopEntry loopEntry : entries) {
								final int fromAddress = loopEntry.getEntryLaneStart();    //	4529
								final int toAddress = loopEntry.getEntryLaneEnd();    //	6151

								if (bundleList.isEmpty()) {
									bundleList.add(String.valueOf(fromAddress));
								}

								final ConcurrentLinkedQueue<RawEdge> rawEdges = mapFromNode2RawEdgeMap.get(mcpName).get(fromAddress);

								for (RawEdge rawEdge : rawEdges) {
									if (rawEdge.toNode == toAddress) {    // railEdge 검증
										this._collectZoneElement(
												mapFromNode2RawEdgeMap.get(mcpName),
												rawHid.getExitSet(),
												rawEdge,
												mapRailEdgeId,
												1
										);

										break;
									}
								}
							}

							for (String railEdgeId : mapRailEdgeId) {
								RailEdge railEdge = tmpRailEdgeMap.get(railEdgeId);

								// 동일한 hid 구간에 위치한 railEdge에 동일한 hid id 값을 부여
								railEdge.setHIDId(hidId);

								bundleList.add(railEdge.getAddress());
							}

							tmpHidMap.put(key, bundleList);
						})).get();
			}

			this._insertHidDataIntoLogpresso(tmpHidMap);

		} catch (InterruptedException e) {
			logger.error(INTERRUPTED_EXCEPTION_LOG, String.format("%02d", sequence), e);
		} catch (ExecutionException e) {
			logger.error(EXECUTION_EXCEPTION_LOG, String.format("%02d", sequence), e);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Setting Initial HID");
		// ~

		// 
		this._START_PROCESS_LOG(++sequence, "LongEdge Building");
		startBlock = System.currentTimeMillis();
		
		try {
			pool.submit(()->{
				tmpNodeMap.values().parallelStream().forEach(n ->{
					try {
						if(n.isJunction() || n.isBranch() || n.isTerminal() || n.isTeConnection()) {
							String startNodeId = n.getId();
							int direction = -1;			
							for(String edgeId : n.getToEdgeIds()) {
								ConcurrentLinkedQueue<String> edgeIdList = new ConcurrentLinkedQueue<String>();
								AbstractEdge e = tmpEdgeMap.get(edgeId);
								edgeIdList.add(edgeId);
								direction++;
								while(tmpNodeMap.get(e.getToNodeId()).isJunction() == false &&
									tmpNodeMap.get(e.getToNodeId()).isBranch() == false && 
									tmpNodeMap.get(e.getToNodeId()).isTerminal() == false && 
									tmpNodeMap.get(e.getToNodeId()).isTeConnection() == false) {
									Queue<String> toEdgeIds = tmpNodeMap.get(e.getToNodeId()).getToEdgeIds();
									if(toEdgeIds.size() > 0) { // peek에서 Exception 발생할까봐
										e = tmpEdgeMap.get(tmpNodeMap.get(e.getToNodeId()).getToEdgeIds().peek());
										edgeIdList.add(e.getId());
									}
									else
										break;
								}
								//String longEdgeId = fabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + startNodeId + "-" + direction + "-" + e.getToNodeId();
								FirstEdgeInfo fei = firstEdgeInfoMap.get(edgeId);
								String longEdgeId = "";
								if(fei!=null && startNodeId.equals(fei.getLongEdgeFromNodeId()) && e.getToNodeId().equals(fei.getLongEdgeToNodeId())) {
									longEdgeId = fei.getLongEdgeId();
									direction = fei.getLongEdgeDir();												
								}else {
									logger.warn("No matching last longedge for {} {} - {}. fei : {}", edgeId, startNodeId, e.getToNodeId(), JsonUtil.convertJSON(fei));
									Integer fromNodeMaxLongEdgeDir = curMaxLongEdgeDirMap.get(startNodeId);
									if(fromNodeMaxLongEdgeDir!= null && fromNodeMaxLongEdgeDir >= 0) {
										direction = ++fromNodeMaxLongEdgeDir;
										curMaxLongEdgeDirMap.put(startNodeId, fromNodeMaxLongEdgeDir);
										
									}else {
										curMaxLongEdgeDirMap.put(startNodeId, direction);
									}
									longEdgeId = fabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + startNodeId + "-" + direction + "-" + e.getToNodeId();
									fei = new FirstEdgeInfo(edgeId, longEdgeId, "", direction, startNodeId, e.getToNodeId(), "", "", -1);
									firstEdgeInfoMap.put(fei.getFirstEdgeId(),fei);
								}
								logger.debug("LongEdge id : {} build completed",longEdgeId);
								tmpLongEdgeMap.put(longEdgeId, new LongEdge(fabId, longEdgeId, startNodeId, e.getToNodeId(), direction, edgeIdList, isUpdate));
							}
						}
					}catch(Exception e) {
						logger.error("",e);
					}
				});
			}).get();
		} catch (InterruptedException e1) {
			logger.error("",e1);
		} catch (ExecutionException e1) {
			logger.error("",e1);
		}
		try {
			pool.submit(()->{
				tmpLongEdgeMap.values().parallelStream().forEach(le ->{
					// LongEdge도 Area, Bay를 설정하자.
					le.setAreaName(tmpEdgeMap.get(le.getEdgeIdList().peek()).getAreaName());
					le.setAreaId(tmpEdgeMap.get(le.getEdgeIdList().peek()).getAreaId());
					le.setBayName(tmpEdgeMap.get(le.getEdgeIdList().peek()).getBayName());
					le.setBayId(tmpEdgeMap.get(le.getEdgeIdList().peek()).getBayId());	
					for(String edgeId : le.getEdgeIdList()) {
						AbstractEdge edge = tmpEdgeMap.get(edgeId);
						edge.setLongEdgeId(le.getId());
						if(le.getFromNodeId().equals(edge.getFromNodeId())) {
							AbstractNode node = tmpNodeMap.get(edge.getFromNodeId());
							if(node.getToLongEdgeIds().contains(le.getId()) == false) {
								node.getToLongEdgeIds().add(le.getId());
								node.setToLongEdgeIds(node.getToLongEdgeIds());
							}
						}
						if(le.getToNodeId().equals(edge.getToNodeId())) {
							AbstractNode node = tmpNodeMap.get(edge.getToNodeId());
							if(node.getFromLongEdgeIds().contains(le.getId()) == false) {
								node.getFromLongEdgeIds().add(le.getId());
								node.setFromLongEdgeIds(node.getFromLongEdgeIds());
							}					
						}				
					}
				});
			}).get();
		} catch (InterruptedException e1) {
			logger.error("",e1);
		} catch (ExecutionException e1) {
			logger.error("",e1);
		}
		
		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "LongEdge Building");
		// ~
		
		//
		this._START_PROCESS_LOG(++sequence, "PortAlias Building");
		startBlock = System.currentTimeMillis();

		ConcurrentMap<String, List<String>> tmpPortAliasListMap = new ConcurrentHashMap<>();

		try {
			DataTable result = OracleAPI.select(fabId, "SELECT_PORT_ALIAS_INF");
			if (result != null)
			{
				for (DataRow dr : result.getRows()) {
					List<String> portNameList = tmpPortAliasListMap.get(dr.getString("ALIASNAME"));

					if (portNameList == null) {
						portNameList = new ArrayList<>();
					}

					String pn = dr.getString("UNITNAME");

					portNameList.add(pn);

					tmpPortAliasListMap.put(dr.getString("ALIASNAME"), portNameList);
				}
				
				for(Conveyor cnv : tmpConveyorMap.values()) {
		            for(Entry<String,ConcurrentLinkedQueue<String>> entry : cnv.getCnvGroupNodeIdMap().entrySet()) {
		            	String aliasName = entry.getKey();
		            	ConcurrentLinkedQueue<String> portNameQueue = entry.getValue();
		            	List<String> portNameList = new ArrayList<String>(portNameQueue);            	
		            	tmpPortAliasListMap.put(aliasName, portNameList);
		            }
	            }	
			}			
		}
		catch (Exception e1) {
			logger.error("",e1);
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "PortAlias Building");
		//~
				
		//
		this._START_PROCESS_LOG(++sequence, "Label from RawLabel");
		startBlock = System.currentTimeMillis();
		
		for(String mcpName : mcp75ConfigMap.keySet()) {
			for(RawLabel rawLabel : mcp75ConfigMap.get(mcpName).getRawLabelMap().values()) {
				final String labelId = fabId + ":" + DataSet.LABEL_PREFIX + ":" + mcpName + ":" + rawLabel.getLabel();
				tmpLabelMap.put(labelId, new Label(labelId, mcpName, rawLabel));
			}
		}
		
		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Label from RawLabel");
		//~
		
		//
		this._START_PROCESS_LOG(++sequence, "Area from RailEdge");
		startBlock = System.currentTimeMillis();
		
		Map<String, ConcurrentLinkedQueue<String>> arm = new ConcurrentHashMap<String, ConcurrentLinkedQueue<String>>();
		for(RailEdge re : tmpRailEdgeMap.values()) {
			if(re.getVelocity() <= 0)
				re.setVelocity(re.getMaxVelocity());
			String areaId = re.getFabId()+":"+DataSet.AREA_PREFIX+":"+re.getAreaName();
			if(tmpAreaMap.containsKey(areaId)==false) {
				tmpAreaMap.put(areaId, new Area(areaId, re.getFabId(), re.getAreaName(), re.getMcpName()));
				arm.put(areaId, new ConcurrentLinkedQueue<String>());
			}
			if(tmpAreaMap.containsKey(areaId)){
				arm.get(areaId).add(re.getId());
			}
		}
		for(Entry<String, ConcurrentLinkedQueue<String>> entry:arm.entrySet()) {
			tmpAreaMap.get(entry.getKey()).setRailEdgeIdList(entry.getValue());
		}
		
		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Area from RailEdge");
		//~
		
		//
		this._START_PROCESS_LOG(++sequence, "Bay from RailEdge");
		startBlock = System.currentTimeMillis();
		
		Map<String, ConcurrentLinkedQueue<String>> bam = new ConcurrentHashMap<String, ConcurrentLinkedQueue<String>>();
		for(RailEdge re : tmpRailEdgeMap.values()) {
			if(re.getVelocity() <= 0)
				re.setVelocity(re.getMaxVelocity());
			String bayId = re.getFabId()+":"+DataSet.BAY_PREFIX+":"+re.getBayName();
			if(tmpBayMap.containsKey(bayId)==false) {
				tmpBayMap.put(bayId, new Bay(bayId, re.getFabId(), re.getBayName(), re.getMcpName()));
				bam.put(bayId, new ConcurrentLinkedQueue<String>());
			}
			if(tmpBayMap.containsKey(bayId)){
				bam.get(bayId).add(re.getId());
			}
		}
		for(Entry<String, ConcurrentLinkedQueue<String>> entry:bam.entrySet()) {
			tmpBayMap.get(entry.getKey()).setRailEdgeIdList(entry.getValue());
		}
		
		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Bay from RailEdge");
		//~
		
		// 		
		this._START_PROCESS_LOG(++sequence, "Alarm Limit Building");
		startBlock = System.currentTimeMillis();

		//Alarm 기준정보 Map, key: {fabId}:{limitType}
		ConcurrentMap<String, Integer> tmpAlarmLimitMap = new ConcurrentHashMap<>();

//		try {
//			String strQuery = "table AMOS_ALARM_PARAMETER"
//					+ "| search FAB_ID==\"%s\""
//					+ "| stats max(_time) as _time by FAB_ID,LIMIT_TYPE"
//					+ "| join type=inner _time [table AMOS_ALARM_PARAMETER | fields _id, _time, LIMIT_TYPE, VALUE]"
//					+ "| sort _time";
//			
//			strQuery = String.format(strQuery, fabId);
//			List<Map<String, Object>> result = LogpressoAPI.responseResult(strQuery);
//			if (result != null)
//			{
//				for (Map<String, Object> item : result) {
//					String key = fabId + ":" + item.get("LIMIT_TYPE").toString();
//					tmpAlarmLimitMap.put(key, Integer.parseInt(item.get("VALUE").toString()));
//				}
//			}
//			// M14A,M16A일때 ServerResourceApmBatch.java 에 적용할 임계치값(APM 파라미터) 가져오기, Fac별
//			if(fabId.equals("M14A") || fabId.equals("M16A")) {
//				strQuery = "table AMOS_ALARM_PARAMETER"
//						+ "| search FAB_ID==\"%s\""
//						+ "| stats max(_time) as _time by FAB_ID,LIMIT_TYPE"
//						+ "| join type=inner _time [table AMOS_ALARM_PARAMETER | fields _id, _time, LIMIT_TYPE, VALUE]"
//						+ "| sort _time";
//				
//				strQuery = String.format(strQuery, facId + "APM");
//				result = LogpressoAPI.responseResult(strQuery);
//				if (result != null)
//				{
//					for (Map<String, Object> item : result) {
//						// M14APM:{LIMIT_TYPE}, M16APM:{LIMIT_TYPE} 
//						String key = facId + "APM:" + item.get("LIMIT_TYPE").toString();
//						tmpAlarmLimitMap.put(key, Integer.parseInt(item.get("VALUE").toString()));
//					}
//				}
//			}
//		}
//		catch (Exception e1) {
//			logger.error("",e1);
//		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
		this._END_PROCESS_LOG(sequence, "Alarm Limit Building");
		//~
		

		pool.shutdown();

		//	위의 과정을 통해 얻어낸 데이터를 모두 취합하여 dataSet(ds)에 저장
		if (dataSet == null) {
			// ?::미적용 항목
			dataSet = new DataSet(
					tmpRailEdgeMap,        	//	(1) M14A:RE:A:M14A:RN:A:07954-M14A:RN:A:07955
					tmpStkRmEdgeMap,       	//	(2) M14A:SRE:M14A:SPN:4ANS6702A_IN05-M14A:SRN:4ANS6702RM
					tmpStationMap,        	//	(3) M14A:ST:A:03338
					tmpTransferEdgeMap,    	//	(4) M14A:TE:M14A:EPN:4KTM3203_1-M14A:ST:A:07243
					tmpNodeMap,            	//	(5) M14A:EPN:4EHS6011_3
					tmpEqpMap,            	//	(6) M14A:EQP:4PWI4301
					tmpFioMap,            	//	(7) M14A:FIO:4AIO6101
					tmpOhtMap,            	//	(8) M14A:OHT:4ACM4701
					tmpStbGroupMap,        	//	(9) ?
					tmpStockerMap,        	//	(10) M14A:STK:4ARS4201
					tmpPortAliasListMap,    //	(11) 4ANS6701_MO22
					tmpVhlMap,            	//	(12) M14A:VHL:A:V00270
					tmpLongEdgeMap,        	//	(13) ?
					tmpConveyorMap,        	//	(14) ?
					tmpCnvEdgeMap,        	//	(15) ?
					tmpLabelMap,            //	(16) ?
					tmpAreaMap,            	//	(17) ?
					tmpBayMap,            	//	(18) ?
					mapFromNode2Edge,       //	(19) M14A:EPN:4EHS6011_3
					mapToNode2Edge,        	//	(20) M14A:EPN:4EHS6011_3
					mapBranchJoinEdge,      //	(21) M14A:BJE:M14A:RN:A:02086-1-M14A:RN:A:02088
					tmpRailCutMap,			// 	(22) M14A:A:07612-07613
					tmpVhlCntMap,			// 	(23) M14A:A:140
					tmpAgvEdgeMap,			// 	(24) ?
					tmpAmpAgvMap,			// 	(25) ?
					tmpAlarmLimitMap		// 	(26) M14A:REQ_LIMIT
			);
		} else {
			dataSet.addDataSet(
					tmpRailEdgeMap,
					tmpStkRmEdgeMap,
					tmpStationMap,
					tmpTransferEdgeMap,
					tmpNodeMap,
					tmpEqpMap,
					tmpFioMap,
					tmpOhtMap,
					tmpStbGroupMap,
					tmpStockerMap,
					tmpPortAliasListMap,
					tmpVhlMap,
					tmpLongEdgeMap,
					tmpConveyorMap,
					tmpCnvEdgeMap,
					tmpLabelMap,
					tmpAreaMap,
					tmpBayMap,
					mapFromNode2Edge,
					mapToNode2Edge,
					mapBranchJoinEdge,
					tmpRailCutMap,
					tmpVhlCntMap,
					tmpAgvEdgeMap,
					tmpAmpAgvMap,
					tmpAlarmLimitMap
			);
		}

// ---------------------------------------------------------------------------------------------------------------------
		// building a log
		List<String> logs = new ArrayList<>();

		logs.add("<DATASET INITIALIZED [" + fabId + "]>");

		try {
			// #1. railEdge
			logs.add(this._resultLogHelper("RAIL EDGE", fabId, dataSet.getRailEdgeMap(), tmpRailEdgeMap));
			// #2. stkRmEdge
			logs.add(this._resultLogHelper("STK RM EDGE", fabId, dataSet.getStkRmEdgeMap(), tmpStkRmEdgeMap));
			// #3. station
			logs.add(this._resultLogHelper("STATION", fabId, dataSet.getStationMap(), tmpStationMap));
			// #4. transferEdge
			logs.add(this._resultLogHelper("TRANSFER EDGE", fabId, dataSet.getTransferEdgeMap(), tmpTransferEdgeMap));
			// #5. node
			logs.add(this._resultLogHelper("NODE", fabId, dataSet.getNodeMap(), tmpNodeMap));
			// #6. eqp
			logs.add(this._resultLogHelper("EDGE", fabId, dataSet.getEdgeMap(), tmpEdgeMap));
			// #7. fio
			logs.add(this._resultLogHelper("FIO", fabId, dataSet.getFioMap(), tmpFioMap));
			// #8. oht
			logs.add(this._resultLogHelper("OHT", fabId, dataSet.getOhtMap(), tmpOhtMap));
			// #9. stbGroup
			logs.add(this._resultLogHelper("STB GROUP(-)", fabId, dataSet.getStbGroupMap(), tmpStbGroupMap));
			// #10. stocker
			logs.add(this._resultLogHelper("STOCKER", fabId, dataSet.getStockerMap(), tmpStockerMap));
			// #11. portAliasList
			logs.add(this._resultLogHelper("PORT ALIAS LIST(&)", fabId, dataSet.getPortAliasSetMap(), tmpPortAliasListMap));
			// #12. vhl
			logs.add(this._resultLogHelper("VHL", fabId, dataSet.getVhlMap(), tmpVhlMap));
			// #13. longEdge
			logs.add(this._resultLogHelper("LONG EDGE(-)", fabId, dataSet.getLongEdgeMap(), tmpLongEdgeMap));
			// #14. conveyor
			logs.add(this._resultLogHelper("CONVEYOR(-)", fabId, dataSet.getConveyorMap(), tmpConveyorMap));
			// #15. cnvEdge
			logs.add(this._resultLogHelper("CNV EDGE(-)", fabId, dataSet.getCnvEdgeMap(), tmpCnvEdgeMap));
			// #16. label
			logs.add(this._resultLogHelper("LABEL(-)", fabId, dataSet.getLabelMap(), tmpLabelMap));
			// #17. area
			logs.add(this._resultLogHelper("AREA(-)", fabId, dataSet.getAreaMap(), tmpAreaMap));
			// #18. bay
			logs.add(this._resultLogHelper("BAY(-)", fabId, dataSet.getBayMap(), tmpBayMap));
			// #19. fromNode
			logs.add(this._resultLogHelper("FROM NODE", fabId, dataSet.getFromNode2EdgeMap(), mapFromNode2Edge));
			// #20. toNode
			logs.add(this._resultLogHelper("TO NODE", fabId, dataSet.getToNode2EdgeMap(), mapToNode2Edge));
			// #21. branchJoinEdge
			logs.add(this._resultLogHelper("BRANCH JOIN EDGE", fabId, dataSet.getBranchJoinEdgeMap(), mapBranchJoinEdge));
			// #22
			logs.add(this._resultLogHelper("BRANCH JOIN EDGE", fabId, dataSet.getRailCutRecordMap(), tmpRailCutMap));
			// #23
			logs.add(this._resultLogHelper("BRANCH JOIN EDGE", fabId, dataSet.getHidVehicleCountMap(), tmpVhlCntMap));
			// #24
			logs.add(this._resultLogHelper("BRANCH JOIN EDGE", fabId, dataSet.getAgvEdgeMap(), tmpAgvEdgeMap));
			// #25
			logs.add(this._resultLogHelper("BRANCH JOIN EDGE", fabId, dataSet.getAmpAgvMap(), tmpAmpAgvMap));
			// #26
			logs.add(this._resultLogHelper("BRANCH JOIN EDGE", fabId, dataSet.getAlarmLimitMap(), tmpAlarmLimitMap));
			// #27
			logs.add(this._resultLogHelper("BRANCH JOIN EDGE", fabId, dataSet.getCnvPortNodeNoMap(), tmpCnvPortNodeNoMap));
		} catch (Exception e) {
			logger.error("... an exception occurred during the result [fab: {}]", fabId, e);

			logs.add("!!! EXCEPTION OCCURRED !!!");
		}
// ---------------------------------------------------------------------------------------------------------------------
		// printing log
		Util.printHelper(logs);
// ---------------------------------------------------------------------------------------------------------------------
		return dataSet;
	}

	/**
	 * @link this._createNewDataSet
	 */
	private <T, E> String _resultLogHelper(
			String target,
			String fabId,
			ConcurrentMap<String, T> addedData,
			ConcurrentMap<String, E> builtData
	) {
		int count = 0;
		int builtSize = builtData == null ? -1 : builtData.size();

		for (Map.Entry<String, T> t : addedData.entrySet()) {
			if (t.getKey().contains(fabId)) {
				count++;
			}
		}

		return String.format("%18s : ", target) + String.format("%5d (B: %5d)", count, builtSize);
	}
	// =====================================================================================================================
	/*
	 * 사전에 다운로드 받은 맵 파일 중 inactive_SCH_1.dat(로컬 환경에서는 lanecut.dat)을 통해 RAIL CUT 데이터를 구성하면서 동시에 해당 레일이 사용 가능한 지 결정
	 */
	private boolean _getRailEdgeAvailableByRailCut(
			ConcurrentMap<String, Mcp75Config> mcp75ConfigMap,
			String mcpName,
			String railEdgeId
	) {
		// ex) 1000-1001
		Set<String> rawRailCutSet = mcp75ConfigMap.get(mcpName).getRawRailCutSet();

		return !rawRailCutSet.contains(railEdgeId);
	}

	/*
	 * HID 구간을 설정하기 위해 지정한 경로를 시작과 끝을 이어줌
	 */
	private void _collectZoneElement(
			final ConcurrentMap<Integer, ConcurrentLinkedQueue<RawEdge>> mapFromNode2RawEdge,
			final Set<Integer[]> stopNodes,
			final RawEdge rawEdge,
			final Set<String> mapRailEdgeId,
			final int depth
	) {
		if (100 < depth) return;

		mapRailEdgeId.add(rawEdge.railEdgeId);

		for (Integer[] edge : stopNodes) {
			if (1 < edge.length && edge[0] == rawEdge.fromNode && edge[1] == rawEdge.toNode) return;
		}

		final ConcurrentLinkedQueue<RawEdge> rawEdges = mapFromNode2RawEdge.get(rawEdge.toNode);

		for (RawEdge nextRawEdge : rawEdges) {
			this._collectZoneElement(
					mapFromNode2RawEdge,
					stopNodes,
					nextRawEdge,
					mapRailEdgeId,
					depth + 1
			);
		}
	}

	public void newMapLoad() {
		long totalTimer = System.currentTimeMillis();
		DataSet tmpDataSet = null;

		/*
		 1. 초기값을 만들 때는 파일 다운로드 구분없이 모두 파싱하여 값을 형성 ---> tmpDs
		 2. 이후 이전 dataSet 값을 참고하여 데이터를 적용
		 */
		for (String fabId : fabPropertiesMap.keySet()) {
			tmpDataSet = this._createNewDataSet(fabId, tmpDataSet, true, 10);
		}

		ThreadPool.pauseAll();

		try {
			Thread.sleep(600);
		} catch (Exception e) {}

//		final int previousRailEdgeMapSize = getDataSet().getRailEdgeMap().size();
//		final int previousStkRmEdgeMapSize = getDataSet().getStkRmEdgeMap().size();
//		final int previousTransferEdgeMapSize = getDataSet().getTransferEdgeMap().size();
//		final int previousVhlMapSize = getDataSet().getVhlMap().size();
//		final int previousStationMapSize = getDataSet().getStationMap().size();
//		final int previousNodeMapSize = getDataSet().getNodeMap().size();

		// dataSet 잠금 ---> 데이터 업데이터 완료 전까지 dataSet 을 사용할 수 없음 !!!
		// 만일 잠금 해제 전까지 dataSet 사용 시 무한 루프를 돌 수 있음 !
		isBlocked.set(true);

		logger.warn("### Data Update Started ...");
		int sequence = 0;

		logger.info("STEP#{} RailEdge", String.format("%02d", ++sequence));
		_parallelUpdateDataSet(
				tmpDataSet,
				tmpDataSet.getRailEdgeMap().values(),
				Objects.requireNonNull(dataQ.peek()).getRailEdgeMap(),
				sequence
		);

		logger.info("STEP#{} StkRmEdge", String.format("%02d", ++sequence));
		_parallelUpdateDataSet(
				tmpDataSet,
				tmpDataSet.getStkRmEdgeMap().values(),
				Objects.requireNonNull(dataQ.peek()).getStkRmEdgeMap(),
				sequence
		);		
	
		logger.info("STEP#{} CnvEdgeMap", String.format("%02d", ++sequence));
		_parallelUpdateDataSet(
				tmpDataSet,
				tmpDataSet.getCnvEdgeMap().values(),
				Objects.requireNonNull(dataQ.peek()).getCnvEdgeMap(),
				sequence
		);		

		logger.info("STEP#{} TransferEdge", String.format("%02d", ++sequence));
		_parallelUpdateDataSet(
				tmpDataSet,
				tmpDataSet.getTransferEdgeMap().values(),
				Objects.requireNonNull(Objects.requireNonNull(dataQ.peek())).getTransferEdgeMap(),
				sequence
		);		
		
		logger.info("STEP#{} LongEdgeMap", String.format("%02d", ++sequence));
		_parallelUpdateDataSet(
				tmpDataSet,
				tmpDataSet.getLongEdgeMap().values(),
				Objects.requireNonNull(Objects.requireNonNull(dataQ.peek())).getLongEdgeMap(),
				sequence
		);

		logger.info("STEP#{} Vhl", String.format("%02d", ++sequence));
		_parallelUpdateDataSet(
				tmpDataSet,
				tmpDataSet.getVhlMap().values(),
				Objects.requireNonNull(Objects.requireNonNull(Objects.requireNonNull(dataQ.peek()))).getVhlMap(),
				sequence
		);

		logger.info("STEP#{} Station", String.format("%02d", ++sequence));
		_parallelUpdateDataSet(
				tmpDataSet,
				tmpDataSet.getStationMap().values(),
				Objects.requireNonNull(dataQ.peek()).getStationMap(),
				sequence
		);

		logger.info("STEP#{} Node", String.format("%02d", ++sequence));
		_parallelUpdateDataSet(
				tmpDataSet,
				tmpDataSet.getNodeMap().values(),
				Objects.requireNonNull(dataQ.peek()).getNodeMap(),
				sequence
		);
			
		logger.info("STEP#{} AllEqpMap", String.format("%02d", ++sequence));
		_parallelUpdateDataSet(
				tmpDataSet,
				tmpDataSet.getAllEqpMap().values(),
				Objects.requireNonNull(dataQ.peek()).getAllEqpMap(),
				sequence
		);

		logger.info("STEP#{} Properties", String.format("%02d", ++sequence));
		this._inlineConnect(tmpDataSet, true);
		this._fabConnect(tmpDataSet, true);
		this._setSpnOhtFabId(tmpDataSet);
		this._setNodeEdgeRef(tmpDataSet);
		this._setRailEdgeRef(tmpDataSet);

		for (Eqp eqp : tmpDataSet.getAllEqpMap().values()) {
			eqp.getMcpNameSet(tmpDataSet);
			eqp.getConnectedFabMcpSet(tmpDataSet);
			eqp.getFirstPortNodeId(tmpDataSet);
		}
		updateEqpExtInfo(tmpDataSet);
		
		
		tmpDataSet.setCommandMap(dataQ.peek().getCommandMap());
		tmpDataSet.setCarrierMap(dataQ.peek().getCarrierMap());
		tmpDataSet.setJobMap(dataQ.peek().getJobMap());
		tmpDataSet.setRouteItemMap(dataQ.peek().getRouteItemMap());
		tmpDataSet.setVhlStateMap(dataQ.peek().getVhlStateMap());
		tmpDataSet.setVhlDetStateMap(dataQ.peek().getVhlDetStateMap());
		tmpDataSet.setVhlCycleMap(dataQ.peek().getVhlCycleMap());
		tmpDataSet.setVhlRunCycleMap(dataQ.peek().getVhlRunCycleMap());
		tmpDataSet.setAreaVhlCountMap(dataQ.peek().getAreaVhlCountMap());
//		tmpDataSet.setPort2JobMap(dataQ.peek().getPort2JobMap());

		dataQ.add(tmpDataSet);
		dataQ.poll();

		isBlocked.set(false);	// dataSet 잠금 해제

		ThreadPool.resumeAll();

		logger.info("... queue data has been added, and unlocked*");

		this._setRailInfoAffectedForRailCut();
		this._initializedVelocity();

		logger.info("... data has been updated completed [elapsed Time: {}ms]", System.currentTimeMillis() - totalTimer);
	}


//	public void updateRailCut(boolean isReset) {
//		Set<String> newRailCutSet = new HashSet<>();
//
//		if (!isReset) {
//			newRailCutSet = this._buildNewRailCutKeySet(fabId, mcpName);
//		}
//
//		ConcurrentMap<String, RailCutRecordItem> result = this._updateRailCutHandler(newRailCutSet, fabId, mcpName);
//
//		getDataSet().setRailCutRecordMap(result);	// 마지막으로 현재의 RAIL CUT 데이터를 저장
//	}

	// data refresh and update
	private <T> void _parallelUpdateDataSet(
			DataSet dataSet,
			Collection<T> newDataCollection,
			ConcurrentHashMap<String,T> originalDataMap,
			int sequence
	) {
		ExecutorService threadPool = Executors.newFixedThreadPool(15);
		List<Future<String>> futures = new ArrayList<>();
		long startBlock = System.currentTimeMillis();

		for (final T newData : newDataCollection) {
			Callable<String> callable = () -> {
				String result;

				switch (newData.getClass().getSimpleName()) {
					case "RailEdge": {
						RailEdge newRailEdge = (RailEdge) newData;
						String newRailEdgeId = newRailEdge.getId();
						RailEdge originalRailEdge = (RailEdge) originalDataMap.get(newRailEdgeId);

						if (originalRailEdge != null) {
							newRailEdge.setUpdate(true);
							newRailEdge.setHisCnt(originalRailEdge.getHisCnt());
							newRailEdge.setLastVelocity(originalRailEdge.getLastVelocity());
							newRailEdge.setVelocity(originalRailEdge.getVelocity());
							newRailEdge.setVhlIdMap(originalRailEdge.getVhlIdMap());
							newRailEdge.setUpdate(false);
						} else {
							newRailEdge.setUpdate(false);
						}

						result = newRailEdgeId + ":OK";
					} break;
					case "StkRmEdge": {
						StkRmEdge newStkRmEdge = (StkRmEdge) newData;
						String newStkRmEdgeId = newStkRmEdge.getId();
						StkRmEdge originalStkRmEdge = (StkRmEdge) originalDataMap.get(newStkRmEdgeId);

						if (originalStkRmEdge != null) {
							newStkRmEdge.setUpdate(true);
							newStkRmEdge.setCurrentMovingCarrierIds(originalStkRmEdge.getCurrentMovingCarrierIds());
							newStkRmEdge.setAvgTransferCost((long) originalStkRmEdge.getAvgTransferCost());
							newStkRmEdge.setUpdate(false);
						} else {
							newStkRmEdge.setUpdate(false);
						}

						result = newStkRmEdgeId + ":OK";
					} break;
					case "CnvEdge" :{
						CnvEdge ne = (CnvEdge) newData;
						CnvEdge oe = (CnvEdge) originalDataMap.get(ne.getId());
						if(oe != null) {
							ne.setUpdate(true);
							ne.setAvgTransferIntervalT((long)oe.getAvgTransferIntervalT());				
	//							ne.setPathPredictQueue(oe.getPathPredictQueue());
							ne.setUpdate(false);
	//							if(redisUpdate && ne.changed(oe)) {
	//								RedisPool.jset(ne.getId(), ne);
	//							}
						}else {
							ne.setUpdate(false);
	//							if(redisUpdate) {
	//								RedisPool.jset(ne.getId(), ne);
	//								RedisPool.getJedisCluster().sadd("CnvEdge", ne.getId());
	//								//AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.CREATE, ne.getClass().getName(), ne));
	//							}
						}
						result = ne.getId() + ":OK";
					} break;
					case "TransferEdge": {
						TransferEdge newTransferEdge = (TransferEdge)newData;
						String newTransferEdgeId = newTransferEdge.getId();
						TransferEdge originalTransferEdge = (TransferEdge)originalDataMap.get(newTransferEdgeId);

						if (originalTransferEdge != null) {
							newTransferEdge.setUpdate(true);
							newTransferEdge.setAssignedVhlCarrierId(originalTransferEdge.getAssignedVhlCarrierId());
							newTransferEdge.setAvgTransferCost(originalTransferEdge.getAvgTransferCost());
							newTransferEdge.setAvgVhlCallCost(originalTransferEdge.getAvgVhlCallCost());
							newTransferEdge.setUpdate(false);
						} else {
							newTransferEdge.setUpdate(false);
						}

						result = newTransferEdgeId + ":OK";
					} break;
					case "LongEdge" :{
						LongEdge ne = (LongEdge)newData;
						LongEdge oe = (LongEdge)originalDataMap.get(ne.getId());
						if(oe != null) {
							ne.setUpdate(true);
							ne.setEstimatedCmdIdPassTimeMap(oe.getEstimatedCmdIdPassTimeMap());				
							ne.setPathPredictQueue(oe.getPathPredictQueue());
							ne.setLast1HourCost(oe.getLast1HourCost());
							ne.setTransWeight(oe.getTransWeight());
							ne.setAcqTransWeight(oe.getAcqTransWeight());
							ne.setDpstTransWeight(oe.getDpstTransWeight());
							ne.setJunctionMultiple(oe.getJunctionMultiple());
							ne.setTransOverlapIntervalT(oe.getTransOverlapIntervalT());
							ne.setLastParaRefreshTime(oe.getLastParaRefreshTime());
							ne.setUpdate(false);
	//							if(redisUpdate && ne.changed(oe)) {
	//								RedisPool.jset(ne.getId(), ne);
	//							}				
						}else {
							ne.setUpdate(false);
	//							if(redisUpdate) {
	//								RedisPool.jset(ne.getId(), ne);
	//								RedisPool.getJedisCluster().sadd("LongEdge", ne.getId());
	//								//AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.CREATE, ne.getClass().getName(), ne));
	//							}
						}
						result = ne.getId() + ":OK";
					} break;
					case "Vhl": {
						Vhl newVhl = (Vhl) newData;
						String newVhlId = newVhl.getId();
						Vhl originalVhl = (Vhl) originalDataMap.get(newVhlId);

						if (originalVhl != null) {
							newVhl.setUpdate(true);
							newVhl.setCarrierId(originalVhl.getCarrierId());
							newVhl.setCommandId(originalVhl.getCommandId());
//							newVhl.setUdpState(originalVhl.getUdpState());
//							newVhl.setPassCrossPointCount(originalVhl.getPassCrossPointCount());
//							newVhl.setDfkRouteList(originalVhl.getDfkRouteList());							
							newVhl.setUpdate(false);
//							if(redisUpdate)
//								RedisPool.jset(newVhl.getId(), newVhl);
//							newVhl.setRegData(originalVhl.getRegData());
						} else {
							newVhl.setUpdate(false);
						}

						result = newVhlId + ":OK";
					} break;
					case "Station": {
						Station newStation = (Station) newData;
						String newStationId = newStation.getId();
						Station originalStation = (Station) originalDataMap.get(newStationId);

						if (originalStation != null) {
							newStation.setUpdate(true);
							newStation.setAssignedVhl(originalStation.getAssignedVhl());
							newStation.setAvailable(originalStation.isAvailable());
							newStation.setAvgAssignCost(originalStation.getAvgAssignCost());
							newStation.setAvgReassignCount(originalStation.getAvgReassignCount());
							newStation.setCarrierId(originalStation.getCarrierId());
							newStation.setCarrierState(originalStation.getCarrierState());
							newStation.setCarryType(originalStation.getCarryType());
							newStation.setDestPortId(originalStation.getDestPortId());
							newStation.setFirstAssignCost(originalStation.getFirstAssignCost());
							newStation.setLastAssignedVhl(originalStation.getLastAssignedVhl());
							newStation.setLastAvgAssignCost(originalStation.getLastAvgAssignCost());
							newStation.setLastAvgReassignCount(originalStation.getLastAvgReassignCount());
							newStation.setLastCarrierId(originalStation.getLastCarrierId());
							newStation.setLastCarrierState(originalStation.getLastCarrierState());
							newStation.setLastDestPortId(originalStation.getLastDestPortId());
							newStation.setLastIsAvailable(originalStation.isLastIsAvailable());
							newStation.setLastReceivedTime(originalStation.getLastReceivedTime());
							newStation.setReassignCount(originalStation.getReassignCount());
							newStation.setReceivedTime(originalStation.getReceivedTime());
							newStation.setIncommingCmdIdMap(originalStation.getIncommingCmdIdMap());
							newStation.setOutGoingCmdId(originalStation.getOutGoingCmdId());
							newStation.setUpdate(false);
						} else {
							newStation.setUpdate(false);
						}

						result = newStationId + ":OK";
					} break;
					case "CnvPortNode":
					case "EqpPortNode":
					case "FioPortNode":
					case "StbNode" :
					case "StkPortNode":
					case "StkRmNode":
					case "StkShelfNode":
					case "RailNode":
					case "AbstractNode": {
						AbstractNode newNode = (AbstractNode) newData;
						String newNodeId = newNode.getId();
						AbstractNode originalNode = (AbstractNode) originalDataMap.get(newNodeId);
						String className = "";

						if (newNode instanceof CnvPortNode)
							className = "CnvPortNode";
						if (newNode instanceof EqpPortNode) {
							className = "EqpPortNode";
						} else if (newNode instanceof FioPortNode) {
							className = "FioPortNode";
						} else if(newNode instanceof StbNode) {
							className = "StbNode";
						} else if (newNode instanceof StkPortNode) {
							className = "StkPortNode";
						} else if (newNode instanceof StkRmNode) {
							className = "StkRmNode";
						} else if (newNode instanceof StkShelfNode) {
							className = "StkShelfNode";
						} else if (newNode instanceof RailNode) {
							className = "RailNode";
						}

						if (originalNode != null) {
							newNode.setUpdate(true);
							newNode.setAvailable(originalNode.isAvailable());

							try {
								switch (className) {
									case "RailNode": {
										RailNode coe = (RailNode) originalNode;
										RailNode cne = (RailNode) newNode;
										cne.setDrawX(coe.getDrawX());
										cne.setDrawY(coe.getDrawY());
										newNode.setUpdate(false);
									} break;
									case "CnvPortNode": {
										CnvPortNode coe = (CnvPortNode)originalNode;
										CnvPortNode cne = (CnvPortNode)newNode;

										cne.setAvgRemovalIntervalT(coe.getAvgRemovalIntervalT());
										cne.setCarrierRemovedTime(coe.getCarrierRemovedTime());
										cne.setCarrierInstalledTime(coe.getCarrierInstalledTime());
										cne.setDestPointedTime(coe.getDestPointedTime());
										cne.setCarrierIdList(coe.getCarrierIdList());
										cne.setAvailable(coe.isAvailable());
										newNode.setUpdate(false);
									} break;
									case "EqpPortNode": {
										EqpPortNode coe = (EqpPortNode) originalNode;
										EqpPortNode cne = (EqpPortNode) newNode;
										cne.setOccupiedTime(coe.getOccupiedTime());
										cne.setCarrierIds(coe.getCarrierIds());
										newNode.setUpdate(false);
									} break;
									case "FioPortNode": {
										FioPortNode coe = (FioPortNode) originalNode;
										FioPortNode cne = (FioPortNode) newNode;
										cne.setCarrierIdList(coe.getCarrierIdList());
										newNode.setUpdate(false);
									} break;
									case "StbNode" :
									{
										StbNode coe = (StbNode)originalNode;
										StbNode cne = (StbNode)newNode;
										cne.setCarrierId(coe.getCarrierId());
										cne.setOccupiedTime(coe.getOccupiedTime());	
										newNode.setUpdate(false);
	//										if(redisUpdate && cne.changed(coe)) {
	//											RedisPool.jset(cne.getId(), cne);
	//										}
									} break;
									case "StkPortNode": {
										StkPortNode coe = (StkPortNode) originalNode;
										StkPortNode cne = (StkPortNode) newNode;
										cne.setCarrierIdList(coe.getCarrierIdList());
										newNode.setUpdate(false);
									} break;
									case "StkRmNode": {
										StkRmNode coe = (StkRmNode) originalNode;
										StkRmNode cne = (StkRmNode) newNode;
										cne.setCarrierIdList(coe.getCarrierIdList());
										cne.setCommandIdList(coe.getCommandIdList());
										newNode.setUpdate(false);
									} break;
									case "StkShelfNode": {
										StkShelfNode coe = (StkShelfNode) originalNode;
										StkShelfNode cne = (StkShelfNode) newNode;
										cne.setCarrierIdList(coe.getCarrierIdList());
										newNode.setUpdate(false);
									} break;
								}
							} catch (Exception e) {
								logger.error("", e);
							}
						} else {
							newNode.setUpdate(false);
						}

						result = newNodeId + ":OK";
					} break;
					case "Conveyor":
					case "Fio":
					case "Oht":
					case "StbGroup" :
					case "Stocker":
					case "Eqp": {
						Eqp newEqp = (Eqp) newData;
						String newEqpId = newEqp.getId();
						Eqp originalEqp = (Eqp) originalDataMap.get(newEqpId);
						String className;

						if (newEqp instanceof Conveyor)
							className = "Conveyor";
						else if (newEqp instanceof Fio)
							className = "Fio";
						else if (newEqp instanceof Oht)
							className = "Oht";
						else if (newEqp instanceof StbGroup)
							className = "StbGroup";
						else if (newEqp instanceof Stocker)
							className = "Stocker";
						else className = "Eqp";

						if (originalEqp != null) {
							newEqp.setUpdate(true);
							newEqp.setAvailable(originalEqp.isAvailable());

							switch (className) {
								case "Fio":
								case "Eqp":
								case "Conveyor":
									break;
								case "Oht": {
									Oht coe = (Oht) originalEqp;
									Oht cne = (Oht) newEqp;
									cne.setAlarmState(coe.getAlarmState());
									cne.setControlState(coe.getControlState());
									cne.setLastAlarmState(coe.getLastAlarmState());
									cne.setLastControlState(coe.getLast_controlState());
									cne.setLastReceivedTime(coe.getLastReceivedTime());
									cne.setLastTscState(coe.getLastTscState());
									cne.setReceivedTime(coe.getReceivedTime());
									cne.setTscState(coe.getTscState());
								} break;
								case "StbGroup": {
									StbGroup coe = (StbGroup) originalEqp;
									StbGroup cne = (StbGroup) newEqp;
									cne.setFull(coe.isFull());
									cne.setOccupancyCnt(coe.getOccupancyCnt(dataSet));
								} break;
								case "Stocker": {
									Stocker coe = (Stocker) originalEqp;
									Stocker cne = (Stocker) newEqp;
									cne.setFull(coe.isFull());
									cne.setOccupancyCnt(coe.getOccupancyCnt(dataSet));
								} break;
							}

							newEqp.setUpdate(false);
						} else {
							newEqp.setUpdate(false);
						}
						result = newEqpId + ":OK";
					} break;
					default: {
						result = newData.getClass().getName() + ":No matching class name";
					} break;
				}

				return result;
			};

			futures.add(threadPool.submit(callable));
		}

		threadPool.shutdown();

		for (Future<String> future : futures) {
			String result = "";

			try {
				result = future.get();
			} catch (Exception e) {
				logger.error("",e);
			}

			if (!result.endsWith("OK")) {
				logger.warn(result);
			}
		}

		this._ELAPSED_TIME_LOG(sequence, startBlock);
	}

	private ConcurrentMap<String, List<String>> _readAndParsingTxtFile() {
		ConcurrentMap<String, List<String>> alarmCodeListMap = new ConcurrentHashMap<>();
		final String[] fileNameList = {"OhtHidOffAlarmCodeList.txt","OhtVhlOffAlarmCodeList.txt"};
		String line;
		String csvSplitBy = ",";

		logger.info("Reading and parsing text file started ...");

		for (String fileName : fileNameList) {
			String path = FilePathUtil.getOhtAlarmCodeCsvFilePath(fileName);
			File file = new File(path);

			if (!file.exists()) {
				logger.warn("... file is not exist [directory: {}]", path);

				continue;
			}

			BufferedReader bufferedReader = null;
			String key;

			switch (fileName) {
				case "OhtHidOffAlarmCodeList.txt": {
					key = FunctionType.HID_OFF.getKey();
				} break;
				case "OhtVhlOffAlarmCodeList.txt": {
					key = FunctionType.VHL_OFF.getKey();
				} break;
				default: continue;
			}

			try {
				bufferedReader = new BufferedReader(new FileReader(path));
				List<String> list = new ArrayList<>();

				while ((line = bufferedReader.readLine()) != null) {
					String[] data = line.split(csvSplitBy);

					if (data.length > 0) {
						String alarmCode = data[0].trim();

						if (alarmCode.length() == 4) {
							list.add(alarmCode);
						}
					}
				}

				alarmCodeListMap.put(key, list);
			} catch (Exception e) {
				alarmCodeListMap = new ConcurrentHashMap<>();

				logger.error("... An error occurred while reading and parsing text file for oht !", e);
			} finally {
				try {
					if (bufferedReader != null) {
						bufferedReader.close();
					}
				} catch (Exception e) {
					logger.error("... An error occurred while closing bufferedReader for oht !", e);
				}
			}
		}

		return alarmCodeListMap;
	}
	
	/**
	 * Reset a loop id of a railedge with RawLoop.
	 * @param fabId
	 * @param rawLoopMap
	 * @param ds
	 */
	static private void resetLoopId(final String fabId, final Map<String,Mcp75Config> mcp75ConfigMap, final Map<String, RailEdge> mapRailEdge, final Map<String, List<AbstractEdge>> mapFromNode2Edge) {
		for(String mcpName : mcp75ConfigMap.keySet()) {
			for(Map.Entry<String, RawLoop> entry : mcp75ConfigMap.get(mcpName).getRawLoopMap().entrySet()) {
				final Set<String> exitSet = new HashSet<String>();
				for(Integer[] exitOne : entry.getValue().getExitSet()) {
					final String railEdgeId = DataSet.address2RailEdgeId(fabId, mcpName, exitOne[0], exitOne[1]);
					exitSet.add(railEdgeId);
				}
				
				final Set<String> checked = new HashSet<String>();
				for(Integer[] entryOne : entry.getValue().getEntrySet()) {
					final RailEdge railEdge = mapRailEdge.get(DataSet.address2RailEdgeId(fabId, mcpName, entryOne[0], entryOne[1]));
					if (railEdge == null) continue;
					
					checked.clear();
					resetLoopIdInLoop(entry.getValue().getId(), railEdge, exitSet, checked, mapRailEdge, mapFromNode2Edge);
				}
			}
		}
	}
	
	/**
	 * Reset roop id.
	 * @param loopId
	 * @param edge
	 * @param exitSet
	 * @param checked
	 * @param ds
	 */
	static private void resetLoopIdInLoop(final int loopId, final RailEdge edge, final Set<String> exitSet, final Set<String> checked, 
									      final Map<String, RailEdge> mapRailEdge, final Map<String, List<AbstractEdge>> mapFromNode2Edge) {
		final String edgeId = edge.getId();
		if (exitSet.contains(edgeId) || checked.contains(edgeId))
			return;
		else {
			edge.setLoopId(loopId);
			checked.add(edgeId);
		}
		
		final List<AbstractEdge> edges = mapFromNode2Edge.get(edge.getToNodeId());
		if (edges == null)
			return;
		
		for(AbstractEdge edge2 : edges) {
			if (edge2 instanceof RailEdge == false)
				continue;
			
			resetLoopIdInLoop(loopId, (RailEdge)edge2, exitSet, checked, mapRailEdge, mapFromNode2Edge);
		}
	}

	public ConcurrentHashMap<String, OhtUdpListener> getOhtUdpListenerMap () {
		return ohtUdpListenerMap;
	}

	public void  setOhtUdpListenerMap (ConcurrentHashMap<String, OhtUdpListener> ohtUdpListenerMap) {
		this.ohtUdpListenerMap = ohtUdpListenerMap;
	}

	public static int getFabBits(String fabId) {
		return fabBitsMap.get(fabId);
	}

	public ConcurrentMap<String, FabProperties> getFabPropertiesMap() {
		return fabPropertiesMap;
	}

	public boolean getInitialized () {
		return isInitialized;
	}

	public ConcurrentMap<String, List<String>> getOhtAlarmCodeListMap() {
		return ohtAlarmCodeListMap;
	}

	public ConcurrentMap<String, TibrvService> getTibrvSenderMap() {
		return tibrvSenderMap;
	}

	public ConcurrentMap<String, TibrvService> getTibrvReceiverMap() {
		return tibrvReceiverMap;
	}

	public TibrvService getTibrvSenderMap (String key) {
		if (key == null || !tibrvSenderMap.containsKey(key)) {
			return null;
		}

		return tibrvSenderMap.get(key);
	}

	public ConcurrentMap<String, TibrvService> getTibrvSenderLikeMap (String key) {
		if (key == null) {
			return new ConcurrentHashMap<>();
		}

		ConcurrentMap<String, TibrvService> result = new ConcurrentHashMap<>();

		for (Map.Entry<String, TibrvService> item : this.tibrvSenderMap.entrySet()) {
			if (item.getKey().startsWith(key)) {
				result.put(item.getKey(), item.getValue());
			}
		}

		return result;
	}

	public void setRailCutInitialized(boolean isRailCutInitialized) {
		this.isRailCutInitialized = isRailCutInitialized;
	}

	public boolean getRailCutInitialized() {
		return isRailCutInitialized;
	}

	// waiting to send tib/rv message
	public void addTibrvMessageQueue(TibrvSendMsg data) {
		this.tibrvMessageQueue.add(data);
	}

	public void addTibrvMessageQueue(List<TibrvSendMsg> list) {
		this.tibrvMessageQueue.addAll(list);
	}

	public <T> void addTibrvMessageQueue(String key, String type, Map<String, T> data) {
		Map<String, Object> convertedData = new HashMap<>(data);
		TibrvSendMsg tibrvSendMsg = new TibrvSendMsg(key, type, convertedData);

		this.addTibrvMessageQueue(tibrvSendMsg);
	}

	public <T> void addTibrvMessageQueue(String key, String type, List<Map<String, T>> list) {
		List<TibrvSendMsg> tibrvSendMsgList = new ArrayList<>();

		for (Map<String, T> data : list) {
			Map<String, Object> convertedData = new HashMap<>(data);
			TibrvSendMsg tibrvSendMsg = new TibrvSendMsg(key, type, convertedData);

			tibrvSendMsgList.add(tibrvSendMsg);
		}

		if (!tibrvSendMsgList.isEmpty()) {
			this.addTibrvMessageQueue(tibrvSendMsgList);
		}
	}
	
	public <T> void addTibrvMessageQueue(String key, String type, SEND_MSG_FORMAT format, Map<String, T> data) {
		Map<String, Object> convertedData = new HashMap<>(data);
		TibrvSendMsg tibrvSendMsg = new TibrvSendMsg(key, type, format, convertedData);

		this.addTibrvMessageQueue(tibrvSendMsg);
	}
	//~waiting to send tib/rv message

	/**
	 * hid information with address number inserted in logpresso database
	 * function of `createNewDataSet` made hid information
	 * @param data hid information
	 */
	private void _insertHidDataIntoLogpresso(Map<String, List<String>> data) {
		long timer = System.currentTimeMillis();
		List<Tuple> logpressoData = new ArrayList<>();

		if (data.isEmpty()) return;

		for (Map.Entry<String, List<String>> item : data.entrySet()) {
			Tuple tuple 	= new Tuple();
			String key 		= item.getKey();
			String[] split 	= key.split(":");

			if (split.length > 2) {
				String fabId 		= split[0];
				String mcpName 		= split[1];
				int hidId 			= Integer.parseInt(split[2]);
				List<String> value 	= item.getValue();

				if (value.size() > 1) {
					int startAddress 			= Integer.parseInt(value.get(0));
					List<String> addressList 	= value.subList(1, value.size());

					tuple.put("FAB_ID", fabId);
					tuple.put("MCP_NM", mcpName);
					tuple.put("HID_ID", hidId);
					tuple.put("START", startAddress);
					tuple.put("ADDRESS", String.join(",", addressList));

					logpressoData.add(tuple);
				}
			}
		}

		boolean isInsertedData = LogpressoAPI.setInsertTuples("ATLAS_HID_INFO", logpressoData, 20);
		long checking = System.currentTimeMillis() - timer;

		if (isInsertedData) {
			logger.info("... hid information has been inserted in logpresso database [elapsed time: {}ms]", checking);
		} else {
			logger.error("... hid information has not inserted in logpresso database [elapsed time: {}ms]", checking);
		}
	}

	/**
	 * logpresso database 를 통해 최근 데이터를 조회하여 초기값으로 삼음
	 * ※ railEdge 초기값이 완성이 선행되어야 함
	 */
	private void _initializedVelocity() {
		long timer = System.currentTimeMillis();
		ConcurrentMap<String, RailEdge> railEdgeMap = getDataSet().getRailEdgeMap();

		// 결과 집계용
		Map<String, Integer> processCountingMap = new HashMap<>();
		List<String> logs = new ArrayList<>();

		processCountingMap.put("UNKNOWN", 0);

		try {
			List<Map<String, Object>> queryData = XmlUtil.selectLogpressoQuery("FIND_RECENT_VELOCITY");

			for (Map<String, Object> row : queryData) {
				if (row.get("velocity") == null || row.get("railEdgeId") == null) continue;

				String railEdgeId 	= row.get("railEdgeId").toString();
				double velocity 	= Double.parseDouble(row.get("velocity").toString());
				RailEdge railEdge 	= railEdgeMap.get(railEdgeId);

				if (railEdge != null) {
					railEdge.addVelocity(velocity);

					String fabId 	= railEdge.getFabId();
					String mcpName 	= railEdge.getMcpName();
					String key 		= fabId + ":" + mcpName;

					if (processCountingMap.containsKey(key)) {
						int count = processCountingMap.get(key);

						processCountingMap.put(key, ++count);
					} else {
						processCountingMap.put(key, 1);
					}
				} else {
					int count = processCountingMap.get("UNKNOWN");

					processCountingMap.put("UNKNOWN", ++count);
				}
			}

			int totalCount = 0;

			for (Map.Entry<String, Integer> entry : processCountingMap.entrySet()) {
				String key 	= entry.getKey();
				int count 	= entry.getValue();

				totalCount += count;

				logs.add(String.format("%10s : ", key) + count);
			}

			logs.add(String.format("%10s : ", "TOTAL") + totalCount);
		} catch (Exception e) {
			logger.error("", e);
		}

		Util.printHelper(logs);

		long checkTimer = System.currentTimeMillis() - timer;

		logger.info("... building an RAIL EDGE velocity(speed) has been finished [elapsed time: {}ms]", checkTimer);
	}

	private void _setRailEdgeRef(DataSet dataSet) {
		long timer = System.currentTimeMillis();

		if (dataSet.getRailEdgeMap() == null || dataSet.getRailEdgeMap().isEmpty()) {
			logger.warn("... railEdgeMap in dataSet is null or is empty !");
		}

		ConcurrentMap<String, RailEdge> railEdgeMap = dataSet.getRailEdgeMap();

		for(AbstractNode abstractNode : dataSet.getNodeMap().values()) {
			if (!(abstractNode instanceof RailNode)) continue;

			RailNode railNode = (RailNode) abstractNode;
			String leftEdgeId = railNode.getLeftEdgeId();
			String rightEdgeId = railNode.getRightEdgeId();

			if (leftEdgeId != null && !leftEdgeId.isEmpty()) {
				RailEdge railEdge = railEdgeMap.get(leftEdgeId);

				if (railEdge != null) {
					railNode.getToRailEdges().add(railEdge);
				}
			}

			if (rightEdgeId != null && !rightEdgeId.isEmpty()) {
				RailEdge railEdge = railEdgeMap.get(rightEdgeId);

				if (railEdge != null) {
					railNode.getToRailEdges().add(railEdge);
				}
			}
		}

		logger.info("... `_setRailEdgeRef` process has finished [elapsed time: {}ms]", System.currentTimeMillis() - timer);
	}

	private void _setNodeEdgeRef(DataSet dataSet) {
		long timer = System.currentTimeMillis();

		if (dataSet == null || dataSet.getNodeMap() == null) {
			logger.warn("... nodeMap in dataSet is null or is empty !");

			return;
		}

		for (AbstractNode abstractNode : dataSet.getNodeMap().values()) {
			if (abstractNode == null) {
				logger.warn("... abstract node is null !");

				continue;
			}

//			for(String longEdgeId : abstractNode.getToLongEdgeIds()) {
//				LongEdge longEdge = dataSet.getLongEdgeMap().get(longEdgeId);
//
//				if (longEdge == null) continue;
//
//				abstractNode.getToLongEdges().add(longEdge);
//
//				if(longEdgeId.matches(".+:RN:.+:RN:.+")) {
//					abstractNode.getToRailLongEdges().add(longEdge);
//				}
//			}

//			for(String longEdgeId : abstractNode.getFromLongEdgeIds()) {
//				LongEdge longEdge = dataSet.getLongEdgeMap().get(longEdgeId);
//
//				if (longEdge == null) continue;
//
//				abstractNode.getFromLongEdges().add(longEdge);
//
//				if(longEdgeId.matches(".+:RN:.+:RN:.+")) {
//					abstractNode.getFromRailLongEdges().add(longEdge);
//				}
//			}

			if (!abstractNode.getToEdgeIds().isEmpty()) {
				for (String edgeId : abstractNode.getToEdgeIds()) {
					AbstractEdge abstractEdge = dataSet.getEdgeMap().get(edgeId);

					if (abstractEdge != null) {
						abstractNode.getToEdges().add(abstractEdge);
					}
				}
			}

			if (!abstractNode.getFromEdgeIds().isEmpty()) {
				for (String edgeId : abstractNode.getFromEdgeIds()) {
					AbstractEdge abstractEdge = dataSet.getEdgeMap().get(edgeId);

					if (abstractEdge != null) {
						abstractNode.getFromEdges().add(abstractEdge);
					}
				}
			}
		}

		logger.info("... `_setNodeEdgeRef` process has finished [elapsed time: {}ms]", System.currentTimeMillis() - timer);
	}

	private void _setSpnOhtFabId(DataSet ds) {
		try {
			for(Stocker lft : ds.getStockerMap().values()) {
				if(lft.getStkType() == STK_TYPE.ZIPTOWER || lft.getStkType() == STK_TYPE.INTERLAYER || lft.getStkType() == STK_TYPE.PODZIPTOWER|| lft.getStkType() == STK_TYPE.LIFTER) {
					for(String portNodeId : lft.getPortNodeIdList()) {
						StkPortNode spn = (StkPortNode)ds.getNodeMap().get(portNodeId);
						if(spn!=null && spn.getInOutType() == STK_PORT_INOUT_TYPE.IN && spn.isTeConnection()) {
							for(String fromEdgeId : spn.getFromEdgeIds()) {
								AbstractEdge fromAE = ds.getEdgeMap().get(fromEdgeId);
								if(fromAE instanceof TransferEdge) {
									RailNode frn = (RailNode)ds.getNodeMap().get(fromAE.getFromNodeId());
									spn.setOhtFabId(frn.getFabId());
									spn.setOhtMcpNm(frn.getMcpName());
									break;
								}
							}
						}else if(spn!=null && spn.getInOutType() == STK_PORT_INOUT_TYPE.OUT && spn.isTeConnection()) {
							for(String toEdgeId : spn.getToEdgeIds()) {
								AbstractEdge toAE = ds.getEdgeMap().get(toEdgeId);
								if(toAE instanceof TransferEdge) {
									RailNode trn = (RailNode)ds.getNodeMap().get(toAE.getToNodeId());
									spn.setOhtFabId(trn.getFabId());
									spn.setOhtMcpNm(trn.getMcpName());
									break;
								}
							}
						}
					}
				}
			}
		}catch(Exception e) {
			logger.error("faied set stocker port node in/out oht fabId, mcpName",e);
		}
	}

	private DataSet _fabConnect(DataSet ds, boolean isUpdate) {
		for(FabProperties fp : fabPropertiesMap.values()) {
			String passiveFabId = fp.getFabId();
			if(fp.getBridgeFromSet().size() > 0) {
				for(String activeFabId : fp.getBridgeFromSet().keySet()) {
					for(String bridgeEqpId : fp.getBridgeFromSet().get(activeFabId)) {						
						if(ds.getAllEqpNameMap().get(bridgeEqpId) instanceof Stocker) {
							Stocker bridgeEqp = (Stocker)ds.getAllEqpNameMap().get(bridgeEqpId);
							for(String portNodeId : bridgeEqp.getPortNodeIdList()) {
								StkPortNode spn = (StkPortNode)ds.getNodeMap().get(portNodeId);
								if(spn.getToEdgeIds().size() == 0 && spn.getInOutType() == STK_PORT_INOUT_TYPE.OUT) {
									int direction = 0;
									for(StkPortNode.SubPort subPort : spn.getSubPortList()) {
										if(ds.getStationPortMap().keySet().contains(subPort.name)) {
											Station st = ds.getStationPortMap().get(subPort.name);
											RailNode rn = (RailNode)ds.getNodeMap().get(st.getRailNodeId());
											//transferEdge 만들기
											TransferEdge te = new TransferEdge(passiveFabId, passiveFabId + ":"+ DataSet.TRANS_EDGE_PREFIX+ ":" + portNodeId+"-"+st.getId(), portNodeId, st.getRailNodeId(), "", st.getId(), 7000, true, 2000, isUpdate);
											st.setAcquireTransferEdgeId(te.getId());
											//층간 Lifter 영역의 area, bay명은 
											te.setAreaName(rn.getAreaName());
											te.setAreaId(rn.getAreaId());
											te.setBayName(rn.getBayName());
											te.setBayId(rn.getBayId());
											spn.setAreaName(rn.getAreaName());
											spn.setAreaId(rn.getAreaId());
											spn.setBayName(rn.getBayName());
											spn.setBayId(rn.getBayId());
											spn.setTeConnection(true);
											rn.setTeConnection(true);
											ds.getEdgeMap().put(te.getId(), te);
											ds.getTransferEdgeMap().put(te.getId(), te);
											
											spn.getToEdgeIds().add(te.getId());
											spn.setToEdgeIds(spn.getToEdgeIds());
											rn.getFromEdgeIds().add(te.getId());
											rn.setFromEdgeIds(rn.getFromEdgeIds());
											//longEdge 만들기
											FirstEdgeInfo fei = firstEdgeInfoMap.get(te.getId());
											String longEdgeId = "";
											if(fei!=null && portNodeId.equals(fei.getLongEdgeFromNodeId()) && rn.getId().equals(fei.getLongEdgeToNodeId())) {
												longEdgeId = fei.getLongEdgeId();
												direction = fei.getLongEdgeDir();												
											}else {
												Integer fromNodeMaxLongEdgeDir = curMaxLongEdgeDirMap.get(portNodeId);
												if(fromNodeMaxLongEdgeDir!= null && fromNodeMaxLongEdgeDir >= 0) {
													direction = ++fromNodeMaxLongEdgeDir;
													curMaxLongEdgeDirMap.put(portNodeId, fromNodeMaxLongEdgeDir);
													
												}else {
													curMaxLongEdgeDirMap.put(portNodeId, direction);
												}
												longEdgeId = passiveFabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + portNodeId + "-" + direction + "-" + rn.getId();
												fei = new FirstEdgeInfo(te.getId(), longEdgeId, "", direction, portNodeId, rn.getId(), "", "", -1);
												firstEdgeInfoMap.put(fei.getFirstEdgeId(),fei);
											}
											//String longEdgeId = passiveFabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + portNodeId + "-" + direction + "-" + rn.getId();
											te.setLongEdgeId(longEdgeId);
//											if (showLogAllMapData)
//												logger.debug("LongEdge id : {} build completed",longEdgeId);
											ConcurrentLinkedQueue<String> edgeIdList = new ConcurrentLinkedQueue<String>();
											edgeIdList.add(te.getId());
											LongEdge le = new LongEdge(passiveFabId, longEdgeId, portNodeId, rn.getId(), direction, edgeIdList, isUpdate);											
											ds.getLongEdgeMap().put(longEdgeId, le);
											le.setAreaName(te.getAreaName());
											le.setBayName(te.getBayName());
											le.setAreaId(te.getAreaId());
											le.setBayId(te.getBayId());
											spn.getToLongEdgeIds().add(longEdgeId);
											spn.setToLongEdgeIds(spn.getToLongEdgeIds());
											rn.getFromLongEdgeIds().add(longEdgeId);
											rn.setFromLongEdgeIds(rn.getFromLongEdgeIds());
											direction++;
										}
									}
								}else if(spn.getFromEdgeIds().size() == 0 && spn.getInOutType() == STK_PORT_INOUT_TYPE.IN) {
									int direction = 0;
									for(StkPortNode.SubPort subPort : spn.getSubPortList()) {
										if(ds.getStationPortMap().keySet().contains(subPort.name)) {
											Station st = ds.getStationPortMap().get(subPort.name);
											RailNode rn = (RailNode)ds.getNodeMap().get(st.getRailNodeId());											
											//transferEdge 만들기
											TransferEdge te = new TransferEdge(passiveFabId, passiveFabId + ":"+ DataSet.TRANS_EDGE_PREFIX+ ":" + st.getId()+"-"+portNodeId, st.getRailNodeId(), portNodeId, st.getId(), "", 7000, false, 2000, isUpdate);
											st.setDepositTransferEdgeId(te.getId());
											ds.getEdgeMap().put(te.getId(), te);
											ds.getTransferEdgeMap().put(te.getId(), te);
											te.setAreaName(rn.getAreaName());
											te.setBayName(rn.getBayName());
											te.setAreaId(rn.getAreaId());
											te.setBayId(rn.getBayId());
											spn.setAreaName(rn.getAreaName());
											spn.setAreaId(rn.getAreaId());
											spn.setBayName(rn.getBayName());
											spn.setBayId(rn.getBayId());
											spn.getFromEdgeIds().add(te.getId());
											spn.setFromEdgeIds(spn.getFromEdgeIds());
											spn.setTeConnection(true);
											rn.setTeConnection(true);
											rn.getToEdgeIds().add(te.getId());
											rn.setToEdgeIds(rn.getToEdgeIds());
											//longEdge 만들기
											//String longEdgeId = passiveFabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + rn.getId() + "-" + direction + "-" + portNodeId;
											FirstEdgeInfo fei = firstEdgeInfoMap.get(te.getId());
											String longEdgeId = "";
											if(fei!=null && rn.getId().equals(fei.getLongEdgeFromNodeId()) && portNodeId.equals(fei.getLongEdgeToNodeId())) {
												longEdgeId = fei.getLongEdgeId();
												direction = fei.getLongEdgeDir();												
											}else {
												Integer fromNodeMaxLongEdgeDir = curMaxLongEdgeDirMap.get(rn.getId());
												if(fromNodeMaxLongEdgeDir!= null && fromNodeMaxLongEdgeDir >= 0) {
													direction = ++fromNodeMaxLongEdgeDir;
													curMaxLongEdgeDirMap.put(rn.getId(), fromNodeMaxLongEdgeDir);													
												}else {
													curMaxLongEdgeDirMap.put(rn.getId(), direction);
												}
												longEdgeId = passiveFabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + rn.getId() + "-" + direction + "-" + portNodeId;
												fei = new FirstEdgeInfo(te.getId(), longEdgeId, "", direction, rn.getId(), portNodeId, "", "", -1);
												firstEdgeInfoMap.put(fei.getFirstEdgeId(),fei);
											}
											te.setLongEdgeId(longEdgeId);
//											if (showLogAllMapData)
//												logger.debug("LongEdge id : {} build completed",longEdgeId);
											ConcurrentLinkedQueue<String> edgeIdList = new ConcurrentLinkedQueue<String>();
											edgeIdList.add(te.getId());
											LongEdge le = new LongEdge(passiveFabId, longEdgeId, rn.getId(), portNodeId, direction, edgeIdList, isUpdate);
											ds.getLongEdgeMap().put(longEdgeId, le);
											le.setAreaName(te.getAreaName());
											le.setBayName(te.getBayName());
											le.setAreaId(te.getAreaId());
											le.setBayId(te.getBayId());
											spn.getFromLongEdgeIds().add(longEdgeId);
											spn.setFromLongEdgeIds(spn.getFromLongEdgeIds());
											rn.getToLongEdgeIds().add(longEdgeId);
											rn.setToLongEdgeIds(rn.getToLongEdgeIds());
											direction++;
										}
									}
								}
							}
						}else if(ds.getAllEqpNameMap().get(bridgeEqpId) instanceof Conveyor) {
							Conveyor bridgeEqp = (Conveyor)ds.getAllEqpNameMap().get(bridgeEqpId);
							for(String portNodeId : bridgeEqp.getPortNodeIdList()) {
								CnvPortNode cpn = (CnvPortNode)ds.getNodeMap().get(portNodeId);
								if(cpn.getToEdgeIds().size() == 0 && cpn.getType() == CNV_NODE_TYPE.OUTPUT) {
									int direction = 0;
									if(ds.getStationPortMap().keySet().contains(cpn.getName())) {
										Station st = ds.getStationPortMap().get(cpn.getName());
										RailNode rn = (RailNode)ds.getNodeMap().get(st.getRailNodeId());
										//transferEdge 만들기
										TransferEdge te = new TransferEdge(passiveFabId, passiveFabId + ":"+ DataSet.TRANS_EDGE_PREFIX+ ":" + portNodeId+"-"+st.getId(), portNodeId, st.getRailNodeId(), "", st.getId(), 7000, true, 2000, isUpdate);
										st.setAcquireTransferEdgeId(te.getId());
										//층간 Lifter 영역의 area, bay명은 
										te.setAreaName(rn.getAreaName());
										te.setAreaId(rn.getAreaId());
										te.setBayName(rn.getBayName());
										te.setBayId(rn.getBayId());
										cpn.setTeConnection(true);
										cpn.setAreaName(rn.getAreaName());
										cpn.setAreaId(rn.getAreaId());
										cpn.setBayName(rn.getBayName());
										cpn.setBayId(rn.getBayId());
										rn.setTeConnection(true);
										ds.getEdgeMap().put(te.getId(), te);
										ds.getTransferEdgeMap().put(te.getId(), te);
										
										cpn.getToEdgeIds().add(te.getId());
										cpn.setToEdgeIds(cpn.getToEdgeIds());
										rn.getFromEdgeIds().add(te.getId());
										rn.setFromEdgeIds(rn.getFromEdgeIds());
										//longEdge 만들기
										//String longEdgeId = passiveFabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + portNodeId + "-" + direction + "-" + rn.getId();
										FirstEdgeInfo fei = firstEdgeInfoMap.get(te.getId());
										String longEdgeId = "";
										if(fei!=null && portNodeId.equals(fei.getLongEdgeFromNodeId()) && rn.getId().equals(fei.getLongEdgeToNodeId())) {
											longEdgeId = fei.getLongEdgeId();
											direction = fei.getLongEdgeDir();												
										}else {
											Integer fromNodeMaxLongEdgeDir = curMaxLongEdgeDirMap.get(rn.getId());
											if(fromNodeMaxLongEdgeDir!= null && fromNodeMaxLongEdgeDir >= 0) {
												direction = ++fromNodeMaxLongEdgeDir;
												curMaxLongEdgeDirMap.put(portNodeId, fromNodeMaxLongEdgeDir);
												
											}else {
												curMaxLongEdgeDirMap.put(portNodeId, direction);
											}
											longEdgeId = passiveFabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + portNodeId + "-" + direction + "-" + rn.getId();
											fei = new FirstEdgeInfo(te.getId(), longEdgeId, "", direction, portNodeId, rn.getId(), "", "", -1);
											firstEdgeInfoMap.put(fei.getFirstEdgeId(),fei);
										}
										te.setLongEdgeId(longEdgeId);
//										if (showLogAllMapData)
//											logger.debug("LongEdge id : {} build completed",longEdgeId);
										ConcurrentLinkedQueue<String> edgeIdList = new ConcurrentLinkedQueue<String>();
										edgeIdList.add(te.getId());
										LongEdge le = new LongEdge(passiveFabId, longEdgeId, portNodeId, rn.getId(), direction, edgeIdList, isUpdate);											
										ds.getLongEdgeMap().put(longEdgeId, le);
										le.setAreaName(te.getAreaName());
										le.setBayName(te.getBayName());
										le.setAreaId(te.getAreaId());
										le.setBayId(te.getBayId());										
										cpn.getToLongEdgeIds().add(longEdgeId);
										cpn.setToLongEdgeIds(cpn.getToLongEdgeIds());
										rn.getFromLongEdgeIds().add(longEdgeId);
										rn.setFromLongEdgeIds(rn.getFromLongEdgeIds());
									}
								}else if(cpn.getFromEdgeIds().size() == 0 && cpn.getType() == CNV_NODE_TYPE.INPUT) {
									int direction = 0;
									if(ds.getStationPortMap().keySet().contains(cpn.getName())) {
										Station st = ds.getStationPortMap().get(cpn.getName());
										RailNode rn = (RailNode)ds.getNodeMap().get(st.getRailNodeId());											
										//transferEdge 만들기
										TransferEdge te = new TransferEdge(passiveFabId, passiveFabId + ":"+ DataSet.TRANS_EDGE_PREFIX+ ":" + st.getId()+"-"+portNodeId, st.getRailNodeId(), portNodeId, st.getId(), "", 7000, false, 2000, isUpdate);
										st.setDepositTransferEdgeId(te.getId());
										ds.getEdgeMap().put(te.getId(), te);
										ds.getTransferEdgeMap().put(te.getId(), te);
										te.setAreaName(rn.getAreaName());
										te.setBayName(rn.getBayName());
										te.setAreaId(rn.getAreaId());
										te.setBayId(rn.getBayId());
										cpn.getFromEdgeIds().add(te.getId());
										cpn.setFromEdgeIds(cpn.getFromEdgeIds());
										cpn.setTeConnection(true);
										cpn.setAreaName(rn.getAreaName());
										cpn.setAreaId(rn.getAreaId());
										cpn.setBayName(rn.getBayName());
										cpn.setBayId(rn.getBayId());
										rn.setTeConnection(true);
										rn.getToEdgeIds().add(te.getId());
										rn.setToEdgeIds(rn.getToEdgeIds());
										//longEdge 만들기
										//String longEdgeId = passiveFabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + rn.getId() + "-" + direction + "-" + portNodeId;
										FirstEdgeInfo fei = firstEdgeInfoMap.get(te.getId());
										String longEdgeId = "";
										if(fei!=null && rn.getId().equals(fei.getLongEdgeFromNodeId()) && portNodeId.equals(fei.getLongEdgeToNodeId())) {
											longEdgeId = fei.getLongEdgeId();
											direction = fei.getLongEdgeDir();												
										}else {
											Integer fromNodeMaxLongEdgeDir = curMaxLongEdgeDirMap.get(rn.getId());
											if(fromNodeMaxLongEdgeDir!= null && fromNodeMaxLongEdgeDir >= 0) {
												direction = ++fromNodeMaxLongEdgeDir;
												curMaxLongEdgeDirMap.put(rn.getId(), fromNodeMaxLongEdgeDir);
												
											}else {
												curMaxLongEdgeDirMap.put(rn.getId(), direction);
											}
											longEdgeId = passiveFabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + rn.getId() + "-" + direction + "-" + portNodeId;
											fei = new FirstEdgeInfo(te.getId(), longEdgeId, "", direction, rn.getId(), portNodeId, "", "", -1);
											firstEdgeInfoMap.put(fei.getFirstEdgeId(),fei);
										}
										te.setLongEdgeId(longEdgeId);
//										if (showLogAllMapData)
//											logger.debug("LongEdge id : {} build completed",longEdgeId);
										ConcurrentLinkedQueue<String> edgeIdList = new ConcurrentLinkedQueue<String>();
										edgeIdList.add(te.getId());
										LongEdge le = new LongEdge(passiveFabId, longEdgeId, rn.getId(), portNodeId, direction, edgeIdList, isUpdate);
										ds.getLongEdgeMap().put(longEdgeId, le);
										le.setAreaName(te.getAreaName());
										le.setBayName(te.getBayName());
										le.setAreaId(te.getAreaId());
										le.setBayId(te.getBayId());										
										cpn.getFromLongEdgeIds().add(longEdgeId);
										cpn.setFromLongEdgeIds(cpn.getFromLongEdgeIds());
										rn.getToLongEdgeIds().add(longEdgeId);
										rn.setToLongEdgeIds(rn.getToLongEdgeIds());
									}
								}
							}
						}						
						
					}
				}
			}
		}
		return ds;
	}
	
	private DataSet _inlineConnect(DataSet ds, boolean isUpdate) {
		for(FabProperties fp : fabPropertiesMap.values()) {
			String fabId = fp.getFabId();
			if(fp.getInlineConnectSet().size() > 0) {
				for(String stkId : fp.getInlineConnectSet().keySet()) {
					Stocker stk = (Stocker)ds.getAllEqpNameMap().get(stkId);
					try {
						StkRmNode srn = (StkRmNode)ds.getNodeMap().get(stk.getRmId());		
						
						for(String eqpPortId : fp.getInlineConnectSet().get(stkId)) {						
							if(ds.getNodePortMap().get(eqpPortId) instanceof EqpPortNode) {
								EqpPortNode eqpPortNode = (EqpPortNode)ds.getNodePortMap().get(eqpPortId);
								eqpPortNode.setInlinePort(true);
								String sreDepositId = fabId + ":"+ DataSet.STK_RM_EDGE_PREFIX+ ":" + srn.getId()+"-"+eqpPortNode.getId();
								StkRmEdge sreDeposit = new StkRmEdge(fabId, sreDepositId, stk.getId(), srn.getId(), eqpPortNode.getId(), 1500L, false, 3000L, true, false, isUpdate);
								while(eqpPortNode.getFromEdgeIds().remove(sreDepositId)) {}
								eqpPortNode.getFromEdgeIds().add(sreDepositId);
								eqpPortNode.setFromEdgeIds(eqpPortNode.getFromEdgeIds());
								eqpPortNode.setAreaName(srn.getAreaName());
								eqpPortNode.setBayName(srn.getBayName());
								sreDeposit.setAreaName(srn.getAreaName());
								sreDeposit.setBayName(srn.getBayName());
								eqpPortNode.setAreaId(srn.getAreaId());
								eqpPortNode.setBayId(srn.getBayId());
								sreDeposit.setAreaId(srn.getAreaId());
								sreDeposit.setBayId(srn.getBayId());
								ds.getEdgeMap().put(sreDeposit.getId(), sreDeposit);
								ds.getStkRmEdgeMap().put(sreDeposit.getId(), sreDeposit);
								while(srn.getToEdgeIds().remove(sreDepositId)) {}
								srn.getToEdgeIds().add(sreDepositId);
								srn.setToEdgeIds(srn.getToEdgeIds());
								//String longEdgeId = fabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + srn.getId() + "-" + 0 + "-" + eqpPortNode.getId();
								FirstEdgeInfo fei = firstEdgeInfoMap.get(sreDeposit.getId());
								String longEdgeId = "";
								int direction = 0;
								if(fei!=null && srn.getId().equals(fei.getLongEdgeFromNodeId()) && eqpPortNode.getId().equals(fei.getLongEdgeToNodeId())) {
									longEdgeId = fei.getLongEdgeId();
									direction = fei.getLongEdgeDir();												
								}else {
									Integer fromNodeMaxLongEdgeDir = curMaxLongEdgeDirMap.get(srn.getId());
									if(fromNodeMaxLongEdgeDir!= null && fromNodeMaxLongEdgeDir >= 0) {
										direction = ++fromNodeMaxLongEdgeDir;
										curMaxLongEdgeDirMap.put(srn.getId(), fromNodeMaxLongEdgeDir);
										
									}else {
										curMaxLongEdgeDirMap.put(srn.getId(), direction);
									}
									longEdgeId = fabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + srn.getId() + "-" + direction + "-" + eqpPortNode.getId();
									fei = new FirstEdgeInfo(sreDeposit.getId(), longEdgeId, "", direction, srn.getId(), eqpPortNode.getId(), "", "", -1);
									firstEdgeInfoMap.put(fei.getFirstEdgeId(),fei);
								}
								sreDeposit.setLongEdgeId(longEdgeId);
								ConcurrentLinkedQueue<String> edgeIdList = new ConcurrentLinkedQueue<String>();
								edgeIdList.add(sreDepositId);
								LongEdge le = new LongEdge(fabId, longEdgeId, srn.getId(), eqpPortNode.getId(), 0, edgeIdList, isUpdate);
								ds.getLongEdgeMap().put(le.getId(), le);
								le.setAreaName(srn.getAreaName());
								le.setBayName(srn.getBayName());
								le.setAreaId(srn.getAreaId());
								le.setBayId(srn.getBayId());
								while(srn.getToLongEdgeIds().remove(le.getId())) {}
								srn.getToLongEdgeIds().add(le.getId());
								srn.setToLongEdgeIds(srn.getToLongEdgeIds());
								while(eqpPortNode.getFromLongEdgeIds().remove(le.getId())){}
								eqpPortNode.getFromLongEdgeIds().add(le.getId());
								eqpPortNode.setFromLongEdgeIds(eqpPortNode.getFromLongEdgeIds());
															
								String sreAcquireId = fabId + ":"+ DataSet.STK_RM_EDGE_PREFIX+ ":" + eqpPortNode.getId() +"-"+srn.getId();
								StkRmEdge sreAcquire = new StkRmEdge(fabId, sreAcquireId, stk.getId(), eqpPortNode.getId(), srn.getId(), 1500L, false, 3000L, false, false, isUpdate);
								while(eqpPortNode.getToEdgeIds().remove(sreAcquireId)) {}
								eqpPortNode.getToEdgeIds().add(sreAcquireId);
								eqpPortNode.setToEdgeIds(eqpPortNode.getToEdgeIds());
								sreAcquire.setAreaName(srn.getAreaName());
								sreAcquire.setBayName(srn.getBayName());
								sreAcquire.setAreaId(srn.getAreaId());
								sreAcquire.setBayId(srn.getBayId());
								ds.getEdgeMap().put(sreAcquire.getId(), sreAcquire);
								ds.getStkRmEdgeMap().put(sreAcquire.getId(), sreAcquire);
								while(srn.getFromEdgeIds().remove(sreAcquireId)) {}
								srn.getFromEdgeIds().add(sreAcquireId);
								srn.setFromEdgeIds(srn.getFromEdgeIds());
								//longEdgeId = fabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + eqpPortNode.getId() + "-" + 0 + "-" + srn.getId();
								fei = firstEdgeInfoMap.get(sreAcquire.getId());
								longEdgeId = "";
								direction = 0;
								if(fei!=null && eqpPortNode.getId().equals(fei.getLongEdgeFromNodeId()) && srn.getId().equals(fei.getLongEdgeToNodeId())) {
									longEdgeId = fei.getLongEdgeId();
									direction = fei.getLongEdgeDir();												
								}else {
									Integer fromNodeMaxLongEdgeDir = curMaxLongEdgeDirMap.get(eqpPortNode.getId());
									if(fromNodeMaxLongEdgeDir!= null && fromNodeMaxLongEdgeDir >= 0) {
										direction = ++fromNodeMaxLongEdgeDir;
										curMaxLongEdgeDirMap.put(eqpPortNode.getId(), fromNodeMaxLongEdgeDir);
										
									}else {
										curMaxLongEdgeDirMap.put(eqpPortNode.getId(), direction);
									}
									longEdgeId = fabId + ":"+ DataSet.LONG_EDGE_PREFIX+ ":" + eqpPortNode.getId() + "-" + direction + "-" + srn.getId();
									fei = new FirstEdgeInfo(sreAcquire.getId(), longEdgeId, "", direction, eqpPortNode.getId(), srn.getId(), "", "", -1);
									firstEdgeInfoMap.put(fei.getFirstEdgeId(),fei);
								}
								sreAcquire.setLongEdgeId(longEdgeId);
								edgeIdList = new ConcurrentLinkedQueue<String>();
								edgeIdList.add(sreAcquireId);
								le = new LongEdge(fabId, longEdgeId, eqpPortNode.getId(), srn.getId(), 0, edgeIdList, isUpdate);
								ds.getLongEdgeMap().put(le.getId(), le);
								le.setAreaName(srn.getAreaName());
								le.setBayName(srn.getBayName());
								le.setAreaId(srn.getAreaId());
								le.setBayId(srn.getBayId());
								while(srn.getFromLongEdgeIds().remove(le.getId())) {}
								srn.getFromLongEdgeIds().add(le.getId());
								srn.setFromLongEdgeIds(srn.getFromLongEdgeIds());
								while(eqpPortNode.getToLongEdgeIds().remove(le.getId())) {}
								eqpPortNode.getToLongEdgeIds().add(le.getId());
								eqpPortNode.setToLongEdgeIds(eqpPortNode.getToLongEdgeIds());							
							}						
							
						}
					}catch(Exception e) {
						logger.error("Inline connection error : {}", stkId, e);
					}
				}
			}
		}
		return ds;
	}
	
	public void updateEqpExtInfo(DataSet ds) {
		try {
			int i=0;
			List<Map<String, Object>> eqpExtInfoList = LogpressoAPI.responseResult("memlookup op=list name=MEM_ATALS_MAS_EQP_EXT");
			if(eqpExtInfoList!=null) {
				for(Map<String, Object> eqpExtInfo : eqpExtInfoList) {
					String eqpId = (String)eqpExtInfo.get("id");
					if(StringUtils.isNotEmpty(eqpId)) {
						Eqp eqp = ds.getAllEqpMap().get(eqpId);
						if(eqp!=null) {
							if(StringUtils.isNotEmpty((String)eqpExtInfo.get("detEqpTyp")))
								eqp.setDetEqpTyp((String)eqpExtInfo.get("detEqpTyp"));
							if(StringUtils.isNotEmpty((String)eqpExtInfo.get("eqpGrpNm"))) {
								eqp.setEqpGrpNm((String)eqpExtInfo.get("eqpGrpNm"));
								i++;
							}
						}
					}
				}
			}
			logger.debug("MEM_ATALS_MAS_EQP_EXT query({}) and update({}) completed", eqpExtInfoList.size(), i);
		}catch(Exception e) {
			logger.error("MEM_ATALS_MAS_EQP_EXT query error",e);
		}
	}
	
	/**
	 * 텍스트 형식으로 데이터를 확인
	 */
	public void writeRecording() {
		// 가변적 데이터와 (준)불변적 데이터는 기록하는 방식에서 차이
		for (FabProperties fabProperties : fabPropertiesMap.values()) {
			String fabId = fabProperties.getFabId();

			for (String mcpName : fabProperties.getMcpName2OhtNameMap().keySet()) {
				// (준)불변적 데이터
				this._writeRailEdgeRecording(fabId, mcpName);
			}
		}

		// 가변적 데이터
		this._writeVehicleRecording();
	}

	private void _writeRailEdgeRecording(String fabId, String mcpName) {
		final ConcurrentMap<String, RailEdge> mappingData = getDataSet().getRailEdgeMap();

		String fileName 		= "RAIL_EDGE_" + fabId + "_" + mcpName + ".csv";
		StringBuilder csvData 	= new StringBuilder();

		csvData.append("RAIL_EDGE_ID").append(",")
				.append("FROM_ADDRESS").append(",")
				.append("TO_ADDRESS").append(",")
				.append("HID_ID")
				.append("\n");

		if (!mappingData.isEmpty()) {
			String compareKey = fabId + ":" + DataSet.RAIL_EDGE_PREFIX + ":" + mcpName;

			for (Map.Entry<String, RailEdge> entry : mappingData.entrySet()) {
				String key = entry.getKey();

				if (!key.contains(compareKey)) continue;

				RailEdge railEdge = entry.getValue();
				String fromAddress, toAddress, hidId;

				if (railEdge == null) {
					fromAddress	= "NA";
					toAddress 	= "NA";
					hidId 		= "NA";
				} else {
					fromAddress	= String.valueOf(railEdge.getFromAddress());
					toAddress 	= String.valueOf(railEdge.getToAddress());
					hidId		= String.valueOf(railEdge.getHIDId());
				}

				csvData.append(key).append(",")
						.append(fromAddress).append(",")
						.append(toAddress).append(",")
						.append(hidId)
						.append("\n");
			}
		}

		this._write(csvData, fileName);
	}

	private void _writeVehicleRecording() {
		final ConcurrentMap<String, Vhl> mappingData = getDataSet().getVhlMap();

		String fileName 		= "VEHICLE.csv";
		StringBuilder csvData 	= new StringBuilder();

		csvData.append("VHL_ID").append(",")
				.append("UNIT_ID")
				.append("\n");

		if (!mappingData.isEmpty()) {
			for (Map.Entry<String, Vhl> entry : mappingData.entrySet()) {
				String key 	= entry.getKey();
				Vhl value 	= entry.getValue();
				String vehicleName;

				if (value == null) {
					vehicleName = "NA";
				} else {
					vehicleName = value.getName();
				}

				csvData.append(key).append(",")
						.append(vehicleName).append(",")
						.append("\n");
			}
		}

		this._write(csvData, fileName);
	}

	private void _write(StringBuilder csvData, String fileName) {
		final String folderPath	= FilePathUtil.RECORD_FILE_PATH;

		try {
			Util.createAndOverwriteFile(folderPath, fileName, csvData.toString());
		} catch (Exception e) {
			logger.error("", e);
		}
	}
	

	// ampUrl
	public String getAmpUrl()
	{
		return ampUrl;
	}
	public void setAmpUrl(String ampUrl)
	{
		this.ampUrl = ampUrl;
	}
	// ampListener
	public AmpListener getAmpListener()
	{
		return ampListener;
	}
	public void setAmpListener(AmpListener ampListener)
	{
		this.ampListener = ampListener;
	}
		
	private class RecursiveRailAreaBayNameSetter{
		private ConcurrentMap<String,RailEdge> railEdgeMap;
		private ConcurrentMap<String,AbstractEdge> edgeMap;
		private ConcurrentMap<String,RailNode> railNodeMap;
		private ConcurrentMap<String,AbstractNode> nodeMap;
		private ConcurrentMap<String,Station> stationMap;
		private ForkJoinPool tpool;
		
		public RecursiveRailAreaBayNameSetter(ConcurrentMap<String,RailEdge> railEdgeMap, ConcurrentMap<String,AbstractEdge> edgeMap, ConcurrentMap<String,AbstractNode> nodeMap, ConcurrentMap<String, Station> stationMap, ForkJoinPool tpool) {
			this.nodeMap = nodeMap;
			this.edgeMap = edgeMap;
			this.railEdgeMap = railEdgeMap;
			this.tpool = tpool;
			this.railNodeMap = new ConcurrentHashMap<String, RailNode>();
			for(Entry<String, AbstractNode> entry : nodeMap.entrySet()) {
				if(entry.getValue() instanceof RailNode)
					this.railNodeMap.put(entry.getKey(), (RailNode)entry.getValue());
			}
			this.stationMap = stationMap;
			
			try {
				this.tpool.submit(()->{
					this.railNodeMap.values().parallelStream().forEach(an ->{
						if(StringUtils.isEmpty(an.getAreaName()) == false) {
							//setAreaName
							
							Stack<RailNode> ns = new Stack<RailNode>();
							ns.push(an);
							while(ns.isEmpty() == false) {
								RailNode sn = ns.pop();
								Set<String> railEdgeIds = new HashSet<String>();
								railEdgeIds.add(sn.getLeftEdgeId());
								if(StringUtils.isNotEmpty(sn.getRightEdgeId())) {
									railEdgeIds.add(sn.getRightEdgeId());
								}
								for(String ei : railEdgeIds) {
									RailEdge e = this.railEdgeMap.get(ei);
									if(e == null)
										logger.warn("{} is null", ei);
									else if(StringUtils.isEmpty(e.getAreaName())) {
										e.setAreaName(sn.getAreaName());
										e.setAreaId(sn.getAreaId());
										this.setStationAreaName(e);
										RailNode n = this.railNodeMap.get(e.getToNodeId());
										n.setAreaName(sn.getAreaName());
										n.setAreaId(sn.getAreaId());
										ns.push(n);					
									}
								}
							}
						}
						
						if(StringUtils.isEmpty(an.getBayName()) == false) {
							//setAreaName
							
							Stack<RailNode> ns = new Stack<RailNode>();
							ns.push(an);
							while(ns.isEmpty() == false) {
								RailNode sn = ns.pop();
								Set<String> railEdgeIds = new HashSet<String>();
								railEdgeIds.add(sn.getLeftEdgeId());
								if(StringUtils.isNotEmpty(sn.getRightEdgeId())) {
									railEdgeIds.add(sn.getRightEdgeId());
								}
								for(String ei : railEdgeIds) {
									RailEdge e = this.railEdgeMap.get(ei);
									if(e == null)
										logger.warn("{} is null", ei);
									else if(StringUtils.isEmpty(e.getBayName())) {
										e.setBayName(sn.getBayName());
										e.setBayId(sn.getBayId());
										this.setStationBayName(e);
										RailNode n = this.railNodeMap.get(e.getToNodeId());
										n.setBayName(sn.getBayName());
										n.setBayId(sn.getBayId());
										ns.push(n);
									}
								}
							}					
						}
					});
				}).get();
			} catch (InterruptedException e1) {
				logger.error("",e1);
			} catch (ExecutionException e1) {
				logger.error("",e1);
			}
			
				
			
			ConcurrentLinkedQueue<AbstractNode> remainedNodes = new ConcurrentLinkedQueue<AbstractNode>();
			ConcurrentLinkedQueue<AbstractNode> remainedNodesReverse = new ConcurrentLinkedQueue<AbstractNode>();
			
			try {
				tpool.submit(()->{
					stationMap.values().parallelStream().forEach(st ->{
						if(StringUtils.isNotEmpty(st.getAcquireTransferEdgeId())) {
							TransferEdge te = (TransferEdge)this.edgeMap.get(st.getAcquireTransferEdgeId());
							if(te!=null) {
								te.setAreaName(st.getAreaName());
								te.setAreaId(st.getAreaId());
								te.setBayName(st.getBayName());
								te.setBayId(st.getBayId());
								AbstractNode an = this.nodeMap.get(te.getFromNodeId());
								if(an!=null && StringUtils.isEmpty(an.getAreaName())) {
									an.setAreaName(st.getAreaName());
									an.setAreaId(st.getAreaId());
									an.setBayName(st.getBayName());
									an.setBayId(st.getBayId());	
									if(an instanceof StkPortNode || an instanceof CnvPortNode) {
										remainedNodesReverse.add(an);
									}
								}
							}
						}
						if(StringUtils.isNotEmpty(st.getDepositTransferEdgeId())) {
							TransferEdge te = (TransferEdge)this.edgeMap.get(st.getDepositTransferEdgeId());
							if(te!=null) {
								te.setAreaName(st.getAreaName());
								te.setAreaId(st.getAreaId());
								te.setBayName(st.getBayName());
								te.setBayId(st.getBayId());
								AbstractNode an = this.nodeMap.get(te.getToNodeId());
								if(an!=null && StringUtils.isEmpty(an.getAreaName())) {
									an.setAreaName(st.getAreaName());
									an.setAreaId(st.getAreaId());
									an.setBayName(st.getBayName());
									an.setBayId(st.getBayId());
									if(an instanceof StkPortNode || an instanceof CnvPortNode) {
										remainedNodes.add(an);
									}
								}
							}
						}
					});
				}).get();
			} catch (InterruptedException e1) {
				logger.error("",e1);
			} catch (ExecutionException e1) {
				logger.error("",e1);
			}
			
			for(AbstractNode an : remainedNodes) {				
				setRemainedAreaBaySet(an);					
			}
			for(AbstractNode an : remainedNodesReverse) {
				setRemainedAreaBaySetReverse(an);
			}
		}
		
		public void setRemainedAreaBaySet(AbstractNode an) {
			for(String ei : an.getToEdgeIds()) {
				AbstractEdge e = this.edgeMap.get(ei);
				if(e == null)
					logger.warn("{} is null", ei);
				else if(StringUtils.isEmpty(e.getAreaName())) {
					e.setAreaName(an.getAreaName());
					e.setAreaId(an.getAreaId());
					e.setBayName(an.getBayName());
					e.setBayId(an.getBayId());	
					AbstractNode n = this.nodeMap.get(e.getToNodeId());
					if(n == null) {
						logger.warn("{} to Node is null", e.getId());
						continue;
					}else if(StringUtils.isNotEmpty(n.getAreaName())) {
						n.setAreaName(an.getAreaName());
						n.setAreaId(an.getAreaId());
						n.setBayName(an.getBayName());
						n.setBayId(an.getBayId());
						this.setRemainedAreaBaySet(n);
					}
				}
			}
		}
		
		public void setRemainedAreaBaySetReverse(AbstractNode an) {
			for(String ei : an.getFromEdgeIds()) {
				AbstractEdge e = this.edgeMap.get(ei);
				if(e == null)
					logger.warn("{} is null", ei);
				else if(StringUtils.isEmpty(e.getAreaName())) {
					e.setAreaName(an.getAreaName());
					e.setAreaId(an.getAreaId());
					e.setBayName(an.getBayName());
					e.setBayId(an.getBayId());	
					AbstractNode n = this.nodeMap.get(e.getFromNodeId());
					if(n == null) {
						logger.warn("{} from Node is null", e.getId());
						continue;
					}else if(StringUtils.isNotEmpty(n.getAreaName())) {
						n.setAreaName(an.getAreaName());
						n.setAreaId(an.getAreaId());
						n.setBayName(an.getBayName());
						n.setBayId(an.getBayId());
						this.setRemainedAreaBaySetReverse(n);
					}
				}
			}
		}
		
		public void setAreaName(RailNode an) {
			Set<String> railEdgeIds = new HashSet<String>();
			railEdgeIds.add(an.getLeftEdgeId());
			if(StringUtils.isNotEmpty(an.getRightEdgeId())) {
				railEdgeIds.add(an.getRightEdgeId());
			}
			for(String ei : railEdgeIds) {
				RailEdge e = this.railEdgeMap.get(ei);
				if(e == null)
					logger.warn("{} is null", ei);
				else if(StringUtils.isEmpty(e.getAreaName())) {
					e.setAreaName(an.getAreaName());
					e.setAreaId(an.getAreaId());
					this.setStationAreaName(e);
					RailNode n = this.railNodeMap.get(e.getToNodeId());
					n.setAreaName(an.getAreaName());
					n.setAreaId(an.getAreaId());
					this.setAreaName(n);					
				}
			}
		}
		
		public void setBayName(RailNode an) {
			Set<String> railEdgeIds = new HashSet<String>();
			railEdgeIds.add(an.getLeftEdgeId());
			if(StringUtils.isNotEmpty(an.getRightEdgeId())) {
				railEdgeIds.add(an.getRightEdgeId());
			}
			for(String ei : railEdgeIds) {
				RailEdge e = this.railEdgeMap.get(ei);
				if(e == null)
					logger.warn("{} is null", ei);
				else if(StringUtils.isEmpty(e.getBayName())) {
					e.setBayName(an.getBayName());
					e.setBayId(an.getBayId());
					this.setStationBayName(e);
					RailNode n = this.railNodeMap.get(e.getToNodeId());
					n.setBayName(an.getBayName());
					n.setBayId(an.getBayId());
					this.setBayName(n);
				}
			}
		}
		public void setStationAreaName(RailEdge e) {
			RailEdge re = (RailEdge)e;
			for(String stationId : re.getStationIdList()) {
				Station st = stationMap.get(stationId);
				if(st == null) {
					logger.debug("no station exists : " + stationId);						
				}
				else {
					st.setAreaName(re.getAreaName());
					st.setAreaId(re.getAreaId());
				}
			}
		}
		public void setStationBayName(AbstractEdge e) {
			RailEdge re = (RailEdge)e;
			for(String stationId : re.getStationIdList()) {
				Station st = stationMap.get(stationId);
				if(st == null) {
					logger.debug("no station exists : " + stationId);						
				}
				else {
					st.setBayName(re.getBayName());
					st.setBayId(re.getBayId());
				}
			}
		}
	}
	
	private class RecursiveLoopNameSetter{
		private ConcurrentMap<String,RailEdge> railEdgeMap;
		private ConcurrentMap<String,AbstractNode> nodeMap;
		private ConcurrentLinkedQueue<RailEdge> entryRailEdgeList;
		private ForkJoinPool tpool;

		public RecursiveLoopNameSetter(ConcurrentMap<String,RailEdge> railEdgeMap, ConcurrentMap<String,AbstractNode> nodeMap, ConcurrentLinkedQueue<RailEdge> entryRailEdgeList, ForkJoinPool tpool) {
			this.tpool = tpool;
			this.railEdgeMap = railEdgeMap;
			this.nodeMap = nodeMap;
			this.entryRailEdgeList = entryRailEdgeList;
			for(RailEdge re : entryRailEdgeList) {
				setLoopId(nodeMap.get(re.getToNodeId()), re.getLoopId());
			}
					
		}
		public void setLoopId(AbstractNode an, int loopId) {
			for(String ei : an.getToEdgeIds()) {
				RailEdge e = this.railEdgeMap.get(ei);
				if(e != null && e.getLoopId() != loopId) {
					e.setLoopId(loopId);
					setLoopId(nodeMap.get(e.getToNodeId()), loopId);
				}else return;
			}
		}		
	}	
}