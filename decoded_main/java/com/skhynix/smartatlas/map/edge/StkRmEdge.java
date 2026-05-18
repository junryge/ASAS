package com.skhynix.smartatlas.map.edge;

import java.util.HashSet;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.data.PredictionPara;
import com.skhynix.smartatlas.data.eq.Stocker;
import com.skhynix.smartatlas.data.Carrier.PROCESS_TYPE;
import com.skhynix.smartatlas.map.AbstractEdge;
import com.skhynix.smartatlas.map.AbstractNode;
import com.skhynix.smartatlas.map.node.StkPortNode;
import com.skhynix.smartatlas.util.DataService;
import com.skhynix.smartatlas.util.JsonToStringBuilder;

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
//		if(lastParaRefreshTime < System.currentTimeMillis() - 60000) {
//			transWeight = PredictionPara.getInstance().getTransWeight(fabId, super.getType(), getStockerType().toString());
//			transOverlapIntervalT = PredictionPara.getInstance().getTransOverlapIntervalT(fabId, super.getType(), getStockerType().toString());
//			lastParaRefreshTime = System.currentTimeMillis();
//		}
//		cleanOldQueue();
//		long viewRange = avgTransferCost;
//		if(isFromRm == false) {	//본 Edge가 to RM Node인 Case
//			// Command와 출발지가 같고 이미 이미 init상태이면 잔여 예상 시간을 사용한다.
//			// assign되어 있지 않으면 평균 Assign시간을 사용
//			if(getCurrentMovingCarrierIds().contains(carrierId)){
//				return 0;						
//			}
//			AbstractNode an = DataService.getDataSet().getNodeMap().get(getFromNodeId());
//			if(an instanceof StkPortNode) {
//				viewRange = ((StkPortNode)an).getAvgRemovalIntervalT();
//			}						
//		}else {//본 Edge가 From RM Node인 Case
//			if(getCurrentMovingCarrierIds().contains(carrierId)){
//				return 0;						
//			}
//			AbstractNode an = DataService.getDataSet().getNodeMap().get(getToNodeId());
//			if(an instanceof StkPortNode) {
//				viewRange = ((StkPortNode)an).getAvgRemovalIntervalT();
//			}
//		}
//		final long now = System.currentTimeMillis();
//		// 해당 Edge에 도착할 미래시점
//		after = now+after;
//		int cnt = 0;	
//		
//		
//		for(RouteItem rs : pathPredictQueue) {
//			if(rs!=null) {
//				long eta = rs.getArrivalTime();
//				if(eta < after - transOverlapIntervalT || eta > after + viewRange || rs.getJobOrCmdId().contains(carrierId))
//					continue;
//				else
//					cnt++;
//			}
//		}
//		return cnt;
		LongEdge le = DataService.getDataSet().getLongEdgeMap().get(longEdgeId);		
		return le.getFutureTransCount(carrierId, after);
	}
	
	public long getFutureCost(String carrierId, long after) {
		
		// 지난 Item이 있으면 삭제 부터 먼저 진행.
//		cleanOldQueue();
//		long transferCost = 0;
//		
//		if(isFromRm == false ) {	//본 Edge가 to RM Node인 Case
//			// Command와 출발지가 같고 이미 이미 init상태이면 잔여 예상 시간을 사용한다.
//			// assign되어 있지 않으면 평균 Assign시간을 사용
//			if(getCurrentMovingCarrierIds().contains(carrierId)){
//				Carrier ca = DataService.getDataSet().getCarrierMap().get(carrierId);
//				Command co = DataService.getDataSet().getCommandMap().get(ca.getCmdId());
//				if(co != null && co.getInitTime() >= 0) {
//					transferCost = this.avgTransferCost - (System.currentTimeMillis()-co.getInitTime());
//					return transferCost > 0 ? transferCost : 0;
//				}
//			}
//		}else {//본 Edge가 From RM Node인 Case
//			if(getCurrentMovingCarrierIds().contains(carrierId)){
//				Carrier ca = DataService.getDataSet().getCarrierMap().get(carrierId);
//				Command co = DataService.getDataSet().getCommandMap().get(ca.getCmdId());
//				if(co.getDepositStartTime() >= 0) {
//					transferCost = this.avgTransferCost - (System.currentTimeMillis()-co.getDepositStartTime());
//					return transferCost > 0 ? transferCost : 0;
//				}
//			}
//		}
//		int cnt = getFutureTransCount(carrierId, after);
//		
//		return avgTransferCost + (long)(cnt * transWeight); // ML weight 치환 필요. 
		LongEdge le = DataService.getDataSet().getLongEdgeMap().get(longEdgeId);
		return le.getFutureCost(carrierId, after);
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
