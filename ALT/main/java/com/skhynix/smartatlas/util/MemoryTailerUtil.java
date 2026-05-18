package com.skhynix.smartatlas.util;

import java.util.Date;
import java.util.HashMap;

public class MemoryTailerUtil {
	private static final HashMap<String, Date> _Expired = new HashMap<String, Date>();
	private static final HashMap<String, String> _Content = new HashMap<String, String>();
	private static Thread _ExpiredTailersRemover;
	
	public static void startListener(String uniqueName) {
		if (commandContent(uniqueName, "ContainsKey", "") == "false") {
			commandContent(uniqueName, "GetAndClearContent", "");
			
			if (_ExpiredTailersRemover == null) {
				_ExpiredTailersRemover = new Thread(() -> RemoveExpiredTailer());
				_ExpiredTailersRemover.start();
			}
			
			appendContent(uniqueName, "Start Listen\n");
			
			_Expired.put(uniqueName, new Date());
		}
	}
	
	public static void stopListener(String uniqueName) {
		commandContent(uniqueName, "RemoveKey", "");
		_Expired.remove(uniqueName);
	}
	
	public static String getContent(String uniqueName) {
		if (commandContent(uniqueName, "ContainsKey", "") == "false") {
			return "";
		}
		
		return commandContent(uniqueName, "GetAndClearContent", "");
	}
	
	public static void appendContent(String uniqueName, String content) {
		if (commandContent(uniqueName, "ContainsKey", "") == "false") {
			return;
		}
		
		commandContent(uniqueName, "AppendContent", content);
	}
	
	private synchronized static String commandContent(String uniqueName, String command, String content) {
		var fileContent = _Content.get(uniqueName);
		
		switch (command) {
			case "ContainsKey":
				return String.valueOf(_Content.containsKey(uniqueName));
			case "RemoveKey":
				_Content.remove(uniqueName);
				break;
			case "GetAndClearContent":
				_Content.put(uniqueName, "");
				
				return fileContent;
			case "AppendContent":
				_Content.put(uniqueName, fileContent + "\n" + content);
				break;
		}
		
		return "";
	}
	
	private static void RemoveExpiredTailer() {
		while (true) {
			try {
				var keys = _Expired.keySet().toArray(new String[0]);
				
				for (String uniqueName : keys) {
					Date startDate = _Expired.get(uniqueName);
					
					if (startDate == null) {
						continue;
					}
					
					long dateDiff = new Date().getTime() - startDate.getTime();
					
					if (dateDiff >= 1000 * 60 * 60 * 24) {
						stopListener(uniqueName);
					}
				}
				
				Thread.sleep(60000 * 60);
			} catch (Exception e) {
				e.printStackTrace();
			}
		}
	} 
}
