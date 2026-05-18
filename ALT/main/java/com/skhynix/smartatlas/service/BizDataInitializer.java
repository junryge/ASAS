package com.skhynix.smartatlas.service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.data.FabProperties;
import com.skhynix.smartatlas.data.McpProperties;
import com.skhynix.smartatlas.data.Msg;
import com.skhynix.smartatlas.data.TibrvSendMsg;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.listener.AgvUdpListener;
import com.skhynix.smartatlas.listener.CnvSocketIOListener;
import com.skhynix.smartatlas.listener.OhtUdpListener;
import com.skhynix.smartatlas.process.AmpMsgWorkerRunnable;
import com.skhynix.smartatlas.process.CnvMsgWorkerRunnable;
import com.skhynix.smartatlas.process.OhtMsgWorkerRunnable;
import com.skhynix.smartatlas.process.OhtMsgWorkerRunnable.OHT_TIB_STATE;
import com.skhynix.smartatlas.process.UiMsgWorkerRunnable;
import com.skhynix.smartatlas.service.TibrvService.SEND_SUB_SUBJECT;
import com.skhynix.smartatlas.util.AleadyClosedException;
import com.skhynix.smartatlas.util.DataService;
import com.skhynix.smartatlas.util.LayoutUtil;
import com.skhynix.smartatlas.util.ThreadPool;

import net.jodah.expiringmap.ExpirationPolicy;
import net.jodah.expiringmap.ExpiringMap;

public class BizDataInitializer {
	private final Logger logger = LoggerFactory.getLogger(getClass());
	private static long ohtSeq = 0;
	//static private final AtomicInteger ohtSeq = new AtomicInteger(0);

	public void initialization() {
		logger.info("######################## <SmartATLAS> initialization has started ########################");

		long timer = System.currentTimeMillis();
		Properties properties = Env.getFabsetProperties();
		
		DataService.getInstance().initialization(properties);

		ConcurrentMap<String, FabProperties> fabPropertiesMap = DataService.getInstance().getFabPropertiesMap();

		if (fabPropertiesMap.isEmpty()) {
			logger.error("... (3) factory property is empty. then building the listening message is skipped");
		} else {
			this.addStartFab(fabPropertiesMap);

			if (!fabPropertiesMap.isEmpty()) {
				for (String fabId : fabPropertiesMap.keySet()) {
					this._init(fabId);
				}
			}

			this._startWorker();
		}

		logger.info("######################## <SmartATLAS> initialization has finished ######################## [elapsed time: {}ms]", System.currentTimeMillis() - timer);
	}



	public void addStartFab(ConcurrentMap<String, FabProperties> fabPropertiesMap) {
		ConcurrentHashMap<String, OhtUdpListener> ohtUdpListenerMap;
		ConcurrentHashMap<String, AgvUdpListener> agvUdpListenerMap;
		
		ohtUdpListenerMap = this._createOhtUdpListener(fabPropertiesMap);

		DataService.getInstance().setOhtUdpListenerMap(ohtUdpListenerMap);

		this._startListening(fabPropertiesMap, ohtUdpListenerMap);
	}

	// #1 listener 구성
	private ConcurrentHashMap<String, OhtUdpListener> _createOhtUdpListener
	(ConcurrentMap<String, FabProperties> fabPropertiesMap) {
		HashMap<String, OhtUdpListener> portOhtUdpListenerMap = new HashMap<>();
		ConcurrentHashMap<String, OhtUdpListener> fabOhtUdpListenerMap = new ConcurrentHashMap<>();

		for (FabProperties fabProperties : fabPropertiesMap.values()) {
			for (String mcpName : fabProperties.getMcpPropertiesMap().keySet()) {
				McpProperties mcpPropertiesMap = fabProperties.getMcpPropertiesMap().get(mcpName);
				String ip = mcpPropertiesMap.getIp();
				int port = mcpPropertiesMap.getPort();
				String fabId = fabProperties.getFabId();
				String key = fabId + "." + mcpName;

				if (mcpPropertiesMap.getIp().contains(",")) {
					if (!portOhtUdpListenerMap.containsKey(String.valueOf(port))) {
						OhtUdpListener ohtUdpListener = new OhtUdpListener(fabId, mcpName, ip, port);

						fabOhtUdpListenerMap.put(key, ohtUdpListener);

						portOhtUdpListenerMap.put(String.valueOf(port), ohtUdpListener);
					} else {
						OhtUdpListener ohtUdpListener = portOhtUdpListenerMap.get(String.valueOf(port));

						ohtUdpListener.addListenMcpIp(fabId, mcpName, ip);
					}
				} else {
					OhtUdpListener ohtUdpListener = new OhtUdpListener(fabId, mcpName, port);

					fabOhtUdpListenerMap.put(key, ohtUdpListener);
				}

				logger.info("... Oht's listener has been created (fab: {})", fabId);
			}
		}

		return fabOhtUdpListenerMap;
	}
		
