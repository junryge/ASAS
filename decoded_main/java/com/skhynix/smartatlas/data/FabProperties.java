package com.skhynix.smartatlas.data;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

import com.skhynix.smartatlas.listener.CnvSocketIOListener;
import com.skhynix.smartatlas.listener.AmpListener;

public class FabProperties {
	String fabId 											= "";	// M14A
	String facId 											= "";	// M14
	String mcpName											= "";	// A
	String mapDir 											= "";
	Map<String, Set<String>> bridgeFromSet 					= new HashMap<>();
	Map<String, Set<String>> bridgeToSet 					= new HashMap<>();
	Map<String, Set<String>> inlineConnectSet 				= new HashMap<>();
	Map<String, McpProperties> mcpPropertiesMap 			= new HashMap<>();
	Map<String, String> mcpName2OhtNameMap 					= new HashMap<>();
	Map<String, String> ohtName2McpNameMap 					= new HashMap<>();
	Map<String, String> cnvToApiUrl 						= new HashMap<String, String>();	// cnv
	Map<String, CnvSocketIOListener> cnvSocketIOListenerMap = new HashMap<String, CnvSocketIOListener>();
	String cnvDaemon 										= "";
	String cnvSubject										= "";
	AmpListener ampListener						= null;
	String agvDaemon 										= "";	// AGV Daemon
	String agvSubject 										= "";	// AGV Subject
	
	// tib/rv - send
	// (1) star
	int sendStarGid = -1;
	String sendStarService = "";
	String sendStarNetwork = "";
	String sendStarDaemon = "";
	String sendStarSubject = "";
	// (2) amos
	int sendAmosGid = -1;
	String sendAmosService = "";
	String sendAmosNetwork = "";
	String sendAmosDaemon = "";
	String sendAmosSubject = "";

	// tib/rv - receive
	// (1) mhs
	int revMhsGid = -1;
	String revMhsService = "";
	String revMhsNetwork = "";
	String revMhsSubject = "";
	String revMhsDaemon = "";
	// (2) mcs
	int revMcsGid = -1;
	String revMcsService = "";
	String revMcsNetwork = "";
	String revMcsSubject = "";
	String revMcsDaemon = "";
	// (3) ui
	int revUiGid = -1;
	String revUiService = "";
	String revUiNetwork = "";
	String revUiSubject = "";
	String revUiDaemon = "";

	public FabProperties() {}
	
	public String getFabId() {
		return fabId;
	}
	
	public void setFabId(String fabId) {
		this.fabId = fabId;
	}	
	
	public String getMapDir() {
		return mapDir;
	}
	
	public void setMapDir(String mapDir) {
		this.mapDir = mapDir;
	}

	public String getFacId() {
		return facId;
	}
	
	public void setFacId(String facId) {
		this.facId = facId;
	}

	
	public Map<String, Set<String>> getBridgeFromSet() {
		return bridgeFromSet;
	}
	
	public void setBridgeFromSet(Map<String, Set<String>> bridgeFromSet) {
		this.bridgeFromSet = bridgeFromSet;
	}
	
	public Map<String, Set<String>> getBridgeToSet() {
		return bridgeToSet;
	}
	
	public void setBridgeToSet(Map<String, Set<String>> bridgeToSet) {
		this.bridgeToSet = bridgeToSet;
	}
	
	public Map<String, Set<String>> getInlineConnectSet() {
		return inlineConnectSet;
	}
	
	public void setInlineConnectSet(Map<String, Set<String>> inlineConnectSet) {
		this.inlineConnectSet = inlineConnectSet;
	}
	
	public Map<String, McpProperties> getMcpPropertiesMap() {
		return mcpPropertiesMap;
	}
	
	public void setMcpPropertiesMap(Map<String, McpProperties> mcpPropertiesMap) {
		this.mcpPropertiesMap = mcpPropertiesMap;
	}
	
	public Map<String, String> getMcpName2OhtNameMap() {
		return mcpName2OhtNameMap;
	}

	public Map<String, String> getOhtName2McpNameMap() {
		return ohtName2McpNameMap;
	}
	
	// cnv
	public Map<String, String> getConveyorToApiUrl() {
		return cnvToApiUrl;
	}
	public void setConveyorToApiUrl(Map<String, String> cnv2ApiUrl) {
		this.cnvToApiUrl = cnv2ApiUrl;
	}
	//
	public String getConveyorDaemon() {
		return cnvDaemon;
	}
	public void setConveyorDaemon(String cnvDaemon) {
		this.cnvDaemon = cnvDaemon;
	}
	//
	public String getConveyorSubject() {
		return cnvSubject;
	}
	public void setConveyorSubject(String cnvSubject) {
		this.cnvSubject = cnvSubject;
	}
	//
	public Map<String, CnvSocketIOListener> getCnvSocketIOListenerMap() {
		return cnvSocketIOListenerMap;
	}
	public void setCnvSocketIOListenerMap(Map<String, CnvSocketIOListener> cnvSocketIOListenerMap) {
		this.cnvSocketIOListenerMap = cnvSocketIOListenerMap;
	}
	public AmpListener getAmpListener() {
		return ampListener;
	}
	public void setAmpListener(AmpListener ampListener) {
		this.ampListener = ampListener;
	}
	public String getAgvDaemon() {
		return agvDaemon;
	}
	public void setAgvDaemon(String daemon) {
		this.agvDaemon = daemon;
	}
	public String getAgvSubject() {
		return agvSubject;
	}
	public void setAgvSubject(String subject) {
		this.agvSubject = subject;
	}	
	
