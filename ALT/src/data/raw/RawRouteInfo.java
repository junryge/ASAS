public class RawRouteInfo {
	String id = "";
	String fabId = "";
	int fromBay = 0;
	int toBay = 0;
	int vhlType = 0;
	int minPriority = 0;
	int maxPriority = 0;
	String outPort = "";
	String entryPort = "";
	int[] viaPoints = null;
	String mcpName = "";
	
	public RawRouteInfo(String id, String fabId, String mcpName, int fromBay, int toBay, int vhlType, int minPriority, int maxPriority,
			String outPort, String entryPort, int[] viaPoints) {
		super();
		this.id = id;
		this.fabId = fabId;
		this.fromBay = fromBay;
		this.toBay = toBay;
		this.vhlType = vhlType;
		this.minPriority = minPriority;
		this.maxPriority = maxPriority;
		this.outPort = outPort;
		this.entryPort = entryPort;
		this.viaPoints = viaPoints;
		this.mcpName = mcpName;
	}
	
	public String getId() {
		return id;
	}
	public void setId(String id) {
		this.id = id;
	}
	public int getFromBay() {
		return fromBay;
	}
	public void setFromBay(int fromBay) {
		this.fromBay = fromBay;
	}
	public int getToBay() {
		return toBay;
	}
	public void setToBay(int toBay) {
		this.toBay = toBay;
	}
	public int getVhlType() {
		return vhlType;
	}
	public void setVhlType(int vhlType) {
		this.vhlType = vhlType;
	}
	public int getMinPriority() {
		return minPriority;
	}
	public void setMinPriority(int minPriority) {
		this.minPriority = minPriority;
	}
	public int getMaxPriority() {
		return maxPriority;
	}
	public void setMaxPriority(int maxPriority) {
		this.maxPriority = maxPriority;
	}
	public String getOutPort() {
		return outPort;
	}
	public void setOutPort(String outPort) {
		this.outPort = outPort;
	}
	public String getEntryPort() {
		return entryPort;
	}
	public void setEntryPort(String entryPort) {
		this.entryPort = entryPort;
	}
	public int[] getViaPoints() {
		return viaPoints;
	}
	public void setViaPoints(int[] viaPoints) {
		this.viaPoints = viaPoints;
	}

	public String getFabId() {
		return fabId;
	}

	public void setFabId(String fabId) {
		this.fabId = fabId;
	}

	public String getMcpName() {
		return mcpName;
	}

	public void setMcpName(String mcpName) {
		this.mcpName = mcpName;
	}
	
	@Override
	public String toString() {
		return "[id=" + id + ", fabId=" + fabId + ", fromBay=" + fromBay + ", toBay=" + toBay
				+ ", vhlType=" + vhlType + ", minPriority=" + minPriority + ", maxPriority=" + maxPriority
				+ ", outPort=" + outPort + ", entryPort=" + entryPort + ", viaPoints=" + Arrays.toString(viaPoints)
				+ ", mcpName=" + mcpName + "]";
	}
}
