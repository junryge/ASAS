package com.oht.analyzer;

import java.io.*;
import java.util.*;
import java.util.stream.Collectors;

/**
 * HID Zone IN/OUT 분석기
 * - HID Zone별 IN/OUT 카운트 분석
 * - FABID별 분리 저장 (로그프레소용)
 */
public class HidZoneAnalyzer {

    // HID Zone 정보
    public static class HidZone {
        public int zoneId;
        public String hidNo;
        public int inCount;
        public int outCount;
        public List<String> inLanes;
        public List<String> outLanes;
        public int vehicleMax;
        public int vehiclePrecaution;
        public String fabId;

        public HidZone(int zoneId) {
            this.zoneId = zoneId;
            this.inLanes = new ArrayList<>();
            this.outLanes = new ArrayList<>();
        }

        @Override
        public String toString() {
            return String.format("HID-%d: IN=%d, OUT=%d, Max=%d",
                zoneId, inCount, outCount, vehicleMax);
        }
    }

    // HID 이벤트 로그
    public static class HidEvent {
        public long timestamp;
        public int zoneId;
        public String eventType;  // "IN" or "OUT"
        public String vehicleId;
        public String fabId;
        public int fromNode;
        public int toNode;

        public HidEvent(long timestamp, int zoneId, String eventType,
                       String vehicleId, String fabId, int fromNode, int toNode) {
            this.timestamp = timestamp;
            this.zoneId = zoneId;
            this.eventType = eventType;
            this.vehicleId = vehicleId;
            this.fabId = fabId;
            this.fromNode = fromNode;
            this.toNode = toNode;
        }
    }

    private Map<Integer, HidZone> zones = new HashMap<>();
    private Map<String, List<HidEvent>> eventsByFabId = new HashMap<>();

    /**
     * HID_ZONE_Master.csv 로드
     */
    public void loadMasterCsv(String csvPath) throws IOException {
        try (BufferedReader reader = new BufferedReader(
                new InputStreamReader(new FileInputStream(csvPath), "UTF-8"))) {

            String header = reader.readLine();  // 헤더 스킵
            String line;

            while ((line = reader.readLine()) != null) {
                String[] parts = parseCsvLine(line);
                if (parts.length < 12) continue;

                int zoneId = Integer.parseInt(parts[0].trim());
                HidZone zone = new HidZone(zoneId);
                zone.hidNo = parts[1].trim();
                zone.inCount = Integer.parseInt(parts[7].trim());
                zone.outCount = Integer.parseInt(parts[8].trim());
                zone.inLanes = parseLanes(parts[9]);
                zone.outLanes = parseLanes(parts[10]);
                zone.vehicleMax = Integer.parseInt(parts[11].trim());
                zone.vehiclePrecaution = Integer.parseInt(parts[12].trim());

                zones.put(zoneId, zone);
            }
        }
        System.out.println("Loaded " + zones.size() + " HID Zones");
    }

    /**
     * CSV 라인 파싱 (세미콜론 포함 필드 처리)
     */
    private String[] parseCsvLine(String line) {
        List<String> result = new ArrayList<>();
        StringBuilder current = new StringBuilder();
        boolean inQuotes = false;

        for (char c : line.toCharArray()) {
            if (c == '"') {
                inQuotes = !inQuotes;
            } else if (c == ',' && !inQuotes) {
                result.add(current.toString());
                current = new StringBuilder();
            } else {
                current.append(c);
            }
        }
        result.add(current.toString());

        return result.toArray(new String[0]);
    }

    /**
     * Lane 문자열 파싱 ("3048→3023; 3091→3002" 형식)
     */
    private List<String> parseLanes(String lanesStr) {
        List<String> lanes = new ArrayList<>();
        if (lanesStr == null || lanesStr.isEmpty()) return lanes;

        for (String lane : lanesStr.split(";")) {
            lanes.add(lane.trim());
        }
        return lanes;
    }

