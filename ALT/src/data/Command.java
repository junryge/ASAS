//import org.apache.commons.lang3.StringUtils;

//import com.skhynix.smartatlas.data.RouteItem.ROUTE_ITEM_DET_TYPE;
//import com.skhynix.smartatlas.data.eq.Eqp;
import com.skhynix.smartatlas.data.eq.Eqp.EQP_TYPE;
//import com.skhynix.smartatlas.map.AbstractEdge.EDGE_TYPE;
//import com.skhynix.smartatlas.map.AbstractNode;
//import com.skhynix.smartatlas.map.edge.LongEdge;
//import com.skhynix.smartatlas.map.edge.RailEdge;
//import com.skhynix.smartatlas.util.DataService;

public class Command {
//	transient private boolean batchFlush = false;
	transient private boolean inserted = false; 
	private String id 					= "";
	private int commandSeq;
	private String jobId 				= "";
	private String carrierId 			= "";
	private String sourceNodeId 		= "";
	private String destNodeId 			= "";
	private String transEqpId 			= "";
	private String transUnitId 			= "";
	private String estimatedVhlId 		= "";
	private int priority 				= 50;
	private long sourceInstalledTime 	= -1;
	private long createTime				= -1;
	private long initTime				= -1;
	private long alternatingTime 		= -1;
	private long alternatedTime 		= -1;
	private long assignTime				= -1;
	private long sourceArrivedTime		= -1;	
	private long acquireStartTime 		= -1;
	private long acquireCmpltTime		= -1;
	private long departedTime			= -1;
	private long destArrivedTime		= -1;
	private long depositStartTime		= -1;
	private long depositCmpltTime		= -1;
	private long cmpltTime				= -1;
	private int assignCnt 				= 0;
	private int acquireTryCnt 			= 0;
	private int depositTryCnt 			= 0;
	private int replyCode 				= -1;
	private int resultCode 				= -1;
	private CMD_STATE state 			= CMD_STATE.NONE;
//	private CMD_STATE oldState = CMD_STATE.NONE;
	private ConcurrentLinkedDeque<String> routeIdList = new ConcurrentLinkedDeque<String>();
	
	private String lotId = "";
	
	private EQP_TYPE sourceEqpTyp 		= null;
	private String sourceDetEqpTyp 		= "";
	private String sourceEqpId 			= "";
	private String sourceEqpGrpNm 		= "";
	private String sourceAreaName 		= "";
	
	private EQP_TYPE destEqpTyp 		= null;
	private String destDetEqpTyp 		= "";
	private String destEqpId 			= "";
	private String destEqpGrpNm 		= "";
	private String destAreaName 		= "";
	
	private String stepId 				= "";
	private String stepNm 				= "";
	private String stepTyp 				= "";
	private String midStepTyp 			= "";
	private String detStepTyp 			= "";
	
	private long elapsed 				= 0;
	private long ranDistance 			= 0;
	
	transient private ConcurrentLinkedDeque<String> bjePath = new ConcurrentLinkedDeque<String>();

	private long stateTime 				= -1;
//	private long oldStateTime = -1;
	
