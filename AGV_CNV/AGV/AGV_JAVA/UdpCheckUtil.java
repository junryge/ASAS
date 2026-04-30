package com.atlas.agv;

/*
 * Required imports:
 * - java.net.DatagramPacket
 * - java.net.DatagramSocket
 */

/**
 * UDP test utility for AGV system.
 * Simple UDP listener for debugging and monitoring incoming AGV messages.
 * Usage: java UdpCheckUtil <port_number>
 * Example: java UdpCheckUtil 5000
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
