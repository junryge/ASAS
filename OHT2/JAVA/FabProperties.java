public class FabProperties {
    String fabId                                             = "";    // M14A
    String facId                                             = "";    // M14
    String mcpName                                            = "";    // A
    String mapDir                                             = "";
    Map<String,Set<String>> bridgeFromSet                     = new HashMap<>();
    Map<String, McpProperties> mcpPropertiesMap             = new HashMap<>();
    Map<String, String> mcpName2OhtNameMap                     = new HashMap<>();
    Map<String, String> ohtName2McpNameMap                     = new HashMap<>();

    // tib/rv - send
    // (1) star
    int sendStarGid = -1;
    String sendStarService = "";
    String sendStarNetwork = "";
    String sendStarDaemon = "";
    String sendStarSubject = "";

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

    // # sender
    // ##1 gid(=group id) → service, network 호출
    public int getSendStarGid() {
        return sendStarGid;
    }

    public int getRevMhsGid() {
        return revMhsGid;
    }

    public int getRevMcsGid() {
        return revMcsGid;
    }

    public void setSendStarGid(Integer sendStarGid) {
        this.sendStarGid = sendStarGid;
    }

    public void setRevMhsGid(Integer revMhsGid) {
        this.revMhsGid = revMhsGid;
    }

    public void setRevMcsGid(Integer revMcsGid) {
        this.revMcsGid = revMcsGid;
    }
    //~##1 gid
   
    // ##2 service
    public String getSendStarService() {
        return sendStarService;
    }

    public String getRevMhsService() {
        return revMhsService;
    }

    public String getRevMcsService() {
        return revMcsService;
    }

    public void setSendStarService(String sendStarService) {
        this.sendStarService = sendStarService;
    }

    public void setRevMhsService(String revMhsService) {
        this.revMhsService = revMhsService;
    }

    public void setRevMcsService(String revMcsService) {
        this.revMcsService = revMcsService;
    }
    //~##2 service

    // ##3 network
    public String getSendStarNetwork() {
        return sendStarNetwork;
    }

    public String getRevMhsNetwork() {
        return revMhsNetwork;
    }

    public String getRevMcsNetwork() {
        return revMcsNetwork;
    }

    public void setSendStarNetwork(String sendStarNetwork) {
        this.sendStarNetwork = sendStarNetwork;
    }

    public void setRevMhsNetwork(String revMhsNetwork) {
        this.revMhsNetwork = revMhsNetwork;
    }

    public void setRevMcsNetwork(String revMcsNetwork) {
        this.revMcsNetwork = revMcsNetwork;
    }
    //~##3 network

    // ##4 daemon
    public String getSendStarDaemon() {
        return sendStarDaemon;
    }

    public String getRevMhsDaemon() {
        return revMhsDaemon;
    }

    public String getRevMcsDaemon() {
        return revMcsDaemon;
    }

    public void setSendStarDaemon(String sendStarDaemon) {
        this.sendStarDaemon = sendStarDaemon;
    }

    public void setRevMcsDaemon(String revMcsDaemon) {
        this.revMcsDaemon = revMcsDaemon;
    }

    public void setRevMhsDaemon(String revMhsDaemon) {
        this.revMhsDaemon = revMhsDaemon;
    }
    //~##4 daemon

    // ##5 subject
    public String getSendStarSubject() {
        return sendStarSubject;
    }

    public String getRevMhsSubject() {
        return revMhsSubject;
    }

    public String getRevMcsSubject() {
        return revMcsSubject;
    }

    public void setSendStarSubject(String sendStarSubject) {
        this.sendStarSubject = sendStarSubject;
    }

    public void setRevMhsSubject(String revMhsSubject) {
        this.revMhsSubject = revMhsSubject;
    }

    public void setRevMcsSubject(String revMcsSubject) {
        this.revMcsSubject = revMcsSubject;
    }
    //~##5 subject

    public String getMcpName() {
        return mcpName;
    }
       
    public void setMcpName(String mcpName) {
        this.mcpName = mcpName;
    }
}
