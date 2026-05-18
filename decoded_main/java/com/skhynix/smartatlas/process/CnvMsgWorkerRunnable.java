package com.skhynix.smartatlas.process;

import java.util.AbstractMap;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.locks.ReentrantLock;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.comm.TibrvAPI;
import com.skhynix.smartatlas.data.Carrier;
import com.skhynix.smartatlas.data.Carrier.CARRIER_STATE;
import com.skhynix.smartatlas.data.CnvTask;
import com.skhynix.smartatlas.data.Command;
import com.skhynix.smartatlas.data.Command.CMD_STATE;
import com.skhynix.smartatlas.data.DataSet;
import com.skhynix.smartatlas.data.FabProperties;
import com.skhynix.smartatlas.data.Job;
import com.skhynix.smartatlas.data.RouteItem;
import com.skhynix.smartatlas.data.RouteItem.ROUTE_ITEM_DET_TYPE;
import com.skhynix.smartatlas.data.RouteItem.ROUTE_ITEM_TYPE;
import com.skhynix.smartatlas.data.eq.Conveyor;
import com.skhynix.smartatlas.data.eq.Conveyor.CNV_EVENT;
import com.skhynix.smartatlas.data.eq.Eqp;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.environment.type.FunctionItem;
import com.skhynix.smartatlas.environment.type.FunctionItem.FunctionType;
import com.skhynix.smartatlas.map.edge.CnvEdge;
import com.skhynix.smartatlas.map.edge.LongEdge;
import com.skhynix.smartatlas.map.node.CnvPortNode;
import com.skhynix.smartatlas.navi.DijkstraCnvFromToPath;
import com.skhynix.smartatlas.util.DataService;

/**
 * A class to process a job related with a conveyor.
 * @author 
 *
 */
public class CnvMsgWorkerRunnable implements Runnable {
	static private final Logger logger = LoggerFactory.getLogger(CnvMsgWorkerRunnable.class);
	private long msgSeq = -1;
	private String msg = null;
	private String fabId = "";
	private String cnvId = "";
	private Conveyor cnv = null;
    private JsonObject jo = null;
    private long receivedMilli = -1;
    private String eqpId = "";
    private String daemon = "";
    private String subject= "";
    
    /**
     * A constructor
     * @param fabId
     * @param cnvId
     * @param msg
     */
	public CnvMsgWorkerRunnable(String fabId, String eqpId, String msg, long receivedMilli) {
		Eqp eqp = DataService.getDataSet().getAllEqpNameMap().get(eqpId);
		this.msg = msg;
		this.receivedMilli = receivedMilli;
		this.cnv = (eqp instanceof Conveyor) ? (Conveyor)eqp : null;
		this.cnvId = cnv == null ? "" : cnv.getId();		
		this.msgSeq = cnv == null ? 0L : cnv.getMsgSeqAndIncrement();
		this.fabId = fabId;
		this.eqpId = eqpId;
		
		try {
			logger.debug("CnvMsgWorkerRunnable >>>>> cnvId:{}, msgSeq:{}, fabId:{}, eqpId:{}, cnv:{}, message:{}", cnvId, msgSeq, fabId, eqpId, cnv==null ? "null":"ok", msg);
			
			daemon 	= DataService.getInstance().getFabPropertiesMap().get(fabId).getConveyorDaemon();
		    subject = DataService.getInstance().getFabPropertiesMap().get(fabId).getConveyorSubject() + "." + eqpId;
		    			
			this.jo = JsonParser.parseString(msg).getAsJsonObject();
		}catch(Exception e) {
			logger.error("{} seq[{}] error occured parsing cnv msg : {} ", this.cnvId, msgSeq, msg,e);
		}
	}

	@Override
	public void run() {
				
		try 
		{
			// Tibrv 발송 스위치 기능 추가
			String requiredKey = fabId + ":" + eqpId;
	        FunctionItem functionItem = Env.getSwitchMap().get(requiredKey);        
			// TIBRV_SEND
	        if (functionItem != null && functionItem.getUseFunction(FunctionType.TIBRV_SEND))
	        {
	    		TibrvAPI.send("", "", daemon, subject, "DATA", msg);	
	        }
	        //~TIBRV_SEND	        
			// CNV_INOUT
	        if (functionItem != null && functionItem.getUseFunction(FunctionType.CNV_INOUT))
	        {
	        	processMsg();	
	        }
	        //~CNV_INOUT	        
		}catch(Exception e) {
			logger.error("{} seq[{}] error occured processing cnv msg : {} ", this.cnvId, msgSeq, msg,e);
		}
	}

