package com.skhynix.smartatlas.db.mongodb;

import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import org.bson.BsonArray;
import org.bson.BsonValue;
import org.bson.Document;
import org.bson.conversions.Bson;

import com.mongodb.ExplainVerbosity;
import com.mongodb.client.AggregateIterable;
import com.mongodb.client.model.Collation;

public class MongodbAggregateLinq extends MongodbLinq<AggregateIterable<Document>> {
	public MongodbAggregateLinq(BsonArray query, AggregateIterable<Document> iterable) {
		super("[" + String.join(",", query.stream().map(v -> v.toString()).collect(Collectors.toList())) + "]", iterable);
	}

	public void toCollection() {
		_Iterable.toCollection();
	}

	public MongodbAggregateLinq allowDiskUse(Boolean allowDiskUse) {
		_Iterable = _Iterable.allowDiskUse(allowDiskUse);
		
		return this;
	}
	
	public MongodbAggregateLinq maxTime(long maxTime, TimeUnit timeUnit) {
		_Iterable = _Iterable.maxTime(maxTime, timeUnit);
		
		return this;
	}

	public MongodbAggregateLinq maxAwaitTime(long maxAwaitTime, TimeUnit timeUnit) {
		_Iterable = _Iterable.maxAwaitTime(maxAwaitTime, timeUnit);
		
		return this;
	}

	public MongodbAggregateLinq bypassDocumentValidation(Boolean bypassDocumentValidation) {
		_Iterable = _Iterable.bypassDocumentValidation(bypassDocumentValidation);
		
		return this;
	}

	public MongodbAggregateLinq collation(Collation collation) {
		_Iterable = _Iterable.collation(collation);
		
		return this;
	}

	public MongodbAggregateLinq comment(String comment) {
		_Iterable = _Iterable.comment(comment);
		
		return this;
	}

	public MongodbAggregateLinq comment(BsonValue comment) {
		_Iterable = _Iterable.comment(comment);
		
		return this;
	}

	public MongodbAggregateLinq hint(Bson hint) {
		_Iterable = _Iterable.hint(hint);
		
		return this;
	}

	public MongodbAggregateLinq hintString(String hint) {
		_Iterable = _Iterable.hintString(hint);
		
		return this;
	}

	public MongodbAggregateLinq let(Bson variables) {
		_Iterable = _Iterable.let(variables);
		
		return this;
	}

	public Document explain() {
		return _Iterable.explain();
	}

	public Document explain(ExplainVerbosity verbosity) {
		return _Iterable.explain(verbosity);
	}

	public <E> E explain(Class<E> explainResultClass) {
		return _Iterable.explain(explainResultClass);
	}

	public <E> E explain(Class<E> explainResultClass, ExplainVerbosity verbosity) {
		return _Iterable.explain(explainResultClass, verbosity);
	}
}
