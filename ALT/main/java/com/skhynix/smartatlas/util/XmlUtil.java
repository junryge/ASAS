package com.skhynix.smartatlas.util;

import static javax.xml.transform.OutputKeys.DOCTYPE_PUBLIC;
import static javax.xml.transform.OutputKeys.DOCTYPE_SYSTEM;
import java.io.File;
import java.io.FileNotFoundException;
import java.io.StringReader;
import java.io.StringWriter;
import java.nio.charset.StandardCharsets;
import java.text.MessageFormat;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.dom.DOMSource;
import javax.xml.transform.stream.StreamResult;

import org.apache.commons.io.input.CharSequenceInputStream;
import org.apache.logging.log4j.util.Strings;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.service.TibrvService;
import org.xml.sax.InputSource;

public class XmlUtil {
	private static final Logger logger = LoggerFactory.getLogger(XmlUtil.class);

	static Map<String, String> alarmMessage 	= null;
	static Map<String, String> ohtAlarmMessage 	= null;
	static Map<String, String> variableMessage 	= null;
	static Map<String, String> logpressoQuery 	= null;
	static Map<String, String> logpressoQuery2 	= null;

	public static boolean verifyXml(String content) {
		if (Strings.isBlank(content)) {
			return false;
		}

		try {
			CharSequenceInputStream stream = new CharSequenceInputStream(content, StandardCharsets.UTF_8);
			DocumentBuilderFactory factory = DocumentBuilderFactory.newDefaultInstance();
			DocumentBuilder builder = factory.newDocumentBuilder();
			builder.parse(stream);

			return true;
		} catch (Exception e) {
			return false;
		}
	}

	// DOCTYPE 선언 유지 설정
	private static void setDocTypeDeclarationMaintenance(Transformer transformer) {
		transformer.setOutputProperty(DOCTYPE_SYSTEM, "mybatis-3-mapper.dtd");
		transformer.setOutputProperty(DOCTYPE_PUBLIC, "-//mybatis.org//DTD Mapper 3.0//EN");
	}

	public static void updateXml(String filePath, String tagName, String queryId, String queryContent) throws Exception {
		Document doc = _loadXml(filePath);

		if (doc == null) {
			logger.warn("... Document loaded is null (file path: {}) !", filePath);

			return;
		}

		NodeList queryNodes = doc.getElementsByTagName(tagName);

		for (int i = 0; i < queryNodes.getLength(); i++) {
			Node node = queryNodes.item(i);
			if (node.getNodeType() != Node.ELEMENT_NODE) continue;
			Element el = (Element) node;
			if (el.getAttribute("id").equalsIgnoreCase(queryId)) {
				el.setTextContent(queryContent);
			}
		}

		Transformer transformer = TransformerFactory.newInstance().newTransformer();
		DOMSource source = new DOMSource(doc);
		StreamResult result = new StreamResult(new File(filePath));

		setDocTypeDeclarationMaintenance(transformer);

		transformer.transform(source, result);
	}

	private static Document _loadXml(String directory) {
		try {
			File file = new File(directory);

			if (file.exists()) {
				DocumentBuilderFactory factory 	= DocumentBuilderFactory.newDefaultInstance();
				DocumentBuilder builder 		= factory.newDocumentBuilder();
				Document document 				= builder.parse(file);

				document.getDocumentElement().normalize();

				return document;
			} else {
				String exceptionMessage = "... file is not exist [directory: " + directory + "]";

				throw new FileNotFoundException(exceptionMessage);
			}
		} catch (Exception e) {
			logger.error("", e);

			return null;
		}
	}

//	public static Map<String, Element> loadXmlMap(String directory, String tagName) {
//		Map<String, Element> queryMap = new HashMap<>();
//		Document document = loadXml(directory);
//
//		if (document == null) {
//			logger.error("... document loaded is null [directory: {}]", directory);
//
//			return new HashMap<>();
//		}
//
//		NodeList nodeList = document.getElementsByTagName(tagName);
//
//		for (int i = 0; i < nodeList.getLength(); i += 1) {
//			Node node = nodeList.item(i);
//
//			if (node.getNodeType() == Node.ELEMENT_NODE) {
//				Element element = (Element) node;
//				String id 		= element.getAttribute("id");
//
//				queryMap.put(id, element);
//			}
//		}
//
//		return queryMap;
//	}

//	public static String loadRaw(String filePath) {
//		return formatXmlToString(loadXml(filePath));
//	}

