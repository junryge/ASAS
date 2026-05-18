package com.skhynix.smartatlas.data;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.map.edge.LongEdge;
import com.skhynix.smartatlas.util.DataService;

public class RouteItem implements Comparable<RouteItem>{
	private String fabId 			= "";
	private String id 				= ""; //"RouteItem;JobId:Predict/NewPredict/History:Seq
	private String jobOrCmdId 		= "";
	private ROUTE_ITEM_TYPE routeItemType 			= ROUTE_ITEM_TYPE.PREDICT;
	private ROUTE_ITEM_DET_TYPE routeItemDetType 	= ROUTE_ITEM_DET_TYPE.ACQUIRE;
	private String edgeId 			= "";
	private int seq 				= -1;
	private long arrivalTime 		= -1; 	//	해당 구간에 도착한 시간.
	private long elpaseIntervalT 	= -1; 	// 	해당 구간까지 걸린시간 합.
	private long itemCost 			= -1; 	// 	해당 구간의 소요시간
	private double currentCost 		= -1;
	private int futureTransCnt 		= -1;
	private int futureAcqCnt 		= -1;
	private int futureDpstCnt 		= -1;
	private String vhlStateMapStr 	= "";
	private String vhlDetStateMapStr = "";
	private String vhlCycleMapStr	= "";
	private String vhlRunCycleMapStr = "";
	private double length 			= 0;
	transient boolean inserted 		= false;
//	private boolean publishFlag 	= true;
	
	public RouteItem(
					String fabId,
					String jobOrCmdId,
					ROUTE_ITEM_TYPE routeItemType, 
					ROUTE_ITEM_DET_TYPE routeItemDetType, 
					String edgeId, 
					int seq, 
					long arrivalTime,
					long elpaseIntervalT,
					long itemCost, 
					boolean publishFlag
	) {
		super();
		
		this.fabId 			= fabId;
		this.id 			= fabId+":"+DataSet.ROUTE_ITEM_PREFIX+":"+jobOrCmdId + ":" + routeItemType + ":" + routeItemDetType + ":" + seq;
		this.jobOrCmdId 	= jobOrCmdId;
		this.routeItemType 	= routeItemType;
		this.routeItemDetType = routeItemDetType;
		this.edgeId = edgeId;
		
		LongEdge le = DataService.getDataSet().getLongEdgeMap().get(edgeId);
		
		this.length = le == null ? -1 : le.getLength();
		this.seq = seq;
		this.arrivalTime = arrivalTime;
		this.elpaseIntervalT = elpaseIntervalT;
		this.itemCost = itemCost;
//		this.publishFlag = publishFlag;
	}
	
	public RouteItem(String fabId, String jobOrCmdId, ROUTE_ITEM_TYPE routeItemType, ROUTE_ITEM_DET_TYPE routeItemDetType, String edgeId, int seq, long arrivalTime,
			long elpaseIntervalT, long itemCost, double currentCost, int futureTransCnt, int futureAcqCnt, int futureDpstCnt, String vhlStateMapStr, String vhlDetStateMapStr, String vhlCycleMapStr, String vhlRunCycleMapStr) {
		super();
		this.fabId = fabId;
		this.id=fabId+":"+DataSet.ROUTE_ITEM_PREFIX+":"+jobOrCmdId + ":" + routeItemType + ":" + routeItemDetType + ":" + seq;
		this.jobOrCmdId = jobOrCmdId;
		this.routeItemType = routeItemType;
		this.routeItemDetType = routeItemDetType;
		this.edgeId = edgeId;
		LongEdge le = DataService.getDataSet().getLongEdgeMap().get(edgeId);
		this.length = le==null?-1:le.getLength();
		this.seq = seq;
		this.arrivalTime = arrivalTime;
		this.elpaseIntervalT = elpaseIntervalT;
		this.itemCost = itemCost;
		this.currentCost = currentCost;
		this.futureTransCnt = futureTransCnt;
		this.futureAcqCnt = futureAcqCnt;
		this.futureDpstCnt = futureDpstCnt;
		this.vhlStateMapStr = vhlStateMapStr;
		this.vhlDetStateMapStr = vhlDetStateMapStr;
		this.vhlCycleMapStr = vhlCycleMapStr;
		this.vhlRunCycleMapStr = vhlRunCycleMapStr;
//		this.publishFlag = true;
	}
	
	public enum ROUTE_ITEM_TYPE{PREDICT, NEWPREDICT, REAL, ORGPREDICT}
	public enum ROUTE_ITEM_DET_TYPE{IDLEVHL, ACQUIRE, DEPOSIT, STK, TRANS_ACQ, TRANS_DPST, RAIL, CNV} // STK, TRANSFER, OHT : PREDICT/NEWPREDICT에서 Edge 종류별로 사용

	public String getId() {
		return id;
	}


	public void setId(String id) {
		this.id = id;
	}


	public String getJobOrCmdId() {
		return jobOrCmdId;
	}


	public void setJobOrCmdId(String jobOrCmdId) {
		this.jobOrCmdId = jobOrCmdId;
	}


	public ROUTE_ITEM_TYPE getRouteItemType() {
		return routeItemType;
	}


	public void setRouteItemType(ROUTE_ITEM_TYPE routeItemType) {
		this.routeItemType = routeItemType;
//		if(publishFlag)
//			AtlasCommPubSub.getInstance().publish(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "routeItemType", this.id, this.routeItemType, new TypeToken<ROUTE_ITEM_TYPE>() {}.getType()));
		//RedisPool.getJReJsonClient().set(this.id, routeItemType, new Path(".routeItemType"));
	}


	public String getEdgeId() {
		return edgeId;
	}


