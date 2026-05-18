/*
 * Copyright (c) SK Hynix Inc.
 * All right reserved.
 *
 * This software is the confidential and proprietary information of SK Hynix.
 * You shall not disclose such Confidential Information and
 * shall use it only in accordance with the terms of the license agreement
 * you entered into with SK Hynix Inc.
 */
package com.skhynix.smartatlas.data.raw;

import com.skhynix.smartatlas.util.JsonToStringBuilder;

/**
 * A class is a label to display on the map.
 * <pre>
 * com.skhynix.smartatlas.data.raw|RawLabel.java
 * </pre>
 * 
 * @author       : dongkun.yoo@partner.sk.com
 * @since        : 2020. 8. 04. 오전 17:00:00
 * @see 
 */
public class RawLabel {
	private final int address;
	private final double x;
	private final double y;
	private final String label;

	/**
	 * A constructor to set the fields.
	 * @param address
	 * @param x
	 * @param y
	 * @param label
	 */
	public RawLabel(final int address, final double x, final double y, final String label) {
		super();
		
		this.address = address;
		this.x = x;
		this.y = y;
		this.label = label;
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

	@Override
	public String toString() {
		JsonToStringBuilder builder = new JsonToStringBuilder(this);
		builder.append("address", address);
		builder.append("y", y);
		builder.append("x", x);
		builder.append("label", label);
		return builder.toString();
	}
}