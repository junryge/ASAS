package com.skhynix.smartatlas.map.node;

import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ConcurrentLinkedQueue;

import com.skhynix.smartatlas.data.Carrier.PROCESS_TYPE;
import com.skhynix.smartatlas.map.AbstractNode;
import com.skhynix.smartatlas.map.CarrierContainable;
import com.skhynix.smartatlas.util.DataService;
import com.skhynix.smartatlas.util.Util;

public class StkShelfNode extends AbstractNode  implements CarrierContainable {
	private String eqpId;
	private ConcurrentLinkedQueue<String> carrierIdList	= new ConcurrentLinkedQueue<String>();
	private int maxCapaCnt;
	private boolean isAvailable;
	private Set<PROCESS_TYPE> processTypeSet			= new HashSet<PROCESS_TYPE>();
	private boolean isN2;

	public boolean changed(StkShelfNode oe) {
		if (this.eqpId.equals(oe.eqpId) == false) {
			return true;
		}
		
		if (this.maxCapaCnt != oe.maxCapaCnt) {
			return true;
		}
		
		if (this.isN2 != oe.isN2) {
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
	 * @param maxCapaCnt
	 * @param isAvailable
	 * @param batchFlush
	 */
	public StkShelfNode(
						final String fabId, 
						final String id, 
						final String name,
						final String eqpId,
						final int maxCapaCnt,
						final boolean isAvailable,
						final boolean batchFlush,
						boolean isUpdate
	) {
		super(fabId, id, name, null, null, null, null, isUpdate);
		
		this.init(eqpId, maxCapaCnt, isAvailable);
	}
	
	public StkShelfNode(
						String fabId, 
						String id, 
						String name,
						ConcurrentLinkedQueue<String> fromEdgeIds, 
						ConcurrentLinkedQueue<String> toEdgeIds, 
						ConcurrentLinkedQueue<String> fromLongEdgeIds,
						ConcurrentLinkedQueue<String> toLongEdgeIds,
						String eqpId,
						ConcurrentLinkedQueue<String> carrierIdList,
						int maxCapaCnt,
						boolean isAvailable,
						Set<PROCESS_TYPE> processTypeSet,
						boolean isUpdate
	) {
		super(fabId, id, name, fromEdgeIds, toEdgeIds, fromLongEdgeIds, toLongEdgeIds, isUpdate);
		
		this.init(eqpId, maxCapaCnt, isAvailable);
		
		this.carrierIdList = carrierIdList;
		this.processTypeSet = processTypeSet;
	}
	
	public StkShelfNode(
						String fabId, 
						String id, 
						String name,
						String eqpId,
						int maxCapaCnt,
						boolean isAvailable,
						boolean isUpdate
	) {
		super(fabId, id, name, null, null, null, null, isUpdate);

		this.init(eqpId, maxCapaCnt, isAvailable);
	}

	/**
	 * The common function to initialize the local field of this class.
	 * @param eqpId
	 * @param maxCapaCnt
	 * @param isAvailable
	 */
	private void init(final String eqpId,
					  final int maxCapaCnt,
					  final boolean isAvailable) {
		this.eqpId = eqpId;
		this.maxCapaCnt = maxCapaCnt;
		this.isAvailable = isAvailable;
		this.isTerminal = true;
	}

	public ConcurrentLinkedQueue<String> getCarrierIdList() {
		return carrierIdList;
	}

	public void setCarrierIdList(ConcurrentLinkedQueue<String> carrierIdList) {
		this.carrierIdList = carrierIdList;
//		if(isUpdate) return;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, carrierIdList, new Path(".carrierIdList"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "carrierIdList", this.id, this.carrierIdList, new TypeToken<ConcurrentLinkedQueue<String>>() {}.getType()));
	}

	public boolean isAvailable() {
		return isAvailable;
	}

	public void setAvailable(boolean isAvailable) {
		this.isAvailable = isAvailable;
//		if(isUpdate) return;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, isAvailable, new Path(".isAvailable"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "isAvailable", this.id, new Boolean(this.isAvailable), new TypeToken<Boolean>() {}.getType()));
	}

	public String getEqpId() {
		return eqpId;
	}

	public int getMaxCapaCnt() {
		return maxCapaCnt;
	}

	public Set<PROCESS_TYPE> getProcessTypeSet() {
		return processTypeSet;
	}

	public void setProcessTypeSet(Set<PROCESS_TYPE> processTypeSet) {
		this.processTypeSet = processTypeSet;
//		if(isUpdate) return;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, processTypeSet, new Path(".processTypeSet"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "processTypeSet", this.id, this.processTypeSet, new TypeToken<Set<PROCESS_TYPE>>() {}.getType()));
	}

	public boolean isN2() {
		return DataService.getDataSet().getStockerMap().get(eqpId).isN2();
	}

	public void setN2(boolean isN2) {
		this.isN2 = isN2;
//		if(isUpdate) return;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, isN2, new Path(".isN2"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "isN2", this.id, new Boolean(this.isN2), new TypeToken<Boolean>() {}.getType()));
	}

	public void setEqpId(String eqpId) {
		this.eqpId = eqpId;
//		if(isUpdate) return;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, eqpId, new Path(".eqpId"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "eqpId", this.id, this.eqpId, new TypeToken<String>() {}.getType()));
	}

	public void setMaxCapaCnt(int maxCapaCnt) {
		this.maxCapaCnt = maxCapaCnt;
//		if(isUpdate) return;
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, maxCapaCnt, new Path(".maxCapaCnt"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "maxCapaCnt", this.id, new Integer(this.maxCapaCnt), new TypeToken<Integer>() {}.getType()));
	}
	
	@Override
	public void addCarrierId(String carrierId) {
		if(carrierIdList.contains(carrierId)==false) {
			carrierIdList.add(carrierId);
//			if (!this.batchFlush)
//				RedisPool.jset(this.id, carrierIdList, new Path(".carrierIdList"));
//			AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.ADD_COLLECTION_ITEM, getClass().getName(), "carrierIdList", this.id, carrierId, new TypeToken<String>() {}.getType()));
		}
	}
	
	@Override
	public void removeCarrierId(String carrierId) {
		carrierIdList.remove(carrierId);
//		if (!this.batchFlush)
//			RedisPool.jset(this.id, carrierIdList, new Path(".carrierIdList"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.REMOVE_COLLECTION_ITEM, getClass().getName(), "carrierIdList", this.id, carrierId, new TypeToken<String>() {}.getType()));
	}

	@Override
	public String[] getCarrierIds() {
		// TODO Auto-generated method stub
		return this.carrierIdList.toArray(new String[this.carrierIdList.size()]);
	}
	
}
