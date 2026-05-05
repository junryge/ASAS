public class RawBay {
	private int id;
	private String fabId;
	private int subId;
	private String name;
	private Set<RawBayPort> entrySet = new HashSet<RawBayPort>();
	private Set<RawBayPort> exitSet = new HashSet<RawBayPort>();
	private int zoneCarrierType=0;
	
	public RawBay(int id, int subId, String name, String fabId, Set<RawBayPort> entrySet, Set<RawBayPort> exitSet, int zoneCarrierType) {
		super();
		this.id = id;
		this.subId = subId;
		this.name = name;
		this.fabId = fabId;
		this.entrySet = entrySet;
		this.exitSet = exitSet;
		this.zoneCarrierType = zoneCarrierType;
	}
	
	public String getName() {
		return name;
	}
	public void setName(String name) {
		this.name = name;
	}
	public Set<RawBayPort> getEntrySet() {
		return entrySet;
	}
	public void setEntrySet(Set<RawBayPort> entrySet) {
		this.entrySet = entrySet;
	}
	public Set<RawBayPort> getExitSet() {
		return exitSet;
	}
	public void setExitSet(Set<RawBayPort> exitSet) {
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
	
	public class RawBayPort{
		public int startPoint = -1;
		public int endPoint = -1;
		public String name = "";
		public RawBayPort(int startPoint, int endPoint, String name) {
			this.startPoint = startPoint;
			this.endPoint = endPoint;
			this.name = name;
			
		}
	}
	
	

	@Override
	public String toString() {
		JsonToStringBuilder builder = new JsonToStringBuilder(this);
		builder.append("id", id);
		builder.append("subId", subId);
		builder.append("name", name);
		builder.append("entrySet", entrySet);
		builder.append("exitSet", exitSet);
		builder.append("zoneCarrierType", zoneCarrierType);
		return builder.toString();
	}

	public String getFabId() {
		return fabId;
	}

	public void setFabId(String fabId) {
		this.fabId = fabId;
	}
	
	
}
