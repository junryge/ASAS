package com.skhynix.smartatlas.util;

import java.io.BufferedReader;
import java.io.File;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonParser;

public class PythonUtil {
    private static final Logger logger              = LoggerFactory.getLogger("PYTHON");
    private static final String PYTHON_FILE_CMD     = "python";
    private static final String PYTHON_FILE_PATH
            = String.format("%s\\%s", FilePathUtil.REPOSITORY_PATH, PYTHON_FILE_CMD);

    public static List<Map<String, Object>> executeWithParam(String fileName, boolean stderrFlag) {
        return executeWithParam(fileName, stderrFlag, "");
    }

    /**
     * @param fileName python file name
     * @param stderrFlag output the result for the input command with an exception
     * @param params parameter for command
     * @return return results for the command entered, but returns a null value if no file exist in the directory
     */
    public static List<Map<String, Object>> executeWithParam(String fileName, boolean stderrFlag, String... params) {
        List<Map<String, Object>> result    = new ArrayList<>();
        Process process                     = null;
        ArrayList<String> commands          = new ArrayList<>();
        String directory                    = PYTHON_FILE_PATH + File.separator + fileName;

        if (fileName == null || fileName.isEmpty()) {
            logger.error("... python file name is null ot empty");
            return null;
        }

        try {
            File file = new File(directory);

            if (!file.exists()) {
                logger.info("... python file is not exist [directory: {}]", directory);
                // 예측 모델은 항상 배치되어 있는 것이 아니기 때문에, 스팸 로그를 피하기 위해 logger.error() 를 사용 하지 않음
                return null;
            }

            commands.add(PYTHON_FILE_CMD);
            commands.add(directory);

            if (params != null && params.length > 0) {
                Collections.addAll(commands, params);
            }

            ProcessBuilder processBuilder = new ProcessBuilder(commands);

            processBuilder.redirectErrorStream(stderrFlag);

            process = processBuilder.start();

            // !!! no using `StandardCharsets`(---> there is occurred parsing exception)
            try (
                    BufferedReader reader
                            = new BufferedReader(new InputStreamReader(process.getInputStream(), "UTF-8"))
            ) {
                String line;
                StringBuilder jsonOutput = new StringBuilder();

                while((line = reader.readLine()) != null) {
                    jsonOutput.append(line);

                    logger.info("[{}]>> {}", fileName, line);
                }

                JsonElement jsonElement = JsonParser.parseString(jsonOutput.toString());

                if (jsonElement == null) {
                    logger.error("[{}] result with python command is return to null value", fileName);
                } else if (jsonElement.isJsonArray()) {
                    JsonArray jsonArray = jsonElement.getAsJsonArray();

                    for (JsonElement jsonObject : jsonArray) {
                        Map<String, Object> map = new ObjectMapper().readValue(jsonObject.toString(), Map.class);

                        result.add(map);
                    }
                } else {
                    logger.error("[{}] unexpected JSON type returned [type={}] [context={}]", fileName, jsonElement.getClass().getName(), jsonOutput);
                }
            } catch (Exception e) {
                logger.error("[{}] an exception occurred while it's reading python script output", fileName, e);
            }

            int exitCode = process.waitFor();

            logger.info("[{}] process exited with code: {}", fileName, exitCode);
        } catch (Exception e) {
            logger.error("[{}] an exception occurred while it's executing python script", fileName, e);
        } finally {
            if (process != null) {
                process.destroy();
            }
        }

        _printResult(result, fileName);

        return result;
    }
// =====================================================================================================================
    /**
     * @param data list of prediction calculated
     * @param fileName selected python file name
     */
    private static void _printResult(List<Map<String, Object>> data, String fileName) {
        if (data.isEmpty()) {
            logger.info("... [{}] calculated prediction is empty", fileName);
        } else {
            StringBuilder content = new StringBuilder();

            content.append("\n").append("<PREDICTION RESULT [").append(fileName).append("]>");

            for (int i = 0; i < data.size(); i++) {
                Map<String, Object> row = data.get(i);

                if (i > 1) {
                    String boundaryLine = "=".repeat(20);

                    content.append("\n").append(boundaryLine);
                }

                for (Map.Entry<String, Object> entry : row.entrySet()) {
                    String column = entry.getKey();
                    Object value = entry.getValue();

                    String log = "[ROW=" + i + "] " + column + ": " + value;

                    content.append("\n").append(log);
                }
            }

            logger.info(content.toString());
        }
    }
}