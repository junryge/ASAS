public class Oht extends Eqp {
	private ConcurrentLinkedQueue<String> vhlIdList 	= new ConcurrentLinkedQueue<String>();
	private ConcurrentLinkedQueue<String> stationIdList	= new ConcurrentLinkedQueue<String>();
	
	private String controlState;	
	private String tscState;
	private String alarmState;
	private long receivedTime;
	private String lastControlState;	
	private String lastTscState;
	private String lastAlarmState;
	private long lastReceivedTime;
	private String mcpName 								= "";
	
	public Oht(
				String fabId, 
				String id, 
				String name, 
				String mcpName, 
				ConcurrentLinkedQueue<String> stationIdList, 
				ConcurrentLinkedQueue<String> vhlIdList, 
				boolean isAvailable, 
				boolean isUpdate
	) {
		super(fabId, id, name, EQP_TYPE.OHT, new HashSet<PROCESS_TYPE>(), null, isAvailable, isUpdate, "NA");
		
		processTypeSet.add(PROCESS_TYPE.ALL);
		
		this.mcpName 		= mcpName;
		this.stationIdList 	= stationIdList;
		this.vhlIdList 		= vhlIdList;
	}

	public ConcurrentLinkedQueue<String> getVhlIdList() {
		return vhlIdList;
	}

	public void setVhlIdList(ConcurrentLinkedQueue<String> vhlIdList) {
		this.vhlIdList = vhlIdList;
	}

	public ConcurrentLinkedQueue<String> getStationIdList() {
		return stationIdList;
	}

	public void setStationIdList(ConcurrentLinkedQueue<String> stationIdList) {
		this.stationIdList = stationIdList;
	}

	public String getControlState() {
		return controlState;
	}

	public void setControlState(String controlState) {
		this.controlState = controlState;
	}

	public String getTscState() {
		return tscState;
	}

	public void setTscState(String tscState) {
		this.tscState = tscState;
	}

	public String getAlarmState() {
		return alarmState;
	}

	public void setAlarmState(String alarmState) {
		this.alarmState = alarmState;
	}

	public long getReceivedTime() {
		return receivedTime;
	}

	public void setReceivedTime(long receivedTime) {
		this.receivedTime = receivedTime;
	}

	public String getLast_controlState() {
		return lastControlState;
	}

	public void setLastControlState(String lastControlState) {
		this.lastControlState = lastControlState;
	}

	public String getLastTscState() {
		return lastTscState;
	}

	public void setLastTscState(String lastTscState) {
		this.lastTscState = lastTscState;
	}

	public String getLastAlarmState() {
		return lastAlarmState;
	}

	public void setLastAlarmState(String lastAlarmState) {
		this.lastAlarmState = lastAlarmState;
	}

	public long getLastReceivedTime() {
		return lastReceivedTime;
	}

	public void setLastReceivedTime(long lastReceivedTime) {
		this.lastReceivedTime = lastReceivedTime;
	}
	
	@Override
	public void removeCarrierId(String carrierId) {
		for (String vhlId : this.vhlIdList) {
			Vhl v = DataService.getDataSet().getVhlMap().get(vhlId);
			
			v.removeCarrierId(carrierId);
		}
	}

	public String getMcpName() {
		return mcpName;
	}

	public void setMcpName(String mcpName) {
		this.mcpName = mcpName;
	}
}
