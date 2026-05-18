package com.skhynix.smartatlas.data.raw;

import com.skhynix.smartatlas.util.JsonToStringBuilder;

public class RawVhlSpeed {
	private int level;
	private double speed;
	
	public RawVhlSpeed(int level, double speed) {
		super();
		this.level = level;
		this.speed = speed;
	}
	public int getLevel() {
		return level;
	}
	public void setLevel(int level) {
		this.level = level;
	}
	public double getSpeed() {
		return speed;
	}
	public void setSpeed(double speed) {
		this.speed = speed;
	}
	@Override
	public String toString() {
		JsonToStringBuilder builder = new JsonToStringBuilder(this);
		builder.append("level", level);
		builder.append("speed", speed);
		return builder.toString();
	}


}