	public static String loadRaw(String filePath, String tagName, String key) {
		return _loadXmlMessage(filePath, tagName, "id").getOrDefault(key, null);
	}

	public static Map<String, Element> loadXmlMap(String filePath, String tagName) {
		Map<String, Element> result	= new HashMap<>();
		Document document 			= _loadXml(filePath);

		if (document == null) {
			logger.error("... document is null, so process exit [directory: {}]", filePath);

			return new HashMap<>();
		}

		NodeList queryNodes = document.getElementsByTagName(tagName);

		for (int i = 0; i < queryNodes.getLength(); i += 1) {
			Node node = queryNodes.item(i);

			if (node.getNodeType() == Node.ELEMENT_NODE) {
				Element element	= (Element) node;
				String id		= element.getAttribute("id");

				result.put(id, element);
			}
		}

		return result;
	}

	public static String loadQuery(String filePath, String queryId) {
		String query = XmlUtil.loadRaw(filePath, "query", queryId);

		if (query == null) {
			query = XmlUtil.loadRaw(filePath, "select", queryId);
		}

		return query;
	}

	/**
	 * <h5>inquire and search an query with `customQuery.xml`</h5>
	 * @param queryId id in query tag
	 * @return result data with query
	 */
	public static List<Map<String, Object>> selectLogpressoQuery(String queryId) {
		if (logpressoQuery.containsKey(queryId)) {
			String query = logpressoQuery.get(queryId);

			return LogpressoAPI.responseResult(query);
		} else {
			return selectLogpressoQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, queryId);			
		}
	}

	/**
	 * <h5>inquire and search an query with `customQuery2.xml`</h5>
	 * @param queryId id in query tag
	 * @return result data with query
	 */
	public static List<Map<String, Object>> selectLogpressoQuery2(String queryId) {
		if (logpressoQuery2.containsKey(queryId)) {
			String query = logpressoQuery2.get(queryId);

			return LogpressoAPI.responseResult(query);
		} else {
			return selectLogpressoQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2, queryId);
		}
	}

	/**
	 * <h5>inquire and search an query</h5>
	 * @param path directory with xml file
	 * @param id id in query tag
	 * @return result data with query
	 */
	public static List<Map<String, Object>> selectLogpressoQuery(String path, String id) {
		try {
			String query = XmlUtil.loadQuery(path, id);

			return LogpressoAPI.responseResult(query);
		} catch (Exception e) {
			logger.error("", e);
		}

		return new ArrayList<>();
	}

	public static List<Tuple> convert(List<Map<String, Object>> list) {
		List<Tuple> result = new ArrayList<>();

		try {
			for (Map<String, Object> data : list) {
				final Tuple countMapSet = new Tuple();

				mapToTplConvert(data, countMapSet);

				result.add(countMapSet);
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		return result;
	}

	public static void mapToTplConvert(final Map<String, Object> data, final Tuple mapDataSet) {
		if (data == null || data.isEmpty()) return;

		for (Map.Entry<String, Object> entry : data.entrySet()) {
			String key = entry.getKey();
			Object value = entry.getValue();

			if (value == null) {
				value = "";
			}

			mapDataSet.put(key, value);
		}
	}

	// Layout 이상 감지를 위한 tib/rv message 구성
	public static <T> String formatLayoutMessage (
			String tibrvKey,
			String errorType,
			Map<String, T> data
	) {
		Map<String, String> formatData = new HashMap<>();

		for (Map.Entry<String, T> entry : data.entrySet()) {
			String key = entry.getKey();
			Object value = entry.getValue();
			String fValue = "";

			if (value == null) {
				fValue = "";
			} else if (value instanceof String) {
				fValue = value.toString();
			}

			formatData.put(key, fValue);
		}

		return formatMessageToString(tibrvKey, FilePathUtil.LAYOUT_DATA_FORMAT, errorType, formatData);
	}
	
	// HID INOUT 위한 tib/rv message 구성
//	public static <T> String formatHidInoutMessage (
//			String tibrvKey,
//			String errorType,
//			Map<String, T> data
//	) {
//		Map<String, String> formatData = new HashMap<>();
//
//		for (Map.Entry<String, T> entry : data.entrySet()) {
//			String key = entry.getKey();
//			Object value = entry.getValue();
//			String fValue = "";
//
//			if (value == null) {
//				fValue = "";
//			} else if (value instanceof String) {
//				fValue = value.toString();
//			}
//
//			formatData.put(key, fValue);
//		}
//
//		return formatMessageToString(tibrvKey, FilePathUtil.LAYOUT_HIDINOUT_FORMAT, errorType, formatData);
//	}

	/**
	 *
	 * @param tibrvKey DataService 에서 사용 중인 tib/rv 키
	 * @param filePath root 가 `DATA`인 xml file 의 위치
	 * @param messageType message 의 종류 (예: VIBRATION, RAILCUT 등)
	 * @param dataMap message 에 적용할 데이터
	 * @return String 형태의 xml 데이터
	 */
	public static String formatMessageToString (
			String tibrvKey,
			String filePath,
			String messageType,
			Map<String, String> dataMap
	) {
		long timer = System.currentTimeMillis();
		String failResult = "";

		// #1 XML file 호출
		Document cmnDoc = null;
		Document dataDoc;
		File file1 = null;
		File file2 = new File(filePath);
		int retryCount = 0;

		try {
			DocumentBuilderFactory builderFactory = DocumentBuilderFactory.newInstance();
			DocumentBuilder builder = builderFactory.newDocumentBuilder();

			while(retryCount < 3) {
				file1 = new File(FilePathUtil.COMMON_ALARM_FORMAT);

				try {
					cmnDoc = builder.parse(file1);

					break;
				} catch (Exception e) {
					++retryCount;

					Thread.sleep(100);

					logger.warn("... The file is occupied by another process. Run the process again after a while !");
				}
			}

			dataDoc = builder.parse(file2);
		} catch (Exception e) {
			logger.error("... Error parsing the file !!!", e);

			return failResult;
		}

		if (cmnDoc == null || dataDoc == null) {
			logger.error("... Document is null !!!");

			return failResult;
		}

		cmnDoc.setXmlStandalone(true);
		cmnDoc.getDocumentElement().normalize();
		dataDoc.getDocumentElement().normalize();

		Element cmnRoot = cmnDoc.getDocumentElement();
		Element dataRoot = dataDoc.getDocumentElement();

		if (cmnRoot == null || dataRoot == null) {
			logger.error("... Element parsed by file is null !!!");

			return failResult;
		}

		// 주석 제거
		_removeComments(cmnRoot);
		_removeComments(dataRoot);

		// #2 공통된 포맷의 HEADER 값 입력
		// #2-1 TRANSACTION_ID 값 설정
		NodeList transactionIds = cmnDoc.getElementsByTagName("TRANSACTIONID");

		if (transactionIds != null && transactionIds.getLength() > 0) {
			Element transactionIdElement = (Element) transactionIds.item(0);
			int transactionId = Integer.parseInt(transactionIdElement.getTextContent());

			transactionIdElement.setTextContent(String.valueOf(++transactionId));

			_saveXmlFile(cmnDoc, file1);
		}

		// #2-2 그외 HEADER 하위 값 설정
		NodeList headers = cmnDoc.getElementsByTagName("HEADER");

		if (headers != null && headers.getLength() > 0) {
			Element header = (Element) headers.item(0);

			for (int i = 0; i < header.getChildNodes().getLength(); i++) {
				Node node = header.getChildNodes().item(i);
				short nodeType = node.getNodeType();

				if (nodeType != Node.TEXT_NODE) {
					String nodeName = node.getNodeName();

					switch (nodeName) {
						case "MESSAGENAME": {
							TibrvService ts = DataService.getInstance().getTibrvSenderMap().get(tibrvKey);

							if (ts == null) {
								logger.error("... TibrvService is not found !!!");

								return failResult;
							}

							String messageName = ts.getSubject();

							node.setTextContent(messageName + "." + messageType);
						}
						break;
						case "TIME": {
							long now = System.currentTimeMillis();
							SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
							String time = dateFormat.format(now);

							node.setTextContent(time);
						}
						break;
					}
				}
			}
		}

		// # 2-3 ORIGINATED 값 입력
		NodeList originated = cmnDoc.getElementsByTagName("ORIGINATED");

		if (originated != null && originated.getLength() > 0) {
			Element header = (Element) originated.item(0);
			NodeList children = header.getChildNodes();

			for (int i = 0; i < children.getLength(); i++) {
				Node node = children.item(i);
				short nodeType = node.getNodeType();

				if (nodeType != Node.TEXT_NODE) {
					String nodeName = node.getNodeName();

					if (nodeName.equals("ORIGINATEDNAME") && !messageType.isEmpty()) {
						node.setTextContent(messageType);
					}
				}
			}
		}

		// #3 입력 받은 DATA 값을 특정 XML file 에 입력
		for (Entry<String, String> entry : dataMap.entrySet()) {
			String key = entry.getKey();
			String value = entry.getValue();
			NodeList nodeList = dataRoot.getElementsByTagName(key);

			if (nodeList.getLength() > 0 && !value.isEmpty()) {
				Element element = (Element) nodeList.item(0);

				element.setTextContent(value);
			}
		}

		// #4 메세지 병합 (공통된 포맷 + DATA)
		String dataTagName	= dataRoot.getTagName();
		NodeList dataList 	= cmnDoc.getElementsByTagName(dataTagName);

		if (dataList != null && dataList.getLength() > 0) {
			Element commonDataElement = (Element) dataList.item(0);
			NodeList children = dataRoot.getChildNodes();

			for (int i = 0; i < children.getLength(); i++) {
				Node child = children.item(i);

				if (child.getNodeType() != Node.ELEMENT_NODE) {
					continue;
				}

				NodeList existingNodes = commonDataElement.getElementsByTagName(child.getNodeName());

				if (existingNodes.getLength() > 0) {
					continue;
				}

				Node importedNode = cmnDoc.importNode(child, true);
				commonDataElement.appendChild(importedNode);
			}

			logger.info("... <*>formatting xml data was finished [elapsed time: {}ms]", System.currentTimeMillis() - timer);

			return prettyFormatXml(flattenDocument(cmnDoc));
		}

		return failResult;
	}

	private static void _removeComments (Node node) {
		NodeList children = node.getChildNodes();

		for (int i = children.getLength() - 1; i >= 0; i--) {
			Node child = children.item(i);
			short nodeType = child.getNodeType();

			if (nodeType == Node.COMMENT_NODE || nodeType == Node.CDATA_SECTION_NODE) {
				node.removeChild(child);
			} else if (node.hasChildNodes()) {
				_removeComments(child);
			}
		}
	}

	private static void _saveXmlFile (Document document, File file) {
		try {
			TransformerFactory transformerFactory 	= TransformerFactory.newInstance();
			Transformer transformer 				= transformerFactory.newTransformer();
			DOMSource domSource 					= new DOMSource(document);
			StreamResult streamResult				= new StreamResult(file);

			transformer.transform(domSource, streamResult);
		} catch (Exception e) {
			logger.error("... an error occurred while save or overwrite xml file [file: {} | path: {}] !!!", file.getName(), file.getPath(), e);
		}
	}

//	// XML → STRING
//	public static String formatXmlToString (Document document) {
//		String result = "";
//
//		try {
//			document.normalizeDocument();
//
//			TransformerFactory transformerFactory 	= TransformerFactory.newDefaultInstance();
//			Transformer transformer					= transformerFactory.newTransformer();
//
//			transformer.setOutputProperty(OutputKeys.OMIT_XML_DECLARATION, "no");	// XML 속성 선언
//			transformer.setOutputProperty(OutputKeys.INDENT, "no");					// 공백 추가 여부
////			transformer.setOutputProperty(OutputKeys.STANDALONE, "no");				//
//			transformer.setOutputProperty(OutputKeys.ENCODING, "UTF-8");			// 인코딩
//
//			DOMSource source 	= new DOMSource(document);
//			StreamResult stream	= new StreamResult(new java.io.StringWriter());
//
//			transformer.transform(source, stream);
//
////			result = stream.getWriter().toString().replaceAll(">\\s+<", "><");
//			result = stream.getWriter().toString();
//		} catch (Exception e) {
//			logger.error("", e);
//		}
//
//		return result;
//	}

	private static String flattenDocument(Document document) {
		try {
			TransformerFactory transformerFactory = TransformerFactory.newInstance();
			Transformer transformer = transformerFactory.newTransformer();

			transformer.setOutputProperty(OutputKeys.INDENT, "no");
			transformer.setOutputProperty(OutputKeys.OMIT_XML_DECLARATION, "no");

			StringWriter writer = new StringWriter();

			transformer.transform(new DOMSource(document), new StreamResult(writer));

			return writer.toString().replaceAll(">\\s+<", "><").trim();
		} catch (Exception e) {
			logger.error("... An error occurred while flattening the xml document !!!", e);
		}

		return "";
	}

	private static String prettyFormatXml(String xml) {
		if (xml.isEmpty()) return "";

		long timer = System.currentTimeMillis();

		try {
			DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
			DocumentBuilder builder = factory.newDocumentBuilder();
			Document document = builder.parse(new InputSource(new StringReader(xml)));
			TransformerFactory transformerFactory = TransformerFactory.newInstance();
			Transformer transformer = transformerFactory.newTransformer();

			transformer.setOutputProperty(OutputKeys.INDENT, "yes");
			transformer.setOutputProperty("{http://xml.apache.org/xslt}indent-amount", "4");

			StringWriter writer = new StringWriter();

			transformer.transform(new DOMSource(document), new StreamResult(writer));

			logger.info("... <1>formatting xml data for pretty form was finished [elapsed time: {}ms]", System.currentTimeMillis() - timer);

			return writer.toString();
		} catch (Exception e) {
			logger.error("... An error occurred while pretty formatting the xml string !!!", e);
		}

		return "";
	}

// =====================================================================================================================
	public static final String DEFAULT_VALUE = "Unknown ALARM CODE: ";

	public static String getMessage(String alarmCode, Object...params) {
		if (alarmMessage == null) {
			loadAlarmMessage();
		}

		if (alarmMessage == null) {
			logger.error("... extra xml data with 'alarm_message.xml' is null");

			return DEFAULT_VALUE + "NA";
		}

		String template = alarmMessage.getOrDefault(alarmCode, DEFAULT_VALUE + alarmCode);

		return MessageFormat.format(template, params);
	}

	public static String getOhtMessage(String alarmCode, Object...params) {
		if (ohtAlarmMessage == null) {
			loadOhtAlarmMessage();
		}

		if (ohtAlarmMessage == null) {
			logger.error("... extra xml data with 'oht_alarm_message.xml' is null");

			return DEFAULT_VALUE + "NA";
		}

		String template = ohtAlarmMessage.getOrDefault(alarmCode, DEFAULT_VALUE + alarmCode);

		return MessageFormat.format(template, params);
	}

	public static String getVariableEnv(String variableCode, Object...params) {
		if (variableMessage == null) {
			loadVariableEnv();
		}

		if (variableMessage == null) {
			logger.error("... extra xml data with 'variable.xml' is null");

			return DEFAULT_VALUE + "NA";
		}

		String template = variableMessage.getOrDefault(variableCode, DEFAULT_VALUE + variableCode);

		if (params == null || params.length == 0) {
			return template;
		} else {
			return MessageFormat.format(template, params);
		}
	}
// =====================================================================================================================
	// extra xml file (alarm_message.xml, oht_alarm_message.xml, variable.xml, customQuery.xml, customQuery2.xml)
	// 1. alarm_message.xml
	public static void loadAlarmMessage() {
		alarmMessage = new HashMap<>();
		Map<String, String> data = _loadXmlMessage(FilePathUtil.ALARM_MESSAGE_PATH, "alarm", "code");

		alarmMessage.putAll(data);
	}

	// 2. oht_alarm_message.xml
	public static void loadOhtAlarmMessage() {
		ohtAlarmMessage = new HashMap<>();
		Map<String, String> data = _loadXmlMessage(FilePathUtil.OHT_ALARM_MESSAGE_PATH, "alarm", "code");

		ohtAlarmMessage.putAll(data);
	}

	// 3. variable.xml
	public static void loadVariableEnv() {
		variableMessage = new HashMap<>();
		Map<String, String> data = _loadXmlMessage(FilePathUtil.VARIABLE_ENV_PATH, "variable", "code");

		variableMessage.putAll(data);
	}

	// 4. customQuery.xml
	// 5. customQuery2.xml
	public static void loadLogpressoParm(String directory) {
		Map<String, String> data = _loadXmlMessage(directory, "query", "id");

		if (directory.equals(FilePathUtil.LOGPRESSO_CUSTOM_QUERY)) {
			logpressoQuery = new HashMap<>();

			logpressoQuery.putAll(data);
		} else if (directory.equals(FilePathUtil.LOGPRESSO_CUSTOM_QUERY2)) {
			logpressoQuery2 = new HashMap<>();

			logpressoQuery2.putAll(data);
		}
	}
// =====================================================================================================================
	/**
	 * it's find message or contents from xml document
	 * @param directory xml file directory
	 * @param tagName tag name in xml context
	 * @param key attribute key
	 * @return mapping data --- key={key}, value={content}
	 */
	private static Map<String, String> _loadXmlMessage(
			String directory,
			String tagName,
			String key
	) {
		Map<String, String> result = new HashMap<>();

		try {
			Document document = _loadXml(directory);

			if (document == null) {
				String exceptionMessage = "... document is null [directory: " + directory + "]";

				throw new IllegalArgumentException(exceptionMessage);
			}

			NodeList nodeList = document.getElementsByTagName(tagName);

			for (int i = 0; i < nodeList.getLength(); i++) {
				if (nodeList.item(i) instanceof Element) {
					Element alarm 	= (Element) nodeList.item(i);
					String id 		= alarm.getAttribute(key);
					String message 	= alarm.getTextContent();

					result.put(id, message);
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		return result;
	}

//	/**
//	 * logpresso 에 저장된 값을 통해 NORMAL 상태로 구성한 뒤 tibco message 를 송신
//	 * @return NORMAL 상태의 tibco message 송신 성공 여부
//	 */
//	public static boolean sendNormalData(String layoutType, String fabId, String deviceName) {
//		List<Map<String, String>> messageList = new ArrayList<>();
//
//		String builder = "table duration=3d ATLAS_TIB_SEND_MSG_LOG" +
//				"| rex field=MESSAGE \"<FAB_ID>(?<FAB_ID>.*?)</FAB_ID>\"" +
//				"| rex field=MESSAGE \"<DEVICE_NM>(?<DEVICE_NM>.*?)</DEVICE_NM>\"" +
//				"| rex field=MESSAGE \"<FALR_RAISE_ADDR_LVAL>(?<FALR_RAISE_ADDR_LVAL>.*?)</FALR_RAISE_ADDR_LVAL>\"" +
//				"| rex field=MESSAGE \"<FALR_AFFECT_PORT_LVAL>(?<FALR_AFFECT_PORT_LVAL>.*?)</FALR_AFFECT_PORT_LVAL>\"" +
//				"| rename FALR_AFFECT_PORT_LVAL as PORT, FALR_RAISE_ADDR_LVAL as ADDRESS" +
//				"| search SUBJECT == \"M14." + Env.getEnv() + ".ATLAS.STARPDT.LAYOUT." + layoutType + "\"" +
//				"| search FAB_ID == \"" + fabId + "\"" +
//				"| search DEVICE_NM == \"" + deviceName + "\"" +
//				"| sort -_time" +
//				"| limit 1" +
//				"| fields FAB_ID, DEVICE_NM, ADDRESS, PORT";
//
//		try {
//			List<Map<String, Object>> data = LogpressoAPI.responseResult(builder);
//
//			if (data == null) {
//				logger.warn("... `{}` data is null [fab: {} | device: {}]", layoutType, fabId, deviceName);
//			} else {
//				String facId = null;
//				String[] facIds = {"M14", "M16"};
//
//				for (String _t : facIds) {
//					if (fabId.contains(_t)) {
//						facId = _t;
//
//						break;
//					}
//				}
//
//				if (facId == null) {
//					facId = "NA";
//					logger.error("... value of fac ID is invalid [fab: {} | fac: {}]", fabId, facId);
//
//					return false;
//				}
//
//				for (Map<String, Object> row : data) {
//					String address = null;
//					String port = null;
//
//					if (row.get("ADDRESS") != null) {
//						address = row.get("ADDRESS").toString();
//					}
//
//					if (row.get("PORT") != null) {
//						port = row.get("PORT").toString();
//					}
//
//					Map<String, String> messageData = LayoutUtil.buildLayoutMessageDataMap(
//							layoutType,
//							fabId,
//							deviceName,
//							OhtMsgWorkerRunnable.OHT_TIB_STATE.NORMAL,
//							address,
//							port,
//							null,
//							null,
//							facId,
//							null,
//							null,
//							false
//					);
//
//					messageList.add(messageData);
//				}
//
//				if (!messageList.isEmpty()) {
//					for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:").keySet()) {
//						DataService.getInstance().addTibrvMessageQueue(tibrvKey, layoutType, messageList);
//					}
//				}
//			}
//
//			return true;
//		} catch (Exception e) {
//			logger.error("", e);
//		}
//
//		return false;
//	}
}
