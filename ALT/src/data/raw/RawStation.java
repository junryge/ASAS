public class RawStation {
	private int stNo;
	private STATION_TYPE stationType;
	private boolean waitAllowed;
	private String portId;
	private int transportCarrierType;
	private boolean bumpAllowed;
	private int address_no;
	private INV_MGT_CATEGORY invMgtCategory;
	private int stationGroup1;
	private int stationGroup2;
	private int portGroup;
	private STATION_LOCATION stationLocation;
	private String comment;
	private int standbyPriority;
	private int parkingPriority;
	private int forcedOutputDestinationPriority;
	private double leftDistance;
	private double rightDistance;
	private int allowableSimultaneousOutputCount;
	private double slide;
	private int eqStationAtTheSameLocation;
	private int stbLeftAtTheSameLocation;
	private int stbRightAtTheSameLocation;
	private double drawX;
	private double drawY;
	private final double SLIDE_THRESHOLD = 100000; 

	public RawStation(
						int stationNo,
						STATION_TYPE stationType, 
						boolean waitAllowed, 
						String portId, 
						int transportCarrierType,
						boolean bumpAllowed, 
						int address_no, 
						INV_MGT_CATEGORY invMgtCategory, 
						int stationGroup1, 
						int stationGroup2,
						int portGroup, 
						STATION_LOCATION stationLocation, 
						String comment, 
						int standbyPriority, 
						int parkingPriority,
						int forcedOutputDestinationPriority, 
						double leftDistance, 
						double rightDistance,
						int allowableSimultaneousOutputCount, 
						int eqStationAtTheSameLocation, 
						int stbLeftAtTheSameLocation,
						int stbRightAtTheSameLocation
	) {
		super();
		
		this.stNo 						= stationNo;
		this.stationType 				= stationType;
		this.waitAllowed 				= waitAllowed;
		this.portId 					= portId;
		this.transportCarrierType 		= transportCarrierType;
		this.bumpAllowed 				= bumpAllowed;
		this.address_no 				= address_no;
		this.invMgtCategory 			= invMgtCategory;
		this.stationGroup1 				= stationGroup1;
		this.stationGroup2 				= stationGroup2;
		this.portGroup 					= portGroup;
		this.stationLocation 			= stationLocation;
		this.comment 					= comment;
		this.standbyPriority 			= standbyPriority;
		this.parkingPriority 					= parkingPriority;
		this.forcedOutputDestinationPriority 	= forcedOutputDestinationPriority;
		this.leftDistance 						= leftDistance;
		this.rightDistance 						= rightDistance;
		this.allowableSimultaneousOutputCount 	= allowableSimultaneousOutputCount;
		this.eqStationAtTheSameLocation 		= eqStationAtTheSameLocation;
		this.stbLeftAtTheSameLocation 			= stbLeftAtTheSameLocation;
		this.stbRightAtTheSameLocation 			= stbRightAtTheSameLocation;
	}

	public int getStNo() {
		return stNo;
	}
	
	public void setStNo(int stNo) {
		this.stNo = stNo;
	}
	
	public STATION_TYPE getStationType() {
		return stationType;
	}
	
	public void setStationType(STATION_TYPE stationType) {
		this.stationType = stationType;
	}
	
	public boolean isWaitAllowed() {
		return waitAllowed;
	}
	
	public void setWaitAllowed(boolean waitAllowed) {
		this.waitAllowed = waitAllowed;
	}
	
	public String getPortId() {
		return portId;
	}
	
	public void setPortId(String portId) {
		this.portId = portId;
	}
	
	public int getTransportCarrierType() {
		return transportCarrierType;
	}
	
	public void setTransportCarrierType(int transportCarrierType) {
		this.transportCarrierType = transportCarrierType;
	}
	
	public boolean isBumpAllowed() {
		return bumpAllowed;
	}
	
	public void setBumpAllowed(boolean bumpAllowed) {
		this.bumpAllowed = bumpAllowed;
	}
	
	public int getAddress_no() {
		return address_no;
	}
	
	public void setAddress_no(int address_no) {
		this.address_no = address_no;
	}
	
	public INV_MGT_CATEGORY getInvMgtCategory() {
		return invMgtCategory;
	}
	
	public void setInvMgtCategory(INV_MGT_CATEGORY invMgtCategory) {
		this.invMgtCategory = invMgtCategory;
	}
	
	public int getStationGroup1() {
		return stationGroup1;
	}
	
	public void setStationGroup1(int stationGroup1) {
		this.stationGroup1 = stationGroup1;
	}
	
	public int getStationGroup2() {
		return stationGroup2;
	}
	
	public void setStationGroup2(int stationGroup2) {
		this.stationGroup2 = stationGroup2;
	}
	
	public int getPortGroup() {
		return portGroup;
	}
	
	public void setPortGroup(int portGroup) {
		this.portGroup = portGroup;
	}
	
	public STATION_LOCATION getStationLocation() {
		return stationLocation;
	}
	
	public void setStationLocation(STATION_LOCATION stationLocation) {
		this.stationLocation = stationLocation;
	}
	
	public String getComment() {
		return comment;
	}
	
	public void setComment(String comment) {
		this.comment = comment;
	}
	
	public int getStandbyPriority() {
		return standbyPriority;
	}
	
	public void setStandbyPriority(int standbyPriority) {
		this.standbyPriority = standbyPriority;
	}
	
	public int getParkingPriority() {
		return parkingPriority;
	}
	
	public void setParkingPriority(int parkingPriority) {
		this.parkingPriority = parkingPriority;
	}
	
	public int getForcedOutputDestinationPriority() {
		return forcedOutputDestinationPriority;
	}
	
	public void setForcedOutputDestinationPriority(int forcedOutputDestinationPriority) {
		this.forcedOutputDestinationPriority = forcedOutputDestinationPriority;
	}
	
	public double getLeftDistance() {
		return leftDistance;
	}
	
	public void setLeftDistance(double leftDistance) {
		this.leftDistance = leftDistance;
	}
	
	public double getRightDistance() {
		return rightDistance;
	}
	
	public void setRightDistance(double rightDistance) {
		this.rightDistance = rightDistance;
	}
	
	public int getAllowableSimultaneousOutputCount() {
		return allowableSimultaneousOutputCount;
	}
	
	public void setAllowableSimultaneousOutputCount(int allowableSimultaneousOutputCount) {
		this.allowableSimultaneousOutputCount = allowableSimultaneousOutputCount;
	}
	
	public double getSlide() {
		return slide;
	}
	
	public void setSlide(double slide) {
		this.slide = slide;
	}
	
	public int getEqStationAtTheSameLocation() {
		return eqStationAtTheSameLocation;
	}


	public void setEqStationAtTheSameLocation(int eqStationAtTheSameLocation) {
		this.eqStationAtTheSameLocation = eqStationAtTheSameLocation;
	}


	public int getStbLeftAtTheSameLocation() {
		return stbLeftAtTheSameLocation;
	}


	public void setStbLeftAtTheSameLocation(int stbLeftAtTheSameLocation) {
		this.stbLeftAtTheSameLocation = stbLeftAtTheSameLocation;
	}


	public int getStbRightAtTheSameLocation() {
		return stbRightAtTheSameLocation;
	}


	public void setStbRightAtTheSameLocation(int stbRightAtTheSameLocation) {
		this.stbRightAtTheSameLocation = stbRightAtTheSameLocation;
	}
	
	public PORT_LOCATION getPortLocation(){
		if ( 
				SLIDE_THRESHOLD < this.slide 
				|| "AZFS_LEFT".equals(this.comment) 
		) {
			return PORT_LOCATION.LEFT;
		} else if (
				(SLIDE_THRESHOLD * -1.0) > this.slide 
				|| "AZFS_RIGHT".equals(this.comment)
		) {
			return PORT_LOCATION.RIGHT;
		} else {
			return PORT_LOCATION.CENTER;
		}
	}

	public enum STATION_TYPE{
		DEPOSIT("Station where VEHICLE deposits carrier"),
		ACQUIRE("Station where VEHICLE acquires carrier"),
		DUAL_ACCESS("Station where VEHICLE acquires/deposits carrier"),
		DUMMY("Dummy Station"),
		MAINTENANCE("Maintenance Station (Location to install/remove VHL)");
		
		private String description;
		
		STATION_TYPE(String description){
			this.description = description;
		}
		
		public String getDescription(){
			return description;
		}
	}
	
	public enum INV_MGT_CATEGORY{
		CATEGORY0("Exempted from Inventory Management Target(STOCKER/EQ)"),
		CATEGORY1("Inventory Management Target(ZFS/AZFS)"),
		CATEGORY2("Inventory Management Target with IDR"),
		CATEGORY3("Exempted from Inventory Management, with TagReader"),
		CATEGORY4("Inventory Management Target with RFC"),
		CATEGORY5("Inventory Management Target with RFC:naming rule 2");
		
		private String description;
		
		INV_MGT_CATEGORY(String description){
			this.description = description;
		}
		public String getDescription(){
			return description;
		}
		
	}
	
	public enum PORT_LOCATION{CENTER,LEFT,RIGHT}
	
	public enum STATION_LOCATION{NO_CONDITION,LEFT_BRANCH,RIGHT_BRANCH}
	
	@Override
	public String toString() {
		JsonToStringBuilder builder = new JsonToStringBuilder(this);
		builder.append("stNo", stNo);
		builder.append("stationType", stationType);
		builder.append("waitAllowed", waitAllowed);
		builder.append("portId", portId);
		builder.append("transportCarrierType", transportCarrierType);
		builder.append("bumpAllowed", bumpAllowed);
		builder.append("address_no", address_no);
		builder.append("invMgtCategory", invMgtCategory);
		builder.append("stationGroup1", stationGroup1);
		builder.append("stationGroup2", stationGroup2);
		builder.append("portGroup", portGroup);
		builder.append("stationLocation", stationLocation);
		builder.append("comment", comment);
		builder.append("standbyPriority", standbyPriority);
		builder.append("parkingPriority", parkingPriority);
		builder.append("forcedOutputDestinationPriority", forcedOutputDestinationPriority);
		builder.append("leftDistance", leftDistance);
		builder.append("rightDistance", rightDistance);
		builder.append("allowableSimultaneousOutputCount", allowableSimultaneousOutputCount);
		builder.append("slide", slide);
		builder.append("eqStationAtTheSameLocation", eqStationAtTheSameLocation);
		builder.append("stbLeftAtTheSameLocation", stbLeftAtTheSameLocation);
		builder.append("stbRightAtTheSameLocation", stbRightAtTheSameLocation);
		
		return builder.toString();
	}

	public double getDrawX() {
		return drawX;
	}


	public void setDrawX(double drawX) {
		this.drawX = drawX;
	}


	public double getDrawY() {
		return drawY;
	}


	public void setDrawY(double drawY) {
		this.drawY = drawY;
	}
	
}
