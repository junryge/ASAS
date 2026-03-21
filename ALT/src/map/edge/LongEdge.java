//import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.ConcurrentMap;
import java.util.concurrent.PriorityBlockingQueue;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.data.Carrier;
import com.skhynix.smartatlas.data.Command;
//import com.skhynix.smartatlas.data.Job;
//import com.skhynix.smartatlas.data.PredictionPara;
import com.skhynix.smartatlas.data.RouteItem;
//import com.skhynix.smartatlas.data.RouteItem.ROUTE_ITEM_DET_TYPE;
import com.skhynix.smartatlas.data.Carrier.PROCESS_TYPE;
import com.skhynix.smartatlas.map.AbstractEdge;
import com.skhynix.smartatlas.map.AbstractNode;
import com.skhynix.smartatlas.map.Vhl;
import com.skhynix.smartatlas.map.Vhl.RUN_CYCLE;
import com.skhynix.smartatlas.map.Vhl.VHL_CYCLE;
import com.skhynix.smartatlas.map.Vhl.VHL_DET_STATE;
import com.skhynix.smartatlas.map.Vhl.VHL_STATE;
import com.skhynix.smartatlas.map.node.RailNode;
import com.skhynix.smartatlas.map.node.StkPortNode;
//import com.skhynix.smartatlas.navi.DijkstraFromToPath;
//import com.skhynix.smartatlas.navi.DijkstraRailReverseShortestPath;
//import com.skhynix.smartatlas.navi.DijkstraRailReverseShortestPath.NearestVhlInfo;
//import com.skhynix.smartatlas.navi.RouteResult;
import com.skhynix.smartatlas.util.DataService;
//import com.skhynix.smartatlas.util.JsonUtil;
import com.skhynix.smartatlas.util.Util;

public class LongEdge extends AbstractEdge {
	private transient Logger logger = LoggerFactory.getLogger(getClass());
	
	private Logger getLogger() {
		if (logger == null) {
			logger = LoggerFactory.getLogger(getClass());
		}
		
		return logger;
	}
	
	private final int direction;
	private ConcurrentLinkedQueue<String> edgeIdList;
	private ConcurrentMap<String, Long> estimatedCmdIdPassTimeMap 	= new ConcurrentHashMap<>();
	private long last1HourCost 										= -1;
	private double transWeight 										= -1;
	private double acqTransWeight 									= -1;
	private double dpstTransWeight 									= -1;
	private double junctionMultiple 								= -1;
	private double transOverlapIntervalT 							= -1;
	private long lastParaRefreshTime 								= -1;
	private PriorityBlockingQueue<RouteItem> pathPredictQueue 		= new PriorityBlockingQueue<>();
	private EDGE_TYPE firstEdgeType 								= null;
	transient private ConcurrentLinkedQueue<AbstractEdge> edgeList 	= null;
	
	public boolean changed(LongEdge oe) {
		if (this.direction != oe.direction) {
			return true;
		}
		
		if (!Util.isContentsEqualsCollection(this.edgeIdList, oe.edgeIdList)) {
			return true;
		}
		
		return super.changed(oe);
	}
	
	public LongEdge(
					String fabId, 
					String id, 
					String fromNodeId, 
					String toNodeId, 
					int direction, 
					ConcurrentLinkedQueue<String> edgeIdList, 
					boolean isUpdate
	) {
		super(fabId, id, fromNodeId, toNodeId, EDGE_TYPE.LONGEDGE, 0, isUpdate);		

		this.direction 	= direction;
		this.edgeIdList	= edgeIdList;	
	}
	
	public String getFirstAreaName() {
		if (getEdgeIdList().isEmpty()) {
			return "";
		}
		
		AbstractEdge firstEdge = DataService.getDataSet().getEdgeMap().get(getEdgeIdList().peek());		
		
		return firstEdge.getAreaName();
	}
	
	public Map<VHL_STATE,Integer> getCurrentVhlStateMap(){
		getEdgeList();
		
		Map<VHL_STATE,Integer> m = new HashMap<>();
		
		if (getFirstEdgeType() == EDGE_TYPE.RAILEDGE) {
			for (AbstractEdge edge : edgeList) {
				RailEdge re 				= (RailEdge)edge;
				Map<VHL_STATE,Integer> s 	=  re.getCurrentVhlStateMap();
				
				for (VHL_STATE vs : s.keySet()) {
					m.compute(vs, (k, v)-> v == null? s.get(vs) : v + s.get(vs));
				}
			}
		}
		return m;
	}
	
