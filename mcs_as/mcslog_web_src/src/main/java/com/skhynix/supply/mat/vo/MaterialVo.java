package com.skhynix.supply.mat.vo;

import java.util.List;

/**
 * @Package Name : com.skhynix.supply.mat.vo
 * @FileName : MatVo.java
 * @작성일 : 2017. 3. 10.
 * @작성자 : 최명수
 * @프로그램 설명 : Carrier 위치 이력조회 화면에 대한 VO
 */
public class MaterialVo {
	
	//2022. 6.15. X0122410 : fab site 변수 추가
	private String fabSite;
	
	/*Page*/
	private String pageNum; /*페이지 번호*/
	private String rowNum; /*한 페이지에서 보여주고자 하는 행수*/
	
	/*Machine*/
	private String areaName; 			// ALL and etc
	private String bayName;				// ALL and etc
	private List<String> machineType; /*ALL / STOCKER / STB / LIFTER / CONVEYOR / PROCESS / OHT*/
	private List<String> machineName;
	
	/*FAB*/
	private List<String> fab; /*All / M14A / M14B / etc*/
		
	/*Level*/
	private List<String> level; /*ALL / DEBUG / INFO / FINE / WELL / WARN / ERROR / FATAL*/
	
	/*Condition*/
	private String carrier;
	private String lotId;
	private String commandId;
	private String unit;
	
	/*Time*/
	private String from;
	private String to;
	
	/*GETTER / SETTER*/
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
	public String getCommandId() {
		return commandId;
	}
	public void setCommandId(String commandId) {
		this.commandId = commandId;
	}
	public String getUnit() {
		return unit;
	}
	public void setUnit(String unit) {
		this.unit = unit;
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
}
