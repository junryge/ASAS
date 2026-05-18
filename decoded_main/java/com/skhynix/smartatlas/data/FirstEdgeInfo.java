package com.skhynix.smartatlas.data;

public class FirstEdgeInfo{
	String firstEdgeId 				= "";
	String longEdgeId 				= "";
	String branchJoinEdgeId 		= "";
	int longEdgeDir 				= -1;
	String longEdgeFromNodeId 		= "";
	String longEdgeToNodeId 		= "";
	String branchJoinEdgeFromNodeId	= "";
	String branchJoinEdgeToNodeId 	= "";
	int branchJoinEdgeDir 			= -1;

	public FirstEdgeInfo(
							String firstEdgeId,
							String longEdgeId,
							String branchJoinEdgeId,
							int longEdgeDir,
							String longEdgeFromNodeId,
							String longEdgeToNodeId,
							String branchJoinEdgeFromNodeId,
							String branchJoinEdgeToNodeId,
							int branchJoinEdgeDir
	) {
		super();

		this.firstEdgeId 				= firstEdgeId;
		this.longEdgeId 				= longEdgeId;
		this.branchJoinEdgeId 			= branchJoinEdgeId;
		this.longEdgeDir 				= longEdgeDir;
		this.longEdgeFromNodeId 		= longEdgeFromNodeId;
		this.longEdgeToNodeId 			= longEdgeToNodeId;
		this.branchJoinEdgeFromNodeId 	= branchJoinEdgeFromNodeId;
		this.branchJoinEdgeToNodeId 	= branchJoinEdgeToNodeId;
		this.branchJoinEdgeDir 			= branchJoinEdgeDir;
	}

	public String getFirstEdgeId() {
		return firstEdgeId;
	}

	public void setFirstEdgeId(String firstEdgeId) {
		this.firstEdgeId = firstEdgeId;
	}

	public String getLongEdgeId() {
		return longEdgeId;
	}

	public void setLongEdgeId(String longEdgeId) {
		this.longEdgeId = longEdgeId;
	}

	public String getBranchJoinEdgeId() {
		return branchJoinEdgeId;
	}

	public void setBranchJoinEdgeId(String branchJoinEdgeId) {
		this.branchJoinEdgeId = branchJoinEdgeId;
	}

	public int getLongEdgeDir() {
		return longEdgeDir;
	}

	public void setLongEdgeDir(int longEdgeDir) {
		this.longEdgeDir = longEdgeDir;
	}

	public String getLongEdgeFromNodeId() {
		return longEdgeFromNodeId;
	}

	public void setLongEdgeFromNodeId(String longEdgeFromNodeId) {
		this.longEdgeFromNodeId = longEdgeFromNodeId;
	}

	public String getLongEdgeToNodeId() {
		return longEdgeToNodeId;
	}

	public void setLongEdgeToNodeId(String longEdgeToNodeId) {
		this.longEdgeToNodeId = longEdgeToNodeId;
	}

	public String getBranchJoinEdgeFromNodeId() {
		return branchJoinEdgeFromNodeId;
	}

	public void setBranchJoinEdgeFromNodeId(String branchJoinEdgeFromNodeId) {
		this.branchJoinEdgeFromNodeId = branchJoinEdgeFromNodeId;
	}

	public String getBranchJoinEdgeToNodeId() {
		return branchJoinEdgeToNodeId;
	}

	public void setBranchJoinEdgeToNodeId(String branchJoinEdgeToNodeId) {
		this.branchJoinEdgeToNodeId = branchJoinEdgeToNodeId;
	}

	public int getBranchJoinEdgeDir() {
		return branchJoinEdgeDir;
	}

	public void setBranchJoinEdgeDir(int branchJoinEdgeDir) {
		this.branchJoinEdgeDir = branchJoinEdgeDir;
	}
}

