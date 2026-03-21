public class ComparableRailNode implements Comparable<ComparableRailNode> {
	private double cost;
	private RailNode node;
	private boolean visited;
	private RailEdgePredecessor predecessor = null;

	public ComparableRailNode(RailNode node, double cost, boolean visited) {
		this.node = node;
		this.cost = cost;
		this.visited = visited;
	}
	@Override
	public int compareTo(ComparableRailNode o) {
		return Double.compare(this.cost, o.getCost());
	}

	public double getCost() {
		return cost;
	}

	public void setCost(double cost) {
		this.cost = cost;
	}

	public RailNode getNode() {
		return node;
	}

	public void setNode(RailNode node) {
		this.node = node;
	}

	public boolean isVisited() {
		return visited;
	}

	public void setVisited(boolean visited) {
		this.visited = visited;
	}

	public RailEdgePredecessor getPredecessor() {
		return predecessor;
	}

	public void setPredecessor(RailEdgePredecessor predecessor) {
		this.predecessor = predecessor;
	}

}
