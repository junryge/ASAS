package com.skhynix.smartatlas.map.node;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ConcurrentLinkedQueue;

//import com.skhynix.smartatlas.data.PredictionPara;
import com.skhynix.smartatlas.data.Carrier.PROCESS_TYPE;
import com.skhynix.smartatlas.data.PredictionPara;
import com.skhynix.smartatlas.map.AbstractNode;
import com.skhynix.smartatlas.map.CarrierContainable;
import com.skhynix.smartatlas.util.Util;

public class CnvPortNode extends AbstractNode implements CarrierContainable {
	private String eqpId;
	private int zoneNo;
	private String containingZoneId1;
	private String containingZoneId2;
	private String currentNodeId;
	private String prevNodeId;
	private String groupId;
	private int level;
	private String displayFabId;
	private String displayMcpName;	
	private double drawX, drawY;
	private CNV_NODE_TYPE type;
	private CNV_REF_DIR dir;
	//private ConcurrentLinkedQueue<SubPort> subPortList = new ConcurrentLinkedQueue<CnvPortNode.SubPort>(); 
	private ConcurrentLinkedQueue<String> carrierIdList = new ConcurrentLinkedQueue<String>();
	private int maxCapaCnt;
	private long avgRemovalIntervalT;
	private Set<PROCESS_TYPE> processTypeSet			= new HashSet<PROCESS_TYPE>();
	private boolean isAvailable;
	private long carrierInstalledTime 					= -1;
	private long destPointedTime 						= -1;
	private long carrierRemovedTime 					= -1;
//	private CNV_PORT_INOUT_TYPE inOutType;
	
	public enum CNV_NODE_TYPE{ZONE,BED,INPUT,OUTPUT,QS,INLFT,OUTLFT,LFT};
	public enum CNV_REF_DIR{UP,DOWN,LEFT,RIGHT};
	
	public boolean changed(CnvPortNode oe) {
		if (this.eqpId.equals(oe.eqpId) == false) 							return true;
		
		if (this.maxCapaCnt != oe.maxCapaCnt) 								return true;

		//	if (this.inOutType != oe.inOutType) return true;
		
		if (this.zoneNo != oe.zoneNo) 										return true;
		
		if (this.containingZoneId1.equals(oe.containingZoneId1) == false) 	return true;
		
		if (this.containingZoneId2.equals(oe.containingZoneId2) == false) 	return true;
		
		if (this.currentNodeId.equals(oe.currentNodeId) == false) 			return true;
		
		if (this.prevNodeId.equals(oe.prevNodeId) == false) 				return true;
		
		if (this.groupId.equals(oe.groupId)==false) 						return true;
		
		if (this.level != oe.level) 										return true;
		
		if (this.displayFabId.equals(oe.displayFabId)==false) 				return true;
		
		if (this.displayMcpName.equals(oe.displayMcpName) == false) 		return true;
		
		if (this.drawX != oe.drawX) 										return true;
		
		if (this.drawY != oe.drawY) 										return true;
		
		if (this.type != oe.type) 											return true;
		
		if (this.dir != oe.dir) 											return true;	
		
		if (this.zoneNo != oe.zoneNo) 										return true;
		
		//	if (JsonUtil.convertJSON(subPortList.stream().sorted().toArray()).equals(JsonUtil.convertJSON(oe.subPortList.stream().sorted().toArray())) == false) return true;
		
		if (Util.isContentsEqualsCollection(this.processTypeSet, oe.processTypeSet) == false) return true;

		return super.changed(oe);
	}
	
	public CnvPortNode(
						String fabId, 
						String id,
						String name, 
						String eqpId, 
						int zoneNo,
						String containingZoneId1, 
						String containingZoneId2, 
						String currentNodeId, 
						String prevNodeId, 
						String groupId,
						int level, 
						String displayFabId,
						String displayMcpName, 
						double drawX, 
						double drawY, 
						CNV_NODE_TYPE type,	
						CNV_REF_DIR dir, 			
						int maxCapaCnt,
						boolean isAvailable, 
						boolean batchFlush, 
						boolean isUpdate
	) {
		super(fabId, id, name, null, null, null, null, isUpdate);
	
		this.eqpId 				= eqpId;
		this.zoneNo 			= zoneNo;
		this.containingZoneId1 	= containingZoneId1;
		this.containingZoneId2 	= containingZoneId2;
		this.currentNodeId 		= currentNodeId;
		this.prevNodeId 		= prevNodeId;
		this.groupId 			= groupId;
		this.level 				= level;
		this.displayFabId 		= displayFabId;
		this.displayMcpName 	= displayMcpName;
		this.drawX 				= drawX;
		this.drawY 				= drawY;
		this.type 				= type;
		this.dir 				= dir;
		this.maxCapaCnt 		= maxCapaCnt;
		this.isAvailable 		= isAvailable;
	}

