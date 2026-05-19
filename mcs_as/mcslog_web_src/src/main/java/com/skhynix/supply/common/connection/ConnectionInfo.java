package com.skhynix.supply.common.connection;

public class ConnectionInfo {
	private String hostPrimary;
	private String hostSecondary;
	private int logpressoPort;
	private String logpressoID;
	private String logpressoPW;

	public final String getHostPrimary() {
		return hostPrimary;
	}

	public final String getHostSecondary() {
		return hostSecondary;
	}
	
	public final int getLogpressoPort() {
		return logpressoPort;
	}

	public final String getLogpressoID() {
		return logpressoID;
	}

	public final String getLogpressoPW() {
		return logpressoPW;
	}

	final void setHostPrimary(String hostPrimary) {
		this.hostPrimary = hostPrimary;
	}

	final void setHostSecondary(String hostSecondary) {
		this.hostSecondary = hostSecondary;
	}
	
	final void setLogpressoPort(int logpressoPort) {
		this.logpressoPort = logpressoPort;
	}

	final void setLogpressoID(String logpressoID) {
		this.logpressoID = logpressoID;
	}

	final void setLogpressoPW(String logpressoPW) {
		this.logpressoPW = logpressoPW;
	}

}
