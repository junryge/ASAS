package com.skhynix.smartatlas.queryformat.type;

public class FormatQueryCondition {
	public final String condition;
	public final ENUM_FULLTEXT_COND isFulltextCondition;
	
	public FormatQueryCondition(String condition) {
		this.condition = condition;
		this.isFulltextCondition = null;
	}
	
	public FormatQueryCondition(String condition, ENUM_FULLTEXT_COND isFulltextCondition) {
		this.condition = condition;
		this.isFulltextCondition = isFulltextCondition;
	}
	
	@Override
	public String toString() {
		return this.condition;
	}
}