	/**
	 * A constructor to set the batchFlush with the initialization to other fields.
	 * @param id
	 * @param carrierId
	 * @param jobId
	 * @param batchFlush
	 */
	public Command(final String id, final String carrierId, final String jobId, final boolean batchFlush, String transEqpId) {
		this.id = id;
		this.carrierId = carrierId;
		this.jobId = jobId;
		this.transEqpId = transEqpId;
		this.createTime = System.currentTimeMillis();
		
//		if (batchFlush)
//			this.enableBatchFlush();
//		else
//			this.disableBatchFlush();
//		
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, this);
//		
//		RedisPool.getJedisCluster().sadd("Command", this.id);
//		
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.CREATE, getClass().getName(), this));
	}
	
	public Command(String id, String carrierId, String jobId) {
		this.id = id;
		this.carrierId = carrierId;
		this.jobId = jobId;
		this.createTime = System.currentTimeMillis();
//		RedisPool.jset(this.id, this);
//		RedisPool.getJedisCluster().sadd("Command", this.id);
//		
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.CREATE, getClass().getName(), this));
	}

	public String getId() {
		return id;
	}

	public void setId(String id) {
		this.id = id;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, id, new Path(".id"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "id", this.id, this.id, new TypeToken<String>() {}.getType()));
	}

	public int getCommandSeq() {
		return commandSeq;
	}

	public void setCommandSeq(int commandSeq) {
		this.commandSeq = commandSeq;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, commandSeq, new Path(".commandSeq"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "commandSeq", this.id, new Integer(this.commandSeq), new TypeToken<Integer>() {}.getType()));
	}

	public String getJobId() {
		return jobId;
	}

	public void setJobId(String jobId) {
		this.jobId = jobId;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, jobId, new Path(".jobId"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "jobId", this.id, this.jobId, new TypeToken<String>() {}.getType()));
	}

	public String getCarrierId() {
		return carrierId;
	}

	public void setCarrierId(String carrierId) {
		this.carrierId = carrierId;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, carrierId, new Path(".carrierId"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "carrierId", this.id, this.carrierId, new TypeToken<String>() {}.getType()));
	}

	public String getSourceNodeId() {
		return sourceNodeId;
	}

	public void setSourceNodeId(String sourceNodeId) {
		this.sourceNodeId = sourceNodeId;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, sourceNodeId, new Path(".sourceNodeId"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "sourceNodeId", this.id, this.sourceNodeId, new TypeToken<String>() {}.getType()));
	}

	public String getDestNodeId() {
		return destNodeId;
	}

	public void setDestNodeId(String destNodeId) {
		this.destNodeId = destNodeId;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, destNodeId, new Path(".destNodeId"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "destNodeId", this.id, this.destNodeId, new TypeToken<String>() {}.getType()));
	}

	public String getTransUnitId() {
		return transUnitId;
	}

	public void setTransUnitId(String transUnitId) {
		this.transUnitId = transUnitId;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, transUnitId, new Path(".transUnitId"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "transUnitId", this.id, this.transUnitId, new TypeToken<String>() {}.getType()));
	}

	public int getPriority() {
		return priority;
	}

	public void setPriority(int priority) {
		this.priority = priority;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, priority, new Path(".priority"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "priority", this.id, new Integer(this.priority), new TypeToken<Integer>() {}.getType()));
	}

	public long getCreateTime() {
		return createTime;
	}

	public void setCreateTime(long createTime) {
		this.createTime = createTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, createTime, new Path(".createTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "createTime", this.id, new Long(this.createTime), new TypeToken<Long>() {}.getType()));
	}

	public long getInitTime() {
		return initTime;
	}

	public void setInitTime(long initTime) {
		this.initTime = initTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, initTime, new Path(".initTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "initTime", this.id, new Long(this.initTime), new TypeToken<Long>() {}.getType()));
	}

	public long getAssignTime() {
		return assignTime;
	}

	public void setAssignTime(long assignTime) {
		this.assignTime = assignTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, assignTime, new Path(".assignTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "assignTime", this.id, new Long(this.assignTime), new TypeToken<Long>() {}.getType()));
	}

	public long getSourceArrivedTime() {
		return sourceArrivedTime;
	}

	public void setSourceArrivedTime(long sourceArrivedTime) {
		this.sourceArrivedTime = sourceArrivedTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, sourceArrivedTime, new Path(".sourceArrivedTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "sourceArrivedTime", this.id, new Long(this.sourceArrivedTime), new TypeToken<Long>() {}.getType()));
	}

	public long getAcquireStartTime() {
		return acquireStartTime;
	}

	public void setAcquireStartTime(long acquireStartTime) {
		this.acquireStartTime = acquireStartTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, acquireStartTime, new Path(".acquireStartTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "acquireStartTime", this.id, new Long(this.acquireStartTime), new TypeToken<Long>() {}.getType()));
	}

	public long getAcquireCmpltTime() {
		return acquireCmpltTime;
	}

	public void setAcquireCmpltTime(long acquireCmpltTime) {
		this.acquireCmpltTime = acquireCmpltTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, acquireCmpltTime, new Path(".acquireCmpltTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "acquireCmpltTime", this.id, new Long(this.acquireCmpltTime), new TypeToken<Long>() {}.getType()));
	}

	public long getDepartedTime() {
		return departedTime;
	}

	public void setDepartedTime(long departedTime) {
		this.departedTime = departedTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, departedTime, new Path(".departedTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "departedTime", this.id, new Long(this.departedTime), new TypeToken<Long>() {}.getType()));
	}

	public long getDestArrivedTime() {
		return destArrivedTime;
	}

	public void setDestArrivedTime(long destArrivedTime) {
		this.destArrivedTime = destArrivedTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, destArrivedTime, new Path(".destArrivedTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "destArrivedTime", this.id, new Long(this.destArrivedTime), new TypeToken<Long>() {}.getType()));
	}

	public long getDepositStartTime() {
		return depositStartTime;
	}

//	public void setDepositStartTime(long depositStartTime) {
//		this.depositStartTime = depositStartTime;
//		for(String rid : routeIdList) {
//			RouteItem ri = DataService.getDataSet().getRouteItemMap().get(rid);
//			if(ri!=null && ri.isInserted() == false) {
//				ri.sendToLogpresso();
//			}
//		}
////		if (!this.batchFlush)
////			RedisPool.jset(this.id, depositStartTime, new Path(".depositStartTime"));
////		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "depositStartTime", this.id, new Long(this.depositStartTime), new TypeToken<Long>() {}.getType()));
//	}

	public long getDepositCmpltTime() {
		return depositCmpltTime;
	}

	public void setDepositCmpltTime(long depositCmpltTime) {
		this.depositCmpltTime = depositCmpltTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, depositCmpltTime, new Path(".depositCmpltTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "depositCmpltTime", this.id, new Long(this.depositCmpltTime), new TypeToken<Long>() {}.getType()));
	}

	public long getCmpltTime() {
		return cmpltTime;
	}

	public void setCmpltTime(long cmpltTime) {
		this.cmpltTime = cmpltTime;
		this.elapsed = this.cmpltTime - this.createTime; 
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, cmpltTime, new Path(".cmpltTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "cmpltTime", this.id, new Long(this.cmpltTime), new TypeToken<Long>() {}.getType()));
	}

	public int getAssignCnt() {
		return assignCnt;
	}

	public void setAssignCnt(int assignCnt) {
		this.assignCnt = assignCnt;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, assignCnt, new Path(".assignCnt"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "assignCnt", this.id, new Integer(this.assignCnt), new TypeToken<Integer>() {}.getType()));
	}

	public int getDepositTryCnt() {
		return depositTryCnt;
	}

	public void setDepositTryCnt(int depositTryCnt) {
		this.depositTryCnt = depositTryCnt;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, depositTryCnt, new Path(".depositTryCnt"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "depositTryCnt", this.id, new Integer(this.depositTryCnt), new TypeToken<Integer>() {}.getType()));
	}

	public int getReplyCode() {
		return replyCode;
	}

	public void setReplyCode(int replyCode) {
		this.replyCode = replyCode;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, replyCode, new Path(".replyCode"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "replyCode", this.id, new Integer(this.replyCode), new TypeToken<Integer>() {}.getType()));
	}

	public int getResultCode() {
		return resultCode;
	}

	public void setResultCode(int resultCode) {
		this.resultCode = resultCode;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, resultCode, new Path(".resultCode"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "resultCode", this.id, new Integer(this.resultCode), new TypeToken<Integer>() {}.getType()));
	}

	public CMD_STATE getState() {
		return state;
	}

	public void setState(CMD_STATE state) {
//		this.oldState = this.state;
//		this.oldStateTime = this.stateTime;
		this.state = state;
		this.stateTime = System.currentTimeMillis();
	}

	public ConcurrentLinkedDeque<String> getRouteIdList() {
		if(this.routeIdList == null)
			this.routeIdList = new ConcurrentLinkedDeque<String>();
		return routeIdList;
	}

	public void setRouteIdList(ConcurrentLinkedDeque<String> routeIdList) {
		this.routeIdList = routeIdList;
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "routeIdList", this.id, this.routeIdList, new TypeToken<ConcurrentLinkedDeque<String>>() {}.getType()));
//		try(Jedis j=RedisPool.getJedisClient()){
//			j.del(this.getId()+"#routeIdList");
//			j.rpush(this.getId()+"#routeIdList", routeIdList.toArray(new String[routeIdList.size()]));
//		}
		//RedisPool.jset(this.id, routeIdList, new Path(".routeIdList"));
	}
	
	public void addRouteIdList(ConcurrentLinkedDeque<String> routeIdList) {
		this.routeIdList.addAll(routeIdList);
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.ADD_COLLECTION_ALL, getClass().getName(), "routeIdList", this.id, routeIdList, new TypeToken<ConcurrentLinkedDeque<String>>() {}.getType()));
//		try(Jedis j=RedisPool.getJedisClient()){
//			j.rpush(this.getId()+"routeIdList", routeIdList.toArray(new String[routeIdList.size()]));
//		}
		//RedisPool.jset(this.id, routeIdList, new Path(".routeIdList"));
	}
	
	public void addRouteId(String routeId) {
		this.getRouteIdList().add(routeId);
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.ADD_COLLECTION_ITEM, getClass().getName(), "routeIdList", this.id, routeId, new TypeToken<String>() {}.getType()));
//		try(Jedis j=RedisPool.getJedisClient()){
//			j.rpush(this.getId()+"routeIdList", routeId);
//		}
		//RedisPool.jset(this.id, routeIdList, new Path(".routeIdList"));
	}

	public long getStateTime() {
		return stateTime;
	}

	public void setStateTime(long stateTime) {
		this.stateTime = stateTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, stateTime, new Path(".stateTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "stateTime", this.id, new Long(this.stateTime), new TypeToken<Long>() {}.getType()));
	}
	
	public int getAcquireTryCnt() {
		return acquireTryCnt;
	}

	public void setAcquireTryCnt(int acquireTryCnt) {
		this.acquireTryCnt = acquireTryCnt;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, acquireTryCnt, new Path(".acquireTryCnt"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "acquireTryCnt", this.id, new Integer(this.acquireTryCnt), new TypeToken<Integer>() {}.getType()));
	}
	
	/**
	 * Enables the batch flush for the Redis.
	 */
	public void enableBatchFlush() {
//		this.batchFlush = true;
	}
	
	/**
	 * Disables the batch flush for the Redis.
	 */
	public void disableBatchFlush() {
//		this.batchFlush = false;
	}
	
	/**
	 * Flush this object into the Redis.
	 */
	public void flush() {
//		RedisPool.jset(this.id, this);
	}

	public enum CMD_STATE{
		NONE("NONE"),
		REQUESTED("REQUESTED"), // 명령내린 상태
		QUEUED("QUEUED"), // Reply 받은 상태
		ACQMOVING("ACQMOVING"), // 시작한 상태/VHL Assign된 상태
		ACQUIRING("ACQUIRING"), // 들어올리는 중
		DESTMOVING("DESTMOVING"), // 목적지로 이동중
		DEPOSITING("DEPOSITING"),
		OUTPORTMOVING("OUTPORTMOVING"), // 스토커 출고 포트에서 이동중.
		COMPLETED("COMPLETED"), 
		CANCELING("CANCELING"),
		CANCELED("CANCELED"),
		ABORTING("ABORTING"),
		ABORTED("ABORTED"),
		UPDATING("UPDATING"),		
		PAUSED("PAUSED"),
		STOREDALT("STOREDALT");
		private final String state;
		CMD_STATE(String state){
			this.state = state;
		}
		public String getState(){
			return this.state;
		}
	}

	public long getAlternatingTime() {
		return alternatingTime;
	}

	public void setAlternatingTime(long alternatingTime) {		
		this.alternatingTime = alternatingTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, alternatingTime, new Path(".alternatingTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "alternatingTime", this.id, new Long(this.alternatingTime), new TypeToken<Long>() {}.getType()));
	}

	public long getAlternatedTime() {
		return alternatedTime;
	}

	public void setAlternatedTime(long alternatedTime) {
		this.alternatedTime = alternatedTime;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, alternatedTime, new Path(".alternatedTime"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "alternatedTime", this.id, new Long(this.alternatedTime), new TypeToken<Long>() {}.getType()));
	}

	public String getTransEqpId() {
		return transEqpId;
	}

	public void setTransEqpId(String transEqpId) {
		this.transEqpId = transEqpId;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, transEqpId, new Path(".transEqpId"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "transEqpId", this.id, this.transEqpId, new TypeToken<String>() {}.getType()));
	}

	public String getEstimatedVhlId() {
		return estimatedVhlId;
	}

	public void setEstimatedVhlId(String estimatedVhlId) {
		this.estimatedVhlId = estimatedVhlId;
//		AtlasCommPubSub.getInstance().publish(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "estimatedVhlId", this.id, this.estimatedVhlId, new TypeToken<String>() {}.getType()));
	}

	public boolean isInserted() {
		return inserted;
	}

	public void setInserted(boolean inserted) {		
		this.inserted = inserted;
	}
	
