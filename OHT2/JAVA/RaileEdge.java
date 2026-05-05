public class RailEdge extends AbstractEdge {
    private final transient Logger logger = LoggerFactory.getLogger(getClass());
    private String branchJoinEdgeId = "";
    private ConcurrentLinkedQueue<String> stationIdList    = new ConcurrentLinkedQueue<>();
    private ConcurrentHashMap<String,Integer> vhlIdMap     = new ConcurrentHashMap<>();
    private boolean isAvailable                         = false;
    private double maxVelocity                             = -1; // 분속 단위
    private double velocity                             = -1; // 분속 단위
    private double lastVelocity                         = -1; // 분속 단위
    transient private long hisCnt                         = 0;
    private int loopId                                     = -1;
    private int hidId                                     = -1; // -1 means an unknown id.
    private String zcuId                                 = "";
    private final String facId;
    private String mcpName;
    private RAIL_DIRECTION railDir;
    private final int fromAddress;
    private final int toAddress;
    private List<String> portIdList    = new ArrayList<>();
    private boolean changedVelocity    = false;

    public boolean changed(RailEdge oe) {
        if (this.maxVelocity != oe.maxVelocity) {
            return true;
        }
       
        if (this.loopId != oe.loopId) {
            return true;
        }
       
        if (this.hidId != oe.hidId) {
            return true;
        }
       
        if (!this.zcuId.equals(oe.zcuId)) {
            return true;
        }
       
        if (!this.mcpName.equals(oe.mcpName)) {
            return true;
        }
       
        if (!this.branchJoinEdgeId.equals(oe.branchJoinEdgeId)) {
            return true;
        }
       
        if (!Util.isContentsEqualsCollection(this.stationIdList, oe.stationIdList)) {
            return true;
        }
       
        if (this.railDir != oe.railDir) {
            return true;
        }
       
        return super.changed(oe);
    }
   
    /**
     * A constructor to set the batchFlush with the initialization to other fields.
     */
    public RailEdge(
                    final String fabId,        // FAB ID
                    final String id,         // rail edge 의 ID
                    final String facId,
                    final String mcpName,
                    final String fromNodeId,
                    final String toNodeId,
                    final boolean ignoredBatchFlush,
                    final double length,
                    final boolean isUpdate,
                    final RAIL_DIRECTION railDir,
                    final int fromAddress,
                    final int toAddress
    ) {
        super(fabId, id, fromNodeId, toNodeId, EDGE_TYPE.RAILEDGE, length, isUpdate);

        this.railDir         = railDir;
        this.mcpName         = mcpName;
        this.facId            = facId;
        this.fromAddress    = fromAddress;
        this.toAddress        = toAddress;
    }

    @Override
    public long getCost(String carrierId) {
        if (velocity <= 0) {
            velocity = 1;
        }

        return (long)(length / (velocity * 1000 / 60 / 1000));    // 거리(mm) / 속도(m/min) / mm변환 / min변환 / ms변환
    }
   
    public long getVhlCountCost() {
        if (velocity <= 0) {
            velocity = 1;
        }
       
        long cost = (long)(length / (velocity * 1000 / 60 / 1000)); // 거리(mm) / 속도(m/min) / mm변환 / min변환 / ms변환

        //Idle Vhl 수량 * 3000, Active Vhl 수량 * 5000, 목적지Station 수량 * 5000 반영 필요.
        int idleVhlCnt     = 0;
        int workVhlCnt     = 0;
        int workDestCnt    = 0;
       
        for (String vhlId : this.getVhlIdMap().keySet()) {
            Vhl v = DataService.getDataSet().getVhlMap().get(vhlId);
           
            if (StringUtils.isNotEmpty(v.getCommandId())) {
                workVhlCnt++;
            } else {
                idleVhlCnt++;
            }
        }
       
        for (String stationId : getStationIdList()) {
            Station station = DataService.getDataSet().getStationMap().get(stationId);
           
            if (station != null) {
                if (StringUtils.isNotEmpty(station.getOutGoingCmdId())){
                    if (DataService.getDataSet().getCommandMap().containsKey(station.getOutGoingCmdId())) {
                        workDestCnt++;
                    } else {
                        station.setOutGoingCmdId("");
                    }
                }
               
                for (String commandId : station.getIncommingCmdIdMap().keySet()) {
                    if (DataService.getDataSet().getCommandMap().containsKey(commandId)) {
                        workDestCnt++;
                    } else {
                        station.removeIncommingCmdId(commandId);
                    }
                }
            } else {
                logger.warn("The Station Is Not Registered In File Or Server Memory ! (Station Id: {})", stationId);
            }
           
        }
       
        return cost
                + (idleVhlCnt * PredictionPara.getInstance().getIdleVhlCntPenalty())
                + (workVhlCnt * PredictionPara.getInstance().getWorkVhlCntPenalty())
                + (workDestCnt * PredictionPara.getInstance().getWorkDestCntPenalty());
    }
   
    public Map<VHL_STATE, Integer> getCurrentVhlStateMap(){
        Map<Vhl.VHL_STATE, Integer> vhlStateMap = new HashMap<>();
        try {
            for (String vhlId : vhlIdMap.keySet()) {
                Vhl v = DataService.getDataSet().getVhlMap().get(vhlId);
               
                vhlStateMap.compute(v.getState(), (key,value) -> value == null? 1 : value + 1);
            }
        } catch (Exception e) {
            //    ...
        }
       
        return vhlStateMap;
    }
   
    public Map<VHL_DET_STATE, Integer> getCurrentVhlDetStateMap(){
        Map<Vhl.VHL_DET_STATE, Integer> vhlDetStateMap = new HashMap<>();
       
        try {
            for (String vhlId : vhlIdMap.keySet()) {
                Vhl v = DataService.getDataSet().getVhlMap().get(vhlId);
               
                vhlDetStateMap.compute(v.getDetailState(), (key,value) -> value == null ? 1 : value + 1);
            }
        } catch (Exception e) {
            //    ...
        }
       
        return vhlDetStateMap;
    }
   
    public Map<VHL_CYCLE, Integer> getCurrentVhlCycleMap(){
        Map<VHL_CYCLE, Integer> vhlCycleMap = new HashMap<>();
       
        try {
            for (String vhlId : vhlIdMap.keySet()) {
                Vhl v = DataService.getDataSet().getVhlMap().get(vhlId);
       
                vhlCycleMap.compute(v.getVhlCycle(), (key,value) -> value == null ? 1 : value + 1);
            }
        } catch (Exception e) {
            //    ...
        }
       
        return vhlCycleMap;
    }
   
    public Map<RUN_CYCLE, Integer> getCurrentVhlRunCycleMap(){
        Map<RUN_CYCLE, Integer> vhlRunCycleMap = new HashMap<>();
       
        try {
            for (String vhlId : vhlIdMap.keySet()) {
                Vhl v = DataService.getDataSet().getVhlMap().get(vhlId);
               
                vhlRunCycleMap.compute(v.getRunCycle(), (key,value) -> value == null ? 1 : value + 1);
            }
        } catch (Exception e) {
            //    ...
        }
        return vhlRunCycleMap;
    }
   
    public long getFutureCost(String carrierId, long after) {
        return DataService.getDataSet().getLongEdgeMap().get(longEdgeId).getFutureCost(carrierId, after);
    }
   
    public boolean isToJunctionEdge() {
        RailNode toNode = (RailNode)DataService.getDataSet().getNodeMap().get(this.toNodeId);
   
        return toNode.isRailJunction();
    }

    public ConcurrentLinkedQueue<String> getStationIdList() {
        return stationIdList;
    }

    public void setStationIdList(ConcurrentLinkedQueue<String> stationIdList) {
        this.stationIdList = stationIdList;
    }

    public List<String> getPortIdList() {
        return portIdList;
    }

    public void setPortIdList(List<String> portIdList) {
        this.portIdList = portIdList;
    }

    public ConcurrentHashMap<String,Integer> getVhlIdMap() {
        if (vhlIdMap == null) {
            this.vhlIdMap = new ConcurrentHashMap<>();
        }
       
        return vhlIdMap;
    }
   
    public void addVhlId(String vhlId) {
        if (vhlIdMap == null) {
            this.vhlIdMap = new ConcurrentHashMap<>();
        }
       
        vhlIdMap.put(vhlId, 0);
    }
   
    public void removeVhlId(String vhlId) {
        if (this.vhlIdMap == null) {
            this.vhlIdMap = new ConcurrentHashMap<>();
        }
       
        this.vhlIdMap.remove(vhlId);
    }

    public void setVhlIdMap(ConcurrentHashMap<String, Integer> vhlIdMap) {
        this.vhlIdMap = vhlIdMap;
    }    

    public boolean isAvailable() {
        return isAvailable;
    }

    public void setAvailable(boolean isAvailable) {
        this.isAvailable = isAvailable;
    }

    public double getMaxVelocity() {
        return maxVelocity;
    }

    public void setMaxVelocity(double maxVelocity) {
        this.maxVelocity = maxVelocity;
    }

    public double getVelocity() {
        return velocity;
    }

    public void setVelocity(double velocity) {
        this.velocity = velocity;
    }
   
    public void addVelocity(double velocity) {
        if (Double.isNaN(velocity) || Double.isInfinite(velocity)) {
            return;        
        }
       
        if (velocity < 1.5) {
            velocity = 1.5;
        } else if(getMaxVelocity() < velocity) {
            velocity = getMaxVelocity();
        }
       
        setLastVelocity(this.velocity);
       
        if (hisCnt > 0){            
            this.velocity = (this.velocity * PredictionPara.getInstance().getLastHisWeight())+(velocity * (1.0 - PredictionPara.getInstance().getLastHisWeight()));
        } else {
            this.velocity = velocity;
        }

        this.changedVelocity = true;
    }
   
    public void addHistory() {
        this.hisCnt++;
    }

    public int getLoopId() {
        return loopId;
    }

    public void setLoopId(int loopId) {
        this.loopId = loopId;
    }

    /**
     * Returns a hid id for this edge.
     * @return int
     */
    public int getHIDId() {
        return this.hidId;
    }
   
    /**
     * Sets a hid
     * @param hidId an id to set.
     */
    public void setHIDId(final int hidId) {
        this.hidId = hidId;
    }

    /**
     * Returns a ZCU id for this edge.
     * @return String
     */
    public String getZCUId() {
        return this.zcuId;
    }
   
    /**
     * Sets a ZCU id
     * @param zcuId an id to set.
     */
    public void setZCUId(final String zcuId) {
        this.zcuId = zcuId;
    }

    @Override
    public int getFutureTransCount(String carrierId, long after) {
        LongEdge longEdge = DataService.getDataSet().getLongEdgeMap().get(longEdgeId);

        return longEdge.getFutureTransCount(carrierId, after);
    }
   
    public int getFutureDpstCount(String carrierId, long after) {
        LongEdge longEdge = DataService.getDataSet().getLongEdgeMap().get(longEdgeId);
       
        return longEdge.getFutureDpstCount(carrierId, after);
    }

    public int getFutureAcqCount(String carrierId, long after) {
        LongEdge longEdge = DataService.getDataSet().getLongEdgeMap().get(longEdgeId);
       
        return longEdge.getFutureAcqCount(carrierId, after);
    }
   
    public long getHisCnt() {
        return this.hisCnt;
    }

    public double getLastVelocity() {
        return lastVelocity;
    }

    public void setLastVelocity(double lastVelocity) {
        this.lastVelocity = lastVelocity;
    }

    @Override
    public boolean isAvailable(PROCESS_TYPE carrierType) {
        return isAvailable && (loopId < 0 || (loopId > 0 && (carrierType == PROCESS_TYPE.ALL || carrierType == PROCESS_TYPE.POD)));
    }

    public String getMcpName() {
        return mcpName;
    }

    public void setMcpName(String mcpName) {
        this.mcpName = mcpName;
    }

    public String getBranchJoinEdgeId() {
        return branchJoinEdgeId;
    }

    public void setBranchJoinEdgeId(String branchJoinEdgeId) {
        this.branchJoinEdgeId = branchJoinEdgeId;
    }    
   
    public enum RAIL_DIRECTION {NONE, LEFT, RIGHT}

    public RAIL_DIRECTION getRailDir() {
        return railDir;
    }

    public void setRailDir(RAIL_DIRECTION railDir) {
        this.railDir = railDir;
    }

    public float getDensity() {
        float vhlLengthSum, vhlLength;

        if (fabId.startsWith("M14")) {
            vhlLength = 784 + 300;
        } else if (fabId.startsWith("M16")) {
            vhlLength = 943 + 300;
        } else {
            vhlLength = 784 + 300;
        }
       
        float railLength = (float)length - ((float)length % vhlLength);
       
        if (railLength <= vhlLength) {
            railLength = vhlLength;
        }
       
        vhlLengthSum = vhlLength * vhlIdMap.size();        
       
        float returnValue = vhlLengthSum / railLength * 100f;
       
        return Math.min(returnValue, 100f);
    }

    public void setHisCnt(long hisCnt) {
        this.hisCnt = hisCnt;
    }
   
    public String getFacId() {
        return facId;
    }
   
    public int getFromAddress () {
        return fromAddress;
    }
   
    public int getToAddress () {
        return toAddress;
    }
   
    public String getAddress () {
        return fromAddress + ":" + toAddress;
    }

    // 속도 변화 감지 ---> 초기화 후 메세지를 통한 변화 여부 (초기값 배제용)
    public boolean isChangedVelocity() {
        return changedVelocity;
    }
}