	public Map<VHL_DET_STATE,Integer> getCurrentVhlDetStateMap(){
		getEdgeList();
		
		Map<VHL_DET_STATE,Integer> m = new HashMap<>();
		
		if (getFirstEdgeType() == EDGE_TYPE.RAILEDGE) {
			for (AbstractEdge edge : edgeList) {
				RailEdge re 					= (RailEdge)edge;
				Map<VHL_DET_STATE,Integer> s 	=  re.getCurrentVhlDetStateMap();
				
				for (VHL_DET_STATE vs : s.keySet()) {
					m.compute(vs, (k, v)-> v == null? s.get(vs) : v + s.get(vs));
				}
			}
		}
		
		return m;
	}
	
	public Map<VHL_CYCLE,Integer> getCurrentVhlCycleMap(){
		getEdgeList();
		Map<VHL_CYCLE,Integer> m = new HashMap<>();
		if(getFirstEdgeType() == EDGE_TYPE.RAILEDGE) {
			for(AbstractEdge edge : edgeList) {
				RailEdge re = (RailEdge)edge;
				Map<VHL_CYCLE,Integer> s =  re.getCurrentVhlCycleMap();
				for(VHL_CYCLE vs : s.keySet()) {
					m.compute(vs, (k, v)-> v==null? s.get(vs) : v + s.get(vs));
				}
			}
		}
		return m;
	}
	
	public Map<RUN_CYCLE,Integer> getCurrentVhlRunCycleMap(){
		getEdgeList();
		Map<RUN_CYCLE,Integer> m =  new HashMap<RUN_CYCLE, Integer>();
		if(getFirstEdgeType() == EDGE_TYPE.RAILEDGE) {
			for(AbstractEdge edge : edgeList) {
				RailEdge re = (RailEdge)edge;
				Map<RUN_CYCLE,Integer> s =  re.getCurrentVhlRunCycleMap();
				for(RUN_CYCLE vs : s.keySet()) {
					m.compute(vs, (k, v)-> v==null? s.get(vs) : v + s.get(vs));
				}
			}
		}
		return m;
	}
	
	@Override
	public double getLength() {
		if(length <= 0) {
			double len = 0;
			getEdgeList();		
			for(AbstractEdge edge : edgeList) {
				len += edge.getLength();
			}
			length = len;
		}
		return length;
	}
	
	public long getDistanceFromHeadToNode(String NodeId) {
		long distance = 0;
		for(AbstractEdge edge : this.getEdgeList()) {
			if(!edge.getFromNodeId().equals(NodeId)) {
				distance += edge.getLength();
			}else {
				break;
			}
		}
		return distance;
	}
//	@Override
//	public boolean isAvailable() {
//		for(String edgeId : edgeIdList) {
//			AbstractEdge ae = DataService.getDataSet().getEdgeMap().get(edgeId);
//			if(ae.isAvailable() == false) {
//				setPathPredictQueue(new PriorityBlockingQueue<RouteItem>());
//				return false;
//			}
//		}
//		return true;
//	}
	@Override
	public boolean isAvailable() {
		getEdgeList();
		for(AbstractEdge ae : edgeList) {
			if(!ae.isAvailable()) {
				setPathPredictQueue(new PriorityBlockingQueue<>());
				return false;
			}
		}
		return true;
	}
	
//	@Override
//	public boolean isAvailable(PROCESS_TYPE carrierType) {
//		for(String edgeId : edgeIdList) {
//			AbstractEdge ae = DataService.getDataSet().getEdgeMap().get(edgeId);
//			if(ae.isAvailable(carrierType) == false)
//				return false;
//		}
//		return true;
//	}
	@Override
	public boolean isAvailable(PROCESS_TYPE carrierType) {
		getEdgeList();
		for(AbstractEdge ae : edgeList) {
			if(!ae.isAvailable(carrierType)) {
				return false;
			}
		}
		return true;
	}
	public ConcurrentLinkedQueue<AbstractEdge> getEdgeList(){
		if (this.edgeList == null) {
			ConcurrentLinkedQueue<AbstractEdge> el = new ConcurrentLinkedQueue<>();
			
			for (String edgeId : edgeIdList) {
				AbstractEdge ae = DataService.getDataSet().getEdgeMap().get(edgeId);
				el.add(ae);
			}
			
			this.edgeList = el;
		}
		
		return this.edgeList;
	}
	
