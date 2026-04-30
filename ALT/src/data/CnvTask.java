public class CnvTask {
	transient static private ConcurrentMap<String, ReentrantLock> lockMap = new ConcurrentHashMap<String, ReentrantLock>();
	private String id				= "";
	private long createTime 		= -1;
	private long frNodeLocatedTime 	= -1;
	private long srcIdReadTime		= -1;
	private long cmdTime 			= -1;
	private long initiatedTime		= -1;
	private long destIdReadTime		= -1;
	private long toNodeFixedTime 	= -1;
	private long completedTime		= -1;
	private long removedTime		= -1;
	private long lastReceivedMilli 	= -1;
	private String cmdId			= "";
	private String carrierId		= "";
	private String frNodeId			= "";
	private String currentNodeId	= "";
	private String toGroupId		= "";
	private String toNodeId			= "";
	private CNV_EVENT event			= CNV_EVENT.UNKNOWN;
	private String reasonCd			= "";
	
	public CnvTask(String id, long cmdTime, String cmdId, String carrierId) {
		this.id			= id;
		this.cmdTime	= cmdTime;
		this.cmdId		= cmdId;
		this.carrierId	= carrierId;
	}
	
	public CnvTask(String id, long createTime) {
		this.id			= id;
		this.createTime	= createTime;
	}
	
	public static synchronized ReentrantLock getLock(String taskId) {
		ReentrantLock rlock = new ReentrantLock ();
		
		if (lockMap.get(taskId) == null) 
			lockMap.put(taskId,  new ReentrantLock(true));		
		try {
			
			rlock = lockMap.get(taskId);

			// 보안취약점 조치 - lock을 finally에서 해제하도록 수정
			if (!rlock.tryLock(50, TimeUnit.MILLISECONDS)) {
				// Couldn't get the lock. If the caller must not unlock in case of this.
				return null; 
			}
		} catch (InterruptedException e) {
			LoggerFactory.getLogger(CnvTask.class).error("Interupted",e);
		} finally {
			if(rlock != null) {
				rlock.unlock();
			}
		}
		return lockMap.get(taskId);
	}
	
	public static synchronized void unLock(String taskId){
		lockMap.get(taskId).unlock();
	}
	
	public String getId() {
		return id;
	}
	
	public void setId(String id) {
		this.id = id;
	}
	
	public long getFrNodeLocatedTime() {
		return frNodeLocatedTime;
	}
	
	public void setFrNodeLocatedTime(long frNodeLocatedTime) {
		this.frNodeLocatedTime = frNodeLocatedTime;
	}
	
	public long getToNodeFixedTime() {
		return toNodeFixedTime;
	}
	
	public void setToNodeFixedTime(long toNodeFixedTime) {
		this.toNodeFixedTime = toNodeFixedTime;
	}
	
	public long getLastReceivedMilli() {
		return lastReceivedMilli;
	}
	
	public void setLastReceivedMilli(long lastReceivedMilli) {
		this.lastReceivedMilli = lastReceivedMilli;
	}
	
	public String getCmdId() {
		return cmdId;
	}
	
	public void setCmdId(String cmdId) {
		this.cmdId = cmdId;
	}
	
	public String getCarrierId() {
		return carrierId;
	}
	
	public void setCarrierId(String carrierId) {
		this.carrierId = carrierId;
	}
	
	public String getFrNodeId() {
		return frNodeId;
	}
	
	public void setFrNodeId(String frNodeId) {
		this.frNodeId = frNodeId;
	}
	
	public String getCurrentNodeId() {
		return currentNodeId;
	}
	
	public void setCurrentNodeId(String currentNodeId) {
		this.currentNodeId = currentNodeId;
	}
	
	public String getToGroupId() {
		return toGroupId;
	}
	
	public void setToGroupId(String toGroupId) {
		this.toGroupId = toGroupId;
	}
	
	public String getToNodeId() {
		return toNodeId;
	}
	
	public void setToNodeId(String toNodeId) {
		this.toNodeId = toNodeId;
	}

	public String getReasonCd() {
		return reasonCd;
	}
	
	public void setReasonCd(String reasonCd) {
		this.reasonCd = reasonCd;
	}

	public long getCmdTime() {
		return cmdTime;
	}

	public void setCmdTime(long cmdTime) {
		this.cmdTime = cmdTime;
	}
	
	public CNV_EVENT getEvent() {
		return event;
	}

	public void setEvent(CNV_EVENT event) {
		this.event = event;
	}

	public long getSrcIdReadTime() {
		return srcIdReadTime;
	}

	public void setSrcIdReadTime(long srcIdReadTime) {
		this.srcIdReadTime = srcIdReadTime;
	}

	public long getInitiatedTime() {
		return initiatedTime;
	}

	public void setInitiatedTime(long initiatedTime) {
		this.initiatedTime = initiatedTime;
	}

	public long getDestIdReadTime() {
		return destIdReadTime;
	}

	public void setDestIdReadTime(long destIdReadTime) {
		this.destIdReadTime = destIdReadTime;
	}

	public long getCompletedTime() {
		return completedTime;
	}

	public void setCompletedTime(long completedTime) {
		this.completedTime = completedTime;
	}

	public long getRemovedTime() {
		return removedTime;
	}

	public void setRemovedTime(long removedTime) {
		this.removedTime = removedTime;
	}

	@Override
	public String toString() {
		return "CnvTask [id=" + id + "createTime=" + createTime + ", frNodeLocatedTime=" + frNodeLocatedTime + ", srcIdReadTime=" + srcIdReadTime
				+ ", cmdTime=" + cmdTime + ", initiatedTime=" + initiatedTime + ", destIdReadTime=" + destIdReadTime
				+ ", toNodeFixedTime=" + toNodeFixedTime + ", completedTime=" + completedTime + ", removedTime="
				+ removedTime + ", lastReceivedMilli=" + lastReceivedMilli + ", cmdId=" + cmdId + ", carrierId="
				+ carrierId + ", frNodeId=" + frNodeId + ", currentNodeId=" + currentNodeId + ", toGroupId=" + toGroupId
				+ ", toNodeId=" + toNodeId + ", event=" + event + ", reasonCd=" + reasonCd + "]";
	}

	public long getCreateTime() {
		return createTime;
	}

	public void setCreateTime(long createTime) {
		this.createTime = createTime;
	}	
}
