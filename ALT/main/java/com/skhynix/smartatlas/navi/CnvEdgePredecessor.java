package com.skhynix.smartatlas.navi;

import com.skhynix.smartatlas.map.edge.CnvEdge;

public class CnvEdgePredecessor {
	CnvEdge ce = null;
	double cost = 0;
	public CnvEdgePredecessor(CnvEdge ce, double cost) {
		this.ce = ce;
		this.cost = cost;
	}
	
	public double getCost() {
		return cost;
	}
	public void setCost(double cost) {
		this.cost = cost;
	}

	public CnvEdge getCe() {
		return ce;
	}

	public void setCe(CnvEdge ce) {
		this.ce = ce;
	}

}
