public class UpdatingDbMasterDataBatch implements Job {
	private final Logger logger = LoggerFactory.getLogger(getClass());

	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		logger.info("Start UpdatingDbMasterDataBatch");
		
		try {
			for (String fab : Env.getMongodbPropertiesMap().keySet()) {
				String suffix = MongodbMcslogQuery.getSuffix(fab);
				
				HashMap<String, Object> args = new HashMap<String, Object>();
				args.put("MasterCollection", "master_" + suffix);
				args.put("Type", "TS_PROCESS");
				args.put("IsTS", "true");
				
				var bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_MASTER_PROCESS", args));
				
				MongodbAPI.aggregate(fab, "ts_data_" + suffix, bsonMatch).toList();
				
				args.put("Type", "CS_PROCESS");
				args.put("IsTS", "false");
				
				bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_MASTER_PROCESS", args));
				
				MongodbAPI.aggregate(fab, "cs_data_" + suffix, bsonMatch).toList();
				
				args.put("Type", "DS_PROCESS");
				
				bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_MASTER_PROCESS", args));
				
				MongodbAPI.aggregate(fab, "ds_data_" + suffix, bsonMatch).toList();
				
				args.put("Type", "EI_PROCESS");
				
				bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_MASTER_PROCESS", args));
				
				MongodbAPI.aggregate(fab, "ei_data_" + suffix, bsonMatch).toList();
				
				bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_MASTER_MACHINE", args));
				
				MongodbAPI.aggregate(fab, "secs_raw_" + suffix, bsonMatch).toList();
			}
		} catch (Exception e) {
			logger.error("", e);
		}
		
		logger.info("Completed UpdatingDbMasterDataBatch");
	}
}
