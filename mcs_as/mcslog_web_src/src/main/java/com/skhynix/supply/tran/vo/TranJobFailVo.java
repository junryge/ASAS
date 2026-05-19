package com.skhynix.supply.tran.vo;

import java.util.List;

public class TranJobFailVo {
	//2022. 6.15. X0122410 : fab site 변수 추가
	private String fabSite;
	
	/*Page*/
	private String pageNum; /*페이지 번호*/
	private String rowNum; /*한 페이지에서 보여주고자 하는 행수*/
	
	/*FAB*/
	private List<String> fab; 
//	private List<String> transportFab; 
//	private List<String> fromFab; 
//	private List<String> toFab;
	
	/*Area/Bay/Unit*/
	private String fromAreaName; 			// ALL and etc
	private String fromBayName;				// ALL and etc
	private String fromUnit;
	private String toAreaName; 				// ALL and etc
	private String toBayName;				// ALL and etc					
	private String toUnit;	
	private String transportAreaName; 		// ALL and etc
	private String transportBayName;		// ALL and etc
	private String transportUnit;
	
	/*Machine*/
	private List<String> fromMachineType; 	/*ALL / STOCKER / STB / LIFTER / CONVEYOR / PROCESS / OHT*/
	private List<String> toMachineType; 	/*ALL / STOCKER / STB / LIFTER / CONVEYOR / PROCESS / OHT*/
	private List<String> transportMachineType; 	/*ALL / STOCKER / STB / LIFTER / CONVEYOR / PROCESS / OHT*/
	private List<String> fromMachineName;	
	private List<String> toMachineName;			
	private List<String> transportMachineName;
		
	/*Time*/
	private String from;
	private String to;
	
	/*JobFailFilter*/
	private String carrier;
	private String lotId;
	private String transportJobId;
	private List<String> reason;
	
	/*public String getKey() {
		return key;
	}
	public void setKey(String key) {
		this.key = key;
	}*/
	
	/*GETTER AND SETTER*/
	public String getFabSite() {
		return this.fabSite;
	}
	public void setFabSite(String fabSite) {
		this.fabSite = fabSite;
	}
	/*Page*/
	public String getPageNum() {
		return pageNum;
	}
	public void setPageNum(String pageNum) {
		this.pageNum = pageNum;
	}
	public String getRowNum() {
		return rowNum;
	}
	public void setRowNum(String rowNum) {
		this.rowNum = rowNum;
	}
	
	/*FAB*/
	public List<String> getFab() {
		return fab;
	}
	public void setFab(List<String> fab) {
		this.fab = fab;
	}
//	public List<String> getFromFab() {
//		return fromFab;
//	}
//	public void setFromFab(List<String> fab) {
//		this.fromFab = fab;
//	}
//	public List<String> getToFab() {
//		return toFab;
//	}
//	public void setToFab(List<String> fab) {
//		this.toFab = fab;
//	}
//	public List<String> getTransportFab() {
//		return transportFab;
//	}
//	public void setTransportFab(List<String> fab) {
//		this.transportFab = fab;
//	}

	/*Area/Bay/Unit*/
	public String getFromAreaName() {
		return fromAreaName;
	}
	public void setFromAreaName(String areaName) {
		this.fromAreaName = areaName;
	}
	public String getFromBayName() {
		return fromBayName;
	}
	public void setFromBayName(String bayName) {
		this.fromBayName = bayName;
	}
	public String getFromUnit() {
		return fromUnit;
	}
	public void setFromUnit(String unit) {
		this.fromUnit = unit;
	}	
	
	public String getToAreaName() {
		return toAreaName;
	}
	public void setToAreaName(String areaName) {
		this.toAreaName = areaName;
	}
	public String getToBayName() {
		return toBayName;
	}
	public void setToBayName(String bayName) {
		this.toBayName = bayName;
	}
	public String getToUnit() {
		return toUnit;
	}
	public void setToUnit(String unit) {
		this.toUnit = unit;
	}
	
	public String getTransportAreaName() {
		return transportAreaName;
	}
	public void setTransportAreaName(String areaName) {
		this.transportAreaName = areaName;
	}
	public String getTransportBayName() {
		return transportBayName;
	}
	public void setTransportBayName(String bayName) {
		this.transportBayName = bayName;
	}	
	public String getTransportUnit() {
		return transportUnit;
	}
	public void setTransportUnit(String unit) {
		this.transportUnit = unit;
	}

	/*Machine*/
	public List<String> getFromMachineType() {
		return fromMachineType;
	}
	public void setFromMachineType(List<String> machineType) {
		this.fromMachineType = machineType;
	}
	public List<String> getToMachineType() {
		return toMachineType;
	}
	public void setToMachineType(List<String> machineType) {
		this.toMachineType = machineType;
	}
	public List<String> getTransportMachineType() {
		return transportMachineType;
	}
	public void setTransportMachineType(List<String> machineType) {
		this.transportMachineType = machineType;
	}

	public List<String> getFromMachineName() {
		return fromMachineName;
	}
	public void setFromMachineName(List<String> machineName) {
		this.fromMachineName = machineName;
	}
	public List<String> getToMachineName() {
		return toMachineName;
	}
	public void setToMachineName(List<String> machineName) {
		this.toMachineName = machineName;
	}
	public List<String> getTransportMachineName() {
		return transportMachineName;
	}
	public void setTransportMachineName(List<String> machineName) {
		this.transportMachineName = machineName;
	}	
		
	/*Time*/
	public String getFrom() {
		return from;
	}
	public void setFrom(String from) {
		this.from = from;
	}
	public String getTo() {
		return to;
	}
	public void setTo(String to) {
		this.to = to;
	}
	
	/*JobFailFilter*/
	public String getCarrier() {
		return carrier;
	}
	public void setCarrier(String carrier) {
		this.carrier = carrier;
	}
	public String getLotId() {
		return lotId;
	}
	public void setLotId(String lotId) {
		this.lotId = lotId;
	}
	public String getTransportJobId() {
		return transportJobId;
	}
	public void setTransportJobId(String transportJobId) {
		this.transportJobId = transportJobId;
	}
	public List<String> getReason() {
		return reason;
	}
	public void setReason(List<String> reason) {
		this.reason = reason;
	}
	
}
