package com.skhynix.smartatlas.db.mongodb;

import java.util.concurrent.TimeUnit;

import org.bson.BsonValue;
import org.bson.Document;
import org.bson.conversions.Bson;

import com.mongodb.CursorType;
import com.mongodb.ExplainVerbosity;
import com.mongodb.client.FindIterable;
import com.mongodb.client.model.Collation;

public class MongodbFindLinq extends MongodbLinq<FindIterable<Document>> {
	public MongodbFindLinq(Bson query, FindIterable<Document> iterable) {
		super(query.toBsonDocument().toJson(), iterable);
	}
	
	public MongodbFindLinq filter(Bson filter) {
		_Iterable = _Iterable.filter(filter);
		
		return this;
	}

	public MongodbFindLinq limit(int limit) {
		_Iterable = _Iterable.limit(limit);
		
		return this;
	}

	public MongodbFindLinq skip(int skip) {
		_Iterable = _Iterable.skip(skip);
		
		return this;
	}

	public MongodbFindLinq maxTime(long maxTime, TimeUnit timeUnit) {
		_Iterable = _Iterable.maxTime(maxTime, timeUnit);
		
		return this;
	}

	public MongodbFindLinq maxAwaitTime(long maxAwaitTime, TimeUnit timeUnit) {
		_Iterable = _Iterable.maxAwaitTime(maxAwaitTime, timeUnit);
		
		return this;
	}

	public MongodbFindLinq projection(Bson projection) {
		_Iterable = _Iterable.projection(projection);
		
		return this;
	}

	public MongodbFindLinq sort(Bson sort) {
		_Iterable = _Iterable.sort(sort);
		
		return this;
	}

	public MongodbFindLinq noCursorTimeout(boolean noCursorTimeout) {
		_Iterable = _Iterable.noCursorTimeout(noCursorTimeout);
		
		return this;
	}

	@SuppressWarnings("deprecation")
	public MongodbFindLinq oplogReplay(boolean oplogReplay) {
		_Iterable = _Iterable.oplogReplay(oplogReplay);
		
		return this;
	}

	public MongodbFindLinq partial(boolean partial) {
		_Iterable = _Iterable.partial(partial);
		
		return this;
	}

	public MongodbFindLinq cursorType(CursorType cursorType) {
		_Iterable = _Iterable.cursorType(cursorType);
		
		return this;
	}

	public MongodbFindLinq collation(Collation collation) {
		_Iterable = _Iterable.collation(collation);
		
		return this;
	}

	public MongodbFindLinq comment(String comment) {
		_Iterable = _Iterable.comment(comment);
		
		return this;
	}

	public MongodbFindLinq comment(BsonValue comment) {
		_Iterable = _Iterable.comment(comment);
		
		return this;
	}

	public MongodbFindLinq hint(Bson hint) {
		_Iterable = _Iterable.hint(hint);
		
		return this;
	}

	public MongodbFindLinq hintString(String hint) {
		_Iterable = _Iterable.hintString(hint);
		
		return this;
	}

	public MongodbFindLinq let(Bson variables) {
		_Iterable = _Iterable.let(variables);
		
		return this;
	}

	public MongodbFindLinq max(Bson max) {
		_Iterable = _Iterable.max(max);
		
		return this;
	}

	public MongodbFindLinq min(Bson min) {
		_Iterable = _Iterable.min(min);
		
		return this;
	}

	public MongodbFindLinq returnKey(boolean returnKey) {
		_Iterable = _Iterable.returnKey(returnKey);
		
		return this;
	}

	public MongodbFindLinq showRecordId(boolean showRecordId) {
		_Iterable = _Iterable.showRecordId(showRecordId);
		
		return this;
	}

	public MongodbFindLinq allowDiskUse(Boolean allowDiskUse) {
		_Iterable = _Iterable.allowDiskUse(allowDiskUse);
		
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
