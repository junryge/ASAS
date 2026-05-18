package com.skhynix.smartatlas.db.logpresso;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Future;
import java.util.concurrent.FutureTask;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Cursor;
import com.logpresso.client.Logpresso;
import com.logpresso.client.Query;
import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.environment.type.DbProperties;
import com.skhynix.smartatlas.util.CryptoUtil;

public class LogpressoAPI {
	private static final Logger logger = LoggerFactory.getLogger(LogpressoAPI.class);
	private static ScheduledThreadPoolExecutor timer = new ScheduledThreadPoolExecutor(1);
	public static int activeNode = 1;
	private static final int CONN_TIMEOUT = 500;
	private static final int READ_TIMEOUT = 5000;
	private static int _ActiveNode = 1;

	/**
	 * cancel delayed query on logpresso by queryid
	 * 
	 * @author X0122410
	 * 
	 *
	 */
	private static class Canceller implements Runnable {
		private Logpresso client;
		private int queryId;

		public Canceller(Logpresso client, int queryId) {
			this.client = client;
			this.queryId = queryId;
		}

		@Override
		public void run() {
			try {
				Logpresso c = client;
				if (c.isClosed())
					return;
				c.stopQuery(queryId);
			} catch (Throwable t) {
				// logging
				logger.warn("!!! * Canceller stopQuery Exception", t.getMessage());
			}
		}
	}

	private static Logpresso getConnection() {
		return getConnection(null, CONN_TIMEOUT, READ_TIMEOUT);
	}

	private static Logpresso getConnection(String fab) {
		return getConnection(fab, CONN_TIMEOUT, READ_TIMEOUT);
	}

	private static Logpresso getConnection(String fab, int connectTimeout, int readTimeout) {
		Logpresso client = null;
		int active = _ActiveNode;
		DbProperties properties;

		try {
			client = new Logpresso();

			if (fab == null) {
				properties = Env.getLogpressoPropertiesMap().entrySet().iterator().next().getValue();
			} else {
				properties = Env.getLogpressoPropertiesMap().get(fab);
			}

			try {
				// 1. encoding account Info
				switch (active) {
				case 1:
					client.connect(properties.getHosts()[0], properties.getPort(), properties.getId(),
							CryptoUtil.decrypt(properties.getPassword(), Env.getLogpressoDecryptKey()), connectTimeout,
							readTimeout);
					logger.debug("active node : [{}], logpressoHost : [{}]", active, properties.getHosts()[0]);
					break;
				case 2:
					try { // 20250609: X0152990 : 1번서버 우선 연결 추가
						client.connect(properties.getHosts()[0], properties.getPort(), properties.getId(),
								CryptoUtil.decrypt(properties.getPassword(), Env.getLogpressoDecryptKey()),
								connectTimeout, readTimeout);
						logger.debug("active node : [{}], logpressoHost : [{}]", active, properties.getHosts()[0]);
					} catch (Exception e) {
						client.connect(properties.getHosts()[1], properties.getPort(), properties.getId(),
								CryptoUtil.decrypt(properties.getPassword(), Env.getLogpressoDecryptKey()),
								connectTimeout, readTimeout);
						logger.debug("active node : [{}], logpressoHost : [{}]", active, properties.getHosts()[1]);
					}
					break;
				}
			} catch (Exception ignore) { // 1,2 서버모두 연결 실패시
				logger.error("active node {} connect fail. changing connect node", active, ignore);

				if (client != null) {
					try {
						client.close();
					} catch (Exception e) {}

					client = new Logpresso();
				}

				if (active == _ActiveNode) {
					switch (active) {
					case 2:
						LogpressoAPI._ActiveNode = 1;
						client.connect(properties.getHosts()[0], properties.getPort(), properties.getId(),
								CryptoUtil.decrypt(properties.getPassword(), Env.getLogpressoDecryptKey()),
								connectTimeout, readTimeout);
						logger.debug("active node : [{}], logpressoHost : [{}]", active, properties.getHosts()[0]);
						break;
					case 1: // 20250609: X0152990 : 1에서 문제 발생시 1 재검증
						try {
							LogpressoAPI._ActiveNode = 1;
							client.connect(properties.getHosts()[0], properties.getPort(), properties.getId(),
									CryptoUtil.decrypt(properties.getPassword(), Env.getLogpressoDecryptKey()),
									connectTimeout, readTimeout);
							logger.debug("active node : [{}], logpressoHost : [{}]", active, properties.getHosts()[0]);
						} catch (Exception e) {
							LogpressoAPI._ActiveNode = 2;
							client.connect(properties.getHosts()[1], properties.getPort(), properties.getId(),
									CryptoUtil.decrypt(properties.getPassword(), Env.getLogpressoDecryptKey()),
									connectTimeout, readTimeout);
							logger.debug("active node : [{}], logpressoHost : [{}]", active, properties.getHosts()[1]);
						}
						break;
					}
				}
			}
		} catch (Exception e) {
			logger.error("setDBConnection Fail!!", e);
		}

		return client;
	}

