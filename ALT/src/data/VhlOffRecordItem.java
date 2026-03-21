public class VhlOffRecordItem {
	private final Logger logger = LoggerFactory.getLogger(getClass());

	private final String id;
	private final String deviceId;
	private final String fabId;
	private final String facId;
	private final String mcpName;
	private final String machineId;
	//	├─ format: {vehicleId}:{stopAddress}:{alarmCode}
	//	├─ example: V00001:4331:9600
	//	└─ 'stopAddress' 는 현재 위치(fromAddress)
	private long eventDateTime;		// 20250708 ATLAS_OHT_VHL_OFF_ONLY 대응
	private long recoveryDateTime = -1;	// 20250708 ATLAS_OHT_VHL_OFF_ONLY 대응
	private int stoppedFromAddress;
	private int stoppedToAddress;
	private List<String> affectedPort;
	private Set<String> affectedAddress;
	private String state;
	private String errorCode;
	private boolean isChanged = true;
	private double velocity = -1;

	public VhlOffRecordItem(
			String id,
			String deviceId,
			String fabId,
			String facId,
			String mcpName,
			String machineId,
			int stoppedFromAddress,
			int stoppedToAddress,
			List<String> affectedPort,
			Set<String> affectedAddress,
			String state,
			String errorCode,
			long eventTime
	) {
		this.id				= id;
		this.deviceId		= deviceId;
		this.fabId			= fabId;
		this.facId			= facId;
		this.mcpName		= mcpName;
		this.machineId		= machineId;
		this.stoppedFromAddress	= stoppedFromAddress;
		this.stoppedToAddress = stoppedToAddress;
		this.affectedPort = affectedPort;
		this.affectedAddress = affectedAddress;
		this.state			= state;
		this.errorCode 		= errorCode;

		this.setEventDateTime(eventTime);
	}

	public void setAffectedPort (List<String> affectedPort) {
		this.affectedPort = affectedPort;
	}

	public void setAffectedAddress (Set<String> affectedAddress) {
		this.affectedAddress = affectedAddress;
	}

	public void setStoppedFromAddress (int stoppedFromAddress) {
		this.stoppedFromAddress = stoppedFromAddress;
	}

	public void setStoppedToAddress (int stoppedToAddress) {
		this.stoppedToAddress = stoppedToAddress;
	}

	public void setState(String state) {
		this.state = state;
	}

	public void setErrorCode(String errorCode) {
		this.errorCode = errorCode;
	}

	public String getFabId () {
		return fabId;
	}

	public String getFacId () {
		return facId;
	}

	public String getId () {
		return id;
	}

	public List<String> getAffectedPort () {
		return affectedPort;
	}

	public Set<String> getAffectedAddress () {
		return affectedAddress;
	}

	public String getState() {
		return state;
	}

	public String getAlarmType () {
		return SEND_SUB_SUBJECT.VHL_OFF;
	}

	public String getErrorCode() {
		return errorCode;
	}

	public String getAffectedAddressString () {
		if (this.affectedAddress == null || this.affectedAddress.isEmpty()) return "";

		return affectedAddress.stream()
				.filter(address -> !address.isEmpty())
				.collect(Collectors.joining(","));
	}

	public String getAffectedPortString () {
		if (this.affectedPort == null || this.affectedPort.isEmpty()) return "";

		return affectedPort.stream()
				.filter(port -> !port.isEmpty())
				.collect(Collectors.joining(","));
	}

	public String getDeviceId () {
		return deviceId;
	}

	public Integer getStoppedFromAddress () {
		return stoppedFromAddress;
	}

	public Integer getStoppedToAddress () {
		return stoppedToAddress;
	}

	public String getStoppedAddressString () {
		return String.format("%d:%d", stoppedFromAddress, stoppedToAddress);
	}

	public RailEdge getRailEdge () {
		RailEdge railEdge = null;
		String railEdgeId = "";

		try {
			FabProperties fabProperties = DataService.getInstance().getFabPropertiesMap().get(fabId);

			if (fabProperties != null) {
				railEdgeId = DataSet.address2RailEdgeId(fabId, mcpName, stoppedFromAddress, stoppedToAddress);

				if (DataService.getDataSet().getRailEdgeMap() != null && DataService.getDataSet().getRailEdgeMap().containsKey(railEdgeId)) {
					railEdge = DataService.getDataSet().getRailEdgeMap().get(railEdgeId);
				} else {
					logger.warn("... Not matching the railEdgeId. (railEdgeId: {}) !", railEdgeId);
				}
			}
		} catch (Exception e) {
			logger.error("... An error occurred while making or matching railEdge data (fab: {} / railEdgeId: {}) !!!", this.fabId, railEdgeId, e);
		}

		return railEdge;
	}

	public String getMachineId () {
		return machineId;
	}

	public void setEventDateTime(long eventDateTime) {
		this.eventDateTime = eventDateTime;
	}

	public void setRecoveryDateTime(long recoveryDateTime) {
		this.recoveryDateTime = recoveryDateTime;
	}

	public long getEventDateTime () {
		return eventDateTime;
	}

	public long getRecoveryDateTime () {
		return recoveryDateTime;
	}

	public String getEventDateTimeString () {
		return _dateTimeHandler(eventDateTime);
	}

	public String getRecoveryDateTimeString () {
		return _dateTimeHandler(recoveryDateTime);
	}

	private String _dateTimeHandler(long currentDateTime) {
		LocalDateTime dateTime = LocalDateTime.ofInstant(Instant.ofEpochMilli(currentDateTime), ZoneId.systemDefault());
		DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

		return dateTime.format(formatter);
	}

	// 20250708 해당 데이터를 remove 하지 않고 남겨두는 대신 isChanged 로 logpresso 저장 등 동작을 구분
	public void setChanged(boolean isChanged) {
		this.isChanged = isChanged;
	}

	public boolean getChanged() {
		return this.isChanged;
	}

	public void setVelocity(double velocity) {
		this.velocity = velocity;
	}

	public double getVelocity() {
		return this.velocity;
	}

	public String getMcpName() {
		return mcpName;
	}
}