	public void processMsg() {
		if (this.cnv == null) return;
		
		// carrier loc update
		// edge speed update
		// re routing
		// averageRemovalIntervalT update
		// cost, futurecost 함수 구현
		// 최적 Port 선정 algorithm 구현(최단, round robin)
		String msgType = jo.get("type").getAsString();
		
	    try {
	    	logger.debug("{} seq[{}] waited for {}ms msg : [{}] ", this.cnvId, msgSeq, System.currentTimeMillis() - receivedMilli, msgType);
	    	
	    	switch(msgType) {
	    	case "tcsEventSet" :
	    	{
	    		String dataStr = jo.get("data").getAsString();
	    		JsonObject ja = JsonParser.parseString(dataStr).getAsJsonObject();
	    		//JsonObject ja = jo.get("data").getAsJsonObject();											//local에서 테스트할떄 사용
	    		//logger.debug("{} seq[{}] created! msg : [{}] {} ", this.cnvId, msgSeq, msgType, dataStr);	//local에서 테스트할떄 사용
	    		CNV_EVENT event = ja.has("EventCode")?CNV_EVENT.getValue(ja.get("EventCode").getAsString()):CNV_EVENT.UNKNOWN;
	    		String taskId = ja.has("TaskID")?ja.get("TaskID").getAsString():"";
	    		ReentrantLock taskLock = null;
	    		if(StringUtils.isNotEmpty(taskId)) {
	    			taskId = cnvId+":"+taskId;
	    			taskLock = CnvTask.getLock(taskId);
	    		}	    		
	    		try {
	    			switch(event) {
	    			case EVENT_CARRIER_DETECTED : {
	    				CnvTask task = new CnvTask(taskId, receivedMilli);
	    				DataService.getDataSet().getCnvTaskMap().put(taskId, task);
	    				logger.debug("{} seq[{}] task[{}] created! msg : [{}] {} ", this.cnvId, msgSeq, taskId, msgType, dataStr);
	    				int currentZoneNo = ja.has("Location")?ja.get("Location").getAsInt():-1;
	    				CnvPortNode cpn = DataService.getDataSet().getCnvPortNodeNoMap().get(cnvId+":"+currentZoneNo);
	    				if (task !=null && cpn!=null)
	    				{
	    					task.setCurrentNodeId(cpn.getId());
		    				task.setFrNodeLocatedTime(receivedMilli);
		    				task.setFrNodeId(cpn.getId());	    				
		    				task.setEvent(event);
		    				task.setReasonCd(ja.has("Reason")?ja.get("Reason").getAsString():"");
		    				task.setLastReceivedMilli(receivedMilli);
		    				cpn.setCarrierInstalledTime(receivedMilli);
		    				saveCnvTaskToLogpresso(task);	
	    				}	    				
	    			}break;
	    			case EVENT_READ_RFID :{
	    				CnvTask task = DataService.getDataSet().getCnvTaskMap().get(taskId);
	    				int currentZoneNo = ja.has("Location")?ja.get("Location").getAsInt():-1;
	    				CnvPortNode cpn = DataService.getDataSet().getCnvPortNodeNoMap().get(cnvId+":"+currentZoneNo);
	    				if(task == null) {
	    					task = new CnvTask(taskId, receivedMilli);
	    					task.setLastReceivedMilli(receivedMilli);
	    					task.setCurrentNodeId(cpn.getId());
	    					cpn.setCarrierInstalledTime(receivedMilli);
		    				DataService.getDataSet().getCnvTaskMap().put(taskId, task);		    				
	    				}
	    				task.setCurrentNodeId(cpn.getId());
	    				task.setEvent(event);
	    				task.setReasonCd(ja.has("Reason")?ja.get("Reason").getAsString():"");
	    				if(cpn.getId().equals(task.getFrNodeId()))
	    					task.setSrcIdReadTime(receivedMilli);
	    				else
	    					task.setDestIdReadTime(receivedMilli);
	    				String carrierName = ja.has("CarrierID")?ja.get("CarrierID").getAsString():"";
	    				String carrierId = "";
			    		Carrier carrier = null;
			    		carrierId = DataSet.CARRIER_PREFIX +":"+ carrierName;
		    			carrier = DataService.getDataSet().getCarrierMap().get(carrierId);
			    		if(StringUtils.isNotEmpty(carrierName)&&"N/A".equalsIgnoreCase(carrierName)==false) {			    			
			    			if(carrier==null) {
			    				carrier = new Carrier(carrierId, carrierName);
			    				DataService.getDataSet().getCarrierMap().put(carrierId, carrier);
			    			}
			    			task.setCarrierId(carrierId);
			    			if(cpn.getId().equals(task.getFrNodeId()) && task.getFrNodeLocatedTime() > 0 )
			    				carrier.setInstallTime(task.getFrNodeLocatedTime());
			    			else {
			    				carrier.setInstallTime(receivedMilli);
			    			}
			    			carrier.setLocId(cpn.getName());
			    			carrier.setEqpId(cpn.getEqpId());			
			    		}
			    		saveCnvTaskToLogpresso(task);
	    			}break;
	    			case EVENT_TRANSFER_INITIATED :{
	    				String carrierName = ja.has("CarrierID")?ja.get("CarrierID").getAsString():"";
	    				String carrierId = "";
			    		Carrier carrier = null;
			    		if(StringUtils.isNotEmpty(carrierName)&&"N/A".equalsIgnoreCase(carrierName)==false) {
			    			carrierId = DataSet.CARRIER_PREFIX +":"+ carrierName;
			    			carrier = DataService.getDataSet().getCarrierMap().get(carrierId);	
			    			if(carrier==null) {
			    				carrier = new Carrier(carrierId, carrierName);
			    				carrier.setInstallTime(receivedMilli);
			    				DataService.getDataSet().getCarrierMap().put(carrierId, carrier);
			    			}
			    		}
			    		
			    		String jobId = DataSet.JOB_PREFIX+":"+ (ja.has("CommandID")?ja.get("CommandID").getAsString():"");
			    		if(carrier !=null && StringUtils.isNotEmpty(carrier.getJobId())) {
			    			jobId = carrier.getJobId();
			    		}
			    		Job job = DataService.getDataSet().getJobMap().get(jobId);
			    		String cmdId = "";
			    		if(job !=null) {
			    			cmdId = job.getCurrentCommandId();
			    		}		    			
			    		Command cmd = null; 
			    		if(StringUtils.isNotEmpty(cmdId)) {
			    			cmd = DataService.getDataSet().getCommandMap().get(cmdId);		    			
			    		}
			    		CnvTask task = DataService.getDataSet().getCnvTaskMap().get(taskId);
			    		if(task == null) {
	    					task = new CnvTask(taskId, receivedMilli);
	    					task.setCarrierId(carrierId);
	    					//task.setIdReadTime(receivedMilli);
		    				DataService.getDataSet().getCnvTaskMap().put(taskId, task);
	    				}
			    		task.setCmdId(cmdId);
			    		if(cmd!=null)
			    			task.setCmdTime(cmd.getCreateTime());
		    			task.setInitiatedTime(receivedMilli);
		    			task.setEvent(event);
	    				task.setReasonCd(ja.has("Reason")?ja.get("Reason").getAsString():"");
		    			int currentZoneNo = ja.has("Location")?ja.get("Location").getAsInt():-1;
		    			CnvPortNode cpn = DataService.getDataSet().getCnvPortNodeNoMap().get(cnvId+":"+currentZoneNo);
		    			if(cmd!=null) {
		    				cmd.setTransUnitId(task.getId());
		    				cmd.setInitTime(receivedMilli);
		    				String leId = cpn.getToLongEdgeIds().peek();
		    				RouteItem ri = new RouteItem(fabId, cmdId, ROUTE_ITEM_TYPE.REAL, ROUTE_ITEM_DET_TYPE.CNV, leId, 0, task.getFrNodeLocatedTime(), 0, 0, false);
		    				cmd.addRouteId(ri.getId());
		    				DataService.getDataSet().getRouteItemMap().put(ri.getId(),ri);		    				
		    			}
			    		if(carrier != null) {
			    			task.setCarrierId(carrierId);
			    			if(task.getFrNodeLocatedTime() > 0)
			    				carrier.setInstallTime(task.getFrNodeLocatedTime());
			    			carrier.setLocId(cpn.getName());
			    			carrier.setEqpId(cpn.getEqpId());		    			
			    		}
			    		saveCnvTaskToLogpresso(task);
	    			}break;
	    			case EVENT_TRANSFER_TRANSFERRING :{
	    				CnvTask task = DataService.getDataSet().getCnvTaskMap().get(taskId);
	    				if(task!=null) {
	    					task.setEvent(event);
		    				task.setReasonCd(ja.has("Reason")?ja.get("Reason").getAsString():"");
	    					Command cmd = DataService.getDataSet().getCommandMap().get(task.getCmdId());
	    					if(cmd!=null) {
	    						cmd.setAcquireCmpltTime(receivedMilli);
	    						cmd.setDepartedTime(receivedMilli);
	    						cmd.setState(CMD_STATE.DESTMOVING);
	    					}
	    				}else {
	    					task = new CnvTask(taskId, receivedMilli);
	    					DataService.getDataSet().getCnvTaskMap().put(taskId, task);
	    				}
	    				saveCnvTaskToLogpresso(task);
	    			}break;
	    			case EVENT_TRANSFER_COMPLETED :{
	    				CnvTask task = DataService.getDataSet().getCnvTaskMap().get(taskId);
	    				String carrierName = ja.has("CarrierID")?ja.get("CarrierID").getAsString():"";
	    				String carrierId = "";	    		
			    		if(StringUtils.isNotEmpty(carrierName)&&"N/A".equalsIgnoreCase(carrierName)==false) {
			    			carrierId = DataSet.CARRIER_PREFIX +":"+ carrierName;
			    		}
	    				if(task!=null) {
		    				task.setEvent(event);
		    				task.setReasonCd(ja.has("Reason")?ja.get("Reason").getAsString():"");
		    				task.setCompletedTime(receivedMilli);
	    				}else {
	    					task = new CnvTask(taskId, receivedMilli);
	    					task.setEvent(event);
		    				task.setReasonCd(ja.has("Reason")?ja.get("Reason").getAsString():"");
		    				task.setCarrierId(carrierId);
		    				task.setCompletedTime(receivedMilli);
	    					DataService.getDataSet().getCnvTaskMap().put(taskId, task);
	    				}
	    				
			    		Carrier carrier = DataService.getDataSet().getCarrierMap().get(carrierId);
			    		String cmdId = "";
			    		if(carrier!=null && StringUtils.isNotEmpty(carrier.getCmdId())) {
			    			cmdId = carrier.getCmdId();
			    			task.setCmdId(cmdId);
			    		}
			    		else if(task!=null && StringUtils.isNotEmpty(task.getCmdId()))
			    			cmdId = task.getCmdId();
			    		else {
			    			String jobId = DataSet.JOB_PREFIX+":"+ (ja.has("CommandID")?ja.get("CommandID").getAsString():"");
			    			if(StringUtils.isNotEmpty(carrier.getJobId())) {
			    				jobId = carrier.getJobId();
			    			}
				    		Job job = DataService.getDataSet().getJobMap().get(jobId);
				    		if(job !=null) {
				    			cmdId = job.getCurrentCommandId();
				    		}
				    		carrier.setCmdId(cmdId);
				    		task.setCmdId(cmdId);
			    		}
	    				Command cmd = DataService.getDataSet().getCommandMap().get(cmdId);
	    				
	    				if(carrier==null) {
	    					carrier = new Carrier(carrierId, carrierName);
		    				carrier.setInstallTime(receivedMilli);
		    				DataService.getDataSet().getCarrierMap().put(carrierId, carrier);
	    				}
	    				carrier.setState(CARRIER_STATE.WAIT_OUT);
    					carrier.setCmdId("");
	    				if(cmd != null) {
	    					cmd.setDepositCmpltTime(receivedMilli);
    	    				cmd.setDestArrivedTime(receivedMilli); 
    	    				cmd.setCmpltTime(receivedMilli);
	    					cmd.setState(CMD_STATE.COMPLETED);
	    					RouteItem lastRi = null;
	    					if(cmd.getRouteIdList().size()>0) {
	    						lastRi = DataService.getDataSet().getRouteItemMap().get(cmd.getRouteIdList().getLast());
			    				lastRi.setElpaseIntervalT(receivedMilli - task.getFrNodeLocatedTime());
								lastRi.setItemCost(receivedMilli - lastRi.getArrivalTime());
								lastRi.sendToLogpresso();
	    					}
							Job job = DataService.getDataSet().getJobMap().get(cmd.getJobId());
							if(job!=null) {
								List<RouteItem> tobeRemovedListFromEdgePredictQueue = new ArrayList<RouteItem>();
								for(String rid : job.getNewPredictionRouteIdList()) {
									RouteItem r = DataService.getDataSet().getRouteItemMap().get(rid);
									if(r==null)continue;
									tobeRemovedListFromEdgePredictQueue.add(r);
									if(lastRi!=null && r.getEdgeId().equals(lastRi.getEdgeId())) {
										for(RouteItem rm : tobeRemovedListFromEdgePredictQueue) {
//											AtlasCommPubSub.getInstance().publish(JsonUtil.getJsonDelCmdString(RouteItem.class.getName(), rm.getId()));
											DataService.getDataSet().getRouteItemMap().remove(rm.getId());
											LongEdge l = DataService.getDataSet().getLongEdgeMap().get(rm.getEdgeId());
											l.removePredictItem(rm);											
										}
										break;
									}
								}
							}
							//Command 완료시 Logpresso Insert 실시.
							cmd.setInserted(true);							
							Tuple mapCmdDataSet = new Tuple();
//							TsMsgWorkerRunnable.collectAllValue(cmd, mapCmdDataSet);
							LogpressoAPI.setInsertTuple("ATLAS_COMMAND", mapCmdDataSet, 100);
//							try(DatagramSocket udpSocket = new DatagramSocket()){
//								cmd.setInserted(true);							
//								Tuple mapCmdDataSet = new Tuple();
//								TsMsgWorkerRunnable.collectAllValue(cmd, mapCmdDataSet);
////								mapCmdDataSet.put("dataType", "2"); // '2' means the data is a command.
//								
//								// Convert a data set for a command to a json.
//								String jsonCmdStr = new JSONObject(mapCmdDataSet).toString();
//							
//							
//								final byte [] sendBuff = jsonCmdStr.getBytes();
//								udpSocket.send(new DatagramPacket(sendBuff, sendBuff.length, Env.getLogpressoUdpHostAsInetAddr(), Env.getLogpressoUdpPort()));
//								if(Env.getLogpressoUdpHostAsInetAddr2() != null) {
//									udpSocket.send(new DatagramPacket(sendBuff, sendBuff.length, Env.getLogpressoUdpHostAsInetAddr2(), Env.getLogpressoUdpPort()));	
//								}
//							}catch(Exception e) {
//								logger.error("Error occured while inserting command history into logpresso",e);
//								cmd.setInserted(false);
//							}
							
	    				}
	    				saveCnvTaskToLogpresso(task);
	    			}break;
	    			case EVENT_CARRIER_REMOVED :{
	    				CnvTask task = DataService.getDataSet().getCnvTaskMap().remove(taskId);
	    				if(task != null) {
		    				task.setEvent(event);
		    				task.setReasonCd(ja.has("Reason")?ja.get("Reason").getAsString():"");
	    				}
	    				//Command cmd = DataService.getDataSet().getCommandMap().get(task.getCmdId());
	    				//Carrier carrier = DataService.getDataSet().getCarrierMap().get(task.getCarrierId());
	    				int currentZoneNo = ja.has("Location")?ja.get("Location").getAsInt():-1;
	    				CnvPortNode cpn = DataService.getDataSet().getCnvPortNodeNoMap().get(cnvId+":"+currentZoneNo);
	    				String carrierId = ja.has("CarrierID")?"CARRIER:"+ja.get("CarrierID").getAsString():task.getCarrierId();
	    				cpn.removeCarrierId(carrierId);
	    				if(task!=null) {
	    					task.setCurrentNodeId(cpn.getId());
	    					task.setRemovedTime(receivedMilli);
	    				}
	    				cpn.addRemovalIntervalT(receivedMilli-cpn.getCarrierInstalledTime());
	    				cpn.setCarrierRemovedTime(receivedMilli);
	    				saveCnvTaskToLogpresso(task);
	    			}break;
					default:
						break;
	    			}
	    			
	    		}catch(Exception e) {
	    			logger.error("{} seq[{}] taskId[{}] msg : [{}] {} ", this.cnvId, msgSeq, taskId, msgType, dataStr,e);
	    		}finally {
	    			if (taskLock != null && taskLock.isHeldByCurrentThread())
	    				taskLock.unlock();
	    		}
	    	}
	    	break;
	    	case "tcmTransferInfo" :
	    	{
	    		if(jo.get("data").isJsonArray()) {
	    			JsonArray ja = jo.get("data").getAsJsonArray();
	    			for(int i=0 ; i< ja.size(); i++) {
	    				String dataStr = ja.get(i).getAsString();
	    				JsonElement je = JsonParser.parseString(dataStr);
	    				processTcmTransferInfo(je.getAsJsonObject().get("Object").getAsJsonObject(), msgType, dataStr);
	    			}
	    		}
//	    		JsonElement je = JsonParser.parseString(dataStr);
//	    		if(je.isJsonArray()) {
//		    		JsonArray ja = je.getAsJsonArray();
//		    		ja.forEach(jje->{
//		    			processTcmTransferInfo(jje.getAsJsonObject().get("Object").getAsJsonObject(), msgType, dataStr);	    			
//		    		});
//	    		}else {
//	    			processTcmTransferInfo(je.getAsJsonObject().get("Object").getAsJsonObject(), msgType, dataStr);
//	    		}
	    		
	    	}
	    	break;
	    	case "UpdateZoneState" : {
	    		if(jo.get("data").isJsonArray()) {
	    			JsonArray ja = jo.get("data").getAsJsonArray();
	    			for(int i=0 ; i< ja.size(); i++) {
	    				String dataStr = ja.get(i).getAsString().replaceAll("\\\"", "\"");
	    				JsonElement je = JsonParser.parseString(dataStr);
	    				JsonObject jo = je.getAsJsonObject().get("Object").getAsJsonObject();
	    				String zoneNoStr = jo.get("ZoneID").getAsString();
	    				CnvPortNode cpn = DataService.getDataSet().getCnvPortNodeNoMap().get(cnvId + ":" + zoneNoStr);
	    				logger.debug(":::::::::: cpn: {}, {}, {}, {}, {}, {}", cnvId, dataStr, je, jo, zoneNoStr, cpn);
	    				if(cpn!=null) {
	    					boolean state = "0".equals(jo.get("State").getAsString());	    					
	    					if(cpn.isAvailable() != state) {
	    						try {
	    							cpn.setAvailable(state);
	    							FabProperties fp = DataService.getInstance().getFabPropertiesMap().get(fabId);
	    							Conveyor cnv = DataService.getDataSet().getConveyorMap().get(cnvId);
	    							fp.getCnvSocketIOListenerMap().get(cnv.getName()).getRawCnvZoneMap().get(Integer.parseInt(zoneNoStr)).state = state;
	    							for(String leId : cpn.getFromLongEdgeIds()) {
	    								logger.debug(":::::::::: cpn: getFromLongEdgeIds: {}", leId);
	    								saveCnvLongEdgeStateToLogpresso(leId);
	    							}
	    							for(String leId : cpn.getToLongEdgeIds()) {
	    								logger.debug(":::::::::: cpn: getToLongEdgeIds: {}", leId);
	    								saveCnvLongEdgeStateToLogpresso(leId);
	    							}
	    						} catch (Exception e) {
	    							logger.error("cnvId : {} zoneId : {} UpdateZoneState error", cnvId, zoneNoStr, e);
	    						}
	    						
	    					}
	    				}
	    			}
	    		}
	    	}
	    	break;
	    	// 최초 Reconcile 이후 ZoneInfo requset 전송시 메시지 수신 불가 현상
//	    	case "initializedataSend" : {
//	    		JSONObject zoneJo = new JSONObject(jo.get("data").getAsString());
//				JSONArray zoneList = new JSONArray();
//				for(Iterator<String> iter = zoneJo.sortedKeys(); iter.hasNext();) {
//					String key = iter.next();
//					zoneList.put(zoneJo.getJSONObject(key));
//				}
//				CnvSocketIOListener csl = DataService.getInstance().getFabPropertiesMap().get(fabId).getCnvSocketIOListenerMap().get(cnvId);
//				csl.setLayoutStr(zoneJo.toString());
//				csl.buildRawMapData(zoneList);
//				logger.warn("{} new buildRawMap data received!",cnvId);
//	    	}
//	    	break;
	    	}
	    	
    	}catch(Exception e) {    		
    		logger.error("{} seq[{}] msg : [{}] {} ", this.cnvId, msgSeq, msgType, msg,e);
    	}finally {    		
    		logger.debug("{} seq[{}] elapsed for {}ms msg : [{}] {} ", this.cnvId, msgSeq, System.currentTimeMillis() - receivedMilli, msgType, msg);
		}
    }
	