	public long getFutureCost(String carrierId, long after) {
//		long cost = 0;
//		for(String edgeId : edgeIdList) {
//			AbstractEdge ae = DataService.getDataSet().getEdgeMap().get(edgeId);
//			long newCost = ae.getFutureCost(carrierId, after);
//			cost += newCost;
//			after += newCost;
//		}
		long cost;
		long futureCost 		= -1;		
		long futureTransCnt;
		long futureAcqCnt;
		long futureDpstCnt;
		
		String otherLongEdgeId 	= "";
		
		switch(getFirstEdgeType()) {
			case RAILEDGE :{
				RailNode toNode = (RailNode)DataService.getDataSet().getNodeMap().get(this.toNodeId);
				if(toNode.isRailJunction()) {
					ConcurrentLinkedQueue<String> joiningEdgeIds = (ConcurrentLinkedQueue<String>) toNode.getFromRailLongEdgeIds();
					for(String joiningEdgeId : joiningEdgeIds) {
						if(!this.longEdgeId.equals(joiningEdgeId)) {
							otherLongEdgeId = joiningEdgeId;

							break;
						}
					}
				}
			long otherEdgeFutureTransCnt = 0L;
			
			if (StringUtils.isNotEmpty(otherLongEdgeId)) {
				LongEdge other 			= DataService.getDataSet().getLongEdgeMap().get(otherLongEdgeId);
				otherEdgeFutureTransCnt	= other.getFutureTransCount(carrierId, after);
				futureTransCnt 			= getFutureTransCount(carrierId, after);
				futureAcqCnt 			= getFutureAcqCount(carrierId, after);
				futureDpstCnt 			= getFutureDpstCount(carrierId, after);
				cost 					= getCost(carrierId);
				futureCost 				= (long)(cost + 
						((futureTransCnt + otherEdgeFutureTransCnt) * transWeight * junctionMultiple) + 
						(futureAcqCnt * acqTransWeight) + 
						(futureDpstCnt * dpstTransWeight));
			} else {
				futureTransCnt 			= getFutureTransCount(carrierId, after);
				futureAcqCnt 			= getFutureAcqCount(carrierId, after);
				futureDpstCnt 			= getFutureDpstCount(carrierId, after);
				cost 					= getCost(carrierId);
				futureCost 				= (long)(cost + 
						(futureTransCnt * transWeight) + 
						(futureAcqCnt * acqTransWeight) + 
						(futureDpstCnt * dpstTransWeight)); // 5000--> ML을 통한 Penalty 계산 대입 필요.
			}
			
			if (futureCost < 0) {
				getLogger().warn("edgeId : {}, futureCost : {}, cost : {}, getFutureTransCount({},{}): {} otherEdgeFutureTransCnt : {}, transWeight : {}, junctionMultiple : {}, "
						+ "getFutureAcqCount : {}, acqTransWeight : {}, getFutureDpstCount : {}, dpstTransWeight : {} ", 
						id, futureCost, cost, carrierId, after, futureTransCnt, otherEdgeFutureTransCnt, transWeight, junctionMultiple, futureAcqCnt, acqTransWeight, futureDpstCnt, dpstTransWeight);
			}			
			
//			if (after <= PredictionPara.getInstance().getUseAvgCostStartAfter() || last1HourCost <= 0) {
//				futureCost = (long)((double)after * PredictionPara.getInstance().getAfterWegith() 
//					+ (double)futureCost * PredictionPara.getInstance().getPredictWeight()
//					+ PredictionPara.getInstance().getBias());
//			} else {
//				futureCost = last1HourCost;
//			}
		} break;
		
		case TRANSEDGE_ACQUIRE: {
			long vhlAssignCost = 0;
			TransferEdge te = (TransferEdge)getFirstEdge();
			if(te.getAssignedVhlCarrierId().endsWith("-"+carrierId)){
				try {
					Vhl v 					= DataService.getDataSet().getVhlMap().get(te.getAssignedVhlCarrierId().split("-")[0]);
//					DijkstraFromToPath dfp 	= new DijkstraFromToPath(carrierId, DataService.getDataSet().getNodeMap().get(v.getCrossPointId()), DataService.getDataSet().getNodeMap().get(this.getToNodeId()), after);
//					RouteResult result 		= dfp.getShortestPath();
//					vhlAssignCost 			= (long)result.totalCost;
				} catch (Exception e) {
					getLogger().error("", e);
				}
			} else if(StringUtils.isNotEmpty(carrierId)){
				Carrier ca = DataService.getDataSet().getCarrierMap().get(carrierId);
				
				if (ca != null && ca.getContainerId().equals(this.fromNodeId)) {
//					RailNode rn 				= (RailNode)DataService.getDataSet().getNodeMap().get(this.getToNodeId());
//					List<NearestVhlInfo> nvil 	= null;
					
//					try {
//						Station destStation	= DataService.getDataSet().getStationMap().get(te.getToStation());
//						nvil 				= new DijkstraRailReverseShortestPath(carrierId, destStation, rn).getNearestVhlList();
//					} catch (Exception e) {
//						getLogger().error("DijkstraRailReverseShortestPath error. Dest : {}, carrier : {}, station : {} ", this.getToNodeId(), carrierId, te.getToStation(), e);						
//					}
					
//					int i = 0;
//					NearestVhlInfo envi = null;
					
//					if (nvil != null) {
//						for (NearestVhlInfo nvi:nvil) {
//							if(i==0) { 
//								vhlAssignCost = nvi.getCost();
//								envi = nvi;
//							}
//							getLogger().debug("{}, {}, {}st nearest vhl : {}", carrierId, rn.getId(), i++, JsonUtil.convertJSON(nvi));
//							if(i==3) break;
//						}
//						if(StringUtils.isNotEmpty(ca.getJobId())) {
//							Job job = DataService.getDataSet().getJobMap().get(ca.getJobId());
//							if(job != null && envi != null)
//								job.setPredictVhlId(envi.getVhl().getId());
//						}
//					}
				}
			}
			if(vhlAssignCost > 0)
				futureCost = te.getAvgTransferCost() + vhlAssignCost;
			else {
				vhlAssignCost = te.getAvgVhlCallCost();
				futureCost = te.getAvgVhlCallCost() + (long)(getFutureTransCount(carrierId, after) * transWeight);
			}
		} break;
		
		case TRANSEDGE_DEPOSIT: {
			TransferEdge te = (TransferEdge)getFirstEdge();
			futureCost = te.getAvgTransferCost() + (long)(getFutureTransCount(carrierId, after) * transWeight);
		} break;			
		
		case CNVEDGE: {
//			Carrier ca = DataService.getDataSet().getCarrierMap().get(carrierId);
//			if(ca != null && StringUtils.isNotEmpty(ca.getCmdId()) && StringUtils.isNotEmpty(ca.getLocId())) {
//				Command co = DataService.getDataSet().getCommandMap().get(ca.getCmdId());
//				if(co != null) {
//					CarrierContainable cc = DataService.getDataSet().getCarrierContainableMap().get(fabId + ":" +ca.getLocId());
//					if(cc != null && cc.getId().equals(co.getSourceNodeId()) && co.getInitTime() >= 0){
//						futureCost = (long)((CnvEdge)getFirstEdge()).getAvgTransferIntervalT() - (System.currentTimeMillis()-co.getInitTime()) + (long)(getFutureTransCount(carrierId, after) * transWeight);
//						return futureCost > 0 ? futureCost : 0;
//					}
//				}
//			}			
//			futureCost = (long)((CnvEdge)getFirstEdge()).getAvgTransferIntervalT() + (long)(getFutureTransCount(carrierId, after) * transWeight);
			futureCost = (long)getCost(carrierId) + (long)(getFutureTransCount(carrierId, after) * transWeight);
		}break;
		case STKRMEDGE: {
			StkRmEdge sre = (StkRmEdge)getFirstEdge();
			if(sre.isFromRm() == false ) {	//본 Edge가 to RM Node인 Case
				// Command와 출발지가 같고 이미 이미 init상태이면 잔여 예상 시간을 사용한다.
				// assign되어 있지 않으면 평균 Assign시간을 사용
				if(sre.getCurrentMovingCarrierIds().contains(carrierId)){
					Carrier ca = DataService.getDataSet().getCarrierMap().get(carrierId);
					Command co = DataService.getDataSet().getCommandMap().get(ca.getCmdId());
					if(co != null && co.getInitTime() >= 0) {
						futureCost = sre.getCost(carrierId) - (System.currentTimeMillis()-co.getInitTime());
						return futureCost > 0 ? futureCost : 0;
					}
				}
			} else {	//	본 Edge가 From RM Node인 Case
				if(sre.getCurrentMovingCarrierIds().contains(carrierId)){
					Carrier ca = DataService.getDataSet().getCarrierMap().get(carrierId);
					Command co = DataService.getDataSet().getCommandMap().get(ca.getCmdId());
					
					if(co != null && co.getDepositStartTime() >= 0) {
						futureCost = sre.getCost(carrierId) - (System.currentTimeMillis()-co.getDepositStartTime());
						return futureCost > 0 ? futureCost : 0;
					}
				}
			}
			futureTransCnt = getFutureTransCount(carrierId, after);
			futureCost = sre.getCost(carrierId) + (long)(futureTransCnt * transWeight);
		} break;
		
		default : 
			break;			
		}
		
		if (futureCost <= 0) {
			logger.warn("{} minus future cost!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! : {} ",longEdgeId, futureCost);
		}
		
		return futureCost;
	}
	
