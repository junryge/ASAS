package com.skhynix.supply.res.vo;

import java.util.List;

/**
 * @Package Name : com.skhynix.supply.res.vo
 * @FileName : ResCraneVo.java
 * @작성일 : 2017. 3. 22.
 * @작성자 : 최명수
 * @프로그램 설명 : CraneHistory 화면에 대한 VO
 */
public class ResPortVo {
	
	//2022. 6.15. X0122410 : fab site 변수 추가
	private String fabSite;
	
	/*Page*/
	private String pageNum; 			/*페이지 번호*/
	private String rowNum; 				/*한 페이지에서 보여주고자 하는 행수*/
	
	/*Machine*/
	private String areaName; 			// ALL and etc
	private String bayName;				// ALL and etc
	private List<String> machineType; 	/*ALL / STOCKER / STB / LIFTER / CONVEYOR / PROCESS / OHT*/
	private List<String> machineName;
	
	/*FAB*/
	private List<String> fab; /*All / M14A / M14B / etc*/
	
	/*Level*/
	private List<String> level; /*ALL / DEBUG / INFO / FINE / WELL / WARN / ERROR / FATAL*/
	
	/*Condition*/
	private String portName;
	private String state;
	private String subState;
	private String processingState;
	private String banned;
	private String occupied;
	private String transportUnitAccessible;
	private String craneAvailable;
	private String inOutType;
	private String manual;
	private String accessMode;
	private String idReadState;
	
	/*Time*/
	private String from;
	private String to;
	
	/*Getter and Setter*/
	public String getFabSite() {
		return this.fabSite;
	}
	public void setFabSite(String fabSite) {
		this.fabSite = fabSite;
	}
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
	public String getAreaName() {
		return areaName;
	}
	public void setAreaName(String areaName) {
		this.areaName = areaName;
	}
	public String getBayName() {
		return bayName;
	}
	public void setBayName(String bayName) {
		this.bayName = bayName;
	}
	public List<String> getMachineType() {
		return machineType;
	}
	public void setMachineType(List<String> machineType) {
		this.machineType = machineType;
	}
	public List<String> getMachineName() {
		return machineName;
	}
	public void setMachineName(List<String> machineName) {
		this.machineName = machineName;
	}
	public String getPortName() {
		return portName;
	}
	public void setPortName(String portName) {
		this.portName = portName;
	}
	public String getState() {
		return state;
	}
	public void setState(String state) {
		this.state = state;
	}
	public String getSubState() {
		return subState;
	}
	public void setSubState(String subState) {
		this.subState = subState;
	}
	public String getProcessingState() {
		return processingState;
	}
	public void setProcessingState(String processingState) {
		this.processingState = processingState;
	}
	public String getBanned() {
		return banned;
	}
	public void setBanned(String banned) {
		this.banned = banned;
	}
	public String getCraneAvailable() {
		return craneAvailable;
	}
	public void setCraneAvailable(String craneAvailable) {
		this.craneAvailable = craneAvailable;
	}
	public String getInOutType() {
		return inOutType;
	}
	public void setInOutType(String inOutType) {
		this.inOutType = inOutType;
	}
	public String getManual() {
		return manual;
	}
	public void setManual(String manual) {
		this.manual = manual;
	}
	public String getAccessMode() {
		return accessMode;
	}
	public void setAccessMode(String accessMode) {
		this.accessMode = accessMode;
	}
	public String getIdReadState() {
		return idReadState;
	}
	public void setIdReadState(String idReadState) {
		this.idReadState = idReadState;
	}	
	public String getOccupied() {
		return occupied;
	}
	public void setOccupied(String occupied) {
		this.occupied = occupied;
	}
	public String getTransportUnitAccessible() {
		return transportUnitAccessible;
	}
	public void setTransportUnitAccessible(String transportUnitAccessible) {
		this.transportUnitAccessible = transportUnitAccessible;
	}
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
	public List<String> getFab() {
		return fab;
	}
	public void setFab(List<String> fab) {
		this.fab = fab;
	}
	public List<String> getLevel() {
		return level;
	}
	public void setLevel(List<String> level) {
		this.level = level;
	}
}
