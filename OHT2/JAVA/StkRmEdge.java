public class StkRmEdge extends AbstractEdge {
	private transient Logger logger = LoggerFactory.getLogger(getClass());
	
	private Logger getLogger() {
		if (logger == null) {
			logger = LoggerFactory.getLogger(getClass());
		}
		
		return logger;
	}
	
	private String eqpId 							= "";
	private long avgTransferCost 					= 7000;
	private boolean isFromRm 						= false;
	private boolean isBridgeRmEdge 					= false;
	private Set<String> currentMovingCarrierIds 	= new HashSet<String>();
	private transient Stocker.STK_TYPE stkType 		= null;
	
	public boolean changed(StkRmEdge oe) {		
		if (this.isFromRm != oe.isFromRm) {
			return true;		
		}
		
		return super.changed(oe);
	}

	/**
	 * A constructor to set the batchFlush with the initialization to other fields.
	 * @param fabId
	 * @param id
	 * @param fromNodeId
	 * @param toNodeId
	 * @param avgTransferCost
	 * @param batchFlush
	 */
	public StkRmEdge(
						final String fabId, 
						final String id, 
						final String eqpId,
						final String fromNodeId, 
						final String toNodeId,
						final long avgTransferCost,
						final boolean batchFlush, 
						final double length, 
						boolean isFromRm,
						boolean isBridgeRmEdge, 
						boolean isUpdate
	) {
		super(fabId, id, fromNodeId, toNodeId, EDGE_TYPE.STKRMEDGE, length, isUpdate);
		
		this.avgTransferCost 	= avgTransferCost;
		this.eqpId 				= eqpId;
		this.isFromRm 			= isFromRm;
		this.isBridgeRmEdge 	= isBridgeRmEdge;
//		if(isUpdate) return;
//		if (batchFlush)
//			this.enableBatchFlush();
//		else
//			this.disableBatchFlush();
//		
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, this);
//		
//		RedisPool.getJedisCluster().sadd("StkRmEdge", this.id);
//
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.CREATE, getClass().getName(), this));
	}
	
	public Stocker.STK_TYPE getStockerType(){
		if (stkType == null) {
			AbstractNode an = null;
			if(isFromRm) {
				an = DataService.getDataSet().getNodeMap().get(fromNodeId);
			} else {
				an = DataService.getDataSet().getNodeMap().get(toNodeId);
			}
			
			Stocker stk = DataService.getDataSet().getStockerMap().get(an.getEqpId());
			
			if (stk == null) {
				getLogger().warn("this stk({}) is not registered on stockermap. rmedgeid : {}", an.getEqpId(), this.id);
			}
			
			stkType = stk.getStkType();			
		}
		
		return stkType;
	}
	
