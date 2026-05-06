public class TransferEdge extends AbstractEdge {
	private transient Logger logger		= LoggerFactory.getLogger(getClass());
	private String fromStation 			= "";
	private String toStation 			= "";
	private long avgTransferCost 		= 7000l;
	private long avgVhlCallCost 		= 20000l;
	private boolean isAcqEdge 			= false;
	private String assignedVhlCarrierId	= "";
	
	public boolean changed(TransferEdge oe) {
		if (this.fromStation.equals(oe.fromStation) == false) {
			return true;
		}
		
		if (this.toStation.equals(oe.toStation) == false) {
			return true;
		}
		
		if (this.isAcqEdge != oe.isAcqEdge ) {
			return true;
		}
		
		return super.changed(oe);
	}
	
	private Logger getLogger() {
		if(logger==null)
			logger = LoggerFactory.getLogger(getClass());
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
	public TransferEdge(
			final String fabId,
			String id,
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
		super(fabId, id, fromNodeId, toNodeId, isAcqEdge?EDGE_TYPE.TRANSEDGE_ACQUIRE:EDGE_TYPE.TRANSEDGE_DEPOSIT, length, isUpdate);

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
		super(fabId, id, fromNodeId, toNodeId, isAcqEdge?EDGE_TYPE.TRANSEDGE_ACQUIRE:EDGE_TYPE.TRANSEDGE_DEPOSIT, length, isUpdate);
		
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
	
//	public int getFutureTransCount(String carrierId, long after) {
//		if(lastParaRefreshTime < System.currentTimeMillis() - 60000) {
//			transWeight = PredictionPara.getInstance().getTransWeight(fabId, super.getType(), "ALL");
//			transOverlapIntervalT = PredictionPara.getInstance().getTransOverlapIntervalT(fabId, super.getType(), "ALL");
//			lastParaRefreshTime = System.currentTimeMillis();
//		}
//		final long now = System.currentTimeMillis();
//// 해당 Edge에 도착할 미래시점
//		after = now+after;
//		
//		int cnt = 0;
////		해당 Edge의 시작 점에서 기다리고 있는건지 아닌지 판단 필요.
////		만약 이미 VHL이 Assign되어 있으면 잔여시간 필요.
//		if(isAcqEdge && assignedVhlCarrierId.endsWith("-"+carrierId)) {
//			return 0;			
//		}
//		
//		for(RouteItem rs : pathPredictQueue) {
//			if(rs!=null) {
//				long eta = rs.getArrivalTime();
//				if(eta < after - transOverlapIntervalT
//						|| eta > after + avgTransferCost +avgVhlCallCost || rs.getJobOrCmdId().contains(carrierId))
//					continue;
//				else
//					cnt++;
//			}
//		}
//		return cnt;
//	}
	
//	public int getFutureTransCountNoVhlCallTIme(String carrierId, long after) {
//		if(lastParaRefreshTime < System.currentTimeMillis() - 60000) {
//			transWeight = PredictionPara.getInstance().getTransWeight(fabId, super.getType(), "ALL");
//			transOverlapIntervalT = PredictionPara.getInstance().getTransOverlapIntervalT(fabId, super.getType(), "ALL");
//			lastParaRefreshTime = System.currentTimeMillis();
//		}
//		final long now = System.currentTimeMillis();
//// 해당 Edge에 도착할 미래시점
//		after = now+after;
//		
//		int cnt = 0;
//		
//		for(RouteItem rs : pathPredictQueue) {
//			if(rs!=null) {
//				long eta = rs.getArrivalTime();
//				if(eta < after - (transOverlapIntervalT / 2.0)
//						|| eta > after + avgTransferCost + transOverlapIntervalT / 2.0 || rs.getJobOrCmdId().contains(carrierId))
//					continue;
//				else
//					cnt++;
//			}
//		}
//		return cnt;
//	}

	public long getFutureCost(String carrierId, long after) {
		// 지난 Item이 있으면 삭제 부터 먼저 진행.
//		cleanOldQueue();
//		
//		long vhlAssignCost = 0;
////		해당 Edge의 시작 점에서 기다리고 있는건지 아닌지 판단 필요.
////		만약 이미 VHL이 Assign되어 있으면 잔여시간 필요.
//		if(isAcqEdge) {		
//			// Command와 출발지가 같고 이미 이미 Assign되어 있으면 VHL의 실제 예상 도착 시간을 사용한다.
//			// assign되어 있지 않으면 평균 Assign시간을 사용
//			if(assignedVhlCarrierId.endsWith("-"+carrierId)){
//				try {
//					Vhl v = DataService.getDataSet().getVhlMap().get(assignedVhlCarrierId.split("-")[0]);
//					//DijkstraReverseShortestPath dsp = new DijkstraReverseShortestPath(carrierId, DataService.getDataSet().getNodeMap().get(this.getToNodeId()));
//					DijkstraFromToPath dfp = new DijkstraFromToPath(carrierId, DataService.getDataSet().getNodeMap().get(v.getCrossPointId()), DataService.getDataSet().getNodeMap().get(this.getToNodeId()), after);
//					//RouteResult result = dsp.getShortestPathFrom(DataService.getDataSet().getNodeMap().get(v.getCrossPointId()));
//					RouteResult result = dfp.getShortestPath();
//					vhlAssignCost = (long)result.totalCost;
//				}catch (Exception e) {
//					getLogger().error("",e);
//				}
//			}else if(StringUtils.isNotEmpty(carrierId)){
//				Carrier ca = DataService.getDataSet().getCarrierMap().get(carrierId);
//				if(ca!=null && ca.getContainerId().equals(this.fromNodeId)) {
//					RailNode rn = (RailNode)DataService.getDataSet().getNodeMap().get(this.getToNodeId());
//					List<NearestVhlInfo> nvil = null;
//					try {
//						Station destStation = DataService.getDataSet().getStationMap().get(this.toStation);
//						nvil = new DijkstraRailReverseShortestPath(carrierId, destStation, rn).getNearestVhlList();
//					}catch(Exception e) {
//						getLogger().error("DijkstraRailReverseShortestPath error. Dest : {}, carrier : {}, station : {} ", this.getToNodeId(), carrierId, toStation, e);						
//					}
//					int i=0;
//					NearestVhlInfo envi = null;
//					if(nvil != null) {
//						for(NearestVhlInfo nvi:nvil) {
//							if(i==0) { 
//								vhlAssignCost = nvi.getCost();
//								envi = nvi;
//							}
//							getLogger().debug("{}, {}, {}st nearest vhl : {}", carrierId, rn.getId(), i++, JsonUtil.convertJSON(nvi));
//							if(i==3) break;
//						}
//						if(StringUtils.isNotEmpty(ca.getJobId())) {
//							Job job = DataService.getDataSet().getJobMap().get(ca.getJobId());
//							if(job != null)
//								job.setPredictVhlId(envi.getVhl().getId());
//						}
//					}
//					
//				}
//			}
//			
//		}
//		if(vhlAssignCost > 0) {
//			return avgTransferCost + vhlAssignCost;
//		}else {
//			if(isAcqEdge) {
//				vhlAssignCost = this.avgVhlCallCost;
//				return this.avgVhlCallCost + (long)(getFutureTransCount(carrierId, after) * transWeight); // acquire edge의 weight와 deposit edge의 weight는 차이가 있어야한다.
//			}else {
//				return avgTransferCost+ (long)(getFutureTransCount(carrierId, after) * transWeight);
//			}			
//		}
		LongEdge le = DataService.getDataSet().getLongEdgeMap().get(longEdgeId);
		
		return le.getFutureCost(carrierId, after);
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
		LongEdge le = DataService.getDataSet().getLongEdgeMap().get(longEdgeId);
		return le.getFutureTransCount(carrierId, after);
	}

}
