public class Vhl implements CarrierContainable, CarrierTransportable {
    private final Logger logger = LoggerFactory.getLogger(this.getClass());
    transient private ReentrantLock lock = new ReentrantLock(true);
    transient private AtomicLong lastMessageSequence = new AtomicLong(0);
    private String fabId;
    private String id;
    private String name;
    private String mcpName;
    private String eqpId;
    private int type;
    private String commandId = "";
    private String carrierId = "";
    private final VhlUdpState udpState;
    private VhlUdpState lastUdpState = null;
    transient private boolean isUpdate;
//    private boolean batchFlush = false;

    public Vhl(
            String id,
            String name,
            String mcpName,
            String fabId,
            String eqpId,
            int type,
            boolean isUpdate
    ) {
        super();

        this.id         = id;
        this.name         = name;
        this.mcpName     = mcpName;
        this.eqpId         = eqpId;
        this.fabId         = fabId;
        this.type         = type;
        this.udpState     = new VhlUdpState(this.id);
        this.isUpdate     = isUpdate;

        // 보안 취약점으로 인해 Math.random() 대신 SecureRandom.class 를 사용
        SecureRandom rnd = new SecureRandom();

        rnd.setSeed(new Date().getTime());

        try {
            lastUdpState = udpState.clone();
        } catch (CloneNotSupportedException e) {
            logger.error("... vhl state[=updState] clone failed", e);
        }
    }

    public void copyCurrentVhlUdpStateToLast() {
        try {
            lastUdpState = udpState.clone();
        } catch (CloneNotSupportedException e) {
            logger.error("... vhl state[=updState] clone failed", e);
        }
    }

//    public void flush() {
//        this.batchFlush = false;
//    }

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public int getType() {
        return type;
    }

    public void setType(int type) {
        this.type = type;
    }

    public VHL_STATE getState() {
        return udpState.state;
    }

    public void setState(VHL_STATE state) {
        this.udpState.state = state;
    }

    public void setFull(boolean isFull) {

        this.udpState.isFull = isFull;
    }

    public void setErrorCode(String errorCode) {
        this.udpState.errorCode = errorCode;
    }

    public void setOnline(boolean isOnline) {
        this.udpState.isOnline = isOnline;
    }

    public String getRailNodeId() {
        return udpState.railNodeId;
    }

    public void setRailNodeId(String railNodeId) {
        this.udpState.railNodeId = railNodeId;
    }

    public void setDistance(double distance) {
        this.udpState.distance = distance;
    }

    public void setNextRailNodeId(String nextRailNodeId) {
        this.udpState.nextRailNodeId = nextRailNodeId;
    }

    public void setNextAddress (int address) {
        this.udpState.nextAddress = address;
    }

    public Integer getNextAddress () {
        return udpState.nextAddress;
    }

    public void setCurrentAddress (int address) {
        this.udpState.currentAddress = address;
    }

    public Integer getCurrentAddress () {
        return udpState.currentAddress;
    }

    public String getRailEdgeId() {
        return udpState.railEdgeId;
    }

    public void setRailEdgeId(String railEdgeId) {
        this.udpState.railEdgeId = railEdgeId;
    }

    public RUN_CYCLE getRunCycle() {
        return udpState.runCycle;
    }

    public void setRunCycle(RUN_CYCLE runCycle) {
        this.udpState.runCycle = runCycle;
    }

    public VHL_CYCLE getVhlCycle() {
        return udpState.vhlCycle;
    }

    public void setVhlCycle(VHL_CYCLE vhlCycle) {
        this.udpState.vhlCycle = vhlCycle;
    }

    public String getCarrierId() {
        return carrierId;
    }

    public void setCarrierId(String carrierId) {
        this.carrierId = carrierId;
    }

    public void setUdpCarrierId(String udpCarrierId) {
        this.udpState.udpCarrierId = udpCarrierId;
    }

    public void setDestStationId(String destStationId) {
        this.udpState.destStationId = destStationId;
    }

    public void setReceivedTime(long receivedTime) {
        this.udpState.receivedTime = receivedTime;
    }

    public String getCommandId() {
        return commandId;
    }

