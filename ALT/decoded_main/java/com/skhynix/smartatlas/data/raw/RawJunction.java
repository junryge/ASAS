package com.skhynix.smartatlas.data.raw;

import java.util.HashSet;
import java.util.Set;

import com.skhynix.smartatlas.util.JsonToStringBuilder;

public class RawJunction {
	private int id;
	private int subId;
	private Set<Integer[]> entrySet = new HashSet<Integer[]>();
	private Set<Integer[]> exitSet = new HashSet<Integer[]>();
	private int vhlPreCaution=1;
	private int zoneCarrierType=0;
	
	public RawJunction(int id, int subId, Set<Integer[]> entrySet, Set<Integer[]> exitSet, int vhlPreCaution,
			int zoneCarrierType) {
		super();
		this.id = id;
		this.subId = subId;
		this.entrySet = entrySet;
		this.exitSet = exitSet;
		this.vhlPreCaution = vhlPreCaution;
		this.zoneCarrierType = zoneCarrierType;
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
	public int getVhlPreCaution() {
		return vhlPreCaution;
	}
	public void setVhlPreCaution(int vhlPreCaution) {
		this.vhlPreCaution = vhlPreCaution;
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
		builder.append("id", id);
		builder.append("subId", subId);
		builder.append("entrySet", entrySet);
		builder.append("exitSet", exitSet);
		builder.append("vhlPreCaution", vhlPreCaution);
		builder.append("zoneCarrierType", zoneCarrierType);
		return builder.toString();
	}
	
}
