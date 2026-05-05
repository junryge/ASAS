public class RawVhlType {
	private int type;
	private String vhlCode; 				// VEHICLE machine code
	private int carrierType; 				// Transport Carrier Type: Numerical value [0-32] corresponding to STATION where transfer can be executed (multiple types can be specified)
	private int runningAreaType; 			// Travel Range Type:Numerical value [0-32] corresponding to the range where VHL can travel
	private long minDistance; 				// Minimum distance between vehicles[mm]
	private long offlineTimer; 				// Monitoring time [msec] from communication cut-off report from VehicleHandler to communication error
	private boolean carrierTypeMoving; 		// Transport carrier type change of the vehicle
	private String vhlCodeName;				// VehicleType(machine type)name configurable up to 16BYTES
	private int varVhlType;  				// HOST notification variable vehicleType values
	private String bumpDisableCarrierType;	// Transport carrier type non-targeted for bumping destination unconditionally: numerical value of the STATION transport carrier type non-targeted for bumping destination unconditionally [0-32]
	
	public RawVhlType(
						int type, 
						String vhlCode, 
						int carrierType, 
						int runningAreaType, 
						long minDistance, 
						long offlineTimer,
						boolean carrierTypeMoving, 
						String vhlCodeName, 
						int varVhlType, 
						String bumpDisableCarrierType
	) {
		super();
		
		this.type 					= type;
		this.vhlCode 				= vhlCode;
		this.carrierType 			= carrierType;
		this.runningAreaType 		= runningAreaType;
		this.minDistance 			= minDistance;
		this.offlineTimer 			= offlineTimer;
		this.carrierTypeMoving 		= carrierTypeMoving;
		this.vhlCodeName 			= vhlCodeName;
		this.varVhlType 			= varVhlType;
		this.bumpDisableCarrierType	= bumpDisableCarrierType;
	}
	
	public String getVhlCode() {
		return vhlCode;
	}
	
	public void setVhlCode(String vhlCode) {
		this.vhlCode = vhlCode;
	}
	
	public int getCarrierType() {
		return carrierType;
	}
	
	public void setCarrierType(int carrierType) {
		this.carrierType = carrierType;
	}
	
	public int getRunningAreaType() {
		return runningAreaType;
	}
	
	public void setRunningAreaType(int runningAreaType) {
		this.runningAreaType = runningAreaType;
	}
	
	public long getMinDistance() {
		return minDistance;
	}
	
	public void setMinDistance(long minDistance) {
		this.minDistance = minDistance;
	}
	
	public long getOfflineTimer() {
		return offlineTimer;
	}
	
	public void setOfflineTimer(long offlineTimer) {
		this.offlineTimer = offlineTimer;
	}
	
	public boolean isCarrierTypeMoving() {
		return carrierTypeMoving;
	}
	
	public void setCarrierTypeMoving(boolean carrierTypeMoving) {
		this.carrierTypeMoving = carrierTypeMoving;
	}
	
	public String getVhlCodeName() {
		return vhlCodeName;
	}
	
	public void setVhlCodeName(String vhlCodeName) {
		this.vhlCodeName = vhlCodeName;
	}
	
	public int getVarVhlType() {
		return varVhlType;
	}
	
	public void setVarVhlType(int varVhlType) {
		this.varVhlType = varVhlType;
	}
	
	public String getBumpDisableCarrierType() {
		return bumpDisableCarrierType;
	}
	
	public void setBumpDisableCarrierType(String bumpDisableCarrierType) {
		this.bumpDisableCarrierType = bumpDisableCarrierType;
	}

	public int getType() {
		return type;
	}

	public void setType(int type) {
		this.type = type;
	}

	@Override
	public String toString() {
//		JsonToStringBuilder builder = new JsonToStringBuilder(this);
//		
//		builder.append("type", 						type);
//		builder.append("vhlCode", 					vhlCode);
//		builder.append("carrierType", 				carrierType);
//		builder.append("runningAreaType", 			runningAreaType);
//		builder.append("minDistance", 				minDistance);
//		builder.append("offlineTimer", 				offlineTimer);
//		builder.append("carrierTypeMoving", 		carrierTypeMoving);
//		builder.append("vhlCodeName", 				vhlCodeName);
//		builder.append("varVhlType", 				varVhlType);
//		builder.append("bumpDisableCarrierType",	bumpDisableCarrierType);
//
//		return builder.toString();
		return null;
	}

}
