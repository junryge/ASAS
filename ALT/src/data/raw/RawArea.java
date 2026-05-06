public class RawArea {
	private int id;
	private int subId;
	private Set<Integer[]> entrySet		= new HashSet<Integer[]>();
	private Set<Integer[]> exitSet 		= new HashSet<Integer[]>();
	private int vhlMax					= 0;
	private int vhlPreCaution			= 0;
	private int vhlAvg 					= 0;
	private int vhlMin					= 0;
	private int idleVhlMax				= 0;
	private int idleVhlAvg				= 0;
	private int idleVhlMin				= 0;
	private String name;
	private int parkDistance			= -1;
	private int areaSearchDistance		= 0;
	private int zoneCarrierType			= 0;
	
	public RawArea(
					int id, 
					int subId, 
					String name, 
					Set<Integer[]> entrySet,
					Set<Integer[]> exitSet, 
					int vhlMax, 
					int vhlPreCaution, 
					int vhlAvg,
					int vhlMin, 
					int idleVhlMax,
					int idleVhlAvg, 
					int idleVhlMin, 
					int parkDistance,
					int areaSearchDistance, 
					int zoneCarrierType
	) {
		super();
		
		this.id 				= id;
		this.subId 				= subId;
		this.entrySet 			= entrySet;
		this.exitSet 			= exitSet;
		this.vhlMax 			= vhlMax;
		this.vhlPreCaution 		= vhlPreCaution;
		this.vhlAvg 			= vhlAvg;
		this.vhlMin 			= vhlMin;
		this.idleVhlMax 		= idleVhlMax;
		this.idleVhlAvg 		= idleVhlAvg;
		this.idleVhlMin 		= idleVhlMin;
		this.name 				= name;
		this.parkDistance 		= parkDistance;
		this.areaSearchDistance	= areaSearchDistance;
		this.zoneCarrierType 	= zoneCarrierType;
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
	
	public int getVhlMax() {
		return vhlMax;
	}
	
	public void setVhlMax(int vhlMax) {
		this.vhlMax = vhlMax;
	}
	
	public int getVhlPreCaution() {
		return vhlPreCaution;
	}
	
	public void setVhlPreCaution(int vhlPreCaution) {
		this.vhlPreCaution = vhlPreCaution;
	}
	
	public int getVhlAvg() {
		return vhlAvg;
	}
	
	public void setVhlAvg(int vhlAvg) {
		this.vhlAvg = vhlAvg;
	}
	
	public int getVhlMin() {
		return vhlMin;
	}
	
	public void setVhlMin(int vhlMin) {
		this.vhlMin = vhlMin;
	}
	
	public int getIdleVhlMax() {
		return idleVhlMax;
	}
	
	public void setIdleVhlMax(int idleVhlMax) {
		this.idleVhlMax = idleVhlMax;
	}
	
	public int getIdleVhlAvg() {
		return idleVhlAvg;
	}
	
	public void setIdleVhlAvg(int idleVhlAvg) {
		this.idleVhlAvg = idleVhlAvg;
	}
	
	public int getIdleVhlMin() {
		return idleVhlMin;
	}
	
	public void setIdleVhlMin(int idleVhlMin) {
		this.idleVhlMin = idleVhlMin;
	}
	
	public String getName() {
		return name;
	}
	
	public void setName(String name) {
		this.name = name;
	}
	
	public int getParkDistance() {
		return parkDistance;
	}
	
	public void setParkDistance(int parkDistance) {
		this.parkDistance = parkDistance;
	}
	
	public int getAreaSearchDistance() {
		return areaSearchDistance;
	}
	
	public void setAreaSearchDistance(int areaSearchDistance) {
		this.areaSearchDistance = areaSearchDistance;
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

	@Override
	public String toString() {
		JsonToStringBuilder builder = new JsonToStringBuilder(this);
		
		builder.append("id", 					id);
		builder.append("subId", 				subId);
		builder.append("entrySet", 				entrySet);
		builder.append("exitSet", 				exitSet);
		builder.append("vhlMax", 				vhlMax);
		builder.append("vhlPreCaution", 		vhlPreCaution);
		builder.append("vhlAvg", 				vhlAvg);
		builder.append("vhlMin", 				vhlMin);
		builder.append("idleVhlMax", 			idleVhlMax);
		builder.append("idleVhlAvg", 			idleVhlAvg);
		builder.append("idleVhlMin", 			idleVhlMin);
		builder.append("name", 					name);
		builder.append("parkDistance", 			parkDistance);
		builder.append("areaSearchDistance", 	areaSearchDistance);
		builder.append("zoneCarrierType", 		zoneCarrierType);
		
		return builder.toString();
	}


}
