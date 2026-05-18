package com.skhynix.smartatlas.process;

import java.io.ByteArrayInputStream;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

import org.apache.commons.lang3.StringUtils;
import org.apache.logging.log4j.util.Strings;
import org.dom4j.Document;
import org.dom4j.Node;
import org.dom4j.io.SAXReader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.data.Carrier;
import com.skhynix.smartatlas.data.Command;
import com.skhynix.smartatlas.data.DataSet;
import com.skhynix.smartatlas.data.Job;
import com.skhynix.smartatlas.data.Msg.MSG_TYP;
import com.skhynix.smartatlas.data.TibrvSendMsg.SEND_MSG_FORMAT;
import com.skhynix.smartatlas.data.eq.Eqp;
import com.skhynix.smartatlas.data.eq.StbGroup;
import com.skhynix.smartatlas.data.eq.Stocker;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.map.AbstractNode;
import com.skhynix.smartatlas.map.CarrierContainable;
import com.skhynix.smartatlas.map.CarrierTransportable;
import com.skhynix.smartatlas.map.node.CnvPortNode;
import com.skhynix.smartatlas.map.node.CnvPortNode.CNV_NODE_TYPE;
import com.skhynix.smartatlas.map.node.EqpPortNode;
import com.skhynix.smartatlas.map.node.StkPortNode;
import com.skhynix.smartatlas.map.node.StkPortNode.STK_PORT_INOUT_TYPE;
import com.skhynix.smartatlas.map.node.StkPortNode.STK_SUB_PORT_TYPE;
import com.skhynix.smartatlas.map.node.StkShelfNode;
import com.skhynix.smartatlas.util.DataService;


public class UiMsgWorkerRunnable implements Runnable {
	static private final Logger logger = LoggerFactory.getLogger(UiMsgWorkerRunnable.class);

    String msg = null;
    String fabId = "";

	public UiMsgWorkerRunnable(String fabId, String msg) {
		this.msg = msg;
		this.fabId = fabId;
	}
	
	@Override
	public String toString() {
		return String.format("%s %s %s", getClass(), fabId, msg);
	}

	@Override
	public void run() {
		processMsg();
	}


