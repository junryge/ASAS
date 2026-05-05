public class AbnormalDetectBatch implements Job{
    private final Logger logger     = LoggerFactory.getLogger(getClass());
    private final int DELAYED_TIME  = 1000 * 60;

    @Override
    public void execute(JobExecutionContext context) throws JobExecutionException {
        if (Util.isCurrentIC()) {
            logger.info("... `{}` has started`", this.getClass().getName());

            long timer = System.currentTimeMillis();

            this._run();

            long checkTimer = System.currentTimeMillis() - timer;

            if (checkTimer >= DELAYED_TIME) {
                logger.error("... !!!DELAYED!!! `{}` has finished [elapsed time: {}m ({}ms)]", this.getClass().getSimpleName(), checkTimer / (60 * 1000), checkTimer);
            } else {
                logger.info("... `{}` has finished [elapsed time: {}ms]", this.getClass().getSimpleName(), checkTimer);
            }
        }
    }

    private void _run() {
        try {
            List<Map<String, Object>> getTsLogList = getTsLogDataByLogpresso();
            // ↓ 패턴 비교 전처리
            List<Map<String, Object>> getLogPatternList = makeLogPatternProc(getTsLogList);
            // ↓ 중복값 제거한 신규 패턴 필터
            List<Map<String, Object>> getPatternData = removeDuplicates(getLogPatternList);

            if (!getPatternData.isEmpty()) {
                List<Tuple> logpressoData = XmlUtil.convert(getPatternData);

                Util.insertInLogpressoDatabase(logpressoData, "ts_log_pattern", this.getClass().getSimpleName());
            }
        } catch (Exception e) {
            logger.error("", e);
        }
    }

    // transactionId 별로 로그 데이터를 나열
    List<Map<String, Object>> getTsLogDataByLogpresso(){
        List<Map<String, Object>> result = XmlUtil.selectLogpressoQuery("tsLogPattern");
        String targetStep = "000-START-{HOST-COMMAND-TRANSPORTJOB-REQUEST}";

        if(!result.isEmpty()) {
            //HOST COMMAND REQUEST 만 다룰 수 있도록
            try {
                Set<Object> transactionIds = result.stream()
                        .filter(map -> targetStep.equals(map.get("STEP")))
                        .map(map -> map.get("TRANSACTIONID"))
                        .collect(Collectors.toSet());

                result = result.stream()
                        .filter(map -> transactionIds.contains(map.get("TRANSACTIONID")))
                        .collect(Collectors.toList());
            } catch (Exception e) {
                logger.error("", e);
            }
        }

        return result;
    }

    public List<Map<String, Object>> makeLogPatternProc(List<Map<String, Object>> inputLogs) {
        List<Map<String, Object>> result = new ArrayList<>();
        List<Map<String, Object>> outputLogs = new ArrayList<>();
        Map<String, List<Map<String, Object>>> transactions = new HashMap<>();

        try {
            // TRANSACTIONID 기준 그룹
            for (Map<String, Object> log : inputLogs) {
                String transactionId = (String) log.get("TRANSACTIONID");

                //transactionId 없으면 신규 array , 있을 경우엔 add
                transactions.computeIfAbsent(transactionId, k -> new ArrayList<>()).add(log);
            }

            for (Map.Entry<String, List<Map<String, Object>>> entry : transactions.entrySet()) {
                String transactionId = entry.getKey();
                List<Map<String, Object>> steps = entry.getValue();

                // transactionId 로 그룹화 한 데이터 기준 입력 데이터 가공
                // Extract necessary information from the first step
                Map<String, Object> firstStep = steps.get(0);
                String time = (String) firstStep.get("TIME");
                String process = (String) firstStep.get("PROCESS");
                String threadNo = (String) firstStep.get("THREAD");

                String step = (String) firstStep.get("STEP");
                String firstStepWithoutBrackets = step.replace("[", "").replace("]", "");
                String svcNm = extractSvcNm(firstStepWithoutBrackets);

                // TXN_PRCS_TIME 추가
                double txnPrcsTimeTotal = steps.stream()
                        .mapToDouble(log -> parseDouble((String) log.get("TXN_PRCS_TIME")))
                        .sum();

                double bpelCountTotal = steps.stream()
                        .mapToDouble(log -> parseDouble((String) log.get("BPEL_CNT")))
                        .sum();

                // STEP STRING JOING PROC_SEQ 필드 값으로 변환
                String procSeq = steps.stream()
                        .map(log -> "[" + log.get("STEP") + "]")
                        .collect(Collectors.joining());

                // Determine SUFFIX_YN and PREFIX_YN
                String suffixYn = firstStepWithoutBrackets.startsWith("000-START") ? "N" : "Y";
                String prefixYn = "";

                try {
                    steps.get(steps.size() - 1).putIfAbsent("TXN_PRCS_TIME", "0");

                    prefixYn = Double.parseDouble((String) steps.get(steps.size() - 1).get("TXN_PRCS_TIME")) == 0 ? "Y" : "N";
                } catch (Exception e) {
                    logger.error("", e);
                }

                // Calculate ACTIVE_THREAD_CNT
                int activeThreadCnt = steps.size();

                // Create the output map
                Map<String, Object> outputLog = new HashMap<>();

                outputLog.put("TIME", time);
                outputLog.put("SVC_NM", svcNm);
                outputLog.put("PROC_NM", process);
                outputLog.put("PROC_SEQ", procSeq);
                outputLog.put("TRANSACTIONID", transactionId);
                outputLog.put("THREAD_NO", threadNo);
                outputLog.put("TXN_PRCS_TIME", txnPrcsTimeTotal);
                outputLog.put("ACTIVE_THREAD_CNT", activeThreadCnt);
                outputLog.put("SUFFIX_YN", suffixYn);
                outputLog.put("PREFIX_YN", prefixYn);
                outputLog.put("BPEL_CNT", bpelCountTotal);

                // Add the output map to the list
                outputLogs.add(outputLog);

                // 짤리지 않은 데이터 반환
                result = outputLogs.stream()
                        .filter(log -> "N".equals(log.get("SUFFIX_YN")) && "N".equals(log.get("PREFIX_YN")))
                        .collect(Collectors.toList());

                //짤린 데이터 따로 temp 저장
                List<Map<String, Object>> otherLogs = outputLogs.stream()
                        .filter(log -> !"N".equals(log.get("SUFFIX_YN")) || !"N".equals(log.get("PREFIX_YN")))
                        .collect(Collectors.toList());
            }
        } catch (Exception e) {
            logger.error("", e);
        }

        return result;
    }

    private static String extractSvcNm(String step) {
        if (step.contains("{") && step.contains("}")) {
            int start = step.indexOf('{') + 1;
            int end = step.indexOf('}');

            return step.substring(start, end);
        } else if (step.contains("-")) {
            String[] parts = step.split("-");

            return parts.length > 1 ? parts[1] : "";
        } else {
            return step;
        }
    }

    private static double parseDouble(String value) {
        if (value == null) {
            return 0.0;
        }
        try {
            return Double.parseDouble(value);
        } catch (NumberFormatException e) {
            return 0.0;
        }
    }

    private List<Map<String, Object>> removeDuplicates(List<Map<String, Object>> logs) {
        Map<String, Map<String, Object>> uniqueLogsMap = new HashMap<>();
        List<Map<String, Object>> result = new ArrayList<>();
        List<Map<String, Object>> uniqueBothNYLogs;

        if (!logs.isEmpty()) {
            for (Map<String, Object> log : logs) {
                String procSeq = (String) log.get("PROC_SEQ");

                if (procSeq != null && !uniqueLogsMap.containsKey(procSeq)) {
                    uniqueLogsMap.put(procSeq, log);
                }
            }

            uniqueBothNYLogs = new ArrayList<>(uniqueLogsMap.values()); //자체 중복 제거

            if(!uniqueBothNYLogs.isEmpty()) {
                // 패턴 테이블 조회 데이터 비교 메소드
                result = compareAndFilterLogs(uniqueBothNYLogs);
            }
        }

        return result;
    }

    private List<Map<String, Object>> compareAndFilterLogs(List<Map<String, Object>> uniqueBothNYLogs) {
        List<Map<String, Object>> deduplicatedLogs = new ArrayList<>();
        List<Map<String, Object>> filteredLogs = new ArrayList<>();
        List<Map<String, Object>> patternList = XmlUtil.selectLogpressoQuery("tsNewPattern");
        String test = "";

        try {
            for (Map<String, Object> log : uniqueBothNYLogs) {
                boolean newPrcsSeqYn = true;
                boolean newFuncNmYn = true;

                for (Map<String, Object> patternLog : patternList) {
                    if (
                            patternLog.get("PROC_NM").toString().equals("ALL")
                                    || patternLog.get("PROC_NM").toString().equals("ALARM")
                                    || patternLog.get("SVC_NM").toString().equals("BPEL")
                    ) { // 차후 삭제할 것 (2025-12-14 삭제)
                        continue;
                    }

                    // ACTIVE THREAD CNT 비교
                    int activeThreadCntLog = Integer.parseInt(log.get("ACTIVE_THREAD_CNT") == null ? "0" : log.get("ACTIVE_THREAD_CNT").toString());
                    int activeThreadCntPattern = Integer.parseInt(patternLog.get("ACTIVE_THREAD_CNT") == null ? "0" : patternLog.get("ACTIVE_THREAD_CNT").toString());

                    //문자열 비교 (패턴)
                    String procSeqLog = log.get("PROC_SEQ").toString().trim().toUpperCase(); // 불필요한 공백 제거 및 대문자로 변환
                    String procSeqPattern = patternLog.get("PROC_SEQ").toString().trim().toUpperCase(); // 불필요한 공백 제거 및 대문자로 변환

                    if (procSeqLog.equals(procSeqPattern)) {
                        newPrcsSeqYn = false;

                        if (activeThreadCntLog == activeThreadCntPattern) {
                            newFuncNmYn = false;
                        }

                        break;
                    }
                }

                log.put("NEW_FUNC_NM_YN", newFuncNmYn ? "Y" : "N");
                log.put("NEW_PRCS_SEQ_YN", newPrcsSeqYn ? "Y" : "N");

                //2차 데이터 제공을 위해 N 아닌 값도 추가
                filteredLogs.add(log);

                // newFuncNmYn 또는 newPrcsSeqYn이 Y인 경우만 filteredLogs에 추가
//                if (newFuncNmYn || newPrcsSeqYn) {
//                    filteredLogs.add(log);
//                }
            }

            Set<String> uniqueKeys = new HashSet<>();

            for (Map<String, Object> log : filteredLogs) {
                String procSeq = log.get("PROC_SEQ").toString().trim().toUpperCase();
                String newFuncNmYn = log.get("NEW_FUNC_NM_YN").toString().trim().toUpperCase();
                String newPrcsSeqYn = log.get("NEW_PRCS_SEQ_YN").toString().trim().toUpperCase();
                String key = procSeq + newFuncNmYn + newPrcsSeqYn;

                if (uniqueKeys.add(key)) {
                    deduplicatedLogs.add(log);
                }
            }
        } catch (Exception e) {
            System.out.println(test);

            logger.error("", e);
        }

        return deduplicatedLogs;
    }
}
