package com.skhynix.smartatlas.data.raw;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;

import org.apache.commons.lang3.StringUtils;
import org.dom4j.Document;
import org.dom4j.Element;
import org.dom4j.Node;
import org.dom4j.io.SAXReader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.data.raw.RawBz.Fd;
import com.skhynix.smartatlas.data.raw.RawBz.HidInfo;
import com.skhynix.smartatlas.data.raw.RawBz.ObzQueue;
import com.skhynix.smartatlas.data.raw.RawBz.StopPoint;
import com.skhynix.smartatlas.data.raw.RawStation.INV_MGT_CATEGORY;
import com.skhynix.smartatlas.data.raw.RawStation.PORT_LOCATION;
import com.skhynix.smartatlas.data.raw.RawStation.STATION_LOCATION;
import com.skhynix.smartatlas.data.raw.RawStation.STATION_TYPE;
import com.skhynix.smartatlas.util.Util;

public class Mcp75Config {
	static private final Logger logger 													= LoggerFactory.getLogger(Mcp75Config.class);
	
	private double pulseRate;
	private String vhlSpeedType;
	private double slidePortDist 														= 10.0; //pixel
	private ConcurrentMap<Integer,RawPoint> rawPointMap 								= new ConcurrentHashMap<>();
	private ConcurrentMap<Integer,RawStation> rawStationMap 							= new ConcurrentHashMap<>();
	private ConcurrentMap<String, RawVhl> rawVhlMap 									= new ConcurrentHashMap<>();
	private ConcurrentMap<Integer, RawVhlType> rawVhlTypeMap 							= new ConcurrentHashMap<>();
	private ConcurrentMap<String, ConcurrentMap<Integer, RawVhlSpeed>> rawVhlSpeedMap 	= new ConcurrentHashMap<>();
	private ConcurrentMap<String, RawArea> rawAreaMap 									= new ConcurrentHashMap<>();
	private ConcurrentMap<String, RawBay> rawBayMap 									= new ConcurrentHashMap<>();
	private ConcurrentMap<String, int[]> bayNameIdMap 									= new ConcurrentHashMap<>();
	private ConcurrentMap<String, RawJunction> rawJunctionMap 							= new ConcurrentHashMap<>();
	private ConcurrentMap<String, RawHid> rawHidMap 									= new ConcurrentHashMap<>();
	private ConcurrentMap<String, RawBz> rawBzMap 										= new ConcurrentHashMap<>();
	private ConcurrentMap<String, RawLoop> rawLoopMap 									= new ConcurrentHashMap<>();
	private ConcurrentMap<String, RawRouteInfo> rawRouteInfoMap 						= new ConcurrentHashMap<>();
	private ConcurrentMap<String, RawLabel> rawLabelMap 								= new ConcurrentHashMap<>();
	private Set<String> rawRailCutSet = ConcurrentHashMap.newKeySet();