//	public StkRmEdge(String fabId, String id,
//			String fromNodeId, 
//			String toNodeId,
//			long avgTransferCost
//			) {
//		super(fabId, id, fromNodeId, toNodeId, EDGE_TYPE.STKRMEDGE);
//		this.avgTransferCost = avgTransferCost;
//		RedisPool.jset(this.id, this);
//		Jedis j = RedisPool.getJedisClient();
//		j.sadd("StkRmEdge", this.id);
//		j.close();
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.CREATE, getClass().getName(), this));
//	}

	@Override
	public long getCost(String carrierId) {
		if(isFromRm == false) {
			AbstractNode an = DataService.getDataSet().getNodeMap().get(getFromNodeId());
			if(an instanceof StkPortNode) {
				return avgTransferCost + ((StkPortNode)an).getAvgRemovalIntervalT();
			}
		}else {
			AbstractNode an = DataService.getDataSet().getNodeMap().get(getToNodeId());
			if(an instanceof StkPortNode) {
				return avgTransferCost + ((StkPortNode)an).getAvgRemovalIntervalT();
			}
		}
		return avgTransferCost;
	}
	
	@Override
	public int getFutureTransCount(String carrierId, long after) {
		return 0;
	}
	
	public long getFutureCost(String carrierId, long after) {
		return 0;
	}
	
	public void addCost(long newCost) {
		long result = (long)((avgTransferCost * PredictionPara.getInstance().getLastHisWeight()) + (1.0-PredictionPara.getInstance().getLastHisWeight()) * newCost);
		if(result > 100000) {
			setAvgTransferCost(7000);
		}else {
			setAvgTransferCost(result);
		}
	}

	public double getAvgTransferCost() {
		return avgTransferCost;
	}

	public void setAvgTransferCost(long avgTransferCost) {
		this.avgTransferCost = avgTransferCost;
//		if(isUpdate) return;
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "avgTransferCost", this.id, new Long(this.avgTransferCost), new TypeToken<Long>() {}.getType()));
		//RedisPool.jset(this.id, avgTransferCost, new Path(".avgTransferCost"));
	}

	@Override
	public String toString() {
		JsonToStringBuilder builder = new JsonToStringBuilder(this);
		builder.append("class", this.getClass().getSimpleName());
		builder.append("id", id);
		builder.append("fromNodeId", fromNodeId);
		builder.append("toNodeId", toNodeId);
		builder.append("avgTransferCost", avgTransferCost);
		builder.append("areaName", areaName);
		builder.append("bayName", bayName);
		return builder.toString();
	}

	public boolean isFromRm() {
		return isFromRm;
	}

	public void setFromRm(boolean isFromRm) {
		this.isFromRm = isFromRm;
//		if(isUpdate) return;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, isFromRm, new Path(".isFromRm"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "isFromRm", this.id, new Boolean(this.isFromRm), new TypeToken<Boolean>() {}.getType()));
	}

	public Set<String> getCurrentMovingCarrierIds() {
		if(currentMovingCarrierIds == null) {
			currentMovingCarrierIds = new HashSet<String>();
		}
		return currentMovingCarrierIds;
	}
	
	public void addCurrentMovingCarrierId(String carrierId) {
		if(currentMovingCarrierIds == null) {
			currentMovingCarrierIds = new HashSet<String>();
		}
		currentMovingCarrierIds.add(carrierId);
		setCurrentMovingCarrierIds(currentMovingCarrierIds);
	}
	
	public void removeCurrentMovingCarrierId(String carrierId) {
		if(currentMovingCarrierIds == null) {
			currentMovingCarrierIds = new HashSet<String>();
		}
		currentMovingCarrierIds.remove(carrierId);
		setCurrentMovingCarrierIds(currentMovingCarrierIds);
	}

	public void setCurrentMovingCarrierIds(Set<String> currentMovingCarrierIds) {
		this.currentMovingCarrierIds = currentMovingCarrierIds;
//		if(isUpdate) return;
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "currentMovingCarrierIds", this.id, this.currentMovingCarrierIds, new TypeToken<Set<String>>() {}.getType()));
	}
	
	@Override
	public boolean isAvailable() {
		return getFromNode().isAvailable() && getToNode().isAvailable();
	}

	@Override
	public boolean isAvailable(PROCESS_TYPE carrierType) {
		return isAvailable();
	}

	public String getEqpId() {
		return eqpId;
	}

	public void setEqpId(String eqpId) {
		this.eqpId = eqpId;
	}

	public boolean isBridgeRmEdge() {
		return isBridgeRmEdge;
	}

	public void setBridgeRmEdge(boolean isBridgeRmEdge) {
		this.isBridgeRmEdge = isBridgeRmEdge;
	}

}

###Station.java

