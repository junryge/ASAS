public class UpdatingDbMachineListBatch implements Job {
	private final Logger logger = LoggerFactory.getLogger(getClass());

	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		final var insertOptions = new InsertManyOptions().ordered(false);
		
		logger.info("Start UpdatingDbMachineListBatch");
		
		try {
			for (String fab : Env.getMongodbPropertiesMap().keySet()) {
				String suffix = MongodbMcslogQuery.getSuffix(fab);
				
				Map<String,String> queryParameter = new HashMap<String, String>();
				
				queryParameter.put("FABID", fab);
				
				//Machine List
				var factory = QueryExecutorFactory.getQueryExecutor(fab);
				var result = factory.selectDataTable("SELECT_MACHINE_LIST", queryParameter);
				var docList = new ArrayList<Document>();
				
				result.forEach(row -> docList.add(new Document(row.toMap())));
				
				MongodbAPI.insertMany(fab, "master_machine_list_"+ suffix, docList, insertOptions);
				
				docList.clear();
				
				//Machine TypeInfo
				result = factory.selectDataTable("SELECT_MACHINE_TYPEINFO", queryParameter);
				result.forEach(row -> docList.add(new Document(row.toMap())));
				
				MongodbAPI.insertMany(fab, "master_machine_typeinfo_"+ suffix, docList, insertOptions);
				
				docList.clear();
				
				//Unit List
				result = factory.selectDataTable("SELECT_UNIT_LIST", queryParameter);
				result.forEach(row -> docList.add(new Document(row.toMap())));
				
				MongodbAPI.insertMany(fab, "master_unit_list_"+ suffix, docList, insertOptions);
				
				docList.clear();
			}
		} catch (Exception e) {
			logger.error("", e);
		}
		
		logger.info("Completed UpdatingDbMachineListBatch");
	}
	
}
