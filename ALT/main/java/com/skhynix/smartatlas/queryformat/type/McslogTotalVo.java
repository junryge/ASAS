package com.skhynix.smartatlas.queryformat.type;

import java.util.List;

public class McslogTotalVo {
	//2022. 6.28. X0122410 : fab site 변수 추가
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
	
	private String searchOption; /*AND / OR*/ 
	private String process;
	private String thread;
	private String gtxnId;	// 201023 hgJeon M16 Global Transaction Id 검색 추가
	private String transactionId;
	private String messageName;
	private String comMsgName;
	private String operationName;
	private String carrier;
	private String commandId;
	private String unit;
	private String text;
	private String fulltext;
	private List<String> key;
	/*M14 통합 로그조회 추가*/
	private String messageName_m;
	private String comMsgName_m;
	private String operationName_m;
	
	/*Time*/
	private String from;
	private String to;
	private String table;
	
	//2022. 6.28. X0122410 : fab site 변수 추가
	public String getFabSite() {
		return this.fabSite;
	}
	
	//2022. 6.28. X0122410 : fab site 변수 추가
	public void setFabSite(String fabSite) {
		this.fabSite = fabSite;
	}
	
	public List<String> getKey() {
		return key;
	}
	
	public void setKey(List<String> key) {
		this.key = key;
	}
	
	/*GETTER / SETTER*/
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
	
	public String getSearchOption() {
		return searchOption;
	}
	
	public void setSearchOption(String searchOption) {
		this.searchOption = searchOption;
	}
	
	public String getProcess() {
		return process;
	}
	
	public void setProcess(String process) {
		this.process = process;
	}
	
	public String getThread() {
		return thread;
	}
	
	public void setThread(String thread) {
		this.thread = thread;
	}
	
	public String getTransactionId() {
		return transactionId;
	}
	
	public void setTransactionId(String transactionId) {
		this.transactionId = transactionId;
	}
	
	public String getMessageName() {
		return messageName;
	}
	
	public void setMessageName(String messageName) {
		this.messageName = messageName;
	}
	
	public String getComMsgName() {
		return comMsgName;
	}
	
	public void setComMsgName(String comMsgName) {
		this.comMsgName = comMsgName;
	}
	
	public String getOperationName() {
		return operationName;
	}
	
	public void setOperationName(String operationName) {
		this.operationName = operationName;
	}
	
	public String getCarrier() {
		return carrier;
	}
	
	public void setCarrier(String carrier) {
		this.carrier = carrier;
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
	
	public String getText() {
		return text;
	}
	
	public void setText(String text) {
		this.text = text;
	}
	
	public String getFulltext() {
		return fulltext;
	}
	
	public void setFulltext(String fulltext) {
		this.fulltext = fulltext;
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
	
	public String getTable() {
		return table;
	}
	
	public void setTable(String table) {
		this.table = table;
	}
	
	public String getMessageName_m() {
		return messageName_m;
	}
	
	public void setMessageName_m(String messageName_m) {
		this.messageName_m = messageName_m;
	}
	
	public String getComMsgName_m() {
		return comMsgName_m;
	}
	
	public void setComMsgName_m(String comMsgName_m) {
		this.comMsgName_m = comMsgName_m;
	}
	
	public String getOperationName_m() {
		return operationName_m;
	}
	
	public void setOperationName_m(String operationName_m) {
		this.operationName_m = operationName_m;
	}
	
	public String getGtxnId() {
		return gtxnId;
	}
	
	public void setGtxnId(String gtxnId) {
		this.gtxnId = gtxnId;
	}
}
