package com.skhynix.smartatlas.queryformat.type;

public class ExtractCommonFilterResult {
	private final String _Site;
	private final String _Fab;
	private final String _Query;
	
	public ExtractCommonFilterResult(String site, String fab, String query) {
		_Site = site;
		_Fab = fab;
		_Query = query;
	}
	
	public String getSite() {
		return _Site;
	}
	
	public String getFab() {
		return _Fab;
	}
	
	public String getQuery() {
		return _Query;
	}
}