//import com.skhynix.smartatlas.data.PredictionPara;
import com.skhynix.smartatlas.map.AbstractNode;
import com.skhynix.smartatlas.map.CarrierContainable;
import com.skhynix.smartatlas.util.JsonToStringBuilder;
import com.skhynix.smartatlas.util.JsonUtil;
import com.skhynix.smartatlas.util.Util;

public class StkPortNode extends AbstractNode  implements CarrierContainable {
	private String eqpId;
	private ConcurrentLinkedQueue<SubPort> subPortList 	= new ConcurrentLinkedQueue<StkPortNode.SubPort>(); 
	private ConcurrentLinkedQueue<String> carrierIdList = new ConcurrentLinkedQueue<String>();
	private int maxCapaCnt;
	private long avgRemovalIntervalT 					= 30000L;
	private int floorNo;
	private Set<PROCESS_TYPE> processTypeSet			= new HashSet<PROCESS_TYPE>();
	private boolean isAvailable;
	private STK_PORT_INOUT_TYPE inOutType;
	private String ohtFabId 							= "";
	private String ohtMcpNm 							= "";
	
	public boolean changed(StkPortNode oe) {
		if (this.eqpId.equals(oe.eqpId) == false) 	return true;
		
		if (this.inOutType != oe.inOutType) 		return true;
		
		if (this.maxCapaCnt != oe.maxCapaCnt) 		return true;
		
		if (this.floorNo != oe.floorNo) 			return true;
		
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
	 * @param maxCapaCnt
	 * @param floorNo
	 * @param inOutType
	 * @param isAvailable
	 * @param batchFlush
	 */
	public StkPortNode(
						final String fabId, 
						final String id, 
						final String name,
						final String eqpId,
						final int maxCapaCnt,
						final int floorNo,
						final STK_PORT_INOUT_TYPE inOutType,
						final boolean isAvailable,
						final boolean batchFlush,
						boolean isUpdate
	) {
		super(fabId, id, name, null, null, null, null, isUpdate);
		
		this.init(eqpId, maxCapaCnt, floorNo, inOutType, isAvailable);
	}

	public StkPortNode(
						String fabId, 
						String id, 
						String name,
						ConcurrentLinkedQueue<String> fromEdgeIds, 
						ConcurrentLinkedQueue<String> toEdgeIds, 
						ConcurrentLinkedQueue<String> fromLongEdgeIds,
						ConcurrentLinkedQueue<String> toLongEdgeIds,
						ConcurrentLinkedQueue<String> carrierIdList,
						String eqpId,
						int maxCapaCnt,
						long avgRemovalIntervalT,
						int floorNo,
						Set<PROCESS_TYPE> processTypeSet,
						STK_PORT_INOUT_TYPE inOutType,
						boolean isAvailable,
						boolean isUpdate
	) {
		super(fabId, id, name, fromEdgeIds, toEdgeIds, fromLongEdgeIds, toLongEdgeIds, isUpdate);
		
		this.carrierIdList = carrierIdList;
	}

	public StkPortNode(
						String fabId, 
						String id, 
						String name,
						String eqpId,
						int maxCapaCnt,
						int floorNo,
						STK_PORT_INOUT_TYPE inOutType,
						boolean isAvailable,
						boolean isUpdate
	) {
		super(fabId, id, name, null, null, null, null, isUpdate);
		
		this.init(eqpId, maxCapaCnt, floorNo, inOutType, isAvailable);
	}

	/**
	 * The common function to initialize the local field of this class.
	 * @param eqpId
	 * @param maxCapaCnt
	 * @param floorNo
	 * @param inOutType
	 * @param isAvailable
	 */
	private void init(
						final String eqpId,
						final int maxCapaCnt,
						final int floorNo,
						final STK_PORT_INOUT_TYPE inOutType,
						final boolean isAvailable
	) {
		this.eqpId			= eqpId;
		this.maxCapaCnt 	= maxCapaCnt;
		this.floorNo 		= floorNo;
		this.inOutType 		= inOutType;
		this.isAvailable 	= isAvailable;
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

	public long getAvgRemovalIntervalT() {
		if (avgRemovalIntervalT <= 0 || avgRemovalIntervalT > 120000) {
			this.setAvgRemovalIntervalT(30000);
		}
		
		return avgRemovalIntervalT;
	}

	public void setAvgRemovalIntervalT(long avgRemovalIntervalT) {
		if (avgRemovalIntervalT <= 0 || avgRemovalIntervalT > 120000) {
			this.avgRemovalIntervalT = 30000;
		} else {
			this.avgRemovalIntervalT = avgRemovalIntervalT;
		}
	}
	
//	public void addRemovalIntervalT(long avgRemovalIntervalT) {		
//		this.setAvgRemovalIntervalT((long)(this.avgRemovalIntervalT * PredictionPara.getInstance().getLastHisWeight() + avgRemovalIntervalT * (1-PredictionPara.getInstance().getLastHisWeight())));		
//	}

	public int getMaxCapaCnt() {
		return maxCapaCnt;
	}

	public int getFloorNo() {
		return floorNo;
	}
	public ConcurrentLinkedQueue<SubPort> getSubPortList() {
		return subPortList;
	}

	public void setSubPortList(ConcurrentLinkedQueue<SubPort> subPortList) {
		this.subPortList = subPortList;
	}

	public class SubPort implements Comparable<SubPort>{
		public STK_SUB_PORT_TYPE type	= STK_SUB_PORT_TYPE.LP;
		public String name				= "";
		
		public SubPort(STK_SUB_PORT_TYPE type, String name){
			this.type = type;
			this.name = name;
		}
		
		@Override
		public String toString() {
			JsonToStringBuilder builder = new JsonToStringBuilder(this);
			
			builder.append("type", type);
			builder.append("name", name);
		
			return builder.toString();
		}
		
		@Override
		public int compareTo(SubPort o) {			
			return this.name.compareTo(o.name);
		}
	}
	
	public enum STK_SUB_PORT_TYPE{LP,BP,OP}
	
	public enum STK_PORT_INOUT_TYPE{IN,OUT}

	public void setEqpId(String eqpId) {
		this.eqpId = eqpId;
	}

	public void setMaxCapaCnt(int maxCapaCnt) {
		this.maxCapaCnt = maxCapaCnt;
	}

	public void setFloorNo(int floorNo) {
		this.floorNo = floorNo;
	}

	public boolean isAvailable() {
		return isAvailable;
	}

	public void setAvailable(boolean isAvailable) {
		this.isAvailable = isAvailable;
	}

	public STK_PORT_INOUT_TYPE getInOutType() {
		return inOutType;
	}

	public void setInOutType(STK_PORT_INOUT_TYPE inOutType) {
		this.inOutType = inOutType;
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

	public String getOhtFabId() {		
		return ohtFabId;
	}

	public void setOhtFabId(String ohtFabId) {
		this.ohtFabId = ohtFabId;
	}

	public String getOhtMcpNm() {
		return ohtMcpNm;
	}

	public void setOhtMcpNm(String ohtMcpNm) {
		this.ohtMcpNm = ohtMcpNm;
	}
}