	/**
	 * Send a query to the Logpresso and get the result, and return them as a list.
	 * 
	 * @param paramQuery
	 * @return List<Map>
	 */
	public static List<Map<String, Object>> responseResult(String paramQuery) {
		return responseResult(null, paramQuery);
	}

	/*
	 * 2022.09.05 X0122410 MCSLOG Logpresso > responseMcslogResult
	 */
	public static List<Map<String, Object>> responseResult(String fabSite, String paramQuery) {
		// M14 Atlaslog 이전 => IC 임시코드
		if ("M14".equals(fabSite)) {
			fabSite = "IC";
		}

		Cursor cursor = null;
		Logpresso client = null;
		List<Map<String, Object>> resultSetLocal = null;

		try {
			resultSetLocal = new ArrayList<Map<String, Object>>();

			logger.info("* fabSite : " + fabSite);
			logger.info("* Query : " + paramQuery);
			client = getConnection(fabSite);
			cursor = client.query(paramQuery);

			while (cursor.hasNext()) {
				resultSetLocal.add(cursor.next().toMap());
			}
			logger.info("* Query End");

		} catch (Exception ignore) {
			logger.warn("!!!! Logpresso QueryError ", ignore);
		} finally {
			final Cursor tempCursor = cursor;
			final Logpresso tempClient = client;
			
			try {
				if (tempCursor != null) {
					var taskClosingCursor = new FutureTask<>(() -> {
						tempCursor.close();
						return tempCursor;
					});
					
					taskClosingCursor.run();
					taskClosingCursor.get(10, TimeUnit.SECONDS);
				}
			} catch (Exception ignore) {
				logger.warn("!!! * cursor close Exception", ignore);
			}

			try {
				if (tempClient != null) {
					var taskClosingClient = new FutureTask<>(() -> {
						tempClient.close();
						return tempClient;
					});
					
					taskClosingClient.run();
					taskClosingClient.get(10, TimeUnit.SECONDS);
				}
			} catch (Exception ignore) {
				logger.warn(" !!! * client close Exception ", ignore);
			}
		}

		return resultSetLocal;
	}

	public static List<Map<String, Object>> executeQuery(String queryStmt) {
		return executeQuery(null, queryStmt, 5000, 15);
	}

	public static List<Map<String, Object>> executeQuery(String fabSite, String queryStmt) {
		return executeQuery(fabSite, queryStmt, 0, 60);
	}

	@SuppressWarnings("unchecked")
	public static List<Map<String, Object>> executeQuery(String fabSite, String queryStmt, int limit, int delaySecond) {
		// M14 Atlaslog 이전 => IC 임시코드
		if ("M14".equals(fabSite)) {
			fabSite = "IC";
		}

		List<Map<String, Object>> resultSetLocal = new ArrayList<Map<String, Object>>();
		Logpresso client = null;
		Query query = null;
		int queryId = -1;
		int searchDelayMillsec = 15000;
		long offset = 0;
		int rowSize = 0;
		long before = (long) 0.0;

		logger.info("* fabSite : " + fabSite);
		logger.info("* QUERY START *");
		logger.info("* QUERY : " + queryStmt);
		try {
			before = System.currentTimeMillis();
			client = getConnection(fabSite);

			queryId = client.createQuery(queryStmt.trim()); // 쿼리생성
			client.startQuery(queryId); // 쿼리시작
			long loaded = 0;
			query = client.getQuery(queryId);

			timer.schedule(new Canceller(client, queryId), delaySecond, TimeUnit.SECONDS);
			if (limit > 0)
				client.waitUntil(queryId, (long) limit);
			else
				client.waitUntil(queryId, null);

			String status = query.getStatus();
			loaded = query.getLoadedCount();
			if (limit > 0 && loaded > limit)
				loaded = limit;

			if (!status.equalsIgnoreCase("CANCELLED")) {
				Map<String, Object> queryResult = client.getResult(queryId, offset, (int) loaded); // 쿼리 결과조회
				resultSetLocal = (List<Map<String, Object>>) queryResult.get("result");
				rowSize = resultSetLocal.size();
			}

			logger.info("* QUERY ID : " + queryId);
			logger.info("* QUERY LOADED SIZE : " + loaded);
			logger.info("* QUERY ROW SIZE : " + rowSize);
			logger.info("* QUERY STATUS:" + status);
			logger.info("* QUERY ELAPSED TIME : " + (System.currentTimeMillis() - before) + " ms");
			logger.info("* SEARCH DELAY : " + searchDelayMillsec + " ms");

		} catch (Exception e) {
			logger.warn("Problem occurred at executing operation : ", e);
		} finally {
			if (client != null) {
				try {
					client.removeQuery(queryId); // 쿼리제거
					client.close();
					client = null;
				} catch (IOException e) {
					logger.warn("Problem occurred at executing operation : ", e);
				}
			}
		}

		return resultSetLocal;
	}

