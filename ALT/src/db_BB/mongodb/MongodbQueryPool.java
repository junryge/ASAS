public class MongodbQueryPool {
	private static final Logger logger = LoggerFactory.getLogger(MongodbQueryPool.class);
	
	private static Object _AcesssLock = new Object();
	private static Element _QueryPool;
	
	private static Element getQueryPool() {
		if (_QueryPool == null) {
			synchronized (_AcesssLock) {
				if (_QueryPool != null) {
					return _QueryPool;
				}
				
				try {
					_QueryPool = new SAXBuilder().build(new File("repository/dataaccessfx/mongodb.xml")).getRootElement().getChild("Queries");
				} catch (Exception e) {
					logger.error("", e);
					_QueryPool = null;
				}
			}
		}
		
		return _QueryPool;
	}
	
	private static void performTag(Element element, HashMap<String, Object> arguments) {
		for (Element childTag : element.getChildren().toArray(new Element[0])) {
			boolean isDetached = false;
			
			switch (childTag.getName()) {
				case "If":
				{
					String attrKey = childTag.getAttributeValue("Key");
					String attrValue = childTag.getAttributeValue("Value");
					
					if (arguments.get(attrKey) == null
							|| attrValue.equals(arguments.get(attrKey).toString()) == false) {
						isDetached = true;
					}
					
					break;
				}
				case "IfNotBlank":
				{
					String attrKey = childTag.getAttributeValue("Key");
					
					if (arguments.get(attrKey) == null
							|| StringUtils.isBlank(arguments.get(attrKey).toString())) {
						isDetached = true;
					}
					
					break;
				}
			}
			
			if (isDetached == true) {
				childTag.detach();
				continue;
			}
			
			if (childTag.getChildren().size() != 0) {
				performTag(childTag, arguments);
			}
		}
	}
	
	public static String getQuery(String id, HashMap<String, Object> arguments) {
		Element queryTree = getQueryPool().getChild(id).clone();
		
		performTag(queryTree, arguments);
		
		String query = queryTree.getValue();
		
		for (var entry : arguments.entrySet()) {
			Object value = entry.getValue() == null ? "" : entry.getValue();
			
			query = query.replace(String.format("#{%s}", entry.getKey()), String.format("'%s'", value));
			query = query.replace(String.format("${%s}", entry.getKey()), String.format("%s", value));
		}
		
		return query;
	}
}
