package com.skhynix.smartatlas.environment.type;

public class SmsProperties {
	int memoryUsage;
	int cpuUsage;
	int diskUsage;
	int udpQueueWarningCount;
	int udpQueueFailoverCount;
	int tibrvQueueWarningCount;
	int tibrvQueueFailoverCount;
	String[] receivers;

	public SmsProperties(int memoryUsage, int cpuUsage, int diskUsage, int udpQueueWarningCount, int udpQueueFailoverCount, 
			int tibrvQueueWarningCount, int tibrvQueueFailoverCount, String[] receivers) {
		this.memoryUsage = memoryUsage;
		this.cpuUsage = cpuUsage;
		this.diskUsage = diskUsage;
		this.udpQueueWarningCount = udpQueueWarningCount;
		this.udpQueueFailoverCount = udpQueueFailoverCount;
		this.tibrvQueueWarningCount = tibrvQueueWarningCount;
		this.tibrvQueueFailoverCount = tibrvQueueFailoverCount;
		this.receivers = receivers;
	}

	public int getMemoryUsage() {
		return memoryUsage;
	}

	public int getCpuUsage() {
		return cpuUsage;
	}

	public int getDiskUsage() {
		return diskUsage;
	}

	public int getUdpQueueWarningCount() {
		return udpQueueWarningCount;
	}

	public int getUdpQueueFailoverCount() {
		return udpQueueFailoverCount;
	}

	public int getTibrvQueueWarningCount() {
		return tibrvQueueWarningCount;
	}

	public int getTibrvQueueFailoverCount() {
		return tibrvQueueFailoverCount;
	}

	public String[] getReceivers() {
		return receivers;
	}
	
}
