package com.skhynix.smartatlas.data.eq;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashSet;
import java.util.TimeZone;

import com.skhynix.smartatlas.data.Carrier.PROCESS_TYPE;

public class AmpUnit extends Eqp {
	private String kind;				// 0: 메시지타입
//	private EQP_TYPE eqpType;		// 1: EqpType
//	private String eqpId;       	// 2: EqpID
    private String unitId;	 		// 3: UnitID, 설비에서 자체적으로 관리되는 UNIT ID (CNV : UNIT ID, AGV : CAR ID, OHT : VEHICLE ID)
    private String hostId;			// 4: HostID, HOST에서 관리되는 UNIT ID (없는 경우 공백) (CNV : UNIT ID, AGV : CAR ID, OHT : VEHICLE ID)
    private String status;			// 5: 상태	(1 ： RUN,2 ： STOP,3 ： ERROR,4 : PM)
    private String carrierDetect;	// 6: 0:없음, 1:있음
    private String carrierDetect2;	// 7: 0 : 없음 (UNIT CAPA가 2개인 경우 사용. 현재 AGV 해당), 1 : 있음
    private String errorCode;		// 8: alarm코드
    private String errorName;		// 9: alarm명
    private String address;			// 10: 현재위치    
    private String nextAddress; 	// 11: 다음이동위치
    private String destAddress;		// 12: 최종도착위치
    private String carrierId;		// 13: Carrier ID 
    private String carrierId2;		// 14: Carrier ID2(AGV일 경우 한 호기에 2개의 CARRIER가 존재할 경우 사용)
    private String cycle; 			// 15: 실행 Cycle (CNV : 해당 없음 | AGV, OHT : 3: Load, 5: Unload, 나머지 : 이동중) 
    private String bufferZoneReady;	// 16: 버퍼대기여부 (0 : BUFFER ZONE 대기 CARRIER 아님, 1 : BUFFER ZONE 대기 CARRIER)
    private String zoneId;   		// 17: Zone ID
//  private String column18; 		// 18:
//  private String column19;		// 19:
    private String createdAt;		// 생성일시

	public AmpUnit(
		String fabId, 
		String id, 
		String name,
		boolean isAvailable, 
		boolean isUpdate,
		String mcsBayNm
	) {
		super(fabId, id, name, EQP_TYPE.AGV, new HashSet<PROCESS_TYPE>(), null, isAvailable, isUpdate, mcsBayNm);
		
		// 1. 현재 날짜 객체 생성
        Date now = new Date();
        // 2. 포맷 설정 (yyyy-MM-dd HH:mm:ss.SSS)
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");        
        // 3. UTC 시간대 설정
        //sdf.setTimeZone(TimeZone.getTimeZone("UTC"));
        // 4. 포맷팅 적용
        this.createdAt = sdf.format(now);
	}

	public String getKind() {
        return kind;
    }
    public void setKind(String kind) {
        this.kind = kind;
    }
	
    public String getUnitId() {
        return unitId;
    }
    public void setUnitId(String unitId) {
        this.unitId = unitId;
    }
    
    public String getHostId() {
        return hostId;
    }
    public void setHostId(String hostId) {
        this.hostId = hostId;
    }
    
    public String getStatus() {
        return status;
    }
    public void setStatus(String status) {
        this.status = status;
    }
    
    public String getCarrierDetect() {
        return carrierDetect;
    }
    public void setCarrierDetect(String carrierDetect) {
        this.carrierDetect = carrierDetect;
    }
    
    public String getCarrierDetect2() {
        return carrierDetect2;
    }
    public void setCarrierDetect2(String carrierDetect2) {
        this.carrierDetect2 = carrierDetect2;
    }
    
    public String getErrorCode() {
        return errorCode;
    }
    public void setErrorCode(String errorCode) {
        this.errorCode = errorCode;
    }
    
    public String getErrorName() {
        return errorName;
    }
    public void setErrorName(String errorName) {
        this.errorName = errorName;
    }
    
    public String getAddress() {
        return address;
    }
    public void setAddress(String address) {
        this.address = address;
    }    

    public String getNextAddress() {
        return nextAddress;
    }
    public void setNextAddress(String nextAddress) {
        this.nextAddress = nextAddress;
    }
    
    public String getDestAddress() {
        return destAddress;
    }
    public void setDestAddress(String destAddress) {
        this.destAddress = destAddress;
    }
    
    public String getCarrierId() {
        return carrierId;
    }
    public void setCarrierId(String carrierId) {
        this.carrierId = carrierId;
    }
    
    public String getCarrierId2() {
        return carrierId2;
    }
    public void setCarrierId2(String carrierId2) {
        this.carrierId2 = carrierId2;
    }
    
    public String getCycle() {
        return cycle;
    }
    public void setCycle(String cycle) {
        this.cycle = cycle;
    }
    
    public String getBufferZoneReady() {
        return bufferZoneReady;
    }
    public void setBufferZoneReady(String bufferZoneReady) {
        this.bufferZoneReady = bufferZoneReady;
    }
    
    public String getZoneId() {
        return zoneId;
    }
    public void setZoneId(String zoneId) {
        this.zoneId = zoneId;
    }
    
    public String getCreatedAt() {
        return createdAt;
    }
}
