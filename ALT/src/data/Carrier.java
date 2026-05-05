public class Carrier {
	transient private ReentrantLock lock = new ReentrantLock(true);
	transient private Logger logger = LoggerFactory.getLogger(getClass());
	private String id 						= "";
	private String name 					= "";
	private String eqpId 					= "";
	private String jobId 					= "";
	private String cmdId 					= "";
	private String locId 					= ""; // vhl/node
	private String subType 					= "";
	private String lotId 					= "";
	private String router 					= "";
	private String stepId 					= "";
	private String batchId 					= "";
	private int batchSeq 					= 0;
	private String requestor 				= "";
	private CARRIER_STATE state 			= CARRIER_STATE.NONE;
	private long stateTime 					= -1;
	private CARRIER_STATE oldState 			= CARRIER_STATE.NONE;
	private long oldStateTime 				= -1;
	private PROCESS_TYPE processType 		= PROCESS_TYPE.ALL;
	private boolean isN2 					= false;
	private String definiteFlag 			= "NO"; // "NO"|"N2"|"YES"
	private int priority 					= 50;
	private long installTime 				= -1;
	private String requestedDestFDestPair 	= "";
	
	/**
	 * A constructor to set the batchFlush with the initialization to other fields.
	 * @param id
	 * @param name
	 */
	public Carrier(final String id, final String name, final boolean batchFlush) {
		this.id 	= id;
		this.name 	= name;
		
		if (batchFlush) {
			this.enableBatchFlush();
		} else {
			this.disableBatchFlush();
		}
	}
	
	public Carrier(String id, String name) {
		this.id = id;
		this.name = name;
	}

	public String getEqpId() {
		return eqpId;
	}

	public void setEqpId(String eqpId) {
		this.eqpId = eqpId;
	}

	public String getJobId() {
		return jobId;
	}

	public void setJobId(String jobId) {
		LoggerFactory.getLogger(this.getClass()).debug("{} jobId changing {} -> {}", this.id, this.jobId, jobId);
		this.jobId = jobId;
	}

	public String getCmdId() {
		return cmdId;
	}

	public void setCmdId(String cmdId) {
		getLogger().debug("{} oldCmdId({}) -> setCmdId({})", id, this.cmdId, cmdId);
		
		this.cmdId = cmdId;		
	}

	public String getLocId() {
		return locId;
	}

	public void setLocId(String locId) {
		this.locId = locId;
	}

	public CARRIER_STATE getState() {
		return state;
	}

	public void setState(CARRIER_STATE state) {
		this.oldState 		= this.state;
		this.oldStateTime 	= this.stateTime;
		this.state 			= state;
		this.stateTime 		= System.currentTimeMillis();
	}

	public long getStateTime() {
		return stateTime;
	}

	public void setStateTime(long stateTime) {
		this.stateTime = stateTime;
	}

	public String getId() {
		return id;
	}

	public long getOldStateTime() {
		return oldStateTime;
	}

	public void setOldStateTime(long oldStateTime) {
		this.oldStateTime = oldStateTime;
	}
	
	public boolean isN2() {
		return isN2;
	}

	public void setN2(boolean isN2) {
		this.isN2 = isN2;
	}

	
	public String getSubType() {
		return subType;
	}

	public void setSubType(String subType) {
		this.subType = subType;
	}

	public String getLotId() {
		return lotId;
	}

	public void setLotId(String lotId) {
		this.lotId = lotId;
	}

	public String getRouter() {
		return router;
	}

	public void setRouter(String router) {
		this.router = router;
	}

	public String getStepId() {
		return stepId;
	}

	public void setStepId(String stepId) {
		this.stepId = stepId;
	}

	public String getBatchId() {
		return batchId;
	}

	public void setBatchId(String batchId) {
		this.batchId = batchId;
	}

	public int getBatchSeq() {
		return batchSeq;
	}

	public void setBatchSeq(int batchSeq) {
		this.batchSeq = batchSeq;
	}

	public PROCESS_TYPE getProcessType() {
		return processType;
	}

	public void setProcessType(PROCESS_TYPE processType) {
		this.processType = processType;
	}

	public void setId(String id) {
		this.id = id;
	}

	public String getDefiniteFlag() {
		return definiteFlag;
	}

	public void setDefiniteFlag(String definiteFlag) {
		this.definiteFlag = definiteFlag;
	}

	public int getPriority() {
		return priority;
	}

	public void setPriority(int priority) {
		this.priority = priority;
	}

	public String getRequestor() {
		return requestor;
	}

	public void setRequestor(String requestor) {
		this.requestor = requestor;
	}
	
	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public ReentrantLock getLock() {
		if (this.lock == null) { 
			this.lock = new ReentrantLock(true);
		}
		
		try {
			if (!this.lock.tryLock(50, TimeUnit.MILLISECONDS)) {
				return null; // Couldn't get the lock. If the caller must not unlock in case of this.
			}
		} catch (InterruptedException e) {
			LoggerFactory.getLogger(getClass()).error("Interupted",e);
		}
		
		return this.lock;
	}

	public void unLock(){
		lock.unlock();
	}

	/**
	 * Enables the batch flush for the Redis.
	 */
	public void enableBatchFlush() {
//		this.batchFlush = true;
	}
	
	/**
	 * Disables the batch flush for the Redis.
	 */
	public void disableBatchFlush() {
//		this.batchFlush = false;
	}
	
	public enum PROCESS_TYPE{
		ALL, 
		FOUP, 
		POD, 
		CU, 
		FOSB, 
		CLEANFOUP, 
		WTFOUP, 
		POD_RSP150, 
		POD_RSP200, 
		POD_EUVPELLICLE, 
		POD_EUVNONPELLICLE,
		WB,
		WB_CU
	}
	public enum CARRIER_STATE{		
		NONE("NONE"),
		INSTALLED("INSTALLED"),
		COMPLETED("COMPLETED"),
		WAIT_OUT("WAIT_OUT"),
		ALTERNATE("ALTERNATE"),
		WAIT_IN("WAIT_IN"),
		TRANSFERRING("TRANSFERRING");
		
		private final String state;
		
		CARRIER_STATE(String state){
			this.state = state;
		}
		
		public String getState(){
			return this.state;
		}
	}
	public CARRIER_STATE getOldState() {
		return oldState;
	}

	public void setOldState(CARRIER_STATE oldState) {
		this.oldState = oldState;
	}

	public long getInstallTime() {
		return installTime;
	}

	public void setInstallTime(long installTime) {
		this.installTime = installTime;
	}
	
	public String getContainerId() {
		CarrierContainable carrierContainable = null;
		
		if (StringUtils.isNotEmpty(eqpId) && StringUtils.isNotEmpty(locId)) {
			Eqp carrierEqp = DataService.getDataSet().getAllEqpMap().get(eqpId);
			
			carrierContainable = DataService.getDataSet().getCarrierContainableByCarrierLoc(locId, carrierEqp.getFabId());			
		}
		
		if(carrierContainable != null) {
			return carrierContainable.getId();
		} else {
			return "";		
		}
	}
	
	private Logger getLogger() {
		if(logger==null) {
			logger = LoggerFactory.getLogger(getClass());
		}
		return logger;
	}

	public String getRequestedDestFDestPair() {
		return requestedDestFDestPair;
	}

	public void setRequestedDestFDestPair(String requestedDestFDestPair) {
		this.requestedDestFDestPair = requestedDestFDestPair;
	}
}
