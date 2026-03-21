public class Msg {
	private String fabId;
	private MSG_TYP type;
	private long receivedMilli;
	private String message;
	private String mcpName = "";
	
	// constructor 1
	public Msg(
				String fabId, 
				MSG_TYP type, 
				long receivedMilli, 
				String message
	) {
		super();
		this.fabId 			= fabId;
		this.type 			= type;
		this.receivedMilli 	= receivedMilli;
		this.message 		= message;
	}
	
	// constructor 2	
	public Msg(
				String fabId,
				MSG_TYP type, 
				long receivedMilli, 
				String mcpName, 
				String message
	) {
		super();
		
		this.fabId 			= fabId;
		this.type 			= type;
		this.receivedMilli 	= receivedMilli;
		this.mcpName 		= mcpName;
		this.message 		= message;
	}

	public enum MSG_TYP{MHS, EI, OHT, UI, CNV}

	public MSG_TYP getType() {
		return type;
	}

	public void setType(MSG_TYP type) {
		this.type = type;
	}

	public long getReceivedMilli() {
		return receivedMilli;
	}

	public void setReceivedMilli(long receivedMilli) {
		this.receivedMilli = receivedMilli;
	}

	public String getMessage() {
		return message;
	}

	public void setMessage(String message) {
		this.message = message;
	}

	public String getFabId() {
		return fabId;
	}

	public void setFabId(String fabId) {
		this.fabId = fabId;
	}

	public String getMcpName() {
		return mcpName;
	}

	public void setMcpName(String mcpName) {
		this.mcpName = mcpName;
	}
}
