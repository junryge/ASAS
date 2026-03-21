public class PredictionPara {
	private transient Logger logger = LoggerFactory.getLogger(getClass());
	
	// fabId, edgeType
	private ConcurrentMap<String, Double> transWeightMap = new ConcurrentHashMap<>();
	
	// fabId, mcpName
	private ConcurrentMap<String, Double> junctionMultipleMap = new ConcurrentHashMap<>();
	
	// edgeType, eqpType 
	private ConcurrentMap<String, Double> transOverlapMap = new ConcurrentHashMap<>();
	
	private double lastHisWeight 		= 0.6;
	private long idleVhlCntPenalty 		= 3000;
	private long workVhlCntPenalty 		= 5000;
	private long workDestCntPenalty 	= 5000;
	private double afterWegith 			= 0.00211615406878313;
	private double predictWeight 		= 0.58382549273309;
	private double bias 				= 587.528052005396;
	private long useAvgCostStartAfter 	= 180000L;
	private long predictQueueTimeout 	= 30000L;
	private long idleMovingVhlStopCost 	= 2000L;
	private long predictCycle 			= 20L;
	
	private static class Singleton {
		public static final PredictionPara instance = new PredictionPara();
	}
	
	static public PredictionPara getInstance() {
		return Singleton.instance;
	}
	
	private PredictionPara() {
		try {
			this.refreshSinglePara();
			
			for (String fabId : DataService.getInstance().getFabPropertiesMap().keySet()) {
				this.transWeightMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.RAILEDGE, "ALL"), 
						getOrCreate("TRANS_WEIGHT", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.RAILEDGE, "ALL")), 135d ));
				this.transWeightMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.LIFTER), 
						getOrCreate("TRANS_WEIGHT", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.LIFTER)), 2000d ));
				this.transWeightMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.ZIPTOWER), 
						getOrCreate("TRANS_WEIGHT", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.ZIPTOWER)), 2500d ));
				this.transWeightMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.PODZIPTOWER), 
						getOrCreate("TRANS_WEIGHT", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.PODZIPTOWER)), 2500d ));
				this.transWeightMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.RETICLE), 
						getOrCreate("TRANS_WEIGHT", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.RETICLE)), 1500d ));
				this.transWeightMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.INTERLAYER), 
						getOrCreate("TRANS_WEIGHT", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.INTERLAYER)), 2500d ));
				this.transWeightMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.NA), 
						getOrCreate("TRANS_WEIGHT", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.NA)), 1500d ));
				this.transWeightMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.CNVEDGE, "ALL"), 
						getOrCreate("TRANS_WEIGHT", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.CNVEDGE, "ALL")), 200d ));
				this.transWeightMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.TRANSEDGE_ACQUIRE, "ALL"), 
						getOrCreate("TRANS_WEIGHT", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.TRANSEDGE_ACQUIRE, "ALL")), 10000d ));
				this.transWeightMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.TRANSEDGE_DEPOSIT, "ALL"), 
						getOrCreate("TRANS_WEIGHT", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.TRANSEDGE_DEPOSIT, "ALL")), 5000d ));		
				
				for(String mcpName : DataService.getInstance().getFabPropertiesMap().get(fabId).getMcpPropertiesMap().keySet()) {
					this.junctionMultipleMap.put(String.format("%s$%s", fabId, mcpName), 
							getOrCreate("JUNCTION_MULTIPLE", new Path(String.format(".%s$%s", fabId, mcpName)), 2.0d ));
				}
				
				this.transOverlapMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.RAILEDGE, "ALL"), 
						getOrCreate("TRANS_OVERLAP_INTERVAL_T", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.RAILEDGE, "ALL")), 2500d ));
				this.transOverlapMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.LIFTER), 
						getOrCreate("TRANS_OVERLAP_INTERVAL_T", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.LIFTER)), 5000d ));
				this.transOverlapMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.ZIPTOWER), 
						getOrCreate("TRANS_OVERLAP_INTERVAL_T", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.ZIPTOWER)), 5000d ));
				this.transOverlapMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.PODZIPTOWER), 
						getOrCreate("TRANS_OVERLAP_INTERVAL_T", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.PODZIPTOWER)), 5000d ));
				this.transOverlapMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.RETICLE), 
						getOrCreate("TRANS_OVERLAP_INTERVAL_T", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.RETICLE)), 5000d ));
				this.transOverlapMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.INTERLAYER), 
						getOrCreate("TRANS_OVERLAP_INTERVAL_T", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.INTERLAYER)), 5000d ));
				this.transOverlapMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.NA), 
						getOrCreate("TRANS_OVERLAP_INTERVAL_T", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.STKRMEDGE, Stocker.STK_TYPE.NA)), 5000d ));
				this.transOverlapMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.CNVEDGE, "ALL"), 
						getOrCreate("TRANS_OVERLAP_INTERVAL_T", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.CNVEDGE, "ALL")), 5000d ));
				this.transOverlapMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.TRANSEDGE_ACQUIRE, "ALL"), 
						getOrCreate("TRANS_OVERLAP_INTERVAL_T", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.TRANSEDGE_ACQUIRE, "ALL")), 5000d ));
				this.transOverlapMap.put(String.format("%s$%s$%s", fabId, EDGE_TYPE.TRANSEDGE_DEPOSIT, "ALL"), 
						getOrCreate("TRANS_OVERLAP_INTERVAL_T", new Path(String.format(".%s$%s$%s", fabId, EDGE_TYPE.TRANSEDGE_DEPOSIT, "ALL")), 5000d ));			
				
			}
		}catch(Exception e) {
			logger.error("PredictionPara initialize fail",e);
		}
	}
	
	private double getOrCreate(String key, Path path, double defaultValue) {
		return defaultValue;
	}
	
	public void refreshSinglePara() {
		this.setLastHisWeight(getOrCreate("LAST_HIS_WEIGHT", new Path("."), 0.9d ));
		//this.setVhlCountPenalty((long)getOrCreate("VHL_COUNT_PENALTY", new Path("."), 3000 ));
		this.setIdleVhlCntPenalty((long)getOrCreate("IDLE_VHL_CNT_PENALTY", new Path("."), 3000 ));
		this.setWorkVhlCntPenalty((long)getOrCreate("WORK_VHL_CNT_PENALTY", new Path("."), 5000 ));
		this.setWorkDestCntPenalty((long)getOrCreate("WORK_DEST_CNT_PENALTY", new Path("."), 5000 ));
		this.setAfterWegith(getOrCreate("REG_AFTER_WEIGHT", new Path("."), 0.00211615406878313 ));
		this.setPredictWeight(getOrCreate("REG_PREDICT_WEIGHT", new Path("."), 0.58382549273309 ));
		this.setBias(getOrCreate("REG_BIAS", new Path("."), 587.528052005396 ));
		this.setUseAvgCostStartAfter((long)getOrCreate("USE_AVG_COST_START_AFTER", new Path("."), 180000L ));
		this.setPredictQueueTimeout((long)getOrCreate("PREDICT_Q_TIMEOUT", new Path("."), 30000L ));
		this.setIdleMovingVhlStopCost((long)getOrCreate("IDLE_MOVING_VHL_STOP_COST", new Path("."), 2000L));
		this.setPredictCycle((long)getOrCreate("PREDICT_CYCLE", new Path("."), 5L));
	}
	
	public double getTransWeight(String fabId, EDGE_TYPE edgeType, String detType) {
		String key = String.format("%s$%s$%s", fabId, edgeType, detType);
		
		double value = 0;
		
		try {
			value = transWeightMap.get(key);
		} catch (Exception e) {
			logger.error("error occured while retieval value by key : {}", key, e);
			logger.warn("current transWeightMap : {}", JsonUtil.convertJSON(transWeightMap));
		}
		
		return value;
	}
	
	public double getJunctionMultiple(String fabId, String mcpName) {
		String key = String.format("%s$%s", fabId, mcpName);
		return this.junctionMultipleMap.get(key);
	}
	
	public double getTransOverlapIntervalT(String fabId, EDGE_TYPE edgeType, String detType) {
		String key = String.format("%s$%s$%s", fabId, edgeType, detType);
		
		return this.transOverlapMap.get(key);
	}

	public void setTransWeightMap(ConcurrentMap<String, Double> transWeightMap) {
		this.transWeightMap = transWeightMap;
	}
	
	public void setJunctionMultiple(ConcurrentMap<String, Double> junctionMultipleMap) {
		this.junctionMultipleMap = junctionMultipleMap;
	}
	
	public void setTransOverlapMap(ConcurrentMap<String, Double> transOverlapMap) {
		this.transOverlapMap = transOverlapMap;
	}

	public ConcurrentMap<String, Double> getTransWeightMap() {
		return transWeightMap;
	}
	
	public ConcurrentMap<String, Double> getJunctionMultipleMap() {
		return junctionMultipleMap;
	}

	public ConcurrentMap<String, Double> getTransOverlapMap() {
		return transOverlapMap;
	}

	public double getLastHisWeight() {
		return lastHisWeight;
	}

	public void setLastHisWeight(double lastHisWeight) {
		this.lastHisWeight = lastHisWeight;
	}

