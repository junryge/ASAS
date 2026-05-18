package com.skhynix.smartatlas.data.raw;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

public class RawCnvZone{
	public String eqpNm 			= "";
	public int level 				= -1;
	public int posX 				= -1;
	public int posY 				= -1;
	public int nextZone 			= -1;
	public int prevZone 			= -1;
	public int zoneDrawCount 		= -1;
	public int zoneId 				= -1;
	public int physicalType 		= -1;
	public int refDirection 		= -1;
	public String displayName 		= "";
	public int currentNode 			= -1;
	public int prevNode 			= -1;
	public int logicalType 			= -1;
	public RawCnvLdAttr ldAttr 		= null;
	public RawCnvQsAttr qsAttr 		= null;
	public RawCnvLftAttr lftAttr 	= null;
	public boolean state 			= true;
	
	public RawCnvZone(
						String eqpNm, 
						int level, 
						int posX, 
						int posY, 
						int nextZone, 
						int prevZone, 
						int zoneDrawCount, 
						int zoneId,
						int physicalType, 
						int refDirection, 
						String displayName, 
						int currentNode, 
						int prevNode, 
						int logicalType,
						RawCnvLdAttr ldAttr, 
						RawCnvQsAttr qsAttr, 
						RawCnvLftAttr lftAttr
	) {
		super();
		this.eqpNm 			= eqpNm;
		this.level 			= level;
		this.posX 			= posX;
		this.posY 			= posY;
		this.nextZone 		= nextZone;
		this.prevZone 		= prevZone;
		this.zoneDrawCount 	= zoneDrawCount;
		this.zoneId 		= zoneId;
		this.physicalType 	= physicalType;
		this.refDirection 	= refDirection;
		this.displayName 	= displayName;
		this.currentNode 	= currentNode;
		this.prevNode 		= prevNode;
		this.logicalType 	= logicalType;
		this.ldAttr 		= ldAttr;
		this.qsAttr 		= qsAttr;
		this.lftAttr 		= lftAttr;
	}
	
	public class RawCnvLdAttr{
		public int included 			= -1;
		public int[] sensorReversZones 	= null;
		
		public RawCnvLdAttr(int included, int[] sensorReversZones) {
			super();
			
			this.included 			= included;
			this.sensorReversZones 	= sensorReversZones;
		}		
	}
	public class RawCnvQsAttr{
		public int included 		= -1;
		public int homeDirection 	= -1;
		public int isWayPoint 		= -1;
		public int[] north 			= null;
		public int[] south 			= null;
		public int[] east 			= null;
		public int[] west 			= null;
		
		public RawCnvQsAttr(
							int included, 
							int homeDirection, 
							int isWayPoint, 
							int[] north, 
							int[] south, 
							int[] east,
							int[] west
		) {
			super();
			this.included 		= included;
			this.homeDirection 	= homeDirection;
			this.isWayPoint 	= isWayPoint;
			this.north 			= north;
			this.south 			= south;
			this.east 			= east;
			this.west 			= west;
		}		
	}
	public class RawCnvLftAttr{
		public int inIncludeZoneId 	= -1;
		public int outIncludeZoneId = -1;
		public int homeLevel 		= -1;
		public int homingDirection 	= -1;
		public int homingClearLimit = -1;
		public List<Map<String,Integer>> levelZoneList = new ArrayList<Map<String,Integer>>();
		
		public RawCnvLftAttr(
								int inIncludeZoneId,
								int outIncludeZoneId, 
								int homeLevel, 
								int homingDirection,
								int homingClearLimit, 
								List<Map<String, Integer>> levelZoneList
		) {
			super();
		
			this.inIncludeZoneId 	= inIncludeZoneId;
			this.outIncludeZoneId 	= outIncludeZoneId;
			this.homeLevel 			= homeLevel;
			this.homingDirection 	= homingDirection;
			this.homingClearLimit 	= homingClearLimit;
			this.levelZoneList 		= levelZoneList;
		}		
	}
}