    public void setCommandId(String commandId) {
        this.commandId = commandId;

        LoggerFactory.getLogger(getClass()).debug("{} commandId {} set completed", this.id, this.commandId);
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public enum VHL_STATE {
        RUN("1"),            // 운전 중
        STOP("2"),            // 정지 중
        ABNORMAL("3"),        // 상태 이상
        MANUAL("4"),        // 수동 조치
        REMOVING("5"),        // 분리 및 제거 중
        OBS_BZ_STOP("6"),    // OBS-STOP/BZ-STOP
        JAM("7"),            // 정체
        HT_STOP("8"),        // HT-STOP
        E84_TIMEOUT("9");    // E84 time out

        private final String code;

        VHL_STATE(String code){
            this.code = code;
        }

        public String code() {
            return this.code;
        }

        public static VHL_STATE getValue(String numberString) {
            for (VHL_STATE value : values()) {
                if (value.code.equals(numberString)) {
                    return value;
                }
            }

            return REMOVING;
        }
    }

    // 작업 상태 상세 정보
    public enum VHL_DET_STATE{
        NONE("0"),                    // 작업 없음
        WAIT("1"),                    // 대기 중
        STAGE_WAIT("2"),            // stage 대기 중
        STANDBY_WAIT("3"),            // standby 대기 중
        DEPOSIT_SIG_WAIT("4"),        // 반송 도매 허가 없이 대기 중
        ACQ_WAIT("5"),                // carrier 회수 대기 중
        MAP_WAIT("6"),                // MAP 배달 대기 중
        MOVING("101"),                // 이동 중
        PARKING_UTS_MOVING("102"),    // parking UTS 주행 중
        STAGE_MOVING("103"),        // stage 이동
        STANDBY_MOVING("104"),        // standby 이동
        BALANCE_MOVING("105"),        // balance 에 의한 이동
        PARKING_MOVING("106");        // parking 에 의한 이동

        private final String code;

        VHL_DET_STATE(String code){
            this.code = code;
        }

        public String code(){
            return this.code;
        }

        public static VHL_DET_STATE getValue(String numberString) {
            for (VHL_DET_STATE value : values()) {
                if (value.code.equals(numberString)) {
                    return value;
                }
            }

            return NONE;
        }
    }

    // 실행 주기 및 사이클
    public enum RUN_CYCLE{
        NONE("0"),                    // 사이클 없음
        POSITION_DETECT("1"),        // 위치 확인 주기 동안
        MOVING("2"),                // 이동 주기 동안
        ACQUIRE("3"),                // 구원 주기 동안
        DEPOSIT("4"),                // 도매 사이클 중
        SAMPLING("5"),                // 샘플링 주기 동안
        FLOOR_TRANS("9"),            // 층간 이동 주기 동안
        WHEELDRIVE("21"),            // 바퀴 주행 주기 동안
        MANUAL_CONTROL("22"),        // 수동 조작 중
        DRIVE_TEACHING("23"),        // 주행 학습 사이클 중
        TRANS_TEACHING("24"),        // 이재 부 학습 중 (교육 중)
        TEST_1("25"),                // 테스트 주기 동안 (패턴1)
        TEST_2("26"),                // 테스트 주기 동안 (패턴2)
        TEST_3("27"),                // 테스트 주기 동안 (패턴3)
        BUILDING_TRANS("2E"),        // 동 간 이동 주기 동안
        EVACUATION("2F");            // 대피 이동 주기 동안

        private final String code;

        RUN_CYCLE(String code){
            this.code = code;
        }

        public String code() {
            return this.code;
        }

        public static RUN_CYCLE getValue(String numberString) {
            for (RUN_CYCLE value : values()) {
                if(value.code.equals(numberString)) {
                    return value;
                }
            }

            return NONE;
        }
    }

    // vehicle 실행 주기 및 사이클
    public enum VHL_CYCLE{
        NONE("0"),                // 실행 사이클 없음
        MOVING("1"),            // 이동 중
        ACQUIRE_MOVING("2"),    // 구원 이동
        ACQUIRING("3"),        // 구원 이송 중
        DEPOSIT_MOVING("4"),    // 도매 이동
        DEPOSITING("5"),        // 도매 이송 중
        MAINT_MOVING("6"),        // 유지 이동 중 (=샘플링을 위해 유지 스테이션으로 이동 중)
        WAITING("7"),            // 대체 지시 대기
        INPUT("8");            // 투입 중

        private final String code;

        VHL_CYCLE (String code){
            this.code = code;
        }

        public String code() {
            return this.code;
        }

        public static VHL_CYCLE getValue(String numberString) {
            for (VHL_CYCLE value : values()) {
                if (value.code.equals(numberString)) {
                    return value;
                }
            }

            return NONE;
        }
    }

    @Override
    public void addCarrierId(String carrierId) {
        this.setCarrierId(carrierId);
    }

    @Override
    public void removeCarrierId(String carrierId) {
        this.setCarrierId("");
    }

    @Override
    public String getEqpId() {
        return this.eqpId;
    }

    public void setEqpId(String eqpId) {
        this.eqpId = eqpId;
    }

    @Override
    public void addCommandId(String commandId) {
        this.setCommandId(commandId);
    }

    @Override
    public void removeCommandId(String commandId) {
        if (commandId.equals(this.commandId)) {
            this.setCommandId("");
        }
    }

    public void setEmStatus(byte emStatus) {
        this.udpState.emStatus = emStatus;
    }

    public void setGroupId(String groupId) {
        this.udpState.groupId = groupId;
    }

    public void setSourcePortId(String sourcePortId) {
        this.udpState.sourcePortId = sourcePortId;
    }

    public void setDestPortId(String destPortId) {
        this.udpState.destPortId = destPortId;
    }

    public int getPriority() {
        return udpState.priority;
    }

    public void setPriority(int priority) {
        this.udpState.priority = priority;
    }

    public VHL_DET_STATE getDetailState() {
        return udpState.detailState;
    }

    public void setDetailState(VHL_DET_STATE detailState) {
        this.udpState.detailState = detailState;
    }

    public void setRunDistance(long runDistance) {
        this.udpState.runDistance = runDistance;
    }

    public double getDistance() {
        return udpState.distance;
    }

    public long getReceivedTime() {
        return udpState.receivedTime;
    }

    public String getCrossPointId() {
        return udpState.crossPointId;
    }

    public void setCrossPointId(String crossPointId) {
        this.udpState.crossPointId = crossPointId;
    }

    public static class VhlUdpState implements Cloneable{
        public String vehicleId;
        public String udpCarrierId             = "";
        public VHL_STATE state                 = VHL_STATE.REMOVING;
        public boolean isFull                 = false;
        public String errorCode             = "";
        public boolean isOnline             = false;
        public String railNodeId             = "";
        public double distance                 = -1;
        public String nextRailNodeId         = "";
        public String railEdgeId             = "";
        public RUN_CYCLE runCycle             = RUN_CYCLE.NONE;
        public VHL_CYCLE vhlCycle             = VHL_CYCLE.NONE;
        public String destStationId         = "";
        public long receivedTime             = -1;
        public byte emStatus                 = Util.binaryStringToByte("00000000");
        public String groupId                 = "";
        public String sourcePortId             = "";
        public String destPortId             = "";
        public int priority                 = 50;
        public VHL_DET_STATE detailState     = VHL_DET_STATE.NONE;
        public long runDistance             = 0;
        public int hidId                    = -1;    // 위치했던 HID 값 기억
        public int currentAddress = -1;
        public int nextAddress = -1;
        public String crossPointId = "";

        public VhlUdpState(String vhlId) {
            this.vehicleId = vhlId;
        }

        @Override
        public VhlUdpState clone() throws CloneNotSupportedException {
            return (VhlUdpState)super.clone();
        }
    }

    public VhlUdpState getLastUdpState() {
        return lastUdpState;
    }

    public ReentrantLock getLock() {
        if (this.lock == null) {
            this.lock = new ReentrantLock(true);
        }

        try {
            if (!this.lock.tryLock(50, TimeUnit.MILLISECONDS)) {
                // Couldn't get the lock. If the caller must not unlock in case of this.
                return null;
            }
        } catch (InterruptedException e) {
            LoggerFactory.getLogger(getClass()).error("Interupted", e);
        }

        return lock;
    }

    public String getFabId() {
        return fabId;
    }

    public void setFabId(String fabId) {
        this.fabId = fabId;
    }

    @Override
    public String[] getCarrierIds() {
        if (StringUtils.isNotEmpty(this.carrierId)) {
            return new String[] {this.carrierId};
        }

        return null;
    }

    public boolean isUpdate() {
        return isUpdate;
    }

    public void setUpdate(boolean isUpdate) {
        this.isUpdate = isUpdate;
    }

    public String getMcpName() {
        return mcpName;
    }

    public void setMcpName(String mcpName) {
        this.mcpName = mcpName;
    }

    public AtomicLong getLastMessageSequenceNo() {
        if (lastMessageSequence == null) {
            lastMessageSequence = new AtomicLong(0);
        }

        return lastMessageSequence;
    }

    public int getHidId () {
        return udpState.hidId;
    }

    public void setHidId (int hidId) {
        this.udpState.hidId = hidId;
    }
}