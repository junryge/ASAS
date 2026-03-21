public class LoopEntry {
	private int entryLaneStart;
	private int entryLaneEnd;
	private String setZcu;
	private int entrySettingNo;
	
	public LoopEntry(
						int entryLaneStart, 
						int entryLaneEnd, 
						String setZcu, 
						int entrySettingNo
	) {
		super();
		
		this.entryLaneStart = entryLaneStart;
		this.entryLaneEnd 	= entryLaneEnd;
		this.setZcu 		= setZcu;
		this.entrySettingNo	= entrySettingNo;
	}
	
	public int getEntryLaneStart() {
		return entryLaneStart;
	}
	
	public void setEntryLaneStart(int entryLaneStart) {
		this.entryLaneStart = entryLaneStart;
	}
	
	public int getEntryLaneEnd() {
		return entryLaneEnd;
	}
	
	public void setEntryLaneEnd(int entryLaneEnd) {
		this.entryLaneEnd = entryLaneEnd;
	}
	
	public String getSetZcu() {
		return setZcu;
	}
	
	public void setSetZcu(String setZcu) {
		this.setZcu = setZcu;
	}
	
	public int getEntrySettingNo() {
		return entrySettingNo;
	}
	
	public void setEntrySettingNo(int entrySettingNo) {
		this.entrySettingNo = entrySettingNo;
	}
}
