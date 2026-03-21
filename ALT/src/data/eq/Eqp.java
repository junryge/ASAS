public class Eqp {
	protected String fabId;
	protected String id;
	protected String name;
	protected EQP_TYPE eqpType;
	protected Set<PROCESS_TYPE> processTypeSet;
	protected ConcurrentLinkedQueue<String> portNodeIdList;
	protected boolean isAvailable;
	private String firstPortNodeId 							= "";
	private String lastPortNodeId 							= "";
	protected transient boolean isUpdate;
	protected Set<String> mcpNameSet 						= new HashSet<>();
	protected Set<String> connectedFabMcpSet 				= new HashSet<>();
	protected String detEqpTyp 								= "";
	protected String eqpGrpNm 								= "";
	protected String mcsBayNm;
	
	public Eqp(
				String fabId, 
				String id, 
				String name, 
				EQP_TYPE eqpType, 
				Set<PROCESS_TYPE> processTypeSet, 
				ConcurrentLinkedQueue<String> portNodeIdList, 
				boolean isAvailable, 
				boolean isUpdate, 
				String mcsBayNm
	) {
		super();
		
		this.fabId 			= fabId;
		this.id 			= id;
		this.name 			= name;
		this.eqpType 		= eqpType;
		this.processTypeSet = processTypeSet;
		this.portNodeIdList = portNodeIdList;
		this.isAvailable 	= isAvailable;
		this.isUpdate 		= isUpdate;
		this.mcsBayNm 		= mcsBayNm;
	}
	
	public enum EQP_TYPE{STK, STBGROUP, EQP, FIO, OHT, CONVEYOR}

	public String getId() {
		return id;
	}

	public void setId(String id) {		
		this.id = id;
    }

	public EQP_TYPE getEqpType() {
		return eqpType;
	}

	public void setEqpType(EQP_TYPE eqpType) {
		this.eqpType = eqpType;
	}

	public Set<PROCESS_TYPE> getProcessTypeSet() {
		return processTypeSet;
	}

	public void setProcessTypeSet(Set<PROCESS_TYPE> processTypeSet) {
		this.processTypeSet = processTypeSet;
	}

	public ConcurrentLinkedQueue<String> getPortNodeIdList() {
		if (portNodeIdList == null) {
			portNodeIdList = new ConcurrentLinkedQueue<>();
		}
		
		return portNodeIdList;
	}

	public void setPortNodeIdList(ConcurrentLinkedQueue<String> portNodeIdList) {
		this.portNodeIdList = portNodeIdList;
	}

	public boolean isAvailable() {
		return isAvailable;
	}

	public void setAvailable(boolean isAvailable) {
		this.isAvailable = isAvailable;
	}

	public String toJsonString() {	
		return JsonUtil.convertJSON(this);
	}

	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}
	
	@Override
	public String toString() {
		return this.id;
	}

	public String getFabId() {
		return fabId;
	}

	public void setFabId(String fabId) {
		this.fabId = fabId;
	}
	
	public void removeCarrierId(String carrierId) {
		for (String portNodeId : this.portNodeIdList) {
			CarrierContainable cc = (CarrierContainable)DataService.getDataSet().getNodeMap().get(portNodeId);
			
			cc.removeCarrierId(carrierId);
		}
	}

	protected Logger getLogger() {
		return LoggerFactory.getLogger(getClass());
	}

	public void getFirstPortNodeId(DataSet ds) {
		if (StringUtils.isNotEmpty(this.firstPortNodeId)) {
			return;
		}
		
		if (this.portNodeIdList == null) {
			getLogger().error("{} portNodeIdList is null!", this.id);
			
			return;
		}
		
		List<String> orderedList = this.portNodeIdList.stream().sorted(Comparator.reverseOrder()).collect(Collectors.toList());
		
		for (String portNodeId : orderedList) {
			AbstractNode abstractNode = ds.getNodeMap().get(portNodeId);
			
			if (abstractNode != null) {
				if (abstractNode instanceof EqpPortNode && ((EqpPortNode) abstractNode).isInlinePort()) {
					continue;
				}
				
				this.setFirstPortNodeId(abstractNode.getId());
			}
		}

	}
	
	public String getAvailableFirstPortNodeId() {
		List<String> orderedList = this.portNodeIdList.stream().sorted(Comparator.reverseOrder()).collect(Collectors.toList());
		
		for (String portNodeId : orderedList) {
			AbstractNode abstractNode = DataService.getDataSet().getNodeMap().get(portNodeId);
			
			if (abstractNode != null && abstractNode.isAvailable()) {
				if (abstractNode instanceof EqpPortNode && ((EqpPortNode) abstractNode).isInlinePort()) {
					continue;
				}
				
				return portNodeId;
			}
		}
		
		return "";
	}
	
	public String getConnectedAnyRailNodeId() {
		for(String portNodeId : this.portNodeIdList) {
			AbstractNode abstractNode = DataService.getDataSet().getNodeMap().get(portNodeId);
			
			if (abstractNode != null) {
				Station station = DataService.getDataSet().getStationPortMap().get(abstractNode.getName());
				
				if (station != null && StringUtils.isNotEmpty(station.getRailEdgeId())) {
					RailEdge railEdge = DataService.getDataSet().getRailEdgeMap().get(station.getRailEdgeId());
					
					if (railEdge != null) {
						LongEdge longEdge = DataService.getDataSet().getLongEdgeMap().get(railEdge.getLongEdgeId());
						
						return longEdge.getFromNodeId();
					}
				}
			}
		}
		
		return "";
	}

	private void setFirstPortNodeId(String firstPortNodeId) {
		this.firstPortNodeId = firstPortNodeId;
	}
	
	public String getLastPortNodeId() {	
		if (StringUtils.isNotEmpty(this.lastPortNodeId)) {
			return this.lastPortNodeId;
		}
		
		List<String> orderedList = this.portNodeIdList.stream().sorted().collect(Collectors.toList());
		
		for (String portNodeId : orderedList) {
			AbstractNode an = DataService.getDataSet().getNodeMap().get(portNodeId);
			
			if (an != null) {
				if (an instanceof EqpPortNode && ((EqpPortNode)an).isInlinePort() == true) {
					continue;
				}
				
				setLastPortNodeId(an.getId());
			}
		}
		return this.lastPortNodeId;
	}
	
	private void setLastPortNodeId(String lastPortNodeId) {
		this.lastPortNodeId = lastPortNodeId;
	}

	public boolean isUpdate() {
		return isUpdate;
	}

	public void setUpdate(boolean isUpdate) {
		this.isUpdate = isUpdate;
	}
	
	public Set<String> getMcpNameSet(DataSet dataSet){
		mcpNameSet = new HashSet<>();
		
		if (this instanceof Oht) {			
			mcpNameSet.add(((Oht)this).getMcpName());
			
			return mcpNameSet;
		}
		
		for (String portNodeId : getPortNodeIdList()) {
			AbstractNode abstractNode = dataSet.getNodeMap().get(portNodeId);
			
			if (abstractNode instanceof EqpPortNode || abstractNode instanceof StbNode) {
				Station station = dataSet.getStationPortMap().get(abstractNode.getName());
				
				if(station != null) {
					mcpNameSet.add(station.getMcpName());
					
					return mcpNameSet;
				}				
			} else if (abstractNode instanceof RailNode) {
				RailNode railNode = (RailNode)abstractNode;
				
				mcpNameSet.add(railNode.getMcpName());
				
				return mcpNameSet;
			} else if (abstractNode instanceof FioPortNode) {
				FioPortNode fioPortNode = (FioPortNode)abstractNode;
				
				for (SubPort subPort : fioPortNode.getSubPortList()) {
					Station station = dataSet.getStationPortMap().get(subPort.name);
					
					if (station != null) {
						mcpNameSet.add(station.getMcpName());
						
						return mcpNameSet;
					}
				}
			} else if (abstractNode instanceof StkPortNode) {
				StkPortNode stkPortNode = (StkPortNode)abstractNode;
				
				for (com.skhynix.smartatlas.map.node.StkPortNode.SubPort subPort : stkPortNode.getSubPortList()) {
					Station station = dataSet.getStationPortMap().get(subPort.name);
					
					if (station != null) {
						mcpNameSet.add(station.getMcpName());
					}
				}
			} else if (abstractNode instanceof CnvPortNode) {
				CnvPortNode cnvPortNode = (CnvPortNode)abstractNode;
				
				if (
						cnvPortNode.getType() != CNV_NODE_TYPE.INPUT
						&& cnvPortNode.getType() != CNV_NODE_TYPE.OUTPUT
				) {
					continue;
				}
				
				Station station = dataSet.getStationPortMap().get(cnvPortNode.getName());
				
				if (station != null) {
					mcpNameSet.add(station.getMcpName());
				}
				
				if (mcpNameSet.size() > 1) {
					break;
				}
			}
		}
		
		return mcpNameSet;
	}
	
	public void getConnectedFabMcpSet(DataSet dataSet){
		connectedFabMcpSet = new HashSet<>();
		
		if (this instanceof Oht) {			
			connectedFabMcpSet.add(this.getFabId() + ":" + ((Oht)this).getMcpName());
			
			return;
		}
		
		for (String portNodeId : getPortNodeIdList()) {
			AbstractNode abstractNode = dataSet.getNodeMap().get(portNodeId);
			
			if (abstractNode instanceof EqpPortNode || abstractNode instanceof StbNode) {
				Station station = dataSet.getStationPortMap().get(abstractNode.getName());
				
				if (station != null) {
					connectedFabMcpSet.add(station.getFabId() + ":" + station.getMcpName());
					
					return;
				}				
			} else if (abstractNode instanceof RailNode) {
				RailNode railNode = (RailNode)abstractNode;
				
				connectedFabMcpSet.add(railNode.getFabId() + ":" + railNode.getMcpName());
				
				return;
			} else if (abstractNode instanceof FioPortNode) {
				FioPortNode fpn = (FioPortNode)abstractNode;
				
				for (SubPort subPort : fpn.getSubPortList()) {
					Station st = dataSet.getStationPortMap().get(subPort.name);
					
					if (st != null) {
						connectedFabMcpSet.add(st.getFabId() + ":" + st.getMcpName());
						
						return;
					}
				}
			} else if (abstractNode instanceof StkPortNode) {
				StkPortNode stkPortNode = (StkPortNode)abstractNode;
				
				for (com.skhynix.smartatlas.map.node.StkPortNode.SubPort subPort : stkPortNode.getSubPortList()) {
					Station station = dataSet.getStationPortMap().get(subPort.name);
					
					if (station != null) {
						connectedFabMcpSet.add(station.getFabId() + ":" + station.getMcpName());
					}
				}
			} else if (abstractNode instanceof CnvPortNode) {
				CnvPortNode cnvPortNode = (CnvPortNode)abstractNode;
				
				if (cnvPortNode.getType() != CNV_NODE_TYPE.INPUT && cnvPortNode.getType() != CNV_NODE_TYPE.OUTPUT) {
					continue;
				}
				
				Station station = dataSet.getStationPortMap().get(cnvPortNode.getName());
				
				if (station != null) {
					connectedFabMcpSet.add(station.getFabId() + ":" + station.getMcpName());
				}
				
				if (connectedFabMcpSet.size() > 1) {
					break;
				}
			}
		}
	}

	public Set<String> getConnectedFabMcpSet() {
		return connectedFabMcpSet;
	}

	public void setConnectedFabMcpSet(Set<String> connectedFabMcpSet) {
		this.connectedFabMcpSet = connectedFabMcpSet;
	}

	public String getDetEqpTyp() {
		return detEqpTyp;
	}

	public void setDetEqpTyp(String detEqpTyp) {
		this.detEqpTyp = detEqpTyp;
	}

	public String getEqpGrpNm() {
		return eqpGrpNm;
	}

	public void setEqpGrpNm(String eqpGrpNm) {
		this.eqpGrpNm = eqpGrpNm;
	}

	public String getMcsBayNm() {
		return mcsBayNm;
	}

	public void setMcsBayNm(String mcsBayNm) {
		this.mcsBayNm = mcsBayNm;
	}	
}
