/**
 * A class to communicate with the conveyor server by the socket io.
 * @author 
 *
 */
public class CnvSocketIOListener {
	private static final Logger logger   			= LoggerFactory.getLogger(CnvSocketIOListener.class);
	private static final String TAG   				= CnvSocketIOListener.class.getSimpleName();
	ConcurrentMap<Integer,RawCnvZone> rawCnvZoneMap = new ConcurrentHashMap<Integer, RawCnvZone>();
	ConcurrentMap<String,Integer> rawHeadZoneIdMap  = new ConcurrentHashMap<String, Integer>();
	private static final String RV_CONVEYORIO 		= "_LOCAL.ATLAS.CONVEYOR.IO";
	Socket socket 									= null;
	boolean initialized0 							= false;
	boolean initialized 							= false;
	String fabId 									= "";
	String cnvId 									= "";
	String protocol 								= "http";
	String ip 										= "localhost";
	int port 										= -1;
    boolean firstConnect 							= true;
    String layoutStr 								= "";
    
    protected static long msg_seq 					= 0;

    /**
     * A constructor
     * @param fabId
     * @param conveyorId
     * @param url
     */
	public CnvSocketIOListener(String fabId, String cnvId, String urlString) {
		URL url;
		
		try {
			url 			= new URL(urlString);
			String protocol = url.getProtocol();
			String ip 		= url.getHost();
			int port 		= url.getPort();
			
			this.fabId 		= fabId;
			this.cnvId 		= cnvId;
			this.protocol 	= protocol;
			this.ip 		= ip;
			this.port 		= port;
		} catch (MalformedURLException e) {
			logger.error(TAG, e);
		}        
	}

    /**
     * A constructor
     * @param fabId
     * @param cnvId
     * @param ip
     * @param port
     */
	public CnvSocketIOListener(String fabId, String cnvId, String ip, int port) {
		this.fabId 	= fabId;
		this.cnvId 	= cnvId;
		this.ip 	= ip;
		this.port 	= port;	
	}

	/**
	 * Connects to the conveyor server and listen the realtime-data. 
	 * @return boolean
	 * @throws FileNotFoundException 
	 */
	
