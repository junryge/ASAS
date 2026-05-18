package com.skhynix.smartatlas.data;

//import java.util.ArrayList;
//import java.util.HashMap;
import java.util.HashSet;
//import java.util.List;
//import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentLinkedDeque;
import java.util.concurrent.ConcurrentLinkedQueue;

import org.apache.commons.lang3.StringUtils;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;

//import com.skhynix.smartatlas.data.RouteItem.ROUTE_ITEM_DET_TYPE;
//import com.skhynix.smartatlas.data.RouteItem.ROUTE_ITEM_TYPE;
import com.skhynix.smartatlas.data.eq.Eqp;
import com.skhynix.smartatlas.data.eq.Eqp.EQP_TYPE;
import com.skhynix.smartatlas.data.raw.RawRouteInfo;
//import com.skhynix.smartatlas.map.AbstractEdge.EDGE_TYPE;
import com.skhynix.smartatlas.map.AbstractNode;
//import com.skhynix.smartatlas.map.CarrierContainable;
import com.skhynix.smartatlas.map.Vhl;
//import com.skhynix.smartatlas.map.Vhl.VHL_STATE;
//import com.skhynix.smartatlas.map.edge.LongEdge;
//import com.skhynix.smartatlas.map.edge.RailEdge;
//import com.skhynix.smartatlas.navi.RouteResult;
//import com.skhynix.smartatlas.navi.RouteResult.PathItem;
import com.skhynix.smartatlas.util.DataService;
//import com.skhynix.smartatlas.util.JsonUtil;

public class Job {
//	private transient Logger logger						= LoggerFactory.getLogger(getClass());
	private String id 									= "";
	private String carrierId 							= "";
	private String lotId 								= "";
	private long createTime 							= -1;
	private long wakeupTime 							= -1;
	private long startTime 								= -1;
	private ConcurrentLinkedQueue<String> commandIdList	= new ConcurrentLinkedQueue<String>();
	private String newFromEqpId 						= "";
	private EQP_TYPE newFromEqpTyp 						= EQP_TYPE.EQP;
	private String newFromEqpGrpNm 						= "";
	private String newFromDetEqpTyp 					= "";
	private String newFromContainerId 					= "";
	private String newFromNodeId 						= "";
	private String newFromFabId 						= "";
	
	// from조건 /////////////////////////////////////////////////
	private String fromFabId 							= "";
	private EQP_TYPE fromEqpTyp 						= EQP_TYPE.EQP;
	private String fromDetEqpTyp 						= "";
	private String fromEqpId 							= "";
	private String fromEqpGrpNm 						= "";
	private String fromNodeId 							= "";	
	
	// to조건 /////////////////////////////////////////////////
	private String toFabId 								= "";
	private EQP_TYPE toEqpTyp 							= EQP_TYPE.EQP;
	private String toDetEqpTyp 							= "";
	private String toEqpGrpNm 							= "";
	//toEqpId
	//toNodeId	
	
	// Etc 조건 /////////////////////////////////////////
	// id : jobId
	// carrierId
	// router
	// stepId
	// router
	// requestor
	// batchId
	// elapsed : createEndIntervalT
	// distance : fromToDistance
	
	private String toNodeGrpId 													= "";
	private String toEqpId 														= "";
	private String toNodeId 													= "";
	private String tmpToNodeId 													= "";
	
	// set Period 조건
	private long endTime 														= -1;
	
	private long cancelTime 													= -1;
	private long newFromToPredictStartTime 										= -1;
	private long newFromToEtaTime 												= -1;
	private long newFromToMLEtaTime 											= -1;
	private long newFromToPredictedCost 										= -1;
	private long etaTime 														= -1;
	private JOB_STATE state 													= JOB_STATE.QUEUED;
	private long vhlErrTime 													= -1;
	private long vhlJamTime 													= -1;
	private long alternatingTime 												= -1;
	private long stateTime 														= -1;
	private JOB_STATE oldState 													= JOB_STATE.QUEUED;
	private long oldStateTime 													= -1;
	private String requestor 													= "";
	private String router 														= "";
	private String stepId 														= "";
	private String stepNm 														= "";
	private String stepTyp 														= "";
	private String midStepTyp 													= "";
	private String detStepTyp 													= "";
	private String batchId 														= "";
	private int batchSeq 														= -1;
//	private int currentCommandSeq 												= -1;
	private ConcurrentLinkedDeque<String> orgPredictionRouteIdList 				= new ConcurrentLinkedDeque<String>();
	private ConcurrentLinkedDeque<String> predictionRouteIdList 				= new ConcurrentLinkedDeque<String>();
	private ConcurrentLinkedDeque<String> newPredictionRouteIdList 				= new ConcurrentLinkedDeque<String>();
	private Set<RawRouteInfo> routeSelectionSet 								= new HashSet<RawRouteInfo>();
	private ConcurrentLinkedDeque<String> routeSelectLongEdgeIdList 			= new ConcurrentLinkedDeque<String>();
	private ConcurrentLinkedDeque<String> routeSelectPassLongEdgeIdList 		= new ConcurrentLinkedDeque<String>();
	private ConcurrentLinkedDeque<String> fromNodeIdHistory 					= new ConcurrentLinkedDeque<String>();
	private ConcurrentLinkedDeque<String> toNodeIdHistory 						= new ConcurrentLinkedDeque<String>();
	private String predictAreaVhlCntStr 										= "";
	private String predictAreaVhlObsCntStr 										= "";
	private String predictAreaVhlJamCntStr 										= "";
	private String predictAreaPredictQueueCntStr 								= "";
	private String predictVhlId 												= "";
	private String assignedVhlId 												= "";
	private ConcurrentLinkedDeque<String> idHistory 							= new ConcurrentLinkedDeque<String>();
	private long ppCostSum 														= -1;
	private long ppCntSum 														= -1;

	private String currentEqpId 												= "";
	private String currentLocId 												= "";
	
//	private Logger getLogger() {
//		if (logger == null) {
//			logger = LoggerFactory.getLogger(getClass());
//		}
//		
//		return logger;
//	}
	