    /**
     * HID 이벤트 처리
     */
    public void processEvent(HidEvent event) {
        // FABID별 이벤트 저장
        eventsByFabId.computeIfAbsent(event.fabId, k -> new ArrayList<>())
                     .add(event);

        // Zone 카운트 업데이트
        HidZone zone = zones.get(event.zoneId);
        if (zone != null) {
            if ("IN".equals(event.eventType)) {
                zone.inCount++;
            } else if ("OUT".equals(event.eventType)) {
                zone.outCount++;
            }
        }
    }

    /**
     * FABID별 분리 저장 (로그프레소용)
     */
    public void saveByFabId(String outputDir) throws IOException {
        File dir = new File(outputDir);
        if (!dir.exists()) {
            dir.mkdirs();
        }

        for (Map.Entry<String, List<HidEvent>> entry : eventsByFabId.entrySet()) {
            String fabId = entry.getKey();
            List<HidEvent> events = entry.getValue();

            String fileName = String.format("hid_events_%s.csv", fabId);
            File outputFile = new File(dir, fileName);

            try (PrintWriter writer = new PrintWriter(
                    new OutputStreamWriter(new FileOutputStream(outputFile), "UTF-8"))) {

                // 헤더
                writer.println("timestamp,zone_id,event_type,vehicle_id,fab_id,from_node,to_node");

                // 데이터
                for (HidEvent event : events) {
                    writer.printf("%d,%d,%s,%s,%s,%d,%d%n",
                        event.timestamp,
                        event.zoneId,
                        event.eventType,
                        event.vehicleId,
                        event.fabId,
                        event.fromNode,
                        event.toNode);
                }
            }

            System.out.println("Saved: " + outputFile.getAbsolutePath() +
                             " (" + events.size() + " events)");
        }
    }

    /**
     * Zone별 IN/OUT 통계 출력
     */
    public void printStatistics() {
        System.out.println("\n=== HID Zone Statistics ===");
        System.out.println("Zone_ID\tIN_Count\tOUT_Count\tVehicle_Max");
        System.out.println("-------\t--------\t---------\t-----------");

        zones.values().stream()
            .sorted(Comparator.comparingInt(z -> z.zoneId))
            .forEach(zone -> {
                System.out.printf("%d\t%d\t\t%d\t\t%d%n",
                    zone.zoneId, zone.inCount, zone.outCount, zone.vehicleMax);
            });

        System.out.println("\n=== FABID Summary ===");
        for (String fabId : eventsByFabId.keySet()) {
            int count = eventsByFabId.get(fabId).size();
            System.out.printf("FABID: %s, Events: %d%n", fabId, count);
        }
    }

    /**
     * Zone별 IN/OUT 카운트 CSV 저장
     */
    public void saveZoneCountsCsv(String outputPath) throws IOException {
        try (PrintWriter writer = new PrintWriter(
                new OutputStreamWriter(new FileOutputStream(outputPath), "UTF-8"))) {

            writer.println("Zone_ID,HID_No,IN_Count,OUT_Count,Vehicle_Max,Vehicle_Precaution");

            zones.values().stream()
                .sorted(Comparator.comparingInt(z -> z.zoneId))
                .forEach(zone -> {
                    writer.printf("%d,%s,%d,%d,%d,%d%n",
                        zone.zoneId,
                        zone.hidNo,
                        zone.inCount,
                        zone.outCount,
                        zone.vehicleMax,
                        zone.vehiclePrecaution);
                });
        }
        System.out.println("Saved zone counts: " + outputPath);
    }

    public static void main(String[] args) {
        HidZoneAnalyzer analyzer = new HidZoneAnalyzer();

        try {
            // 1. Master CSV 로드
            String masterCsvPath = "../HID_ZONE_Master.csv";
            analyzer.loadMasterCsv(masterCsvPath);

            // 2. 샘플 이벤트 처리 (실제로는 로그에서 파싱)
            // analyzer.processEvent(new HidEvent(...));

            // 3. FABID별 분리 저장
            String outputDir = "./output_by_fabid";
            analyzer.saveByFabId(outputDir);

            // 4. 통계 출력
            analyzer.printStatistics();

            // 5. Zone 카운트 CSV 저장
            analyzer.saveZoneCountsCsv("./zone_counts.csv");

        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
