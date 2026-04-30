public class LogpressoCommonFilterQuery {
	private static final Logger logger = LoggerFactory.getLogger(LogpressoCommonFilterQuery.class);

	public static StringBuilder extractCommonFilterJobHistory(final String filterPropertiesJson) {
		StringBuilder query4Logprs = new StringBuilder();
		Map<String, String> filterGroup;
		
		try {
			Map<String, Map<String, String>> filterProperties = JsonUtil.getMapMapFromJson(filterPropertiesJson);
			
			if (filterProperties.containsKey("SetPeriod")) {
				filterGroup = filterProperties.get("SetPeriod");
				String[] date = filterGroup.get("Elapsed").split(",");
				
				query4Logprs.append("set from=\"" + date[0] + "\"");
				query4Logprs.append(" | set to=\"" + date[1] + "\"");
				
				if ("TRUE".equalsIgnoreCase(filterGroup.get("IsRowCountMode"))) {
					query4Logprs.append(" | table ATLAS_JOB");
				} else {
					query4Logprs.append(" | table from=$(\"from\") to=$(\"to\") ATLAS_JOB");
				}
			}
			
			if (filterProperties.containsKey("From")) {
				filterGroup = filterProperties.get("From");
				
				query4Logprs.append(" | search (1");
				if ("ALL".equalsIgnoreCase(filterGroup.get("McpName")) == false) {
					query4Logprs.append(" and ");
					if ("TRUE".equalsIgnoreCase(filterGroup.get("IsNewFromMode"))) {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("newFromFabMcpNm", StringUtils.upperCase(filterGroup.get("McpName")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("McpNameNot")));
					} else {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("fromFabMcpNm", StringUtils.upperCase(filterGroup.get("McpName")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("McpNameNot")));
					}
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("EqpType")) == false) {
					query4Logprs.append(" and ");
					if ("TRUE".equalsIgnoreCase(filterGroup.get("IsNewFromMode"))) {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("newFromEqpTyp", StringUtils.upperCase(filterGroup.get("EqpType")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpTypeNot")));
					} else {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("fromEqpTyp", StringUtils.upperCase(filterGroup.get("EqpType")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpTypeNot")));
					}
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("DetailType")) == false) {
					query4Logprs.append(" and ");
					if ("TRUE".equalsIgnoreCase(filterGroup.get("IsNewFromMode"))) {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("newFromDetEqpTyp", StringUtils.upperCase(filterGroup.get("DetailType")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("DetailTypeNot")));
					} else {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("fromDetEqpTyp", StringUtils.upperCase(filterGroup.get("DetailType")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("DetailTypeNot")));
					}
				}
				
				if (filterGroup.get("EqpText").isBlank() == false) {
					query4Logprs.append(" and ");
					if ("TRUE".equalsIgnoreCase(filterGroup.get("IsNewFromMode"))) {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("newFromEqpId", StringUtils.upperCase(filterGroup.get("EqpText")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpTextNot")));
					} else {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("fromEqpId", StringUtils.upperCase(filterGroup.get("EqpText")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpTextNot")));
					}
				}
				
				if (filterGroup.get("PortText").isBlank() == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("fromNodeId", StringUtils.upperCase(filterGroup.get("PortText")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("PortTextNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("RailArea")) == false) {
					query4Logprs.append(" and ");
					if ("TRUE".equalsIgnoreCase(filterGroup.get("IsNewFromMode"))) {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("newFromRailArea", StringUtils.upperCase(filterGroup.get("RailArea")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("RailAreaNot")));
					} else {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("fromRailArea", StringUtils.upperCase(filterGroup.get("RailArea")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("RailAreaNot")));
					}
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("EqpGroup")) == false) {
					query4Logprs.append(" and ");
					if ("TRUE".equalsIgnoreCase(filterGroup.get("IsNewFromMode"))) {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("newFromEqpGrpNm", StringUtils.upperCase(filterGroup.get("EqpGroup")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpGroupNot")));
					} else {
						query4Logprs.append(
								LogpressoConditionUtil.createQueryCondition("fromEqpGrpNm", StringUtils.upperCase(filterGroup.get("EqpGroup")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpGroupNot")));
					}
				}
				query4Logprs.append(")");
			}
			
			if (filterProperties.containsKey("To")) {
				filterGroup = filterProperties.get("To");
				
				if (filterProperties.containsKey("From")
						&& "TRUE".equalsIgnoreCase(filterProperties.get("AndOr").get("IsOrFromTo"))) {
					query4Logprs.append(" or ");
				} else {
					query4Logprs.append(" and ");
				}
				
				query4Logprs.append("(1");
				if ("ALL".equalsIgnoreCase(filterGroup.get("McpName")) == false) {
					query4Logprs.append(" and ");	
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("toFabMcpNm", StringUtils.upperCase(filterGroup.get("McpName")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("McpNameNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("EqpType")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("toEqpTyp", StringUtils.upperCase(filterGroup.get("EqpType")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpTypeNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("DetailType")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("toDetEqpTyp", StringUtils.upperCase(filterGroup.get("DetailType")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("DetailTypeNot")));
				}
				
				if (filterGroup.get("EqpText").isBlank() == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("toEqpId", StringUtils.upperCase(filterGroup.get("EqpText")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpTextNot")));
				}
				
				if (filterGroup.get("PortText").isBlank() == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("toNodeId", StringUtils.upperCase(filterGroup.get("PortText")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("PortTextNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("RailArea")) == false) {
					query4Logprs.append(" and ");	
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("toAreaId", StringUtils.upperCase(filterGroup.get("RailArea")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("RailAreaNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("EqpGroup")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("toEqpGrpNm", StringUtils.upperCase(filterGroup.get("EqpGroup")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpGroupNot")));
				}
				
				query4Logprs.append(")");
			}
			
			if (filterProperties.containsKey("TransEqp")) {
				filterGroup = filterProperties.get("TransEqp");
				
				query4Logprs.append(" | search (1");
				if ("ALL".equalsIgnoreCase(filterGroup.get("TransEqpType")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryConditionArray("transEqpTypeList", StringUtils.upperCase(filterGroup.get("TransEqpType")), ENUM_RANGE_SEARCH_OPTION.RANGE, filterGroup.get("TransEqpTypeNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("TransEqpOHT")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryConditionArray("transEqpIdList", StringUtils.upperCase(filterGroup.get("TransEqpOHT")), ENUM_RANGE_SEARCH_OPTION.RANGE, filterGroup.get("TransEqpOHTNot")));
				}
				query4Logprs.append(")");
			}
			
			if (filterProperties.containsKey("DataCleansing")) {
				filterGroup = filterProperties.get("DataCleansing");
				
				query4Logprs.append(" | search (1");
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("AbnormalCmplt")) == false) {
					query4Logprs.append(" and upper(isAbnormalJob) == upper(\"" + filterGroup.get("AbnormalCmplt").equalsIgnoreCase("ONLY") + "\")");
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("CycleExists")) == false) {
					query4Logprs.append(" and upper(nvl(cycleExists, false, cycleExists)) == upper(\"" + filterGroup.get("CycleExists").equalsIgnoreCase("ONLY") + "\")");
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("JamedVHL")) == false) {
					query4Logprs.append(" and (vhlJamTime != \"-1\") == " + filterGroup.get("JamedVHL").equalsIgnoreCase("ONLY"));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("ErroredVHL")) == false) {
					query4Logprs.append(" and (vhlErrTime != \"-1\") == " + filterGroup.get("ErroredVHL").equalsIgnoreCase("ONLY"));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("BatchTrans")) == false) {
					query4Logprs.append(" and (nvl(batchId, \"\", batchId) != \"\") == " + filterGroup.get("BatchTrans").equalsIgnoreCase("ONLY"));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("Alternated")) == false) {
					query4Logprs.append(" and (alternatingTime != \"-1\") == " + filterGroup.get("Alternated").equalsIgnoreCase("ONLY"));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("Canceled")) == false) {
					query4Logprs.append(" and (cancelTime != \"-1\") == " + filterGroup.get("Canceled").equalsIgnoreCase("ONLY"));
				}
				
				query4Logprs.append(")");
			}
			
			if (filterProperties.containsKey("Etc")) {
				filterGroup = filterProperties.get("Etc");
				
				query4Logprs.append(" | search (1");
				if (StringUtils.isBlank(filterGroup.get("Job")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("id", StringUtils.upperCase(filterGroup.get("Job")), ENUM_RANGE_SEARCH_OPTION.EXACT, "FALSE"));
				}
				
				if (StringUtils.isBlank(filterGroup.get("Carrier")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("carrierId", StringUtils.upperCase(filterGroup.get("Carrier")), ENUM_RANGE_SEARCH_OPTION.EXACT, "FALSE"));
				}
				
				if (StringUtils.isBlank(filterGroup.get("Lot")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("lotId", StringUtils.upperCase(filterGroup.get("Lot")), ENUM_RANGE_SEARCH_OPTION.EXACT, "FALSE"));
				}
				
				if (StringUtils.isBlank(filterGroup.get("StepID")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("stepId", StringUtils.upperCase(filterGroup.get("StepID")), ENUM_RANGE_SEARCH_OPTION.EXACT, "FALSE"));
				}
				
				if (StringUtils.isBlank(filterGroup.get("Router")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("router", StringUtils.upperCase(filterGroup.get("Router")), ENUM_RANGE_SEARCH_OPTION.EXACT, "FALSE"));
				}
				
				if (StringUtils.isBlank(filterGroup.get("Requestor")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("requestor", StringUtils.upperCase(filterGroup.get("Requestor")), ENUM_RANGE_SEARCH_OPTION.EXACT, "FALSE"));
				}
				
				if (StringUtils.isBlank(filterGroup.get("BatchID")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("batchId", StringUtils.upperCase(filterGroup.get("BatchID")), ENUM_RANGE_SEARCH_OPTION.EXACT, "FALSE"));
				} 
				
				if (StringUtils.isBlank(filterGroup.get("ViaBJEdge")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryConditionArray("bjePath", StringUtils.upperCase(filterGroup.get("ViaBJEdge")), ENUM_RANGE_SEARCH_OPTION.RANGE, "FALSE"));
				}
				
				query4Logprs.append(" and double(createEndIntervalT) >= " + Integer.parseInt(filterGroup.get("Elapsed").split(",")[0]) * 60000);
				query4Logprs.append(" and double(createEndIntervalT) <= " + Integer.parseInt(filterGroup.get("Elapsed").split(",")[1]) * 60000);
				query4Logprs.append(" and double(fromToRanDistance) >= " + Integer.parseInt(filterGroup.get("Distance").split(",")[0]) * 1000);
				query4Logprs.append(" and double(fromToRanDistance) <= " + Integer.parseInt(filterGroup.get("Distance").split(",")[1]) * 1000);

				query4Logprs.append(")");
			}
			
			if (filterProperties.containsKey("SetPeriod")) {
				filterGroup = filterProperties.get("SetPeriod");
				
				if ("TRUE".equalsIgnoreCase(filterGroup.get("IsRowCountMode"))) {
					query4Logprs.append(" | limit " + filterGroup.get("RowCount"));
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		return new StringBuilder(QueryUtil.replaceDummy(query4Logprs.toString()));
	}
	
	public static StringBuilder extractCommonFilterCommandHistory(String filterPropertiesJson) {
		StringBuilder query4Logprs = new StringBuilder();
		Map<String, String> filterGroup;
		
		try {
			Map<String, Map<String, String>> filterProperties = JsonUtil.getMapMapFromJson(filterPropertiesJson);
			
			if (filterProperties.containsKey("SetPeriod")) {
				filterGroup = filterProperties.get("SetPeriod");
				String[] date = filterGroup.get("Elapsed").split(",");
				
				query4Logprs.append("set from=\"" + date[0] + "\"");
				query4Logprs.append(" | set to=\"" + date[1] + "\"");
				
				if ("TRUE".equalsIgnoreCase(filterGroup.get("IsRowCountMode"))) {
					query4Logprs.append(" | table ATLAS_COMMAND");
				} else {
					query4Logprs.append(" | table from=$(\"from\") to=$(\"to\") ATLAS_COMMAND");
				}
			}
			
			if (filterProperties.containsKey("From")) {
				filterGroup = filterProperties.get("From");
				
				query4Logprs.append(" | search (1");
				if ("ALL".equalsIgnoreCase(filterGroup.get("EqpType")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("sourceEqpTyp", StringUtils.upperCase(filterGroup.get("EqpType")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpTypeNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("DetailType")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("sourceDetEqpTyp", StringUtils.upperCase(filterGroup.get("DetailType")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("DetailTypeNot")));
				}
				
				if (filterGroup.get("EqpText").isBlank() == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("sourceEqpId", StringUtils.upperCase(filterGroup.get("EqpText")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpTextNot")));
				}
				
				if (filterGroup.get("PortText").isBlank() == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("sourceNodeId", StringUtils.upperCase(filterGroup.get("PortText")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("PortTextNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("RailArea")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("sourceAreaName", StringUtils.upperCase(filterGroup.get("RailArea")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("RailAreaNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("EqpGroup")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("sourceEqpGrpNm", StringUtils.upperCase(filterGroup.get("EqpGroup")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpGroupNot")));
				}
				
				query4Logprs.append(")");
			}
			
			if (filterProperties.containsKey("To")) {
				filterGroup = filterProperties.get("To");
				
				if (filterProperties.containsKey("From") 
						&& "TRUE".equalsIgnoreCase(filterProperties.get("AndOr").get("IsOrFromTo"))) {
					query4Logprs.append(" or ");
				} else {
					query4Logprs.append(" and ");
				}
				
				query4Logprs.append("(1");
				if ("ALL".equalsIgnoreCase(filterGroup.get("EqpType")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("destEqpTyp", StringUtils.upperCase(filterGroup.get("EqpType")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpTypeNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("DetailType")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("destDetEqpTyp", StringUtils.upperCase(filterGroup.get("DetailType")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("DetailTypeNot")));
				}
				
				if (filterGroup.get("EqpText").isBlank() == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("destEqpId", StringUtils.upperCase(filterGroup.get("EqpText")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpTextNot")));
				}
				
				if (filterGroup.get("PortText").isBlank() == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("destNodeId", StringUtils.upperCase(filterGroup.get("PortText")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("PortTextNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("RailArea")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("destAreaName", StringUtils.upperCase(filterGroup.get("RailArea")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("RailAreaNot")));
				}
				
				if ("ALL".equalsIgnoreCase(filterGroup.get("EqpGroup")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("destEqpGrpNm", StringUtils.upperCase(filterGroup.get("EqpGroup")), ENUM_RANGE_SEARCH_OPTION.EXACT, filterGroup.get("EqpGroupNot")));
				}
				
				query4Logprs.append(")");
			}
			
			if (filterProperties.containsKey("Etc")) {
				filterGroup = filterProperties.get("Etc");
				
				query4Logprs.append(" | search (1");
				if (StringUtils.isBlank(filterGroup.get("Job")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("jobId", StringUtils.upperCase(filterGroup.get("Job")), ENUM_RANGE_SEARCH_OPTION.EXACT, "FALSE"));
				}
				
				if (StringUtils.isBlank(filterGroup.get("Carrier")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("carrierId", StringUtils.upperCase(filterGroup.get("Carrier")), ENUM_RANGE_SEARCH_OPTION.EXACT, "FALSE"));
				}
				
				if (StringUtils.isBlank(filterGroup.get("StepID")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("stepId", StringUtils.upperCase(filterGroup.get("StepID")), ENUM_RANGE_SEARCH_OPTION.EXACT, "FALSE"));
				}
				
				if (StringUtils.isBlank(filterGroup.get("StepName")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryCondition("stepNm", StringUtils.upperCase(filterGroup.get("StepName")), ENUM_RANGE_SEARCH_OPTION.EXACT, "FALSE"));
				}
				
				if (StringUtils.isBlank(filterGroup.get("ViaBJEdge")) == false) {
					query4Logprs.append(" and ");
					query4Logprs.append(
							LogpressoConditionUtil.createQueryConditionArray("bjePath", StringUtils.upperCase(filterGroup.get("ViaBJEdge")), ENUM_RANGE_SEARCH_OPTION.RANGE, "FALSE"));
				}
				
				query4Logprs.append(" and double(elapsed) >= " + Integer.parseInt(filterGroup.get("Elapsed").split(",")[0]) * 60000);
				query4Logprs.append(" and double(elapsed) <= " + Integer.parseInt(filterGroup.get("Elapsed").split(",")[1]) * 60000);
				query4Logprs.append(" and double(ranDistance) >= " + Integer.parseInt(filterGroup.get("Distance").split(",")[0]) * 1000);
				query4Logprs.append(" and double(ranDistance) <= " + Integer.parseInt(filterGroup.get("Distance").split(",")[1]) * 1000);

				query4Logprs.append(")");
			}
			
			if (filterProperties.containsKey("SetPeriod")) {
				filterGroup = filterProperties.get("SetPeriod");
				
				if ("TRUE".equalsIgnoreCase(filterGroup.get("IsRowCountMode"))) {
					query4Logprs.append(" | limit " + filterGroup.get("RowCount"));
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		return new StringBuilder(QueryUtil.replaceDummy(query4Logprs.toString()));
	}
	
	public static List<ExtractCommonFilterResult> extractCommonFilterBody(
			String filterPropertiesJson, McslogTablesCollection tablesCollection, boolean isFulltext) {
		var queries = new ArrayList<ExtractCommonFilterResult>();
		Map<String, String> filterGroup;
		
		try {
			Map<String, Map<String, String>> filterProperties = JsonUtil.getMapMapFromJson(filterPropertiesJson);
			List<FormatQueryCondition> conditions = new ArrayList<FormatQueryCondition>();
			Map<String, String> fabTablesMap = new HashMap<>();
			
			var queryBuilder = new StringBuilder();
			var site = "";
			var fabs = new ArrayList<String>();
			var machineNameFieldName = "";
			
			if (filterProperties.containsKey("McslogFab")) {
				filterGroup = filterProperties.get("McslogFab");
				
				site = filterGroup.get("Site");
				fabTablesMap = tablesCollection.get(site);
				
				for (String fab : filterGroup.get("Fabs").split(",")) {
					if ("ALL".equalsIgnoreCase(fab) == true) {
						fabs.addAll(LogpressoMcslogQuery.getFabsList(site));
						break;
					}
					
					fabs.add(fab);
				}
			}
			
			if (filterProperties.containsKey("McslogAlarmReportLog")) {
				filterGroup = filterProperties.get("McslogAlarmReportLog");
				
				machineNameFieldName = "MACHINENAME";
				
				conditions.add(new FormatQueryCondition("method == \"createAlarmReportHistory\"", ENUM_FULLTEXT_COND.TRUE));
				
				if (StringUtils.isNotEmpty(filterGroup.get("UnitName"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"CURRENTUNITNAME"
							, Arrays.asList(filterGroup.get("UnitName").replace("-", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("AlarmID"))) {
					conditions.add(new FormatQueryCondition(String.format("ALARMID == \"%s\"", filterGroup.get("AlarmID")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("AlarmCode"))) {
					conditions.add(new FormatQueryCondition(String.format("ALARMCODE == \"%s\"", filterGroup.get("AlarmCode")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("AlarmText"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"ALARMTEXT"
							, Arrays.asList(filterGroup.get("AlarmText").replace("-", "_").replace(" ", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("State"))) {
					conditions.add(new FormatQueryCondition(String.format("STATE == \"%s\"", filterGroup.get("State")), ENUM_FULLTEXT_COND.TRUE));
				}
			}
			
			if (filterProperties.containsKey("McslogMaterialCarrierLocLog")) {
				filterGroup = filterProperties.get("McslogMaterialCarrierLocLog");
				
				machineNameFieldName = "CURRENTMACHINENAME";
				
				conditions.add(new FormatQueryCondition("method == \"createCarrierLocationHistory\"", ENUM_FULLTEXT_COND.TRUE));
				
				if (StringUtils.isNotEmpty(filterGroup.get("Carrier"))) {
					conditions.add(new FormatQueryCondition(String.format("CARRIER == \"%s\"", filterGroup.get("Carrier")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("LotID"))) {
					conditions.add(new FormatQueryCondition(String.format("LOTID == \"%s\"", filterGroup.get("LotID")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("CommandID"))) {
					conditions.add(new FormatQueryCondition(String.format("TRANSPORTCOMMANDID == \"%s\"", filterGroup.get("CommandID")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("UnitName"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"CURRENTUNITNAME"
							, Arrays.asList(filterGroup.get("UnitName").replace("-", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				}
			}
			
			if (filterProperties.containsKey("McslogResourceMachineLog")) {
				filterGroup = filterProperties.get("McslogResourceMachineLog");
				
				machineNameFieldName = "MACHINENAME";
				
				conditions.add(new FormatQueryCondition("method == \"createMachineHistory\"", ENUM_FULLTEXT_COND.TRUE));
				
				if (StringUtils.isNotEmpty(filterGroup.get("State"))) {
					conditions.add(new FormatQueryCondition(String.format("STATE == \"%s\"", filterGroup.get("State")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("ConnectionState"))) {
					conditions.add(new FormatQueryCondition(String.format("CONNECTIONSTATE == \"%s\"", filterGroup.get("ConnectionState")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("ControlState"))) {
					conditions.add(new FormatQueryCondition(String.format("CONTROLSTATE == \"%s\"", filterGroup.get("ControlState")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("TSCState"))) {
					conditions.add(new FormatQueryCondition(String.format("TSCSTATE == \"%s\"", filterGroup.get("TSCState")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("ProcessingState"))) {
					conditions.add(new FormatQueryCondition(String.format("PROCESSINGSTATE == \"%s\"", filterGroup.get("ProcessingState")), ENUM_FULLTEXT_COND.TRUE));
				}
			}
			
			if (filterProperties.containsKey("McslogResourcePortLog")) {
				filterGroup = filterProperties.get("McslogResourcePortLog");
				
				machineNameFieldName = "MACHINENAME";
				
				conditions.add(new FormatQueryCondition("method == \"createPortHistory\"", ENUM_FULLTEXT_COND.TRUE));

				if (StringUtils.isNotEmpty(filterGroup.get("PortName"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"PORTNAME"
							, Arrays.asList(filterGroup.get("PortName").replace("-", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("State"))) {
					conditions.add(new FormatQueryCondition(String.format("STATE == \"%s\"", filterGroup.get("State")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("SubState"))) {
					conditions.add(new FormatQueryCondition(String.format("SUBSTATE == \"%s\"", filterGroup.get("SubState")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("ProcessingState"))) {
					conditions.add(new FormatQueryCondition(String.format("PROCESSINGSTATE == \"%s\"", filterGroup.get("ProcessingState")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("Banned"))) {
					conditions.add(new FormatQueryCondition(String.format("BANNED == \"%s\"", filterGroup.get("Banned")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("InOutType"))) {
					conditions.add(new FormatQueryCondition(String.format("INOUTTYPE == \"%s\"", filterGroup.get("InOutType")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("Manual"))) {
					conditions.add(new FormatQueryCondition(String.format("MANUAL == \"%s\"", filterGroup.get("Manual")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("AccessMode"))) {
					conditions.add(new FormatQueryCondition(String.format("ACCESSMODE == \"%s\"", filterGroup.get("AccessMode")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("IdReadState"))) {
					conditions.add(new FormatQueryCondition(String.format("IDREADSTATE == \"%s\"", filterGroup.get("IdReadState")), ENUM_FULLTEXT_COND.TRUE));
				}
			}
			
			if (filterProperties.containsKey("McslogResourceShelfLog")) {
				filterGroup = filterProperties.get("McslogResourceShelfLog");
				
				machineNameFieldName = "MACHINENAME";
				
				conditions.add(new FormatQueryCondition("method == \"createShelfHistory\"", ENUM_FULLTEXT_COND.TRUE));

				if (StringUtils.isNotEmpty(filterGroup.get("ShelfName"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"SHELFNAME"
							, Arrays.asList(filterGroup.get("ShelfName").replace("-", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("State"))) {
					conditions.add(new FormatQueryCondition(String.format("STATE == \"%s\"", filterGroup.get("State")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("ProcessingState"))) {
					conditions.add(new FormatQueryCondition(String.format("PROCESSINGSTATE == \"%s\"", filterGroup.get("ProcessingState")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("Banned"))) {
					conditions.add(new FormatQueryCondition(String.format("BANNED == \"%s\"", filterGroup.get("Banned")), ENUM_FULLTEXT_COND.TRUE));
				}
			}
			
			if (filterProperties.containsKey("McslogResourceCraneLog")) {
				filterGroup = filterProperties.get("McslogResourceCraneLog");
				
				machineNameFieldName = "MACHINENAME";
				
				conditions.add(new FormatQueryCondition("method == \"createCraneHistory\"", ENUM_FULLTEXT_COND.TRUE));

				if (StringUtils.isNotEmpty(filterGroup.get("CraneName"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"CRANENAME"
							, Arrays.asList(filterGroup.get("CraneName").replace("-", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("State"))) {
					conditions.add(new FormatQueryCondition(String.format("STATE == \"%s\"", filterGroup.get("State")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("SubState"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"SUBSTATE"
							, Arrays.asList(filterGroup.get("SubState").replace("-", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("ProcessingState"))) {
					conditions.add(new FormatQueryCondition(String.format("PROCESSINGSTATE == \"%s\"", filterGroup.get("ProcessingState")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("TrCommand"))) {
					conditions.add(new FormatQueryCondition(String.format("TRANSPORTCOMMANDID == \"%s\"", filterGroup.get("TrCommand")), ENUM_FULLTEXT_COND.TRUE));
				}
			}
			
			if (filterProperties.containsKey("McslogResourceVehicleLog")) {
				filterGroup = filterProperties.get("McslogResourceVehicleLog");
				
				machineNameFieldName = "MACHINENAME";
				
				conditions.add(new FormatQueryCondition("method == \"createVehicleHistory\"", ENUM_FULLTEXT_COND.TRUE));

				if (StringUtils.isNotEmpty(filterGroup.get("VehicleName"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"VEHICLENAME"
							, Arrays.asList(filterGroup.get("VehicleName").replace("-", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("State"))) {
					conditions.add(new FormatQueryCondition(String.format("STATE == \"%s\"", filterGroup.get("State")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("SubState"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"SUBSTATE"
							, Arrays.asList(filterGroup.get("SubState").replace("-", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("ProcessingState"))) {
					conditions.add(new FormatQueryCondition(String.format("PROCESSINGSTATE == \"%s\"", filterGroup.get("ProcessingState")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("TrCommand"))) {
					conditions.add(new FormatQueryCondition(String.format("TRANSPORTCOMMANDID == \"%s\"", filterGroup.get("TrCommand")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("Carrier"))) {
					conditions.add(new FormatQueryCondition(String.format("CARRIER == \"%s\"", filterGroup.get("Carrier")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("TransferPort"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"TRANSFERPORTNAME"
							, Arrays.asList(filterGroup.get("TransferPort").replace("-", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("IdReadState"))) {
					conditions.add(new FormatQueryCondition(String.format("IDREADSTATE == \"%s\"", filterGroup.get("IdReadState")), ENUM_FULLTEXT_COND.TRUE));
				}
			}
			
			if (filterProperties.containsKey("McslogResourceStorageLog")) {
				filterGroup = filterProperties.get("McslogResourceStorageLog");
				
				machineNameFieldName = "MACHINENAME";
				
				conditions.add(new FormatQueryCondition("method == \"createStorageFullHistory\"", ENUM_FULLTEXT_COND.TRUE));

				if (StringUtils.isNotEmpty(filterGroup.get("State"))) {
					conditions.add(new FormatQueryCondition(String.format("STATE == \"%s\"", filterGroup.get("State")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("FullState"))) {
					conditions.add(new FormatQueryCondition(String.format("FULLSTATE == \"%s\"", filterGroup.get("FullState")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("ProcessingState"))) {
					conditions.add(new FormatQueryCondition(String.format("PROCESSINGSTATE == \"%s\"", filterGroup.get("ProcessingState")), ENUM_FULLTEXT_COND.TRUE));
				}
			}
			
			if (filterProperties.containsKey("McslogTransportReturnLog")) {
				filterGroup = filterProperties.get("McslogTransportReturnLog");
				
				conditions.add(new FormatQueryCondition("method == \"createTransportJobHistory\"", ENUM_FULLTEXT_COND.TRUE));
				
				if (StringUtils.isNotEmpty(filterGroup.get("Carrier"))) {
					conditions.add(new FormatQueryCondition(String.format("CARRIER == \"%s\"", filterGroup.get("Carrier")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("LotID"))) {
					conditions.add(new FormatQueryCondition(String.format("LOTID == \"%s\"", filterGroup.get("LotID")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("JobID"))) {
					conditions.add(new FormatQueryCondition(String.format("TRANSPORTJOBID == \"%s\"", filterGroup.get("JobID")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("CommandID"))) {
					conditions.add(new FormatQueryCondition(String.format("TRANSPORTCOMMANDID == \"%s\"", filterGroup.get("CommandID")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if ("False".equalsIgnoreCase(filterGroup.get("State"))) {
					conditions.add(new FormatQueryCondition("(STATE==\"COMPLETED\" or STATE==\"CANCELED\")", ENUM_FULLTEXT_COND.TRUE));
				}
			}
			
			if (filterProperties.containsKey("McslogTransportReturnJobLog")) {
				filterGroup = filterProperties.get("McslogTransportReturnJobLog");
				
				conditions.add(new FormatQueryCondition("method == \"createTransportJobHistory\"", ENUM_FULLTEXT_COND.TRUE));
				
				if (StringUtils.isNotEmpty(filterGroup.get("Carrier"))) {
					conditions.add(new FormatQueryCondition(String.format("CARRIER == \"%s\"", filterGroup.get("Carrier")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("LotID"))) {
					conditions.add(new FormatQueryCondition(String.format("LOTID == \"%s\"", filterGroup.get("LotID")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("JobID"))) {
					conditions.add(new FormatQueryCondition(String.format("TRANSPORTJOBID == \"%s\"", filterGroup.get("JobID")), ENUM_FULLTEXT_COND.TRUE));
				}
			}
			
			if (filterProperties.containsKey("McslogTransportReturnCommandLog")) {
				filterGroup = filterProperties.get("McslogTransportReturnCommandLog");
				
				conditions.add(new FormatQueryCondition("method == \"createTransportCommandHistory\"", ENUM_FULLTEXT_COND.TRUE));
				
				if (StringUtils.isNotEmpty(filterGroup.get("Carrier"))) {
					conditions.add(new FormatQueryCondition(String.format("CARRIER == \"%s\"", filterGroup.get("Carrier")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("CommandID"))) {
					conditions.add(new FormatQueryCondition(String.format("TRANSPORTCOMMANDID == \"%s\"", filterGroup.get("CommandID")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("SourceUnit"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"SOURCEUNITNAME"
							, Arrays.asList(filterGroup.get("SourceUnit").replace("-", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("DestUnit"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionAnd(
							"DESTUNITNAME"
							, Arrays.asList(filterGroup.get("DestUnit").replace("-", "_").split("_"))
							, ENUM_RANGE_SEARCH_OPTION.EXACT, true)
						, ENUM_FULLTEXT_COND.TRUE));
				}
			}
			
			if (filterProperties.containsKey("McslogTransportReturnJobFailLog")) {
				filterGroup = filterProperties.get("McslogTransportReturnJobFailLog");
				
				conditions.add(new FormatQueryCondition("method == \"createTransportJobFailHistory\"", ENUM_FULLTEXT_COND.TRUE));
				
				if (StringUtils.isNotEmpty(filterGroup.get("Carrier"))) {
					conditions.add(new FormatQueryCondition(String.format("CARRIER == \"%s\"", filterGroup.get("Carrier")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("LotID"))) {
					conditions.add(new FormatQueryCondition(String.format("LOTID == \"%s\"", filterGroup.get("LotID")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("JobID"))) {
					conditions.add(new FormatQueryCondition(String.format("TRANSPORTJOBID == \"%s\"", filterGroup.get("JobID")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("Reason"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionIn(
							"REASON"
							, Arrays.asList(filterGroup.get("Reason").split(",")))
						)
					);
				}
			}
			
			if (filterProperties.containsKey("McslogTransportReturnCommandFailLog")) {
				filterGroup = filterProperties.get("McslogTransportReturnCommandFailLog");
				
				conditions.add(new FormatQueryCondition("method == \"createTransportCommandFailHistory\"", ENUM_FULLTEXT_COND.TRUE));
				
				if (StringUtils.isNotEmpty(filterGroup.get("Carrier"))) {
					conditions.add(new FormatQueryCondition(String.format("CARRIER == \"%s\"", filterGroup.get("Carrier")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("CommandID"))) {
					conditions.add(new FormatQueryCondition(String.format("TRANSPORTCOMMANDID == \"%s\"", filterGroup.get("CommandID")), ENUM_FULLTEXT_COND.TRUE));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("Reason"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionIn(
							"REASON"
							, Arrays.asList(filterGroup.get("Reason").split(",")))
						)
					);
				}
			}
			
			if (filterProperties.containsKey("McslogTransportJobState")
					|| filterProperties.containsKey("McslogTransportCommandState")) {
				filterGroup = (Map<String, String>)Objects.requireNonNullElse(
						filterProperties.get("McslogTransportJobState"), filterProperties.get("McslogTransportCommandState"));
				
				if (StringUtils.isNotEmpty(filterGroup.get("States"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionIn(
							"STATE"
							, Arrays.asList(filterGroup.get("States").split(",")))
						)
					);
				}
			}
			
			if (filterProperties.containsKey("McslogMachine")) {
				filterGroup = filterProperties.get("McslogMachine");
				
				if (StringUtils.isNotEmpty(filterGroup.get("MachineTypes"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionIn(
							"MACHINETYPE"
							, Arrays.asList(filterGroup.get("MachineTypes").split(",")))
					));
				}
				
				if (StringUtils.isNotEmpty(filterGroup.get("MachineNames"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionOr(
							machineNameFieldName
							, Arrays.asList(filterGroup.get("MachineNames").split(","))
							, ENUM_RANGE_SEARCH_OPTION.EXACT
							, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				}
			}
			
			if (filterProperties.containsKey("McslogMachineTransport")) {
				filterGroup = filterProperties.get("McslogMachineTransport");
				
				if (StringUtils.isNotEmpty(filterGroup.get("MachineNames"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionOr(
							"TRANSPORTMACHINENAME"
							, Arrays.asList(filterGroup.get("MachineNames").split(","))
							, ENUM_RANGE_SEARCH_OPTION.EXACT
							, true))
					);
				} else {
					if (StringUtils.isNotEmpty(filterGroup.get("MachineTypes"))) {
						conditions.add(new FormatQueryCondition(
							LogpressoConditionUtil.createQueryConditionIn(
								"TRANSPORTTYPE"
								, Arrays.asList(filterGroup.get("MachineTypes").split(",")))
							)
						);
					}
				}
			}
			
			if (filterProperties.containsKey("McslogMachineSource")) {
				filterGroup = filterProperties.get("McslogMachineSource");
				
				if (StringUtils.isNotEmpty(filterGroup.get("MachineNames"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionOr(
							"SOURCEMACHINENAME"
							, Arrays.asList(filterGroup.get("MachineNames").split(","))
							, ENUM_RANGE_SEARCH_OPTION.EXACT
							, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				} else {
					if (StringUtils.isNotEmpty(filterGroup.get("MachineTypes"))) {
						conditions.add(new FormatQueryCondition(
							LogpressoConditionUtil.createQueryConditionIn(
								"SOURCEMACHINETYPE"
								, Arrays.asList(filterGroup.get("MachineTypes").split(",")))
							)
						);
					}
				}
			}
			
			if (filterProperties.containsKey("McslogMachineDest")) {
				filterGroup = filterProperties.get("McslogMachineDest");
				
				if (StringUtils.isNotEmpty(filterGroup.get("MachineNames"))) {
					conditions.add(new FormatQueryCondition(
						LogpressoConditionUtil.createQueryConditionOr(
							"DESTMACHINENAME"
							, Arrays.asList(filterGroup.get("MachineNames").split(","))
							, ENUM_RANGE_SEARCH_OPTION.EXACT
							, true)
						, ENUM_FULLTEXT_COND.TRUE)
					);
				} else {
					if (StringUtils.isNotEmpty(filterGroup.get("MachineTypes"))) {
						conditions.add(new FormatQueryCondition(
							LogpressoConditionUtil.createQueryConditionIn(
								"DESTMACHINETYPE"
								, Arrays.asList(filterGroup.get("MachineTypes").split(",")))
							)
						);
					}
				}
			}
			
			if (filterProperties.containsKey("McslogTimeRange")) {
				filterGroup = filterProperties.get("McslogTimeRange");
				
				var from = filterGroup.get("DateTimeFrom");
				var to = filterGroup.get("DateTimeTo");
				
				queryBuilder.append("set from=\"" + from + "\"");
				queryBuilder.append(" | set to=\"" + to + "\"");
			}
			

			var conditionFulltext = new StringBuilder();
			var conditionNormal = new StringBuilder();
			
			for (FormatQueryCondition condition : conditions) {
				if (condition.isFulltextCondition == ENUM_FULLTEXT_COND.TRUE) {
					if (conditionFulltext.length() != 0) {
						conditionFulltext.append("\n and ");
					}
					
					conditionFulltext.append(condition.condition);
				} else {
					conditionNormal.append("\n | search ");
					conditionNormal.append(condition.condition);
				}
			}
			
			var tableNameSet = new HashSet<String>();
			
			for (String fab : fabs) {
				tableNameSet.add(fabTablesMap.get(fab));
			}
			
			var tableNames = String.join(",", tableNameSet);
			
			if (isFulltext) {
				if (conditionFulltext.length() == 0) {
					conditionFulltext.append("\"\"");
				}

				queryBuilder.append(String.format(" | fulltext from=$(\"from\") to=$(\"to\")\n%s from %s ", conditionFulltext.toString(), tableNames));
			} else {
				queryBuilder.append(" | table from=$(\"from\") to=$(\"to\") " + String.join(", ", tableNameSet));
			}
			
			queryBuilder.append(conditionNormal.toString());
			
			queries.add(new ExtractCommonFilterResult(site, tableNames, queryBuilder.toString()));
		} catch (Exception e) {
			logger.error("", e);
		}

		return queries;
	}
}
