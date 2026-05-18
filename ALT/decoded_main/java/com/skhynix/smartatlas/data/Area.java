package com.skhynix.smartatlas.data;

import java.util.concurrent.ConcurrentLinkedQueue;

public class Area {
	private String id 		= "";
	private String fabId 	= "";
	private String name 	= "";
	private String mcpName 	= "";
	private ConcurrentLinkedQueue<String> railEdgeIdList = new ConcurrentLinkedQueue<String>();

	public String getId() {
		return id;
	}

	public void setId(String id) {
		this.id = id;
	}

	public Area(String id, String fabId, String name, String mcpName) {
		super();

		this.id 		= id;
		this.fabId 		= fabId;
		this.name 		= name;
		this.mcpName 	= mcpName;
	}
	
	public Area(String id, String fabId, String name, ConcurrentLinkedQueue<String> railEdgeIdList) {
		super();

		this.id 			= id;
		this.fabId 			= fabId;
		this.name 			= name;
		this.railEdgeIdList	= railEdgeIdList;
	}

	public String getFabId() {
		return fabId;
	}

	public void setFabId(String fabId) {
		this.fabId = fabId;
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public ConcurrentLinkedQueue<String> getRailEdgeIdList() {
		return railEdgeIdList;
	}

	public void setRailEdgeIdList(ConcurrentLinkedQueue<String> railEdgeIdList) {
		this.railEdgeIdList = railEdgeIdList;
//		RedisPool.jset(this.id, railEdgeIdList, new Path(".railEdgeIdList"));
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.UPDATE, getClass().getName(), "railEdgeIdList", this.id, this.railEdgeIdList, new TypeToken<ConcurrentLinkedQueue<String>>() {}.getType()));
	}
	
	public void addRailEdgeId(String railEdgeId) {		
		this.getRailEdgeIdList().add(railEdgeId);
//		AtlasCommPubSub.getInstance().publishIfDataMaker(JsonUtil.getJsonCmdString(ActionType.ADD_COLLECTION_ITEM, getClass().getName(), "railEdgeIdList", this.id, railEdgeId, new TypeToken<String>() {}.getType()));
	}

	public String getMcpName() {
		return mcpName;
	}

	public void setMcpName(String mcpName) {
		this.mcpName = mcpName;
	}
}
