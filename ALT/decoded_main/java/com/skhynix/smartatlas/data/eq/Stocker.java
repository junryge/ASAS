package com.skhynix.smartatlas.data.eq;

import java.util.Set;
import java.util.concurrent.ConcurrentLinkedQueue;

import org.apache.commons.lang3.StringUtils;

import com.skhynix.smartatlas.data.Carrier.PROCESS_TYPE;
import com.skhynix.smartatlas.data.DataSet;
import com.skhynix.smartatlas.map.node.StkRmNode;
import com.skhynix.smartatlas.map.node.StkShelfNode;
import com.skhynix.smartatlas.util.DataService;

public class Stocker extends Eqp{
	private String shelfNodeId 	= "";
	private String rmId 		= "";
	private boolean isN2 		= false;
	private STK_TYPE stkType 	= STK_TYPE.NA;
	private boolean isFull 		= false; // MCS로 부터 수신
	private int maxCapaCnt 		= -1; // MCS로 부터 수신
	private int occupancyCnt 	= -1;	// MCS로 부터 수신
	
	
	public Stocker(
					String fabId,
					String id, 
					String name, 
					Set<PROCESS_TYPE> processTypeSet, 
					ConcurrentLinkedQueue<String> portNodeIdList,
					String shelfNodeId, 
					String rmId,
					boolean isN2, 
					STK_TYPE stkType,
					boolean isAvailable, 
					boolean isUpdate, 
					String mcsBayNm
	) {
		super(fabId, id, name, EQP_TYPE.STK, processTypeSet, portNodeIdList, isAvailable, isUpdate, mcsBayNm);
		
		this.shelfNodeId 	= shelfNodeId;
		this.rmId 			= rmId;
		this.isN2 			= isN2;
		this.stkType 		= stkType;
//		if(isUpdate) return;
//		RedisPool.jset(this.id, this);
//		RedisPool.getJedisCluster().sadd("Stocker", this.id);
//		
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.CREATE, getClass().getName(), this));
	}	
	
	public ConcurrentLinkedQueue<String> getPortNodeIdList() {
		return portNodeIdList;
	}
	
	public void setPortNodeIdList(ConcurrentLinkedQueue<String> portNodeIdList) {
		this.portNodeIdList = portNodeIdList;
	}
	
	public String getShelfNodeId() {
		return shelfNodeId;
	}
	
	public void setShelfNodeId(String shelfNodeId) {
		this.shelfNodeId = shelfNodeId;
	}
	
	public String getRmId() {
		return rmId;
	}
	
	public void setRmId(String rmId) {
		this.rmId = rmId;
	}
	
	public Set<PROCESS_TYPE> getProcessTypeSet() {
		return processTypeSet;
	}
	
	public void setProcessTypeSet(Set<PROCESS_TYPE> processTypeSet) {
		this.processTypeSet = processTypeSet;
//		if(isUpdate) return;
//		RedisPool.jset(this.id, processTypeSet, new Path(".processTypeSet"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "processTypeSet", this.id, this.processTypeSet, new TypeToken<Set<PROCESS_TYPE>>() {}.getType()));
	}

	public boolean isN2() {
		return isN2;
	}

	public void setN2(boolean isN2) {
		this.isN2 = isN2;
//		if(isUpdate) return;
//		RedisPool.jset(this.id, isN2, new Path(".isN2"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "isN2", this.id, new Boolean(this.isN2), new TypeToken<Boolean>() {}.getType()));
	}
	
	public STK_TYPE getStkType() {
		return stkType;
	}

	public void setStkType(STK_TYPE stkType) {
		this.stkType = stkType;
//		if(isUpdate) return;
//		RedisPool.jset(this.id, stkType, new Path(".stkType"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "stkType", this.id, this.stkType, new TypeToken<STK_TYPE>() {}.getType()));
	}
	
	@Override
	public void removeCarrierId(String carrierId) {
		super.removeCarrierId(carrierId);
		StkRmNode srn = (StkRmNode)DataService.getDataSet().getNodeMap().get(rmId);
		
		srn.removeCarrierId(carrierId);
		
		if (StringUtils.isNotEmpty(shelfNodeId)) {
			StkShelfNode ssn = (StkShelfNode)DataService.getDataSet().getNodeMap().get(shelfNodeId);
			
			if (ssn != null) {
				ssn.removeCarrierId(carrierId);
			}
		}
//		else
//			LoggerFactory.getLogger(getClass()).warn("{} could not removed on {} that is not existing StkShelfNode of {}.", carrierId, shelfNodeId, this.id);
	}

	public enum STK_TYPE{NA,PODZIPTOWER,LIFTER,ZIPTOWER,INTERAILSEMITS,INTERLAYER,RETICLE,INTERRAILSTORAGE}//20210413 KKH RETICLE Stocker는  M16이전엔 NA로 구분되었음. 현재 혼용중

	public boolean isFull() {
		return isFull;
	}

	public void setFull(boolean isFull) {
		this.isFull = isFull;
//		if(isUpdate) return;
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "isFull", this.id, new Boolean(this.isFull), new TypeToken<Boolean>() {}.getType()));
	}

	public int getMaxCapaCnt() {
		if(this.maxCapaCnt < 0) {
			if(StringUtils.isNotEmpty(this.shelfNodeId)) {
				StkShelfNode ssn = (StkShelfNode)DataService.getDataSet().getNodeMap().get(this.shelfNodeId);
				if(ssn == null) {
					this.maxCapaCnt = 0;
					this.occupancyCnt = 0;
				}else {
					this.maxCapaCnt = ssn.getMaxCapaCnt();
					this.occupancyCnt = ssn.getCarrierIdList().size();
				}
			}else {
				this.maxCapaCnt = 0;
				this.occupancyCnt = 0;
			}
		}
		return maxCapaCnt;
	}

	public void setMaxCapaCnt(int maxCapaCnt) {
		this.maxCapaCnt = maxCapaCnt;
//		if(isUpdate) return;
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "maxCapaCnt", this.id, new Integer(this.maxCapaCnt), new TypeToken<Integer>() {}.getType()));
	}

	
	public int getOccupancyCnt(DataSet dataSet) {
		if(this.occupancyCnt < 0) {
			if(StringUtils.isNotEmpty(this.shelfNodeId)) {
				StkShelfNode ssn = (StkShelfNode) dataSet.getNodeMap().get(this.shelfNodeId);
				if(ssn == null) {
					this.maxCapaCnt = 0;
					this.occupancyCnt = 0;
				}else {
					this.maxCapaCnt = ssn.getMaxCapaCnt();
					this.occupancyCnt = ssn.getCarrierIdList().size();
				}
			}else {
				this.maxCapaCnt = 0;
				this.occupancyCnt = 0;
			}
		}
		return occupancyCnt;
	}

	public void setOccupancyCnt(int occupancyCnt) {
		this.occupancyCnt = occupancyCnt;
//		if(isUpdate) return;
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "occupancyCnt", this.id, new Integer(this.occupancyCnt), new TypeToken<Integer>() {}.getType()));
	}

}