	public Mcp75Config(String mcpConfigDir, String fabId, String mcpName) {
		File file;
		InputStream inputStream = null;
		BufferedReader bufferedReader = null;
		String r;

		try {
			// mcp75
			file = new File(mcpConfigDir + "/" + mcpName + ".mcp75.cfg");	//	(example) map/M14A/A.mcp.cfg
			inputStream = new FileInputStream(file);
			bufferedReader = new BufferedReader(new InputStreamReader(inputStream));
			r = "";
			
			Pattern p_point = Pattern.compile("^\\s*POINT = "	// POINT = 20, 13026, 21, 1461, 11, 22, 2888, 32, 0, 1
					+ "\\s*\\d+," 	// address
	                + "\\s*\\d+," 	// st-no
	                + "\\s*\\d+," 	// left-address
	                + "\\s*\\d+," 	// left-distance
	                + "\\s*\\d+," 	// left-speed
	                + "\\s*\\d+," 	// right-address
	                + "\\s*\\d+," 	// right-distance
	                + "\\s*\\d+," 	// right-speed
	                + "\\s*\\d+," 	// via-point
	                + "\\s*\\d+" 	// stop/reset-registration-point
	                + "\\s*$");	
			
			Pattern p_vhl = Pattern.compile("^\\s*VEHICLE = "
	                + "\\s*\".*\"," // vhl_id
	                + "\\s*\\d+," // type
	                + "\\s*\\d+," // loop_id
	                + "\\s*\\d+," // IDR operation status
	                + "\\s*\\d+;" // Mask detection operation status
	                + "\\s*$");	
			
			Pattern p_speed = Pattern.compile("^\\s*SPEED ="
	                + "\\s*\\d+," // index
	                + "\\s*\\d+.*\\d*;" // speed
	                + "\\s*$");
			
			Pattern p_station = Pattern.compile("^\\s*STATION = "
	                + "\\s*\\d+," // StationNo
	                + "\\s*\".*\"," // $STATION_TYPE
	                + "\\s*\\d+," // $Wait Allowed or Not Allowed
	                + "\\s*\".*\"," // PortID
	                + "\\s*0x[0-9a-fA-F]+," // $Transport Carrier Type
	                + "\\s*\\d+," // $Bumping Destination setting
	                + "\\s*\\d+," // $Address Number
	                + "\\s*\\d+," // $Inventory Management Category
	                + "\\s*\\d+," // $STATION-Group1
	                + "\\s*\\d+," // $STATION-Group2
	                + "\\s*\\d+," // $Port_Group
	                + "\\s*\\d+," // $STATION-Location
	                + "\\s*\".*\"," // $Comment
	                + "\\s*\\d+," // $Standby Priority
	                + "\\s*\\d+," // $Parking Priority
	                + "\\s*\\d+," // $Forced Output Destination Priority
	                + "\\s*\\d+," // $Left Distance
	                + "\\s*\\d+," // $Right Distance
	                + "\\s*\\d+," // $Allowable simultaneous output count
	                + "\\s*\\d+," // $EQ-STATION at the same location
	                + "\\s*\\d+," // $STB Left at the same location
	                + "\\s*\\d+" // $STB Right at the same location
	                + "\\s*$");
			
			Set<String> tempR = new HashSet<>();
			
			while(
					(r != null && r.startsWith("["))
					|| null != (r = bufferedReader.readLine())
			) {
				if (
						r.startsWith("[")
						&& tempR.contains(r)
				) {
					r = bufferedReader.readLine();
				} else if (r.startsWith("[")) {
					tempR.add(r);
				}
				
				if (r.trim().startsWith("[MCP75_LAYOUT@")) {
					while(!(r = bufferedReader.readLine()).trim().startsWith("[")){
						if (r.trim().startsWith(";")) {	// 주석 생략
							continue;
						}
						Matcher p_point_matcher   = p_point.matcher(r);
						Matcher p_station_matcher = p_station.matcher(r);
						
						if (p_point_matcher.matches()) {
							String tempStr  = r.substring(r.lastIndexOf('=') + 1);
		                    String[] tokens = StringUtils.splitPreserveAllTokens(tempStr, ',');                    
		                    RawPoint rawPoint = new RawPoint(
		                    							   Util.getIntOrZero(tokens[0].trim()), 
		                    							   Util.getIntOrZero(tokens[1].trim()), 
		                    							   Util.getIntOrZero(tokens[2].trim()), 
								                   		   Util.getIntOrZero(tokens[3].trim()), 
								                   		   Util.getIntOrZero(tokens[4].trim()), 
								                   		   Util.getIntOrZero(tokens[5].trim()), 
								                   		   Util.getIntOrZero(tokens[6].trim()), 
								                   		   Util.getIntOrZero(tokens[7].trim()), 
								                   		   Util.getIntOrZero(tokens[8].trim()) > 0, 
								                   		   Util.getIntOrZero(tokens[9].trim())
							);
		                    rawPointMap.put(rawPoint.getAddress(), rawPoint);
						} else if(p_station_matcher.matches()) {
							String tempStr 	= r.substring(r.lastIndexOf('=') + 1);
		                    String[] tokens = tempStr.split("[,]"); 
		                    //StationNo, $STATION_TYPE , $Wait Allowed or Not Allowed, PortID, $Transport Carrier Type, $Bumping Destination setting, $Address Number, 
		                    //$Inventory Management Category, $STATION-Group1, $STATION-Group2, $Port_Group, $STATION-Location, $Comment, $Standby Priority, $Parking Priority, 
		                    //$Forced Output Destination Priority, $Left distance, $Right distance, $Allowable simultaneous output count, 
		                    //$EQ-STATION at the same location, $STB Left at the same location, $STB Right at the same location
		                    RawStation rst 	= new RawStation(
								                    		 Util.getIntOrZero(tokens[0].trim()), 
								                    		 STATION_TYPE.valueOf(tokens[1].replaceAll("\"", "").trim()), 
								                    		 "0".equals(tokens[2].trim()), 
								                    		 tokens[3].replaceAll("\"", "").trim(), 
								                    		 Integer.parseInt(tokens[4].trim().substring(2), 16), 
								                    		 "0".equals(tokens[5].trim()), 
								                    		 Util.getIntOrZero(tokens[6].trim()), 
								                    		 INV_MGT_CATEGORY.values()[Util.getIntOrZero(tokens[7].trim())], 
								                    		 Util.getIntOrZero(tokens[8].trim()), 
								                    		 Util.getIntOrZero(tokens[9].trim()), 
								                    		 Util.getIntOrZero(tokens[10].trim()), 
								                    		 STATION_LOCATION.values()[Util.getIntOrZero(tokens[11].trim())], 
								                    		 tokens[12].replaceAll("\"", "").trim(), 
								                    		 Util.getIntOrZero(tokens[13].trim()), 
								                    		 Util.getIntOrZero(tokens[14].trim()), 
								                    		 Util.getIntOrZero(tokens[15].trim()), 
								                    		 Util.getDoubleOrZero(tokens[16].trim()), 
								                    		 Util.getDoubleOrZero(tokens[17].trim()), 
								                    		 Util.getIntOrZero(tokens[18].trim()),
								                    		 Util.getIntOrZero(tokens[19].trim()),
								                    		 Util.getIntOrZero(tokens[20].trim()),
								                    		 Util.getIntOrZero(tokens[21].trim())
							);
		                    rawStationMap.put(rst.getStNo(), rst);
						} else if (r.trim().startsWith("<ZONE>")) {
							int id, subId;
							
							String idStr = r.substring(0, r.indexOf(';'));
							id 			 = Util.getIntOrZero(idStr.split(":")[1]);
							subId 		 = Util.getIntOrZero(idStr.split(":")[2]);
							r 			 = bufferedReader.readLine();
							
							if (r.indexOf("\"LOOP\"") > 0) {
								Set<Integer[]> entrySet = new HashSet<>();
								Set<Integer[]> exitSet 	= new HashSet<>();
								String name 			= "";
								int zoneCarrierType 	= 0;
								int runningAreaType 	= 0;
								
								while(!(r = bufferedReader.readLine()).trim().startsWith(">")) {
									if (r.trim().startsWith(";")) {
										continue;
									}
								
									String cfg = r.split(";")[0].trim();
									
									if (cfg.startsWith("ENTRY")) {
										int entryLaneStart = Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim());
										int entryLaneEnd   = Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim());
										
										entrySet.add(new Integer[] {entryLaneStart, entryLaneEnd});
									} else if(cfg.startsWith("EXIT")) {
										int exitLaneStart = Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim());
										int exitLaneEnd   = Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim());
										
										exitSet.add(new Integer[] {exitLaneStart, exitLaneEnd});
									} else if(cfg.startsWith("NAME")) {
										name = cfg.split("=")[1].replaceAll("\"", "").trim();
									} else if(cfg.startsWith("ZONE_CARRIER_TYPE")) {
										zoneCarrierType = Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if(cfg.startsWith("RUNNING_AREA_TYPE")) {
										runningAreaType = Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim());
									}
								}
								
								RawLoop rl = new RawLoop(
														 id, 
														 subId, 
														 entrySet, 
														 exitSet, 
														 name, 
														 zoneCarrierType, 
														 runningAreaType
														);
								
								this.rawLoopMap.put(rl.getId() + ":" + rl.getSubId(), rl);
							} else if(r.indexOf("\"HID\"") > 0) {
								Set<LoopEntry> loopEntrySet = new HashSet<>();
								Set<Integer[]> exitSet 		= new HashSet<>();
								int vhlMax 					= 0;
								int vhlPreCaution 			= 0;
								int zoneCarrierType 		= 0;
								Set<Integer[]> autoCloseSet = new HashSet<>();
								int autoCloseVhlCntDisable 	= 0;
								int autoCloseVhlCntRestore 	= 0;
								
								while(!(r = bufferedReader.readLine()).trim().startsWith(">")) {
									if (r.trim().startsWith(";")) continue;
									
									String cfg = r.split(";")[0].trim();
									
									if (cfg.startsWith("LOOP_ENTRY")) {										
										int entryLaneStart = Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim());
										int entryLaneEnd   = Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim());
										String setZcu 	   = cfg.split("=")[1].split(",")[2].trim();
										int entrySettingNo = Util.getIntOrZero(cfg.split("=")[1].split(",")[3].trim());
										
										loopEntrySet.add(
														 new LoopEntry(
																 	   entryLaneStart, 
																 	   entryLaneEnd, 
																 	   setZcu, 
																 	   entrySettingNo
															 	   	  )
														);
									} else if (cfg.startsWith("EXIT")) {
										exitSet.add(new Integer[]{
																  Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim()), 
																  Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim())
																 });
									} else if (cfg.startsWith("VEHICLE_MAX")) {
										vhlMax 					= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if (cfg.startsWith("VEHICLE_PRECAUTION")) {
										vhlPreCaution 			= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if (cfg.startsWith("ZONE_CARRIER_TYPE")) {
										zoneCarrierType 		= Util.getIntOrZero(cfg.split("=")[1].trim());									
									} else if (cfg.startsWith("AUTO_CLOSE_VEHICLE_COUNT")) {
										autoCloseVhlCntDisable 	= Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim());
										autoCloseVhlCntRestore 	= Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim());
									} else if (cfg.startsWith("AUTO_CLOSE")) {
										autoCloseSet.add(new Integer[]{
																	   Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim()), 
																	   Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim())
																	  });
									}
								}
								
								RawHid rh = new RawHid(
													   id, 
													   subId, 
													   loopEntrySet, 
													   exitSet, 
													   vhlMax, 
													   vhlPreCaution, 
													   zoneCarrierType, 
													   autoCloseSet, 
													   autoCloseVhlCntDisable, 
													   autoCloseVhlCntRestore
													  );
								
								this.rawHidMap.put(rh.getId() + ":" + rh.getSubId(), rh);
							} else if (r.indexOf("\"AREA\"") > 0) {
								String name 			= ""; 
								Set<Integer[]> entrySet = new HashSet<>();
								Set<Integer[]> exitSet 	= new HashSet<>();
								int vhlMax				= 0, 
									vhlPreCaution 		= 0, 
									vhlAvg 				= 0;
								int vhlMin				= 0, 
									idleVhlMax			= 0, 
									idleVhlAvg			= 0,
									idleVhlMin			= 0, 
									parkDistance		= -1;
								int areaSearchDistance  = 0, 
									zoneCarrierType		= 0;
								
								while(!(r = bufferedReader.readLine()).trim().startsWith(">")) {
									if (r.trim().startsWith(";")) {
										continue;
									}
									
									String cfg = r.split(";")[0].trim();
									
									if (cfg.startsWith("ENTRY")) {
										entrySet.add(new Integer[]{
															       Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim()), 
															       Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim())
															     });
									} else if(cfg.startsWith("EXIT")) {
										exitSet.add(new Integer[]{Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim()), Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim())});
									} else if(cfg.startsWith("VEHICLE_MAX")) {
										vhlMax 				= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if(cfg.startsWith("VEHICLE_PRECAUTION")) {
										vhlPreCaution 		= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if(cfg.startsWith("VEHICLE_AVG")) {
										vhlAvg 				= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if(cfg.startsWith("VEHICLE_MIN")) {
										vhlMin 				= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if(cfg.startsWith("IDLE_VEHICLE_MAX")) {
										idleVhlMax 			= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if(cfg.startsWith("IDLE_VEHICLE_AVG")) {
										idleVhlAvg 			= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if(cfg.startsWith("IDLE_VEHICLE_MIN")) {
										idleVhlMin 			= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if(cfg.startsWith("NAME")) {
										name 				= cfg.split("=")[1].trim().replaceAll("\"", "");
									} else if(cfg.startsWith("PARK_DISTANCE")) {
										parkDistance 		= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if(cfg.startsWith("AREA_SEARCH_DISTANCE")) {
										areaSearchDistance 	= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if(cfg.startsWith("ZONE_CARRIER_TYPE")) {
										zoneCarrierType 	= Util.getIntOrZero(cfg.split("=")[1].trim());
									}
								}
								
								RawArea ra = new RawArea(
														 id, 
														 subId, 
														 name, 
														 entrySet,
														 exitSet, 
														 vhlMax, 
														 vhlPreCaution, 
														 vhlAvg, 
														 vhlMin, 
														 idleVhlMax, 
														 idleVhlAvg, 
														 idleVhlMin, 
														 parkDistance, 
														 areaSearchDistance, 
														 zoneCarrierType
														);
								
								this.rawAreaMap.put(ra.getId() + ":" + ra.getSubId(), ra);
							} else if (r.indexOf("\"BAY\"") > 0) {
								String name 					= ""; 
								Set<RawBay.RawBayPort> entrySet = new HashSet<>();
								Set<RawBay.RawBayPort> exitSet 	= new HashSet<>();
								int zoneCarrierType				= 0;
								RawBay rb 						= new RawBay(
																			 id, 
																			 subId, 
																			 name, 
																			 fabId, 
																			 entrySet,
																			 exitSet, 
																			 zoneCarrierType
																			);
								
								while(!(r = bufferedReader.readLine()).trim().startsWith(">")) {
									if (r.trim().startsWith(";")) {
										continue;
									}
									
									String cfg = r.split(";")[0].trim();
									
									if (cfg.startsWith("ENTRY")) {
										rb.getEntrySet().add(
															 rb.new RawBayPort(
																			   Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim()), 
																			   Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim()), 
																			   cfg.split("=")[1].split(",")[2].trim().replaceAll("\"", "")
																			   )
															 );
									} else if(cfg.startsWith("EXIT")) {
										rb.getExitSet().add(
															rb.new RawBayPort(
																		      Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim()), 
																		      Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim()), 
																		      cfg.split("=")[1].split(",")[2].trim().replaceAll("\"", "")
																		      )
															);
									} else if(cfg.startsWith("NAME")) {
										rb.setName(cfg.split("=")[1].trim().replaceAll("\"", ""));
									} else if(cfg.startsWith("ZONE_CARRIER_TYPE")) {
										rb.setZoneCarrierType(Util.getIntOrZero(cfg.split("=")[1].trim()));
									}
								}
								
								this.rawBayMap.put(rb.getId() + ":" + rb.getSubId(), rb);
								
								this.bayNameIdMap.put(
													  rb.getName(), 
													  new int[] {rb.getId(), rb.getSubId()}
													 );
							} else if (r.indexOf("\"JUNCTION\"") > 0) {
								Set<Integer[]> entrySet = new HashSet<>();
								Set<Integer[]> exitSet  = new HashSet<>();
								int zoneCarrierType		= 0;
								int vhlPreCaution 		= 1;
								
								while(!(r = bufferedReader.readLine()).trim().startsWith(">")) {
									if (r.trim().startsWith(";")) {
										continue;
									}
									
									String cfg = r.split(";")[0].trim();
									
									if (cfg.startsWith("ENTRY")) {
										entrySet.add(new Integer[]{
																   Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim()), 
																   Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim())
																  });
									} else if(cfg.startsWith("EXIT")) {
										exitSet.add(new Integer[]{
																  Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim()), 
																  Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim())
																 });
									} else if(cfg.startsWith("VEHICLE_PRECAUTION")) {
										vhlPreCaution 	= Util.getIntOrZero(cfg.split("=")[1].trim());
									} else if(cfg.startsWith("ZONE_CARRIER_TYPE")) {
										zoneCarrierType = Util.getIntOrZero(cfg.split("=")[1].trim());
									}
								}
								
								RawJunction rj = new RawJunction(id, subId, entrySet, exitSet, vhlPreCaution, zoneCarrierType);
								
								this.rawJunctionMap.put(rj.getId() + ":" + rj.getSubId(), rj);
							}
							
						}
					}
				} else if (r.contains("[MCP75_VEHICLE]")) {
					while(!(r = bufferedReader.readLine()).trim().startsWith("[")) {
						Matcher p_vhl_matcher = p_vhl.matcher(r);
						
						if (p_vhl_matcher.matches()){
							String tempStr 	= r.substring(r.lastIndexOf('=') + 1);
		                    String[] tokens = tempStr.replaceAll("\"", "").replaceAll(";", "").split("[,]");
		                    
		                    this.rawVhlMap.put(
		                    				   tokens[0].trim(),
		                    				   new RawVhl(
		                    						   	  tokens[0].trim(), 
		                    						   	  Util.getIntOrZero(tokens[1].trim()), 
		                    						   	  Util.getIntOrZero(tokens[2].trim()), 
		                    						   	  Util.getIntOrZero(tokens[3].trim()) > 0,
		                    						   	  Util.getIntOrZero(tokens[4].trim()) > 0
		                    						   	 )
		                    				   );                    
						} else if (r.trim().startsWith("<TYPE>")) {
							int type 					  = Util.getIntOrZero(r.split(":")[1]);
							String vhlCode  			  = "";
							int carrierType 			  = 0;
							int runningAreaType 		  = 0;
							long minDistance 			  = 1400L;
							long offlineTimer 			  = 30000L;
							boolean carrierTypeMoving  	  = false;
							String vhlCodeName			  = "";
							int varVhlType				  = 0;
							String bumpDisableCarrierType = "";
							
							while(!(r = bufferedReader.readLine()).trim().startsWith(">")) {
								if (r.trim().startsWith(";")) {
									continue;
								}
								
								String cfg = r.split(";")[0].trim();
								
								if (cfg.startsWith("VEHICLE_CODE") && !cfg.contains("VEHICLE_CODE_NAME")) {
									vhlCode = cfg.split("=")[1].trim().replaceAll("\"", "");
								} else if (cfg.startsWith("CARRIER_TYPE")) {
									carrierType = Util.getIntOrZero(cfg.split("=")[1].trim());
								} else if (cfg.startsWith("RUNNING_AREA_TYPE")) {
									runningAreaType = Util.getIntOrZero(cfg.split("=")[1].trim());
								} else if (cfg.startsWith("MIN_DISTANCE")) {
									minDistance = Util.getIntOrZero(cfg.split("=")[1].trim());
								} else if (cfg.startsWith("OFFLINE_TIMER")) {
									offlineTimer = Util.getIntOrZero(cfg.split("=")[1].trim());
								} else if (cfg.startsWith("CARRIER_TYPE_MOVING")) {
									carrierTypeMoving = Util.getIntOrZero(cfg.split("=")[1].trim())>0;
								} else if (cfg.startsWith("VEHICLE_CODE_NAME")) {
									vhlCodeName = cfg.split("=")[1].trim().replaceAll("\"", "");
								} else if (cfg.startsWith("VAR_VEHICLE_TYPE")) {
									varVhlType = Util.getIntOrZero(cfg.split("=")[1].trim());
								} else if (cfg.startsWith("BUMP_DISABLE_CARRIER_TYPE")) {
									bumpDisableCarrierType = cfg.split("=")[1].trim();
								}
							}
							
							RawVhlType rvt = new RawVhlType(type, vhlCode, carrierType, runningAreaType, minDistance, offlineTimer, carrierTypeMoving, vhlCodeName, varVhlType, bumpDisableCarrierType);
							
							this.rawVhlTypeMap.put(rvt.getType(), rvt);
						} else if (r.matches("^\\s*PULSE_RATE =.*")){
							this.setPulseRate(Util.getDoubleOrZero(r.substring(r.lastIndexOf('=') + 1).replaceAll(";", "")));
						} else if (r.matches("^\\s*VHL_SPEED_TYPE =.*")){
							this.setVhlSpeedType(r.substring(r.lastIndexOf('=') + 1).replaceAll(";", "").replaceAll("\"", "").trim());
						}
					}
				} else if(r.contains("[MCP75_BZ]")) {
					while(!(r = bufferedReader.readLine()).trim().startsWith("[")) {
						if (r.indexOf("<BZ>") > 0) {
							String cfg 						= r.split(";")[0].trim();
							int schedulerId 				= Util.getIntOrZero(cfg.split(":")[1].trim());
							int territoryNo 				= Util.getIntOrZero(cfg.split(":")[2].trim());	
							String code 					= "53";
							String id 						= "";
							List<ObzQueue> obzQueueList 	= new ArrayList<>();
							HidInfo hidInfo 				= null;
							List<StopPoint> stopPointList 	= new ArrayList<>();
							List<Fd> fdList 				= new ArrayList<>();
							RawBz rb 						= new RawBz();
							
							while(!(r = bufferedReader.readLine()).trim().startsWith(">")) {
								if (r.trim().startsWith(";")) {
									continue;
								}
								
								cfg = r.split(";")[0].trim();
								
								if (cfg.startsWith("BZ_CODE")) {
									code 				= cfg.split("=")[1].replaceAll("\"", "").trim();
								} else if (cfg.startsWith("BZ")) {
									id 					= cfg.split("=")[1].replaceAll("\"", "").trim();
								} else if (cfg.startsWith("QUEUE")) {
									int no 				= Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim());
									int mcpZoneNo 		= Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim());
									int[] stopAddresses = new int[cfg.split("=")[1].split(",").length - 2];
									
									for (int i = 2; i < cfg.split("=")[1].split(",").length; i++) {
										stopAddresses[i-2] = Util.getIntOrZero(cfg.split("=")[1].split(",")[i].trim());
									}
									
									obzQueueList.add(
													 rb.new ObzQueue(no, mcpZoneNo, stopAddresses)
													);
								} else if (cfg.startsWith("FD")) {
									String machineId 	= cfg.split("=")[1].split(",")[0].replaceAll("\"", "").trim();
									int fd1or2 			= Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim());
									int laneStartPoint 	= Util.getIntOrZero(cfg.split("=")[1].split(",")[2].trim());
									int laneEndPoint 	= Util.getIntOrZero(cfg.split("=")[1].split(",")[3].trim());
									
									fdList.add(
											   rb.new Fd(machineId, fd1or2, laneStartPoint, laneEndPoint)
											  );									
								} else if (cfg.startsWith("HID_UNIT")) {
									if (hidInfo != null) {
										hidInfo.setHidSynchUnit(cfg.split("=")[1].replaceAll("\"", "").trim());
									}
								} else if (cfg.startsWith("HID")) {	
									String machineId 		 = cfg.split("=")[1].split(",")[0].replaceAll("\"", "").trim();
									int hid1or2 			 = Util.getIntOrZero(cfg.split("=")[1].split(",")[1].trim());
									int mcpZoneNo 			 = Util.getIntOrZero(cfg.split("=")[1].split(",")[2].trim());
									String machineTypeCode 	 = cfg.split("=")[1].split(",")[3].replaceAll("\"", "").trim();
									String extendedMachineId = cfg.split("=")[1].split(",")[4].replaceAll("\"", "").trim();						
									
									hidInfo 				 = rb.new HidInfo(
																			  machineId, 
																			  hid1or2, 
																			  mcpZoneNo, 
																			  machineTypeCode, 
																			  extendedMachineId, 
																			  null
																			 );									
								} else if (cfg.startsWith("STOP_POINT")) {
									stopPointList.add(
													  rb.new StopPoint(
															  		   Util.getIntOrZero(cfg.split("=")[1].split(",")[0].trim()), 
															  		   Byte.decode(cfg.split("=")[1].split(",")[1].trim())
															  		  )
													 );
								}
								
								rb = new RawBz(
											   code, 
											   id, 
											   obzQueueList, 
											   hidInfo, 
											   stopPointList, 
											   fdList, 
											   schedulerId, 
											   territoryNo
											  );
								
								this.rawBzMap.put(rb.getId(), rb);
							}
						}
					}
				} else if (r.contains("[MCP75_VEHICLE_SPEED]")){
					while(!(r = bufferedReader.readLine()).trim().startsWith("[")) {
						if (r.trim().startsWith(";")) {
							continue;
						}
						
						if (r.matches("^\\s*[<].*[>]\\s*$")){
							String vhl_speed_type 				  = r.trim().replaceAll("<","").replaceAll(">", "");
							ConcurrentMap<Integer,RawVhlSpeed> vm = new ConcurrentHashMap<>();
							
							while(!(r = bufferedReader.readLine()).trim().startsWith(">")) {
								if (r.trim().startsWith(";")) {
									continue;
								}
								
								Matcher p_speed_matcher = p_speed.matcher(r);
								
								if (p_speed_matcher.matches()){
									String[] st = r.substring(r.lastIndexOf('=') + 1).split("[,]");
									
									vm.put(
										   Util.getIntOrZero(st[0].trim()), 
										   new RawVhlSpeed(
												   		   Util.getIntOrZero(st[0].trim()), 
												   		   Util.getDoubleOrZero(st[1].replaceAll(";", "").trim())
												   		  )
										  );
								}
							}
							
							rawVhlSpeedMap.put(vhl_speed_type, vm);
						}
					}
				}
			}
			
			bufferedReader.close();
			inputStream.close();
			
			// lanecut/inactive_SCH_1
			if (!this.rawRailCutSet.isEmpty()) {
				// 초기화
				this.rawRailCutSet = ConcurrentHashMap.newKeySet();
			}
			this.rawRailCutSet = this._formatNewRawRailCut(mcpConfigDir, mcpName);
			