	public Map<EDGE_TYPE, Float> getFutureTransCountMap(String carrierId, long after){
		Map<EDGE_TYPE, Float> resultSet = new ConcurrentHashMap<>();
		
		resultSet.put(EDGE_TYPE.CNVEDGE,0f);
		resultSet.put(EDGE_TYPE.RAILEDGE,0f);
		resultSet.put(EDGE_TYPE.STKRMEDGE,0f);
		resultSet.put(EDGE_TYPE.TRANSEDGE_ACQUIRE,0f);
		resultSet.put(EDGE_TYPE.TRANSEDGE_DEPOSIT,0f);
		
		resultSet.put(getFirstEdgeType(), (float)getFutureTransCount(carrierId, after));
		
//		Map<EDGE_TYPE, Float> resultCountSet = new ConcurrentHashMap<EDGE_TYPE, Float>();
//		for(String edgeId : edgeIdList) {
//			AbstractEdge ae = DataService.getDataSet().getEdgeMap().get(edgeId);
//			resultSet.put(ae.getType(), resultSet.get(ae.getType())+ae.getFutureTransCount(carrierId, after));
//			resultCountSet.compute(ae.getType(), (k,v) -> v==null?1f:v+1f);
//		}
//		for(Entry<EDGE_TYPE, Float> entry: resultSet.entrySet()) {
//			if(resultCountSet.containsKey(entry.getKey()))
//				entry.setValue(entry.getValue()/resultCountSet.get(entry.getKey()));
//		}
		return resultSet;
	}
	
