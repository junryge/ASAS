public class BridgeJudgeRangeBatch implements Job{
    private final Logger logger     = LoggerFactory.getLogger(getClass());
    private final int DELAYED_TIME  = 1000 * 60;

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        if (Util.isCurrentIC()) {
            logger.info("... `{}` has started", this.getClass().getSimpleName());

            long timer = System.currentTimeMillis();

            this._run();

            long checkTime = System.currentTimeMillis() - timer;

            if (checkTime >= DELAYED_TIME) {
                logger.error("... !!!DELAYED!!! `{}` has finished [elapsed time: {}m ({}ms)]", this.getClass().getSimpleName(), checkTime / (60 * 1000), checkTime);
            } else {
                logger.info("... `{}` has finished [elapsed time: {}ms]", this.getClass().getSimpleName(), checkTime);
            }

        }
    }

    private void _run() {
        try {
            final List<Tuple> countList = new ArrayList<>();
            List<Map<String, Object>> dataList = getBridgeLayoutList();

            String sigmaStr = XmlUtil.getVariableEnv("LAYOUT_SIGMA",null);

            if (sigmaStr.contains(XmlUtil.DEFAULT_VALUE)) {
                sigmaStr = "3";
            }

            int sigma = Integer.parseInt(sigmaStr);

            List<Map<String, Object>>  detectData =  detectAnomaly(dataList, sigma);

            // 현재 날짜와 시간 적용
            LocalDateTime now = LocalDateTime.now();

            // 원하는 형식으로 포맷팅합니다.
            DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyyMMdd");
            String eventDt = now.format(formatter);

            for (Map<String, Object> row :  detectData) {
                // EVENT_DT 값 동기화
                row.put("EVENT_DT", eventDt);
            }

            for (Map<String, Object> map : detectData) {
                final Tuple countMapSet = new Tuple();

                mapToTplConvert(map, countMapSet);

                countList.add(countMapSet);
            }

            Util.insertInLogpressoDatabase(countList, "bridge_judge_range", this.getClass().getSimpleName());
        } catch (Exception e) {
            logger.error("", e);
        }
    }

    public List<Map<String,Object>> getBridgeLayoutList(){
        StringBuilder sQuery = new StringBuilder();
        List<Map<String, Object>> result = new ArrayList<>();

        try {
            String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "bridgeLayoutWeek");
            sQuery.append(strQuery);
            result = LogpressoAPI.responseResult(sQuery.toString());

        }catch (Exception e) {
            logger.error("",e);
        }
        return result;
    }


    public List<Map<String, Object>> detectAnomaly(List<Map<String, Object>> data, int sigma) {
        logger.info("Start Validation Warn Y/N");
        List<Map<String, Object>> result = new ArrayList<>();

        try {
            if (data == null || data.isEmpty()) {
                throw new IllegalArgumentException("Insufficient data for the specified time window.");
            }

            // GROUP BY
            Map<String, List<Map<String, Object>>> groupData = data.stream()
                    .collect(Collectors.groupingBy(row -> row.get("FR_FAB_ID") + "|"
                            + row.get("TO_FAB_ID") + "|"
                            + row.get("IDC_NM") + "|"
                            + row.get("FR_LOC_NM") + "|"
                            + row.get("TO_LOC_NM")));

            List<Map<String, Object>> lastDataList = new ArrayList<>();

            // 최신값 빼두기
            for (Map.Entry<String, List<Map<String, Object>>> entry : groupData.entrySet()) {
                String key = entry.getKey();
                List<Map<String, Object>> groupRows = entry.getValue();

                groupRows.sort((row1, row2) -> {
                    try {
                        SimpleDateFormat dateFormat = new SimpleDateFormat("yyyyMMddHHmm");
                        Date date1 = dateFormat.parse(row1.get("EVENT_DT").toString());
                        Date date2 = dateFormat.parse(row2.get("EVENT_DT").toString());
                        return date2.compareTo(date1); // 내림차순
                    } catch (ParseException e) {
                        logger.error("Error parsing date", e);
                        return 0; // 오류 처리
                    }
                });

                Map<String, Object> latestData = groupRows.get(0);
                lastDataList.add(latestData);
            }
            String trimValueStr = XmlUtil.getVariableEnv("TRIM_VAL",null);
            String trimValueStrQCompleted = XmlUtil.getVariableEnv("CLIP_QPT_VAL",null);
            String qCompletedSigma = XmlUtil.getVariableEnv("QPT_SIGMA_VAL",null);

            // pk 값 기준 그룹별 시그마 판단 계산
            for (Map.Entry<String, List<Map<String, Object>>> entry : groupData.entrySet()) {
                String key = entry.getKey();
                List<Map<String, Object>> groupRows = entry.getValue();

                //입력 변수 초기화
                String trimVal = trimValueStr;
                int sigmaVal = sigma;

                // CURR_VAL을 기준으로 정렬
                groupRows.sort(Comparator.comparingDouble(row -> Double.parseDouble(row.get("CURR_VAL").toString())));
                int size = groupRows.size();


                if(trimValueStr.contains("Unknown ALARM CODE")) {
                    trimVal = "0.15";
                }

                // Bridge Image 지표 Completed 계산식은 별도 관리 할 수 잇도록 수정 적용
                if(key.equals("M14|M16|CD_HUBTOM16QCPT|M16 HUB|M16 6F2F") || key.equals("M16|M14|CD_M16TOHUBQCPT|M16 6F2F|M16 HUB")) {
                    trimVal = trimValueStrQCompleted.contains("Unknown ALARM CODE") ? "0.15" : trimValueStrQCompleted;
                    sigmaVal = qCompletedSigma.contains("Unknown ALARM CODE") ? 5 : Integer.parseInt(qCompletedSigma);
                }
                double trimValue = Double.parseDouble(trimVal);

                // 데이터 수가 충분하지 않은 경우 skip
                int excludeCount = (int) Math.ceil(size * trimValue);
                if (excludeCount * 2 >= size) {
                    logger.warn("Insufficient data for group: " + key);
                    continue;
                }

                // 상위 및 하위 15% 제외
                List<Double> filteredValues = groupRows.subList(excludeCount, size - excludeCount)
                        .stream()
                        .map(row -> Double.parseDouble(row.get("CURR_VAL").toString()))
                        .collect(Collectors.toList());

                // 평균 계산
                double sum = filteredValues.stream().mapToDouble(Double::doubleValue).sum();
                double avg = sum / filteredValues.size();

                // 현재 그룹 row 값 - 최신값 적용
                Map<String, Object> lastData = lastDataList.stream()
                        .filter(row -> (row.get("FR_FAB_ID") + "|" + row.get("TO_FAB_ID") + "|" + row.get("IDC_NM") + "|" + row.get("FR_LOC_NM") + "|" + row.get("TO_LOC_NM")).equals(key))
                        .findFirst()
                        .orElse(null);

                if (lastData == null) {
                    logger.warn("No latest data found for group: " + key);
                    continue;
                }

                // 현재 값에 AVG_VAL 컬럼 추가
                lastData.put("AVG_VAL", String.format("%.2f", avg));

                // 분산 계산
                double varianceSum = filteredValues.stream()
                        .mapToDouble(value -> Math.pow(value - avg, 2))
                        .sum();
                double variance = varianceSum / filteredValues.size();
                double standardDeviation = Math.sqrt(variance);

                double lowerBound = avg - sigmaVal * standardDeviation;
                double upperBound = avg + sigmaVal * standardDeviation;
                double avg_val = Double.parseDouble(lastData.get("AVG_VAL").toString());

                // 결과 값 저장
                lastData.put("STD_VAL", String.format("%.2f", standardDeviation));
                lastData.put("LOWER_VAL", String.format("%.2f", lowerBound));
                lastData.put("UPPER_VAL", String.format("%.2f", upperBound));
                lastData.put("SIGMA_VAL", sigmaVal);
                lastData.put("ALARM_MSG", "");

                result.add(lastData);
            }
        } catch (Exception e) {
            logger.error("Error in detectAnomaly", e);
        }

        logger.info("End Validation Warn Y/N");
        return result;
    }


    public static void mapToTplConvert(final Map<String, Object> obj, final Tuple mapDataSet) {
        if (obj == null)
            return;
        for (Map.Entry<String, Object> entry : obj.entrySet()) {
            try {
                mapDataSet.put(entry.getKey(), entry.getValue().toString());
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }
}
