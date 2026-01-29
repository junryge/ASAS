public class DijkstraVhlRouteFind {
    private final Logger logger = LoggerFactory.getLogger(getClass());
    Map <RailNode, ComparableRailNode> nodeToComparableMap;
    private RailNode destinationNode;
    private RailNode sourceNode;
    private Vhl vehicle;

    /**
     *
     * @param vehicle vehicle 정보
     * @param sourceNode 이전 및 최근 vehicle 이 위치 했던 railEdge 의 fromNode
     * @param destinationNode 현재 vehicle 이 위치한 railEdge 의 fromNode
     */
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
            logger.warn("... {} route getting failed, because source or destination node is null [source: {} | destination: {}]", vehicle.getId(), sourceNode, destinationNode);
        }
    }
   
    public ConcurrentLinkedQueue<RailEdge> getRailEdgeList() {
        ConcurrentLinkedQueue<RailEdge> reListToReturn = new ConcurrentLinkedQueue<>();
        PriorityQueue<ComparableRailNode> priorityQueue = new PriorityQueue<>();

        nodeToComparableMap.put(sourceNode, new ComparableRailNode(sourceNode, 0, true));

        priorityQueue.add(nodeToComparableMap.get(sourceNode));

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
                    logger.error("{} not registered edge on railNode : {}", vehicle.getId(), railNode.getId());

                    continue;
                }

                if (!railEdge.isAvailable()) {
                    // 단절된 경로는 차단
                    continue;
                }

                RailNode node = (RailNode) railEdge.getToNode();
                ComparableRailNode comparableRailNode = nodeToComparableMap.computeIfAbsent(
                        node,
                        _railNode -> new ComparableRailNode(_railNode, Double.POSITIVE_INFINITY, false)
                );

                if (!comparableRailNode.isVisited()) {
                    double newDistance = actualVertex.getCost() + railEdge.getVhlCountCost();

                    // 나중에 parameter 로 carrierId 와 직전 Edge 까지의 Cost 도 주자 (예상 경과 시점상 예측된 다른 Route 의 수량을 Cost 에 반영하기 위함)
                    // Carrier 종류에 따라 갈 수 있는 길인지 없는 길인지 판단 해야함.. Cost 로 반영
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
            logger.warn("... list of {} route failed to get. could not find route [source: {} | destination: {}]", vehicle.getId(), sourceNode.getId(), destinationNode.getId());

            return reListToReturn;
        }

        ConcurrentLinkedDeque<RailEdge> railEdgeList = new ConcurrentLinkedDeque<>();
        RailNode tdest = destinationNode;
        RailEdgePredecessor p;

        while((p = this.nodeToComparableMap.get(tdest).getPredecessor()) != null) {
            RailEdge railEdge = p.getRailEdge();

            railEdgeList.addFirst(railEdge);

            tdest = (RailNode) DataService.getDataSet().getNodeMap().get(railEdge.getFromNodeId());
        }

        reListToReturn.addAll(railEdgeList);

//        logger.info("... {} route list setting success [source: {} | destination: {}]", vehicle.getId(), sourceNode.getId(), destinationNode.getId());

        return reListToReturn;
    }
}