public class HidOffRecordItem {
	private final Logger logger = LoggerFactory.getLogger(getClass());

	private final String id;	// {fabId}:{hidId}
	private final String fabId;
	private final String facId;
	private final String mcpName;
	private final String deviceId;
	private final int hidId;
	private final Date eventDateTime;
	private final int stoppedFromAddress;
	private final int stoppedToAddress;
	private Set<String> hidAreaAddress;
	private List<String> affectedPort;
	private String state;
	private final String errorCode;
	private final String alarmCode;	// chatbot 의 도면을 호출하기 위한 코드 (ex: "HID011")

	public HidOffRecordItem(
			String id,
			String fabId,
			String facId,
			String mcpName,
			String deviceId,
			int hidId,
			int stoppedFromAddress,
			int stoppedToAddress,
			Set<String> hidAreaAddress,
			List<String> affectedPort,
			String state,
			String errorCode,
			String alarmCode,
			long eventTime
	) {
		this.id				= id;
		this.fabId			= fabId;
		this.facId			= facId;
		this.mcpName			= mcpName;
		this.deviceId		= deviceId;
		this.hidId			= hidId;
		this.stoppedFromAddress	= stoppedFromAddress;
		this.stoppedToAddress	= stoppedToAddress;
		this.hidAreaAddress	= hidAreaAddress;
		this.affectedPort 	= affectedPort;
		this.state			= state;
		this.errorCode 		= errorCode;
		this.alarmCode 		= alarmCode;
		this.eventDateTime	= new Date(eventTime);
	}

	public void setState (String state) {
		this.state = state;
	}

	public void setAffectedPort (List<String> affectedPort) {
		this.affectedPort = affectedPort;
	}

	public void setHidAreaAddress (Set<String> hidAreaAddress) {
		this.hidAreaAddress = hidAreaAddress;
	}

//		public void setAlarmCode(String alarmCode) {
//			this.alarmCode = alarmCode;
//		}

//		public void setErrorCode(String errorCode) {
//			this.errorCode = errorCode;
//		}

//	public void setHidId (int hidId) {
//		this.hidId = hidId;
//	}

	public String getFabId () {
		return fabId;
	}

	public String getFacId () {
		return facId;
	}

	public Integer getHidId () {
		return hidId;
	}

	public String getHidIdString () {
		return String.valueOf(hidId);
	}

	public String getState () {
		return state;
	}

	public String getAlarmType () {
		return SEND_SUB_SUBJECT.HID_OFF;
	}

	public String getAlarmCode() {
		return alarmCode;
	}

	public String getErrorCode() {
		return errorCode;
	}

	public String getId () {
		return id;
	}

//		public int getStoppedFromAddress () {
//			return stoppedFromAddress;
//		}

//		public int getStoppedToAddress () {
//			return stoppedToAddress;
//		}

//		public Set<String> getHidAreaAddress () {
//			return hidAreaAddress;
//		}

//		public List<String> getAffectedPort () {
//			return affectedPort;
//		}

	public String getHidAreaAddressString () {
		if (this.hidAreaAddress == null || this.hidAreaAddress.isEmpty()) return "";

		return hidAreaAddress.stream()
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
					logger.warn("... Not matching the railEdgeId (railEdgeId: {}) !", railEdgeId);
				}
			}
		} catch (Exception e) {
			logger.error("... An error occurred while making or matching railEdge data (fab: {} / railEdgeId: {}) !!!", this.fabId, railEdgeId, e);
		}

		return railEdge;
	}

//		public Date getEventDateTime () {
//			return eventDateTime;
//		}

	public String getEventDateTimeString () {
		SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

		return dateFormat.format(this.eventDateTime);
	}

	public String getMcpName() {
		return mcpName;
	}
}
