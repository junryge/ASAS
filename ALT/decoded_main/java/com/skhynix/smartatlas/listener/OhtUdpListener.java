package com.skhynix.smartatlas.listener;

import java.net.DatagramPacket;
import java.net.DatagramSocket;
import java.net.SocketException;
import java.util.HashMap;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.data.Msg;
import com.skhynix.smartatlas.data.Msg.MSG_TYP;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.util.DataService;

public class OhtUdpListener {
	private final Logger logger 			= LoggerFactory.getLogger(getClass());
	private static final String UDP_LISTENER_STOP_LOG = ">>> the thread for UDP Listener is stopped [fab: {} | mcp: {}]";
	private static final String PORT_OPEN_LOG = "> OHT opened port : {} [fab: {} | mcp: {}]";
	boolean isMultiListener = false;
	Map<String,String[]> ipFabMcpNameMap = new HashMap<>();
	String fabId = "";
	String mcpName  = "";
	int port;
	boolean isRunning = false;
	Thread receiveThread = null;
	DatagramSocket socket = null;
	String daemon = "";
	String subject = "";

	public OhtUdpListener(String fabId, String mcpName, int port) {
		this.fabId 		= fabId;
		this.mcpName 	= mcpName;
		this.port 		= port;
		this.daemon 	= DataService.getInstance().getFabPropertiesMap().get(fabId).getMcpPropertiesMap().get(mcpName).getDaemon();
		this.subject 	= DataService.getInstance().getFabPropertiesMap().get(fabId).getMcpPropertiesMap().get(mcpName).getSubject();
	}

	//동일 포트를 사용하는 2개 이상의 FAB 경우
	public OhtUdpListener(String fabId, String mcpName, String ipString, int port) {
		this.port = port;

		addListenMcpIp(fabId, mcpName, ipString);
	}

	public void addListenMcpIp(String fabId, String mcpName, String ipString) {
		String[] ips = ipString.split(",");

		if (ips.length > 1) {
			for (String ip : ips) {
				ipFabMcpNameMap.put(ip.trim(), new String[] {fabId, mcpName});
			}

			isMultiListener = true;			

			logger.info("[fab: {} | mcp: {}] Created Listeners ({}) - multiple ips exist in one factory", this.fabId, this.mcpName, ips.length);
		} else {
			logger.error("this constructor only use when over 1 mcp share same port. check ip address! [ip: {}]", ipString);

			System.exit(1);
		}
	}

