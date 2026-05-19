//package com.skhynix.supply.common;
//import java.util.concurrent.Callable;
//import java.util.concurrent.Executors;
//import java.util.concurrent.ThreadPoolExecutor;
//import java.util.concurrent.atomic.AtomicLong;
//
//import org.apache.commons.logging.Log;
//import org.apache.commons.logging.LogFactory;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//
//public class ThreadPool {
//	
//	private AtomicLong seq = new AtomicLong(0);
//	private static final Log log = LogFactory.getLog(ThreadPool.class);
//	private boolean closed = false;
//	public ThreadPoolExecutor executor = null;
//	
//	private static class Singleton{
//    	private static final ThreadPool instance = new ThreadPool( 15, 15, 15, 15 );
//    }
//	
//	public static ThreadPool getInstance() {
//		return Singleton.instance;
//	}
//
//
//	private ThreadPool(int initThreadCount, int maxThreadCount, int minThreadCount, int allowedIdleCount) {
//		executor = (ThreadPoolExecutor) Executors.newFixedThreadPool(maxThreadCount);		
//	}
//
//	public ThreadPool(int initThreadCount, int maxThreadCount, int minThreadCount) {
//		executor = (ThreadPoolExecutor) Executors.newFixedThreadPool(maxThreadCount);
//	}
//
//	/**
//	 * 큐에 작업할 객체를 삽입한다.
//	 *
//	 * @work 쓰레드가 수행할 작업
//	 */
//	public synchronized void execute(Runnable work) {
//		if (closed) return;
//		try {
//			executor.execute( work );
//			
//			log.info(" Current Thread Name : " + Thread.currentThread().getName());			
//		}catch(Exception e) {
//			log.error("Exception occured while executing thread {} : " + work.toString(), e);
//		}
//		if(seq.incrementAndGet() % 20000 == 0) { 
//			printStatus();
//		}
//	}
//	
//	/**
//	 * 쓰레드 풀을 종료한다.
//	 */
//	public synchronized void close() {
//		if (closed) return;
//		closed = true;
//		executor.shutdown();
//	}
//
//	public void printStatus() {
//		synchronized(executor) {
//			int poolSize = executor.getPoolSize();
//			int activeCount = executor.getActiveCount();
//			long queued = executor.getQueue().size();
//			
//			log.warn(String.format("[Created :\t{}][Active :\t{}][Idle :\t{}][Queued :\t{}][AllReceived : \t{}]"
//					,poolSize, activeCount, poolSize-activeCount, queued, seq)) ;
//		}
//	}
//
//	public int[] getThreadPoolStatus() {
//		int poolSize = 0;
//		int activeCount = 0;
//		int queued = 0;
//		synchronized(executor) {
//			poolSize = executor.getPoolSize();
//			activeCount = executor.getActiveCount();
//			queued = executor.getQueue().size();
//		}
//		return new int[]{poolSize, activeCount, queued};
//	}
//
//	public int getIdleThreadCount() {
//		int idleCnt = 0;
//		synchronized(executor) {
//			idleCnt = executor.getPoolSize()-executor.getActiveCount();
//		}
//		return idleCnt>=0?idleCnt:0;
//	}
//
//}
