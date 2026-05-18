package com.skhynix.smartatlas.map;

import com.skhynix.smartatlas.data.Carrier.PROCESS_TYPE;
import com.skhynix.smartatlas.util.DataService;

public abstract class AbstractEdge {
	public enum EDGE_TYPE{LONGEDGE, RAILEDGE, STKRMEDGE, TRANSEDGE_ACQUIRE, TRANSEDGE_DEPOSIT, CNVEDGE, BRANCHJOINEDGE, AGVEDGE}
	
	transient protected boolean batchFlush 		= false;
	protected String id 						= "";
	protected String fabId 						= "";
	protected String fromNodeId 				= "";
	protected String toNodeId 					= "";
	protected String areaName 					= "";
	protected String bayName 					= "";
	protected String areaId 					= "";
	protected String bayId 						= "";
	protected String longEdgeId 				= "";
	protected double length 					= 0;
	protected EDGE_TYPE type 					= EDGE_TYPE.RAILEDGE;
	protected boolean isUpdate 					= false;
	transient protected int fromNodeFabBit 		= 0;
	transient protected int toNodeFabBit 		= 0;
	transient protected AbstractNode fromNode 	= null;
	transient protected AbstractNode toNode 	= null;
	
	public boolean changed(AbstractEdge oe) {
		if (this.fabId.equals(oe.fabId) == false ) {
			return true;
		}
		
		if (this.fromNodeId.equals(oe.fromNodeId) == false) {
			return true;
		}
		
		if (this.toNodeId.equals(oe.toNodeId) == false) {
			return true;
		}
		
		if (this.areaName.equals(oe.areaName) == false) {
			return true;
		}
		
		if (this.areaId.equals(oe.areaId) == false) {
			return true;
		}
		
		if (this.bayName.equals(oe.bayName) == false) {
			return true;
		}
		
		if (this.bayId.equals(oe.bayId) == false) {
			return true;
		}
		
		if (this.longEdgeId.equals(oe.longEdgeId) == false) {
			return true;
		}
		
		if (this.length != oe.length) {
			return true;
		}
		
		if (this.type != oe.type) {
			return true;
		}
		
		return false;
	}
	
	protected AbstractEdge(
							String fabId, 
							String id, 
							String fromNodeId, 
							String toNodeId, 
							EDGE_TYPE type, 
							double length, 
							boolean isUpdate
	) {
		this.fabId 			= fabId;
		this.id				= id;
		this.fromNodeId		= fromNodeId;
		this.toNodeId 		= toNodeId;
		this.type 			= type;
		this.length 		= length;
		this.isUpdate 		= isUpdate;
	}
	
	abstract public long getCost(String carrierId);
	abstract public long getFutureCost(String carrierId, long after);
	abstract public int getFutureTransCount(String carrierId, long after);
	abstract public boolean isAvailable();
	abstract public boolean isAvailable(PROCESS_TYPE carrierType);
	
	public String getId() {
		return id;
	}
	
	public void setId(String id) {
		this.id = id;
	}
	
	public String getFromNodeId() {
		return fromNodeId;
	}
	
	public void setFromNodeId(String fromNodeId) {
		this.fromNodeId = fromNodeId;
	}
	
	public String getToNodeId() {
		return toNodeId;
	}
	
	public void setToNodeId(String toNodeId) {
		this.toNodeId = toNodeId;
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

	public String getLongEdgeId() {
		return longEdgeId;
	}

	public void setLongEdgeId(String longEdgeId) {
		this.longEdgeId = longEdgeId;
	}

	public String getFabId() {
		return fabId;
	}

	public void setFabId(String fabId) {
		this.fabId = fabId;
	}

	public EDGE_TYPE getType() {
		return type;
	}

	public void setType(EDGE_TYPE type) {
		this.type = type;
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
//		RedisPool.jset(this.id, this);
	}

	public double getLength() {
		return length;
	}

	public void setLength(double length) {
		this.length = length;
	}

	public boolean isUpdate() {
		return isUpdate;
	}

	public void setUpdate(boolean isUpdate) {
		this.isUpdate = isUpdate;
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
	
	public AbstractNode getFromNode() {
		if (fromNode == null && DataService.getDataSet() != null) {
			fromNode = DataService.getDataSet().getNodeMap().get(fromNodeId);
		}
		
		return fromNode;
	}
	
	public int getFromNodeFabBit() {
		if (fromNodeFabBit > 0) {
			return fromNodeFabBit;
		} else {
			this.fromNodeFabBit = DataService.getFabBits(getFromNode().getFabId());
			
			return fromNodeFabBit;
		}
	}
	
	public int getToNodeFabBit() {
		if (toNodeFabBit > 0) {
			return toNodeFabBit;
		} else {
			this.toNodeFabBit = DataService.getFabBits(getToNode().getFabId());
			
			return toNodeFabBit;
		}
	}
	
	public AbstractNode getToNode() {
		if (toNode == null && DataService.getDataSet() != null) {
			toNode = DataService.getDataSet().getNodeMap().get(toNodeId);
		}
		
		return toNode;
	}
}
