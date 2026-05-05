public class McslogMachineVo {
	//2022. 6.28. X0122410 : fab site 변수 추가
	private String fabSite;
	
	private List<String> machineType;
	private List<String> selectFab;
	private List<String> selectType;	// 201223 hgJeon 추가
	private String areaName;
	private String bayName;
	
	//2022. 6.28. X0122410 : fab site 변수 추가
	public String getFabSite() {
		return this.fabSite;
	}
	
	//2022. 6.28. X0122410 : fab site 변수 추가
	public void setFabSite(String fabSite) {
		this.fabSite = fabSite;
	}
	
	public List<String> getMachineType() {
		return machineType;
	}
	
	public void setMachineType(List<String> machineType) {
		this.machineType = machineType;
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
	
	public List<String> getSelectFab() {
		return selectFab;
	}
	
	public void setSelectFab(List<String> selectFab) {
		this.selectFab = selectFab;
	}
	
	public List<String> getSelectType() {
		return selectType;
	}
	
	public void setSelectType(List<String> selectType) {
		this.selectType = selectType;
	}
}