	// 해당 메서드는 dataService.loadFab()에서 fabPropertiesMap 데이터를 구성하는 과정에서 conveyor 초기화 후 동작
	public boolean connectAndBuildCnvRawLayout() {
		boolean connected = false;
		
		try {
			if (this.socket != null) {
				return false;
			}

			String connStr = String.format("%s://%s:%d", this.protocol, this.ip, port);
			this.socket    = IO.socket(connStr);
						
			logger.debug("started connect conveyor socket :: " + connStr);
			
			this.socket.on(Socket.EVENT_CONNECT, new Emitter.Listener() {
				@Override
			    public void call(Object... args) {
			    	try {
				    	for (Object arg : args) {
				    		logger.warn("{} connected arg : {}", cnvId, arg);
				    	}
				    	
				    	logger.warn("{} connected : {}", cnvId, socket.id());
				    	
				    	JSONObject jo = new JSONObject();			    	
						
				    	jo.put("type", "ZONE_GET_INFO");
				    	
				    	initialized   = false;
				    	
				    	socket.emit("message", jo);
			    	} catch (Exception e) {
			    		logger.error("[EVENT_CONNECT ERROR]", TAG, e);
					}
			    }
			});
			
			socket.on("message", new Emitter.Listener() {
				@Override
			    public void call(Object... args) {	//	Object... = Object[]
			    	logger.debug("confirm socket arguments" + args);
			    	
			    	for(Object arg : args) {
			    		
				    	JSONObject received = (JSONObject)arg;
				    	String type 		= "";
				    	
				    	try {
							type = received.getString("type");
							
							if (
									"initializedataSend".equals(type) 
									&& initialized0 == false
							) {
								logger.warn("{} initializedata received!!!!!!!!!!!!", cnvId);
								
								logger.debug("{} initializedata received : {}", cnvId, received.getString("data"));
							
								JSONObject zoneJo  = new JSONObject(received.getString("data"));
								JSONArray zoneList = new JSONArray();
								
								for (Iterator<String> iter = zoneJo.sortedKeys(); iter.hasNext();) {
									String key = iter.next();
									
									zoneList.put(zoneJo.getJSONObject(key));
								}
								
								layoutStr 	 = zoneJo.toString();
								
								buildRawMapData(zoneList);	//	→ (JSON)값을 파싱하여 rawCnvZoneMap에 저장 
								
								initialized0 = true;
							} else if (
									"UpdateZoneState".equals(type) 
									&& initialized == false
							) {
								while(initialized0 == false) {
									Thread.sleep(100);
								}
								
								JsonObject dataJo = JsonParser.parseString(received.toString().replaceAll("\\\"", "\"")).getAsJsonObject();
							
								logger.warn("{} UpdateZoneState received!!!!!!!!!!!!!!!!!!", cnvId);
								logger.debug("{} UpdateZoneState received : {}", cnvId, dataJo.toString());
								
								if (dataJo.get("data").isJsonArray()) {
					    			JsonArray ja = dataJo.get("data").getAsJsonArray();
					    			
					    			for (int ii = 0 ; ii < ja.size(); ii++) {
					    				String dataStr 	 = ja.get(ii).getAsString().replaceAll("\\\"", "\"");
					    				JsonElement je 	 = JsonParser.parseString(dataStr);
					    				JsonObject jo  	 = je.getAsJsonObject().get("Object").getAsJsonObject();
					    				String zoneNoStr = jo.get("ZoneID").getAsString();
					    				RawCnvZone rcz 	 = rawCnvZoneMap.get(Integer.parseInt(zoneNoStr));
					    				
					    				if (rcz != null) {
					    					boolean state = "0".equals(jo.get("State").getAsString());
					    					rcz.state 	  = state;
					    				}
					    			}
					    		}
								
								initialized = true;
								 
								if (firstConnect == true){
									firstConnect = false;
								} else {
									// 이미 초기화 완료 이후 재접속이 된 경우 자체 listen 재개가 필요.
									listenStart();									
								}
							}
				    	} catch (Exception e) {						
							logger.error("[MESSAGE ERROR]", TAG, e);
						}
			    	}
			    }
			});
			
			this.socket.on(Socket.EVENT_CONNECT_ERROR, new Emitter.Listener() {
			    @Override
			    public void call(Object... args) {
			    	for (Object arg : args) {
			    		logger.warn("connect error arg : {}", arg);
			    	}
			    	
			    	logger.debug("connect error : {}", socket.id());
			    }
			});
			
			this.socket.on(Socket.EVENT_DISCONNECT, new Emitter.Listener() {
			    @Override
			    public void call(Object... args) {
			    	initialized0 = false;
			    	initialized  = false;
			    	
			    	for (Object arg : args) {			    		
			    		logger.warn("disconnection arg : {}", arg);
			    	}
			    	
			    	logger.debug("disconnected : {}", socket.id());
			    }
			});
			
			connected = this.socket.connect().connected();
			
			while(initialized == false) {
				Thread.sleep(10);
			}
			logger.debug("finished...conveyor initializion");
		} catch (Exception e) {
			logger.error("SOCKET - ", TAG, e);
		}
		
		return connected;
	}
	
	// 해당 메서드는 launcherListener에서 listener를 동작시키는 과정에서 동작하지만 현재는 주석 처리하여 사용되지 않고 있음
	public boolean listenStart() {
		if (
				initialized == true 
				&& this.socket != null 
				&& this.socket.connected()
		) {
			socket.listeners("message").clear();
		
			try {
				JSONObject jo = new JSONObject();			    	
		
				jo.put("type", "INITIAL_REDIS_SUBSCRIBER");	
				
				initialized   = true;
				
				socket.emit("message", jo);
			} catch (Exception e) {
				logger.error("[JSON FORMAT ERROR]", e);
			}
			
			logger.warn("{} listen started...", cnvId);
			
			// ↓ listener open
			this.socket.on("message", new Emitter.Listener() {
			    @Override
			    public void call(Object... args) {
			    	for (int i = 0; i < args.length ;i++) {
				    	try {
				    		String message = args[i].toString();								

				    		TibrvMsg msg = new TibrvMsg();
				            
				    		msg.setSendSubject(RV_CONVEYORIO);
				            
				            msg.update("FABID", fabId);
				            msg.update("CNVID", cnvId);
				            msg.update("DATA", 	message);
				            
//				            TibrvSendToLocalDaemon.sendMessage(msg);
				    		
				    		// worker 미사용으로 인한 롲기 제거
				            DataService.getInstance().queue.add(
											            		new Msg(
											            				fabId, 
											            				MSG_TYP.CNV, 
											            				System.currentTimeMillis(), 
											            				cnvId, 
											            				message
											            			   )
											            		);
				        } catch (Exception e) {						
							logger.error("[MESSAGE ERROR 2]", TAG, e);
						}
			    	}
			    }
			});
			
			return true;
		} 
		
		return false;		
	}
	