	// #2 listener 동작
	private void _startListening(
			ConcurrentMap<String, FabProperties> fabPropertiesMap,
			ConcurrentHashMap<String, OhtUdpListener> fabOhtUdpListenerMap
	) {
		for (String fabId : fabPropertiesMap.keySet()) {
			Set<String> mcpNames = fabPropertiesMap.get(fabId).getMcpPropertiesMap().keySet();

			// oht
			for (String mcpName : mcpNames) {
				logger.info("... Oht's listener(udp) has started listening (fab: {})", fabId);

				String key = String.format("%s.%s", fabId, mcpName);

				if (fabOhtUdpListenerMap.containsKey(key)) fabOhtUdpListenerMap.get(key).start();
			}	
			
			// cnv
			for(Map.Entry<String, CnvSocketIOListener> entry : fabPropertiesMap.get(fabId).getCnvSocketIOListenerMap().entrySet()) {
				logger.info("... Conveyor's listener has started listening (fab: {})", entry.getKey());
				entry.getValue().listenStart();
			}
		}		
	}

	// #3 worker(runnable) 동작 → 시스템 종료 전까지 계속 동작
	private void _startWorker() {
		ExpiringMap.Builder<Object, Object> builder = ExpiringMap.builder();
		Map<String, Integer> messageCache = builder.build();

        builder.maxSize(1000);
		builder.expirationPolicy(ExpirationPolicy.CREATED);
		builder.expiration(1000, TimeUnit.MILLISECONDS);

		new Thread("Msg Dispatcher") {
			public void run() {
				var threadPool = new ThreadPool("WorkerRunnableQueue", Env.getUdpQThreadPoolSize());
				
				logger.info("######################## Running Message Worker ######################");
				
				while (true) {
					if (!DataService.getInstance().isDataServiceRunning()) continue;
					
					// → Msg(fabId, type, receivedTime(millisecond 단위), mcpName, message)
                    Msg messageQueue = null;

					try {
                        messageQueue = DataService.getInstance().queue.take();
                    } catch (InterruptedException e) {
                        logger.error("", e);
                    }

					if (messageQueue == null) continue;

                    switch (messageQueue.getType()) {
            		case OHT:
                		String messageCacheKey = messageQueue.getFabId() + messageQueue.getMcpName() + messageQueue.getMessage();

						if (messageCache.get(messageCacheKey) == null) {
							messageCache.put(messageCacheKey, 1);

							String fabId = messageQueue.getFabId();
							String message = messageQueue.getMessage();
							long receivedMilli = messageQueue.getReceivedMilli();
							long msgSeq = ohtSeq++;
							String mcpName = messageQueue.getMcpName();

                            try {
                            	threadPool.execute(new OhtMsgWorkerRunnable(fabId, message, mcpName, receivedMilli, msgSeq));
                            } catch (AleadyClosedException e) {
                                logger.error("", e);
                            }
                        }
						break;
            		case CNV:
            			try {
							threadPool.execute(new CnvMsgWorkerRunnable(messageQueue.getFabId(), messageQueue.getMcpName(), messageQueue.getMessage(), messageQueue.getReceivedMilli()));
                        } catch (AleadyClosedException e) {
                            logger.error("", e);
                        }
            			break;
            		case AMP:
						try {
							threadPool.execute(new AmpMsgWorkerRunnable(messageQueue));
                        } catch (AleadyClosedException e) {
                            logger.error("", e);
                        }
						break;
            		case UI:
						try {
							threadPool.execute(new UiMsgWorkerRunnable(messageQueue.getFabId(), messageQueue.getMessage()));
                        } catch (AleadyClosedException e) {
                            logger.error("", e);
                        }
						break;
					default:
						break;
                    }
				}
			}
		}.start();
	}

	private void _init(String fabId) {
		FabProperties fabProperties = DataService.getInstance().getFabPropertiesMap().get(fabId);
		String facId = fabProperties.getFacId();

		for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:").keySet()) {
			Map<String, String> dataMap = LayoutUtil.buildLayoutMessageDataMap(
					SEND_SUB_SUBJECT.INIT,
					fabId,
					SEND_SUB_SUBJECT.INIT,
					OHT_TIB_STATE.NORMAL,
					null,
					null,
					null,
					null,
					facId,
					null,
					null,
					false
			);
			Map<String, Object> convertedData = new HashMap<>(dataMap);
			TibrvSendMsg tibrvSendMsg = new TibrvSendMsg(tibrvKey, SEND_SUB_SUBJECT.INIT, convertedData);

			DataService.getInstance().addTibrvMessageQueue(tibrvSendMsg);
		}
	}
}