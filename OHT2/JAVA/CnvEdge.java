public class CnvEdge extends AbstractEdge {
	private long avgTransferIntervalT = 150;
	
	/**
	 * A constructor to set the batchFlush with the initialization to other fields.
	 * @param fabId
	 * @param id
	 * @param fromNodeId
	 * @param toNodeId
	 * @param avgTransferIntervalT
	 * @param batchFlush
	 */
	public CnvEdge(
					final String fabId, 
					final String id,
					final String fromNodeId, 
					final String toNodeId,
					final long avgTransferIntervalT,
					final boolean batchFlush, 
					final double length, 
					boolean isUpdate
	) {
		super(fabId, id, fromNodeId, toNodeId, EDGE_TYPE.CNVEDGE, length, isUpdate);
		
		this.avgTransferIntervalT = avgTransferIntervalT;
	}
	
	@Override
	public long getCost(String carrierId) {
		return avgTransferIntervalT;
	}
	
	@Override
	public int getFutureTransCount(String carrierId, long after) {
//		LongEdge le = DataService.getDataSet().getLongEdgeMap().get(longEdgeId);		
//
//		return le.getFutureTransCount(carrierId, after);
		return 0;
	}
	
	public long getFutureCost(String carrierId, long after) {
//		LongEdge le = DataService.getDataSet().getLongEdgeMap().get(longEdgeId);
//		
//		return le.getFutureCost(carrierId, after);
		return 0;
	}
	
	public void addCost(long newCost) {
		if (newCost > 30000) {
			newCost = 30000;
		} else if (newCost < 300) {
			newCost = 300;
		}
		
		setAvgTransferIntervalT((long)((avgTransferIntervalT * PredictionPara.getInstance().getLastHisWeight()) + (1.0-PredictionPara.getInstance().getLastHisWeight()) * newCost));
	}

	public double getAvgTransferIntervalT() {
		if (avgTransferIntervalT > 30000) {
			avgTransferIntervalT = 30000;
		} else if (avgTransferIntervalT < 300) {
			avgTransferIntervalT = 300;
		}
		
		return avgTransferIntervalT;
	}

	public void setAvgTransferIntervalT(long avgTransferIntervalT) {
		if (avgTransferIntervalT > 30000) {
			avgTransferIntervalT = 30000;
		} else if (avgTransferIntervalT < 300) {
			avgTransferIntervalT = 300;
		}

		this.avgTransferIntervalT = avgTransferIntervalT;
	}

	@Override
	public String toString() {
		JsonToStringBuilder builder = new JsonToStringBuilder(this);
		
		builder.append("class", 				this.getClass().getSimpleName());
		builder.append("id", 					id);
		builder.append("fromNodeId", 			fromNodeId);
		builder.append("toNodeId", 				toNodeId);
		builder.append("avgTransferIntervalT", 	avgTransferIntervalT);
		builder.append("areaName", 				areaName);
		builder.append("bayName", 				bayName);
		
		return builder.toString();
	}

	@Override
	public boolean isAvailable() {
		return getFromNode().isAvailable() && getToNode().isAvailable();
	}

	@Override
	public boolean isAvailable(PROCESS_TYPE carrierType) {
		return isAvailable();
	}
}