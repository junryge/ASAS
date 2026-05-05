public class DijkstraVhlRouteFind {
	private final Logger logger = LoggerFactory.getLogger(getClass());
	Map <RailNode, ComparableRailNode> nodeToComparableMap;
	private final RailNode destinationNode;
	private final RailNode sourceNode;
	private final Vhl vehicle;

	public DijkstraVhlRouteFind(
			Vhl vehicle,
			RailNode sourceNode,
			RailNode destinationNode
	) {
		this.vehicle = vehicle;
		this.sourceNode = sourceNode;
		this.destinationNode = destinationNode;
		this.nodeToComparableMap = new HashMap<>();

		if (destinationNode ==  null || sourceNode == null) {
			logger.warn("{} route getting failed. source : {} or dest : {} is null", vehicle.getId(), sourceNode, destinationNode);
		}
	}
	
	public ConcurrentLinkedQueue<RailEdge> getRailEdgeList() {
		ConcurrentLinkedQueue<RailEdge> reListToReturn = new ConcurrentLinkedQueue<>();
		PriorityQueue<ComparableRailNode> priorityQueue = new PriorityQueue<>();

		// init
		ComparableRailNode comparableRailNode = new ComparableRailNode(sourceNode, 0, true);

		nodeToComparableMap.put(sourceNode, comparableRailNode);

		priorityQueue.add(comparableRailNode);
		//~init

		while(!priorityQueue.isEmpty()) {
			// Getting the minimum distance vertex from priority queue
			ComparableRailNode actualVertex = priorityQueue.poll();

			if (actualVertex.getNode().equals(destinationNode)) {
				// 목적지 까지의 경로를 찾음
				break;
			}

			RailNode railNode = actualVertex.getNode();

			for (RailEdge railEdge : railNode.getToRailEdges()) {
				if (railEdge == null) {
					logger.error("{} Not registered edge on rn : {}", vehicle.getId(), railNode.getId());

					continue;
				}

				if (!railEdge.isAvailable()) {
					// 단절된 경로는 차단
					continue;
				}

				RailNode node = (RailNode) railEdge.getToNode();
				//@
				comparableRailNode = nodeToComparableMap.computeIfAbsent(
						node,
						_railNode -> new ComparableRailNode(_railNode, Double.POSITIVE_INFINITY, false)
				);

				if (!comparableRailNode.isVisited()) {
					double eco = railEdge.getVhlCountCost();
					double newDistance = actualVertex.getCost() + eco;

					// 나중에 parameter로 carrierId와 직전 Edge까지의 Cost도 주자(예상 경과시점상 예측된 다른 Route의 수량을 Cost에 반영하기 위함.)
					//CarrierId는 뭐에 쓸려고 했더라???.. 아 맞다. Carrier 종류에 따라 갈 수 있는 길인지 없는 길인지 판단 해야함.. Cost로 반영.
					if (newDistance < comparableRailNode.getCost()){
						priorityQueue.remove(comparableRailNode);

						comparableRailNode.setCost(newDistance);
						comparableRailNode.setPredecessor(new RailEdgePredecessor(railEdge, newDistance));

						priorityQueue.add(comparableRailNode);
					}
				}
			}

			actualVertex.setVisited(true);
		}

		if (this.nodeToComparableMap.get(destinationNode) == null) {
//			logger.warn("{} route list failed to get. could not find route. source : {}, dest : {}", vehicle.getId(), sourceNode.getId(), destinationNode.getId());

			return reListToReturn;
		}

		ConcurrentLinkedDeque<RailEdge> reList = new ConcurrentLinkedDeque<>();
		RailNode tdest = destinationNode;
		RailEdgePredecessor p;

		while((p = this.nodeToComparableMap.get(tdest).getPredecessor()) != null) {
			RailEdge railEdge = p.getRailEdge();

			reList.addFirst(railEdge);

			tdest = (RailNode) DataService.getDataSet().getNodeMap().get(railEdge.getFromNodeId());
		}

		reListToReturn.addAll(reList);

		logger.debug("{} route list setting success. source : {}, dest : {}", vehicle.getId(), sourceNode.getId(), destinationNode.getId());

		return reListToReturn;
	}

}
