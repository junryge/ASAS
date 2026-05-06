public class MongodbAPI {
	private static final Logger logger = LoggerFactory.getLogger(MongodbAPI.class);
	private static final int TIMEOUT_MINUTE = 2;
	
	private static HashMap<String, MongoDatabase> _DatabasePool = new HashMap<String, MongoDatabase>();
	
	private static MongoDatabase getDatabase(String fab) {
		MongoDatabase database = _DatabasePool.get(fab);
		
		if (database != null) {
			return database;
		}
		
		DbProperties properties = Env.getMongodbPropertiesMap().get(fab);
		String dataBaseName = properties.getDatabase();
		String connectionString = "";
		String id = properties.getId();
		String password = "";
		
		try {
			password = URLEncoder.encode(CryptoUtil.decrypt(properties.getPassword(), Env.getMongodbDecryptKey()), "UTF-8");
		} catch (UnsupportedEncodingException e) {
			logger.error("", e);
		}
		
		connectionString = String.format("mongodb://%s:%s@", id, password); 
		
		for (String host : properties.getHosts()) {
			connectionString += String.format("%s:%s,", host, properties.getPort());
		}
		
		if (connectionString.endsWith(",")) {
			connectionString = connectionString.substring(0, connectionString.length() - 1);
		}
		
		connectionString += "/?authSource=mcslog";
		
		database = MongoClients.create(connectionString).getDatabase(dataBaseName);
		
		_DatabasePool.put(fab, database);
		
		return database; 
	}
	
	public static MongodbFindLinq find(String fab, String collection, Bson filter) {
		try {
			return new MongodbFindLinq(filter, getDatabase(fab).getCollection(collection).find(filter)
					.maxTime(TIMEOUT_MINUTE, TimeUnit.MINUTES).allowDiskUse(true));
		} catch (MongoCommandException commandException) {
			logger.error("", commandException);
		} catch (Exception e) {
			logger.error("", e);
		}
		
		return null;
	}
	
	public static MongodbAggregateLinq aggregate(String fab, String collection, BsonArray filter) {
		try {
			return new MongodbAggregateLinq(filter, getDatabase(fab).getCollection(collection).aggregate(
					filter.getValues()
						.stream()
						.map(v -> v.asDocument())
						.collect(Collectors.toList())))
					.maxTime(TIMEOUT_MINUTE, TimeUnit.MINUTES).allowDiskUse(true);
		} catch (MongoCommandException commandException) {
			logger.error("", commandException);
		} catch (Exception e) {
			logger.error("", e);
		}
		
		return null;
	}
	
	public static boolean insertMany(String fab, String collection, List<Document> documents, InsertManyOptions options) {
		try {
			getDatabase(fab).getCollection(collection).insertMany(documents, options);
			
			return true;
		} catch (MongoBulkWriteException e) {
			if (options.isOrdered()) {
				logger.error("", e);
			}
		} catch (Exception e) {
			logger.error("", e);
		}
		
		return false;
	}
}