	private void processTcmTransferInfo(JsonElement jje, String msgType, String dataStr) {
		JsonObject j = jje.getAsJsonObject();
		String taskId = cnvId+":"+j.get("TaskID").getAsString();
		ReentrantLock taskLock = CnvTask.getLock(taskId);
		try {
			CnvTask task = DataService.getDataSet().getCnvTaskMap().get(taskId);
			if(task != null) {
				String zoneIdLast = task.getCurrentNodeId();			
				String zoneIdCurrent = j.has("ZoneIDCurrent")?j.get("ZoneIDCurrent").getAsString():"";
				String zoneIdTo = j.has("ZoneIDTo")?j.get("ZoneIDTo").getAsString():"";
				logger.debug("{} zoneIdLast : {} zoneIdCurrent : {}, zoneIdTo : {}", taskId, zoneIdLast, zoneIdCurrent, zoneIdTo);
				JsonArray zoneIdJunctions = new JsonArray();
				if(j.has("ZoneIDJunctions")) {
					if(j.get("ZoneIDJunctions").isJsonArray()) {
						zoneIdJunctions = j.get("ZoneIDJunctions").getAsJsonArray();
					}else {
						if(StringUtils.isNotEmpty(j.get("ZoneIDJunctions").getAsString()))
							zoneIdJunctions.add(j.get("ZoneIDJunctions"));
					}
				}
				//j.has("ZoneIDJunctions")?j.get("ZoneIDJunctions").getAsJsonArray():new JsonArray();
				String carrierId = task.getCarrierId();
				CnvPortNode finalToCpn = null;
				if(StringUtils.isNotEmpty(zoneIdTo) && zoneIdTo.equals("0")==false) {
					finalToCpn = DataService.getDataSet().getCnvPortNodeNoMap().get(cnvId+":"+zoneIdTo);
					zoneIdTo = finalToCpn.getId();
					if(zoneIdTo.equals(task.getToNodeId()) == false) {
						task.setToNodeId(zoneIdTo);
						task.setToNodeFixedTime(receivedMilli);
						finalToCpn.setDestPointedTime(receivedMilli);
					}
				}
				if(zoneIdJunctions.size() > 0) {
					String toGroupId = zoneIdJunctions.get(0).getAsString();
					CnvPortNode gpn = DataService.getDataSet().getCnvPortNodeNoMap().get(cnvId+":"+toGroupId);
					if(gpn!=null)
						task.setToGroupId(gpn.getName());
					else
						task.setToGroupId(toGroupId);
				}
				if(StringUtils.isNotEmpty(zoneIdCurrent)) {
					CnvPortNode lastCpn = (CnvPortNode)DataService.getDataSet().getNodeMap().get(zoneIdLast);
					zoneIdCurrent = cnvId+":"+zoneIdCurrent;
					CnvPortNode cpn = DataService.getDataSet().getCnvPortNodeNoMap().get(zoneIdCurrent);
					task.setCurrentNodeId(cpn.getId());
					long totalTime = receivedMilli-task.getLastReceivedMilli();
					Command cmd = null;
					RouteItem lastRi = null;
					String lastLeId = "";
					if(StringUtils.isEmpty(task.getCmdId())) {
						Carrier carrier = DataService.getDataSet().getCarrierMap().get(carrierId);
						if(carrier != null && StringUtils.isNotEmpty(carrier.getCmdId())) {
							cmd = DataService.getDataSet().getCommandMap().get(carrier.getCmdId());
							if(cmd!=null && StringUtils.isNotEmpty(cmd.getTransEqpId()) && cmd.getTransEqpId().contains(":CNV:"))
								task.setCmdId(carrier.getCmdId());
							else
								cmd = null;
						}
					}
					if(StringUtils.isNotEmpty(task.getCmdId())) {
						cmd = DataService.getDataSet().getCommandMap().get(task.getCmdId());
						if(finalToCpn!=null && zoneIdTo.equals(cmd.getDestNodeId()) == false) {
							cmd.setDestNodeId(zoneIdTo);
							Job job = DataService.getDataSet().getJobMap().get(cmd.getJobId());
							if(job!=null && job.getToEqpId().equals(cnvId)) {
								job.setToNodeId(zoneIdTo);
							}
						}
						if(cmd==null) {
							logger.error("{} CMD IS NULL!", task.getCmdId());
						}
						if(cmd.getRouteIdList().size()>0) {
							lastRi = DataService.getDataSet().getRouteItemMap().get(cmd.getRouteIdList().getLast());
							lastLeId = lastRi.getEdgeId();
						}
					}else {
						logger.warn("{} command Id is not set. carrierId : {}", task.getId(), task.getCarrierId());
					}
					logger.debug("{} zoneIdLast : {}, lastCpn : {}, zoneIdCurrent : {}, cpn : {}", taskId, zoneIdLast, lastCpn, zoneIdCurrent, cpn);
					if(lastCpn != null && lastCpn.getId().equals(cpn.getId())==false && cmd != null) {
						ConcurrentLinkedQueue<CnvEdge> edgeList = new DijkstraCnvFromToPath(lastCpn, cpn, carrierId).getCnvEdgeList();
						
						int size = edgeList.size();
						
						logger.debug("{} lastCpn : {} cpn : {}, edgeList size : {}", taskId,lastCpn.getId(), cpn.getId(), edgeList.size());
						
						long cost = size == 0 ? 0 : totalTime/size;	    						
						long subCostLeSum = 0;
						Set<String> leSet = new HashSet<>();
						for(CnvEdge ce : edgeList) {
							ce.addCost(cost);							
							CnvPortNode headCpn = (CnvPortNode)DataService.getDataSet().getNodeMap().get(ce.getFromNodeId());
							headCpn.setCarrierRemovedTime(headCpn.getCarrierInstalledTime()+cost);	    							
							headCpn.addRemovalIntervalT(cost);
							CnvPortNode tailCpn = (CnvPortNode)DataService.getDataSet().getNodeMap().get(ce.getToNodeId());
							tailCpn.setCarrierInstalledTime(headCpn.getCarrierInstalledTime()+cost);
							leSet.add(ce.getLongEdgeId());
							if(ce.getLongEdgeId().equals(lastLeId) == false) {
								if(lastRi!=null) {
									lastRi.setElpaseIntervalT(task.getLastReceivedMilli()+subCostLeSum - task.getFrNodeLocatedTime());
									lastRi.setItemCost(task.getLastReceivedMilli()+subCostLeSum - lastRi.getArrivalTime());
									lastRi.sendToLogpresso();
								}
								lastRi = new RouteItem(fabId, cmd.getId(), ROUTE_ITEM_TYPE.REAL, ROUTE_ITEM_DET_TYPE.CNV, ce.getLongEdgeId(), cmd.getRouteIdList().size(), task.getLastReceivedMilli()+subCostLeSum, 0, 0, false);
								cmd.addRouteId(lastRi.getId());
								DataService.getDataSet().getRouteItemMap().put(lastRi.getId(), lastRi);
								//logger.debug("{} new route history created : {} longedgeId : {}, route seq : {}", taskId, lastRi.getId(), ce.getLongEdgeId(), lastRi.getSeq());
								subCostLeSum = 0;
							}else {
								subCostLeSum+=cost;
							}
						}
						
						task.setLastReceivedMilli(receivedMilli);
						lastCpn.removeCarrierId(carrierId);
						lastCpn.setCarrierRemovedTime(receivedMilli);
						cpn.addCarrierId(carrierId);
						for(String leId : leSet) {
							saveCnvLongEdgeStateToLogpresso(leId);
						}
					}
					
					if(StringUtils.isNotEmpty(task.getCarrierId())) {
						Carrier carrier = DataService.getDataSet().getCarrierMap().get(task.getCarrierId());
						carrier.setLocId(cpn.getName());
						carrier.setInstallTime(receivedMilli);
						cpn.setCarrierInstalledTime(receivedMilli);
					}
					
				} else {
					logger.debug("{} seq[{}] task {} zoneIdCurrent is {} msg : [{}] {} ", this.cnvId, msgSeq, taskId, zoneIdCurrent, msgType, dataStr);
				}
			}else {
				logger.debug("{} seq[{}] task {} is null msg : [{}] {} ", this.cnvId, msgSeq, taskId, msgType, dataStr);
			}
			saveCnvTaskToLogpresso(task);
		}catch(Exception e) {
			logger.debug("{} seq[{}] msg : [{}] {} ", this.cnvId, msgSeq, msgType, dataStr,e);
		}finally {
			if (taskLock != null && taskLock.isHeldByCurrentThread())
				taskLock.unlock();
		}
	}
	
