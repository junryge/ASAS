package com.skhynix.smartatlas.data;

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

	//public enum MSG_TYP{MHS, EI, OHT, UI, CNV, AGV, ALARM}
	public enum MSG_TYP {
	    MHS("mhs"),
	    EI("ei"),
	    OHT("oht"),
	    UI("ui"),
	    CNV("cnv"),
	    AGV("agv"),
	    AMP("amp"),
	    ALARM("alarm");

	    private final String code;

	    MSG_TYP(String code) {
	        this.code = code;
	    }

	    public String getCode() {
	        return code;
	    }

	    // 문자열을 ENUM 으로 변환하는 static 메서드
	    public static MSG_TYP fromString(String target) {
	        if (target == null) {
	            return null; // 또는 기본 값, 예외 발생
	        }

	        for (MSG_TYP type : MSG_TYP.values()) {
	            if (type.code.equalsIgnoreCase(target)) { // 대소문자 무시 비교
	                return type;
	            }
	        }
	        
	        // 매칭되는 값이 없을 경우 처리 (null 반환 또는 예외)
	        return null; 
	        // throw new IllegalArgumentException("Unknown MSG_TYP: " + target);
	    }
	}
	
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
