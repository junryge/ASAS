package com.skhynix.smartatlas.service;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.MessageFormat;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

import org.dom4j.Document;
import org.dom4j.Element;
import org.dom4j.io.SAXReader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.comm.TibrvAPI;
import com.skhynix.smartatlas.data.Msg;
import com.skhynix.smartatlas.data.Msg.MSG_TYP;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.util.DataService;
import com.tibco.tibrv.Tibrv;
import com.tibco.tibrv.TibrvException;
import com.tibco.tibrv.TibrvListener;
import com.tibco.tibrv.TibrvMsg;
import com.tibco.tibrv.TibrvMsgCallback;
import com.tibco.tibrv.TibrvQueue;
import com.tibco.tibrv.TibrvRvdTransport;
import com.tibco.tibrv.TibrvTransport;

public class TibrvService implements TibrvMsgCallback{
	private final Logger logger = LoggerFactory.getLogger(getClass());
	private static final String CONFIG_PATH_TEMPLATE = "cmessage/cfg/CMESSAGE_{0}_{1}.xml";
	private final int MAX_ENTRIES = 30;
	String service = "";
	String network = "";
	String daemon;
	String subject;
	private MSG_TYP msgTyp = null;
	private final String facId;
	private final String fabId;

	TibrvTransport transport = null;
	TibrvQueue tibrvQueue = null;
	TibrvMsg tibrvMessage;

	private int receivedMessageCount = 0;
	private final LinkedHashMap<String, Integer> receivedMessageCountMap = new LinkedHashMap<>(
			MAX_ENTRIES,
			0.75f,
			true
	){
		private static final long serialVersionUID = 1L;

		@Override
		protected boolean removeEldestEntry(Map.Entry<String, Integer> eldest) {
			return size() > MAX_ENTRIES;
		}
	};
	private boolean initialized	= false;

	// init 1. gid(= groupId/sequence id) 를 통해 service, network 호출
	public TibrvService(
			String fabId,
			String facId,
			String subject,
			String daemon,
			int gid
	) {
		String type = Env.getEnv();
		this.fabId = fabId;
		this.facId = facId;
		this.daemon = daemon;

		this._initSubject(subject);

		this._loadTibrvInfoByGid(facId, type, gid);

		this.init();
	}

	// init 2. service, network 를 직접 입력
	public TibrvService (
			String fabId,
			String facId,
			String daemon,
			String subject,
			String service,
			String network,
			MSG_TYP msgTyp
	) {
		this.fabId		= fabId;
		this.facId		= facId;
		this.daemon 	= daemon;
		this.service	= service;
		this.network	= network;
		this.msgTyp		= msgTyp;

		this._initSubject(subject);

		this.init();
	}

	private void _initSubject(String subject) {
		if (subject != null && !subject.isEmpty()) {
			String type = Env.getEnv();
			String[] splitSubject = subject.split("\\.");

			if (splitSubject.length > 0 && splitSubject[0].equals(facId)) {
				this.subject = subject;
			} else {
				this.subject = MessageFormat.format("{0}.{1}.{2}", facId, type, subject);
			}
		}
	}

	private void _loadTibrvInfoByGid (String facId, String type, int gid) {
		if (gid > -1) {
			logger.info("... Loading tib/rv information by group id (fac: {} / gid: {})", facId, gid);

			Path path = Paths.get(MessageFormat.format(CONFIG_PATH_TEMPLATE, facId, type));

			if (Files.exists(path)) {
				try {
					Document document = new SAXReader().read(path.toFile());
					Element rootElement = document.getRootElement();
					Element matchingElement = _findElementByGid(rootElement, gid);

					if (matchingElement != null) {
						_extractServiceAndNetwork(matchingElement);

						logger.info("... Tib/rv information was loaded successfully (fac: {})", facId);
					}
				} catch (Exception e) {
					logger.error("... An error occurred while reading or parsing xml file (file name: {}) !!!", path.getFileName(), e);
				}
			} else {
				logger.warn("... File does not exist (file name: {}) !", path.getFileName());
			}
		} else {
			logger.warn("... It is invalid group id [required gid>=0] (fac: {} / gid: {}) !", facId, gid);
		}
	}

