public class StbGroup extends Eqp {
	private boolean isN2 		= false;
	private boolean isFull 		= false; // MCS로 부터 수신
	private int maxCapaCnt 		= -1; // MCS로 부터 수신
	private int occupancyCnt 	= -1;	// MCS로 부터 수신

	public StbGroup(String fabId, String id, String name, Set<PROCESS_TYPE> processTypeSet, ConcurrentLinkedQueue<String> portNodeIdList, boolean isN2, boolean isAvailable, boolean isUpdate, String mcsBayNm) {
		super(fabId, id, name, EQP_TYPE.STBGROUP, processTypeSet, portNodeIdList, isAvailable, isUpdate, mcsBayNm);
		
		this.isN2 = isN2;
	}

	public boolean isN2() {
		return isN2;
	}

	public void setN2(boolean isN2) {
		this.isN2 = isN2;
	}
	
	public List<StbNode> getAvailableStbNodeList(){
		List<StbNode> snl = new ArrayList<StbNode>();
		
		for (String portNodeId : portNodeIdList) {
			StbNode sn = (StbNode)DataService.getDataSet().getNodeMap().get(portNodeId);
			
			if (
					sn.isEmpty() 
					&& sn.isAvailable() 
					&& sn.isReaderPort() == false
			) {
				snl.add(sn);
			}
		}
		return snl;
	}
	
	public StbNode getAnyAvailableStbNode(){
		for(String portNodeId : portNodeIdList) {
			StbNode sn = (StbNode)DataService.getDataSet().getNodeMap().get(portNodeId);
			if(sn.isEmpty() && sn.isAvailable() && sn.isReaderPort() == false) {
				return sn;
			}
		}
		return null;
	}
	
	public boolean isFull() {
		return isFull;
	}

	public void setFull(boolean isFull) {
		this.isFull = isFull;
//		if(isUpdate) return;
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "isFull", this.id, new Boolean(this.isFull), new TypeToken<Boolean>() {}.getType()));
	}

	public int getMaxCapaCnt() {
		if(maxCapaCnt < 0) {
			int maxCapa = 0;
			int occupancy = 0;
			for(String portNodeId : portNodeIdList) {
				StbNode sn = (StbNode)DataService.getDataSet().getNodeMap().get(portNodeId);
				if(sn.isAvailable() && sn.isReaderPort() == false) {
					maxCapa++;
					if(sn.isEmpty()==false){
						occupancy++;
					}
				}
				this.maxCapaCnt = maxCapa;
				this.occupancyCnt = occupancy;
			}
		}
		return maxCapaCnt;
	}

	public void setMaxCapaCnt(int maxCapaCnt) {
		this.maxCapaCnt = maxCapaCnt;
//		if(isUpdate) return;
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "maxCapaCnt", this.id, new Integer(this.maxCapaCnt), new TypeToken<Integer>() {}.getType()));
	}

	public int getOccupancyCnt() {
		if(this.occupancyCnt < 0) {
			int maxCapa = 0;
			int occupancy = 0;
			for(String portNodeId : portNodeIdList) {
				StbNode sn = (StbNode)DataService.getDataSet().getNodeMap().get(portNodeId);
				if(sn.isAvailable() && sn.isReaderPort() == false) {
					maxCapa++;
					if(sn.isEmpty()==false){
						occupancy++;
					}
				}
				this.maxCapaCnt = maxCapa;
				this.occupancyCnt = occupancy;
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
