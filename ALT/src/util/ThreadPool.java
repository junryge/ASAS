public class ThreadPool {
	private static final Logger logger = LoggerFactory.getLogger("THREADPOOL");
	private static long lastSent = 0;
	
	private boolean closed = false;
	private AtomicLong seq = new AtomicLong(0);
	private long startTime = -1;
	private long lastProcessed = 0;
	ThreadPoolExecutor executor = null;
	private boolean paused = false;
	
	private static class Singleton{
    	private static final ThreadPool instance = new ThreadPool(
													    			Env.getAtlasThreadPoolSize(), 
													    			Env.getAtlasThreadPoolSize(), 
													    			Env.getAtlasThreadPoolSize(), 
													    			Env.getAtlasThreadPoolSize()
													    		); 
    }
	
	public static ThreadPool getInstance() {
		return Singleton.instance;
	}


	private ThreadPool(
						int initThreadCount, 
						int maxThreadCount,
						int minThreadCount, 
						int allowedIdleCount
	) {
		startTime 	= System.currentTimeMillis();
		executor 	= (ThreadPoolExecutor) Executors.newFixedThreadPool(maxThreadCount);
	}

	public ThreadPool(
						int initThreadCount, 
						int maxThreadCount, 
						int minThreadCount
	) {
		executor = (ThreadPoolExecutor) Executors.newFixedThreadPool(maxThreadCount);
	}

	/**
	 * 큐에 작업할 객체를 삽입한다.
	 *
	 * @work 쓰레드가 수행할 작업
	 */
	public synchronized void execute(Runnable work) throws AleadyClosedException {
		if (closed) {
			throw new AleadyClosedException();
		}
		
		while(paused) {
			try {
				Thread.sleep(10);
			} catch (Exception e) {}
		}
		try {
			executor.execute(work);
		} catch(Exception e) {
			logger.error("Exception occured while executing thread {}", work.toString(), e);
		}
		
		if (System.currentTimeMillis() - lastSent > 60000) {
			lastSent = System.currentTimeMillis();
			printStatus();
		}
	}
	
	public int getActiveCount() {
		return executor.getActiveCount();
	}

	/**
	 * 쓰레드 풀을 종료한다.
	 */
	public synchronized void close() throws AleadyClosedException {
		if (closed) throw new AleadyClosedException();
		closed = true;
		executor.shutdown();
	}



	public void printStatus() {
		synchronized(executor) {
			int poolSize 	= executor.getPoolSize();
			int activeCount	= executor.getActiveCount();
			long queued 	= executor.getQueue().size();
			long completed 	= executor.getCompletedTaskCount();
			long processed 	= completed - lastProcessed;
			long now 		= System.currentTimeMillis();
			double warningCount = Env.getSmsProperties().getQueueWarningCount();
			double failoverCount = Env.getSmsProperties().getQueueFailoverCount();
			
			warningCount = warningCount == -1 ? 999999 : warningCount;
			failoverCount = failoverCount == -1 ? 999999 : failoverCount;
			
			logger.warn("[Created :\t{}][Active :\t{}][Idle :\t{}][Queued :\t{}][AllReceived : \t{}][Completed : \t{}]"
					,poolSize, activeCount, poolSize-activeCount, queued, seq, completed);
			
			logger.warn("[ProcessSpeed : {}msg/ms]",(double)processed/(double)(now-startTime));
			
			lastProcessed 	= completed;
			startTime 		= now;
			
	        //미처리 건수가 임계치 이상이면 sms전송
			if (queued >= warningCount) {
				sendWarningSMS(queued);
			}
			
			if (queued >= failoverCount) {
				sendExceedSMSAndFailover(queued);
			}
		}
	}
	
	private void sendWarningSMS(long queued) {
		try {
			String message = String.format("[%s] Warning Queue ▶ Queue Count: %d", InetAddress.getLocalHost().getHostName(), queued);
			
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
			String message = String.format("[%s] Exceed Queue ▶ Queue Count: %d, Failover", InetAddress.getLocalHost().getHostName(), queued);
			
	    	for (String receiver : Env.getSmsProperties().getReceivers()) {
				if(SmsUtil.getLast5MinCountSMS(receiver, "Exceed Queue") <= 0) {
					SmsUtil.sendSMS(receiver, message);
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		} finally {
			logger.error("Failover Starting.......................................");
			failOver();
		}
	}
	
	//powerShell로 failover 실행
	private void failOver() {
		try {
			new ProcessBuilder("powershell.exe", "Move-ClusterGroup", "-Name", "smartATLAS").start();
			logger.info("powershell exec Done");			
		}catch(Exception e) {
			logger.error("failover exec error : ", e);
		}		
	}

	public int[] getThreadPoolStatus() {
		int poolSize = 0;
		int activeCount = 0;
		int queued = 0;
		synchronized(executor) {
			poolSize = executor.getPoolSize();
			activeCount = executor.getActiveCount();
			queued = executor.getQueue().size();
		}
		return new int[]{poolSize, activeCount, queued};
	}

	public int getIdleThreadCount() {
		int idleCnt = 0;
		synchronized(executor) {
			idleCnt = executor.getPoolSize()-executor.getActiveCount();
		}
		return idleCnt>=0?idleCnt:0;
	}


	public boolean isPaused() {
		return paused;
	}


	public void setPaused(boolean paused) {
		this.paused = paused;
	}

}
