public class MongodbLinq<TIterable extends MongoIterable<Document>> {
	private static final Logger logger = LoggerFactory.getLogger(MongodbLinq.class);
	
	private String _BsonJson;
	protected TIterable _Iterable;
	
	public MongodbLinq(String bsonjson, TIterable iterable) {
		_BsonJson = bsonjson;
		_Iterable = iterable;
	}
	
	public MongoCursor<Document> iterator() {
		return _Iterable.iterator();
	}

	public MongoCursor<Document> cursor() {
		return _Iterable.cursor();
	}

	public Document first() {
		return _Iterable.first();
	}

	public <U> MongoIterable<U> map(Function<Document, U> mapper) {
		return _Iterable.map(mapper);
	}

	public <A extends Collection<? super Document>> A into(A target) {
		return _Iterable.into(target);
	}

	public MongodbLinq<MongoIterable<Document>> batchSize(int batchSize) {
		return new MongodbLinq<MongoIterable<Document>>(_BsonJson, _Iterable.batchSize(batchSize));
	}
	
	public List<Map<String, Object>> toList() {
		return toList(-1);
	}
	
	public List<Map<String, Object>> toList(int limit) {
		var result = limit >= 1 ? new ArrayList<Map<String, Object>>(limit) : new ArrayList<Map<String, Object>>();
		var newIterable = batchSize(limit >= 1 ? limit : 1)._Iterable;
		
		try {
			for (Document adapterRow : newIterable) {
				var row = new HashMap<String, Object>();

				for (var adapterColumn : adapterRow.entrySet()) {
					row.put(adapterColumn.getKey(), Objects.toString(adapterColumn.getValue(), ""));
				}
				
				result.add(row);
				
				if (result.size() == limit) {
					break;
				}
			}
		} catch (MongoInterruptedException e) {
		} catch (MongoExecutionTimeoutException e) {
		} catch (Exception e) {
			logger.error("", e);
		} finally {
			newIterable.cursor().close();
		}
		
		logger.info("Execution MongoDB Command : " + _BsonJson);
		
		return result;
	}
	
	public FutureTask<List<Map<String, Object>>> toListTask(int limit) {
		return new FutureTask<List<Map<String, Object>>>(() -> { 
			return toList(limit);
		});
	}
}
