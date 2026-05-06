public class StbNode extends AbstractNode implements CarrierContainable {
	private Set<PROCESS_TYPE> processTypeSet	= new HashSet<PROCESS_TYPE>();
	private String carrierId 					= "";
	private boolean isAvailable 				= true; // 사용가능한지. Carrier가 있건 없건 상관없이 막아놓거나 Down 등이 아니면 True
	private boolean isN2 						= false;
	private String eqpId 						= "";
	private long occupiedTime;
	private boolean isReaderPort 				= false;
	
	public boolean changed(StbNode oe) {
		if (this.eqpId.equals(oe.eqpId) == false) 	{
			return true;
		}
		
		if (this.isN2 != oe.isN2) {
			return true;
		}
		
		if (this.isReaderPort != oe.isReaderPort) {
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
	 * @param isAvailable
	 * @param isN2
	 * @param eqpId
	 * @param isReaderPort
	 * @param batchFlush
	 */
	public StbNode(
					final String fabId, 
					final String id, 
					final String name,
					final boolean isAvailable,
					final boolean isN2,
					final String eqpId,
					final boolean isReaderPort,
					final boolean batchFlush, boolean isUpdate
	) {
		super(fabId, id, name, null, null, null, null, isUpdate);
		
		this.init(isAvailable, isN2, eqpId, isReaderPort);
	}
	
	public StbNode(
					String fabId, 
					String id, 
					String name,
					ConcurrentLinkedQueue<String> fromEdgeIds, 
					ConcurrentLinkedQueue<String> toEdgeIds, 
					ConcurrentLinkedQueue<String> fromLongEdgeIds,
					ConcurrentLinkedQueue<String> toLongEdgeIds,
					Set<PROCESS_TYPE> processTypeSet, 
					String carrierId,
					boolean isAvailable,
					boolean isN2,
					String eqpId,
					boolean isReaderPort,
					boolean isUpdate
	) {
		super(fabId, id, name, fromEdgeIds, toEdgeIds, fromLongEdgeIds, toLongEdgeIds, isUpdate);
		
		this.setProcessTypeSet(processTypeSet);
	
		this.carrierId = carrierId;
		
		this.init(isAvailable, isN2, eqpId, isReaderPort);
	}
	
	public StbNode(
					String fabId,
					String id, 
					String name,
					boolean isAvailable,
					boolean isN2,
					String eqpId,
					boolean isReaderPort,
					boolean isUpdate
	) {
		super(fabId, id, name, null, null, null, null, isUpdate);
		
		this.init(isAvailable, isN2, eqpId, isReaderPort);
	}
	
	/**
	 * A constructor to set the batchFlush with the initialization to other fields.
	 * @param isAvailable
	 * @param isN2
	 * @param eqpId
	 * @param isReaderPort
	 */
	private void init(
						final boolean isAvailable,
						final boolean isN2,
						final String eqpId,
						final boolean isReaderPort
	) {
		this.isAvailable 	= isAvailable;
		this.isN2			= isN2;
		this.eqpId			= eqpId;
		this.isReaderPort 	= isReaderPort;
		this.isTerminal 	= true;
	}

	public String getCarrierId() {
		return carrierId;
	}

	public void setCarrierId(String carrierId) {
		this.carrierId = carrierId;
	}

	public boolean isAvailable() {
		return isAvailable;
	}

	public void setAvailable(boolean isAvailable) {
		this.isAvailable = isAvailable;
	}

	public boolean isN2() {
		return isN2;
	}

	public void setN2(boolean isN2) {
		this.isN2 = isN2;
	}

	public String getEqpId() {
		return eqpId;
	}

	public void setEqpId(String eqpId) {
		this.eqpId = eqpId;
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

	public boolean isReaderPort() {
		return isReaderPort;
	}

	public void setReaderPort(boolean isReaderPort) {
		this.isReaderPort = isReaderPort;
	}

	public Set<PROCESS_TYPE> getProcessTypeSet() {
		if (processTypeSet == null || processTypeSet.size() == 0) {
			return DataService.getDataSet().getStbGroupMap().get(eqpId).getProcessTypeSet();
		}
		
		return processTypeSet;
	}

	public void setProcessTypeSet(Set<PROCESS_TYPE> processTypeSet) {
		this.processTypeSet = processTypeSet;
	}

	@Override
	public void addCarrierId(String carrierId) {
		setCarrierId(carrierId);
	}
	
	@Override
	public void removeCarrierId(String carrierId) {
		setCarrierId("");		
	}

	@Override
	public String[] getCarrierIds() {
		if (StringUtils.isNotEmpty(this.carrierId)) {
			return new String[] {this.carrierId};
		}
		
		return new String[0];
	}
}
