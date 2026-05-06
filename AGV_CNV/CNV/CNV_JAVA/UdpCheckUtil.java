package com.atlas.cnv;

/*
 * IMPORTS REQUIRED (for reference):
 * import java.net.DatagramSocket;
 * import java.net.DatagramPacket;
 */

/**
 * UDP receive test utility for CNV (Conveyor) system.
 * Used for testing and validating UDP message reception from STK MCP7/SSS.
 *
 * Usage: java UdpCheckUtil <port_number>
 * Example: java UdpCheckUtil 5000
 *
 * This utility listens on the specified port and logs incoming UDP packets
 * with timing information and message content.
 */
public class UdpCheckUtil {

    public static void main(String[] args) {
        int port = args.length > 0 ? Integer.parseInt(args[0]) : 5000;

        System.out.println("[UDP Check] Listening on port " + port + " ...");

        try (DatagramSocket socket = new DatagramSocket(port)) {
            socket.setSoTimeout(10000); // 10초 타임아웃

            int count = 0;

            while (true) {
                byte[] buffer = new byte[1500];
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);

                try {
                    socket.receive(packet);
                    count++;

                    String ip = packet.getAddress().getHostAddress();
                    String msg = new String(packet.getData(), 0, packet.getLength()).trim();

                    System.out.println("──────────────────────────────────────────────────");
                    System.out.println("[UDP #" + count + "] from: " + ip + ":" + packet.getPort() + " | len: " + packet.getLength());
                    System.out.println(msg);
                    System.out.println("──────────────────────────────────────────────────");

                } catch (java.net.SocketTimeoutException e) {
                    System.out.println("[UDP Check] NO DATA for 10s (total received: " + count + ")");
                }
            }
        } catch (Exception e) {
            System.err.println("[UDP Check] ERROR: " + e.getMessage());
            e.printStackTrace();
        }
    }
}
