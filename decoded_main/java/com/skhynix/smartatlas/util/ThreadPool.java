package com.skhynix.smartatlas.util;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadPoolExecutor;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class ThreadPool {
	private static final Logger logger = LoggerFactory.getLogger(ThreadPool.class);
	
	private static Map<String, ThreadPool> createdPools = new HashMap<>(); 
	
	private String poolName = "No Name";
	private ThreadPoolExecutor executor = null;
	private boolean closed = false;
	private boolean paused = false;
	
	public ThreadPool(String name, int maxThreadCount) {
		poolName = name; 
		executor = (ThreadPoolExecutor)Executors.newFixedThreadPool(maxThreadCount);
		
		executor.execute((() -> { logger.info("ThreadPool started : name={}", name); }));
		
		createdPools.put(name, this);
	}
	
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
			logger.error("Exception occured while executing thread {} - {}", poolName, work.toString(), e);
		}
	}
	
	public synchronized void close() throws AleadyClosedException {
		if (closed) throw new AleadyClosedException();
		closed = true;
		executor.shutdown();
	}
	
	public String getName() {
		return poolName;
	}
	
	public void pause() {
		paused = true;
	}
	
	public void resume() {
		paused = false;
	}
	
	public int getPoolSize() {
		return executor.getPoolSize();
	}
	
	public int getQueuedSize() {
		return executor.getQueue().size();
	}
	
	public long getCompletedThreadCount() {
		return executor.getCompletedTaskCount();
	}
	
	public int getActiveThreadCount() {
		return executor.getActiveCount();
	}
	
	public static ThreadPool getCreatedPool(String name) {
		return createdPools.get(name);
	}
	
	public static void pauseAll() {
		createdPools.values().forEach(x -> { 
			if (x != null) x.pause();
		});
	}
	
	public static void resumeAll() {
		createdPools.values().forEach(x -> { 
			if (x != null) x.resume();
		});
	}
}