	private Element _findElementByGid(Element rootElement, int gid) {
		for (Element multicastElement : rootElement.elements()) {
			String seqStr = multicastElement.attributeValue("SEQ");
			int seq = Integer.parseInt(seqStr);

			if (seq == gid) {
				logger.info("... Found matching element (fac: {} / seq: {})", facId, seq);

				return multicastElement;
			}
		}

		return null;
	}

	private void _extractServiceAndNetwork(Element multicastElement) {
		final String ELEMENT_SERVICE = "SERVICE";
		final String ELEMENT_NETWORK = "NETWORK";

		for (Element element : multicastElement.elements()) {
			String name = element.getName();

			switch (name) {
				case ELEMENT_SERVICE: {
					this.service = element.getTextTrim();
				} break;
				case ELEMENT_NETWORK: {
					this.network = element.getTextTrim();
				} break;
			}
		}
	}

	private void _close() {
		try {
			if (tibrvQueue != null && tibrvQueue.isValid()) {
				tibrvQueue.destroy();
			}

			if (transport != null) {
				transport.destroy();
			}

			Tibrv.close();

			logger.info("... Tib/rv was closed (fab: {})", fabId);
		} catch (TibrvException tibrvException) {
			logger.error("... An error occurred while closing TibrvService (fab: {}) !!!", fabId, tibrvException);
		}
	}

	/*
	 * Initialize this listener.
	 */
	public void init() {
		// Create RVD transport
		try {
			TibrvMsg.setStringEncoding("MS949");
			this.tibrvMessage = new TibrvMsg();

			Tibrv.open(Tibrv.IMPL_NATIVE);

			logger.info("Tibrv test connection started ... \n@ service: {}\n@ network: {}\n@ daemon: {}\n@ subject: {}",
					this.service,
					this.network,
					this.daemon,
					this.subject
			);

			transport = new TibrvRvdTransport(this.service, this.network, this.daemon);
			this.tibrvQueue = new TibrvQueue();
			TibrvListener listener = new TibrvListener(this.tibrvQueue, this, transport, this.subject, null);

			this.initialized = true;

			logger.info("... Tib/rv test connection finished and it is initialized (fab: {})", fabId);
		} catch (Exception e) {
			logger.error("... An error occurred while initialize tibrvService (fab: {}) !!!", fabId, e);

			this._close();
		}
	}

	public void startListen() {
		if (!this.initialized) {
			logger.warn("... Tib/rv is not initialized (fac : {}) !", facId);

			return;
		}

		try {
			this._listenHandler();
		} catch (Exception e) {
			logger.error("... An error occurred while starting listen thread of tib/rv (fab: {}) !!!", fabId, e);

			this._close();
		}
	}

	private void _listenHandler() {
		logger.info("The tibrv module has started listening (fab: {}) ...", this.fabId);

		this._countMessageReceivedPer1Minutes();

		new Thread("TibrvThreadPool") {
			public void run(){
				while(true) {
					if (tibrvQueue != null && tibrvQueue.isValid()) {
						try {
							tibrvQueue.dispatch();    // 송신된 메세지를 잡아 내는 곳
						} catch (Exception e) {
							logger.error("... An error occurred while receiving message (fab: {}) !!!", fabId, e);

							throw new RuntimeException(e);
						}
					} else {
						logger.warn("... Tib/rv queue is invalid state (fab: {}) !", fabId);

						break;
					}
				}
			}
		}.start();
	}

	public void sendMessage(String data) throws RuntimeException {
		this.sendMessage(data, this.subject, this.service, this.network, this.daemon);
	}

	public void sendMessage(String data, String suffixSubject) throws RuntimeException {
		this.sendMessage(data, this.subject + "." + suffixSubject, this.service, this.network, this.daemon);
	}

	public void sendMessage(String data, String subject, String service, String network, String daemon) {
		if (!initialized || data.trim().isEmpty()) {
			logger.warn("... tib/rv module is not initialized or message is empty (fab : {} / message: {}) !", fabId, data);
		} else {
			boolean isSucceed = TibrvAPI.send(service, network, daemon, subject, "xmlData", data);
			
			if (!this._insertLogpresso(isSucceed, subject, network, service, daemon, data)) {
				logger.error("... sending tib/rv message was not inserted into logpresso database [fab: {}] !!!", fabId);
			}
		}
	}