public class Station {
	transient protected boolean batchFlush 						= false;
	private String fabId 										= "";
	private String id 											= "";
	private String mcpName 										= "";
	private String railNodeId 									= "";	
	private String portId 										= "";
	private int carryType 										= 1; // 0/1/5/9/A
	private String areaName 									= "";	// rail edge와 동일한 값으로 묶임
	private String bayName 										= "";
	private String areaId 										= "";
	private String bayId 										= "";
	private double offset;
	private String railEdgeId;
	private STATION_TYPE stationType;
	private String acquireTransferEdgeId 						= "";
	private String depositTransferEdgeId 						= "";
	private long avgAssignCost;
	private double avgReassignCount;
	private int reassignCount;
	private long firstAssignCost;
	private long receivedTime;
	private double lastAvgReassignCount;
	private long lastAvgAssignCost;
	private long lastReceivedTime;
	private double drawX										= 0; 
	private double drawY 										= 0;
	private boolean isAvailable 								= true;
	private boolean lastIsAvailable 							= true;
	private String carrierId 									= "";
	private String outGoingCmdId 								= "";
	private ConcurrentHashMap<String,Long> incommingCmdIdMap 	= new ConcurrentHashMap<String, Long>();
	private STATION_CARRIER_STATE carrierState 					= STATION_CARRIER_STATE.UNKNOWN;
	private String destPortId 									= "";
	private String assignedVhl 									= "";
	private String lastCarrierId 								= "";
	private STATION_CARRIER_STATE lastCarrierState 				= STATION_CARRIER_STATE.UNKNOWN;
	private String lastDestPortId 								="";
	private String lastAssignedVhl 								= "";
	private transient boolean isUpdate 							= false;
	// +
	private int hidId 											= -1;
	
	/**
	 * A constructor to set the batchFlush with the initialization to other fields.
	 * @param fabId
	 * @param id
	 * @param railNodeId
	 * @param carryType
	 * @param offset
	 * @param railEdgeId
	 * @param stationType
	 * @param portId
	 * @param drawX
	 * @param drawY
	 * @param batchFlush
	 */
	public Station(
					final String fabId, 
					final String id, 
					final String mcpName,
					final String railNodeId,
					final int carryType, // 0/1/5/9/A
					final double offset,
					final String railEdgeId,
					final STATION_TYPE stationType,
					final String portId,
					final double drawX,
					final double drawY,
					final boolean batchFlush, 
					boolean isUpdate
	) {
		this.isUpdate 	= isUpdate;
		this.mcpName 	= mcpName;
		
		this.init(fabId, id, railNodeId, carryType, offset, railEdgeId, stationType, portId, drawX, drawY);
	}

	public Station(
					String fabId, 
					String id, 
					String mcpName,
					String railNodeId,
					int carryType, // 0/1/5/9/A
					double offset,
					String railEdgeId,
					STATION_TYPE stationType,
					String portId,
					double drawX,
					double drawY,
					boolean isUpdate
	){
		this.mcpName 	= mcpName;
		this.isUpdate 	= isUpdate;
		
		this.init(fabId, id, railNodeId, carryType, offset, railEdgeId, stationType, portId, drawX, drawY);
	}

	/**
	 * A constructor to set the batchFlush with the initialization to other fields.
	 * @param fabId
	 * @param id
	 * @param railNodeId
	 * @param carryType
	 * @param offset
	 * @param railEdgeId
	 * @param stationType
	 * @param portId
	 * @param drawX
	 * @param drawY
	 */
	private void init(
						final String fabId, 
						final String id,
						final String railNodeId,
						final int carryType, // 0/1/5/9/A
						final double offset,
						final String railEdgeId,
						final STATION_TYPE stationType,
						final String portId,
						final double drawX,
						final double drawY
	) {
		this.fabId 					= fabId;
		this.id 					= id;
		this.railNodeId 			= railNodeId;
		this.carryType 				= carryType;
		this.offset 				= offset;
		this.railEdgeId 			= railEdgeId;
		this.stationType 			= stationType;
		this.avgAssignCost 			= 24000;
		this.avgReassignCount 		= 0;
		this.reassignCount 			= 0;
		this.firstAssignCost 		= 24000;
		this.receivedTime 			= -1;
		this.lastAvgReassignCount 	= 0;
		this.lastAvgAssignCost 		= 24000;
		this.lastReceivedTime 		= -1;
		this.portId 				= portId;
		this.drawX 					= drawX;
		this.drawY 					= drawY;
	}

	public int getCarryType() {
		return carryType;
	}

	public void setCarryType(int carryType) {
		this.carryType = carryType;
	}

	public double getOffset() {
		return offset;
	}

	public void setOffset(double offset) {
		this.offset = offset;
	}

	public String getRailEdgeId() {
		return railEdgeId;
	}