	public EDGE_TYPE getFirstEdgeType(){
		if(firstEdgeType == null) {
			firstEdgeType = DataService.getDataSet().getEdgeMap().get(this.getEdgeIdList().peek()).getType();
		}
		return firstEdgeType;
	}
	
//	public AbstractEdge getFirstEdge() {
//		if(this.getEdgeIdList().size()>0)
//			return DataService.getDataSet().getEdgeMap().get(this.getEdgeIdList().peek());
//		return null;
//	}
	
	public AbstractEdge getFirstEdge() {
		getEdgeList();
		
		if (this.getEdgeIdList().size()>0) {
			return this.getEdgeList().peek();
		}
		
		return null;
	}
	
	public AbstractEdge getLastEdge() {
		int size = this.getEdgeList().size();
		if(size>0)
			return this.getEdgeList().toArray(new AbstractEdge[size])[size-1];
		return null;
	}
	
//	public AbstractEdge getLastEdge() {
//		int size = this.getEdgeIdList().size();
//		if(size>0)
//			return DataService.getDataSet().getEdgeMap().get(this.getEdgeIdList().toArray(new String[size])[size-1]);
//		return null;
//	}
	
	@Override
	public long getCost(String carrierId) {
		long cost = 0;
		
		getEdgeList();
		
		for (AbstractEdge edge : edgeList) {
			cost += edge.getCost(carrierId);
		}
		
		return cost;
	}
	
	public long getPPCost() {
		double cost = getCost("") * 0.7;
		
		switch(getFirstEdgeType()) {
			case STKRMEDGE :
				cost += (pathPredictQueue.size() * 5000);
				
				break;
			default :
				cost += (pathPredictQueue.size() * 50);//penalty 반영
		}
		
		return (long)cost;
	}
	
	public long getVhlCountCost() {
		long cost = 0;
		
		if (getFirstEdgeType() != EDGE_TYPE.RAILEDGE) {
			return 0;
		}
		
		getEdgeList();
		
		for (AbstractEdge edge : edgeList) {
			RailEdge re = (RailEdge)edge;			
			
			cost += re.getVhlCountCost();
		}
		return cost;
	}
	
