package com.skhynix.smartatlas.data;

import java.util.concurrent.ConcurrentLinkedQueue;

public class Bay {
	
	private String id 		= "";
	private String fabId 	= "";
	private String name 	= "";
	private ConcurrentLinkedQueue<String> railEdgeIdList = new ConcurrentLinkedQueue<String>();

	public String getId() {
		return id;
	}

	public void setId(String id) {
		this.id = id;
	}

	public Bay(String id, String fabId, String name, String mcpName) {
		super();
		
		this.id 	= id;
		this.fabId 	= fabId;
		this.name 	= name;
	}
	
	public Bay(String id, String fabId, String name, ConcurrentLinkedQueue<String> railEdgeIdList) {
		super();
		this.id 			= id;
		this.fabId 			= fabId;
		this.name 			= name;
		this.railEdgeIdList = railEdgeIdList;
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
	}
	
	public void addRailEdgeId(String railEdgeId) {		
		this.getRailEdgeIdList().add(railEdgeId);
	}
}
