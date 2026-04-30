public class ParseUtil {
	public static int parseIntOrDefault(String s, int defaultValue) {
		try {
			return Integer.parseInt(s);
		} catch (Exception e) {
			return defaultValue;
		}
	}

	/**
	 * KEY1_1:VALUE1|KEY1_2:VALUE2|KEY1_3:VALUE3,
	 * KEY2_1:VALUE1|KEY2_2:VALUE2|KEY2_3:VALUE3
	 */
	public static List<Map<String, String>> parseStringToMap(String content) {
		List<Map<String, String>> result = new ArrayList<>();
		String[] splitContent = content.split(",");

		// KEY:VALUE|KEY:VALUE
		for (String line : splitContent) {
			line = line.trim();
			String[] fields = line.split("\\|");
			Map<String, String> mapping = new HashMap<>();

			// KEY:VALUE
			for (String field : fields) {
				String[] splitField = field.split(":");

				if (splitField.length > 1) {
					String key = splitField[0].trim();
					String value;

					if (splitField.length == 2) {
						value = splitField[1].trim();
					} else {
						value = "";
					}

					mapping.put(key, value);
				}
			}

			result.add(mapping);
		}

		return result;
	}

	/**
	 * String 형식의 xml 데이터를 Document 객체로 파싱 후 반환
	 * @param xmlData xml 데이터
	 * @return Document
	 */
	public static Document parseStringToXmlDocument(String xmlData) throws Exception {
		if (xmlData == null || xmlData.isEmpty()) {
			throw new IllegalArgumentException("XML data is null or empty");
		}

		if (!xmlData.startsWith("<?xml")) {
			xmlData = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" + xmlData;
		}

		try {
			// parsing 설정
			DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();

			factory.setNamespaceAware(true);					// # namespace 인식 여부 설정
			factory.setIgnoringElementContentWhitespace(true);	// # 공백 여부 설정

			DocumentBuilder builder = factory.newDocumentBuilder();
			InputSource inputSource = new InputSource(new StringReader(xmlData));

			return builder.parse(inputSource);
		} catch (ParserConfigurationException | SAXException | IOException e) {
			throw new Exception("Error parsing XML string to Document", e);
		}
	}
}