//	public void fillOhtDetailHistory() {
//		if(StringUtils.isNotEmpty(this.transUnitId) && this.transUnitId.contains(DataSet.VHL_PREFIX)) {
//			if(StringUtils.isNotEmpty(this.sourceNodeId)) {
//				AbstractNode sourceNode	= (AbstractNode)DataService.getDataSet().getNodeMap().get(this.sourceNodeId);
//				Eqp eqp 				= DataService.getDataSet().getAllEqpMap().get(sourceNode.getEqpId());
//				
//				if (eqp != null) {
//					this.setSourceEqpId(eqp.getId());
//					this.setSourceEqpGrpNm(eqp.getEqpGrpNm());
//					this.setSourceEqpTyp(eqp.getEqpType());
//					this.setSourceDetEqpTyp(eqp.getDetEqpTyp());
//				}
//				
//			}
//			if(StringUtils.isNotEmpty(this.destNodeId)) {
//				AbstractNode destNode = (AbstractNode)DataService.getDataSet().getNodeMap().get(this.destNodeId);
//				Eqp eqp = DataService.getDataSet().getAllEqpMap().get(destNode.getEqpId());
//				if(eqp!=null) {
//					this.setDestEqpId(eqp.getId());
//					this.setDestEqpGrpNm(eqp.getEqpGrpNm());
//					this.setDestEqpTyp(eqp.getEqpType());
//					this.setDestDetEqpTyp(eqp.getDetEqpTyp());
//				}
//			}
//			Job j = DataService.getDataSet().getJobMap().get(this.jobId);
//			if(j!=null) {
//				this.lotId = j.getLotId();
//				this.stepId = j.getStepId();
//				this.stepNm = j.getStepNm();
//				this.stepTyp = j.getStepTyp();
//				this.midStepTyp = j.getMidStepTyp();
//				this.detStepTyp = j.getDetStepTyp();
//			}
//			long distance = 0;
//			String lastBjeId = "";
//			for(String routeId : this.getRouteIdList()) {
//				RouteItem ri = DataService.getDataSet().getRouteItemMap().get(routeId);
//				if(ri!=null && ri.getRouteItemDetType() == ROUTE_ITEM_DET_TYPE.DEPOSIT) {
//					LongEdge le = DataService.getDataSet().getLongEdgeMap().get(ri.getEdgeId());
//					distance+=ri.getLength();
//					if(le != null && le.getFirstEdgeType() == EDGE_TYPE.RAILEDGE) {
//						distance += le.getLength();
//						RailEdge re = (RailEdge)le.getFirstEdge();
//						if(lastBjeId.equals(re.getBranchJoinEdgeId()) == false) {
//							lastBjeId = re.getBranchJoinEdgeId();
//							this.bjePath.add(lastBjeId);
//						}
//						if(StringUtils.isEmpty(this.sourceAreaName)) {
//							this.sourceAreaName = re.getAreaName();
//						}
//						this.destAreaName = re.getAreaName();
//					}
//				}
//			}
//			this.ranDistance = distance;
//		}
//	}

	public long getSourceInstalledTime() {
		return sourceInstalledTime;
	}

	public void setSourceInstalledTime(long sourceInstalledTime) {
		this.sourceInstalledTime = sourceInstalledTime;
	}

	public EQP_TYPE getSourceEqpTyp() {
		return sourceEqpTyp;
	}

	public void setSourceEqpTyp(EQP_TYPE sourceEqpTyp) {
		this.sourceEqpTyp = sourceEqpTyp;
	}

	public String getSourceDetEqpTyp() {
		return sourceDetEqpTyp;
	}

	public void setSourceDetEqpTyp(String sourceDetEqpTyp) {
		this.sourceDetEqpTyp = sourceDetEqpTyp;
	}

	public String getSourceEqpId() {
		return sourceEqpId;
	}

	public void setSourceEqpId(String sourceEqpId) {
		this.sourceEqpId = sourceEqpId;
	}

	public String getSourceEqpGrpNm() {
		return sourceEqpGrpNm;
	}

	public void setSourceEqpGrpNm(String sourceEqpGrpNm) {
		this.sourceEqpGrpNm = sourceEqpGrpNm;
	}

	public String getSourceAreaName() {
		return sourceAreaName;
	}

	public void setSourceAreaName(String sourceAreaName) {
		this.sourceAreaName = sourceAreaName;
	}

	public EQP_TYPE getDestEqpTyp() {
		return destEqpTyp;
	}

	public void setDestEqpTyp(EQP_TYPE destEqpTyp) {
		this.destEqpTyp = destEqpTyp;
	}

	public String getDestDetEqpTyp() {
		return destDetEqpTyp;
	}

	public void setDestDetEqpTyp(String destDetEqpTyp) {
		this.destDetEqpTyp = destDetEqpTyp;
	}

	public String getDestEqpId() {
		return destEqpId;
	}

	public void setDestEqpId(String destEqpId) {
		this.destEqpId = destEqpId;
	}

	public String getDestEqpGrpNm() {
		return destEqpGrpNm;
	}

	public void setDestEqpGrpNm(String destEqpGrpNm) {
		this.destEqpGrpNm = destEqpGrpNm;
	}

	public String getDestAreaName() {
		return destAreaName;
	}

	public void setDestAreaName(String destAreaName) {
		this.destAreaName = destAreaName;
	}

	public String getStepId() {
		return stepId;
	}

	public void setStepId(String stepId) {
		this.stepId = stepId;
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

	public long getElapsed() {
		return elapsed;
	}

	public void setElapsed(long elapsed) {
		this.elapsed = elapsed;
	}

	public long getRanDistance() {
		return ranDistance;
	}

	public void setRanDistance(long ranDistance) {
		this.ranDistance = ranDistance;
	}

	public ConcurrentLinkedDeque<String> getBjePath() {
		if(bjePath==null)
			bjePath = new ConcurrentLinkedDeque<>();
		return bjePath;
	}

	public void setBjePath(ConcurrentLinkedDeque<String> bjePath) {
		this.bjePath = bjePath;
	}

	public String getLotId() {
		return lotId;
	}

	public void setLotId(String lotId) {
		this.lotId = lotId;
	}

	
}
