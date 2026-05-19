package com.skhynix.supply.common;


public enum enumTYPE {
	ALL("ALL")
	, STOCKER("STOCKER")
	, STB("STB")
	, LIFTER("LIFTER")
	, CONVEYOR("CONVEYOR")
	, PROCESS("PROCESS")
	, OHT("OHT");
	
	private String sTYPE;
	
	enumTYPE(String sType) 		{ this.sTYPE = sType; }
	public String getTYPE() 	{ return this.sTYPE;  }
 
};