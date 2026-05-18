package com.skhynix.smartatlas.data;

public class OhtStats {
	String tblNm = "ATLAS_OHT_STATS_HIS";
	String fabId = "";
	String mcpName = "";
	
	int vhlCnt = 0;	
	int vhlTransferringCnt = 0;
	int vhlStageCnt = 0;
	int vhlAbnormalCnt = 0;
	int vhlE84Cnt = 0;
	int vhlManualCnt = 0;
	int vhlHtStopCnt = 0;
	int vhlOfflineCnt = 0;	
	int vhlJamCnt = 0;
	int vhlObsStopCnt = 0;
	
	int trCnt = 0;
	int trQueuedCnt = 0;
	int trWaitingCnt = 0;
	int trTransferringCnt = 0;
	int trPausedCnt = 0;
	int trCancelingCnt = 0;
	int trAbortingCnt = 0;
	int trUpdatingCnt = 0;
	int trDelay0_1Cnt = 0;
	int trDelay1_2Cnt = 0;
	int trDelay2_3Cnt = 0;
	int trDelay3_4Cnt = 0;
	int trDelay4_5Cnt = 0;
	int trDelay5OverCnt = 0;
	
	float avgAssignSec = 0;
	float avgAcquireSec = 0;
	
	public OhtStats(String fabId, String mcpName) {
		this.fabId = fabId;
		this.mcpName = mcpName;
	}

	public String getTblNm() {
		return tblNm;
	}

	public void setTblNm(String tblNm) {
		this.tblNm = tblNm;
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

	public int getVhlCnt() {
		return vhlCnt;
	}

	public void addVhlCnt() {
		this.vhlCnt++;
	}

	public int getVhlTransferringCnt() {
		return vhlTransferringCnt;
	}

	public void addVhlTransferringCnt() {
		this.vhlTransferringCnt++;
	}

	public int getVhlStageCnt() {
		return vhlStageCnt;
	}

	public void addVhlStageCnt() {
		this.vhlStageCnt++;
	}	

	public int getVhlManualCnt() {
		return vhlManualCnt;
	}

	public void addVhlManualCnt() {
		this.vhlManualCnt++;
	}
	
	public int getVhlAbnormalCnt() {
		return vhlAbnormalCnt;
	}

	public void addVhlAbnormalCnt() {
		this.vhlAbnormalCnt++;
	}
	
	public int getVhlE84Cnt() {
		return vhlE84Cnt;
	}

	public void addVhlHtStopCnt() {
		this.vhlHtStopCnt++;
	}
	
	public int getVhlHtStopCnt() {
		return vhlHtStopCnt;
	}

	public void addVhlE84Cnt() {
		this.vhlE84Cnt++;
	}

	public int getVhlOfflineCnt() {
		return vhlOfflineCnt;
	}

	public void addVhlOfflineCnt() {
		this.vhlOfflineCnt++;
	}

	public int getVhlJamCnt() {
		return vhlJamCnt;
	}

	public void addVhlJamCnt() {
		this.vhlJamCnt++;
	}

	public int getTrCnt() {
		return trCnt;
	}

	public void addTrCnt() {
		this.trCnt++;
	}

	public int getTrQueuedCnt() {
		return trQueuedCnt;
	}

	public void addTrQueuedCnt() {
		this.trQueuedCnt++;
	}

	public int getTrWaitingCnt() {
		return trWaitingCnt;
	}

	public void addTrWaitingCnt() {
		this.trWaitingCnt++;
	}

	public int getTrTransferringCnt() {
		return trTransferringCnt;
	}

	public void addTrTransferringCnt() {
		this.trTransferringCnt++;
	}

	public int getTrPausedCnt() {
		return trPausedCnt;
	}

	public void addTrPausedCnt() {
		this.trPausedCnt++;
	}

	public int getTrCancelingCnt() {
		return trCancelingCnt;
	}

	public void addTrCancelingCnt() {
		this.trCancelingCnt++;
	}

	public int getTrAbortingCnt() {
		return trAbortingCnt;
	}

	public void addTrAbortingCnt() {
		this.trAbortingCnt++;
	}

	public int getTrUpdatingCnt() {
		return trUpdatingCnt;
	}

	public void addTrUpdatingCnt() {
		this.trUpdatingCnt++;
	}

	public int getTrDelay0_1Cnt() {
		return trDelay0_1Cnt;
	}

	public void addTrDelay0_1Cnt() {
		this.trDelay0_1Cnt++;
	}

	public int getTrDelay1_2Cnt() {
		return trDelay1_2Cnt;
	}

	public void addTrDelay1_2Cnt() {
		this.trDelay1_2Cnt++;
	}

	public int getTrDelay2_3Cnt() {
		return trDelay2_3Cnt;
	}

	public void addTrDelay2_3Cnt() {
		this.trDelay2_3Cnt++;
	}

	public int getTrDelay3_4Cnt() {
		return trDelay3_4Cnt;
	}

	public void addTrDelay3_4Cnt() {
		this.trDelay3_4Cnt++;
	}

	public int getTrDelay4_5Cnt() {
		return trDelay4_5Cnt;
	}

	public void addTrDelay4_5Cnt() {
		this.trDelay4_5Cnt++;
	}

	public int getTrDelay5OverCnt() {
		return trDelay5OverCnt;
	}

	public void addTrDelay5OverCnt() {
		this.trDelay5OverCnt++;
	}

	public int getVhlObsStopCnt() {
		return vhlObsStopCnt;
	}

	public void addVhlObsStopCnt() {
		this.vhlObsStopCnt++;
	}

	public float getAvgAssignSec() {
		return avgAssignSec;
	}

	public void setAvgAssignSec(float avgAssignSec) {
		this.avgAssignSec = avgAssignSec;
	}

	public float getAvgAcquireSec() {
		return avgAcquireSec;
	}

	public void setAvgAcquireSec(float avgAcquireSec) {
		this.avgAcquireSec = avgAcquireSec;
	}

	
}
