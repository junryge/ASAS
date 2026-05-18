/*
 * Copyright (c) SK Hynix Inc.
 * All right reserved.
 *
 * This software is the confidential and proprietary information of SK Hynix.
 * You shall not disclose such Confidential Information and
 * shall use it only in accordance with the terms of the license agreement
 * you entered into with SK Hynix Inc.
 */
package com.skhynix.smartatlas.map;

import com.skhynix.smartatlas.data.raw.RawLabel;

/**
 * A class is a label to display on the map.
 * The data for this is from a RawLabel
 * <pre>
 * com.skhynix.smartatlas.map|Label.java
 * </pre>
 * 
 * @author       : dongkun.yoo@partner.sk.com
 * @since        : 2020. 8. 05. 오전 09:55:00
 * @see 
 */
public class Label {
	private final String id;
	private final String mcpName;
	private final int address;
	private final double x;
	private final double y;
	private final String label;
	
	public Label(final String id, final String mcpName, final RawLabel rawLabel) {
		super();

		this.mcpName = mcpName;
		this.address = rawLabel.getAddress();
		this.x = rawLabel.getX();
		this.y = rawLabel.getY();
		this.label = rawLabel.getLabel();
		this.id = id;
	}
	
	/**
	 * Returns an Id for this label.
	 * @return String
	 */
	public String getId() {
		return this.id;
	}
	
	/**
	 * Returns an address for this label.
	 * @return int 
	 */
	public int getAddress() {
		return this.address;
	}

	/**
	 * Returns a x-coordinate this label will be positioned.
	 * @return double 
	 */
	public double getX() {
		return this.x;
	}

	/**
	 * Returns a y-coordinate this label will be positioned.
	 * @return double 
	 */
	public double getY() {
		return this.y;
	}

	/**
	 * Returns a label string to be shown.
	 * @return String
	 */
	public String getLabel() {
		return this.label;
	}

	public String getMcpName() {
		return mcpName;
	}
}