	// # sender
	// ##1 gid(=group id) → service, network 호출
	public int getSendStarGid() {
		return sendStarGid;
	}
	
	public int getSendAmosGid() {
		return sendAmosGid;
	}

	public int getRevMhsGid() {
		return revMhsGid;
	}

	public int getRevMcsGid() {
		return revMcsGid;
	}
	
	public int getRevUiGid() {
		return revUiGid;
	}
	
	public void setSendStarGid(Integer sendStarGid) {
		this.sendStarGid = sendStarGid;
	}
	
	public void setSendAmosGid(Integer sendAmosGid) {
		this.sendAmosGid = sendAmosGid;
	}

	public void setRevMhsGid(Integer revMhsGid) {
		this.revMhsGid = revMhsGid;
	}

	public void setRevMcsGid(Integer revMcsGid) {
		this.revMcsGid = revMcsGid;
	}
	
	public void setRevUiGid(Integer revUiGid) {
		this.revUiGid = revUiGid;
	}
	//~##1 gid
	
	// ##2 service
	public String getSendStarService() {
		return sendStarService;
	}

	public String getSendAmosService() {
		return sendAmosService;
	}
	public String getRevMhsService() {
		return revMhsService;
	}

	public String getRevMcsService() {
		return revMcsService;
	}
	
	public String getRevUiService() {
		return revUiService;
	}

	public void setSendStarService(String sendStarService) {
		this.sendStarService = sendStarService;
	}
	
	public void setSendAmosService(String sendAmosService) {
		this.sendAmosService = sendAmosService;
	}

	public void setRevMhsService(String revMhsService) {
		this.revMhsService = revMhsService;
	}

	public void setRevMcsService(String revMcsService) {
		this.revMcsService = revMcsService;
	}
	
	public void setRevUiService(String revUiService) {
		this.revUiService = revUiService;
	}	
	//~##2 service

	// ##3 network
	public String getSendStarNetwork() {
		return sendStarNetwork;
	}
	
	public String getSendAmosNetwork() {
		return sendAmosNetwork;
	}

	public String getRevMhsNetwork() {
		return revMhsNetwork;
	}

	public String getRevMcsNetwork() {
		return revMcsNetwork;
	}
	
	public String getRevUiNetwork() {
		return revUiNetwork;
	}

	public void setSendStarNetwork(String sendStarNetwork) {
		this.sendStarNetwork = sendStarNetwork;
	}
	
	public void setSendAmosNetwork(String sendAmosNetwork) {
		this.sendAmosNetwork = sendAmosNetwork;
	}

	public void setRevMhsNetwork(String revMhsNetwork) {
		this.revMhsNetwork = revMhsNetwork;
	}

	public void setRevMcsNetwork(String revMcsNetwork) {
		this.revMcsNetwork = revMcsNetwork;
	}
	
	public void setRevUiNetwork(String revUiNetwork) {
		this.revUiNetwork = revUiNetwork;
	}	
	//~##3 network

	// ##4 daemon
	public String getSendStarDaemon() {
		return sendStarDaemon;
	}
	
	public String getSendAmosDaemon() {
		return sendAmosDaemon;
	}

	public String getRevMhsDaemon() {
		return revMhsDaemon;
	}

	public String getRevMcsDaemon() {
		return revMcsDaemon;
	}
	
	public String getRevUiDaemon() {
		return revUiDaemon;
	}

	public void setSendStarDaemon(String sendStarDaemon) {
		this.sendStarDaemon = sendStarDaemon;
	}
	
	public void setSendAmosDaemon(String sendAmosDaemon) {
		this.sendAmosDaemon = sendAmosDaemon;
	}

	public void setRevMcsDaemon(String revMcsDaemon) {
		this.revMcsDaemon = revMcsDaemon;
	}

	public void setRevMhsDaemon(String revMhsDaemon) {
		this.revMhsDaemon = revMhsDaemon;
	}
	
	public void setRevUiDaemon(String revUiDaemon) {
		this.revUiDaemon = revUiDaemon;
	}
	//~##4 daemon

	// ##5 subject
	public String getSendStarSubject() {
		return sendStarSubject;
	}
	
	public String getSendAmosSubject() {
		return sendAmosSubject;
	}

	public String getRevMhsSubject() {
		return revMhsSubject;
	}

	public String getRevMcsSubject() {
		return revMcsSubject;
	}
	
	public String getRevUiSubject() {
		return revUiSubject;
	}

	public void setSendStarSubject(String sendStarSubject) {
		this.sendStarSubject = sendStarSubject;
	}
	
	public void setSendAmosSubject(String sendAmosSubject) {
		this.sendAmosSubject = sendAmosSubject;
	}

	public void setRevMhsSubject(String revMhsSubject) {
		this.revMhsSubject = revMhsSubject;
	}

	public void setRevMcsSubject(String revMcsSubject) {
		this.revMcsSubject = revMcsSubject;
	}
	
	public void setRevUiSubject(String revUiSubject) {
		this.revUiSubject = revUiSubject;
	}
	//~##5 subject

	public String getMcpName() {
		return mcpName;
	}
		
	public void setMcpName(String mcpName) {
		this.mcpName = mcpName;
	}
}