	/**
	 * A constructor to set the batchFlush with the initialization to other fields.
	 * @param id
	 * @param carrierId
	 * @param createTime
	 * @param fromEqpId
	 * @param fromContainerId
	 * @param toGroupId
	 * @param toEqpId
	 * @param toNodeId
	 * @param requestor
	 * @param router
	 * @param stepId
	 * @param batchId
	 * @param batchSeq
	 * @param batchFlush
	 */
	public Job (
				final String id, 
				final String carrierId, 
				final long createTime, 
				final String fromEqpId, 
				final String fromContainerId, 
				final String toNodeGrpId,
				final String toEqpId, 
				final String toNodeId, 
				final String tmpToNodeId, 
				final String requestor, 
				final String router, 
				final String stepId, 
				final String batchId,
				final int batchSeq,
				final boolean batchFlush
	) {
		super();
		
		this.id 				= id;
		
		this.addIdHistory(id);
		
		this.carrierId 			= carrierId;
		this.createTime 		= createTime;
		this.wakeupTime 		= createTime;
		this.newFromEqpId 		= fromEqpId;
		this.newFromContainerId	= fromContainerId;
		
		if (
				StringUtils.isNotEmpty(fromContainerId)
				&& fromContainerId.contains(DataSet.VHL_PREFIX) == false
		) {
			this.setNewFromNodeId(this.newFromContainerId);
		} else if (
				StringUtils.isNotEmpty(fromContainerId)
				&& fromContainerId.contains(DataSet.VHL_PREFIX)
		) {
			Vhl v = DataService.getDataSet().getVhlMap().get(this.newFromContainerId);
			
			this.setNewFromNodeId(v.getRailNodeId());
		}
		
		if (StringUtils.isNotEmpty(this.newFromNodeId)) {
			this.setFromNodeId(this.newFromNodeId);
		}
		
		this.toNodeGrpId 	= toNodeGrpId;
		this.toEqpId 		= toEqpId;
		
//		this.setToNodeId(toNodeId);
		this.setTmpToNodeId(tmpToNodeId);
		
		this.requestor 		= requestor;
		this.router 		= router;
		
		this.setStepId(stepId);
		
		this.batchId 		= batchId;
		this.batchSeq 		= batchSeq;
		this.state 			= JOB_STATE.QUEUED;
		this.stateTime 		= System.currentTimeMillis();
	}
	
	public Job(
				Carrier ca, 
				final long createTime, 
				final String fromEqpId, 
				final String fromContainerId, 
				final String toNodeGrpId,
				final String toEqpId, 
				final String toNodeId,
				final String tmpToNodeId,
				final boolean batchFlush
	) {
		super();
		
		this.id 				= ca.getJobId();
		
		this.addIdHistory(id);
		
		this.carrierId 			= ca.getId();
		this.createTime 		= createTime;
		this.wakeupTime 		= createTime;
		this.newFromEqpId 		= fromEqpId;
		this.newFromContainerId	= fromContainerId;
		
		if (
				StringUtils.isNotEmpty(fromContainerId)
				&& fromContainerId.contains(DataSet.VHL_PREFIX) == false
		) {
			this.setNewFromNodeId(this.newFromContainerId);
		} else if (
				StringUtils.isNotEmpty(fromContainerId) 
				&& fromContainerId.contains(DataSet.VHL_PREFIX)
		) {
			Vhl v = DataService.getDataSet().getVhlMap().get(this.newFromContainerId);
		
			this.setNewFromNodeId(v.getRailNodeId());
		}
		
		if (StringUtils.isNotEmpty(this.newFromNodeId)) {
			this.setFromNodeId(this.newFromNodeId);
		}
		
		this.toNodeGrpId 		= toNodeGrpId;
		this.toEqpId 			= toEqpId;
		
//		this.setToNodeId(toNodeId);
		this.setTmpToNodeId(tmpToNodeId);
		
		this.requestor 			= ca.getRequestor();
		this.router 			= ca.getRouter();
		
		this.setStepId(ca.getStepId());
		
		this.batchId 			= ca.getBatchId();
		this.batchSeq 			= ca.getBatchSeq();
		this.state 				= JOB_STATE.QUEUED;
		this.stateTime 			= System.currentTimeMillis();
	}
	
	public String getId() {
		return id;
	}
	
	public void setId(String id) {
		if (this.id.equals(id) == false) {
			DataService.getDataSet().getJobMap().remove(this.id);
		}
		
		this.id = id;
		
		this.addIdHistory(id);
		
		DataService.getDataSet().getJobMap().put(this.id, this);
	}
	
	public String getNewCommandId(String fabId) {// commandId를 발번하고 job의 commandIdList에 추가
		String commandId = fabId + ":" + DataSet.COMMAND_PREFIX + ":" + this.id.substring(this.id.lastIndexOf(":")+1) + "-" + (getCurrentCommandSeq()+1);		
	
		if (this.commandIdList == null) {
			this.commandIdList = new ConcurrentLinkedQueue<String>();
		}
		
		this.commandIdList.add(commandId);
		this.setCommandIdList(this.commandIdList);
//		setCurrentCommandSeq(getCurrentCommandSeq());
		
		return commandId;
	}
	
	public void addNewCommandId(String commandId) {
		if (this.commandIdList == null) {
			this.commandIdList = new ConcurrentLinkedQueue<String>();
		}
		
		this.commandIdList.add(commandId);
		
		this.setCommandIdList(this.commandIdList);
		
//		setCurrentCommandSeq(getCurrentCommandSeq());
	}
	
	public String getCarrierId() {
		return carrierId;
	}
	
	public void setCarrierId(String carrierId) {
		this.carrierId = carrierId;
	}
	
	public long getWakeupTime() {
		return wakeupTime;
	}
	
	public void setWakeupTime(long wakeupTime) {
		if (this.createTime < 0) {
			this.createTime = wakeupTime;
		}
		
		this.wakeupTime = wakeupTime;
	}
	
	public long getStartTime() {
		return startTime;
	}
	
	public void setStartTime(long startTime) {
		this.startTime = startTime;
	}
	
	public ConcurrentLinkedQueue<String> getCommandIdList() {
		if(commandIdList == null) {
			this.commandIdList = new ConcurrentLinkedQueue<String>();
		}
		return commandIdList;
	}
	
	public void setCommandIdList(ConcurrentLinkedQueue<String> commandIdList) {
		this.commandIdList = commandIdList;
	}
	
	public String getNewFromEqpId() {
		return newFromEqpId;
	}
	
	public void setNewFromEqpId(String newFromEqpId) {
		this.newFromEqpId = newFromEqpId;
	}
	
	public String getNewFromContainerId() {
		return newFromContainerId;
	}
	
	public void setNewFromContainerId(String newFromContainerId) {
		this.newFromContainerId = newFromContainerId;
		
		if (
				StringUtils.isNotEmpty(newFromContainerId)
				&& newFromContainerId.contains(DataSet.VHL_PREFIX) == false
		) {
			this.setNewFromNodeId(this.newFromContainerId);
		} else if (
				StringUtils.isNotEmpty(newFromContainerId)
				&& newFromContainerId.contains(DataSet.VHL_PREFIX)
		) {
			Vhl v = DataService.getDataSet().getVhlMap().get(this.newFromContainerId);
		
			this.setNewFromNodeId(v.getRailNodeId());
		}
		if(StringUtils.isEmpty(this.fromNodeId) && StringUtils.isNotEmpty(this.newFromNodeId))
			this.setFromNodeId(this.newFromNodeId);
	}
	
	public String getNewFromNodeId() {
		return this.newFromNodeId;
	}
	
