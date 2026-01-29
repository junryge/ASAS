package com.oht.analyzer;

import java.io.*;
import java.net.*;
import java.util.*;
import java.text.SimpleDateFormat;

/**
 * 로그프레소 연동 클래스
 * - FABID별 HID 이벤트 분리 저장
 * - 로그프레소 테이블별 저장
 */
public class LogpressoExporter {

    private String logpressoHost;
    private int logpressoPort;
    private String apiKey;
    private SimpleDateFormat dateFormat;

    public LogpressoExporter(String host, int port, String apiKey) {
        this.logpressoHost = host;
        this.logpressoPort = port;
        this.apiKey = apiKey;
        this.dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
    }

    /**
     * FABID별 테이블명 생성
     */
    public String getTableName(String fabId) {
        return String.format("hid_events_%s", fabId.toLowerCase());
    }

    /**
     * HID 이벤트를 로그프레소용 JSON으로 변환
     */
    public String toLogpressoJson(HidZoneAnalyzer.HidEvent event) {
        StringBuilder json = new StringBuilder();
        json.append("{");
        json.append(String.format("\"timestamp\":\"%s\",", dateFormat.format(new Date(event.timestamp))));
        json.append(String.format("\"zone_id\":%d,", event.zoneId));
        json.append(String.format("\"event_type\":\"%s\",", event.eventType));
        json.append(String.format("\"vehicle_id\":\"%s\",", event.vehicleId));
        json.append(String.format("\"fab_id\":\"%s\",", event.fabId));
        json.append(String.format("\"from_node\":%d,", event.fromNode));
        json.append(String.format("\"to_node\":%d", event.toNode));
        json.append("}");
        return json.toString();
    }

    /**
     * FABID별 CSV 파일 분리 저장
     */
    public void exportByFabId(Map<String, List<HidZoneAnalyzer.HidEvent>> eventsByFabId,
                              String outputDir) throws IOException {
        File dir = new File(outputDir);
        if (!dir.exists()) {
            dir.mkdirs();
        }

        for (Map.Entry<String, List<HidZoneAnalyzer.HidEvent>> entry : eventsByFabId.entrySet()) {
            String fabId = entry.getKey();
            List<HidZoneAnalyzer.HidEvent> events = entry.getValue();

            // CSV 파일
            String csvFileName = String.format("FABID_%s_hid_events.csv", fabId);
            exportToCsv(events, new File(dir, csvFileName));

            // JSON 파일 (로그프레소 임포트용)
            String jsonFileName = String.format("FABID_%s_hid_events.json", fabId);
            exportToJson(events, new File(dir, jsonFileName));

            System.out.printf("FABID %s: %d events exported%n", fabId, events.size());
        }
    }

    /**
     * CSV 파일로 저장
     */
    private void exportToCsv(List<HidZoneAnalyzer.HidEvent> events, File file) throws IOException {
        try (PrintWriter writer = new PrintWriter(
                new OutputStreamWriter(new FileOutputStream(file), "UTF-8"))) {

            // BOM for Excel
            writer.write('\ufeff');

            // 헤더
            writer.println("timestamp,zone_id,event_type,vehicle_id,fab_id,from_node,to_node");

            // 데이터
            for (HidZoneAnalyzer.HidEvent event : events) {
                writer.printf("%s,%d,%s,%s,%s,%d,%d%n",
                    dateFormat.format(new Date(event.timestamp)),
                    event.zoneId,
                    event.eventType,
                    event.vehicleId,
                    event.fabId,
                    event.fromNode,
                    event.toNode);
            }
        }
    }

    /**
     * JSON 파일로 저장 (로그프레소 임포트용)
     */
    private void exportToJson(List<HidZoneAnalyzer.HidEvent> events, File file) throws IOException {
        try (PrintWriter writer = new PrintWriter(
                new OutputStreamWriter(new FileOutputStream(file), "UTF-8"))) {

            writer.println("[");
            for (int i = 0; i < events.size(); i++) {
                writer.print("  " + toLogpressoJson(events.get(i)));
                if (i < events.size() - 1) {
                    writer.println(",");
                } else {
                    writer.println();
                }
            }
            writer.println("]");
        }
    }

    /**
     * FABID별 통계 요약
     */
    public void printSummary(Map<String, List<HidZoneAnalyzer.HidEvent>> eventsByFabId) {
        System.out.println("\n========================================");
        System.out.println("       FABID별 HID 이벤트 요약");
        System.out.println("========================================");
        System.out.printf("%-15s %-10s %-10s %-10s%n", "FABID", "총 이벤트", "IN", "OUT");
        System.out.println("----------------------------------------");

        for (Map.Entry<String, List<HidZoneAnalyzer.HidEvent>> entry : eventsByFabId.entrySet()) {
            String fabId = entry.getKey();
            List<HidZoneAnalyzer.HidEvent> events = entry.getValue();

            long inCount = events.stream().filter(e -> "IN".equals(e.eventType)).count();
            long outCount = events.stream().filter(e -> "OUT".equals(e.eventType)).count();

            System.out.printf("%-15s %-10d %-10d %-10d%n",
                fabId, events.size(), inCount, outCount);
        }
        System.out.println("========================================\n");
    }

    public static void main(String[] args) {
        // 테스트
        LogpressoExporter exporter = new LogpressoExporter("localhost", 8888, "api-key");

        // 샘플 데이터 생성
        Map<String, List<HidZoneAnalyzer.HidEvent>> testData = new HashMap<>();

        List<HidZoneAnalyzer.HidEvent> fab1Events = new ArrayList<>();
        fab1Events.add(new HidZoneAnalyzer.HidEvent(
            System.currentTimeMillis(), 1, "IN", "VH001", "FAB1", 3048, 3023));
        fab1Events.add(new HidZoneAnalyzer.HidEvent(
            System.currentTimeMillis(), 1, "OUT", "VH001", "FAB1", 3025, 3026));
        testData.put("FAB1", fab1Events);

        List<HidZoneAnalyzer.HidEvent> fab2Events = new ArrayList<>();
        fab2Events.add(new HidZoneAnalyzer.HidEvent(
            System.currentTimeMillis(), 2, "IN", "VH002", "FAB2", 3043, 3044));
        testData.put("FAB2", fab2Events);

        try {
            exporter.exportByFabId(testData, "./output_logpresso");
            exporter.printSummary(testData);
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