	public int getDirection() {
		return direction;
	}
	
	public ConcurrentMap<String, Long> getEstimatedCmdIdPassTimeMap() {
		return estimatedCmdIdPassTimeMap;
	}
	
	public void setEstimatedCmdIdPassTimeMap(ConcurrentMap<String, Long> estimatedCmdIdPassTimeMap) {
		this.estimatedCmdIdPassTimeMap = estimatedCmdIdPassTimeMap;
	}

	public ConcurrentLinkedQueue<String> getEdgeIdList() {
		if(edgeIdList == null)
			edgeIdList = new ConcurrentLinkedQueue<String>();
		return edgeIdList;
	}

	public void setEdgeIdList(ConcurrentLinkedQueue<String> edgeIdList) {
		this.edgeIdList = edgeIdList;
	}
	
	@Override
	public String toString() {
		return this.id;
	}

	@Override
	public int getFutureTransCount(String carrierId, long after) {
		if (lastParaRefreshTime < System.currentTimeMillis() - 60000) {
			if (getFirstEdgeType() != EDGE_TYPE.STKRMEDGE) {
//				transWeight = PredictionPara.getInstance().getTransWeight(fabId, getFirstEdgeType(), "ALL");
//				transOverlapIntervalT = PredictionPara.getInstance().getTransOverlapIntervalT(fabId, getFirstEdgeType(), "ALL");
			} else {
//				transWeight = PredictionPara.getInstance().getTransWeight(fabId, getFirstEdgeType(), ((StkRmEdge)getFirstEdge()).getStockerType().toString());
//				transOverlapIntervalT = PredictionPara.getInstance().getTransOverlapIntervalT(fabId, getFirstEdgeType(), ((StkRmEdge)getFirstEdge()).getStockerType().toString());
			}
//			acqTransWeight = PredictionPara.getInstance().getTransWeight(fabId, EDGE_TYPE.TRANSEDGE_ACQUIRE, "ALL");
//			dpstTransWeight = PredictionPara.getInstance().getTransWeight(fabId, EDGE_TYPE.TRANSEDGE_DEPOSIT, "ALL");
			
			if (getFirstEdgeType() == EDGE_TYPE.RAILEDGE) {
//				junctionMultiple = PredictionPara.getInstance().getJunctionMultiple(fabId, ((RailEdge)getFirstEdge()).getMcpName());
			}
			
			lastParaRefreshTime = System.currentTimeMillis();
		}
		
		final long now = System.currentTimeMillis();
		
		// 지난 Item이 있으면 삭제 부터 먼저 진행.
		cleanOldQueue();
		
		// 해당 Edge에 도착할 미래시점
		after = now+after;
		int cnt = 0;
		long ec = getCost(carrierId);
		
		switch(getFirstEdgeType()) {
			case TRANSEDGE_ACQUIRE :{
				TransferEdge te = (TransferEdge)getFirstEdge();
				if(te.getAssignedVhlCarrierId().endsWith("-"+carrierId)) {
					return 0;
				}
				//TRANSEDGE_DEPOSIT과 동일하므로 break 없이 계속 진행.
			}
			case TRANSEDGE_DEPOSIT :{
				long avgTransferCost = 0;
				long avgVhlCallCost = 0;
				TransferEdge te = (TransferEdge)getFirstEdge();
				avgTransferCost = te.getAvgTransferCost();
				avgVhlCallCost = te.getAvgVhlCallCost();
				for(RouteItem rs : pathPredictQueue) {
					if(rs!=null) {
						long eta = rs.getArrivalTime();
						if(eta < after - transOverlapIntervalT
								|| eta > after + avgTransferCost +avgVhlCallCost || (StringUtils.isNotEmpty(carrierId) && rs.getJobOrCmdId().contains(carrierId)))
							continue;
						else
							cnt++;
					}
				}
			}break;
			case RAILEDGE : {
				for(RouteItem rs : pathPredictQueue) {
					if(rs!=null) {
						long eta = rs.getArrivalTime();
						if(eta < after - transOverlapIntervalT || eta > after + ec + transOverlapIntervalT || (StringUtils.isNotEmpty(carrierId) && rs.getJobOrCmdId().contains(carrierId)))
							continue;
						else
							cnt++;
					}
				}
			}break;
			case STKRMEDGE : {
				StkRmEdge re = (StkRmEdge)getFirstEdge();
				long viewRange = (long)re.getAvgTransferCost();
				if(re.isFromRm()==false) {
					// Command와 출발지가 같고 이미 이미 init상태이면 잔여 예상 시간을 사용한다.
					// assign되어 있지 않으면 평균 Assign시간을 사용
					if(re.getCurrentMovingCarrierIds().contains(carrierId)){
						return 0;						
					}
					AbstractNode an = DataService.getDataSet().getNodeMap().get(re.getFromNodeId());
					if(an instanceof StkPortNode) {
						viewRange = ((StkPortNode)an).getAvgRemovalIntervalT();
					}
				}else {
					if(re.getCurrentMovingCarrierIds().contains(carrierId)){
						return 0;						
					}
					AbstractNode an = DataService.getDataSet().getNodeMap().get(re.getToNodeId());
					if(an instanceof StkPortNode) {
						viewRange = ((StkPortNode)an).getAvgRemovalIntervalT();
					}
				}
				for(RouteItem rs : pathPredictQueue) {
					if(rs!=null) {
						long eta = rs.getArrivalTime();
						if(eta < after - transOverlapIntervalT || eta > after + viewRange || (StringUtils.isNotEmpty(carrierId) && rs.getJobOrCmdId().contains(carrierId)))
							continue;
						else
							cnt++;
					}
				}
			}break;
			case CNVEDGE : {
				CnvEdge ce = (CnvEdge)getFirstEdge();
				long avgTransferIntervalT = (long)ce.getAvgTransferIntervalT();
				for(RouteItem rs : pathPredictQueue) {
					if(rs!=null) {
						long eta = rs.getArrivalTime();
						if(eta < after - transOverlapIntervalT || eta > after + avgTransferIntervalT + ec)
							continue;
						else
							cnt++;				
					}
				}
			}break;
			default:break;
			
			}
			
			return cnt;	
	}
	
