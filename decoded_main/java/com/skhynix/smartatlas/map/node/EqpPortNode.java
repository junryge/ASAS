package com.skhynix.smartatlas.map.node;

import java.util.HashSet;
import java.util.Queue;
import java.util.Set;

import org.apache.commons.lang3.StringUtils;

import com.skhynix.smartatlas.data.Carrier.PROCESS_TYPE;
import com.skhynix.smartatlas.map.AbstractNode;
import com.skhynix.smartatlas.map.CarrierContainable;
import com.skhynix.smartatlas.util.Util;

public class EqpPortNode extends AbstractNode implements CarrierContainable {
	private Set<PROCESS_TYPE> processTypeSet	= new HashSet<PROCESS_TYPE>();
	private String carrierId					= "";
	private boolean isAvailable					= true;
	private boolean isInlinePort				= false;
	private long occupiedTime;
	private String eqpId						= "";
	
	public boolean changed(EqpPortNode oe) {
		if (this.eqpId.equals(oe.eqpId) == false) {
			return true;
		}
		
		if (Util.isContentsEqualsCollection(this.processTypeSet, oe.processTypeSet) == false) {
			return true;
		}
		
		return super.changed(oe);
	}

	/**
	 * A constructor to set the batchFlush with the initialization to other fields.
	 * @param fabId
	 * @param id
	 * @param name
	 * @param eqpId
	 * @param fromEdgeIds
	 * @param toEdgeIds
	 * @param fromLongEdgeIds
	 * @param toLongEdgeIds
	 * @param processTypeSet
	 * @param carrierId
	 * @param isAvailable
	 * @param batchFlush
	 */
	public EqpPortNode(
						final String fabId,
						final String id, 
						final String name,
						final String eqpId,
						final Queue<String> fromEdgeIds, 
						final Queue<String> toEdgeIds, 
						final Queue<String> fromLongEdgeIds,
						final Queue<String> toLongEdgeIds,
						final Set<PROCESS_TYPE> processTypeSet,
						final String carrierId,			
						final boolean isAvailable,
						final boolean batchFlush,
						boolean isUpdate
	) {
		super(fabId, id, name, fromEdgeIds, toEdgeIds, fromLongEdgeIds, toLongEdgeIds, isUpdate);
		
		this.init(eqpId, processTypeSet, carrierId, isAvailable);
	}
	
	public EqpPortNode(
						String fabId, 
						String id, 
						String name,
						String eqpId,
						Queue<String> fromEdgeIds, 
						Queue<String> toEdgeIds, 
						Queue<String> fromLongEdgeIds,
						Queue<String> toLongEdgeIds,
						Set<PROCESS_TYPE> processTypeSet,
						String carrierId,			
						boolean isAvailable,
						boolean isUpdate
	) {
		super(fabId, id, name, fromEdgeIds, toEdgeIds, fromLongEdgeIds, toLongEdgeIds, isUpdate);

		this.init(eqpId, processTypeSet, carrierId, isAvailable);
	}

	/**
	 * The common function to initialize the local field of this class.
	 * @param eqpId
	 * @param processTypeSet
	 * @param carrierId
	 * @param isAvailable
	 */
	private void init(
						final String eqpId,
						final Set<PROCESS_TYPE> processTypeSet,
						final String carrierId,			
						final boolean isAvailable
	) {
		this.eqpId 			= eqpId;
		this.processTypeSet	= processTypeSet;
		this.carrierId		= carrierId;
		this.isAvailable	= isAvailable;
		this.isTerminal 	= true;
	}

	public boolean isAvailable() {
		return isAvailable;
	}

	public void setAvailable(boolean isAvailable) {
		this.isAvailable = isAvailable;
	}
	
	public String getTransferState() {
		// 해당 STB와 관련된 Command 목록이 있는지, 저장된 Carrier가 있는지 확인하여 적합한 상태를 Return 
		return null;
	}

	public boolean isEmpty() {
		return StringUtils.isEmpty(carrierId) && isAvailable;
	}

	public long getOccupiedTime() {
		return occupiedTime;
	}

	public void setOccupiedTime(long occupiedTime) {
		this.occupiedTime = occupiedTime;
	}
	
	@Override
	public String getEqpId() {
		return eqpId;
	}
	
	@Override
	public void setEqpId(String eqpId) {
		this.eqpId = eqpId;
	}
	
	public Set<PROCESS_TYPE> getProcessTypeSet() {
		return processTypeSet;
	}
	
	public void setProcessTypeSet(Set<PROCESS_TYPE> processTypeSet) {
		this.processTypeSet = processTypeSet;
	}

	@Override
	public void addCarrierId(String carrierId) {
		this.carrierId = carrierId;
	}

	@Override
	public void removeCarrierId(String carrierId) {
		this.carrierId = "";	
	}

	@Override
	public String[] getCarrierIds() {
		if(StringUtils.isNotEmpty(this.carrierId)) {
			return new String[] {this.carrierId};
		}
		
		return new String[0];
	}
	
	public void setCarrierIds(String[] carrierIds) {
		if (
				carrierIds != null 
				&& carrierIds.length > 0
		) {
			this.carrierId = carrierIds[0].trim();
		} else {
			this.carrierId = "";
		}
	}

	public boolean isInlinePort() {
		return isInlinePort;
	}

	public void setInlinePort(boolean isInlinePort) {
		this.isInlinePort = isInlinePort;
	}
}
