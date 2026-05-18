package com.skhynix.smartatlas.map;

import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;

import org.apache.commons.lang3.StringUtils;

import com.skhynix.smartatlas.data.DataSet;
import com.skhynix.smartatlas.data.eq.Eqp;
import com.skhynix.smartatlas.map.edge.LongEdge;
import com.skhynix.smartatlas.map.edge.Station;
import com.skhynix.smartatlas.map.node.CnvPortNode;
import com.skhynix.smartatlas.map.node.EqpPortNode;
import com.skhynix.smartatlas.map.node.FioPortNode;
import com.skhynix.smartatlas.map.node.RailNode;
import com.skhynix.smartatlas.map.node.StbNode;
import com.skhynix.smartatlas.map.node.StkPortNode;
import com.skhynix.smartatlas.map.node.FioPortNode.SubPort;
import com.skhynix.smartatlas.util.Util;

public abstract class AbstractNode {
	transient protected boolean batchFlush 					= false;
	protected String fabId;
	protected String id;
	protected String name;
	protected Queue<String> fromEdgeIds;
	transient protected Queue<AbstractEdge> fromEdges 		= new ConcurrentLinkedQueue<>();
	protected Queue<String> toEdgeIds;
	transient protected Queue<AbstractEdge> toEdges 		= new ConcurrentLinkedQueue<>();
	protected Queue<String> fromLongEdgeIds;
	transient protected Queue<LongEdge> fromLongEdges 		= new ConcurrentLinkedQueue<>();
	protected Queue<String> toLongEdgeIds;
	transient protected Queue<LongEdge> toLongEdges 		= new ConcurrentLinkedQueue<>();
	protected Queue<String> fromRailLongEdgeIds 			= new ConcurrentLinkedQueue<>();
	transient protected Queue<LongEdge> fromRailLongEdges 	= new ConcurrentLinkedQueue<>();
	protected Queue<String> toRailLongEdgeIds 				= new ConcurrentLinkedQueue<>();
	transient protected Queue<LongEdge> toRailLongEdges 	= new ConcurrentLinkedQueue<>();
	protected boolean isJunction 							= false;
	protected boolean isBranch 								= false;
	protected boolean isTerminal 							= false;
	protected boolean isTeConnection 						= false;
	protected String areaName 								= "";
	protected String bayName 								= "";
	protected String areaId 								= "";
	protected String bayId 									= "";
	protected transient boolean isUpdate;
	protected String mcpName 								= "";
	
	protected int hidId										= -1;	// 2025.02.17
	
	protected boolean changed(AbstractNode oe) {
		if (!this.fabId.equals(oe.fabId)) {
			return true;
		}
		
		if (!this.name.equals(oe.name)) {
			return true;
		}
		
		if (!this.areaName.equals(oe.areaName)) {
			return true;
		}
		
		if (!this.bayName.equals(oe.bayName)) {
			return true;
		}
		
		if (this.isJunction != oe.isJunction) {
			return true;
		}
		
		if (this.isBranch != oe.isBranch) {
			return true;
		}
		
		if (this.isTerminal != oe.isTerminal) {
			return true;
		}
		
		if (this.isTeConnection != oe.isTeConnection) {
			return true;
		}
		
		if (!Util.isContentsEqualsCollection(this.fromEdgeIds, oe.fromEdgeIds)) {
			return true;
		}
		
		if (!Util.isContentsEqualsCollection(this.toEdgeIds, oe.toEdgeIds)) {
			return true;
		}
		
		if (!Util.isContentsEqualsCollection(this.fromLongEdgeIds, oe.fromLongEdgeIds)) {
			return true;
		}

        return !Util.isContentsEqualsCollection(this.toLongEdgeIds, oe.toLongEdgeIds);
    }
	
