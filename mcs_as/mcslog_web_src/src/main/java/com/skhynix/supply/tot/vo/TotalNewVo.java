package com.skhynix.supply.tot.vo;

import java.util.List;

/**
 * @Package Name : com.skhynix.supply.tot.vo
 * @FileName : TotalNewVo.java
 * @작성일 : 2017. 3. 10.
 * @작성자 : 최명수
 * @프로그램 설명 : 신규 로그조회 화면에 대한 VO
 */
public class TotalNewVo {
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
	
	/*Level*/
	private List<String> level; /*ALL / DEBUG / INFO / FINE / WELL / WARN / ERROR / FATAL*/
	
	/*Condition*/
	private String searchOption; /*AND / OR*/ 
	private String carrier;
	private String totalElapsedTime;
	private String elapsedTime;
	private String command;
	private String messageName;
	private String process;
	private String transactionId;
	private String commandId;
	private String unit;
	private String thread;
	private String comment;
	
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
	public List<String> getLevel() {
		return level;
	}
	public void setLevel(List<String> level) {
		this.level = level;
	}
	public String getSearchOption() {
		return searchOption;
	}
	public void setSearchOption(String searchOption) {
		this.searchOption = searchOption;
	}
	public String getCarrier() {
		return carrier;
	}
	public void setCarrier(String carrier) {
		this.carrier = carrier;
	}
	public String getTotalElapsedTime() {
		return totalElapsedTime;
	}
	public void setTotalElapsedTime(String totalElapsedTime) {
		this.totalElapsedTime = totalElapsedTime;
	}
	public String getElapsedTime() {
		return elapsedTime;
	}
	public void setElapsedTime(String elapsedTime) {
		this.elapsedTime = elapsedTime;
	}
	public String getCommand() {
		return command;
	}
	public void setCommand(String command) {
		this.command = command;
	}
	public String getMessageName() {
		return messageName;
	}
	public void setMessageName(String messageName) {
		this.messageName = messageName;
	}
	public String getProcess() {
		return process;
	}
	public void setProcess(String process) {
		this.process = process;
	}
	public String getTransactionId() {
		return transactionId;
	}
	public void setTransactionId(String transactionId) {
		this.transactionId = transactionId;
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
	public String getThread() {
		return thread;
	}
	public void setThread(String thread) {
		this.thread = thread;
	}
	public String getComment() {
		return comment;
	}
	public void setComment(String comment) {
		this.comment = comment;
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