	private boolean _insertLogpresso(
			boolean isSucceed,
			String subject,
			String network,
			String service,
			String daemon,
			String data
	) {
		var tuple = new Tuple();

		tuple.put("RESULT", isSucceed ? "SUCCESS" : "FAIL");
		tuple.put("FAB_ID", fabId);
		tuple.put("FAC_ID", facId);
		tuple.put("SUBJECT", subject);
		tuple.put("SERVICE", service);
		tuple.put("NETWORK", network);
		tuple.put("DAEMON", daemon);
		tuple.put("MESSAGE", data);
		tuple.put("ENCODE", new TibrvMsg().getMsgStringEncoding());
		tuple.put("ENV", Env.getEnv());

		return LogpressoAPI.setInsertTuple("ATLAS_TIB_SEND_MSG_LOG", tuple, 20);
	}

	@Override
	public void onMsg(TibrvListener tibrvListener, TibrvMsg tibrvMessage) {
		if (tibrvMessage != null) {
			++receivedMessageCount;
			
	        try {	        	
	        	
	        	Msg data = new Msg(
	        			this.fabId,
	    				this.msgTyp,
	    				System.currentTimeMillis(),
	    				(String)tibrvMessage.getField("xmlData").data
	    		);
	    		DataService.getInstance().queue.add(data);

	    		// 기록용으로 남겨두는 message, 단 monitoringControlBatch 에서 호출 후 해당 데이터 초기화
	    		if ("TRUE".equals(Env.getFabsetProperties().getProperty("CMN.CMN.UDP_MESSAGE_MONITORING"))) {
	    			DataService.getInstance().recordQueue.add(data);
	    		}
    			
	        } catch (TibrvException e) {
	            logger.error(">>> [TibRV Error] Failed to parse received message content.", e);
	        }
		} else {
			logger.warn("... received message is null !");
		}
	}

	private void _countMessageReceivedPer1Minutes() {
		/*
		 * isFirstCheck 값을 통해 첫번째 카운팅 제거
		 * 처음 동작 시간이 h:m:s 인 경우, h:m+1:00 부터 h:m+1:59 까지의 카운팅 범위는 (59 + (59 - s))초
		 */
		final AtomicBoolean isFirstCheck = new AtomicBoolean(false);

		new Thread("TibrvCountMessageReceivedPer1Minutes") {
			public void run(){
				while(true) {
					LocalDateTime now = LocalDateTime.now();
					LocalDateTime startTime = now.withSecond(0).withNano(0);

					if (now.getSecond() > 0) {
						long millisToWait = 60 - now.getSecond();

						try {
							TimeUnit.SECONDS.sleep(millisToWait);

							startTime = startTime.plusMinutes(1);

							TimeUnit.SECONDS.sleep(59);
						} catch (InterruptedException e) {
							logger.error("... An error occurred while waiting for 1 minute (fab: {}) !!!", fabId, e);
						}
					}

					if (isFirstCheck.get()) {
						DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");
						String timeKey = startTime.format(formatter);

						receivedMessageCountMap.put(timeKey, receivedMessageCount);

						logger.info("[{}] tib/rv messages count received: {} [data size: {}]",
								timeKey,
								receivedMessageCount,
								receivedMessageCountMap.size()
						);
					} else {
						isFirstCheck.set(true);

					}

					receivedMessageCount = 0;
				}
			}
		}.start();
	}

	public String getService () {
		return service;
	}

	public String getNetwork () {
		return network;
	}

	public String getDaemon () {
		return daemon;
	}

	public String getSubject () {
		return subject;
	}

	public Integer getMessageCount(String key) {
		return receivedMessageCountMap.getOrDefault(key, -1);
	}

	/**
	 * {@link com.skhynix.smartatlas.environment.type.FunctionItem.FunctionType}
	 */
	public static class SEND_SUB_SUBJECT{
		public static final String ALARM = "ALARM";
		public static final String INIT = "INIT";
		// 	↓↓↓ error 알림 ↓↓↓
		public static final String HID_OFF = "HIDOFF";
		public static final String VHL_OFF = "VHLOFF";
		public static final String RAIL_CUT = "RAILCUT";
		public static final String RAIL_VIBRATION = "VIBRATION";
		public static final String VHL_AVG_SPEED = "VHLSPEED";
		public static final String VHL_CNT = "VHLBEING";
		public static final String CNV_INOUT = "CNV_INOUT";
	}

	public String getFabId() {
		return fabId;
	}

	public String getFacId() {
		return facId;
	}
}