	protected AbstractNode(
							String fabId, 
							String id, 
							String name, 
							Queue<String> fromEdgeIds, 
							Queue<String> toEdgeIds, 
							Queue<String> fromLongEdgeIds, 
							Queue<String> toLongEdgeIds,
							boolean isUpdate
	) {
		this.fabId 				= fabId;
		this.name 				= name;
		this.id					= id;
		this.fromEdgeIds 		= fromEdgeIds == null ? new ConcurrentLinkedQueue<>() : fromEdgeIds;
		this.toEdgeIds 			= toEdgeIds == null ? new ConcurrentLinkedQueue<>() : toEdgeIds;
		this.fromLongEdgeIds 	= fromLongEdgeIds == null ? new ConcurrentLinkedQueue<>() : fromLongEdgeIds;
		this.toLongEdgeIds 		= toLongEdgeIds == null ? new ConcurrentLinkedQueue<>() : toLongEdgeIds;
		this.isUpdate 			= isUpdate;
	}

	public String getId() {
		return id;
	}
	
	public abstract String getEqpId();
	public abstract void setEqpId(String eqpId);
	public abstract boolean isAvailable();
	public abstract void setAvailable(boolean isAvailable);
	
	public Queue<String> getFromEdgeIds() {
		if (fromEdgeIds == null) {
			fromEdgeIds = new ConcurrentLinkedQueue<>();
		}
		
		return fromEdgeIds;
	}

	public Queue<String> getToEdgeIds() {
		if (toEdgeIds == null) {
			toEdgeIds = new ConcurrentLinkedQueue<>();
		}
		
		return toEdgeIds;
	}
	
	public Queue<String> getFromLongEdgeIds() {
		if (fromLongEdgeIds == null) {
			fromLongEdgeIds = new ConcurrentLinkedQueue<>();
		}
		
		return fromLongEdgeIds;
	}
	
	public Queue<String> getFromRailLongEdgeIds() {
		if (fromLongEdgeIds == null) {
			fromLongEdgeIds = new ConcurrentLinkedQueue<>();
		}
	
		if (this instanceof RailNode) {
			if (fromRailLongEdgeIds == null || fromRailLongEdgeIds.isEmpty()) {
				fromRailLongEdgeIds = new ConcurrentLinkedQueue<>();
				
				for (String fromLongEdgeId : fromLongEdgeIds) {
					if (fromLongEdgeId.matches(".+:RN:.+:RN:.+")) {
						fromRailLongEdgeIds.add(fromLongEdgeId);
					}
				}
			}

			return fromRailLongEdgeIds;
		}
		
		return new ConcurrentLinkedQueue<>();
	}
	
	public Queue<String> getToLongEdgeIds() {
		if(toLongEdgeIds == null) {
			toLongEdgeIds = new ConcurrentLinkedQueue<>();
		}
		
		return toLongEdgeIds;
	}
	
	public Queue<String> getToRailLongEdgeIds() {
		if (toLongEdgeIds == null) {
			toLongEdgeIds = new ConcurrentLinkedQueue<>();
		}
		
		if (this instanceof RailNode) {
			if (toRailLongEdgeIds == null || toRailLongEdgeIds.isEmpty()) {
				toRailLongEdgeIds = new ConcurrentLinkedQueue<>();
				
				for (String toLongEdgeId : toLongEdgeIds) {
					if (toLongEdgeId.matches(".+:RN:.+:RN:.+")) {
						toRailLongEdgeIds.add(toLongEdgeId);
					}
				}
			}
			return toRailLongEdgeIds;
		}
		
		return new ConcurrentLinkedQueue<>();
	}
	
	public boolean isJunction() {
		return this.fromEdgeIds.size() > 1;
	}
	
	public boolean isBranch() {
		return this.toEdgeIds.size() > 1;
	}

	public void setId(String id) {
		this.id = id;
	}

	public void setFromEdgeIds(Queue<String> fromEdgeIds) {
		this.fromEdgeIds = fromEdgeIds;
	}

	public void setToEdgeIds(Queue<String> toEdgeIds) {
		this.toEdgeIds = toEdgeIds;
	}

	public void setFromLongEdgeIds(Queue<String> fromLongEdgeIds) {
		this.fromLongEdgeIds = fromLongEdgeIds;
	}

	public void setToLongEdgeIds(Queue<String> toLongEdgeIds) {
		this.toLongEdgeIds = toLongEdgeIds;
	}

	public void setJunction(boolean isJunction) {
		this.isJunction = isJunction;
	}

