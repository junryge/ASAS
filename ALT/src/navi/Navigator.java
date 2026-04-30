public class Navigator {
	private final Logger logger 		= LoggerFactory.getLogger(Navigator.class);
	private Set<String> affectedRailSet	= new HashSet<>();
	private List<String> portSortedList	= new ArrayList<>();

	public Navigator(RailEdge railEdge) {
		this.searchRailAffected(railEdge);
	}

	private void initialize() {
		this.affectedRailSet.clear();
		this.portSortedList.clear();
	}

	public void searchRailAffected(RailEdge railEdge) {
		Set<String> addressSet 	= new HashSet<>();
		List<String> portList 	= new ArrayList<>();

		try {
			logger.info("[----] search rail affected with RAIL CUT [target address: {}]", railEdge.getAddress());

			if (!affectedRailSet.isEmpty() || !portSortedList.isEmpty()) {
				this.initialize();

				logger.info("... initialized and cleared navigation-related data");
			}

			ConcurrentHashMap<String, AbstractNode> nodeMap	= DataService.getDataSet().getNodeMap();

			String address					= railEdge.getAddress();
			String fromNodeId 				= railEdge.getFromNodeId();
			String toNodeId 				= railEdge.getToNodeId();
			AbstractNode abstractFromNode 	= nodeMap.get(fromNodeId);
			AbstractNode abstractToNode 	= nodeMap.get(toNodeId);

			this.affectedRailSet.add(address);

			if (abstractToNode instanceof RailNode) {
				RailNode toNode = (RailNode) abstractToNode;

				logger.info("[=---] tracking backward based on <to> node [<to> node address: {}]", toNode.getAddress());

				Item toItem = this._searchRailAffectedBasedOnToNode(toNode, new Item(), 0);

				if (toItem != null) {
					addressSet.addAll(toItem.getAddressSet());
					portList.addAll(toItem.getPortList());
				}

				logger.info("[#---] ... complete tracking and collection of <to> node [rail ({}) | port ({})]",
						toItem == null ? -1 : toItem.getAddressSet().size(),
						toItem == null ? -1 : toItem.getPortList().size()
				);
			} else {
				logger.error("[#---] ... invalid or unmatched <to> node type");
			}

			if (abstractFromNode instanceof RailNode) {
				RailNode fromNode = (RailNode) abstractFromNode;

				logger.info("[#=--] tracking forward based on <from> node [<from> node address: {}]", fromNode.getAddress());

				Item fromItem = this._searchRailAffectedBasedOnFromNode(fromNode, new Item(), 0);

				if (fromItem != null && !fromItem.getAddressSet().isEmpty()) {
					addressSet.addAll(fromItem.getAddressSet());
					portList.addAll(fromItem.getPortList());
				}

				logger.info("[##--] complete tracking and collection of <from> node [rail ({}) | port ({})]",
						fromItem == null ? -1 : fromItem.getAddressSet().size(),
						fromItem == null ? -1 : fromItem.getPortList().size()
				);
			} else {
				logger.error("[##--] invalid or unmatched <from> node type");
			}

			// railCut 영향도 조사 중 함께 적재한 port 정보(affectedPortSet)를 배열로 나열 후 `summarizePorts()`를 사용해 축약
			logger.info("[##=-] sort and abbreviate port collected while tracking through node [port affected ({})]", portList.size());

			if (!portList.isEmpty()) {
				Set<String> tmp = new HashSet<>(portList);

				if (tmp.size() != portList.size()) {
					portList = new ArrayList<>(tmp);
				}

				portList = DataSet.summarizePorts(portList);

				logger.info("[###-] completed sorting and abbreviate port [port abbreviated ({})]", portList.size());
			} else {
				logger.info("[###-] completed sorting and abbreviate port [port abbreviated is empty]");
			}
		} catch (Exception e) {
			logger.error("... an error occurred while searching for the affected rail [target address: {}]", railEdge.getAddress(), e);
		}

		this.affectedRailSet.addAll(addressSet);
		this.portSortedList.addAll(portList);

		logger.info("[####] collecting rail affected by railCut finished [rail ({}) | port ({})] [target address: {}]",
				addressSet.size(),
				portList.size(),
				railEdge.getAddress()
		);
	}

	// lanecut 영향 범위 추적 - 1
	private Item _searchRailAffectedBasedOnFromNode (
			RailNode fromNode,
			Item item,
			int overTrackCount
	) {
		/*
		 * from node 기준으로 진행의 역방향으로 범위를 추적
		 * 추적은 도달한 railNode 에서 분리되는 경우 (isRailBranch=true), 경로가 더 이상 존재하지 않는 경우에 종료
		 * 반환 값은 from, to 를 한 쌍 씩 이루는 값 (예: "1000:1001", "1001:1002"...)
		 */
		try {
			if (overTrackCount > 1000) {
				logger.warn("... overTrackCount is more than 1000 [<from> node address: {}]", fromNode.getAddress());

				return null;
			}

			if (fromNode.isRailBranch()) {
				return item;
			} else {
				// 병합되는 railNode (isRailJunction=true)이거나 일직선일 경우
				List<AbstractEdge> backwardEdges = DataService.getDataSet().getToNode2EdgeMap().get(fromNode.getId());

				for (AbstractEdge edge : backwardEdges) {
					if (edge instanceof RailEdge) {
						RailEdge backwardRailEdge = (RailEdge) edge;
						String backwardFromNodeId = backwardRailEdge.getFromNodeId();
						AbstractNode backwardFromNode = DataService.getDataSet().getNodeMap().get(backwardFromNodeId);

						if (backwardFromNode instanceof RailNode) {
							String address = backwardRailEdge.getAddress();

							item.addAddress(address);
							item.addPortList(backwardRailEdge.getPortIdList());

							_searchRailAffectedBasedOnFromNode((RailNode) backwardFromNode, item, overTrackCount++);
						}
					}
				}
			}
		} catch (Exception e) {
			logger.error("... an error occurred while searching rail affected base on <from> node [<from> node address: {}]", fromNode.getAddress(), e);
		}

		return item;
	}

	// lanecut 영향 범위 추적 - 2
	private Item _searchRailAffectedBasedOnToNode (
			RailNode toNode,
			Item item,
			int overTrackCount
	) {
		/*
		 * to node 기준으로 진행의 정방향으로 범위를 추적
		 * 추적은 도달한 railNode 에서 병합되는 경우 (isRailJunction=true), 경로가 더 이상 존재하지 않는 경우에 종료
		 * 반환 값은 from, to 를 한 쌍 씩 이루는 값 (예: "1000:1001", "1001:1002"...)
		 */
		try {
			if (overTrackCount > 1000) {
				logger.warn("... overTrackCount is more than 1000 [<to> node address: {}]", toNode.getAddress());

				return null;
			}

			if (toNode.isRailJunction()) {
				return item;
			} else {
				// 분리되는 railNode (isRailBranch=true)이거나 일직선일 경우
				List<AbstractEdge> forwardEdges = DataService.getDataSet().getFromNode2EdgeMap().get(toNode.getId());

				for (AbstractEdge edge : forwardEdges) {
					if (edge instanceof RailEdge) {
						RailEdge forwardRailEdge = (RailEdge) edge;
						String forwardToNodeId = forwardRailEdge.getToNodeId();
						AbstractNode forwardToNode = DataService.getDataSet().getNodeMap().get(forwardToNodeId);

						if (forwardToNode instanceof RailNode) {
							String address = forwardRailEdge.getAddress();

							item.addAddress(address);
							item.addPortList(forwardRailEdge.getPortIdList());

							_searchRailAffectedBasedOnToNode((RailNode) forwardToNode, item, overTrackCount++);
						}
					}
				}
			}
		} catch (Exception e) {
			logger.error("... an error occurred while searching rail affected base on <to> node [<to> node address: {}]", toNode.getAddress(), e);
		}

		return item;
	}
	//~lanecut 영향 범위 추적

	public Set<String> getAffectedRailSet () {
		return affectedRailSet;
	}

	public List<String> getAffectedPortSortedList () {
		return portSortedList;
	}

	private class Item {
		private final Set<String> addressSet = new HashSet<>();
		private final List<String> portList = new ArrayList<>();

		public Set<String> getAddressSet () {
			return this.addressSet;
		}

		public List<String> getPortList () {
			return this.portList;
		}

		public void addAddress (String address) {
			this.addressSet.add(address);
		}

		public void addPortList (List<String> port) {
			this.portList.addAll(port);
		}
	}
}
