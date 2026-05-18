package com.skhynix.smartatlas.navi;

import com.skhynix.smartatlas.map.edge.RailEdge;

public class RailEdgePredecessor {
	private final RailEdge railEdge;
	private final double cost;

	public RailEdgePredecessor(RailEdge re, double cost) {
		this.railEdge = re;
		this.cost = cost;
	}
	
	public double getCost() {
		return cost;
	}

	public RailEdge getRailEdge() {
		return railEdge;
	}
}