	public void setBranch(boolean isBranch) {
		this.isBranch = isBranch;
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

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public boolean isTerminal() {
		return isTerminal;
	}

	public void setTerminal(boolean isTerminal) {
		this.isTerminal = isTerminal;
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
	public void flush() {}

	public boolean isTeConnection() {
		return isTeConnection;
	}

	public void setTeConnection(boolean isTeConnection) {
		this.isTeConnection = isTeConnection;
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
	
	public String getMcpName(DataSet ds){
		if (StringUtils.isNotEmpty(this.mcpName)) {
			return this.mcpName;
		}
		
		if (this instanceof EqpPortNode || this instanceof StbNode) {
			Station st = ds.getStationPortMap().get(getName());
			
			if (st != null) {
				mcpName = st.getMcpName();
				
				return mcpName;
			}				
		} else if (this instanceof RailNode) {
			RailNode rn = (RailNode)this;
			mcpName 	= rn.getMcpName();
			
			return mcpName;
		} else if (this instanceof FioPortNode) {
			FioPortNode fpn = (FioPortNode)this;
			
			for (SubPort sfpn : fpn.getSubPortList()) {
				Station st = ds.getStationPortMap().get(sfpn.name);
				
				if (st != null) {
					mcpName = st.getMcpName();
					
					return mcpName;
				}
			}
		} else if (this instanceof StkPortNode) {
			StkPortNode spn = (StkPortNode)this;
			
			for (com.skhynix.smartatlas.map.node.StkPortNode.SubPort sspn : spn.getSubPortList()) {
				Station st = ds.getStationPortMap().get(sspn.name);
				
				if (st != null) {
					mcpName = st.getMcpName();						
				}
			}
		} else if (this instanceof CnvPortNode) {
			CnvPortNode cpn = (CnvPortNode)this;
			mcpName 		= cpn.getDisplayMcpName();
			
			return mcpName;
		} else {
			Eqp eqp = ds.getAllEqpMap().get(getEqpId());
			
			if (eqp == null || eqp.getMcpNameSet(ds).size() > 1 || eqp.getMcpNameSet(ds).isEmpty()) {
				mcpName="";
			} else {
				mcpName=eqp.getMcpNameSet(ds).iterator().next();
			}
			
			return mcpName;
		}
		
		return mcpName;
	}

	public Queue<LongEdge> getFromLongEdges() {
		if (fromLongEdges == null) {
			fromLongEdges = new ConcurrentLinkedQueue<>();
		}
		
		return fromLongEdges;
	}

	public void setFromLongEdges(Queue<LongEdge> fromLongEdges) {
		this.fromLongEdges = fromLongEdges;
	}

	public Queue<LongEdge> getToLongEdges() {
		if (toLongEdges == null) {
			toLongEdges = new ConcurrentLinkedQueue<>();
		}
		
		return toLongEdges;
	}

	public void setToLongEdges(Queue<LongEdge> toLongEdges) {
		this.toLongEdges = toLongEdges;
	}

	public Queue<LongEdge> getFromRailLongEdges() {
		if (fromRailLongEdges == null) {
			fromRailLongEdges = new ConcurrentLinkedQueue<>();
		}
		
		return fromRailLongEdges;
	}

	public void setFromRailLongEdges(Queue<LongEdge> fromRailLongEdges) {
		this.fromRailLongEdges = fromRailLongEdges;
	}

	public Queue<LongEdge> getToRailLongEdges() {
		if (toRailLongEdges == null) {
			toRailLongEdges = new ConcurrentLinkedQueue<>();
		}
		
		return toRailLongEdges;
	}

	public void setToRailLongEdges(Queue<LongEdge> toRailLongEdges) {
		this.toRailLongEdges = toRailLongEdges;
	}

	public Queue<AbstractEdge> getFromEdges() {
		return fromEdges;
	}

	public void setFromEdges(Queue<AbstractEdge> fromEdges) {
		this.fromEdges = fromEdges;
	}

	public Queue<AbstractEdge> getToEdges() {
		return toEdges;
	}

	public void setToEdges(Queue<AbstractEdge> toEdges) {
		this.toEdges = toEdges;
	}
	
	// 2025.02.17
	public void setHidId(int hidId) {
		this.hidId = hidId;
	}
	
	public int getHidId() {
		return hidId;
	}
	//~
}
