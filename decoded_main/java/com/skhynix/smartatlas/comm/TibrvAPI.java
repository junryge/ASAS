package com.skhynix.smartatlas.comm;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.tibco.tibrv.TibrvListener;
import com.tibco.tibrv.TibrvMsg;
import com.tibco.tibrv.TibrvMsgCallback;
import com.tibco.tibrv.TibrvQueue;
import com.tibco.tibrv.TibrvRvdTransport;

public class TibrvAPI {
	private static final Logger logger = LoggerFactory.getLogger(TibrvAPI.class);
	
	public static boolean send(String service, String network, String daemon, String subject, String dataFieldName, String data) {
		TibrvRvdTransport transport = null;
		TibrvMsg tibrvMessage = null;
		
		try {
			transport = new TibrvRvdTransport(service, network, daemon);
			
			if (transport.isValid()) {
				tibrvMessage = new TibrvMsg();
				
				tibrvMessage.setSendSubject(subject);
				tibrvMessage.add(dataFieldName, data);

				transport.send(tibrvMessage);
			} else {
				throw new Exception("Invalid Service/Network/Daemon");
			}
		} catch (Exception e) {
			logger.error("TibrvSend Error : service: {}, network: \"{}\", daemon: \"{}\", subject: \"{}\", data: \"{}\"", service, network, daemon, subject, data, e);
			
			return false;
		} finally {
			if (transport != null) {
				transport.destroy();
			}
			
			tibrvMessage.dispose();
		}
		
		return true;
	}
	
	public static TibrvListener listen(String service, String network, String daemon, String subject, TibrvMsgCallback callback) {
		TibrvRvdTransport transport = null;
		TibrvQueue queue = null;
		
		try {
			transport = new TibrvRvdTransport(service, network, daemon);
			
			if (transport.isValid()) {
				queue = new TibrvQueue();
				return new TibrvListener(queue, callback, transport, subject, null);
			} else {
				throw new Exception("Invalid Service/Network/Daemon");
			}
		} catch (Exception e) {
			logger.error("TibrvListener Error : service: {}, network: \"{}\", daemon: \"{}\", subject: \"{}\", data: \"{}\"", service, network, daemon, subject, e);
			
			if (transport != null) {
				transport.destroy();
			}
			
			if (queue != null) {
				queue.destroy();
			}
		}
		
		return null;
	}
}
