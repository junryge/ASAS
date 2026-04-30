package com.atlas.cnv;

/*
 * IMPORTS REQUIRED (for reference):
 * import org.quartz.Job;
 * import org.quartz.JobExecutionContext;
 * import org.quartz.JobExecutionException;
 * import org.slf4j.Logger;
 * import org.slf4j.LoggerFactory;
 * import java.util.ArrayList;
 * import java.util.List;
 * import java.util.Map;
 * import java.util.ConcurrentHashMap;
 * (DataService, Env, Util, Tuple, LogpressoAPI classes if available)
 */

/**
 * CNV (Conveyor) Traffic Batch - Quartz Job for collecting and storing conveyor traffic data.
 * Executes every 1 minute to batch process CnvEdge traffic information.
 *
 * Features:
 * - Iterates over CnvEdge entries to collect avgTransferIntervalT data
 * - Builds Tuple objects with: createTime, fabId, mcpName, cnvEdgeId, avgTransferIntervalT, fromNodeId, toNodeId
 * - Batch inserts into Logpresso "ATLAS_CNV_TRAFFIC" table
 * - Factory-specific and MCP-specific traffic collection
 */
public class CnvTrafficBatch implements Job {
	private final Logger logger = LoggerFactory.getLogger(getClass());
	private long currentDateTime = -1;
	private final int DELAYED_TIME = 1000 * 60;
	private static ConcurrentMap<String, Long> lastHisCntMap = new ConcurrentHashMap<>();

	@Override
	public void execute(JobExecutionContext arg0) throws JobExecutionException {
		if (Util.isCurrentIC()) {
			this.currentDateTime = System.currentTimeMillis();

			for (Map.Entry<String, FunctionItem> functionItemEntry : Env.getSwitchMap().entrySet()) {
				String key = functionItemEntry.getKey();	// {fabId}:{mcpName}
				FunctionItem functionItem = functionItemEntry.getValue();

				if (functionItem != null && functionItem.isUseCnvTraffic()) {
					String fabId = functionItem.getFabId();
					String mcpName = functionItem.getMcpName();

					logger.info("... `CnvTrafficBatch` has started [fab: {} | mcp: {}]", fabId, mcpName);

					long timer = System.currentTimeMillis();

					this._run(fabId, mcpName, functionItem);

					long checkTimer = System.currentTimeMillis() - timer;

					if (checkTimer >= DELAYED_TIME) {
						logger.error("... !!!DELAYED!!! `CnvTrafficBatch` has finished [fab: {} | mcp: {}] [elapsed time: {}m ({}ms)]", fabId, mcpName, checkTimer / (60 * 1000), checkTimer);
					} else {
						logger.info("... `CnvTrafficBatch` has finished [fab: {} | mcp: {}] [elapsed time: {}ms]", fabId, mcpName, checkTimer);
					}
				}
			}
		}
	}

	private void _run(String fabId, String mcpName, FunctionItem functionItem) {
		List<Tuple> logpressoData = new ArrayList<>();

		try {
			// Iterate over CnvEdge entries (not RailEdge)
			for (CnvEdge cnvEdge : DataService.getDataSet().getCnvEdgeMap().values()) {
				if (!cnvEdge.getFabId().equals(fabId)) {
					continue;
				}

				String cnvEdgeId = cnvEdge.getId();
				long avgTransferIntervalT = cnvEdge.getAvgTransferIntervalT();
				String fromNodeId = cnvEdge.getFromNodeId();
				String toNodeId = cnvEdge.getToNodeId();

				lastHisCntMap.putIfAbsent(cnvEdgeId, 0L);

				if (functionItem.isUseCnvTrafficSub()) {
					Tuple tuple = this._buildBase(cnvEdge, functionItem);

					if (tuple != null) {
						logpressoData.add(tuple);
					}
				}

				// Update last history count
				lastHisCntMap.put(cnvEdgeId, cnvEdge.getHisCnt());
			}

			// Insert batched data into Logpresso
			if (!logpressoData.isEmpty()) {
				Util.insertInLogpressoDatabase(logpressoData, "ATLAS_CNV_TRAFFIC", this.getClass().getSimpleName());

				logger.debug("... Inserted {} CNV traffic records [fab: {} | mcp: {}]",
					logpressoData.size(), fabId, mcpName);
			}

		} catch (Exception e) {
			logger.error("... Error during CNV traffic batch processing [fab: {} | mcp: {}]", fabId, mcpName, e);
		}
	}

	private Tuple _buildBase(CnvEdge cnvEdge, FunctionItem functionItem) {
		Tuple result = new Tuple();
		String fabId = functionItem.getFabId();
		String mcpName = functionItem.getMcpName();

		try {
			String cnvEdgeId = cnvEdge.getId();
			long avgTransferIntervalT = cnvEdge.getAvgTransferIntervalT();
			String fromNodeId = cnvEdge.getFromNodeId();
			String toNodeId = cnvEdge.getToNodeId();

			result.put("createTime", this.currentDateTime);
			result.put("fabId", fabId);
			result.put("mcpName", mcpName);
			result.put("cnvEdgeId", cnvEdgeId);
			result.put("avgTransferIntervalT", avgTransferIntervalT);
			result.put("fromNodeId", fromNodeId);
			result.put("toNodeId", toNodeId);

		} catch (Exception e) {
			logger.error("... Error building CNV traffic tuple [edgeId: {}]", cnvEdge.getId(), e);
			return null;
		}

		return result;
	}
}
