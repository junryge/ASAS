package com.skhynix.smartatlas.data.raw;

public class RawEdge {
	final public int fromNode;
	final public int toNode;
	final public String railEdgeId;

	/**
	 * A constructor
	 * @param fromAddr
	 * @param toAddr
	 * @param railEdgeId
	 */
	public RawEdge(final int fromAddr, final int toAddr, final String railEdgeId) {
		this.fromNode 	= fromAddr;
		this.toNode 	= toAddr;
		this.railEdgeId = railEdgeId;
	}
}
