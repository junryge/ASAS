package com.skhynix.supply.secs.vo;

import java.util.List;

/**
 * @Package Name : com.skhynix.supply.tot.vo
 * @FileName : EiVo.java
 * @작성일 : 2020. 3. 25.
 * @작성자 : 전현구
 * @프로그램 설명 : EI_CS_DS 로그조회 화면에 대한 VO
 */

public class EiVo {

	//2022. 6.15. X0122410 : fab site 변수 추가
	private String fabSite;
	
	/*Page*/
	private String pageNum; /*페이지 번호*/
	private String rowNum; /*한 페이지에서 보여주고자 하는 행수*/
	
	/*FAB*/
	private List<String> fab; /*All / C2 / C2F / etc*/
	
	/*Level*/
	private List<String> level; /*ALL / DEBUG / INFO / FINE / WELL / WARN / ERROR / FATAL*/
	private List<String> host; /*Primary, Secondary*/
	private List<String> log;
	
	/*Condition*/
	private String process;
	private String text;
	private String eiTextConditionCheckBox;
	
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
	public List<String> getHost() {
		return host;
	}
	public void setHost(List<String> host) {
		this.host = host;
	}
	public List<String> getLog() {
		return log;
	}
	public void setLog(List<String> log) {
		this.log = log;
	}
	public String getText() {
		return text;
	}
	public void setText(String text) {
		this.text = text;
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
	public String getEiTextConditionCheckBox() {
		return eiTextConditionCheckBox;
	}
	public void setEiTextConditionCheckBox(String eiTextConditionCheckBox) {
		this.eiTextConditionCheckBox = eiTextConditionCheckBox;
	}
	public String getProcess() {
		return process;
	}
	public void setProcess(String process) {
		this.process = process;
	}
	
	
}
