package com.skhynix.smartatlas.util;

import java.lang.reflect.Type;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.google.gson.Gson;
import com.google.gson.JsonElement;
import com.google.gson.reflect.TypeToken;
import com.logpresso.client.Tuple;

public class JsonUtil {
	private static final Logger logger = LoggerFactory.getLogger(JsonUtil.class);
    private static final Gson gson = new Gson();
	private static final Type MAPMAP = TypeToken.getParameterized(Map.class, String.class, TypeToken.getParameterized(Map.class, String.class, String.class).getType()).getType();

	public static Map<String, Map<String, String>> getMapMapFromJson(String json) {
		return gson.fromJson(json, MAPMAP);
	}
	
	static public String getJsonFromMapMap(Map<String, Map<String, String>> mapmap) {
		return gson.toJson(mapmap, MAPMAP);
	}
	
	//+
	private final ThreadLocal<Gson> tlsGson 	= new ThreadLocal<>();
	
	private static final Type TUPLEMAP = new TypeToken<Map<String, Object>>(){}.getType();

	/**
	 * The Gson isn't safe for the thread. 
	 * Manage a Gson with the TLS(thread local storage) 
	 * And return the Gson in the TLS.
	 * @return Gson
	 */
	public Gson gson() {
		Gson gson = this.tlsGson.get();
		
		if (gson == null) {
			this.tlsGson.set(gson = new Gson());
		}
		
		return gson;
	}
	
	private static class Singleton {
		private static final JsonUtil instance = new JsonUtil();
	}
	
	static public JsonUtil getInstance() {
		return Singleton.instance;
	}

	static public String convertJSON(Object object) {
		return Singleton.instance.gson().toJson(object);
	}

	static public JsonElement toJsonTree(Object object) {		
		return Singleton.instance.gson().toJsonTree(object);
	}
	
	static public Tuple getTupleByJsonElement(JsonElement je) {
		try {
			Map<String,Object> tplMap = Singleton.instance.gson().fromJson(je, TUPLEMAP);
			Tuple tpl = new Tuple(tplMap);
			return tpl;
		}catch(Exception e) {
			logger.error("JsonElement : {}",je, e);
		}
		return null;
	}
}