	public CnvPortNode(
						String fabId, 
						String id, 
						String name, 
						String eqpId, 
						int zoneNo,
						String containingZoneId1, 
						String containingZoneId2, 
						String currentNodeId, 
						String prevNodeId, 
						String groupId,
						int level, 
						String displayFabId,
						String displayMcpName, 
						double drawX, 
						double drawY, 
						ConcurrentLinkedQueue<String> fromEdgeIds, 
						ConcurrentLinkedQueue<String> toEdgeIds,
						ConcurrentLinkedQueue<String> fromLongEdgeIds, 
						ConcurrentLinkedQueue<String> toLongEdgeIds, 
						ConcurrentLinkedQueue<String> carrierIdList, 
						CNV_NODE_TYPE type,
						CNV_REF_DIR dir, 
						int maxCapaCnt, 
						long avgRemovalIntervalT,
						Set<PROCESS_TYPE> processTypeSet,
						boolean isAvailable, 
						boolean isUpdate
	) {
		super(fabId, id, name, fromEdgeIds, toEdgeIds, fromLongEdgeIds, toLongEdgeIds, isUpdate);
		
		this.eqpId 					= eqpId;
		this.zoneNo 				= zoneNo;
		this.containingZoneId1 		= containingZoneId1;
		this.containingZoneId2 		= containingZoneId2;
		this.currentNodeId 			= currentNodeId;
		this.prevNodeId 			= prevNodeId;
		this.groupId 				= groupId;
		this.level 					= level;
		this.displayFabId 			= displayFabId;
		this.displayMcpName 		= displayMcpName;
		this.drawX 					= drawX;
		this.drawY 					= drawY;
		this.type 					= type;
		this.dir 					= dir;
		this.carrierIdList 			= carrierIdList;
		this.maxCapaCnt 			= maxCapaCnt;
		this.avgRemovalIntervalT 	= avgRemovalIntervalT;
		this.processTypeSet 		= processTypeSet;
		this.isAvailable 			= isAvailable;
	}
	
	public String getEqpId() {
		return eqpId;
	}

	public ConcurrentLinkedQueue<String> getCarrierIdList() {
		return carrierIdList;
	}	

	@Override
	public void addCarrierId(String carrierId) {
		if (carrierIdList.contains(carrierId) == false) {
			carrierIdList.clear();
			
			carrierIdList.add(carrierId);
		}
	}
	
	@Override
	public void removeCarrierId(String carrierId) {
		setCarrierIdList(new ConcurrentLinkedQueue<String>());
	}

	public void setCarrierIdList(ConcurrentLinkedQueue<String> carrierIdList) {
		this.carrierIdList = carrierIdList;
	}

	public long getAvgRemovalIntervalT() {
		return avgRemovalIntervalT;
	}

	public void setAvgRemovalIntervalT(long avgRemovalIntervalT) {
		if (avgRemovalIntervalT <= 0 || avgRemovalIntervalT > 120000) {
			this.avgRemovalIntervalT = 30000;
		} else {
			this.avgRemovalIntervalT = avgRemovalIntervalT;
		}
	}
	
	public void addRemovalIntervalT(long avgRemovalIntervalT) {		
		this.setAvgRemovalIntervalT((long)(this.avgRemovalIntervalT * PredictionPara.getInstance().getLastHisWeight() + avgRemovalIntervalT * (1-PredictionPara.getInstance().getLastHisWeight())));		
	}

	public int getMaxCapaCnt() {
		return maxCapaCnt;
	}

	public void setEqpId(String eqpId) {
		this.eqpId = eqpId;
	}

	public void setMaxCapaCnt(int maxCapaCnt) {
		this.maxCapaCnt = maxCapaCnt;
	}

	public boolean isAvailable() {
		return isAvailable;
	}

	public void setAvailable(boolean isAvailable) {
		this.isAvailable = isAvailable;
	}

	public Set<PROCESS_TYPE> getProcessTypeSet() {
		return processTypeSet;
	}

	public void setProcessTypeSet(Set<PROCESS_TYPE> processTypeSet) {
		this.processTypeSet = processTypeSet;
	}

	@Override
	public String[] getCarrierIds() {
		return this.carrierIdList.toArray(new String[this.carrierIdList.size()]);
	}

	public int getZoneNo() {
		return zoneNo;
	}

	public void setZoneNo(int zoneNo) {
		this.zoneNo = zoneNo;
	}

	public String getContainingZoneId1() {
		return containingZoneId1;
	}

	public void setContainingZoneId1(String containingZoneId1) {
		this.containingZoneId1 = containingZoneId1;
	}

	public String getContainingZoneId2() {
		return containingZoneId2;
	}

	public void setContainingZoneId2(String containingZoneId2) {
		this.containingZoneId2 = containingZoneId2;
	}

	public String getCurrentNodeId() {
		return currentNodeId;
	}

	public void setCurrentNodeId(String currentNodeId) {
		this.currentNodeId = currentNodeId;
	}

	public String getPrevNodeId() {
		return prevNodeId;
	}

	public void setPrevNodeId(String prevNodeId) {
		this.prevNodeId = prevNodeId;
	}

	public String getGroupId() {
		return groupId;
	}

	public void setGroupId(String groupId) {
		this.groupId = groupId;
	}

	public int getLevel() {
		return level;
	}

	public void setLevel(int level) {
		this.level = level;
	}

	public String getDisplayFabId() {
		return displayFabId;
	}

	public void setDisplayFabId(String displayFabId) {
		this.displayFabId = displayFabId;
	}

	public String getDisplayMcpName() {
		return displayMcpName;
	}

	public void setDisplayMcpName(String displayMcpName) {
		this.displayMcpName = displayMcpName;
		
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

	public CNV_NODE_TYPE getType() {
		return type;
	}

	public void setType(CNV_NODE_TYPE type) {
		this.type = type;
	}

	public CNV_REF_DIR getDir() {
		return dir;
	}

	public void setDir(CNV_REF_DIR dir) {
		this.dir = dir;
	}

	public long getCarrierInstalledTime() {
		return carrierInstalledTime;
	}

	public void setCarrierInstalledTime(long carrierInstalledTime) {
		this.carrierInstalledTime = carrierInstalledTime;
	}

	public long getDestPointedTime() {
		return destPointedTime;
	}

	public void setDestPointedTime(long destPointedTime) {
		this.destPointedTime = destPointedTime;
	}

	public long getCarrierRemovedTime() {
		return carrierRemovedTime;
	}

	public void setCarrierRemovedTime(long carrierRemovedTime) {
		this.carrierRemovedTime = carrierRemovedTime;
	}
}
