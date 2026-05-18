package com.skhynix.smartatlas.data.raw;

import java.util.ArrayList;
import java.util.List;

public class RawBz {
	private String code = "";
	private String id = "";
	private List<ObzQueue> obzQueueList = new ArrayList<ObzQueue>();
	private HidInfo hidInfo = null;
	private List<Fd> fdList = new ArrayList<RawBz.Fd>();
	private List<StopPoint> stopPointList = new ArrayList<RawBz.StopPoint>();
	private int schedulerId = 1;
	private int territoryNo = 1;
	public static final String BZ_CODE = "53";
	public static final String HID_CODE = "92";
	public static final String AD_CODE = "91";
	public static final String FD_CODE = "91";
	public static final String FFU_CODE = "93";
	public static final String HID_UNIT_CODE = "94";
	public static final String OHT_LIFTER_CODE = "57";
	public static final String CDP_CODE = "9A";
	public static final String GRID_HID_CODE = "9D";
		
	public RawBz(String code, String id, List<ObzQueue> obzQueueList, HidInfo hidInfo, List<StopPoint> stopPointList, List<Fd> fdList,
			int schedulerId, int territoryNo) {
		super();
		this.code = code;
		this.id = id;
		this.obzQueueList = obzQueueList;
		this.hidInfo = hidInfo;
		this.stopPointList = stopPointList;
		this.schedulerId = schedulerId;
		this.territoryNo = territoryNo;
		this.fdList = fdList;
	}
	public RawBz() {
		
	}

	public class ObzQueue{
		int no = 0;
		int mcpZoneNo = 0;
		int[] stopAddresses;
		
		public ObzQueue(int no, int mcpZoneNo, int[] stopAddresses) {
			super();
			this.no = no;
			this.mcpZoneNo = mcpZoneNo;
			this.stopAddresses = stopAddresses;
		}
		public int getNo() {
			return no;
		}
		public void setNo(int no) {
			this.no = no;
		}
		public int getMcpZoneNo() {
			return mcpZoneNo;
		}
		public void setMcpZoneNo(int mcpZoneNo) {
			this.mcpZoneNo = mcpZoneNo;
		}
		public int[] getStopAddresses() {
			return stopAddresses;
		}
		public void setStopAddresses(int[] stopAddresses) {
			this.stopAddresses = stopAddresses;
		}		
	}
	
	public class StopPoint{
		int stopAddr = 0;
		byte passageDirection = 0x00;
		public StopPoint(int stopAddr, byte passageDirection) {
			super();
			this.stopAddr = stopAddr;
			this.passageDirection = passageDirection;
		}
		public int getStopAddr() {
			return stopAddr;
		}
		public void setStopAddr(int stopAddr) {
			this.stopAddr = stopAddr;
		}
		public byte getPassageDirection() {
			return passageDirection;
		}
		public void setPassageDirection(byte passageDirection) {
			this.passageDirection = passageDirection;
		}		
	}
	
	public class HidInfo{
		String machineId = "";
		int hid1or2 = 1;
		int mcpZoneNo = 0;
		String machineTypeCode = "";
		String extendedMachineId = "";
		String hidSynchUnit = "";
		
		public HidInfo(String machineId, int hid1or2, int mcpZoneNo, String machineTypeCode, String extendedMachineId,
				String hidSynchUnit) {
			super();
			this.machineId = machineId;
			this.hid1or2 = hid1or2;
			this.mcpZoneNo = mcpZoneNo;
			this.machineTypeCode = machineTypeCode;
			this.extendedMachineId = extendedMachineId;
			this.hidSynchUnit = hidSynchUnit;
		}
		
		public String getMachineId() {
			return machineId;
		}
		public void setMachineId(String machineId) {
			this.machineId = machineId;
		}
		public int getHid1or2() {
			return hid1or2;
		}
		public void setHid1or2(int hid1or2) {
			this.hid1or2 = hid1or2;
		}
		public int getMcpZoneNo() {
			return mcpZoneNo;
		}
		public void setMcpZoneNo(int mcpZoneNo) {
			this.mcpZoneNo = mcpZoneNo;
		}
		public String getMachineTypeCode() {
			return machineTypeCode;
		}
		public void setMachineTypeCode(String machineTypeCode) {
			this.machineTypeCode = machineTypeCode;
		}
		public String getExtendedMachineId() {
			return extendedMachineId;
		}
		public void setExtendedMachineId(String extendedMachineId) {
			this.extendedMachineId = extendedMachineId;
		}
		public String getHidSynchUnit() {
			return hidSynchUnit;
		}
		public void setHidSynchUnit(String hidSynchUnit) {
			this.hidSynchUnit = hidSynchUnit;
		}
		
	}
	
	public class Fd{
		private String machineId = "";
		private int fd1or2 = 1;
		private int laneStartPoint = 0;
		private int laneEndPoint = 0;
		public Fd(String machineId, int fd1or2, int laneStartPoint, int laneEndPoint) {
			super();
			this.machineId = machineId;
			this.fd1or2 = fd1or2;
			this.laneStartPoint = laneStartPoint;
			this.laneEndPoint = laneEndPoint;
		}
		public String getMachineId() {
			return machineId;
		}
		public void setMachineId(String machineId) {
			this.machineId = machineId;
		}
		public int getFd1or2() {
			return fd1or2;
		}
		public void setFd1or2(int fd1or2) {
			this.fd1or2 = fd1or2;
		}
		public int getLaneStartPoint() {
			return laneStartPoint;
		}
		public void setLaneStartPoint(int laneStartPoint) {
			this.laneStartPoint = laneStartPoint;
		}
		public int getLaneEndPoint() {
			return laneEndPoint;
		}
		public void setLaneEndPoint(int laneEndPoint) {
			this.laneEndPoint = laneEndPoint;
		}
		
	}

	public String getCode() {
		return code;
	}

	public void setCode(String code) {
		this.code = code;
	}

	public String getId() {
		return id;
	}

	public void setId(String id) {
		this.id = id;
	}

	public List<ObzQueue> getObzQueueList() {
		return obzQueueList;
	}

	public void setObzQueueList(List<ObzQueue> obzQueueList) {
		this.obzQueueList = obzQueueList;
	}

	public HidInfo getHidInfo() {
		return hidInfo;
	}

	public void setHidInfo(HidInfo hidInfo) {
		this.hidInfo = hidInfo;
	}

	public List<StopPoint> getStopPointList() {
		return stopPointList;
	}

	public void setStopPointList(List<StopPoint> stopPointList) {
		this.stopPointList = stopPointList;
	}

	public int getSchedulerId() {
		return schedulerId;
	}

	public void setSchedulerId(int schedulerId) {
		this.schedulerId = schedulerId;
	}

	public int getTerritoryNo() {
		return territoryNo;
	}

	public void setTerritoryNo(int territoryNo) {
		this.territoryNo = territoryNo;
	}
	public List<Fd> getFdList() {
		return fdList;
	}
	public void setFdList(List<Fd> fdList) {
		this.fdList = fdList;
	}
}