	private void saveCnvTaskToLogpresso(CnvTask task){
		if(task == null) return;
		
//		Tuple tpl = JsonUtil.getTupleByJsonElement(JsonUtil.toJsonTree(task));
//		LogpressoAPI.setInsertTuple("ATLAS_HIS_CNV_TASK", tpl, 100);		
		// cnvTaskBufferMap 에 저장, Batch에서 Logpresso로 Insert
		DataService.getDataSet().getCnvTaskBufferMap().add(new AbstractMap.SimpleEntry<>(task.getId(), task));
		
		//Tibrv 발송
//		String type = MSG_TYP.CNV.toString() + ".TASK";
//		Map<String, Object> dataMap = new HashMap<>();
//		dataMap.put("TYPE", type);
//		dataMap.put("FAB_ID", fabId);
////		for (Map.Entry<String, Object> entry : tpl.toMap().entrySet()) {
////		    dataMap.put(entry.getKey(), entry.getValue());
////		}
//		dataMap.put("carrierId", task.getCarrierId());
//		dataMap.put("cmdId", task.getCmdId());
//		dataMap.put("cmdTime", task.getCmdTime());
//		dataMap.put("completedTime", task.getCompletedTime());
//		dataMap.put("createTime", task.getCreateTime());
//		dataMap.put("currentNodeId", task.getCurrentNodeId());
//		dataMap.put("destIdReadTime", task.getDestIdReadTime());
//		dataMap.put("event", task.getEvent());
//		dataMap.put("frNodeId", task.getFrNodeId());
//		dataMap.put("frNodeLocatedTime", task.getFrNodeLocatedTime());
//		dataMap.put("id", task.getId());
//		dataMap.put("initiatedTime", task.getInitiatedTime());
//		dataMap.put("lastReceivedMilli", task.getLastReceivedMilli());
//		dataMap.put("reasonCd", task.getReasonCd());
//		dataMap.put("removedTime", task.getRemovedTime());
//		dataMap.put("srcIdReadTime", task.getSrcIdReadTime());
//		dataMap.put("toGroupId", task.getToGroupId());
//		dataMap.put("toNodeFixedTime", task.getToNodeFixedTime());
//		dataMap.put("toNodeId", task.getToNodeId());
//		
//        for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:amos").keySet()) {
//			DataService.getInstance().addTibrvMessageQueue(
//					tibrvKey,
//					type,
//					dataMap
//			);
//		}
	}
	