	public void setNewFromNodeId(String newFromNodeId) {		
		this.newFromNodeId = newFromNodeId;
	
		if (StringUtils.isNotEmpty(this.newFromNodeId)) {
			AbstractNode an = DataService.getDataSet().getNodeMap().get(newFromNodeId);
			
			if (an != null) {
				Eqp eqp = DataService.getDataSet().getAllEqpMap().get(an.getEqpId());
				
				if (eqp != null) {
					this.setNewFromFabId(		eqp.getFabId());
					this.setNewFromEqpId(		eqp.getId());
					this.setNewFromEqpGrpNm(	eqp.getEqpGrpNm());
					this.setNewFromEqpTyp(		eqp.getEqpType());
					this.setNewFromDetEqpTyp(	eqp.getDetEqpTyp());
				}
			}
			
			this.addFromNodeIdHistory(this.newFromNodeId);
			
			if (StringUtils.isEmpty(this.fromNodeId)) {
				this.setFromNodeId(this.newFromNodeId);
			}
		}
	}
	
	public String getToNodeGrpId() {
		return toNodeGrpId;
	}
	
	public void setToNodeGrpId(String toNodeGrpId) {
		this.toNodeGrpId = toNodeGrpId;
	}
	
	public String getToEqpId() {
		return toEqpId;
	}
	
	public void setToEqpId(String toEqpId) {
		this.toEqpId = toEqpId;
	}
	
	public String getToNodeId() {
		return toNodeId;
	}
	
	public void setToNodeId(String toNodeId) {
		String orgToNodeId = this.toNodeId;
		this.toNodeId = toNodeId;			
		if(StringUtils.isNotEmpty(toNodeId)) {
			this.addToNodeIdHistory(toNodeId);
		}
		if(StringUtils.isNotEmpty(orgToNodeId)) {
			AbstractNode orgToNode = DataService.getDataSet().getNodeMap().get(orgToNodeId);
//			if(orgToNode != null) 
//				UiMsgWorkerRunnable.sendPortReservedInfo(orgToNode, orgToNode.isAvailable());
		}
		AbstractNode an = DataService.getDataSet().getNodeMap().get(toNodeId);
		
		if(an != null) {
//			UiMsgWorkerRunnable.sendPortReservedInfo(an, true);
			this.setToFabId(an.getFabId());
			Eqp eqp = DataService.getDataSet().getAllEqpMap().get(an.getEqpId());
			if(eqp != null) {
				this.setToEqpId(eqp.getId());
				this.setToEqpGrpNm(eqp.getEqpGrpNm());
				this.setToEqpTyp(eqp.getEqpType());
				this.setToDetEqpTyp(eqp.getDetEqpTyp());
			}
		}
	}
	
	public String getTmpToNodeId() {
		return tmpToNodeId;
	}
	public void setTmpToNodeId(String tmpToNodeId) {
		this.tmpToNodeId = tmpToNodeId;

		if (StringUtils.isNotEmpty(tmpToNodeId)) {
			this.addToNodeIdHistory(tmpToNodeId + "(T)");
		}
	}
	
	public long getEndTime() {
		return endTime;
	}
	
	public void setEndTime(long endTime) {
		this.endTime = endTime;
	}
	
	public long getEtaTime() {
		return etaTime;
	}
	
	public void setEtaTime(long etaTime) {
		this.etaTime = etaTime;
	}
	
	public JOB_STATE getState() {
		return state;
	}
	
	public void setState(JOB_STATE state) {
		this.oldState 		= this.state;
		this.oldStateTime 	= this.stateTime;
		this.state 			= state;
		this.stateTime 		= System.currentTimeMillis();
	}
	
	public long getStateTime() {
		return stateTime;
	}
	
	public void setStateTime(long stateTime) {
		this.stateTime = stateTime;
	}
	
	public JOB_STATE getOldState() {
		return oldState;
	}
	
	public void setOldState(JOB_STATE oldState) {
		this.oldState = oldState;
	}
	
	public long getOldStateTime() {
		return oldStateTime;
	}
	
	public void setOldStateTime(long oldStateTime) {
		this.oldStateTime = oldStateTime;
	}
	
	public String getRequestor() {
		return requestor;
	}
	
	public void setRequestor(String requestor) {
		this.requestor = requestor;
	}
	
	public String getRouter() {
		return router;
	}
	
	public void setRouter(String router) {
		this.router = router;
	}
	
	public String getStepId() {
		return stepId;
	}
	
	public void setStepId(String stepId) {
		this.stepId = stepId;		
	}
	
//	public void fillStepDescription() {
//		if (
//				StringUtils.isNotEmpty(this.stepId) 
//				&& "REAL".equals(DataService.getInstance().getEnv())
//		) {
//			Map<String,Object> operMap = null;
//			
//			if (StringUtils.isNotEmpty(stepId)) {			
//				try (QueryExecutor qe = QueryExecutorFactory.build("stasms")) {
//					Map<String,String> paraM 	= new HashMap<String, String>();
//					
//					paraM.put("OPER_ID", stepId);
//					
//					operMap 					= qe.selectOne("SELECT_STA_OPER_MAS", paraM);
//					
//					if (operMap != null) {
//						this.stepNm 	= (String)operMap.get("OPER_NM");
//						this.stepTyp 	= (String)operMap.get("OPER_TYP");
//						this.midStepTyp	= (String)operMap.get("MID_OPER_TYP");
//						this.detStepTyp	= (String)operMap.get("DET_OPER_TYP");
//					}
//				} catch (Exception e) {
//					getLogger().error("Set Step Fail!", e);
//				}		
//			}
//		}
//	}
	
	public String getBatchId() {
		return batchId;
	}
	public void setBatchId(String batchId) {
		this.batchId = batchId;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, batchId, new Path(".batchId"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "batchId", this.id, this.batchId, new TypeToken<String>() {}.getType()));
	}
	public int getBatchSeq() {
		return batchSeq;
	}
	public void setBatchSeq(int batchSeq) {
		this.batchSeq = batchSeq;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, batchSeq, new Path(".batchSeq"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "batchSeq", this.id, new Integer(this.batchSeq), new TypeToken<Integer>() {}.getType()));
	}
	public int getCurrentCommandSeq() {		
		return getCommandIdList().size()-1;
	}
