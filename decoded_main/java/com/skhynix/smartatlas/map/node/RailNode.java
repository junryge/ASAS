package com.skhynix.smartatlas.map.node;

import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;

import org.apache.commons.lang3.StringUtils;

import com.skhynix.smartatlas.map.AbstractNode;
import com.skhynix.smartatlas.map.edge.RailEdge;

public class RailNode extends AbstractNode {
	private double drawX;
	private double drawY;
	private double cadX;
	private double cadY;
	private double cadZ;
	private String eqpId 							= "";
	private boolean isRailBranch 					= false;
	private boolean isRailJunction 					= false;
	private String leftEdgeId;
	private String rightEdgeId;
	transient private Queue<RailEdge> toRailEdges 	= new ConcurrentLinkedQueue<>();
	private int address;

	public boolean changed(RailNode oe) {
		if (!this.eqpId.equals(oe.eqpId)) {
			return true;
		}
		
		if (this.drawX != oe.drawX) {
			return true;
		}
		
		if (this.drawY != oe.drawY) {
			return true;
		}
		
		if (this.cadX != oe.cadX) {
			return true;
		}
		
		if (this.cadY != oe.cadY) {
			return true;
		}
		
		if (this.cadZ != oe.cadZ) {
			return true;
		}
		
		if (this.isRailBranch != oe.isRailBranch) {
			return true;
		}
		
		if (this.isRailJunction != oe.isRailJunction) {
			return true;
		}
		
		if (!this.mcpName.equals(oe.mcpName)) {
			return true;
		}
		
		if (StringUtils.isNotEmpty(this.leftEdgeId) && !this.leftEdgeId.equals(oe.leftEdgeId)) {
			return true;
		}
		
		if (StringUtils.isNotEmpty(oe.leftEdgeId) && !oe.leftEdgeId.equals(this.leftEdgeId)) {
			return true;
		}
		
		if (StringUtils.isNotEmpty(this.rightEdgeId) && !this.rightEdgeId.equals(oe.rightEdgeId)) {
			return true;
		}
		
		if (StringUtils.isNotEmpty(oe.rightEdgeId) && !oe.rightEdgeId.equals(this.rightEdgeId)) {
			return true;
		}
		
		return super.changed(oe);
	}
	
	public RailNode(
					String fabId, 
					String id, 
					String name, 
					String mcpName,	
					double drawX,
					double drawY,
					double cadX,
					double cadY,
					double cadZ,
					boolean isUpdate, 
					String leftEdgeId, 
					String rightEdgeId,
					int address
	) {
		super(
				fabId,
				id,
				name,
				null,
				null,
				null,
				null,
				isUpdate
		);
		
		this.mcpName 		= mcpName;
		this.drawX 			= drawX;
		this.drawY 			= drawY;
		this.cadX 			= cadX;
		this.cadY 			= cadY;
		this.cadZ 			= cadZ;
		this.leftEdgeId 	= leftEdgeId;
		this.rightEdgeId 	= rightEdgeId;
		this.address		= address;
	}
	
	public double getDrawX() {
		return drawX;
	}

	public double getDrawY() {
		return drawY;
	}

	public double getCadX() {
		return cadX;
	}

	public double getCadY() {
		return cadY;
	}
	
	public double getCadZ() {
		return cadZ;
	}

	public void setDrawX(double drawX) {
		this.drawX = drawX;
		
		if (isUpdate) {
			return;
		}
	}

	public void setDrawY(double drawY) {
		this.drawY = drawY;
	}

	public void setCadX(double cadX) {
		this.cadX = cadX;
	}

	public void setCadY(double cadY) {
		this.cadY = cadY;
	}

	public void setCadZ(double cadZ) {
		this.cadZ = cadZ;
	}
	
	@Override
	public String getEqpId() {
		return this.eqpId;
	}

	@Override
	public void setEqpId(String eqpId) {
		this.eqpId = eqpId;
	}

	@Override
	public boolean isAvailable() {
		return true;
	}

	@Override
	public void setAvailable(boolean isAvailable) {}

	public boolean isRailBranch() {
		return isRailBranch;
	}

	public void setRailBranch(boolean isRailBranch) {
		this.isRailBranch = isRailBranch;
	}

	public boolean isRailJunction() {
		return isRailJunction;
	}

	public void setRailJunction(boolean isRailJunction) {
		this.isRailJunction = isRailJunction;
	}

	public String getMcpName() {
		return mcpName;
	}

	public void setMcpName(String mcpName) {
		this.mcpName = mcpName;
	}

	public String getLeftEdgeId() {
		return leftEdgeId;
	}

	public void setLeftEdgeId(String leftEdgeId) {
		this.leftEdgeId = leftEdgeId;
	}

	public String getRightEdgeId() {
		return rightEdgeId;
	}

	public void setRightEdgeId(String rightEdgeId) {
		this.rightEdgeId = rightEdgeId;
	}

	public Queue<RailEdge> getToRailEdges() {
		return toRailEdges;
	}

	public void setToRailEdges(Queue<RailEdge> toRailEdges) {
		this.toRailEdges = toRailEdges;
	}

	public int getAddress() {
		return address;
	}

	public void setAddress(int address) {
		this.address = address;
	}
}