	public void setRailEdgeId(String railEdgeId) {
		this.railEdgeId = railEdgeId;
	}

	public String getId() {
		return id;
	}

	public STATION_TYPE getStationType() {
		return stationType;
	}

	public void setStationType(STATION_TYPE stationType) {
		this.stationType = stationType;
	}

	public long getAvgAssignCost() {
		return avgAssignCost;
	}

	public void setAvgAssignCost(long avgAssignCost) {
		this.avgAssignCost = avgAssignCost;
	}

	public double getAvgReassignCount() {
		return avgReassignCount;
	}

	public void setAvgReassignCount(double avgReassignCount) {
		this.avgReassignCount = avgReassignCount;
	}

	public int getReassignCount() {
		return reassignCount;
	}

	public void setReassignCount(int reassignCount) {
		this.reassignCount = reassignCount;
	}

	public long getFirstAssignCost() {
		return firstAssignCost;
	}

	public void setFirstAssignCost(long firstAssignCost) {
		this.firstAssignCost = firstAssignCost;
	}

	public long getReceivedTime() {
		return receivedTime;
	}

	public void setReceivedTime(long receivedTime) {
		this.receivedTime = receivedTime;
	}

	public double getLastAvgReassignCount() {
		return lastAvgReassignCount;
	}

	public void setLastAvgReassignCount(double lastAvgReassignCount) {
		this.lastAvgReassignCount = lastAvgReassignCount;
	}

	public long getLastAvgAssignCost() {
		return lastAvgAssignCost;
	}

	public void setLastAvgAssignCost(long lastAvgAssignCost) {
		this.lastAvgAssignCost = lastAvgAssignCost;
	}

	public long getLastReceivedTime() {
		return lastReceivedTime;
	}

	public void setLastReceivedTime(long lastReceivedTime) {
		this.lastReceivedTime = lastReceivedTime;
	}
	
	public String getRailNodeId() {
		return railNodeId;
	}
	
	public void setRailNodeId(String railNodeId) {
		this.railNodeId = railNodeId;
	}
	
	public String getPortId() {
		return portId;
	}
	
	public void setPortId(String portId) {
		this.portId = portId;
	}

	public String toString() {
		return JsonUtil.convertJSON(this);
	}
	
	public double getDrawX() {
		return drawX;
	}
	
	public void setDrawX(double drawX) {
		this.drawX = drawX;
	}
	
	public double getDrawY() {
		return drawY;
	}
	
	public void setDrawY(double drawY) {
		this.drawY = drawY;
	}
	
	public String getAreaName() {
		return areaName;
	}
	
	public void setAreaName(String areaName) {
		this.areaName = areaName;
	}
	
	public String getBayName() {
		return bayName;
	}
	
	public void setBayName(String bayName) {
		this.bayName = bayName;
	}
	
	public void setId(String id) {
		this.id = id;
	}
	
	public boolean isAvailable() {
		return isAvailable;
	}
	
	public void setAvailable(boolean isAvailable) {
		this.isAvailable = isAvailable;
	}
	
	public enum STATION_CARRIER_STATE{
		UNKNOWN("0"), ASSIGN_WAIT("1"), ASSIGNED("2"), NO_CARRIER("3");
	
		private final String code;
		
		STATION_CARRIER_STATE(String code){
			this.code = code;
		}
	
		public String code() {
			return this.code;
		}
	}
	
	public String getCarrierId() {
		return carrierId;
	}
	
	public void setCarrierId(String carrierId) {
		this.carrierId = carrierId;
	}
	
	public STATION_CARRIER_STATE getCarrierState() {
		return carrierState;
	}
	
	public void setCarrierState(STATION_CARRIER_STATE carrierState) {
		this.carrierState = carrierState;
	}
	
	public String getDestPortId() {
		return destPortId;
	}
	
	public void setDestPortId(String destPortId) {
		this.destPortId = destPortId;
	}
	
	public String getAssignedVhl() {
		return assignedVhl;
	}
	
	public void setAssignedVhl(String assignedVhl) {
		this.assignedVhl = assignedVhl;
	}
	
	public String getLastCarrierId() {
		return lastCarrierId;
	}
	