//	public void setCurrentCommandSeq(int currentCommandSeq) {
//		this.currentCommandSeq = currentCommandSeq;
////		if (!this.batchFlush)
////			RedisPool.jset(this.id, currentCommandSeq, new Path(".currentCommandSeq"));
////		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "currentCommandSeq", this.id, new Integer(this.currentCommandSeq), new TypeToken<Integer>() {}.getType()));
//	}
	
	public ConcurrentLinkedDeque<String> getPredictionRouteIdList() {
		if(this.predictionRouteIdList == null)
			this.predictionRouteIdList = new ConcurrentLinkedDeque<String>();
		return predictionRouteIdList;
	}

	public void setPredictionRouteIdList(ConcurrentLinkedDeque<String> predictionRouteIdList) {
		this.predictionRouteIdList = predictionRouteIdList;
//		AtlasCommPubSub.getInstance().publish(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "predictionRouteIdList", this.id, this.predictionRouteIdList, new TypeToken<ConcurrentLinkedDeque<String>>() {}.getType()));
//		try(Jedis j=RedisPool.getJedisClient()){
//			j.del(this.getId()+"#predictionRouteIdList");
//			j.rpush(this.getId()+"#predictionRouteIdList", predictionRouteIdList.toArray(new String[predictionRouteIdList.size()]));
//		}
		//RedisPool.jset(this.id, predictionRouteIdList, new Path(".predictionRouteIdList"));
	}
	
	public void addPredictionRouteIdList(ConcurrentLinkedDeque<String> predictionRouteIdList) {
		this.predictionRouteIdList.addAll(predictionRouteIdList);
//		AtlasCommPubSub.getInstance().publish(JsonUtil.getJsonCmdString(ActionType.ADD_COLLECTION_ALL, getClass().getName(), "predictionRouteIdList", this.id, this.predictionRouteIdList, new TypeToken<ConcurrentLinkedDeque<String>>() {}.getType()));
//		try(Jedis j=RedisPool.getJedisClient()){
//			j.rpush(this.getId()+"#predictionRouteIdList", predictionRouteIdList.toArray(new String[predictionRouteIdList.size()]));
//		}
		//RedisPool.jset(this.id, predictionRouteIdList, new Path(".predictionRouteIdList"));
	}
	
	public void addPredictionRouteId(String predictionRouteId) {
		this.getPredictionRouteIdList().add(predictionRouteId);
//		AtlasCommPubSub.getInstance().publish(JsonUtil.getJsonCmdString(ActionType.ADD_COLLECTION_ITEM, getClass().getName(), "predictionRouteIdList", this.id, predictionRouteId, new TypeToken<String>() {}.getType()));
//		try(Jedis j=RedisPool.getJedisClient()){
//			j.rpush(this.getId()+"#predictionRouteIdList", predictionRouteId);
//		}
		//RedisPool.jset(this.id, predictionRouteIdList, new Path(".predictionRouteIdList"));
	}

	public ConcurrentLinkedDeque<String> getNewPredictionRouteIdList() {
		if(this.newPredictionRouteIdList == null)
			this.newPredictionRouteIdList = new ConcurrentLinkedDeque<String>();
		return newPredictionRouteIdList;
	}

	public void setNewPredictionRouteIdList(ConcurrentLinkedDeque<String> newPredictionRouteIdList) {
		this.newPredictionRouteIdList = newPredictionRouteIdList;
//		AtlasCommPubSub.getInstance().publish(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "newPredictionRouteIdList", this.id, this.newPredictionRouteIdList, new TypeToken<ConcurrentLinkedDeque<String>>() {}.getType()));
//		try(Jedis j=RedisPool.getJedisClient()){
//			j.del(this.getId()+"#newPredictionRouteIdList");
//			j.rpush(this.getId()+"#newPredictionRouteIdList", newPredictionRouteIdList.toArray(new String[newPredictionRouteIdList.size()]));
//		}
		//RedisPool.jset(this.id, newPredictionRouteIdList, new Path(".newPredictionRouteIdList"));
	}
	public void addNewPredictionRouteIdList(ConcurrentLinkedDeque<String> newPredictionRouteIdList) {
		this.newPredictionRouteIdList.addAll(newPredictionRouteIdList);
//		AtlasCommPubSub.getInstance().publish(JsonUtil.getJsonCmdString(ActionType.ADD_COLLECTION_ALL, getClass().getName(), "newPredictionRouteIdList", this.id, newPredictionRouteIdList, new TypeToken<ConcurrentLinkedDeque<String>>() {}.getType()));
//		try(Jedis j=RedisPool.getJedisClient()){
//			j.rpush(this.getId()+"#newPredictionRouteIdList", newPredictionRouteIdList.toArray(new String[newPredictionRouteIdList.size()]));
//		}
		//RedisPool.jset(this.id, newPredictionRouteIdList, new Path(".newPredictionRouteIdList"));
	}
	
	public void addNewPredictionRouteId(String newPredictionRouteId) {
		this.getNewPredictionRouteIdList().add(newPredictionRouteId);
//		AtlasCommPubSub.getInstance().publish(JsonUtil.getJsonCmdString(ActionType.ADD_COLLECTION_ITEM, getClass().getName(), "newPredictionRouteIdList", this.id, newPredictionRouteId, new TypeToken<String>() {}.getType()));
//		try(Jedis j=RedisPool.getJedisClient()){
//			j.rpush(this.getId()+"#newPredictionRouteIdList", newPredictionRouteId);
//		}
		//RedisPool.jset(this.id, newPredictionRouteIdList, new Path(".newPredictionRouteIdList"));
	}
	
