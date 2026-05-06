public class TransferEdge extends AbstractEdge {
	private transient Logger logger		= LoggerFactory.getLogger(getClass());
	private String fromStation 			= "";
	private String toStation 			= "";
	private long avgTransferCost 		= 7000l;
	private long avgVhlCallCost 		= 20000l;
	private boolean isAcqEdge 			= false;
	private String assignedVhlCarrierId	= "";
	
	public boolean changed(TransferEdge oe) {
		if (!this.fromStation.equals(oe.fromStation)) {
			return true;
		}
		
		if (!this.toStation.equals(oe.toStation)) {
			return true;
		}
		
		if (this.isAcqEdge != oe.isAcqEdge ) {
			return true;
		}
		
		return super.changed(oe);
	}
	
	private Logger getLogger() {
		if(logger == null) {
			logger = LoggerFactory.getLogger(getClass());
		}

		return logger;
	}
	
	/**
	 * A constructor to set the batchFlush with the initialization to other fields.
	 * @param fabId
	 * @param id
	 * @param fromNodeId
	 * @param toNodeId
	 * @param fromStation
	 * @param toStation
	 * @param avgTransferCost
	 * @param isAcqEdge
	 * @param batchFlush
	 */
	public TransferEdge(final String fabId, String id, 
						final String fromNodeId, 
						final String toNodeId,
						final String fromStation,
						final String toStation,
						final long avgTransferCost,
						final boolean isAcqEdge,
						final boolean batchFlush,
						final double length,
						boolean isUpdate
						) {		
		
		super(
				fabId,
				id,
				fromNodeId,
				toNodeId,
				isAcqEdge ? EDGE_TYPE.TRANSEDGE_ACQUIRE : EDGE_TYPE.TRANSEDGE_DEPOSIT,
				length,
				isUpdate
		);

		this.init(fromStation, toStation, avgTransferCost, isAcqEdge);
	}
	
	public TransferEdge(
			String fabId,
			String id,
			String fromNodeId, 
			String toNodeId,
			String fromStation,
			String toStation,
			long avgTransferCost,
			boolean isAcqEdge,
			double length,
			boolean isUpdate
	) {
		super(
				fabId,
				id,
				fromNodeId,
				toNodeId, isAcqEdge?EDGE_TYPE.TRANSEDGE_ACQUIRE:EDGE_TYPE.TRANSEDGE_DEPOSIT, length, isUpdate);
		
		this.init(fromStation, toStation, avgTransferCost, isAcqEdge);
	}

	/**
	 * The common function to initialize the local field of this class.
	 * @param fromStation
	 * @param toStation
	 * @param avgTransferCost
	 * @param isAcqEdge
	 */
	public void init(final String fromStation,
					 final String toStation,
					 final long avgTransferCost,
					 final boolean isAcqEdge) {
		this.fromStation=fromStation;
		this.toStation=toStation;
		this.avgTransferCost = avgTransferCost;
		this.isAcqEdge = isAcqEdge;
		if(isAcqEdge == false) {
			this.avgVhlCallCost = 0;
			if(fromNodeId.contains(":CPN:") || toNodeId.contains(":CPN:")) {
				this.avgTransferCost = 12000l;
			}
		}else if(fromNodeId.contains(":CPN:") || toNodeId.contains(":CPN:")) {
			this.avgVhlCallCost = 60000l; // Conveyor -> OHT -> Conveyor 경로 억제		
			this.avgTransferCost = 15000l;
		}
	}
	
	@Override
	public long getCost(String carrierId) {
		
		return avgTransferCost;
	}

	public String getFromStation() {
		return fromStation;
	}

	public String getToStation() {
		return toStation;
	}

	public long getAvgTransferCost() {
		return avgTransferCost;
	}
	
	public void setAvgTransferCost(long avgTransferCost) {
		this.avgTransferCost = avgTransferCost;
//		if(isUpdate) return;
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "avgTransferCost", this.id, new Long(this.avgTransferCost), new TypeToken<Long>() {}.getType()));
		//RedisPool.jset(this.id, avgTransferCost, new Path(".avgTransferCost"));
	}
	
	public void addAvgTransferCost(long newCost) {
		long result = (long)((avgTransferCost * PredictionPara.getInstance().getLastHisWeight()) + (1.0-PredictionPara.getInstance().getLastHisWeight()) * newCost);
		this.setAvgTransferCost(result);
		//RedisPool.jset(this.id, this.avgTransferCost, new Path(".avgTransferCost"));
	}



	public void setFromStation(String fromStation) {
		this.fromStation = fromStation;
//		if(isUpdate) return;
//		RedisPool.jset(this.id, fromStation, new Path(".fromStation"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "fromStation", this.id, this.fromStation, new TypeToken<String>() {}.getType()));
	}



	public void setToStation(String toStation) {
		this.toStation = toStation;
//		if(isUpdate) return;
//		RedisPool.jset(this.id, toStation, new Path(".toStation"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "toStation", this.id, this.toStation, new TypeToken<String>() {}.getType()));
	}



	public String toJsonString() {
		return JsonUtil.convertJSON(this);
	}

	public boolean isAcqEdge() {
		return isAcqEdge;
	}

	public void setAcqEdge(boolean isAcqEdge) {
		this.isAcqEdge = isAcqEdge;
//		if(isUpdate) return;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, isAcqEdge, new Path(".isAcqEdge"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "isAcqEdge", this.id, new Boolean(this.isAcqEdge), new TypeToken<Boolean>() {}.getType()));
	}

	public String getAssignedVhlCarrierId() {
		return assignedVhlCarrierId;
	}

	public void setAssignedVhlCarrierId(String assignedVhlCarrierId) {
		this.assignedVhlCarrierId = assignedVhlCarrierId;
//		if(isUpdate) return;
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "assignedVhlCarrierId", this.id, this.assignedVhlCarrierId, new TypeToken<String>() {}.getType()));
	}
	
	@Override
	public boolean isAvailable() {
		return getFromNode().isAvailable() && getToNode().isAvailable();
	}

	public long getAvgVhlCallCost() {
		return avgVhlCallCost;
	}

	public void setAvgVhlCallCost(long avgVhlCallCost) {
		this.avgVhlCallCost = avgVhlCallCost;
//		if(isUpdate) return;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, avgVhlCallCost, new Path(".avgVhlCallCost"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "avgVhlCallCost", this.id, new Long(this.avgVhlCallCost), new TypeToken<Long>() {}.getType()));
	}
	
	public void addVhlCallCost(long vhlCallCost) {
		if(vhlCallCost > 60L*1000L) {
			getLogger().debug("Too long vhlCallCost. edgeId {}, new {}, before {}. so adding default max value 60sec", this.id, vhlCallCost, this.avgVhlCallCost);
			vhlCallCost = 60L*1000L;			
		}
		long result = (long)((avgVhlCallCost * PredictionPara.getInstance().getLastHisWeight()) + (1.0-PredictionPara.getInstance().getLastHisWeight()) * vhlCallCost);
		
		setAvgVhlCallCost(result);
	}
	
	@Override
	public boolean isAvailable(PROCESS_TYPE carrierType) {
		return isAvailable();
	}

	@Override
	public int getFutureTransCount(String carrierId, long after) {
		return 0;
	}

	@Override
	public long getFutureCost(String carrierId, long after) {
		return 0;
	}

}