	public int getFutureAcqCount(String carrierId, long after) {
		int cnt = 0;
		if(getFirstEdgeType() == EDGE_TYPE.RAILEDGE) {
			RailNode rn = (RailNode)DataService.getDataSet().getNodeMap().get(this.toNodeId);
			for(String fromLongEdgeId : rn.getFromLongEdgeIds()) {
				LongEdge le = DataService.getDataSet().getLongEdgeMap().get(fromLongEdgeId);
				if(le != null && le.getFirstEdgeType() == EDGE_TYPE.TRANSEDGE_ACQUIRE) {
					cnt += le.getFutureAcqDpstCountNoVhlCallTime(carrierId, after);
				}
			}
		}
		return cnt;
//		for(String edgeId : edgeIdList) {
//			RailEdge ae = DataService.getDataSet().getRailEdgeMap().get(edgeId);
//			if(ae != null) {
//				cnt += ae.getFutureAcqCount(carrierId, after);
//			}
//		}		
//		return cnt; 
	}
	
	public int getFutureAcqDpstCountNoVhlCallTime(String carrierId, long after) {
		if (getFirstEdgeType() != EDGE_TYPE.TRANSEDGE_ACQUIRE) {
			return 0;
		}
		
		long avgTransferCost = 0;
		TransferEdge te = (TransferEdge)getFirstEdge();
		avgTransferCost = te.getAvgTransferCost();
		
		if(lastParaRefreshTime < System.currentTimeMillis() - 60000) {
//			transWeight 			= PredictionPara.getInstance().getTransWeight(fabId, getFirstEdgeType(), "ALL");
//			transOverlapIntervalT 	= PredictionPara.getInstance().getTransOverlapIntervalT(fabId, getFirstEdgeType(), "ALL");
			lastParaRefreshTime 	= System.currentTimeMillis();
		}
		
		final long now = System.currentTimeMillis();
		
		// 해당 Edge에 도착할 미래시점
		after = now+after;
		
		int cnt = 0;
		
		for(RouteItem rs : pathPredictQueue) {
			if(rs!=null) {
				long eta = rs.getArrivalTime();
				if(eta < after - (transOverlapIntervalT / 2.0)
						|| eta > after + avgTransferCost + transOverlapIntervalT / 2.0 || rs.getJobOrCmdId().contains(carrierId))
					continue;
				else
					cnt++;
			}
		}
		return cnt;
	}
	
