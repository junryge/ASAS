public class AsyncUtil {
	private static Thread _CheckerThread;
	private static final Long _DefaultLifetime = 60 * 60 * 1000L;
	private static final Map<String, List<Map<String, Object>>> _AsyncResult = new ConcurrentHashMap<>();
	private static final Map<String, Long> _ResultLifetime = new ConcurrentHashMap<>();
	
	private static void startThread() {
		_CheckerThread = new Thread(() -> { 
			while (true) { 
				try {
					removeExpired();
					Thread.sleep(60000);
				} catch (Exception e) {}
			}
		});
		_CheckerThread.start();
	}
	
	private static void removeExpired() {
		var asyncKeys = _ResultLifetime.keySet().toArray(new String[0]);
		
		for (String asyncKey : asyncKeys) {
			if (System.currentTimeMillis() - _ResultLifetime.get(asyncKey) > _DefaultLifetime) {
				remove(asyncKey);
				System.out.println("Removed Async : " + asyncKey);
			}
		}
	}
	
	private static void extendLifetime(String asyncKey) {
		_ResultLifetime.put(asyncKey, System.currentTimeMillis());
	}
	
	public static List<Map<String, Object>> get(String asyncKey) {
		try {
			if (_AsyncResult.containsKey(asyncKey) == true) {
				extendLifetime(asyncKey);
				return _AsyncResult.get(asyncKey);
			}
		} catch (Exception e) {}
		
		return new ArrayList<>();
	}
	
	public static void put(String asyncKey, List<Map<String, Object>> result) {
		if (asyncKey == null) {
			return;
		}
		
		if (_CheckerThread == null) {
			startThread();
		}
		
		_AsyncResult.put(asyncKey, result);
		extendLifetime(asyncKey);
	}
	
	public static void remove(String asyncKey) {
		try {
			_AsyncResult.remove(asyncKey);
		} catch (Exception e) {}
	}
}
