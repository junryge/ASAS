public class StageCommandRecordItem {
    private final String id;	            // key 값
    private final String fabId;
    private final String mcpName;
    private final String facId;
    private final String deviceId;
    private final String machineId;// 기준이 되는 port
    private String destinationPortId;
    private Date prevEventDateTime;
    private Date eventDateTime;
    private String state;
    private boolean isChanged;

    // hid off, vhl off, rail cut 과는 다르게 특정 port 를 기준으로 삼고 해당 port 에 적재 중이거나 적재된 machine(vehicle) 의 수를 monitoring
    public StageCommandRecordItem (
            String id,
            String fabId,
            String mcpName,
            String facId,
            String deviceId,
            String machineId,
            String destinationPortId,
            long eventDateTime
    ) {
        this.id			= id;
        this.fabId		= fabId;
        this.mcpName		= mcpName;
        this.facId		= facId;
        this.deviceId	= deviceId;
        this.destinationPortId = destinationPortId;
        this.machineId  = machineId;
        this.prevEventDateTime = new Date(eventDateTime);
        this.eventDateTime = new Date(eventDateTime);
        this.state = OHT_TIB_STATE.ABNORMAL;
        this.isChanged = true;
    }

    public String getId() {
        return id;
    }

    public String getFabId() {
        return fabId;
    }

    public String getFacId() {
        return facId;
    }

    public void setDestinationPortId(String destinationPortId) {
        this.destinationPortId = destinationPortId;
    }

    public String getDestinationPortId() {
        return destinationPortId;
    }

    public String getDeviceId() {
        return deviceId;
    }

    public void setEventDateTime(long eventDateTime) {
        this.setEventDateTime(new Date(eventDateTime));
    }

    public void setEventDateTime(Date eventDateTime) {
        this.prevEventDateTime = this.eventDateTime;
        this.eventDateTime = eventDateTime;
    }

    public Date getEventDateTime() {
        return eventDateTime;
    }

    public Date getPrevEventDateTime() {
        return prevEventDateTime;
    }

    public String getEventDateTimeString () {
        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

        return dateFormat.format(this.eventDateTime);
    }

    public String getMachineId() {
        return machineId;
    }

    public void setState(String state) {
        this.state = state;
    }

    public String getState() {
        return state;
    }

    public void setChanged(boolean changed) {
        this.isChanged = changed;
    }

    public boolean getChanged() {
        return isChanged;
    }

    public String getMcpName() {
        return mcpName;
    }
}