//	public void updatePredictionRoute(RouteResult rr, boolean isUpdateOrgPredictionRoute) {
//		if(rr == null) return;
//		ConcurrentLinkedDeque<String> rl = new ConcurrentLinkedDeque<String>();
//		int seq = 0;
//		long startMilli = System.currentTimeMillis();
//		long costsum = 0;
//		long ppCostSum = 0;
//		long ppCntSum = 0;
//// First, remove the prior route item.
//		for(String ris : this.getPredictionRouteIdList()) {
//			RouteItem ri = DataService.getDataSet().getRouteItemMap().remove(ris);
////			AtlasCommPubSub.getInstance().publish(JsonUtil.getJsonDelCmdString(RouteItem.class.getName(), ris));
//			if(ri!=null) {
//				LongEdge le = DataService.getDataSet().getLongEdgeMap().get(ri.getEdgeId());
//				le.removePredictItem(ri);
////				for(String edgeId : le.getEdgeIdList()) {
////					AbstractEdge ae = DataService.getDataSet().getEdgeMap().get(edgeId);
////					ae.removePredictItem(ri);
////				}
//			}
//		}
//		this.updateNewPredictionRouteReset();
//		this.setNewFromToPredictStartTime(System.currentTimeMillis());
//		this.setNewFromToEtaTime(System.currentTimeMillis() + (long)rr.totalCost);
//		List<String> passAreaList = new ArrayList<String>();
//		Map<String,int[]> passAreaMap = new HashMap<String,int[]>();
//		
//		List<Object[]> areaVhlCntList = new ArrayList<Object[]>();
//		List<Object[]> areaVhlObsCntList = new ArrayList<Object[]>();
//		List<Object[]> areaVhlJamCntList = new ArrayList<Object[]>();
//		List<Object[]> areaPredictQueueCntList = new ArrayList<Object[]>();
//		
//		List<RouteItem> routeItemList = new ArrayList<RouteItem>();
//		List<RouteItem> orgRouteItemList = new ArrayList<RouteItem>();
//		ConcurrentLinkedDeque<String> orl = new ConcurrentLinkedDeque<String>();
//		if(isUpdateOrgPredictionRoute) {
//			for(String ori : getOrgPredictionRouteIdList()) {
//				DataService.getDataSet().getRouteItemMap().remove(ori);
//			}
//			setOrgPredictionRouteIdList(new ConcurrentLinkedDeque<>());
//		}
//		for(PathItem pi : rr.getPath()) {
//			costsum+=pi.cost;
//			LongEdge le = DataService.getDataSet().getLongEdgeMap().get(pi.longEdgeId);
//			String leFabAreaId = le.getFabId() + ":" + DataSet.AREA_PREFIX + ":" + le.getFirstAreaName();
//			if(passAreaMap.containsKey(leFabAreaId) == false) {
//				passAreaList.add(leFabAreaId);				
//			}
//			passAreaMap.put(leFabAreaId,new int[] {0,0,0,0});
//			EDGE_TYPE et = le.getFirstEdgeType();
//			ROUTE_ITEM_DET_TYPE ridt = null;
//			RouteItem ri = null;
//			switch(et) {
//				case RAILEDGE : {
//					ridt = ROUTE_ITEM_DET_TYPE.RAIL;	
//				}break;
//				case TRANSEDGE_ACQUIRE :{
//					ridt = ROUTE_ITEM_DET_TYPE.TRANS_ACQ;
//				}break;
//				case TRANSEDGE_DEPOSIT :{
//					ridt = ROUTE_ITEM_DET_TYPE.TRANS_DPST;
//				}break;
//				case STKRMEDGE : {
//					ridt = ROUTE_ITEM_DET_TYPE.STK;
//				}break;
//				case CNVEDGE : {
//					ridt = ROUTE_ITEM_DET_TYPE.CNV;
//				}break;
//				default : {
//					getLogger().debug("no type def exists of {}",et);
//				}
//			}
//			ri = new RouteItem(le.getFabId(), this.id, ROUTE_ITEM_TYPE.PREDICT, ridt, pi.longEdgeId, seq++, startMilli+costsum-(long)pi.cost, costsum, (long)pi.cost, le.getCost(""), le.getFutureTransCount(carrierId, costsum), le.getFutureAcqCount(carrierId, costsum), le.getFutureDpstCount(carrierId, costsum), le.getCurrentVhlStateMap().toString(), le.getCurrentVhlDetStateMap().toString(), le.getCurrentVhlCycleMap().toString(), le.getCurrentVhlRunCycleMap().toString());
//			DataService.getDataSet().getRouteItemMap().put(ri.getId(),ri);
//			if(isUpdateOrgPredictionRoute) {
//				RouteItem ori = new RouteItem(le.getFabId(), this.id, ROUTE_ITEM_TYPE.ORGPREDICT, ridt, pi.longEdgeId, seq++, startMilli+costsum-(long)pi.cost, costsum, (long)pi.cost, le.getCost(""), le.getFutureTransCount(carrierId, costsum), le.getFutureAcqCount(carrierId, costsum), le.getFutureDpstCount(carrierId, costsum), le.getCurrentVhlStateMap().toString(), le.getCurrentVhlDetStateMap().toString(), le.getCurrentVhlCycleMap().toString(), le.getCurrentVhlRunCycleMap().toString());
//				DataService.getDataSet().getRouteItemMap().put(ori.getId(),ori);
//				orl.add(ori.getId());
//				orgRouteItemList.add(ori);
//			}
//			rl.add(ri.getId());
//			routeItemList.add(ri);
//			ppCostSum += le.getCost("");
//			ppCntSum += le.getPathPredictQueueSize();
//		}
//		if(isUpdateOrgPredictionRoute) {
//			this.setOrgPredictionRouteIdList(orl);
//		}
//		for(String areaId : passAreaList) {
//			Area area = DataService.getDataSet().getAreaMap().get(areaId);
//			if(area == null)continue;
//			int[] areaCnts = passAreaMap.get(areaId);
//			Set<String> les = new HashSet<String>(); 
//			for(String railEdgeId : area.getRailEdgeIdList()) {
//				RailEdge re = DataService.getDataSet().getRailEdgeMap().get(railEdgeId);
//				for(String vhlId : re.getVhlIdMap().keySet()) {
//					Vhl vhl = DataService.getDataSet().getVhlMap().get(vhlId);					
//					areaCnts[0]++;
//					if(vhl.getState() == VHL_STATE.OBS_BZ_STOP) areaCnts[1]++;
//					if(vhl.getState() == VHL_STATE.JAM) areaCnts[2]++;
//				}				
//				les.add(re.getLongEdgeId());
//			}
//			for(String leId : les) {
//				LongEdge le = DataService.getDataSet().getLongEdgeMap().get(leId);
//				if(le != null)
//					areaCnts[3] += le.getPathPredictQueueSize();
//			}
//			areaVhlCntList.add(new Object[] {areaId,areaCnts[0]});
//			areaVhlObsCntList.add(new Object[] {areaId,areaCnts[1]});
//			areaVhlJamCntList.add(new Object[] {areaId,areaCnts[2]});
//			areaPredictQueueCntList.add(new Object[] {areaId,(float)areaCnts[3]/(float)les.size()});
//		}
//		this.setPredictAreaVhlCntStr(JsonUtil.convertJSON(areaVhlCntList));
//		this.setPredictAreaVhlObsCntStr(JsonUtil.convertJSON(areaVhlObsCntList));
//		this.setPredictAreaVhlJamCntStr(JsonUtil.convertJSON(areaVhlJamCntList));
//		this.setPredictAreaPredictQueueCntStr(JsonUtil.convertJSON(areaPredictQueueCntList));
//		this.setPredictionRouteIdList(rl);
//		this.setRouteSelectionSet(rr.routeSelectionSet);
//		this.getRouteSelectLongEdgeIdList().clear();
//		this.getRouteSelectLongEdgeIdList().addAll(rr.routeSelectionLongEdgeIdList);
//		this.setRouteSelectLongEdgeIdList(this.getRouteSelectLongEdgeIdList());
//		this.setPpCostSum(ppCostSum);
//		this.setPpCntSum(ppCntSum);
////		int futureAcqCnt = 0;  
////		int futureDpstCnt = 0; 
////		int ftcs_TRANS_ACQ = 0; 
////		int ftcs_TRANS_DPST = 0; 
////		int ftcs_STK = 0; 
////		int ftcs_CNV = 0;
////		int ftcs_RAIL = 0;
////		int cs_TRANS_ACQ = 0;
////		int cs_TRANS_DPST = 0;
////		int cs_STK = 0;
////		int cs_CNV = 0;
////		int cs_RAIL = 0;
////		int predictDistance = 0;
////		String fromFabId = "";
////		String toFabId = "";
//		
//		AbstractNode fn = DataService.getDataSet().getNodeMap().get(newFromNodeId);		
//		AbstractNode tn = DataService.getDataSet().getNodeMap().get(toNodeId);
//		if(tn == null)
//			tn = DataService.getDataSet().getNodeMap().get(tmpToNodeId);
//		
////		for(RouteItem ri : routeItemList) {
////			futureAcqCnt += ri.getFutureAcqCnt();
////			futureDpstCnt += ri.getFutureDpstCnt();
////			predictDistance += ri.getLength();
////			
////			switch(ri.getRouteItemDetType()) {
////				case TRANS_ACQ : 
////					ftcs_TRANS_ACQ += ri.getFutureTransCnt();
////					cs_TRANS_ACQ += ri.getCurrentCost();
////					
////					break;
////				case TRANS_DPST :
////					ftcs_TRANS_DPST += ri.getFutureTransCnt();
////					cs_TRANS_DPST += ri.getCurrentCost();
////					
////					break;
////				case STK :
////					ftcs_STK += ri.getFutureTransCnt();
////					cs_STK += ri.getCurrentCost();
////					
////					break;
////				case CNV :
////					ftcs_CNV += ri.getFutureTransCnt();
////					cs_CNV += ri.getCurrentCost();
////					
////					break;
////				case RAIL :
////					ftcs_RAIL += ri.getFutureTransCnt();
////					cs_RAIL += ri.getCurrentCost();
////					
////					break;
////			}
////		}
//		
//		float enhancedPredictResult = -1;
//
//		if (
//				fn != null 
//				&& tn != null 
//				&& fn.getId().startsWith("M14") 
//				&& tn.getId().startsWith("M14")
//		) {		
//			fromFabId 				= fn.getFabId();
//			toFabId 				= tn.getFabId();
////			enhancedPredictResult 	= AtlasPredictEnhanceTibrvReq.getInstance()
////						.requestPredictEnhancedValue(fromFabId, toFabId, futureAcqCnt, futureDpstCnt, ftcs_TRANS_ACQ, ftcs_TRANS_DPST, ftcs_STK, ftcs_CNV, ftcs_RAIL, cs_TRANS_ACQ, cs_TRANS_DPST, cs_STK, cs_CNV, cs_RAIL, predictDistance);
//		}
//		
//		if (enhancedPredictResult == -1) {
//			this.setEtaTime(this.getNewFromToEtaTime());
//			this.setNewFromToMLEtaTime(this.getNewFromToEtaTime());
//		} else {
//			this.setNewFromToMLEtaTime(System.currentTimeMillis() + (long)(enhancedPredictResult*1000));
//			this.setEtaTime(this.getNewFromToMLEtaTime());
//		}
//	}
	