	public int getFutureDpstCount(String carrierId, long after) {
		AbstractNode an	= DataService.getDataSet().getNodeMap().get(this.toNodeId);
		int cnt 		= 0;
		
		if (an instanceof RailNode) {
			RailNode rn = (RailNode)an;
			
			for (String toLongEdgeId : rn.getToLongEdgeIds()) {
				LongEdge le = DataService.getDataSet().getLongEdgeMap().get(toLongEdgeId);
				
				if (
						le != null 
						&& le.getFirstEdgeType() == EDGE_TYPE.TRANSEDGE_DEPOSIT
				) {
					cnt += le.getFutureAcqDpstCountNoVhlCallTime(carrierId, after);
				}
			}
		}
		
		return cnt; 
	}

	public long getLast1HourCost() {
		return last1HourCost;
	}

	public void setLast1HourCost(long last1HourCost) {
		this.last1HourCost = last1HourCost;
	}

	public double getTransWeight() {
		return transWeight;
	}

	public void setTransWeight(double transWeight) {
		this.transWeight = transWeight;
	}

	public double getAcqTransWeight() {
		return acqTransWeight;
	}

	public void setAcqTransWeight(double acqTransWeight) {
		this.acqTransWeight = acqTransWeight;
	}

	public double getDpstTransWeight() {
		return dpstTransWeight;
	}

	public void setDpstTransWeight(double dpstTransWeight) {
		this.dpstTransWeight = dpstTransWeight;
	}

	public double getJunctionMultiple() {
		return junctionMultiple;
	}

	public void setJunctionMultiple(double junctionMultiple) {
		this.junctionMultiple = junctionMultiple;
	}

	public double getTransOverlapIntervalT() {
		return transOverlapIntervalT;
	}

	public void setTransOverlapIntervalT(double transOverlapIntervalT) {
		this.transOverlapIntervalT = transOverlapIntervalT;
	}

	public long getLastParaRefreshTime() {
		return lastParaRefreshTime;
	}

	public void setLastParaRefreshTime(long lastParaRefreshTime) {
		this.lastParaRefreshTime = lastParaRefreshTime;
	}
	
	public int cleanOldQueue() {
		RouteItem ri 	= pathPredictQueue.peek();
		int cnt 		= 0;
		
//		while (
//				ri != null 
//				&& (ri.getArrivalTime() <= System.currentTimeMillis() - PredictionPara.getInstance().getPredictQueueTimeout() 
//				|| (
//						!DataService.getDataSet().getJobMap().containsKey(ri.getJobOrCmdId()) 
//						&& ri.getRouteItemDetType() != ROUTE_ITEM_DET_TYPE.IDLEVHL) 
//				)
//			) {
//			pathPredictQueue.poll();
//
//			ri = pathPredictQueue.peek();
//
//			cnt++;
//		}
		
		return cnt;
	}
	
	public PriorityBlockingQueue<RouteItem> getPathPredictQueue(){
		return this.pathPredictQueue;
	}
	
	public void addPredictItem(RouteItem ri) {
		pathPredictQueue.add(ri);
	}
	
	public void removePredictItem(RouteItem ri) {
		if (pathPredictQueue.remove(ri)) {
			logger.info("... removing the path of predict queue was completed");
		} else {
			logger.warn("... removing the path of predict queue was fail !");
		}
	}

	public int getPathPredictQueueSize() {	
		if (pathPredictQueue == null) {
			pathPredictQueue = new PriorityBlockingQueue<>();
		}
		
		return this.pathPredictQueue.size();
	}
	
	public void setPathPredictQueue(PriorityBlockingQueue<RouteItem> pathPredictQueue) {
		this.pathPredictQueue = pathPredictQueue;
	}
	
	public float getDensity() {
		if (getFirstEdgeType() != EDGE_TYPE.RAILEDGE) {
			return 0f;
		}
		
		float vhlLengthSum;
		float vhlLength;
		
		if (fabId.startsWith("M14")) {
			vhlLength = 784 + 300;
		} else if (fabId.startsWith("M16")) {
			vhlLength = 943 + 300;
		} else {
			vhlLength = 784 + 300;
		}
		
		int vhlCntSum = 0;
		
		for(AbstractEdge edge : edgeList) {
			vhlCntSum += ((RailEdge)edge).getVhlIdMap().size();			
		}
		
		vhlLengthSum = vhlCntSum * vhlLength;
		
		float railLength = (float)getLength() - ((float)getLength() % vhlLength);
		
		if (railLength <= vhlLength) {
			railLength = vhlLength;
		}
		
		float returnValue = vhlLengthSum / railLength * 100f;
		
		return Math.min(returnValue, 100f);
	}
}