	public static boolean setDropTable(String sTable) {
		boolean isSuccess = false;
		Logpresso client = null;
		try {
			client = getConnection();
			client.dropTable(sTable);

			isSuccess = true;
		} catch (Exception ignore) {
			isSuccess = false;
			logger.warn("!!!! Error ", ignore);
		} finally {
			try {
				if (client != null) {
					client.close();
				}
			} catch (Exception ignore) {
				logger.warn("!!! * client close Exception ", ignore);
			}
		}

		return isSuccess;
	}

	public static boolean setCreateTable(String sTable) {
		boolean isSuccess = false;
		Logpresso client = null;
		try {
			client = getConnection();
			logger.debug("* Query : " + sTable);
			client.query("import create=t " + sTable);

			isSuccess = true;
		} catch (Exception ignore) {
			isSuccess = false;
			logger.warn("!!!! Error ", ignore);
		} finally {
			try {
				if (client != null) {
					client.close();
				}
			} catch (Exception ignore) {
				logger.warn(" !!! * client close Exception", ignore);
			}
		}

		return isSuccess;
	}

	public static boolean setInsertTable(String sQuery) {
		boolean isSuccess = false;
		Logpresso client = null;
		try {
			client = getConnection();

			sQuery = sQuery.replace('"', '\"').replace('\r', ' ').replace('\n', ' ');
			client.query(sQuery);

			isSuccess = true;
		} catch (Exception ex) {
			isSuccess = false;
		} finally {
			try {
				if (client != null) {
					client.close();
				}
			} catch (Exception ignore) {
				logger.warn("!!! * client close Exception", ignore);
			}
		}

		return isSuccess;
	}

	public static boolean setPurgeTableData(String from, String to, String sTable) {
		boolean isSuccess = false;
		Logpresso client = null;
		try {
			client = getConnection();

			logger.debug("* Query : " + sTable);
			client.query("purge from=" + from + " to=" + to + " " + sTable); // data delete query

			isSuccess = true;

		} catch (Exception ignore) {
			isSuccess = false;
			logger.warn("!!!! Error ", ignore);
		} finally {
			try {
				if (client != null) {
					client.close();
				}
			} catch (Exception ignore) {
				logger.warn("!!! * client close Exception ", ignore);
			}
		}

		return isSuccess;
	}

	public static boolean setInsertTuple(String table, Tuple tuple, int timeoutSecond) {
		return setInsertTuples(table, List.of(tuple), timeoutSecond);
	}

	public static boolean setInsertTuples(String table, List<Tuple> tuples, int timeoutSecond) {
		try {
			try {
				return setInsertTuplesInternal(table, tuples, timeoutSecond);
			} catch (TimeoutException e) {
				for (int i = 1; i <= 3; i++) {
					try {
						logger.error("Timeout Retry : " + i + " Time(s)");
						return setInsertTuplesInternal(table, tuples, timeoutSecond);
					} catch (TimeoutException ex) {
					}
				}

				logger.error("Timeout Failed");
			}
		} catch (Exception e) {
			logger.error("insert Error ", e);
		}

		return false;
	}

	private static boolean setInsertTuplesInternal(String table, List<Tuple> tuples, int timeoutSecond)
			throws Exception {
		Logpresso client = null;

		try {
			client = getConnection();

			Future<Integer> result = client.insert(table, tuples);

			client.flush();
			result.get(timeoutSecond, TimeUnit.SECONDS);
		} finally {
			try {
				if (client != null) {
					client.close();
				}
			} catch (Exception ignore) {
				logger.warn("!!! * client close Exception ", ignore);
			}
		}

		return true;
	}
}