	public void buildRawMapData(JSONArray zoneList) {
		for (int j = 0; j < zoneList.length(); j++) {
			try {
				JSONObject zo 		= zoneList.getJSONObject(j);
				int level 			= -1;
				int posX 			= -1;
				int posY 			= -1;
				int nextZone 		= -1;
				int prevZone 		= -1;
				int zoneDrawCount 	= -1;
				int zoneId 			= -1;
				int physicalType 	= -1;
				int refDirection 	= -1;
				String displayName 	= "";
				int currentNode 	= -1;
				int prevNode 		= -1;
				int logicalType 	= -1;
			
				if (zo.opt("Level")			!= null) {
					level = zo.getInt("Level");
				}
				
				if (zo.opt("posX")			!= null) {
					posX = zo.getInt("posX");
				}
				
				if (zo.opt("posY")			!= null) {
					posY = zo.getInt("posY");
				}
				
				if (zo.opt("NextZone")		!= null) {
					nextZone = zo.getInt("NextZone");
				}
				
				if (zo.opt("PrevZone")		!= null) {
					prevZone = zo.getInt("PrevZone");
					
					if (prevZone == 107109) {
						prevZone = 10709;
					}
				}
				
				if (zo.opt("ZoneDrawCount") != null) {
					zoneDrawCount = zo.getInt("ZoneDrawCount");
				}
				
				if (zo.opt("ZoneID")		!= null) {
					zoneId = zo.getInt("ZoneID");
				}
				
				if (zo.opt("PhysicalType") 	!= null) {
					physicalType = zo.getInt("PhysicalType");    			
				}
				
				if (zo.opt("RefDirection") 	!= null) {
					refDirection = zo.getInt("RefDirection");
				}
				
				if (zo.opt("DisplayName")  	!= null) {
					displayName = zo.getString("DisplayName");
				}
				
				if (displayName.contains("OUTG")) {
					rawHeadZoneIdMap.put(displayName,zoneId);
				}
				
				if (zo.opt("CurrentNode") 	!= null) {
					currentNode = zo.getInt("CurrentNode");
				}
				
				if (zo.opt("PrevNode")		!= null) {
					prevNode = zo.getInt("PrevNode");
				}
				
				if (zo.opt("LogicalType")	!= null) {
					logicalType = zo.getInt("LogicalType");
				}
				
				RawCnvZone rcz = new RawCnvZone(
												cnvId, 
												level, 
												posX, 
												posY, 
												nextZone, 
												prevZone, 
												zoneDrawCount, 
												zoneId, 
												physicalType, 
												refDirection, 
												displayName, 
												currentNode, 
												prevNode, 
												logicalType, 
												null, 
												null, 
												null
											   );
				
				JSONObject attributeLD = null;
				
				if (zo.optJSONObject("AttributeLD") != null) {
					attributeLD  = zo.optJSONObject("AttributeLD");
    				int included = -1;
    				
    				if (attributeLD.opt("Included") != null) {
    					included = attributeLD.optInt("Included");
    				}
    				
    				int[] sensorReversZones = null;
    				
    				if (attributeLD.opt("SensorReversZones") != null) {
    					sensorReversZones = new int[attributeLD.optJSONArray("SensorReversZones").length()];
	    				
    					for (int i = 0 ; i < sensorReversZones.length; i++) {
	    					sensorReversZones[i] = attributeLD.optJSONArray("SensorReversZones").getInt(i);
	    				}
    				}
    				
    				rcz.ldAttr = rcz.new RawCnvLdAttr(included, sensorReversZones);
				}
				
				JSONObject attributeQS = null;
    			
				if (zo.optJSONObject("AttributeQS") != null) {
    				attributeQS  = zo.optJSONObject("AttributeQS");
    				int included = -1;
    				
    				if (attributeQS.opt("Included") != null) {
    					included = attributeQS.optInt("Included");
    				}
    				
    				int homeDirection = -1;
    				
    				if (attributeQS.opt("HomeDirection") != null) {
    					homeDirection = attributeQS.optInt("HomeDirection");
    				}
    				
    				int isWayPoint = -1;
    				
    				if (attributeQS.opt("IsWayPoint")!=null) {
    					isWayPoint = attributeQS.optInt("IsWayPoint");
    				}
    				
    				int[] north = null;
    				int[] south = null;
    				int[] east  = null;
    				int[] west  = null;
    				
    				if (attributeQS.opt("North") != null) {
    					north 	 = new int[2];
    					north[0] = attributeQS.optJSONArray("North").getInt(0);
    					north[1] = attributeQS.optJSONArray("North").getInt(1);
    				}
    				
    				if (attributeQS.opt("South") != null) {
    					south 	 = new int[2];
    					south[0] = attributeQS.optJSONArray("South").getInt(0);
    					south[1] = attributeQS.optJSONArray("South").getInt(1);
    				}
    				
    				if (attributeQS.opt("East") != null) {
    					east 	= new int[2];
    					east[0] = attributeQS.optJSONArray("East").getInt(0);
    					east[1] = attributeQS.optJSONArray("East").getInt(1);
    				}
    				
    				if (attributeQS.opt("West") != null) {
    					west 	= new int[2];
    					west[0] = attributeQS.optJSONArray("West").getInt(0);
    					west[1] = attributeQS.optJSONArray("West").getInt(1);
    				} 
    				
    				rcz.qsAttr = rcz.new RawCnvQsAttr(
    												  included, 
    												  homeDirection, 
    												  isWayPoint, 
    												  north, 
    												  south, 
    												  east, 
    												  west
    												 );
    			}
				
    			JSONObject attributeLifter = null;
    			
    			if (zo.optJSONObject("AttributeLifter") != null) {
    				attributeLifter = zo.optJSONObject("AttributeLifter");
    				
    				int inIncludeZoneId 	= -1;
    				
    				if (attributeLifter.opt("InIncludeZoneID")	!= null) {
    					inIncludeZoneId = attributeLifter.optInt("InIncludeZoneID");
    				}
    				
    				int outIncludeZoneID 	= -1;
    				
    				if (attributeLifter.opt("OutIncludeZoneID")	!= null) {
    					outIncludeZoneID = attributeLifter.optInt("OutIncludeZoneID");
    				}
    				
    				int homeLevel 			= -1;
    				
    				if (attributeLifter.opt("HomeLevel")		!= null) {
    					homeLevel = attributeLifter.optInt("HomeLevel");
    				}
    				
    				int homingDirection 	= -1;
    				
    				if (attributeLifter.opt("HomingDirection")	!= null) {
    					homingDirection = attributeLifter.optInt("HomingDirection");
    				}
    				
    				int homingClearLimit 	= -1;
    				
    				if (attributeLifter.opt("HomingClearLimit")	!= null) {
    					homingClearLimit = attributeLifter.optInt("HomingClearLimit");
    				}
    				
    				List<Map<String,Integer>> levelZoneList = new ArrayList<Map<String,Integer>>();
    				JSONArray lvzs 							= attributeLifter.optJSONArray("LevelZone");
    				
    				for (int k = 0; k < lvzs.length(); k++) {
    					JSONObject lvz 			 = lvzs.optJSONObject(k);
    					Map<String,Integer> lvzm = new HashMap<String, Integer>();
    					
    					lvzm.put("In", 		 lvz.optInt("In"));
    					lvzm.put("Out", 	 lvz.optInt("Out"));
    					lvzm.put("Position", lvz.optInt("Position"));
    				}    				
    				
    				rcz.lftAttr = rcz.new RawCnvLftAttr(
    													inIncludeZoneId, 
    													outIncludeZoneID, 
    													homeLevel, 
    													homingDirection, 
    													homingClearLimit, 
    													levelZoneList
    													);
    			}
    			
    			rawCnvZoneMap.put(rcz.zoneId, rcz);
    		} catch (JSONException e) {
				logger.error("[buildRawMapData]", e);
			}
		}
	}

	public ConcurrentMap<Integer, RawCnvZone> getRawCnvZoneMap() {
		return rawCnvZoneMap;
	}

	public void setRawCnvZoneMap(ConcurrentHashMap<Integer, RawCnvZone> rawCnvZoneMap) {
		this.rawCnvZoneMap = rawCnvZoneMap;
	}

	public ConcurrentMap<String, Integer> getRawHeadZoneIdMap() {
		return rawHeadZoneIdMap;
	}

	public void setRawHeadZoneIdMap(ConcurrentHashMap<String, Integer> rawHeadZoneIdMap) {
		this.rawHeadZoneIdMap = rawHeadZoneIdMap;
	}

	public String getFabId() {
		return fabId;
	}

	public void setFabId(String fabId) {
		this.fabId = fabId;
	}

	public String getCnvId() {
		return cnvId;
	}

	public void setCnvId(String cnvId) {
		this.cnvId = cnvId;
	}

	public String getLayoutStr() {
		return layoutStr;
	}

	public void setLayoutStr(String layoutStr) {
		this.layoutStr = layoutStr;
	}
}
