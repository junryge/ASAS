public class SmsProperties {
	int _MemoryUsage;
	int _CpuUsage;
	int _DiskUsage;
	int _QueueWarningCount;
	int _QueueFailoverCount;
	String[] _Receivers;
	
	public SmsProperties(int memoryUsage, int cpuUsage, int diskUsage, int queueWarningCount, int queueFailoverCount, String[] receivers) {
		_MemoryUsage = memoryUsage;
		_CpuUsage = cpuUsage;
		_DiskUsage = diskUsage;
		_QueueWarningCount = queueWarningCount;
		_QueueFailoverCount = queueFailoverCount;
		_Receivers = receivers;
	}
	
	public final int getMemoryUsage() {
		return _MemoryUsage;
	}

	public final int getCpuUsage() {
		return _CpuUsage;
	}

	public final int getDiskUsage() {
		return _DiskUsage;
	}
	
	public final int getQueueWarningCount() {
		return _QueueWarningCount;
	}
	
	public final int getQueueFailoverCount() {
		return _QueueFailoverCount;
	}

	public final String[] getReceivers() {
		return _Receivers;
	}
}
