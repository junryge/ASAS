public class McslogSecsVo {
	private String fabSite;
	
	/*Page*/
	private String pageNum; /*페이지 번호*/
	private String rowNum; /*한 페이지에서 보여주고자 하는 행수*/
	
	/*FAB*/
	private List<String> fab; /*All / C2 / C2F / etc*/
	
	/*Level*/
	private List<String> level; /*ALL / DEBUG / INFO / FINE / WELL / WARN / ERROR / FATAL*/
	private List<String> host; /*Primary, Secondary*/
	
	/*Condition*/
	//private String searchOption; /*AND / OR*/ 
	private String carrier;
	private String vehicle;
	private String secs;
	private String carrierLoc;
	private String commandId;
	private String transferport;
	private String sourceport;
	private String destport;
	private String text;
	private String secsTextConditionCheckBox;		// 200305 hgJeon TEXT 조건검색 변수 추가
	
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

	public String getCarrier() {
		return carrier;
	}
	
	public void setCarrier(String carrier) {
		this.carrier = carrier;
	}
	
	public String getVehicle() {
		return vehicle;
	}
	
	public void setVehicle(String vehicle) {
		this.vehicle = vehicle;
	}
	
	public String getSecs() {
		return secs;
	}
	
	public void setSecs(String secs) {
		this.secs = secs;
	}
	
	public String getCarrierLoc() {
		return carrierLoc;
	}
	
	public void setCarrierLoc(String carrierLoc) {
		this.carrierLoc = carrierLoc;
	}
	
	public String getCommandId() {
		return commandId;
	}
	
	public void setCommandId(String commandId) {
		this.commandId = commandId;
	}
	
	public String getTransferport() {
		return transferport;
	}
	
	public void setTransferport(String transferport) {
		this.transferport = transferport;
	}
	
	public String getSourceport() {
		return sourceport;
	}
	
	public void setSourceport(String sourceport) {
		this.sourceport = sourceport;
	}
	
	public String getDestport() {
		return destport;
	}
	
	public void setDestport(String destport) {
		this.destport = destport;
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
	
	public String getSecsTextConditionCheckBox() {
		return secsTextConditionCheckBox;
	}
	
	public void setSecsTextConditionCheckBox(String secsTextConditionCheckBox) {
		this.secsTextConditionCheckBox = secsTextConditionCheckBox;
	}
}
