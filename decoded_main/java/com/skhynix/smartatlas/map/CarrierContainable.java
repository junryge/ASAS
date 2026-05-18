package com.skhynix.smartatlas.map;

public interface CarrierContainable {
	public String getName();
	public String getId();
	public String getEqpId();
	public void addCarrierId(String carrierId);
	public void removeCarrierId(String carrierId);
	public String[] getCarrierIds();
}
