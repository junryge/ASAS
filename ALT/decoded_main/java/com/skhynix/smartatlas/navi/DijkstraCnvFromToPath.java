package com.skhynix.smartatlas.navi;

import java.util.HashMap;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.concurrent.ConcurrentLinkedDeque;
import java.util.concurrent.ConcurrentLinkedQueue;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.util.DataService;
import com.skhynix.smartatlas.map.AbstractEdge;
import com.skhynix.smartatlas.map.edge.CnvEdge;
import com.skhynix.smartatlas.map.edge.TransferEdge;
import com.skhynix.smartatlas.map.node.CnvPortNode;

public class DijkstraCnvFromToPath{
	private final Logger logger = LoggerFactory.getLogger(getClass());
	Map <CnvPortNode, ComparableCnvNode> nodeToComparableMap = new HashMap<CnvPortNode, ComparableCnvNode>();
	private CnvPortNode dest = null, source = null;
	private String carrierId = "";
	/**
	 * 목적지 기준 각 출발지별 경로 및 소요시간을 Return
	 * Assign Vhl 예측 등에 사용.
	 * @param carrierId
	 * @param dest
	 */
	public DijkstraCnvFromToPath(CnvPortNode source, CnvPortNode dest, String carrierId) {
		try {
			this.source = source;
			this.dest = dest;
			this.carrierId = carrierId;
			
			if(dest ==  null || source == null) {	
				logger.warn("{} cnv route getting failed. source : {} or dest : {} is null", carrierId, source, dest);
				return;
			}
			else if(dest.equals(source)) {				
				return;
			}
		}catch(Exception e) {
			logger.error("", e);
		}
				
	}
	
	public ConcurrentLinkedQueue<CnvEdge> getCnvEdgeList() {
		ConcurrentLinkedQueue<CnvEdge> ceListToReturn = new ConcurrentLinkedQueue<CnvEdge>();
		try {			
			
			PriorityQueue<ComparableCnvNode> priorityQueue = new PriorityQueue<>();
			nodeToComparableMap.put(source, new ComparableCnvNode(source, 0, true));
			priorityQueue.add(nodeToComparableMap.get(source));
			
			
			while( !priorityQueue.isEmpty() ){
				// Getting the minimum distance vertex from priority queue
				ComparableCnvNode actualVertex = priorityQueue.poll();
				if(actualVertex.getNode().equals(dest)) // 목적지 까지의 경로를 찾았으면 그만 찾는다.
					break;
				CnvPortNode rn = actualVertex.getNode();
				for(AbstractEdge ae : rn.getToEdges()){
					if(ae instanceof TransferEdge) // 불필요 Logging skip
						continue;
					CnvEdge edge = (CnvEdge) ae; 
					//CnvEdge edge = DataService.getDataSet().getCnvEdgeMap().get(edgeId);
					if(edge == null) {
						logger.error("{} cnv route finding... Not registered edge : {}", carrierId, edge);
						continue;
					}
					if(edge.isAvailable()==false) { // 단절된 경로는 차단.
						logger.warn("{} cnvEdge is currently not available!!!", edge.getId());
						continue;
					}
					CnvPortNode v = (CnvPortNode)DataService.getDataSet().getNodeMap().get(edge.getToNodeId());
					ComparableCnvNode cn = nodeToComparableMap.get(v);
					if(cn == null) {
						cn = new ComparableCnvNode(v, Double.POSITIVE_INFINITY, false);
						nodeToComparableMap.put(v,cn);
					}					
					if(cn.isVisited() == false)
					{
						double eco = (double)edge.getCost("");
						double newDistance = actualVertex.getCost() + eco; 
						// 나중에 parameter로 carrierId와 직전 Edge까지의 Cost도 주자(예상 경과시점상 예측된 다른 Route의 수량을 Cost에 반영하기 위함.)
						//CarrierId는 뭐에 쓸려고 했더라???.. 아 맞다. Carrier 종류에 따라 갈 수 있는 길인지 없는 길인지 판단 해야함.. Cost로 반영.
	 					if( newDistance < cn.getCost() ){
							priorityQueue.remove(cn);
							cn.setCost(newDistance);
							cn.setPredecessor(new CnvEdgePredecessor(edge, newDistance));
							priorityQueue.add(cn);
						}
					}
				}
				actualVertex.setVisited(true);
				//actualVertex.setAllVisited(allVisited);
			}
			
			if(this.nodeToComparableMap.get(dest) == null) {
				logger.warn("{} cnv route finding... route list failed to get. could not find route. source : {}, dest : {}", carrierId, source.getId(), dest.getId());
				return ceListToReturn;
			}
			ConcurrentLinkedDeque<CnvEdge> ceList = new ConcurrentLinkedDeque<CnvEdge>();
			CnvPortNode tdest = dest;
			CnvEdgePredecessor p = null;
			while((p=this.nodeToComparableMap.get(tdest).getPredecessor())!=null) {
				CnvEdge ce = p.getCe();
				ceList.addFirst(ce);
				tdest = (CnvPortNode)ce.getFromNode();//DataService.getDataSet().getNodeMap().get(ce.getFromNodeId());
			}
			
			
			
			for(CnvEdge ce : ceList) {
				ceListToReturn.add(ce);
			}
			
			logger.debug("{} cnv route finding... route list setting success. source : {}, dest : {}", carrierId, source.getId(), dest.getId());			
			
		}catch(Exception e) {
			logger.error("{} cnv route finding...", carrierId, e);
		}
		return ceListToReturn;
	}	
}
