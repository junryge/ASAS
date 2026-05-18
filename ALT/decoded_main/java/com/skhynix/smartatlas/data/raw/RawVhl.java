package com.skhynix.smartatlas.data.raw;

import com.skhynix.smartatlas.util.JsonToStringBuilder;

public class RawVhl {
	private String vhlId;
	private int type;
	private int loopId;
	private boolean idReadEnabled;
	private boolean maskDetectionEnabled;
	
	public RawVhl(
			String vhlId,
			int type,
			int loopId,
			boolean idReadEnabled,
			boolean maskDetectionEnabled
	) {
		super();

		this.vhlId = vhlId;
		this.type = type;
		this.loopId = loopId;
		this.idReadEnabled = idReadEnabled;
		this.maskDetectionEnabled = maskDetectionEnabled;
	}
	public String getVhlId() {
		return vhlId;
	}
	public void setVhlId(String vhlId) {
		this.vhlId = vhlId;
	}
	public int getType() {
		return type;
	}
	public void setType(int type) {
		this.type = type;
	}
	public int getLoopId() {
		return loopId;
	}
	public void setLoopId(int loopId) {
		this.loopId = loopId;
	}
	public boolean isIdReadEnabled() {
		return idReadEnabled;
	}
	public void setIdReadEnabled(boolean idReadEnabled) {
		this.idReadEnabled = idReadEnabled;
	}
	public boolean isMaskDetectionEnabled() {
		return maskDetectionEnabled;
	}
	public void setMaskDetectionEnabled(boolean maskDetectionEnabled) {
		this.maskDetectionEnabled = maskDetectionEnabled;
	}

	@Override
	public String toString() {
		JsonToStringBuilder builder = new JsonToStringBuilder(this);

		builder.append("vhlId", vhlId);
		builder.append("type", type);
		builder.append("loopId", loopId);
		builder.append("idReadEnabled", idReadEnabled);
		builder.append("maskDetectionEnabled", maskDetectionEnabled);

		return builder.toString();
	}
}