	public void start() {
		isRunning = true;

		logger.info("[fab: {} | mcp: {}] the thread for udp listener is started !!!", fabId, mcpName);
				
		receiveThread = new Thread("OhtMessageQueuing") {
			public void run(){
				DatagramPacket packet 	= null;
				byte[] buffer;

				try {
					socket = new DatagramSocket(port);

					_logPortOpened(port);

					while (isRunning) {
						try {
							buffer 	= new byte[1500];
							packet 	= new DatagramPacket(buffer, buffer.length);

							socket.receive(packet);

							String message = (new String(packet.getData()).trim());
							
							if (isMultiListener) {
								String ip 	= packet.getAddress().getHostAddress();
								
								String[] info = ipFabMcpNameMap.get(ip);
		                        if (info != null) {
		                        	fabId 	= info[0];
		                        	mcpName = info[1];
		                        } else {
		                            logger.warn("Received packet from unknown IP: {}", ip);
		                            continue; // 알 수 없는 IP 는 무시
		                        }
		                    }
							
							//TibrvAPI.send("", "", "tcp:10.125.117.113:7500", "_LOCAL.ATLAS.OHTUDP."+fabId+"."+mcpName, message);
							//TibrvAPI.send("", "", daemon, subject, "DATA", message);
															
							_addMessageInAtlasMemory(fabId, mcpName, message);								
						} catch (Exception e) {
							logger.error("An Error while processing [fab: {} | mcp: {}] OHT Message [packet: {}]", fabId, mcpName, packet, e);
						}
					}
				} catch (SocketException e1) {
					logger.error("An Error while opening [fab: {} | mcp: {}] OHT DatagramSocket [{}] ", fabId, mcpName, port, e1);
				}
			}
		};
		
//		if (!isMultiListener) {
//			// 하나의 fab 에 두 개 이상의 ip 를 갖지 아니한 경우
//			receiveThread = new Thread("OhtMessageQueuing") {
//				public void run(){
//					DatagramPacket packet 	= null;
//					byte[] buffer;
//
//					try {
//						socket = new DatagramSocket(port);
//
//						_logPortOpened(port);
//
//						while (isRunning) {
//							try {
//								buffer 	= new byte[1500];
//								packet 	= new DatagramPacket(buffer, buffer.length);
//
//								socket.receive(packet);
//
//								String message = (new String(packet.getData()).trim());
//								
//								//TibrvAPI.send("", "", "tcp:10.125.117.113:7500", "_LOCAL.ATLAS.OHTUDP."+fabId+"."+mcpName, message);
//								//TibrvAPI.send("", "", daemon, subject, "DATA", message);
//																
//								_addMessageInAtlasMemory(fabId, mcpName, message);								
//							} catch (Exception e) {
//								logger.error("An Error while processing [fab: {} | mcp: {}] OHT Message [packet: {}]", fabId, mcpName, packet, e);
//							}
//						}
//					} catch (SocketException e1) {
//						logger.error("An Error while opening [fab: {} | mcp: {}] OHT DatagramSocket [{}] ", fabId, mcpName, port, e1);
//					}
//				}
//			};
//		} else {
//			receiveThread = new Thread("MultiOhtMessageQueuing") {
//				public void run(){
//					DatagramPacket packet 	= null;
//					byte[] buffer;
//
//					try {
//						socket = new DatagramSocket(port);
//
//						_logPortOpened(port);
//
//						while(isRunning) {
//							String fabId	= "";
//							String mcpName	= "";
//
//							try {
//								buffer 	= new byte[1500];
//								packet 	= new DatagramPacket(buffer, buffer.length);
//
//								socket.receive(packet);
//
//								String message = (new String(packet.getData()).trim());
//								String ip 	= packet.getAddress().getHostAddress();
//								fabId 		= ipFabMcpNameMap.get(ip)[0];
//								mcpName 	= ipFabMcpNameMap.get(ip)[1];
//								
//								//TibrvAPI.send("", "", daemon, subject, "DATA", message);
//								
//								_addMessageInAtlasMemory(fabId, mcpName, message);
//							} catch (Exception e) {
//								logger.error("An Error while processing [fab: {} | mcp: {}] OHT Message [packet: {}] ", fabId, mcpName, packet, e);
//							}
//						}
//					} catch (SocketException e1) {
//						logger.error("An Error while opening [port: {}] OHT DatagramSocket [{}] ", port, e1);
//					}
//				}
//			};
//		}

		receiveThread.start();
	}

	private void _addMessageInAtlasMemory(String fabId, String mcpName, String message) {
		Msg data = new Msg(
				fabId,
				MSG_TYP.OHT,
				System.currentTimeMillis(),
				mcpName,
				message
		);

		// 실제 사용되는 message
		DataService.getInstance().queue.add(data);

		// 기록용으로 남겨두는 message, 단 monitoringControlBatch 에서 호출 후 해당 데이터 초기화
		if ("TRUE".equals(Env.getFabsetProperties().getProperty("CMN.CMN.UDP_MESSAGE_MONITORING"))) {
			DataService.getInstance().recordQueue.add(data);
		}
	}

	// 동작 중인 socket 을 중지 ---> port 스위칭 기능을 위해 추가
	public void stop() {
		if (this.socket != null) {
			isRunning = false;

			this._closeSocket();
		}
	}

	private void _closeSocket () {
		if (this.socket != null && !this.socket.isClosed()) {
			try {
				this.socket.close();

				logger.info(UDP_LISTENER_STOP_LOG, fabId, mcpName);
			} catch (Exception e) {
				logger.error("An Error Occurred While Closing UDP Socket !", e);
			}
		}
	}

	private void _logPortOpened(int port) {
		logger.info(PORT_OPEN_LOG, port, fabId, mcpName);
	}

	public String getFabId () {
		return fabId;
	}

	public String getMcpName () {
		return mcpName;
	}

	public int getPort () {
		return port;
	}

	public void setPort (int port) {
		this.port = port;
	}
}