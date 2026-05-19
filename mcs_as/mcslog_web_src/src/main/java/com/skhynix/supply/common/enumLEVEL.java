package com.skhynix.supply.common;


public enum enumLEVEL {
	ALL("ALL")		 
	, DEBUG("DEBUG")	 
	, INFO("INFO")	 
	, FINE("FINE")	 
	, WELL("WELL")	 
	, WARN("WARN")	 
	, ERROR("ERROR") 
	, FATAL("FATAL");
	
	private String sLEVEL;
	
	enumLEVEL(String sLevel) 	{ this.sLEVEL = sLevel; }
	public String getLEVEL() 	{ return this.sLEVEL;   }
 
};
