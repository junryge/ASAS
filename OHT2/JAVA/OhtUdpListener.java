public class OhtUdpListener {
    private final Logger logger             = LoggerFactory.getLogger(getClass());
    private static final String UDP_LISTENER_STOP_LOG = ">>> the thread for UDP Listener is stopped [fab: {} | mcp: {}]";
    private static final String PORT_OPEN_LOG = "> opened port : {} [fab: {} | mcp: {}]";
    boolean isMultiListener = false;
    Map<String,String[]> ipFabMcpNameMap = new HashMap<>();
    String fabId = "";
    String mcpName  = "";
    int port;
    boolean isRunning = false;
    Thread receiveThread = null;
    DatagramSocket socket = null;

    public OhtUdpListener(String fabId, String mcpName, int port) {
        this.fabId         = fabId;
        this.mcpName     = mcpName;
        this.port         = port;
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

        if (!isMultiListener) {
            // 하나의 fab 에 두 개 이상의 ip 를 갖지 아니한 경우
            receiveThread = new Thread("OhtMessageQueuing") {
                public void run(){
                    DatagramPacket packet     = null;
                    byte[] buffer;

                    try {
                        socket = new DatagramSocket(port);

                        _logPortOpened(port);

                        while (isRunning) {
                            try {
                                buffer     = new byte[1500];
                                packet     = new DatagramPacket(buffer, buffer.length);

                                socket.receive(packet);

                                String message = (new String(packet.getData()).trim());

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
        } else {
            receiveThread = new Thread("MultiOhtMessageQueuing") {
                public void run(){
                    DatagramPacket packet     = null;
                    byte[] buffer;

                    try {
                        socket = new DatagramSocket(port);

                        _logPortOpened(port);

                        while(isRunning) {
                            String fabId    = "";
                            String mcpName    = "";

                            try {
                                buffer     = new byte[1500];
                                packet     = new DatagramPacket(buffer, buffer.length);

                                socket.receive(packet);

                                String message     = (new String(packet.getData()).trim());
                                String ip     = packet.getAddress().getHostAddress();
                                fabId         = ipFabMcpNameMap.get(ip)[0];
                                mcpName     = ipFabMcpNameMap.get(ip)[1];

                                _addMessageInAtlasMemory(fabId, mcpName, message);
                            } catch (Exception e) {
                                logger.error("An Error while processing [fab: {} | mcp: {}] OHT Message [packet: {}] ", fabId, mcpName, packet, e);
                            }
                        }
                    } catch (SocketException e1) {
                        logger.error("An Error while opening [port: {}] OHT DatagramSocket [{}] ", port, e1);
                    }
                }
            };
        }

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
        DataService.getInstance().recordQueue.add(data);
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