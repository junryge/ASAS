package com.skhynix.smartatlas.queryformat.type;

import java.util.Map;

public class McslogTablesCollection {
	private final Map<String, Map<String, String>> _Tables;
	
	public McslogTablesCollection(Map<String, Map<String, String>> mapSiteFabTables) {
		_Tables = mapSiteFabTables;
	}
	
	public Map<String, String> get(String site) {
		return _Tables.get(site);
	}
	
	public String get(String site, String fab) {
		if (_Tables.get(site) == null) {
			return null;
		}
		
		return _Tables.get(site).get(fab);
	}
}
