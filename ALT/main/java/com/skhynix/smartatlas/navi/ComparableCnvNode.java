package com.skhynix.smartatlas.navi;

import com.skhynix.smartatlas.map.node.CnvPortNode;

public class ComparableCnvNode implements Comparable<ComparableCnvNode> {
	private double cost = 0;
	private CnvPortNode node = null;
	private boolean visited = false;
	private CnvEdgePredecessor predecessor = null;
	public ComparableCnvNode(CnvPortNode node, double cost, boolean visited) {
		this.node = node;
		this.cost = cost;
		this.visited = visited;
	}
	@Override
	public int compareTo(ComparableCnvNode o) {
		return Double.compare(this.cost, o.getCost());
	}
	public double getCost() {
		return cost;
	}
	public void setCost(double cost) {
		this.cost = cost;
	}
	public CnvPortNode getNode() {
		return node;
	}
	public void setNode(CnvPortNode node) {
		this.node = node;
	}
	public boolean isVisited() {
		return visited;
	}
	public void setVisited(boolean visited) {
		this.visited = visited;
	}
	public CnvEdgePredecessor getPredecessor() {
		return predecessor;
	}
	public void setPredecessor(CnvEdgePredecessor predecessor) {
		this.predecessor = predecessor;
	}

}