	private void saveCnvLongEdgeStateToLogpresso(String longEdgeId){
		LongEdge le = DataService.getDataSet().getLongEdgeMap().get(longEdgeId);
		if(le == null) return;
		
		long cost = le.getCost("");
		if(cost > 0) {
			boolean isAvailable = le.isAvailable();
			double speed = (double)le.getLength()/(double)cost*60d;
			
//			Tuple tpl = new Tuple();
//			tpl.put("id", longEdgeId);
//			tpl.put("isAvailable", isAvailable);				
//			tpl.put("cost", cost);
//			tpl.put("speed", speed);
//			LogpressoAPI.setInsertTuple("ATLAS_HIS_CNV_LE_STATE", tpl, 100);
			// cnvLongEdgeBufferMap 에 저장, Batch에서 Logpresso로 Insert			
			DataService.getDataSet().getCnvLongEdgeBufferMap().add(new AbstractMap.SimpleEntry<>(le.getId(), le));
			
			//Tibrv 발송
//			Map<String, Object> dataMap = new HashMap<>();
//			String type = MSG_TYP.CNV.toString() + ".LE";
//            dataMap.put("TYPE", type);
//            dataMap.put("FAB_ID", fabId);
//            dataMap.put("id", longEdgeId);
//            dataMap.put("isAvailable", isAvailable);  
//            dataMap.put("cost", cost);  
//            dataMap.put("speed", speed);  
//            
//            for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:amos").keySet()) {
//    			DataService.getInstance().addTibrvMessageQueue(
//    					tibrvKey,
//    					type,
//    					dataMap
//    			);
//    		}
		}
	}
	
	@Override
	public String toString() {
		return String.format("%s %s %s %s", getClass(), fabId, cnvId, msg);
	}
}
