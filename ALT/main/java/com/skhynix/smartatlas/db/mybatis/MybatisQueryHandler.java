package com.skhynix.smartatlas.db.mybatis;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.w3c.dom.Element;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import static com.skhynix.smartatlas.util.XmlUtil.*;
import static java.util.stream.Collectors.toList;

public class MybatisQueryHandler {
    private static final Logger logger = LoggerFactory.getLogger(MybatisQueryHandler.class);
    private static final String FILE_PATH = String.format("%s\\dataaccessfx", System.getProperty("SMARTFX_REPOSITORY"));
    private static final String PREFIX = "mcs_";

    public static List<String> getAllQueryFileNames() {
        return getAllQueryFiles().stream()
                .map(p -> p.getFileName().toString())
                .filter(fileName -> fileName.contains(PREFIX))
                .collect(toList());
    }

    public static List<String> getQueryList(String fileName) {
        try {
            Map<String, Element> queries = loadXmlMap(getFilePath(fileName), "select");
            return new ArrayList<>(queries.keySet());
        } catch (Exception e) {
            logger.error(e.getMessage());
            return List.of();
        }
    }

    public static String getQueryContent(String fileName, String queryId) {
        try {
            return loadRaw(getFilePath(fileName), "select", queryId);
        } catch (Exception e) {
            logger.error(e.getMessage());
            return "";
        }
    }

    public static boolean updateQueryContent(String fileName, String queryId, String queryContent) {
        try {
            updateXml(getFilePath(fileName), "select", queryId, queryContent);
            return true;
        } catch (Exception e) {
            logger.error(e.getMessage());
            return false;
        }
    }

    private static String getFilePath(String fileName) {
        return Path.of(String.format("%s\\%s", FILE_PATH, fileName)).toString();
    }

    private static List<Path> getAllQueryFiles() {
        Path path = Path.of(FILE_PATH);
        try (Stream<Path> lines = Files.list(path)) {
            return lines.collect(toList());
        } catch (IOException e) {
            logger.error(e.getMessage());
            return List.of();
        }
    }
}
