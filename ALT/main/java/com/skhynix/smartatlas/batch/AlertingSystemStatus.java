package com.skhynix.smartatlas.batch;

import java.io.File;
import java.lang.management.ManagementFactory;
import java.util.Collection;
import java.util.HashMap;

import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.util.DataService;
import com.skhynix.smartatlas.util.SmsUtil;
import com.skhynix.smartatlas.util.ThreadPool;
import com.skhynix.smartatlas.util.Util;
import com.sun.management.OperatingSystemMXBean;

public class AlertingSystemStatus implements Job {
	private final Logger logger = LoggerFactory.getLogger(getClass());
	
	private final OperatingSystemMXBean osBean = ManagementFactory.getPlatformMXBean(OperatingSystemMXBean.class);
	
	private static final int LIMIT_STREAK_COUNT = 10;
	private static final String COMPUTER_NAME = Util.getComputerName();
	
	private static int resourcesWarningStreakCount = 0;
	private static long gcLastExecutionTime = 0;
	private static HashMap<ThreadPool, Long> queuedLastCompletedThreadCount = new HashMap<>();
	private static HashMap<ThreadPool, Long> queuedLastCheckTime = new HashMap<>();
	
	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		var smsProperties = Env.getSmsProperties();
		
		executeGC();
		checkSystemResources();
		checkThreadQueue(ThreadPool.getCreatedPool("WorkerRunnableQueue"), smsProperties.getUdpQueueWarningCount(), smsProperties.getUdpQueueFailoverCount());
		checkThreadQueue(ThreadPool.getCreatedPool("TibrvQueue"), smsProperties.getTibrvQueueWarningCount(), smsProperties.getTibrvQueueFailoverCount());
		checkCollection(DataService.getInstance().queue, "WorkerRunnableQueue");
		checkCollection(DataService.getInstance().tibrvMessageQueue, "TibrvQueue");
		checkCollection(DataService.getInstance().recordQueue, "RecordQueue");
	}
	
	private void executeGC() {
		if (System.currentTimeMillis() - gcLastExecutionTime > 10 * 60 * 1000) {
			gcLastExecutionTime = System.currentTimeMillis();
			System.gc();
		}
	}
	
	private void checkSystemResources() {
		try {
			double memoryLimit = Env.getSmsProperties().getMemoryUsage();
			double cpuLimit = Env.getSmsProperties().getCpuUsage();
			double diskLimit = Env.getSmsProperties().getDiskUsage();
			
			memoryLimit = memoryLimit == -1 ? 999 : memoryLimit;
			cpuLimit = cpuLimit == -1 ? 999 : cpuLimit;
			diskLimit = diskLimit == -1 ? 999 : diskLimit;
			
			var resources = getSystemResources(); 
			var memory = resources[0];
			var cpu = resources[1];
			var disk = resources[2];

			if (memory >= memoryLimit
				|| cpu >= cpuLimit
				|| disk >= diskLimit) {
				if (resourcesWarningStreakCount++ >= LIMIT_STREAK_COUNT) {
					var message = String.format("[%s] Exceed Resources ▶ Memory: %3.2f%% CPU: %3.2f%% Disk: %3.2f%%", COMPUTER_NAME, memory, cpu, disk);
					
					for (String receiver : Env.getSmsProperties().getReceivers()) {
						SmsUtil.sendSMS(receiver, message);
					}
					resourcesWarningStreakCount = 0;
				}
			} else {
				resourcesWarningStreakCount = 0;
			}
		} catch (Exception e) {
			logger.error("", e);
		}
	}
	
	private void checkThreadQueue(ThreadPool threadPool, int warningCount, int failoverCount) {
		if (threadPool == null) {
			return;
		}
		
		var now = System.currentTimeMillis();
		var poolSize = threadPool.getPoolSize();
		var queuedSize = threadPool.getQueuedSize();
		var activeThreadCount = threadPool.getActiveThreadCount();
		var completedThreadCount = threadPool.getCompletedThreadCount(); 
		
		logger.info("[Pool : {}][Created :\t{}][Active :\t{}][Idle :\t{}][Queued :\t{}][Completed : \t{}][ProcessSpeed :\t{}EA/ms][Warning :\t{}][Failover :\t{}]"
				, threadPool.getName()
				, poolSize
				, activeThreadCount
				, poolSize - activeThreadCount
				, queuedSize
				, completedThreadCount
				, (completedThreadCount - queuedLastCompletedThreadCount.getOrDefault(threadPool, 0L)) / 
					(double)(now - queuedLastCheckTime.getOrDefault(threadPool, System.currentTimeMillis()))
				, warningCount
				, failoverCount);
		
		queuedLastCompletedThreadCount.put(threadPool, completedThreadCount);
		queuedLastCheckTime.put(threadPool, System.currentTimeMillis());
		
		if (warningCount > 0 && queuedSize >= warningCount) {
			sendWarningSMS(queuedSize);
		}
		
		if (failoverCount > 0 && queuedSize >= failoverCount) {
			sendExceedSMSAndFailover(queuedSize);
		}
	}

	@SuppressWarnings("rawtypes")
	private void checkCollection(Collection collection, String name) {
		if (collection == null) {
			return;
		}
		
		try {
			logger.info("[Collection :\t{}][Remains :\t{}]", name, collection.size());
		} catch (Exception e) {
			logger.error("", e);
		}
	}
	
	private double[] getSystemResources() {
		var memoryfree = osBean.getFreePhysicalMemorySize();
		var memorytotal = osBean.getTotalPhysicalMemorySize();
		var cpuUsed = osBean.getSystemCpuLoad();
		var diskUsed = 0d;
		
		//CPU
		while (cpuUsed <= 0) {
			cpuUsed = osBean.getSystemCpuLoad();
			
			try {
				Thread.sleep(100);
			} catch (Exception e) {}
		}
		
		//DISK
		File rootDir = null;
		
		try {
			rootDir = new File("/");
		} catch (Exception e) {
			diskUsed = -1;
		}
		
		return new double[] {
			(1 - memoryfree / (double)memorytotal) * 100,
			cpuUsed * 100,
			diskUsed == -1 ? 0 : (1 - (rootDir.getFreeSpace() / (double)rootDir.getTotalSpace())) * 100
		};
	}
	
	private void sendWarningSMS(long queued) {
		try {
			String message = String.format("[%s] Warning Queue ▶ Queue Count: %d", COMPUTER_NAME, queued);
			
	    	for (String receiver : Env.getSmsProperties().getReceivers()) {
				if(SmsUtil.getLast5MinCountSMS(receiver, "Warning Queue") <= 0) {
					SmsUtil.sendSMS(receiver, message);
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		}
	}
	
	private void sendExceedSMSAndFailover(long queued) {
		try {
			String message = String.format("[%s] Exceed Queue ▶ Queue Count: %d, Failover", COMPUTER_NAME, queued);
			
	    	for (String receiver : Env.getSmsProperties().getReceivers()) {
				if(SmsUtil.getLast5MinCountSMS(receiver, "Exceed Queue") <= 0) {
					SmsUtil.sendSMS(receiver, message);
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		} finally {
			logger.error("Failover Starting.......................................");
			
			//Executing Failover
			try {
				new ProcessBuilder("powershell.exe", "Move-ClusterGroup", "-Name", "smartATLAS").start();
				logger.info("powershell exec Done");
			} catch(Exception e) {
				logger.error("failover exec error : ", e);
			}
		}
	}
	
}
