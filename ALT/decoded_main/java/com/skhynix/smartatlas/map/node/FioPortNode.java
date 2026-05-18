package com.skhynix.smartatlas.map.node;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ConcurrentLinkedQueue;

import com.skhynix.smartatlas.data.Carrier.PROCESS_TYPE;
import com.skhynix.smartatlas.map.AbstractNode;
import com.skhynix.smartatlas.map.CarrierContainable;
import com.skhynix.smartatlas.util.JsonToStringBuilder;
import com.skhynix.smartatlas.util.JsonUtil;
import com.skhynix.smartatlas.util.Util;

public class FioPortNode extends AbstractNode  implements CarrierContainable {
	private Set<PROCESS_TYPE> processTypeSet			= new HashSet<PROCESS_TYPE>();
	private String eqpId;
	private ConcurrentLinkedQueue<String> carrierIdList = new ConcurrentLinkedQueue<String>();
	private boolean isAvailable;
	private FIO_PORT_INOUT_TYPE inOutType;
	private ConcurrentLinkedQueue<SubPort> subPortList 	= new ConcurrentLinkedQueue<FioPortNode.SubPort>(); 
	
	public boolean changed(FioPortNode oe) {
		if (this.eqpId.equals(oe.eqpId) == false) 	return true;
	
		if (this.inOutType != oe.inOutType) 		return true;
		
		if (JsonUtil.convertJSON(subPortList.stream().sorted().toArray()).equals(JsonUtil.convertJSON(oe.subPortList.stream().sorted().toArray())) == false) return true;
		
		if (Util.isContentsEqualsCollection(this.processTypeSet, oe.processTypeSet) == false) return true;
		
		return super.changed(oe);
	}
	
	/**
	 * A constructor to set the batchFlush with the initialization to other fields.
	 * @param fabId
	 * @param id
	 * @param name
	 * @param eqpId
	 * @param isAvailable
	 * @param inOutType
	 * @param batchFlush
	 */
	public FioPortNode(
						final String fabId, 
						final String id, 
						final String name,
						final String eqpId,
						final boolean isAvailable,
						final FIO_PORT_INOUT_TYPE inOutType,
						final boolean batchFlush,
						boolean isUpdate
	) {
		super(fabId, id, name, null, null, null, null, isUpdate);
		
		this.init(eqpId, isAvailable, inOutType);
	}
	
	public FioPortNode(
						String fabId, 
						String id, 
						String name,
						ConcurrentLinkedQueue<String> fromEdgeIds, 
						ConcurrentLinkedQueue<String> toEdgeIds, 
						ConcurrentLinkedQueue<String> fromLongEdgeIds,
						ConcurrentLinkedQueue<String> toLongEdgeIds,
						String eqpId,
						ConcurrentLinkedQueue<String> carrierIdList,
						boolean isAvailable,
						FIO_PORT_INOUT_TYPE inOutType,
						boolean isUpdate
	) {
		super(fabId, id, name, fromEdgeIds, toEdgeIds, fromLongEdgeIds, toLongEdgeIds, isUpdate);
		
		this.carrierIdList = carrierIdList;
		
		this.init(eqpId, isAvailable, inOutType);
	}
	
	public FioPortNode(
						String fabId, 
						String id, 
						String name,
						String eqpId,
						boolean isAvailable,
						FIO_PORT_INOUT_TYPE inOutType,
						boolean isUpdate
	) {
		super(fabId, id, name, null, null, null, null, isUpdate);

		this.init(eqpId, isAvailable, inOutType);
	}
	

	/**
	 * The common function to initialize the local field of this class.
	 * @param eqpId
	 * @param isAvailable
	 * @param inOutType
	 */
	private void init(
						final String eqpId,
						final boolean isAvailable,
						final FIO_PORT_INOUT_TYPE inOutType
	) {
		this.eqpId 			= eqpId;
		this.isAvailable 	= isAvailable;
		this.inOutType 		= inOutType;
		this.isTerminal 	= true;
	}

	public ConcurrentLinkedQueue<String> getCarrierIdList() {
		return carrierIdList;
	}
	
	@Override
	public void addCarrierId(String carrierId) {
		if (carrierIdList.contains(carrierId) == false) {
			carrierIdList.add(carrierId);
		}
	}
	
	@Override
	public void removeCarrierId(String carrierId) {
		carrierIdList.remove(carrierId);
	}

	public void setCarrierIdList(ConcurrentLinkedQueue<String> carrierIdList) {
		this.carrierIdList = carrierIdList;
	}

	public boolean isAvailable() {
		return isAvailable;
	}

	public void setAvailable(boolean isAvailable) {
		this.isAvailable = isAvailable;
	}
	
	@Override
	public String getEqpId() {
		return eqpId;
	}

	public FIO_PORT_INOUT_TYPE getInOutType() {
		return inOutType;
	}

	public void setInOutType(FIO_PORT_INOUT_TYPE inOutType) {
		this.inOutType = inOutType;
	}

	public class SubPort implements Comparable<SubPort>{
		public FIO_SUB_PORT_TYPE type	= FIO_SUB_PORT_TYPE.LP;
		public String name				= "";
		public FIO_SUB_PORT_ACCESSMODE accessmode = FIO_SUB_PORT_ACCESSMODE.AUTO;
		
		public SubPort(FIO_SUB_PORT_TYPE type, String name, FIO_SUB_PORT_ACCESSMODE accessmode) {
			this.type 		= type;
			this.name 		= name;
			this.accessmode = accessmode;
		}
		
		@Override
		public String toString() {
			JsonToStringBuilder builder = new JsonToStringBuilder(this);
			builder.append("type", 			type);
			builder.append("name", 			name);
			builder.append("accessmode", 	accessmode);
			
			return builder.toString();
		}
		
		@Override
		public int compareTo(SubPort o) {			
			return this.name.compareTo(o.name);
		}
	}
	
	public enum FIO_SUB_PORT_TYPE{LP,BP,OP}
	public enum FIO_SUB_PORT_ACCESSMODE{AUTO,MANUAL}
	public enum FIO_PORT_INOUT_TYPE{IN,OUT,BOTH}

	@Override
	public void setEqpId(String eqpId) {
		this.eqpId = eqpId;
	}

	public ConcurrentLinkedQueue<SubPort> getSubPortList() {
		return subPortList;
	}

	public void setSubPortList(ConcurrentLinkedQueue<SubPort> subPortList) {
		this.subPortList = subPortList;
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
}
