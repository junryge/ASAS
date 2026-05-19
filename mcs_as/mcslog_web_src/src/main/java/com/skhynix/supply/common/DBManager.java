package com.skhynix.supply.common;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;

import com.logpresso.client.Logpresso;
import com.logpresso.client.Query;
import com.skhynix.supply.common.connection.ConnectionInfo;
import com.skhynix.supply.common.connection.ConnectionInfoPool;

/*
 * 2022. 6.16. X0122410 : fab site 추가로 connection접속로직 수정
 */
public class DBManager {

	private String fabSite = null;
	private ConnectionInfo connectionInfo = null;
	int queryId = 0;
	Logpresso client = null;
	private static final Log log = LogFactory.getLog(DBManager.class);
	private static ScheduledThreadPoolExecutor timer = new ScheduledThreadPoolExecutor(1);

	private static class Canceller implements Runnable {
		private Logpresso c;
		private int queryId;

		public Canceller(Logpresso client, int queryId) {
			this.c = client;
			this.queryId = queryId;
		}

		@Override
		public void run() {
			try {
				if (this.c.isClosed())
					return;
				this.c.stopQuery(queryId);
			} catch (Throwable t) {
				// logging
				log.warn("!!! ■ Canceller stopQuery Exception " + t.getMessage());
			}
		}
	}

	public DBManager(String fabSite) {
		// 접속 정보 최초 초기화
		// 2022. 6.16. X0122410 : fab site 추가로 connection접속로직 수정
		// if(!ConnectionInfo.init) ConnectionInfo.init();
		connectionInfo = ConnectionInfoPool.getConnectionInfo(fabSite);
		this.fabSite = fabSite;
	}

	@SuppressWarnings({ "unchecked", "rawtypes" })
	public List<Map> executeQuery(String queryStmt) throws Exception {
		long offset = 0;
		int limit = 10000; // UI 에서 조회 할 수 있는 최대 개수
		// long count = 0;
		int rowSize = 0;
		int subResultSize = 0;
		long before = (long) 0.0; // System.currentTimeMillis();
		Query query = null;
		long loaded = 0;

		List<Map> result = null; // new ArrayList<Map>();
		// ScheduledThreadPoolExecutor timer;
		ScheduledFuture<?> future;

		log.info("");
		log.info("■ ■ ■ QUERY START : " + this.fabSite);
		log.info("■ QUERY : " + queryStmt);

		this.client = getConnect();
		if (this.client == null)
			return null;

		try {
			before = System.currentTimeMillis();
			this.queryId = this.client.createQuery(queryStmt.trim()); // 쿼리생성
			// log.warn("client start query id is " + this.queryId);
			this.client.startQuery(this.queryId); // 쿼리시작
			query = this.client.getQuery(this.queryId);
			// timer = new ScheduledThreadPoolExecutor(1);
			future = timer.schedule(new Canceller(this.client, this.queryId), Common.searchDelayTime,
					TimeUnit.MILLISECONDS);
			this.client.waitUntil(this.queryId, (long) limit);

			String status = query.getStatus();
			loaded = query.getLoadedCount();

			if (!status.equalsIgnoreCase("CANCELLED")) {
				Map resultSet = this.client.getResult(this.queryId, offset, limit); // 쿼리 결과조회
				// subResultSize = (((Long) resultSet.get("count")).intValue());
				// subResultSize = (int)resultSet.get("count");
				// subResultSize = Long.valueOf(String.valueOf(resultSet.get("count")));
				subResultSize = Integer.valueOf(String.valueOf(resultSet.get("count")));
				// result = ((List<Map>) resultSet.get("result"));
				if (subResultSize < loaded) {
					result = ((List<Map>) resultSet.get("result")).subList(0, subResultSize);
				} else {
					result = ((List<Map>) resultSet.get("result")).subList(0, (int) loaded); // 조회 결과수만큼 적재 강제
				}
				rowSize = result.size();
			}

			log.info("■ Current Thread Name : " + Thread.currentThread().getName());
			log.info("■ QUERY ID : " + this.queryId);
			log.info("■ QUERY LOADED SIZE : " + loaded);
			log.info("■ QUERY ROW SIZE : " + rowSize);
			log.info("■ QUERY STATUS:" + status);
			log.info("■ QUERY ELAPSED TIME : " + (System.currentTimeMillis() - before) + " ms");

			// Thread.sleep(1000 * 100); //100초 대기

			if (future != null) {
				// log.warn("client cancel query id is " + this.queryId);
				if (!future.isCancelled())
					future.cancel(true);
				future = null;
			}

		} catch (Exception e) {
			log.error("Problem occurred at executing operation : ", e);
		} finally {
			if (this.client != null) {
				try {
					this.client.removeQuery(this.queryId); // 쿼리제거
					// log.warn("client end query id is " + this.queryId);
					this.client.close();
				} catch (Exception e) {
					log.error("Problem occurred at executing operation in finally : ", e);
				}
				this.client = null;
			}
		}
		return result;
	}

	/* ConnectionInfo.host_primary */
	private Logpresso getConnect() {
		Logpresso _client = null;

		try {
			// primary
			_client = new Logpresso();
			_client.connect(connectionInfo.getHostPrimary(), connectionInfo.getLogpressoPort(),
					connectionInfo.getLogpressoID(), connectionInfo.getLogpressoPW(), 500, 300000);
		} catch (Exception e) {
			try {
				// secondary
				log.warn("Problem occurred at executing operation :" + e.getMessage());
				_client.connect(connectionInfo.getHostSecondary(), connectionInfo.getLogpressoPort(),
						connectionInfo.getLogpressoID(), connectionInfo.getLogpressoPW(), 500, 300000);
				log.warn("Connection Host Changed to : " + connectionInfo.getHostSecondary());
			} catch (Exception e2) {
				log.warn("Problem occurred at executing operation(Secondary Host) :" + e.getMessage());
			}
		}

		return _client;
	}

	public void executeQueryStop() {
		if (this.client == null)
			return;

		try {
			if (!this.client.isClosed())
				this.client.stopQuery(this.queryId);
		} catch (Throwable e) {
			log.warn("Problem occurred at executing executeQueryStop :" + e.getMessage());
		} finally {
			try {
				this.client.removeQuery(this.queryId); // 쿼리제거
				this.client.close();
			} catch (Exception e) {
				log.warn("Problem occurred at executing operation : " + e.getMessage());
			}
			this.client = null;
		}
	}
}