	public void setLastCarrierId(String lastCarrierId) {
		this.lastCarrierId = lastCarrierId;
	}

	public STATION_CARRIER_STATE getLastCarrierState() {
		return lastCarrierState;
	}
	
	public void setLastCarrierState(STATION_CARRIER_STATE lastCarrierState) {
		this.lastCarrierState = lastCarrierState;
	}
	
	public String getLastDestPortId() {
		return lastDestPortId;
	}
	
	public void setLastDestPortId(String lastDestPortId) {
		this.lastDestPortId = lastDestPortId;
	}

	public String getLastAssignedVhl() {
		return lastAssignedVhl;
	}
	
	public void setLastAssignedVhl(String lastAssignedVhl) {
		this.lastAssignedVhl = lastAssignedVhl;
	}

	public boolean isLastIsAvailable() {
		return lastIsAvailable;
	}
	
	public void setLastIsAvailable(boolean lastIsAvailable) {
		this.lastIsAvailable = lastIsAvailable;
	}


	public String getFabId() {
		return fabId;
	}


	public void setFabId(String fabId) {
		this.fabId = fabId;
	}

	/**
	 * Enables the batch flush for the Redis.
	 */
	public void enableBatchFlush() {
		this.batchFlush = true;
	}
	
	/**
	 * Disables the batch flush for the Redis.
	 */
	public void disableBatchFlush() {
		this.batchFlush = false;
	}
	
	/**
	 * Flush this object into the Redis.
	 */
	public void flush() {
		//	...
	}

	public String getAcquireTransferEdgeId() {
		return acquireTransferEdgeId;
	}

	public void setAcquireTransferEdgeId(String acquireTransferEdgeId) {
		this.acquireTransferEdgeId = acquireTransferEdgeId;
	}

	public String getDepositTransferEdgeId() {
		return depositTransferEdgeId;
	}

	public void setDepositTransferEdgeId(String depositTransferEdgeId) {
		this.depositTransferEdgeId = depositTransferEdgeId;
	}

	public boolean isUpdate() {
		return isUpdate;
	}

	public void setUpdate(boolean isUpdate) {
		this.isUpdate = isUpdate;
	}

	public String getMcpName() {
		return mcpName;
	}

	public void setMcpName(String mcpName) {
		this.mcpName = mcpName;
	}
	
	public String getAreaId() {
		return areaId;
	}

	public void setAreaId(String areaId) {
		this.areaId = areaId;
	}

	public String getBayId() {
		return bayId;
	}

	public void setBayId(String bayId) {
		this.bayId = bayId;
	}

	public String getOutGoingCmdId() {		
		return outGoingCmdId;
	}

	public void setOutGoingCmdId(String outGoingCmdId) {
		this.outGoingCmdId = outGoingCmdId;
	}

	public ConcurrentHashMap<String, Long> getIncommingCmdIdMap() {
		if(incommingCmdIdMap == null)
			this.incommingCmdIdMap = new ConcurrentHashMap<String, Long>();
		return incommingCmdIdMap;
	}

	public void setIncommingCmdIdMap(ConcurrentHashMap<String, Long> incommingCmdIdMap) {
		this.incommingCmdIdMap = incommingCmdIdMap;
	}

	public void addIncommingCmdId(String cmdId) {
		if (incommingCmdIdMap == null) {
			this.incommingCmdIdMap = new ConcurrentHashMap<String, Long>();
		}
		
		if (incommingCmdIdMap.containsKey(cmdId)) {
			return;
		}
		
		long now = System.currentTimeMillis();
		
		this.incommingCmdIdMap.put(cmdId, now);
	}
	
	public void removeIncommingCmdId(String cmdId) {
		if (incommingCmdIdMap == null) {
			this.incommingCmdIdMap = new ConcurrentHashMap<String, Long>();
		}
		
		if (cmdId == null) {
			return;
		}
	}
	
	public int getHidId () {
		return hidId;
	}
	
	public void setHidId (int hidId) {
		if (hidId < -1) {
			this.hidId = -1;
		}
		
		this.hidId = hidId;
	}
}