//	public void updateNewPredictionRouteReset() {
//		ConcurrentLinkedDeque<String> rl = new ConcurrentLinkedDeque<String>();
//		
//		// First, remove the prior route item.
//		for (String ris : this.getNewPredictionRouteIdList()) {
//			RouteItem ri = DataService.getDataSet().getRouteItemMap().remove(ris);
//
//			if (ri != null) {
//				LongEdge le = DataService.getDataSet().getLongEdgeMap().get(ri.getEdgeId());
//				
//				le.removePredictItem(ri);
//			}
//		}
//		// Second, add the new route item.		
//		this.setNewPredictionRouteIdList(rl);
//	}
	
//	public void updateNewPredictionRoute(RouteResult rr) {
//		ConcurrentLinkedDeque<String> rl = new ConcurrentLinkedDeque<String>();
//		int seq = 0;
//		long startMilli = System.currentTimeMillis();		
//		long costsum = 0;
//		if(rr==null) {
//			getLogger().error("No route exists!!!!!!!!!!!!!!!!!!\nJob:{}",JsonUtil.convertJSON(this));
//			return;
//		}
//		
//		// First, remove the prior route item.
//		for (String ris : this.getNewPredictionRouteIdList()) {
//			RouteItem ri = DataService.getDataSet().getRouteItemMap().remove(ris);
//
//			if (ri != null) {
//				LongEdge le = DataService.getDataSet().getLongEdgeMap().get(ri.getEdgeId());
//				le.removePredictItem(ri);
//			}
//		}
//		
//		this.setEtaTime(System.currentTimeMillis() + (long)rr.totalCost);
//		
//		Vhl currentVhl = null;
//		Carrier ca = DataService.getDataSet().getCarrierMap().get(carrierId);
//		if(ca != null && StringUtils.isNotEmpty(ca.getLocId()) && StringUtils.isNotEmpty(ca.getEqpId()) ) {
//			Eqp carrierEqp = DataService.getDataSet().getAllEqpMap().get(ca.getEqpId());
//			CarrierContainable cc = DataService.getDataSet().getCarrierContainableByCarrierLoc(ca.getLocId(), carrierEqp.getFabId());
//			if(cc != null && cc instanceof Vhl) {
//				currentVhl = (Vhl)cc;
//			}
//		}
//		
//		// Second, add the new route item.
//		ROUTE_ITEM_DET_TYPE lastRidt = null;
//		for(PathItem pi : rr.getPath()) {
//			costsum+=pi.cost;
//			LongEdge le = DataService.getDataSet().getLongEdgeMap().get(pi.longEdgeId);
//			EDGE_TYPE et = le.getFirstEdgeType();
//			ROUTE_ITEM_DET_TYPE ridt = null;
//			RouteItem ri = null;
//			
//			switch(et) {
//				case RAILEDGE : {
//					ridt = ROUTE_ITEM_DET_TYPE.RAIL;					
//				}break;
//				case TRANSEDGE_ACQUIRE : {
//					ridt = ROUTE_ITEM_DET_TYPE.TRANS_ACQ;
//				}break;
//				case TRANSEDGE_DEPOSIT : {
//					ridt = ROUTE_ITEM_DET_TYPE.TRANS_DPST;
//				}break;
//				case STKRMEDGE : {
//					ridt = ROUTE_ITEM_DET_TYPE.STK;
//				}break;
//				case CNVEDGE : {
//					ridt = ROUTE_ITEM_DET_TYPE.CNV;
//				}break;
//				default : {
//					getLogger().debug("no type def exists of {}",et);
//				}
//			}
//			
//			// 이동중인 vhl의 현재 목적지 까지의 도착 예상시간 update실시
//			if (
//					ridt != lastRidt 
//					&& lastRidt != null 
//					&& lastRidt == ROUTE_ITEM_DET_TYPE.RAIL 
//					&& currentVhl != null 
//					&& currentVhl.getFabId().equals(le.getFabId())
//			) { 
////				currentVhl.setCurrentDestEta(startMilli+costsum);
//			}
//
//			lastRidt = ridt;
//			ri = new RouteItem(le.getFabId(), this.id, ROUTE_ITEM_TYPE.NEWPREDICT, ridt, pi.longEdgeId, seq++, startMilli+costsum-(long)pi.cost, costsum, (long)pi.cost, le.getCost(""), le.getFutureTransCount(carrierId, costsum), le.getFutureAcqCount(carrierId, costsum), le.getFutureDpstCount(carrierId, costsum), le.getCurrentVhlStateMap().toString(), le.getCurrentVhlDetStateMap().toString(), le.getCurrentVhlCycleMap().toString(), le.getCurrentVhlRunCycleMap().toString());
//			DataService.getDataSet().getRouteItemMap().put(ri.getId(),ri);
//			rl.add(ri.getId());
//			
//			le.addPredictItem(ri);
//		}
//		this.setNewPredictionRouteIdList(rl);
//	}

	public enum JOB_STATE{
		QUEUED, PROCESSING, ALTERNATING, ALTERNATED, CANCELING, 
		CANCELED, ABORTING, ABORTED, COMPLETED, ERROR, NONE
	}

	public Set<RawRouteInfo> getRouteSelectionSet() {
		if(routeSelectionSet == null)
			this.routeSelectionSet = new HashSet<RawRouteInfo>();
		return routeSelectionSet;
	}
	
	public void setRouteSelectionSet(Set<RawRouteInfo> routeSelectionSet) {
		this.routeSelectionSet = routeSelectionSet;
	}
	
	public ConcurrentLinkedDeque<String> getRouteSelectLongEdgeIdList() {
		if (routeSelectLongEdgeIdList == null) {
			this.routeSelectLongEdgeIdList = new ConcurrentLinkedDeque<String>();
		}
		
		return routeSelectLongEdgeIdList;
	}
	
	public void setRouteSelectLongEdgeIdList(ConcurrentLinkedDeque<String> routeSelectLongEdgeIdList) {
		this.routeSelectLongEdgeIdList = routeSelectLongEdgeIdList;
	}
	
	public ConcurrentLinkedDeque<String> getRouteSelectPassLongEdgeIdList() {
		if(routeSelectPassLongEdgeIdList == null) {
			this.routeSelectPassLongEdgeIdList = new ConcurrentLinkedDeque<String>();
		}
		return routeSelectPassLongEdgeIdList;
	}
	
	public void setRouteSelectPassLongEdgeIdList(ConcurrentLinkedDeque<String> routeSelectPassLongEdgeIdList) {
		this.routeSelectPassLongEdgeIdList = routeSelectPassLongEdgeIdList;
	}
	
	public void addRouteSelectPassLongEdgeId(String routeSelectPassLongEdgeId) {
		if(this.getRouteSelectPassLongEdgeIdList().contains(routeSelectPassLongEdgeId))
			return;
		this.getRouteSelectPassLongEdgeIdList().add(routeSelectPassLongEdgeId);
	}
	
	public ConcurrentLinkedDeque<String> getFromNodeIdHistory() {
		if(this.fromNodeIdHistory == null)
			this.fromNodeIdHistory = new ConcurrentLinkedDeque<String>();
		return fromNodeIdHistory;
	}
	
	public void setFromNodeIdHistory(ConcurrentLinkedDeque<String> fromNodeIdHistory) {
		this.fromNodeIdHistory = fromNodeIdHistory;
	}
	
	synchronized public boolean addFromNodeIdHistory(String fromNodeId) {
		ConcurrentLinkedDeque<String> fromNodeIdHistory = getFromNodeIdHistory();
		if(fromNodeIdHistory.size()>0 && fromNodeIdHistory.getLast().equals(fromNodeId))
			return false;
		fromNodeIdHistory.add(fromNodeId);
		return true;
	}
	
	public ConcurrentLinkedDeque<String> getToNodeIdHistory() {
		if(this.toNodeIdHistory == null)
			this.toNodeIdHistory = new ConcurrentLinkedDeque<String>();
		return toNodeIdHistory;
	}
	
	public void setToNodeIdHistory(ConcurrentLinkedDeque<String> toNodeIdHistory) {
		this.toNodeIdHistory = toNodeIdHistory;
	}
	
	synchronized public boolean addToNodeIdHistory(String toNodeId) {
		ConcurrentLinkedDeque<String> toNodeIdHistory = getToNodeIdHistory();		
		if(toNodeIdHistory.size() > 0 && toNodeIdHistory.getLast().equals(toNodeId))
			return false;
		toNodeIdHistory.add(toNodeId);
		return true;
	}
	
	public long getNewFromToPredictStartTime() {
		return newFromToPredictStartTime;
	}
	
	public void setNewFromToPredictStartTime(long newFromToPredictStartTime) {
		this.newFromToPredictStartTime = newFromToPredictStartTime;
	}
	
	public long getNewFromToMLEtaTime() {
		return newFromToMLEtaTime;
	}
	
	public void setNewFromToMLEtaTime(long newFromToMLEtaTime) {
		this.newFromToMLEtaTime = newFromToMLEtaTime;
		if(newFromToMLEtaTime > 0)
			this.setNewFromToPredictedCost(newFromToMLEtaTime - this.newFromToPredictStartTime);
	}
	
	public String getPredictAreaVhlCntStr() {
		return predictAreaVhlCntStr;
	}
	
	public void setPredictAreaVhlCntStr(String predictAreaVhlCntStr) {
		this.predictAreaVhlCntStr = predictAreaVhlCntStr;
	}
	
	public String getPredictAreaVhlObsCntStr() {
		return predictAreaVhlObsCntStr;
	}
	public void setPredictAreaVhlObsCntStr(String predictAreaVhlObsCntStr) {
		this.predictAreaVhlObsCntStr = predictAreaVhlObsCntStr;
	}
	public String getPredictAreaVhlJamCntStr() {
		return predictAreaVhlJamCntStr;
	}
	public void setPredictAreaVhlJamCntStr(String predictAreaVhlJamCntStr) {
		this.predictAreaVhlJamCntStr = predictAreaVhlJamCntStr;
	}
	public String getPredictAreaPredictQueueCntStr() {
		return predictAreaPredictQueueCntStr;
	}
	public void setPredictAreaPredictQueueCntStr(String predictAreaPredictQueueCntStr) {
		this.predictAreaPredictQueueCntStr = predictAreaPredictQueueCntStr;
	}
	public long getCancelTime() {
		return cancelTime;
	}
	public void setCancelTime(long cancelTime) {
		this.cancelTime = cancelTime;
	}
	public long getVhlErrTime() {
		return vhlErrTime;
	}
	public void setVhlErrTime(long vhlErrTime) {
		this.vhlErrTime = vhlErrTime;
	}
	public long getVhlJamTime() {
		return vhlJamTime;
	}
	public void setVhlJamTime(long vhlJamTime) {
		this.vhlJamTime = vhlJamTime;
	}
	public long getAlternatingTime() {
		return alternatingTime;
	}
	public void setAlternatingTime(long alternatingTime) {
		this.alternatingTime = alternatingTime;
	}
	
	public String getCurrentCommandId() {
		if(getCurrentCommandSeq() >= 0)
			return (String)getCommandIdList().toArray()[getCurrentCommandSeq()];
		else 
			return null;
	}
	public String getPredictVhlId() {
		return predictVhlId;
	}
	public void setPredictVhlId(String predictVhlId) {
		this.predictVhlId = predictVhlId;
	}
	public String getAssignedVhlId() {
		return assignedVhlId;
	}
	public void setAssignedVhlId(String assignedVhlId) {
		this.assignedVhlId = assignedVhlId;
	}
	public long getNewFromToEtaTime() {
		return newFromToEtaTime;
	}
	public void setNewFromToEtaTime(long newFromToEtaTime) {
		this.newFromToEtaTime = newFromToEtaTime;
	}
	public ConcurrentLinkedDeque<String> getIdHistory() {
		if(this.idHistory == null)
			this.idHistory = new ConcurrentLinkedDeque<String>();
		return idHistory;
	}
	public void setIdHistory(ConcurrentLinkedDeque<String> idHistory) {
		this.idHistory = idHistory;
	}
	public void addIdHistory(String id) {
		if (this.idHistory == null) {
			this.idHistory = new ConcurrentLinkedDeque<String>();
		}
		
		if (this.idHistory.contains(id) == false) {
			this.idHistory.add(id);
		}
	}
	
	public long getCreateTime() {
		return createTime;
	}
	
	public void setCreateTime(long createTime) {
		this.createTime = createTime;
	}
	
	public String getFromNodeId() {
		return fromNodeId;
	}
	
	public void setFromNodeId(String fromNodeId) {
		this.fromNodeId = fromNodeId;
		
		if (StringUtils.isNotEmpty(fromNodeId)) {
			AbstractNode an = DataService.getDataSet().getNodeMap().get(fromNodeId);
			
			this.setFromFabId(an.getFabId());
			
			if(an!=null) {
				Eqp eqp = DataService.getDataSet().getAllEqpMap().get(an.getEqpId());
			
				if(eqp != null) {
					this.setFromEqpId(		eqp.getId());
					this.setFromEqpGrpNm(	eqp.getEqpGrpNm());
					this.setFromEqpTyp(		eqp.getEqpType());
					this.setFromDetEqpTyp(	eqp.getDetEqpTyp());
				}
			}
		}
	}
	public long getPpCostSum() {
		return ppCostSum;
	}
	public void setPpCostSum(long ppCostSum) {
		this.ppCostSum = ppCostSum;
	}
	public long getPpCntSum() {
		return ppCntSum;
	}
	public void setPpCntSum(long ppCntSum) {
		this.ppCntSum = ppCntSum;
	}
	public String getFromFabId() {
		return fromFabId;
	}
	public void setFromFabId(String fromFabId) {
		this.fromFabId = fromFabId;
	}
	public String getFromEqpId() {
		return fromEqpId;
	}
	public void setFromEqpId(String fromEqpId) {
		this.fromEqpId = fromEqpId;
	}
	public String getToFabId() {
		return toFabId;
	}
	public void setToFabId(String toFabId) {
		this.toFabId = toFabId;
	}
	public EQP_TYPE getFromEqpTyp() {
		return fromEqpTyp;
	}
	public void setFromEqpTyp(EQP_TYPE fromEqpTyp) {
		this.fromEqpTyp = fromEqpTyp;
	}
	public String getFromDetEqpTyp() {
		return fromDetEqpTyp;
	}
	public void setFromDetEqpTyp(String fromDetEqpTyp) {
		this.fromDetEqpTyp = fromDetEqpTyp;
	}
	
	public String getFromEqpGrpNm() {
		return fromEqpGrpNm;
	}
	
	public void setFromEqpGrpNm(String fromEqpGrpNm) {
		this.fromEqpGrpNm = fromEqpGrpNm;
	}
	
	public EQP_TYPE getToEqpTyp() {
		return toEqpTyp;
	}
	
	public void setToEqpTyp(EQP_TYPE toEqpTyp) {
		this.toEqpTyp = toEqpTyp;
	}
	
	public String getToDetEqpTyp() {
		return toDetEqpTyp;
	}
	
	public void setToDetEqpTyp(String toDetEqpTyp) {
		this.toDetEqpTyp = toDetEqpTyp;
	}
	
	public String getToEqpGrpNm() {
		return toEqpGrpNm;
	}
	
	public void setToEqpGrpNm(String toEqpGrpNm) {
		this.toEqpGrpNm = toEqpGrpNm;
	}
	
	public long getNewFromToPredictedCost() {
		return newFromToPredictedCost;
	}
	
	public void setNewFromToPredictedCost(long newFromToPredictedCost) {
		this.newFromToPredictedCost = newFromToPredictedCost;
	}
	
	public EQP_TYPE getNewFromEqpTyp() {
		return newFromEqpTyp;
	}
	
	public void setNewFromEqpTyp(EQP_TYPE newFromEqpTyp) {
		this.newFromEqpTyp = newFromEqpTyp;
	}
	
	public String getNewFromEqpGrpNm() {
		return newFromEqpGrpNm;
	}
	
	public void setNewFromEqpGrpNm(String newFromEqpGrpNm) {
		this.newFromEqpGrpNm = newFromEqpGrpNm;
	}
	
	public String getNewFromDetEqpTyp() {
		return newFromDetEqpTyp;
	}
	
	public void setNewFromDetEqpTyp(String newFromDetEqpTyp) {
		this.newFromDetEqpTyp = newFromDetEqpTyp;
	}
	
	public String getNewFromFabId() {
		return newFromFabId;
	}
	
	public void setNewFromFabId(String newFromFabId) {
		this.newFromFabId = newFromFabId;
	}
	
	public ConcurrentLinkedDeque<String> getOrgPredictionRouteIdList() {
		if (this.orgPredictionRouteIdList == null) {
			this.orgPredictionRouteIdList = new ConcurrentLinkedDeque<String>();
		}
		
		return orgPredictionRouteIdList;
	}
	
	public void setOrgPredictionRouteIdList(ConcurrentLinkedDeque<String> orgPredictionRouteIdList) {
		this.orgPredictionRouteIdList = orgPredictionRouteIdList;
	}
	
	public String getLotId() {
		return lotId;
	}
	
	public void setLotId(String lotId) {
		this.lotId = lotId;
	}
	
	public String getCurrentEqpId() {
		return currentEqpId;
	}
	
	public void setCurrentEqpId(String currentEqpId) {
		this.currentEqpId = currentEqpId;
	}
	
	public String getCurrentLocId() {
		return currentLocId;
	}
	
	public void setCurrentLocId(String currentLocId) {
		this.currentLocId = currentLocId;
	}
	
	public String getStepNm() {
		return stepNm;
	}
	
	public void setStepNm(String stepNm) {
		this.stepNm = stepNm;
	}
	
	public String getStepTyp() {
		return stepTyp;
	}
	
	public void setStepTyp(String stepTyp) {
		this.stepTyp = stepTyp;
	}
	
	public String getMidStepTyp() {
		return midStepTyp;
	}
	
	public void setMidStepTyp(String midStepTyp) {
		this.midStepTyp = midStepTyp;
	}
	
	public String getDetStepTyp() {
		return detStepTyp;
	}

	public void setDetStepTyp(String detStepTyp) {
		this.detStepTyp = detStepTyp;
	}
}
