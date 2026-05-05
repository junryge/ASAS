public class AlertingSystemStatus implements Job {
	private final Logger logger = LoggerFactory.getLogger(getClass());
	
	private final int LIMIT_STREAK_COUNT = 10;

	private final OperatingSystemMXBean _OsBean = ManagementFactory.getPlatformMXBean(OperatingSystemMXBean.class);
	private static int _WarningStreakCount = 0;
	
	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		try {
			double memoryLimit = Env.getSmsProperties().getMemoryUsage();
			double cpuLimit = Env.getSmsProperties().getCpuUsage();
			double diskLimit = Env.getSmsProperties().getDiskUsage();
			
			memoryLimit = memoryLimit == -1 ? 999 : memoryLimit;
			cpuLimit = cpuLimit == -1 ? 999 : cpuLimit;
			diskLimit = diskLimit == -1 ? 999 : diskLimit;
			
			double memory = getMemoryUsage();
			double cpu = getCpuUsage();
			double disk = getDiskUsage();

			if (memory >= memoryLimit
				|| cpu >= cpuLimit
				|| disk >= diskLimit) {
				if (_WarningStreakCount++ >= LIMIT_STREAK_COUNT) {
					var message = String.format("[%s] Exceed Resources ▶ Memory: %3.2f%% CPU: %3.2f%% Disk: %3.2f%%", InetAddress.getLocalHost().getHostName(), memory, cpu, disk);
					
					for (String receiver : Env.getSmsProperties().getReceivers()) {
						SmsUtil.sendSMS(receiver, message);
					}
					_WarningStreakCount = 0;
				}
			} else {
				_WarningStreakCount = 0;
			}
		} catch (Exception e) {
			logger.error("", e);
		}
	}
	
	private double getMemoryUsage() {
		long free = _OsBean.getFreePhysicalMemorySize();
		long total = _OsBean.getTotalPhysicalMemorySize();
		
		return (1 - free / (double)total) * 100;
	}
	
	private double getCpuUsage() {
		double systemLoad = 0;
		
		do {
			systemLoad = _OsBean.getSystemCpuLoad();
			
			try {
				Thread.sleep(100);
			} catch (Exception e) {}
		} while (systemLoad <= 0);
		
		return systemLoad * 100;
	}
	
	private double getDiskUsage() {
		File rootDir = null;
		
		try {
			rootDir = new File("/");
		} catch (Exception e) {
			return 0;
		}
		return (1 - (rootDir.getFreeSpace() / (double)rootDir.getTotalSpace())) * 100;
	}
	
}
