package com.skhynix.smartatlas.map.node;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ConcurrentLinkedQueue;

import com.skhynix.smartatlas.data.Carrier;
import com.skhynix.smartatlas.data.Command;
import com.skhynix.smartatlas.data.Job;
import com.skhynix.smartatlas.map.AbstractNode;
import com.skhynix.smartatlas.map.CarrierContainable;
import com.skhynix.smartatlas.map.CarrierTransportable;
import com.skhynix.smartatlas.util.DataService;

public class StkRmNode extends AbstractNode  implements CarrierContainable, CarrierTransportable {
	private String eqpId;
	private ConcurrentLinkedQueue<String> carrierIdList = new ConcurrentLinkedQueue<String>();
	private ConcurrentLinkedQueue<String> commandIdList = new ConcurrentLinkedQueue<String>();
	private boolean isAvailable;
	private int maxCapaCnt;
	
	public boolean changed(StkRmNode oe) {
		if (this.eqpId.equals(oe.eqpId) == false) {
			return true;
		}
	
		if (this.maxCapaCnt != oe.maxCapaCnt) {
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
	 * @param isAvailable
	 * @param maxCapaCnt
	 * @param batchFlush
	 */
	public StkRmNode(
						final String fabId, 
						final String id, 
						final String name, 
						final String eqpId,			
						final boolean isAvailable, 
						final int maxCapaCnt, 
						final boolean batchFlush,
						boolean isUpdate
	) {
		super(fabId, id, name, null, null, null, null, isUpdate);
		
		this.init(eqpId, isAvailable, maxCapaCnt);
	}
	
	public StkRmNode(
						String fabId, 
						String id, 
						String name, 
						String eqpId,
						ConcurrentLinkedQueue<String> fromEdgeIds, 
						ConcurrentLinkedQueue<String> toEdgeIds, 
						ConcurrentLinkedQueue<String> fromLongEdgeIds,
						ConcurrentLinkedQueue<String> toLongEdgeIds,
						ConcurrentLinkedQueue<String> carrierIdList,
						boolean isAvailable,
						int maxCapaCnt,
						boolean isUpdate
	) {
		super(fabId, id, name, fromEdgeIds, toEdgeIds, fromLongEdgeIds, toLongEdgeIds, isUpdate);

		this.carrierIdList = carrierIdList;
		
		this.init(eqpId, isAvailable, maxCapaCnt);
	}
	
	public StkRmNode(
						String fabId, 
						String id, 
						String name, 
						String eqpId,			
						boolean isAvailable,
						int maxCapaCnt,
						boolean isUpdate
	) {
		super(fabId, id, name, null, null, null, null, isUpdate);
		
		this.init(eqpId, isAvailable, maxCapaCnt);
	}
	
	/**
	 * The common function to initialize the local field of this class.
	 * @param eqpId
	 * @param isAvailable
	 * @param maxCapaCnt
	 */
	private void init(
						final String eqpId,			
						final boolean isAvailable, 
						final int maxCapaCnt
	) {
		this.eqpId 			= eqpId;
		this.maxCapaCnt 	= maxCapaCnt;
		this.isAvailable 	= isAvailable;
	}

	public String getEqpId() {
		return eqpId;
	}

	public void setEqpId(String eqpId) {
		this.eqpId = eqpId;
	}

	public ConcurrentLinkedQueue<String> getCarrierIdList() {
		return carrierIdList;
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

	public int getMaxCapaCnt() {
		return maxCapaCnt;
	}

	public void setMaxCapaCnt(int maxCapaCnt) {
		this.maxCapaCnt = maxCapaCnt;
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

	public ConcurrentLinkedQueue<String> getCommandIdList() {
		cleanCommandIdList();

		return commandIdList;
	}

	public void addCommandId(String commandId) {
		if (commandIdList.contains(commandId) == false) {
			commandIdList.add(commandId);
		}
	}
	
	public void cleanCommandIdList() {
		if(DataService.isBlocked.get()) {
			return;
		}
		
		Set<String> removalCmdIdSet = new HashSet<>();
		
		for (String cmdId : commandIdList) {
			
			Command cmd = DataService.getDataSet().getCommandMap().get(cmdId);
			
			if(cmd == null) {
				removalCmdIdSet.add(cmdId);
				continue;
			}

			Job job = DataService.getDataSet().getJobMap().get(cmd.getJobId());
			
			if (job == null) {
				removalCmdIdSet.add(cmdId);
				continue;
			}
			
			Carrier carrier = DataService.getDataSet().getCarrierMap().get(cmd.getCarrierId());
			
			if (carrier == null || eqpId.equals(carrier.getEqpId()) == false) {
				removalCmdIdSet.add(cmdId);
				
				continue;
			}
		}
	
		if (removalCmdIdSet.size() > 0) {
			commandIdList.removeAll(removalCmdIdSet);
		}
	}
	
	public void removeCommandId(String commandId) {
		cleanCommandIdList();
		
		commandIdList.remove(commandId);
	}
		
	public void setCommandIdList(ConcurrentLinkedQueue<String> commandIdList) {
		this.commandIdList = commandIdList;
	}

	@Override
	public String[] getCarrierIds() {
		return this.carrierIdList.toArray(new String[this.carrierIdList.size()]);
	}
}