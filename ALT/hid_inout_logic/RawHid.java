package com.skhynix.smartatlas.data.raw;

import java.util.HashSet;
import java.util.Set;

public class RawHid {
	private int id;
	private int subId;
	private Set<LoopEntry> loopEntrySet	= new HashSet<LoopEntry>();
	private Set<Integer[]> exitSet 		= new HashSet<Integer[]>();
	private int vhlMax					= 0;
	private int vhlPreCaution			= 0;
	private int zoneCarrierType			= 0;
	private Set<Integer[]> autoCloseSet	= new HashSet<Integer[]>();
	private int autoCloseVhlCntDisable 	= 0;
	private int autoCloseVhlCntRestore 	= 0;
	
	public RawHid(
					int id, 
					int subId, 
					Set<LoopEntry> loopEntrySet, 
					Set<Integer[]> exitSet, 
					int vhlMax, 
					int vhlPreCaution,
					int zoneCarrierType, 
					Set<Integer[]> autoCloseSet, 
					int autoCloseVhlCntDisable, 
					int autoCloseVhlCntRestore
	) {
		super();
		
		this.id 					= id;
		this.subId 					= subId;
		this.loopEntrySet 			= loopEntrySet;
		this.exitSet 				= exitSet;
		this.vhlMax 				= vhlMax;
		this.vhlPreCaution 			= vhlPreCaution;
		this.zoneCarrierType 		= zoneCarrierType;
		this.autoCloseSet 			= autoCloseSet;
		this.autoCloseVhlCntDisable = autoCloseVhlCntDisable;
		this.autoCloseVhlCntRestore = autoCloseVhlCntRestore;
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
	
	public Set<LoopEntry> getLoopEntrySet() {
		return loopEntrySet;
	}
	
	public void setLoopEntrySet(Set<LoopEntry> loopEntrySet) {
		this.loopEntrySet = loopEntrySet;
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
	
	public int getZoneCarrierType() {
		return zoneCarrierType;
	}
	
	public void setZoneCarrierType(int zoneCarrierType) {
		this.zoneCarrierType = zoneCarrierType;
	}
	
	public Set<Integer[]> getAutoCloseSet() {
		return autoCloseSet;
	}
	
	public void setAutoCloseSet(Set<Integer[]> autoCloseSet) {
		this.autoCloseSet = autoCloseSet;
	}
	
	public int getAutoCloseVhlCntDisable() {
		return autoCloseVhlCntDisable;
	}
	
	public void setAutoCloseVhlCntDisable(int autoCloseVhlCntDisable) {
		this.autoCloseVhlCntDisable = autoCloseVhlCntDisable;
	}
	
	public int getAutoCloseVhlCntRestore() {
		return autoCloseVhlCntRestore;
	}
	
	public void setAutoCloseVhlCntRestore(int autoCloseVhlCntRestore) {
		this.autoCloseVhlCntRestore = autoCloseVhlCntRestore;
	}	
}
