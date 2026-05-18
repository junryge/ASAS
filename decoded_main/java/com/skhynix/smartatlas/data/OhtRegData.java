package com.skhynix.smartatlas.data;

import com.skhynix.smartatlas.map.Vhl.RUN_CYCLE;

public class OhtRegData {	
	private String tblNm 				= "ATLAS_OHT_PARA_REG_DATA";
	private String fabId 				= "";
	private String mcpName 				= "";
	private long inTime 				= -1;
	private long elapsed 				= -1;
	private String longEdgeId 			= "";
	private String vhlId 				= "";
	private double distancePerVelocity 	= -1;
	private long distance 				= -1;
	private int idleVhlCnt 				= -1;
	private int workingVhlCnt 			= -1;
	private int srcStCnt 				= -1;
	private int dstStCnt 				= -1;
	private int junctionCnt 			= -1;
	private int branchCnt 				= -1;
	private int stCnt 					= -1;
	private RUN_CYCLE myInRunCycle 		= RUN_CYCLE.NONE;
	private RUN_CYCLE myOutRunCycle 	= RUN_CYCLE.NONE;
	
	public OhtRegData(
						String fabId, 
						String mcpName, 
						long inTime, 
						String longEdgeId, 
						double distancePerVelocity, 
						long distance, 
						String vhlId, 
						int idleVhlCnt,
						int workingVhlCnt, 
						int srcStCnt, 
						int dstStCnt, 
						int junctionCnt, 
						int branchCnt, 
						int stCnt, 
						RUN_CYCLE myInRunCycle
	) {
		super();
		
		this.fabId 					= fabId;
		this.mcpName 				= mcpName;
		this.inTime 				= inTime;
		this.longEdgeId 			= longEdgeId;
		this.distancePerVelocity 	= distancePerVelocity;
		this.distance 				= distance;
		this.vhlId 					= vhlId;
		this.idleVhlCnt 			= idleVhlCnt;
		this.workingVhlCnt 			= workingVhlCnt;
		this.srcStCnt 				= srcStCnt;
		this.dstStCnt 				= dstStCnt;
		this.junctionCnt 			= junctionCnt;
		this.branchCnt 				= branchCnt;
		this.stCnt 					= stCnt;
		this.myInRunCycle 			= myInRunCycle;		
	}
	
	public long getInTime() {
		return inTime;
	}
	
	public void setInTime(long inTime) {
		this.inTime = inTime;
	}
	
	public long getElapsed() {
		return elapsed;
	}
	
	public void setElapsed(long elapsed) {
		this.elapsed = elapsed;
	}
	
	public String getLongEdgeId() {
		return longEdgeId;
	}
	
	public void setLongEdgeId(String longEdgeId) {
		this.longEdgeId = longEdgeId;
	}
	
	public String getVhlId() {
		return vhlId;
	}
	
	public void setVhlId(String vhlId) {
		this.vhlId = vhlId;
	}
	
	public int getIdleVhlCnt() {
		return idleVhlCnt;
	}
	
	public void setIdleVhlCnt(int idleVhlCnt) {
		this.idleVhlCnt = idleVhlCnt;
	}
	
	public int getWorkingVhlCnt() {
		return workingVhlCnt;
	}
	
	public void setWorkingVhlCnt(int workingVhlCnt) {
		this.workingVhlCnt = workingVhlCnt;
	}
	
	public int getSrcStCnt() {
		return srcStCnt;
	}
	
	public void setSrcStCnt(int srcStCnt) {
		this.srcStCnt = srcStCnt;
	}
	
	public int getDstStCnt() {
		return dstStCnt;
	}
	
	public void setDstStCnt(int dstStCnt) {
		this.dstStCnt = dstStCnt;
	}
	
	public int getJunctionCnt() {
		return junctionCnt;
	}
	
	public void setJunctionCnt(int junctionCnt) {
		this.junctionCnt = junctionCnt;
	}
	
	public int getBranchCnt() {
		return branchCnt;
	}
	
	public void setBranchCnt(int branchCnt) {
		this.branchCnt = branchCnt;
	}
	
	public int getStCnt() {
		return stCnt;
	}
	
	public void setStCnt(int stCnt) {
		this.stCnt = stCnt;
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
	
	public RUN_CYCLE getMyInRunCycle() {
		return myInRunCycle;
	}
	
	public void setMyInRunCycle(RUN_CYCLE myInRunCycle) {
		this.myInRunCycle = myInRunCycle;
	}
	
	public RUN_CYCLE getMyOutRunCycle() {
		return myOutRunCycle;
	}
	
	public void setMyOutRunCycle(RUN_CYCLE myOutRunCycle) {
		this.myOutRunCycle = myOutRunCycle;
	}
	
	public double getDistancePerVelocity() {
		return distancePerVelocity;
	}
	
	public void setDistancePerVelocity(double distancePerVelocity) {
		this.distancePerVelocity = distancePerVelocity;
	}
	
	public String getTblNm() {
		return tblNm;
	}
	
	public void setTblNm(String tblNm) {
		this.tblNm = tblNm;
	}
	
	public long getDistance() {
		return distance;
	}
	
	public void setDistance(long distance) {
		this.distance = distance;
	}
}