//			theFile = new File(mcpConfigDir + "/" + mcpName + ".lanecut.dat");	// Need to update in 30 seconds.
//			in 		= new FileInputStream(theFile);
//			br 		= new BufferedReader(new InputStreamReader(in));
//			
//			while(null != (r = br.readLine())) {
//				String line = r.trim();
//				
//				if (line.startsWith("LANE")) {
//					String[] contents = line.split("=")[1].split(",");
//					String laneCut    = String.format("%05d", Util.getIntOrZero(contents[0].trim())) + "-" + String.format("%05d" , Util.getIntOrZero(contents[1].trim()));
//					
//					rawLaneCutSet.add(laneCut);	// 1293-15121
//				}
//			}
//			
//			br.close();
//			in.close();
			
			// station
			file = new File(mcpConfigDir + "/" + mcpName + ".station.dat");
			inputStream 		= new FileInputStream(file);
			bufferedReader 		= new BufferedReader(new InputStreamReader(inputStream));
			
			while(
					(r != null && r.startsWith("["))
					|| null != (r = bufferedReader.readLine())
			){
				if (
						r.startsWith("[")
						&& tempR.contains(r)
				) {
					r = bufferedReader.readLine();
				} else if (r.startsWith("[")) {
					tempR.add(r);
				}
				
				Matcher p_station_matcher = p_station.matcher(r);
				
				if (p_station_matcher.matches()) {
					String tempStr 	= r.substring(r.lastIndexOf('=') + 1);
                    String[] tokens = tempStr.split("[,]"); 
                    RawStation rst;
                    
                    try {
	                    rst = new RawStation(
				                    		 Util.getIntOrZero(tokens[0].trim()), 
				                    		 STATION_TYPE.valueOf(tokens[1].trim().replaceAll("\"", "")), 
				                    		 "0".equals(tokens[2].trim()), 
				                    		 tokens[3].trim().replaceAll("\"", ""), 
				                    		 Integer.parseInt(tokens[4].trim().replaceAll("\"", "").substring(2), 16), 
				                    		 "0".equals(tokens[5].trim()), 
				                    		 Util.getIntOrZero(tokens[6].trim()), 
				                    		 INV_MGT_CATEGORY.values()[Util.getIntOrZero(tokens[7].trim())], 
				                    		 Util.getIntOrZero(tokens[8].trim()), 
				                    		 Util.getIntOrZero(tokens[9].trim()), 
				                    		 Util.getIntOrZero(tokens[10].trim()), 
				                    		 STATION_LOCATION.values()[Util.getIntOrZero(tokens[11].trim())], 
				                    		 tokens[12].replaceAll("\"", "").trim(),
				                    		 Util.getIntOrZero(tokens[13].trim()), 
				                    		 Util.getIntOrZero(tokens[14].trim()), 
				                    		 Util.getIntOrZero(tokens[15].trim()), 
				                    		 Util.getDoubleOrZero(tokens[16].trim()), 
				                    		 Util.getDoubleOrZero(tokens[17].trim()), 
				                    		 Util.getIntOrZero(tokens[18].trim()),
				                    		 Util.getIntOrZero(tokens[19].trim()),
				                    		 Util.getIntOrZero(tokens[20].trim()),
				                    		 Util.getIntOrZero(tokens[21].trim())
				        );
	                    rawStationMap.put(rst.getStNo(), rst);
                    } catch (Exception e) {
                    	logger.error("Error parsing rawStation [{}]", tempStr, e);
                    }
				}
			}
			
			bufferedReader.close();
			inputStream.close();
			
			// route