	public void processMsg() { // Job을 생성 및 완료시 History 이동.
	    try {
    		
    		//logger.info(msg);
    		
    		SAXReader reader = new SAXReader();
			Document doc = reader.read(new ByteArrayInputStream(msg.getBytes("utf-8")));
			Node msgNameNode = doc.selectSingleNode("//MESSAGENAME");
			Node dataNode = null;//
			
			String msgName = msgNameNode.getStringValue();

			switch(msgName){
				case "UI-UNIT-PORT" :	// 목적지 경로 예측 수행.
				case "UI-UNIT-SHELF" :
				{
					dataNode = doc.selectSingleNode("//DATA");
					String unitName = dataNode.selectSingleNode("//UNITNAME").getStringValue();					
					String stateStr = dataNode.selectSingleNode("//STATE").getStringValue();
					String occupiedStr = dataNode.selectSingleNode("//OCCUPIED").getStringValue();
					//String reservedStr = dataNode.selectSingleNode("//RESERVED").getStringValue();
					String bannedStr = dataNode.selectSingleNode("//BANNED").getStringValue();
					//String transportUnitAccessibleStr = dataNode.selectSingleNode("//TRANSPORTUNITACCESSIBLE").getStringValue();
					//String accessModeStr = dataNode.selectSingleNode("//ACCESSMODE").getStringValue();
					if(unitName.matches(".AFC.*_OP")) {
						unitName = unitName.replace("_OP", "");
					}
					AbstractNode an = DataService.getDataSet().getNodePortMap().get(unitName);
					if(an!=null && "F".equals(occupiedStr) && an instanceof EqpPortNode ) {
						if(an instanceof CarrierContainable) {
							CarrierContainable cc = (CarrierContainable) an;
							for(String carrierId : cc.getCarrierIds()) {								
								cc.removeCarrierId(carrierId);
							}
						}
					}
					boolean isAvailable = "INSERVICE".equals(stateStr) &&"F".equals(bannedStr);
					
					sendPortReservedInfo(an, isAvailable);
				}
				break;				
				case "UI-MACHINE" :
				{
					String machineName = doc.selectSingleNode("//MACHINENAME").getStringValue();
					dataNode = doc.selectSingleNode("//DATA");
					String stateStr = dataNode.selectSingleNode("//STATE").getStringValue();
					String connStateStr = dataNode.selectSingleNode("//CONNECTIONSTATE").getStringValue();
					String ctrlStateStr = dataNode.selectSingleNode("//CONTROLSTATE").getStringValue();
					Eqp eqp = DataService.getDataSet().getAllEqpNameMap().get(machineName);
					if(eqp != null) {
						boolean isAvailable = "INSERVICE".equals(stateStr) && "ONLINEREMOTE".equals(ctrlStateStr) && "CONNECTED".equals(connStateStr);
						eqp.setAvailable(isAvailable);
						final String eqpId = eqp.getId();
						final Map<String, String> mapProperties = new HashMap<String,String>();
						mapProperties.put("eqpId", eqpId);
						mapProperties.put("isAvailable", String.valueOf(eqp.isAvailable()));
						final Set<String> mcpNameSet = eqp.getMcpNameSet(DataService.getDataSet());
						mapProperties.put("mcpName", mcpNameSet == null || mcpNameSet.isEmpty() ? "" : mcpNameSet.iterator().next());
						if(eqp.getConnectedFabMcpSet() != null) {
							for(String fabMcpName : eqp.getConnectedFabMcpSet()) {
								String [] names = fabMcpName.split(":");
								if(names.length > 1)
									//AtlasCommPubUI.getInstance().publish("UpdateEqp", mapProperties, DataService.getInstance().getSite(), names[0], names[1]);
									_addTibSenderWaiting("UpdateEqp", mapProperties, Env.getSite(), names[0], names[1]);
								else
									logger.warn("UI-MACHINE {} need to check connectedMcpName : {}", eqpId, fabMcpName);
							}
						}
					}
				}
				break;
				case "UI-MACHINE-STORAGE-CAPACITY" :
				{
					String machineName = doc.selectSingleNode("//MACHINENAME").getStringValue();
					dataNode = doc.selectSingleNode("//DATA");
					String stateStr = dataNode.selectSingleNode("//STATE").getStringValue();
					String connStateStr = dataNode.selectSingleNode("//CONNECTIONSTATE").getStringValue();
					String ctrlStateStr = dataNode.selectSingleNode("//CONTROLSTATE").getStringValue();
//					String tscStateStr = dataNode.selectSingleNode("//TSCSTATE").getStringValue();
					String fullStateStr = dataNode.selectSingleNode("//FULLUP").getStringValue();
					String maxCapaCntStr = dataNode.selectSingleNode("//MAXCAPACITY").getStringValue();
					String occupancyCntStr = dataNode.selectSingleNode("//CURRENTCAPACITY").getStringValue();
					
					Eqp eqp = DataService.getDataSet().getAllEqpNameMap().get(machineName);
					if(eqp != null) {					
						boolean isAvailable = "INSERVICE".equals(stateStr) && "ONLINEREMOTE".equals(ctrlStateStr) && "CONNECTED".equals(connStateStr);
						eqp.setAvailable(isAvailable);
						if(eqp instanceof StbGroup) {
							StbGroup stg = (StbGroup) eqp;
							int maxCapaCnt = Integer.parseInt(maxCapaCntStr);
							if(stg.getMaxCapaCnt() != maxCapaCnt)
								stg.setMaxCapaCnt(maxCapaCnt);
							int occupancyCnt = Integer.parseInt(occupancyCntStr);
							if(stg.getOccupancyCnt(DataService.getDataSet()) != occupancyCnt) {
								stg.setOccupancyCnt(occupancyCnt);
							}
							boolean isFull = "T".equals(fullStateStr);
							if(stg.isFull() != isFull) {
								stg.setFull(isFull);
							}
							
							final String stbGroupId = stg.getId();
							final Map<String, String> mapProperties = new HashMap<String,String>();
							mapProperties.put("stbGroupId", stbGroupId);
							mapProperties.put("isAvailable", String.valueOf(stg.isAvailable()));
							mapProperties.put("isFull", String.valueOf(isFull));
							mapProperties.put("isN2", String.valueOf(stg.isN2()));
							mapProperties.put("occupancyCnt", String.valueOf(occupancyCnt));
							mapProperties.put("maxCapaCnt", String.valueOf(maxCapaCnt));
							final Set<String> mcpNameSet = stg.getMcpNameSet(DataService.getDataSet());
							mapProperties.put("mcpName", mcpNameSet == null || mcpNameSet.isEmpty() ? "" : mcpNameSet.iterator().next());
							
							if(stg.getConnectedFabMcpSet() != null) {
								for(String fabMcpName : stg.getConnectedFabMcpSet()){
									String[] names = fabMcpName.split(":");
									if(StringUtils.isNotEmpty(fabMcpName) && names.length > 1){
										//AtlasCommPubUI.getInstance().publish("UpdateStbGroup", mapProperties, DataService.getInstance().getSite(), names[0], names[1]);
										_addTibSenderWaiting("UpdateStbGroup", mapProperties, Env.getSite(), names[0], names[1]);
									}
								}
							}
							
							mapProperties.put("createTime", String.valueOf(System.currentTimeMillis()));
							mapProperties.put("dataType", "stbGroup");
							sendUdp(mapProperties);
						}else if(eqp instanceof Stocker) {
							Stocker stk = (Stocker) eqp;
							int maxCapaCnt = Integer.parseInt(maxCapaCntStr);
							if(stk.getMaxCapaCnt() != maxCapaCnt)
								stk.setMaxCapaCnt(maxCapaCnt);
							int occupancyCnt = Integer.parseInt(occupancyCntStr);
							if(stk.getOccupancyCnt(DataService.getDataSet()) != occupancyCnt) {
								stk.setOccupancyCnt(occupancyCnt);
							}
							boolean isFull = "T".equals(fullStateStr);
							if(stk.isFull() != isFull) {
								stk.setFull(isFull);
							}
							
							final String stockerId = stk.getId();
							final Map<String, String> mapProperties = new HashMap<String,String>();
							mapProperties.put("stockerId", stockerId);
							mapProperties.put("isAvailable", String.valueOf(stk.isAvailable()));
							mapProperties.put("isFull", String.valueOf(isFull));
							mapProperties.put("isN2", String.valueOf(stk.isN2()));
							mapProperties.put("occupancyCnt", String.valueOf(occupancyCnt));
							mapProperties.put("maxCapaCnt", String.valueOf(maxCapaCnt));
							final Set<String> mcpNameSet = stk.getMcpNameSet(DataService.getDataSet());
							mapProperties.put("mcpName", mcpNameSet == null || mcpNameSet.isEmpty() ? "" : mcpNameSet.iterator().next());
							
							if(stk.getConnectedFabMcpSet() != null) {
								for(String fabMcpName : eqp.getConnectedFabMcpSet()){
									String[] names = fabMcpName.split(":");
									if(StringUtils.isNotEmpty(fabMcpName) && names.length > 1){
										//AtlasCommPubUI.getInstance().publish("UpdateStocker", mapProperties, DataService.getInstance().getSite(), names[0], names[1]);
										_addTibSenderWaiting("UpdateStocker", mapProperties, Env.getSite(), names[0], names[1]);
									}
								}								
							}
							mapProperties.put("createTime", String.valueOf(System.currentTimeMillis()));
							mapProperties.put("dataType", "stocker");
							sendUdp(mapProperties);
						}
						else if (eqp instanceof Eqp) {
							final String eqpId = eqp.getId();
							final Map<String, String> mapProperties = new HashMap<String,String>();
							mapProperties.put("eqpId", eqpId);
							mapProperties.put("isAvailable", String.valueOf(eqp.isAvailable()));
							final Set<String> mcpNameSet = eqp.getMcpNameSet(DataService.getDataSet());
							mapProperties.put("mcpName", mcpNameSet == null || mcpNameSet.isEmpty() ? "" : mcpNameSet.iterator().next());
							if(eqp.getConnectedFabMcpSet() != null) {
								for(String fabMcpName : eqp.getConnectedFabMcpSet()){
									String[] names = fabMcpName.split(":");
									if(StringUtils.isNotEmpty(fabMcpName) && names.length > 1){
										//AtlasCommPubUI.getInstance().publish("UpdateEqp", mapProperties, DataService.getInstance().getSite(), names[0], names[1]);
										_addTibSenderWaiting("UpdateEqp", mapProperties, Env.getSite(), names[0], names[1]);
									}
								}								
							}							
						}
					}
				}							
				break;
				case "COMMON-CARRIERTRANSPORT-AWAKE" :	// Awake 발생시 경로 재예측 수행.
				case "COMMON-AWAKE" :
				{
					String carrierName = doc.selectSingleNode("//CARRIERNAME").getStringValue();
					String carrierId = DataSet.CARRIER_PREFIX+":"+carrierName;
					Carrier ca = DataService.getDataSet().getCarrierMap().get(carrierId);
					if(ca!=null) {
						String jobId = ca.getJobId();
						if(StringUtils.isNotEmpty(jobId)) {
							Job job = DataService.getDataSet().getJobMap().get(jobId);
							if(job!=null) {
								job.setWakeupTime(System.currentTimeMillis());
								
//								JsonObject jo = new JsonObject();
								
								String carrierEqpId = ca.getEqpId();
								String carrierContainerId = job.getNewFromContainerId();
								if(StringUtils.isNotEmpty(carrierEqpId)) {
									Eqp carrierEqp = DataService.getDataSet().getAllEqpMap().get(carrierEqpId);
									String carrierLocId = ca.getLocId();
									if(carrierEqp != null && StringUtils.isNotEmpty(carrierLocId) ) {
										CarrierContainable cc = DataService.getDataSet().getCarrierContainableByCarrierLoc(carrierLocId, carrierEqp.getFabId());
										carrierContainerId = cc.getId();
									}
								}
								
								//RoutePredictor.newRouteReq(jobId, carrierId, carrierContainerId, StringUtils.isNotEmpty(job.getToNodeId())?job.getToNodeId():job.getTmpToNodeId());
//								String tnId = StringUtils.isNotEmpty(job.getToNodeId())?job.getToNodeId():job.getTmpToNodeId();
//								int toNodeIdHistorySize = job.getToNodeIdHistory().size();
//								// 목적지 장비명이 변경되지 않는 한 최초 출발지 부터 목적지까지의 초기 예측 경로를 보관한다.
//								if(toNodeIdHistorySize > 1 && job.getToNodeIdHistory().toArray(new String[toNodeIdHistorySize])[toNodeIdHistorySize-2].contains(tnId)) { // 목적지							
//									RoutePredictor.newRouteReq(jobId, carrierId, carrierContainerId, tnId, false); // orgRoutePrediction 갱신 불필요.   
//								}else
//								{							
//									RoutePredictor.newRouteReq(jobId, carrierId, carrierContainerId, tnId, true); // orgRoutePrediction 갱신 필요.
//								}
							}
						}
					}					
				}
				break;
			}//switch
    	}catch(Exception e) {    		
    		logger.error("No DATA",e);
    	}
    }
	
