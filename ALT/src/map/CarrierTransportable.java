public interface CarrierTransportable {
	public String getId();
	public String getEqpId();
	public void addCommandId(String commandId);
	public void removeCommandId(String commandId);	
}