	public void setEdgeId(String edgeId) {
		this.edgeId = edgeId;
		LongEdge le = DataService.getDataSet().getLongEdgeMap().get(edgeId);
		this.length = le==null?-1:le.getLength();
	}


	public int getSeq() {
		return seq;
	}


	public void setSeq(int seq) {
		this.seq = seq;
	}


	public long getArrivalTime() {
		return arrivalTime;
	}

	public void setArrivalTime(long arrivalTime) {
		this.arrivalTime = arrivalTime;
	}


	public long getElpaseIntervalT() {
		return elpaseIntervalT;
	}


	public void setElpaseIntervalT(long elpaseIntervalT) {
		this.elpaseIntervalT = elpaseIntervalT;
	}


	public long getItemCost() {
		return itemCost;
	}

	public void setItemCost(long itemCost) {
		this.itemCost = itemCost;
	}


	public String getFabId() {
		return fabId;
	}


	public void setFabId(String fabId) {
		this.fabId = fabId;
	}


	public ROUTE_ITEM_DET_TYPE getRouteItemDetType() {
		return routeItemDetType;
	}


	public void setRouteItemDetType(ROUTE_ITEM_DET_TYPE routeItemDetType) {
		this.routeItemDetType = routeItemDetType;
	}


	@Override
	public int compareTo(RouteItem o) {
		return (int)(this.getArrivalTime() - o.getArrivalTime());		
	}


	public double getCurrentCost() {
		return currentCost;
	}


	public void setCurrentCost(double currentCost) {
		this.currentCost = currentCost;
	}


	public int getFutureTransCnt() {
		return futureTransCnt;
	}


	public void setFutureTransCnt(int futureTransCnt) {
		this.futureTransCnt = futureTransCnt;
	}

	public double getLength() {
		return length;
	}

	public void setLength(double length) {
		this.length = length;
	}

	public int getFutureAcqCnt() {
		return futureAcqCnt;
	}

	public void setFutureAcqCnt(int futureAcqCnt) {
		this.futureAcqCnt = futureAcqCnt;
	}

	public int getFutureDpstCnt() {
		return futureDpstCnt;
	}

	public void setFutureDpstCnt(int futureDpstCnt) {
		this.futureDpstCnt = futureDpstCnt;
	}

	public String getVhlStateMapStr() {
		return vhlStateMapStr;
	}

	public void setVhlStateMapStr(String vhlStateMapStr) {
		this.vhlStateMapStr = vhlStateMapStr;
	}

	public String getVhlDetStateMapStr() {
		return vhlDetStateMapStr;
	}

	public void setVhlDetStateMapStr(String vhlDetStateMapStr) {
		this.vhlDetStateMapStr = vhlDetStateMapStr;
	}

	public String getVhlCycleMapStr() {
		return vhlCycleMapStr;
	}

	public void setVhlCycleMapStr(String vhlCycleMapStr) {
		this.vhlCycleMapStr = vhlCycleMapStr;
	}

	public String getVhlRunCycleMapStr() {
		return vhlRunCycleMapStr;
	}

	public void setVhlRunCycleMapStr(String vhlRunCycleMapStr) {
		this.vhlRunCycleMapStr = vhlRunCycleMapStr;
	}
	
	public void sendToLogpresso() {
		// 실제 이동경로는 생성 즉시 Logpresso에 적재시킨다.
		if (this.routeItemType != ROUTE_ITEM_TYPE.REAL) {
			return;
		}
		
		setInserted(true);
		
		Tuple mapRouteDataSet 	= new Tuple();
		Command cmd 			= DataService.getDataSet().getCommandMap().get(jobOrCmdId);
		String carrierId 		= "";
		String jobId 			= "";
		
		if (cmd == null) {
			//...			
		} else {
			carrierId 	= cmd.getCarrierId();
			jobId 		= cmd.getJobId();
		}
		
		mapRouteDataSet.put("carrierId", 			carrierId);
		mapRouteDataSet.put("jobOrCmdId", 			jobId);
		mapRouteDataSet.put("fabId",				fabId);
		mapRouteDataSet.put("id",					id);
		mapRouteDataSet.put("routeItemType",		routeItemType.toString());
		mapRouteDataSet.put("routeItemDetType",		routeItemDetType.toString());
		mapRouteDataSet.put("edgeId",				edgeId);
		mapRouteDataSet.put("seq",					Integer.toString(seq));
		mapRouteDataSet.put("arrivalTime",			Long.toString(arrivalTime));
		mapRouteDataSet.put("itemCost",				Long.toString(itemCost));
		mapRouteDataSet.put("currentCost",			Double.toString(currentCost));
		mapRouteDataSet.put("futureTransCnt",		Integer.toString(futureTransCnt));
		mapRouteDataSet.put("futureAcqCnt",			Integer.toString(futureAcqCnt));
		mapRouteDataSet.put("futureDpstCnt",		Integer.toString(futureDpstCnt));
		mapRouteDataSet.put("vhlStateMapStr",		vhlStateMapStr);
		mapRouteDataSet.put("vhlDetStateMapStr",	vhlDetStateMapStr);
		mapRouteDataSet.put("vhlCycleMapStr",		vhlCycleMapStr);
		mapRouteDataSet.put("vhlRunCycleMapStr",	vhlRunCycleMapStr);
		mapRouteDataSet.put("length",				Double.toString(length));
		
//		LogpressoInsertAPi.getInstance().insertTuple("ATLAS_ROUTE", mapRouteDataSet);
	}

	public boolean isInserted() {
		return inserted;
	}

	public void setInserted(boolean inserted) {
		this.inserted = inserted;
	}
	
	@Override
	public boolean equals(Object o) {
		if(o==null)return false;
		return this.getId().equals(((RouteItem)o).getId());// && this.getArrivalTime() == ((RouteItem)o).getArrivalTime();
	}
}