//	public long getVhlCountPenalty() {
//		return vhlCountPenalty;
//	}
//
//	public void setVhlCountPenalty(long vhlCountPenalty) {
//		this.vhlCountPenalty = vhlCountPenalty;
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "vhlCountPenalty", "Singleton", this.vhlCountPenalty, new TypeToken<Long>() {}.getType()));
//	}

	public long getIdleVhlCntPenalty() {
		return idleVhlCntPenalty;
	}

	public void setIdleVhlCntPenalty(long idleVhlCntPenalty) {
		this.idleVhlCntPenalty = idleVhlCntPenalty;
	}

	public long getWorkVhlCntPenalty() {
		return workVhlCntPenalty;
	}

	public void setWorkVhlCntPenalty(long workVhlCntPenalty) {
		this.workVhlCntPenalty = workVhlCntPenalty;
	}

	public long getWorkDestCntPenalty() {
		return workDestCntPenalty;
	}

	public void setWorkDestCntPenalty(long workDestCntPenalty) {
		this.workDestCntPenalty = workDestCntPenalty;
	}

	public double getAfterWegith() {
		return afterWegith;
	}

	public void setAfterWegith(double afterWegith) {
		this.afterWegith = afterWegith;
	}

	public double getPredictWeight() {
		return predictWeight;
	}

	public void setPredictWeight(double predictWeight) {
		this.predictWeight = predictWeight;
	}

	public double getBias() {
		return bias;
	}

	public void setBias(double bias) {
		this.bias = bias;
	}

	public long getUseAvgCostStartAfter() {
		return useAvgCostStartAfter;
	}

	public void setUseAvgCostStartAfter(long useAvgCostStartAfter) {
		this.useAvgCostStartAfter = useAvgCostStartAfter;
	}

	public long getPredictQueueTimeout() {
		return predictQueueTimeout;
	}

	public void setPredictQueueTimeout(long predictQueueTimeout) {
		this.predictQueueTimeout = predictQueueTimeout;
	}

	public long getIdleMovingVhlStopCost() {
		return idleMovingVhlStopCost;
	}

	public void setIdleMovingVhlStopCost(long idleMovingVhlStopCost) {
		this.idleMovingVhlStopCost = idleMovingVhlStopCost;
	}

	public long getPredictCycle() {
		return predictCycle;
	}

	public void setPredictCycle(long predictCycle) {
		this.predictCycle = predictCycle;
	}
}
