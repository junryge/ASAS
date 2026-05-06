public class RawPoint {
	private static Map<Integer,RawPoint> map = new HashMap<Integer,RawPoint>(); 
	private int address;
	private int stNo;
	private int leftAddress;
	private double leftDistance;
	private int leftSpeed;
	private int rightAddress;	
	private double rightDistance;
	private int rightSpeed;
	private boolean viaPoint;
	private int stopResetPoint;
	private double drawX;
	private double drawY;
	private double cadX;
	private double cadY;
	private double cadZ;	

	public RawPoint(
					int address, 
					int stNo, 
					int leftAddress, 
					double leftDistance, 
					int leftSpeed, 
					int rightAddress,
					double rightDistance, 
					int rightSpeed, 
					boolean viaPoint, 
					int stopResetPoint
	) {
		super();
		
		this.address 		= address;
		this.stNo 			= stNo;
		this.leftAddress 	= leftAddress;
		this.leftDistance 	= leftDistance;
		this.leftSpeed 		= leftSpeed;
		this.rightAddress 	= rightAddress;
		this.rightDistance 	= rightDistance;
		this.rightSpeed 	= rightSpeed;
		this.viaPoint 		= viaPoint;
		this.stopResetPoint	= stopResetPoint;
		
		map.put(this.address, this);
	}

	public static Map<Integer, RawPoint> getMap() {
		return map;
	}

	public static void setMap(Map<Integer, RawPoint> map) {
		RawPoint.map = map;
	}

	public int getAddress() {
		return address;
	}

	public void setAddress(int address) {
		this.address = address;
	}

	public int getStNo() {
		return stNo;
	}

	public void setStNo(int stNo) {
		this.stNo = stNo;
	}

	public int getLeftAddress() {
		return leftAddress;
	}

	public void setLeftAddress(int leftAddress) {
		this.leftAddress = leftAddress;
	}

	public double getLeftDistance() {
		return leftDistance;
	}

	public void setLeftDistance(double leftDistance) {
		this.leftDistance = leftDistance;
	}

	public int getLeftSpeed() {
		return leftSpeed;
	}

	public void setLeftSpeed(int leftSpeed) {
		this.leftSpeed = leftSpeed;
	}

	public int getRightAddress() {
		return rightAddress;
	}

	public void setRightAddress(int rightAddress) {
		this.rightAddress = rightAddress;
	}

	public double getRightDistance() {
		return rightDistance;
	}

	public void setRightDistance(double rightDistance) {
		this.rightDistance = rightDistance;
	}

	public int getRightSpeed() {
		return rightSpeed;
	}

	public void setRightSpeed(int rightSpeed) {
		this.rightSpeed = rightSpeed;
	}

	public boolean isViaPoint() {
		return viaPoint;
	}

	public void setViaPoint(boolean viaPoint) {
		this.viaPoint = viaPoint;
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

	public double getCadX() {
		return cadX;
	}

	public void setCadX(double cadX) {
		this.cadX = cadX;
	}

	public double getCadY() {
		return cadY;
	}

	public void setCadY(double cadY) {
		this.cadY = cadY;
	}

	public double getCadZ() {
		return cadZ;
	}

	public void setCadZ(double cadZ) {
		this.cadZ = cadZ;
	}

	@Override
	public String toString() {
		JsonToStringBuilder builder = new JsonToStringBuilder(this);
		
		builder.append("address", 			address);
		builder.append("stNo", 				stNo);
		builder.append("leftAddress", 		leftAddress);
		builder.append("leftDistance", 		leftDistance);
		builder.append("leftSpeed", 		leftSpeed);
		builder.append("rightAddress", 		rightAddress);
		builder.append("rightDistance", 	rightDistance);
		builder.append("rightSpeed", 		rightSpeed);
		builder.append("viaPoint", 			viaPoint);
		builder.append("stopResetPoint", 	stopResetPoint);
		builder.append("drawX", 			drawX);
		builder.append("drawY", 			drawY);
		builder.append("cadX", 				cadX);
		builder.append("cadY", 				cadY);
		builder.append("cadZ", 				cadZ);
		
		return builder.toString();
	}

	public int getStopResetPoint() {
		return stopResetPoint;
	}

	public void setStopResetPoint(int stopResetPoint) {
		this.stopResetPoint = stopResetPoint;
	}
}