//			theFile 	= new File(mcpConfigDir + "/" + mcpName + ".route.dat");
//			in 			= new FileInputStream(theFile);
//			br 		 	= new BufferedReader(new InputStreamReader(in));
//			int fromBay = 0;
//			int toBay 	= 0;
//			
//			while(null != (r = br.readLine())) {
//				if (r.trim().startsWith("<DATA>")) {
//					String[] cfg = r.trim().split(";")[0].split(":");
//					fromBay 	 = Util.getIntOrZero(cfg[1].trim());
//					toBay 		 = Util.getIntOrZero(cfg[2].trim());
//				} else if (r.trim().startsWith("ROUTE_INFO")) {
//					String[] cfg 	= r.trim().split("=")[1].split(",");
//					int[] viaPoints = new int[cfg.length -5];
//					
//					for (int i=0; i < viaPoints.length; i++) {
//						viaPoints[i] = Util.getIntOrZero(cfg[i+5].trim());
//					}
//					
//					RawRouteInfo rr = new RawRouteInfo(
//													   fromBay + ":" + toBay, 
//													   fabId, 
//													   mcpName, 
//													   fromBay, 
//													   toBay, 
//													   Util.getIntOrZero(cfg[0].trim()), 
//													   Util.getIntOrZero(cfg[1].trim()), 
//													   Util.getIntOrZero(cfg[2].trim()), 
//													   cfg[3].replaceAll("\"", "").trim(), 
//													   cfg[4].replaceAll("\"", "").trim(), 
//													   viaPoints
//													  );
//					
//					this.getRawRouteInfoMap().put(rr.getId(), rr);
//				}
//			}
		} catch (Exception e) {
			logger.error("", e);
		} finally {
			try {
				if (bufferedReader != null)
					bufferedReader.close();
			} catch (IOException e) {
				logger.error("", e);
			}
			
			try {
				if (inputStream != null) {
					inputStream.close();
				}
			} catch (IOException e) {
				logger.error("", e);
			}
		}
		
		ZipFile zipFile   = null;
		InputStream zipIn = null;
		
		try{
			zipFile = new ZipFile("map/" + fabId + "/" + mcpName + ".layout.zip");
			
			for (Enumeration<? extends ZipEntry> e = zipFile.entries(); e.hasMoreElements();){
				ZipEntry ze = e.nextElement();
				
				if (ze.getName().endsWith("layout.xml")){
					zipIn =  zipFile.getInputStream(ze);
					
					break;
				}
			}
			
			SAXReader reader  = new SAXReader();
			Document document = reader.read( zipIn );
			
			List<Node> nodes  = document.selectNodes("/group/group/group[@class='jp.co.daifuku.tsc.common.layoutdata.layout.address.Addr']");

            for (Node n : nodes) {
                Element e = (Element) n;

                if (!"remove".equals(e.attributeValue("param[@key='update']"))) {
                    int address = Util.getIntOrZero(Util.getSingleNodeValue(n, "param[@key='address']"));
                    double cadX = Util.getDoubleOrZero(Util.getSingleNodeValue(n, "param[@key='cad-x']"));
                    double cadY = Util.getDoubleOrZero(Util.getSingleNodeValue(n, "param[@key='cad-y']"));
                    double cadZ = Util.getDoubleOrZero(Util.getSingleNodeValue(n, "param[@key='cad-z']"));
                    double drawX = Util.getDoubleOrZero(Util.getSingleNodeValue(n, "param[@key='draw-x']"));
                    double drawY = Util.getDoubleOrZero(Util.getSingleNodeValue(n, "param[@key='draw-y']"));
                    RawPoint rp = this.getRawPointMap().get(address);

                    if (rp != null) {
                        rp.setCadX(cadX);
                        rp.setCadY(cadY);
                        rp.setCadZ(cadZ);
                        rp.setDrawX(drawX);
                        rp.setDrawY(drawY);
                    }

                    List<Node> sl = n.selectNodes("group[@class='jp.co.daifuku.tsc.common.layoutdata.layout.address.Station']");

                    for (Node s : sl) {
                        Element es = (Element) s;

                        if (!"remove".equals(es.attributeValue("param[@key='update']"))) {
                            int no = Util.getIntOrZero(Util.getSingleNodeValue(s, "param[@key='no']"));
                            double slide = Util.getDoubleOrZero(Util.getSingleNodeValue(s, "param[@key='slide']"));

                            if (this.getRawStationMap().containsKey(no)) {
                                this.getRawStationMap().get(no).setSlide(slide);
                            }
                        }
                    }
                }
            }
			
			/*
			  Collect all the label to be shown on the map and compute the coordinate for them.
			 */
			final Map<Integer,RawPoint> mapRawPoint = this.getRawPointMap();
			final Map<String, RawLabel> mapRawLabel = this.getRawLabelMap();
			final List<Node> ll 					= document.selectNodes("/group/group/group[@class='jp.co.daifuku.tsc.common.layoutdata.layout.label.Label']");

            for (Node s : ll) {
                Element es = (Element) s;

                if (!"remove".equals(es.attributeValue("param[@key='update']"))) {
                    final int addrBase = Util.getIntOrZero(Util.getSingleNodeValue(s, "param[@key='address']"));
                    final RawPoint rawPoint = mapRawPoint.get(addrBase);

                    if (rawPoint == null) {
                        continue;
                    }

                    final double x = Util.getIntOrZero(Util.getSingleNodeValue(s, "param[@key='draw-x']")) + rawPoint.getDrawX();
                    final double y = Util.getIntOrZero(Util.getSingleNodeValue(s, "param[@key='draw-y']")) + rawPoint.getDrawY();
                    final String label = Util.getSingleNodeValue(s, "param[@key='machine-id']");

                    final RawLabel rawLabel = new RawLabel(addrBase, x, y, label);

                    mapRawLabel.put(label, rawLabel);
                }
            }
			
			for (RawStation rs : this.getRawStationMap().values()) {
				RawPoint head 		  = this.getRawPointMap().get(rs.getAddress_no());
				RawPoint tail;
				double stDistFromHead;
				double edgeLength;
				
				if (rs.getStationLocation() == STATION_LOCATION.RIGHT_BRANCH) {
					tail 			= this.getRawPointMap().get(head.getRightAddress());
					stDistFromHead  = rs.getRightDistance();
					edgeLength 		= head.getRightDistance();  
				} else {
					tail 			= this.getRawPointMap().get(head.getLeftAddress());
					stDistFromHead 	= rs.getLeftDistance();
					edgeLength 		= head.getLeftDistance();
				}
				
				double x 		 = head.getDrawX() + ((tail.getDrawX() - head.getDrawX()) * stDistFromHead/edgeLength);
				double y 		 = head.getDrawY() + ((tail.getDrawY() - head.getDrawY()) * stDistFromHead/edgeLength);
				
				double edgeAngle = Math.atan2(tail.getDrawX()-head.getDrawX(), tail.getDrawY()-head.getDrawY());
				
				if (rs.getPortLocation() == PORT_LOCATION.RIGHT) {
					edgeAngle += Math.PI / 2.0;
					edgeAngle %= Math.PI * 2.0;
					
					x += slidePortDist * Math.sin(edgeAngle);
					
					y += slidePortDist * Math.cos(edgeAngle);
				} else if (rs.getPortLocation() == PORT_LOCATION.LEFT) {
					edgeAngle -= Math.PI / 2.0;
					edgeAngle %= Math.PI * 2.0;
					
					x += slidePortDist * Math.sin(edgeAngle);
					
					y += slidePortDist * Math.cos(edgeAngle);
				}
				
				rs.setDrawX(x);
				rs.setDrawY(y);				
			}
		} catch (Exception e){
			logger.error("", e);
		} finally {
			try {
				if (zipIn != null) {
					zipIn.close();
				}
				
				//보안 취약점 조치(Unreleased Resource: Files)
				if(zipFile != null) {
					zipFile.close();
				}
			} catch (IOException e) {
				logger.error("", e);
			}
		}
	}

	public ConcurrentMap<Integer, RawPoint> getRawPointMap() {
		return rawPointMap;
	}

	public void setRawPointMap(ConcurrentMap<Integer, RawPoint> rawPointMap) {
		this.rawPointMap = rawPointMap;
	}

	public ConcurrentMap<Integer, RawStation> getRawStationMap() {
		return rawStationMap;
	}

	public void setRawStationMap(ConcurrentMap<Integer, RawStation> rawStationMap) {
		this.rawStationMap = rawStationMap;
	}

	public ConcurrentMap<String, RawVhl> getRawVhlMap() {
		return rawVhlMap;
	}

	public void setRawVhlMap(ConcurrentMap<String, RawVhl> rawVhlMap) {
		this.rawVhlMap = rawVhlMap;
	}

	public ConcurrentMap<Integer, RawVhlType> getRawVhlTypeMap() {
		return rawVhlTypeMap;
	}

	public void setRawVhlTypeMap(ConcurrentMap<Integer, RawVhlType> rawVhlTypeMap) {
		this.rawVhlTypeMap = rawVhlTypeMap;
	}

	public ConcurrentMap<String, ConcurrentMap<Integer, RawVhlSpeed>> getRawVhlSpeedMap() {
		return rawVhlSpeedMap;
	}
	
	public void setRawVhlSpeedMap(ConcurrentMap<String, ConcurrentMap<Integer, RawVhlSpeed>> rawVhlSpeedMap) {
		this.rawVhlSpeedMap = rawVhlSpeedMap;
	}

	public ConcurrentMap<String, RawArea> getRawAreaMap() {
		return rawAreaMap;
	}

	public void setRawAreaMap(ConcurrentMap<String, RawArea> rawAreaMap) {
		this.rawAreaMap = rawAreaMap;
	}

	public ConcurrentMap<String, RawBay> getRawBayMap() {
		return rawBayMap;
	}

	public void setRawBayMap(ConcurrentMap<String, RawBay> rawBayMap) {
		this.rawBayMap = rawBayMap;
	}

	public ConcurrentMap<String, RawJunction> getRawJunctionMap() {
		return rawJunctionMap;
	}

	public void setRawJunctionMap(ConcurrentMap<String, RawJunction> rawJunctionMap) {
		this.rawJunctionMap = rawJunctionMap;
	}

	public double getPulseRate() {
		return pulseRate;
	}

	public void setPulseRate(double pulseRate) {
		this.pulseRate = pulseRate;
	}

	public String getVhlSpeedType() {
		return vhlSpeedType;
	}

	public void setVhlSpeedType(String vhlSpeedType) {
		this.vhlSpeedType = vhlSpeedType;
	}

	public ConcurrentMap<String, RawHid> getRawHidMap() {
		return rawHidMap;
	}

	public void setRawHidMap(ConcurrentMap<String, RawHid> rawHidMap) {
		this.rawHidMap = rawHidMap;
	}

	public ConcurrentMap<String, RawBz> getRawBzMap() {
		return rawBzMap;
	}

	public void setRawBzMap(ConcurrentMap<String, RawBz> rawBzMap) {
		this.rawBzMap = rawBzMap;
	}

	public ConcurrentMap<String, RawRouteInfo> getRawRouteInfoMap() {
		return rawRouteInfoMap;
	}

	public void setRawRouteInfoMap(ConcurrentMap<String, RawRouteInfo> rawRouteInfoMap) {
		this.rawRouteInfoMap = rawRouteInfoMap;
	}
	
	/**
	 * Returns a map having all the RawLabel
	 * @return ConcurrentMap<String, RawLabel>
	 */
	public ConcurrentMap<String, RawLabel> getRawLabelMap() {
		return rawLabelMap; 
	}

	/**
	 * Sets a new map having all the RawLabel
	 * @param rawLabelMap a map to set
	 */
	public void setRawLabelMap(ConcurrentMap<String, RawLabel> rawLabelMap) {
		this.rawLabelMap = rawLabelMap;
	}

	public double getSlidePortDist() {
		return slidePortDist;
	}

	public void setSlidePortDist(double slidePortDist) {
		this.slidePortDist = slidePortDist;
	}

	public Set<String> getRawRailCutSet() {
		return rawRailCutSet;
	}

	public void setRawRailCutSet(Set<String> rawRailCutSet) {
		this.rawRailCutSet = rawRailCutSet;
	}

	public ConcurrentMap<String, int[]> getBayNameIdMap() {
		return bayNameIdMap;
	}

	public void setBayNameIdMap(ConcurrentMap<String, int[]> bayNameIdMap) {
		this.bayNameIdMap = bayNameIdMap;
	}

	public ConcurrentMap<String, RawLoop> getRawLoopMap() {
		return rawLoopMap;
	}

	public void setRawLoopMap(ConcurrentMap<String, RawLoop> rawLoopMap) {
		this.rawLoopMap = rawLoopMap;
	}	
	
	private Set<String> _formatNewRawRailCut (
			String mapDirectory,
			String mcpName
	) {
		File file;
		InputStream inputStream = null;
		BufferedReader bufferedReader = null;
		String reader;
		Set<String> newRawRailCutSet = ConcurrentHashMap.newKeySet();

		try {
			String path = String.format("%s/%s.lanecut.dat", mapDirectory, mcpName);
			file = new File(path);	// Need to update in 30 seconds.

			if (file.exists()) {
				inputStream = new FileInputStream(file);
				bufferedReader = new BufferedReader(new InputStreamReader(inputStream));

				while ((reader = bufferedReader.readLine()) != null) {
					String line = reader.trim();

					if (line.startsWith("LANE")) {
						String[] contents = line.split("=")[1].split(",");
						String railCut
								= String.format("%05d", Util.getIntOrZero(contents[0].trim()))
								+ "-"
								+ String.format("%05d" , Util.getIntOrZero(contents[1].trim())
						);

						newRawRailCutSet.add(railCut);
					}
				}
			} else {
				logger.warn("No File Exists In That Path ! (Path: {})", path);
			}
		} catch (Exception e) {
			logger.error("An Error Occurred While Update RailCut !", e);
		} finally {
			if (bufferedReader != null) {
				try {
					bufferedReader.close();
				} catch (Exception e) {
					logger.error("An Error Occurred While Closing BufferReader Of RailCut !!!", e);
				}
			}
			
			if (inputStream != null) {
				try {
					inputStream.close();
				} catch (Exception e) {
					logger.error("An Error Occurred While Closing InputStream Of RailCut !!!", e);
				}
			}
		}

		return newRawRailCutSet;
	}

	public void updateRawRailCut (String mapDirectory, String mcpName) {
		this.rawRailCutSet = _formatNewRawRailCut(mapDirectory, mcpName);
	}
}
