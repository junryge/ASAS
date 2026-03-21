public class RawLoop {
	private int id;
	private int subId;
	private Set<Integer[]> entrySet = new HashSet<Integer[]>();
	private Set<Integer[]> exitSet = new HashSet<Integer[]>();
	private String name;	
	private int zoneCarrierType=0;
	private int runningAreaType = 1;
	
	public RawLoop(
			int id,
			int subId,
			Set<Integer[]> entrySet,
			Set<Integer[]> exitSet,
			String name,
			int zoneCarrierType,
			int runningAreaType
	) {
		super();

		this.id = id;
		this.subId = subId;
		this.entrySet = entrySet;
		this.exitSet = exitSet;
		this.name = name;		
		this.zoneCarrierType = zoneCarrierType;
		this.runningAreaType = runningAreaType;
	}
	public Set<Integer[]> getEntrySet() {
		return entrySet;
	}
	public void setEntrySet(Set<Integer[]> entrySet) {
		this.entrySet = entrySet;
	}
	public Set<Integer[]> getExitSet() {
		return exitSet;
	}
	public void setExitSet(Set<Integer[]> exitSet) {
		this.exitSet = exitSet;
	}
	public int getZoneCarrierType() {
		return zoneCarrierType;
	}
	public void setZoneCarrierType(int zoneCarrierType) {
		this.zoneCarrierType = zoneCarrierType;
	}
	public int getId() {
		return id;
	}
	public void setId(int id) {
		this.id = id;
	}
	public int getSubId() {
		return subId;
	}
	public void setSubId(int subId) {
		this.subId = subId;
	}
	public String getName() {
		return name;
	}
	public void setName(String name) {
		this.name = name;
	}
	public int getRunningAreaType() {
		return runningAreaType;
	}
	public void setRunningAreaType(int runningAreaType) {
		this.runningAreaType = runningAreaType;
	}
}