	static private void sendUdp(Map<String,String> map) {
//		Gson gson = new Gson();
//		DatagramSocket udpSocket = null;
//		
//		try {
//			String jsonStr = gson.toJson(map);
//			byte [] sendBuff = jsonStr.getBytes();
//
//			udpSocket = new DatagramSocket();
//			udpSocket.send(new DatagramPacket(sendBuff, sendBuff.length, Env.getLogpressoUdpHostAsInetAddr(), Env.getLogpressoUdpPort()));
//			
//			if(Env.getLogpressoUdpHostAsInetAddr2() != null) {
//				udpSocket.send(new DatagramPacket(sendBuff, sendBuff.length, Env.getLogpressoUdpHostAsInetAddr2(), Env.getLogpressoUdpPort()));	
//			}				
//		} catch(Exception e) {
//			logger.error(e.getMessage());
//		} finally {
//			if (udpSocket != null) udpSocket.close();
//		}
	}
	
	static public void sendPortReservedInfo(AbstractNode an, boolean isAvailable) {
		
		if(an != null) {
			if(	an.isAvailable() != isAvailable ) {
				logger.debug("{} isAvaiable {} -> {}", an.getId(), an.isAvailable(), isAvailable);
				an.setAvailable(isAvailable);
			}
			
			if (an instanceof CarrierContainable && an instanceof CarrierTransportable == false && an instanceof StkShelfNode == false) {
				// Stocker Shelf는 안보일거니깐 처리 제외
				final String portId = an.getId();
				Set<String> portIds = new HashSet<>();
				final String [] carrierIds = ((CarrierContainable) an).getCarrierIds();
				final boolean isOccupied = carrierIds != null && 0 < carrierIds.length;
				String nextReservedJob = "";
				final Map<String, String> mapProperties = new HashMap<String,String>();
				boolean isStkAutoIn = false, isStkAutoOut = false;
				portIds.add(portId);
				if(an instanceof StkPortNode) {
					StkPortNode spn = (StkPortNode) an;
					if(spn.isTeConnection()) {
						isStkAutoIn = spn.getInOutType() == STK_PORT_INOUT_TYPE.IN;
						isStkAutoOut = spn.getInOutType() == STK_PORT_INOUT_TYPE.OUT;
					}					
					for(StkPortNode.SubPort sp : spn.getSubPortList()) { // LP Port들 상태를 모두 보내도록
						if(sp.type == STK_SUB_PORT_TYPE.LP) {
							String subId = spn.getName().equals(sp.name)? spn.getId() : sp.name;
							portIds.add(subId);
						}
					}
				}else if(an instanceof CnvPortNode) {
					CnvPortNode cpn = (CnvPortNode) an;
					if(cpn.isTeConnection()) {
						isStkAutoIn = cpn.getType() == CNV_NODE_TYPE.INPUT;
						isStkAutoOut = cpn.getType() == CNV_NODE_TYPE.OUTPUT;
					}					
//					for(StkPortNode.SubPort sp : spn.getSubPortList()) { // LP Port들 상태를 모두 보내도록
//						if(sp.type == STK_SUB_PORT_TYPE.LP) {
//							String subId = spn.getName().equals(sp.name)? spn.getId() : sp.name;
//							portIds.add(subId);
//						}
//					}
				}
				if (isOccupied && isStkAutoIn == false) { // StkAutoIn인 경우 진입할 Job목록만 보이도록
					for(String carrierId : carrierIds) {
						final Carrier carrier = DataService.getDataSet().getCarrierMap().get(carrierId);
						if(carrier == null) {
							logger.error("carrierId : {} (on {}) is null. check please~", carrierId, portId);
						}else {
							final String jobId = carrier.getJobId();
							if (!Strings.isEmpty(jobId)) {
								if (!nextReservedJob.isEmpty())
									nextReservedJob += ',';
								nextReservedJob += jobId;
							}							
						}
					}
				}
				Set<String> reservedJobIdSet = ConcurrentHashMap.newKeySet();
				if(isStkAutoOut == false) { // Stocker Auto  Out인 경우 진출 예정인 Job목록만 보이도록.
					for(Job job : DataService.getDataSet().getJobMap().values()) {
						if (portId.equals(job.getToNodeId()))
							reservedJobIdSet.add(job.getId());
						
						final String jobCarrierId = job.getCarrierId();
						if (isOccupied) {
							for(String carrierId : carrierIds) {
								// Already arrived.
								if (carrierId.equals(jobCarrierId)) {
									reservedJobIdSet.remove(job.getId());
									break;
								}
							}
						}
					}
					for(Command cmd : DataService.getDataSet().getCommandMap().values()) {
						if(cmd.isInserted()==false && portId.equals(cmd.getDestNodeId()) && cmd.getCmpltTime() <=0 
								&& StringUtils.isNotEmpty(cmd.getTransEqpId()) 
								&& cmd.getTransEqpId().contains(":STK:") == false 
								&& cmd.getTransEqpId().contains(":CNV:") == false) {
							reservedJobIdSet.add(cmd.getJobId());
							final String cmdCarrierId = cmd.getCarrierId();
							if (isOccupied) {
								for(String carrierId : carrierIds)
									// Already arrived.
									if (carrierId.equals(cmdCarrierId)) {
										reservedJobIdSet.remove(cmd.getJobId());									
										break;
									}
							}
						}
					}
				}
				final String mcpName = an.getMcpName(DataService.getDataSet());			
				
				mapProperties.put("portId", String.join(",",portIds));
				mapProperties.put("isAvailable", String.valueOf(isAvailable));
				mapProperties.put("isOccupied", String.valueOf(isOccupied));
				mapProperties.put("nextReservedJob", nextReservedJob);
				mapProperties.put("carrierIds", isOccupied ? String.join(",", carrierIds) : "null");				
				mapProperties.put("reservedJob", String.join(",", reservedJobIdSet));				
				mapProperties.put("mcpName", mcpName);
				if(StringUtils.isNotEmpty(mcpName))
					_addTibSenderWaiting("UpdatePort", mapProperties, Env.getSite(), an.getFabId(), mcpName);
					//AtlasCommPubUI.getInstance().publish("UpdatePort", mapProperties, DataService.getInstance().getSite(), an.getFabId(), mcpName);
					
				
//				mapProperties.put("createTime", String.valueOf(System.currentTimeMillis()));
//				mapProperties.put("dataType", "abstractNode");
//				mapProperties.put("fabId", an.getFabId());
//				mapProperties.put("eqpId", an.getEqpId());
//				mapProperties.put("eqpName", an.getName());
//				mapProperties.put("areaName", an.getAreaName());
//				mapProperties.put("bayName", an.getBayName());
//				mapProperties.put("carrierId", occupiedCarrierId);
//				sendUdp(mapProperties);
			}
		}
	}
	
	static private void _addTibSenderWaiting(String actionType, Map<String, String> dataMap, String site, String fabId, String mcpName) {
		String type = MSG_TYP.UI.toString() + "." + actionType;
		
		dataMap.put("fabId", fabId);
		dataMap.put("mcpName", mcpName);
		for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:amos").keySet()) {			
  			DataService.getInstance().addTibrvMessageQueue(
  					tibrvKey,
  					type,
  					SEND_MSG_FORMAT.JSON,
  					dataMap
  			);
  		}
	}
}
