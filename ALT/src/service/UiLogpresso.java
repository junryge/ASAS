@Service("USER_IF_LOG")
public class UiLogpresso {
	private static final Logger logger = LoggerFactory.getLogger(UiLogpresso.class);
	private static final String MethodLog = "USER_IF_LOG#{} : userId={}, elapsed time={}ms, query={}";

	private static final String GRID_LAYOUT_FILE_PATH = "gridLayout";

	private static boolean isEnabled = false;

	public static void initialize() {
		isEnabled = true;
	}

	public boolean isAlive() {
		return true;
	}

	/**
	 * 비동기 처리 결과를 조회
	 *
	 * @param asyncKey
	 * @param userId
	 * @return
	 */
	public List<Map<String, Object>> getAsyncResult(String asyncKey, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		List<Map<String, Object>> returnList = new ArrayList<Map<String, Object>>();
		String query = "AsyncKey : " + asyncKey;

		try {
			returnList = AsyncUtil.get(asyncKey);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnList;
	}
	
	/**
	 * Grid 레이아웃 파일로 저장
	 *
	 * @param key
	 * @param hasSuffixUserId
	 * @param contents
	 * @param userId
	 * @return
	 */
	public boolean saveGridLayout(String key, boolean hasSuffixUserId, String contents, String userId) {
		if (!isEnabled)
			return false;
		long start = System.currentTimeMillis();

		if (hasSuffixUserId == false) {
			SecurityUtil.assertAccessLevel(AccessLevel.SystemAdministrator);
		}
		
		boolean result = false;

		String fileName = String.format("%s%s.xml", StringUtils.trim(key),
				(hasSuffixUserId ? "_" + userId : ""));
		String filePath = GRID_LAYOUT_FILE_PATH + File.separator + fileName;

		result = Util.writeFileString(filePath, contents);
		
		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start));
		return result;
	}

	/**
	 * Grid 레이아웃 파일에서 불러오기
	 *
	 * @param key
	 * @param userId
	 * @return
	 */
	public String loadGridLayout(String key, boolean hasSuffixUserId, String userId) {
		if (!isEnabled)
			return null;
		long start = System.currentTimeMillis();
		
		String contents = "";

		String fileName = String.format("%s%s.xml", StringUtils.trim(key),
				(hasSuffixUserId ? "_" + userId : ""));
		String filePath = GRID_LAYOUT_FILE_PATH + File.separator + fileName;
		
		contents = Util.readFileString(filePath);

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start));
		return contents;
	}

	/*
	 * =============================================================================
	 * = Start MCSLOG API
	 * =============================================================================
	 * =
	 */
	public List<String> getMasterMachineListAreaNames(String site, List<String> fabs, boolean hasMongodb,
			String userId) {
		if (!isEnabled)
			return null;
		long start = System.currentTimeMillis();

		SecurityUtil.assertNull(site, fabs);

		List<String> dataResult = new ArrayList<String>();
		String query = "";

		try {
			List<String> finalResult = new ArrayList<String>();

			McslogTablesCollection tables = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.MASTER_MACHINELIST);

			if (hasMongodb) {
				for (String fab : fabs) {
					HashMap<String, Object> args = new HashMap<String, Object>();
					args.put("FabNames", String.join("', '", fabs));
					args.put("GroupingArea", "True");

					var bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_MACHINELIST_FILTER", args));
					var partResult = MongodbAPI.aggregate(fab, tables.get(site, fab), bsonMatch).toList();

					if (partResult != null) {
						partResult.forEach(row -> finalResult.add(row.get("_id").toString()));
					}

					query = bsonMatch.toString();
				}
			} else {
				var machineVo = new McslogMachineVo();
				// 2022.0628 X0122410 fabSite 추가
				machineVo.setFabSite(site);
				machineVo.setSelectFab(fabs);

				query = LogpressoMcslogQuery.getAreaBayQueryParser(machineVo);

				var partResult = LogpressoAPI.executeQuery(site, query);

				if (partResult != null) {
					partResult.forEach(row -> finalResult
							.add(Objects.toString(row.entrySet().iterator().next().getValue(), null)));
				}
			}

			dataResult = finalResult.stream().distinct().sorted().collect(Collectors.toList());
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return dataResult;
	}

	public List<String> getMasterMachineListBayNames(String site, List<String> fabs, boolean hasMongodb,
			String areaName, String userId) {
		if (!isEnabled)
			return null;
		long start = System.currentTimeMillis();

		SecurityUtil.assertNull(site, fabs);

		List<String> dataResult = new ArrayList<String>();
		String query = "";

		try {
			List<String> finalResult = new ArrayList<String>();

			McslogTablesCollection tables = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.MASTER_MACHINELIST);

			if (hasMongodb) {
				for (String fab : fabs) {
					HashMap<String, Object> args = new HashMap<String, Object>();
					args.put("FabNames", String.join("', '", fabs));
					args.put("AreaName", "ALL".equals(areaName) ? "" : areaName);
					args.put("GroupingBay", "True");

					var bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_MACHINELIST_FILTER", args));
					var partResult = MongodbAPI.aggregate(fab, tables.get(site, fab), bsonMatch).toList();

					if (partResult != null) {
						partResult.forEach(row -> finalResult.add(row.get("_id").toString()));
					}

					query = bsonMatch.toString();
				}
			} else {
				var machineVo = new McslogMachineVo();
				// 2022.0628 X0122410 fabSite 추가
				machineVo.setFabSite(site);
				machineVo.setSelectFab(fabs);
				machineVo.setAreaName(areaName);

				query = LogpressoMcslogQuery.getAreaBayQueryParser(machineVo);

				var partResult = LogpressoAPI.executeQuery(site, query);

				if (partResult != null) {
					partResult.forEach(row -> finalResult
							.add(Objects.toString(row.entrySet().iterator().next().getValue(), null)));
				}
			}

			dataResult = finalResult.stream().distinct().sorted().collect(Collectors.toList());
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return dataResult;
	}

	public List<String> getMasterMachineListType(String site, List<String> fabs, boolean hasMongodb, String userId) {
		if (!isEnabled)
			return null;
		long start = System.currentTimeMillis();

		SecurityUtil.assertNull(site, fabs);

		List<String> dataResult = new ArrayList<String>();
		String query = "";

		try {
			List<String> finalResult = new ArrayList<String>();

			McslogTablesCollection tables = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.MASTER_MACHINELIST);

			if (hasMongodb) {
				for (String fab : fabs) {
					HashMap<String, Object> args = new HashMap<String, Object>();
					args.put("FabNames", String.join("', '", fabs));
					args.put("GroupingType", "True");

					var bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_MACHINELIST_FILTER", args));
					var partResult = MongodbAPI.aggregate(fab, tables.get(site, fab), bsonMatch).toList();

					if (partResult != null) {
						partResult.forEach(row -> finalResult.add(row.get("_id").toString()));
					}

					query = bsonMatch.toString();
				}
			} else {
				var queryBuilder = new StringBuilder(LogpressoMcslogQuery.sGetMachineQuery);
				var machineVo = new McslogMachineVo();
				// 2022.0628 X0122410 fabSite 추가
				machineVo.setFabSite(site);
				machineVo.setSelectFab(fabs);

				// FAB 선택 machineVo SecsFab 사용
				if (machineVo.getSelectFab() != null && machineVo.getSelectFab().size() > 0) {
					StringBuilder sFab = new StringBuilder();
					// SHOPNAME == FAB
					sFab.append(
							LogpressoMcslogQuery.sCRLF + String.format(LogpressoMcslogQuery.sSearch_in, "SHOPNAME"));

					for (String s : machineVo.getSelectFab()) {
						if (s.indexOf(LogpressoMcslogQuery.sALL) >= 0) {
							sFab = null;
							break;
						} else {
							sFab.append(LogpressoMcslogQuery.getColumnFromFab(machineVo.getFabSite(), s));
						}
					}

					if (sFab != null && !(sFab.toString().isEmpty())) {
						if (sFab.toString().indexOf("(") >= 0) {
							sFab.append(" )");
						} // search in ( ... )
						queryBuilder.append(sFab.toString());
					}
				}

				// Sort
				queryBuilder.append(" | stats count by TYPE | fields TYPE | sort TYPE");

				query = queryBuilder.toString();

				var partResult = LogpressoAPI.executeQuery(site, query);

				if (partResult != null) {
					partResult.forEach(row -> finalResult
							.add(Objects.toString(row.entrySet().iterator().next().getValue(), null)));
				}
			}

			dataResult = finalResult.stream().distinct().sorted().collect(Collectors.toList());
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return dataResult;
	}

	public List<String> getMasterMachineListNames(String site, List<String> fabs, boolean hasMongodb, String areaName,
			String bayName, List<String> machineTypes, String userId) {
		if (!isEnabled)
			return null;
		long start = System.currentTimeMillis();

		SecurityUtil.assertNull(site, fabs);

		List<String> dataResult = new ArrayList<String>();
		String query = "";

		try {
			List<String> finalResult = new ArrayList<String>();

			McslogTablesCollection tables = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.MASTER_MACHINELIST);

			if (hasMongodb) {
				for (String fab : fabs) {
					HashMap<String, Object> args = new HashMap<String, Object>();
					args.put("FabNames", String.join("', '", fabs));
					args.put("AreaName", "ALL".equals(areaName) ? "" : areaName);
					args.put("BayName", "ALL".equals(bayName) ? "" : bayName);
					args.put("MachineTypes", machineTypes.contains("ALL") ? "" : String.join("', '", machineTypes));
					args.put("GroupingId", "True");

					var bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_MACHINELIST_FILTER", args));
					var partResult = MongodbAPI.aggregate(fab, tables.get(site, fab), bsonMatch).toList();

					if (partResult != null) {
						partResult.forEach(row -> finalResult.add(row.get("_id").toString()));
					}

					query = bsonMatch.toString();
				}
			} else {
				var machineVo = new McslogMachineVo();
				// 2022.0628 X0122410 fabSite 추가
				machineVo.setFabSite(site);
				machineVo.setSelectFab(fabs);
				machineVo.setAreaName(areaName);
				machineVo.setBayName(bayName);
				machineVo.setMachineType(machineTypes);

				query = LogpressoMcslogQuery.getMachineQueryParser(machineVo);

				var partResult = LogpressoAPI.executeQuery(site, query);

				if (partResult != null) {
					partResult.forEach(row -> finalResult
							.add(Objects.toString(row.entrySet().iterator().next().getValue(), null)));
				}
			}

			dataResult = finalResult.stream().distinct().sorted().collect(Collectors.toList());
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return dataResult;
	}

	public List<Map<String, Object>> getCommMsgNameList(final String fabSite, final String userId) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertNull(fabSite);

		long start = System.currentTimeMillis();

		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();

		String sQuery = null;

		try {
			sQuery = "memlookup name=comm_msg_name | sort COMM_MSG";

			// 2022.09.05 X0122410 fabSite 추가
			result = LogpressoAPI.responseResult(fabSite, sQuery);
		} catch (Exception e) {
			logger.error("An error while running getCommMsgNameList", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				sQuery);

		return result;
	}

	public List<Map<String, Object>> getOperationNameList(final String fabSite, final String userId) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertNull(fabSite);

		long start = System.currentTimeMillis();

		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();

		String sQuery = null;

		try {
			sQuery = "memlookup name=operation_name | sort OPERATION";

			// 2022.09.05 X0122410 fabSite 추가
			result = LogpressoAPI.responseResult(fabSite, sQuery);
		} catch (Exception e) {
			logger.error("An error while running getOperationNameList", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				sQuery);

		return result;
	}

	public List<Map<String, Object>> getMessageNameList(final String fabSite, final String userId) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertNull(fabSite);

		long start = System.currentTimeMillis();

		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();

		String sQuery = null;

		try {
			sQuery = "memlookup name=message_name | sort MESSAGE";

			// 2022.09.05 X0122410 fabSite 추가
			result = LogpressoAPI.responseResult(fabSite, sQuery);
		} catch (Exception e) {
			logger.error("An error while running getMessageNameList", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				sQuery);

		return result;
	}

	public Map<String, Object> getTotalLogListForMongodb(final String fabSite, List<String> fabs, List<String> levels,
			List<String> machineTypes, List<String> machineNames, String searchOption, String process, String thread,
			String gtxnId, String transactionId, String messageName, String comMsgName, String operationName,
			String carrier, String commandId, String unit, String text, String fulltext, String messageName_m,
			String comMsgName_m, String operationName_m, String from, String to, String table, String pageNum,
			String rowNum, boolean hasTotalCount, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		SecurityUtil.assertNull(fabSite, fabs);

		Map<String, Object> returnMap = new HashMap<>(Map.of("rows", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			if (rowNum == null || rowNum.equals("")) {
				rowNum = "1000";
			}

			if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
				fabs = LogpressoMcslogQuery.getFabsList(fabSite);
			}

			int limit = Integer.parseInt(rowNum);
			List<Map<String, Object>> dataResult = new ArrayList<>();

			boolean isViewTable = levels.stream()
					.allMatch(l -> StringUtils.equalsAny(l.toUpperCase(), "WELL", "WARN", "ERROR", "FATAL"));

			for (String fab : fabs) {
				String collection = "";
				String suffix = MongodbMcslogQuery.getSuffix(fab);

				collection = isViewTable
						? QueryUtil.getTsViewPartitionCollection("ts_data_view_" + suffix,
								QueryUtil.convertToDate(from), QueryUtil.convertToDate(to))
						: "ts_data_view_" + suffix;

				HashMap<String, Object> args = new HashMap<String, Object>();
				args.put("Collection", collection);
				args.put("From", QueryUtil.convertToUtcTimezone(from));
				args.put("To", QueryUtil.convertToUtcTimezone(to));
				args.put("Level", "ALL".equals(levels.get(0)) ? "" : String.join("','", levels));
				args.put("SearchOption", searchOption);
				args.put("HasCondition", !StringUtils.isAllBlank(process, thread, gtxnId, transactionId, comMsgName,
						messageName, operationName, carrier, commandId, unit, text));
				args.put("MachineName", String.join("','", machineNames));
				args.put("MachineType", String.join("','", machineTypes));
				args.put("ProcessName", process);
				args.put("ThreadName", thread);
				args.put("GtxnID", gtxnId);
				args.put("TransactionID", transactionId);
				args.put("ComMsgName", comMsgName.replace("*", ".*"));
				args.put("BpelName", messageName.replace("*", ".*"));
				args.put("OperationName", operationName);
				args.put("CarrierName", carrier);
				args.put("CommandID", commandId);
				args.put("UnitName", unit);
				args.put("Text", text);
				args.put("FullText", "or".equals(searchOption) ? "" : StringUtils.firstNonBlank(fulltext, carrier));
				args.put("Key",
						lastKeys == null || lastKeys.containsKey(collection) == false ? "" : lastKeys.get(collection));
				args.put("Limit", limit);

				var executionTime = System.currentTimeMillis();
				var bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_TOTAL_LOG", args));
				var partResult = MongodbAPI.aggregate(fab, collection, bsonMatch).toList(limit);

				logger.info("USER_IF_LOG#{} : Execution Time {}ms", ReflectionUtil.getCurrentMethodName(),
						System.currentTimeMillis() - executionTime);

				if (partResult != null) {
					dataResult.addAll(partResult);
				}

				query = bsonMatch.toString();
			}

			dataResult = dataResult.stream()
					.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString())).limit(limit)
					.collect(Collectors.toList());

			if (lastKeys == null) {
				lastKeys = new HashMap<String, Object>();
			}

			for (Map<String, Object> row : dataResult) {
				if (row.get("_table") != null) {
					lastKeys.put(row.get("_table").toString(), row.get("Key"));
				}
			}

			returnMap.put("rows", dataResult);
			returnMap.put("total", 0);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getTotalLogList(final String fabSite, List<String> fabs, List<String> levels,
			List<String> machineTypes, List<String> machineNames, String searchOption, String process, String thread,
			String gtxnId, String transactionId, String messageName, String comMsgName, String operationName,
			String carrier, String commandId, String unit, String text, String fulltext, String messageName_m,
			String comMsgName_m, String operationName_m, String from, String to, String table, String pageNum,
			String rowNum, boolean hasTotalCount, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		SecurityUtil.assertNull(fabSite, fabs);

		Map<String, Object> returnMap = new HashMap<>(Map.of("rows", List.of(), "lastKeys", Map.of()));
		String resultQuery = "";
		try {
			if (pageNum == null || pageNum.equals("")) {
				pageNum = "1";
			}

			if (rowNum == null || rowNum.equals("")) {
				rowNum = "100";
			}

			if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
				fabs = LogpressoMcslogQuery.getFabsList(fabSite);
			}

			McslogTotalVo totalVo = new McslogTotalVo();
			// 2022.0628 X0122410 fabSite 추가
			totalVo.setFabSite(fabSite);
			totalVo.setMachineType(machineTypes);
			totalVo.setMachineName(machineNames);
			totalVo.setFab(fabs);
			totalVo.setLevel(levels);
			totalVo.setSearchOption(searchOption);
			totalVo.setProcess(process);
			totalVo.setThread(thread);
			totalVo.setTransactionId(transactionId);
			totalVo.setMessageName(messageName);
			totalVo.setComMsgName(comMsgName);
			totalVo.setOperationName(operationName);
			totalVo.setCarrier(carrier);
			totalVo.setCommandId(commandId);
			totalVo.setUnit(unit);
			totalVo.setText(text);
			totalVo.setFulltext(fulltext);
			totalVo.setFrom(from);
			totalVo.setTo(to);
			totalVo.setTable(table);
			totalVo.setMessageName_m(messageName_m);
			totalVo.setComMsgName_m(comMsgName_m);
			totalVo.setOperationName_m(operationName_m);
			totalVo.setGtxnId(gtxnId);
			totalVo.setPageNum(pageNum);
			totalVo.setRowNum(rowNum);

			List<Map<String, Object>> dataList = null;
			long offset = (Long.parseLong(totalVo.getPageNum()) - 1) * Long.parseLong(totalVo.getRowNum());
			int limit = Integer.parseInt(totalVo.getRowNum());
			resultQuery = LogpressoMcslogQuery.getTotalLogListQueryParser(totalVo);

			if (resultQuery != null && !(resultQuery.isEmpty())) {
				String resultQuery2 = resultQuery;

				if (!(resultQuery2.contains("sort"))) {
					resultQuery2 += LogpressoMcslogQuery.sPipeLine + "limit " + offset + " " + limit; // 결과
					// 출력에 대해 limit을 적용한 쿼리
					// 2022.06.20 X0122410 _id 정렬조건 추가
					resultQuery2 += LogpressoMcslogQuery.sPipeLine + LogpressoMcslogQuery.sSort
							+ LogpressoMcslogQuery.s_TIME + LogpressoMcslogQuery.sComma + LogpressoMcslogQuery.s_ID; // 결과
					// 출력에 대해 time sort를 적용한 쿼리
				} else {
					resultQuery2 = resultQuery2.replace(LogpressoMcslogQuery.sPipeLine + LogpressoMcslogQuery.sSort,
							LogpressoMcslogQuery.sPipeLine + "limit " + offset + " " + limit + " "
									+ LogpressoMcslogQuery.sPipeLine + LogpressoMcslogQuery.sSort); // 결과
					// 출력에 대해 limit를 적용한 쿼리
				}

				resultQuery2 += String.format(LogpressoMcslogQuery.sEval, "No", "seq()") + LogpressoMcslogQuery.sPlus
						+ offset;
				resultQuery2 += " | eval COMM_MSG_NAME = nvl(nvl(COMMAND, MESSAGENAME), \"\")";
				// 2022.09.05 X0122410 fabSite 추가
				dataList = LogpressoAPI.executeQuery(fabSite, resultQuery2);
			}

			String sCnt = "0";
			if (dataList != null && dataList.size() > 0) {
				if (hasTotalCount) {
					// 2022.09.05 X0122410 fabSite 추가
					sCnt = LogpressoAPI.responseResult(fabSite, resultQuery + " | stats count").get(0).get("count")
							.toString();
				}
			}

			returnMap.put("total", sCnt);
			returnMap.put("rows", dataList);
		} catch (Exception e) {
			logger.error("An error while running getTotalLogList", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				resultQuery);

		return returnMap;
	}

	/* SecsLog */
	public List<Map<String, Object>> getSecsFabList(final String fabSite, final List<String> fabs,
			final String userId) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertNull(fabSite, fabs);

		long start = System.currentTimeMillis();

		McslogMachineVo machineVo = new McslogMachineVo();
		// 2022.0628 X0122410 fabSite 추가
		machineVo.setFabSite(fabSite);
		machineVo.setSelectFab(fabs);

		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();

		StringBuilder sQuery = new StringBuilder();
		try {
			String secsNameQuery = "memlookup name=machine_list | search isnotnull(MACHINETYPE) | eval SECSII=MACHINENAME, FAB=SHOPNAME | fields FAB, SECSII | sort SECSII";
			sQuery.append(secsNameQuery);

			// Type
			if (machineVo.getSelectFab() != null && machineVo.getSelectFab().size() > 0) {
				StringBuilder sMachine = new StringBuilder();
				sMachine.append(LogpressoMcslogQuery.sCRLF + String.format(LogpressoMcslogQuery.sSearch_in, "FAB"));

				for (String s : machineVo.getSelectFab()) {
					if (s.indexOf(LogpressoMcslogQuery.sALL) >= 0) {
						sMachine = null;
						break;
					} else {
						sMachine.append(LogpressoMcslogQuery.sComma + LogpressoMcslogQuery.sDoubleQuotation
								+ s.toUpperCase(Locale.ENGLISH) + LogpressoMcslogQuery.sAsterisk
								+ LogpressoMcslogQuery.sDoubleQuotation);
					}
				}

				if (sMachine != null && !(sMachine.toString().isEmpty())) {
					if (sMachine.toString().indexOf("(") >= 0) {
						sMachine.append(" )");
					} // search in ( ... )
					sQuery.append(sMachine.toString());
				}
			}

			// 2022.09.05 X0122410 fabSite 추가
			result = LogpressoAPI.responseResult(fabSite, sQuery.toString());
			// result = LogpressoAPI.responseResult(sQuery.toString());

		} catch (Exception e) {
			logger.error("An error while running getSecsFabList", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				sQuery.toString());

		return result;
	}

	public List<Map<String, Object>> getSecsFabListForMongodb(final String fabSite, final List<String> fabs,
			final String userId) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertNull(fabSite, fabs);

		long start = System.currentTimeMillis();

		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();

		try {
			for (String fab : fabs) {
				String suffix = MongodbMcslogQuery.getSuffix(fab);
				String collection = "master_" + suffix;

				var partialResult = MongodbAPI.find(fab, collection, Document.parse("{ TYPE: 'SECS_MACHINE' }"))
						.projection(Document.parse("{ SECSII: '$VALUE' }")).toList();

				result.addAll(partialResult);
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				"[]");

		return result;
	}

	public Map<String, Object> getSecsLogListForMongodb(final String fabSite, List<String> fabs, List<String> levels,
			List<String> hosts, String secs, String text, String secsTextConditionCheckBox, String from, String to,
			String pageNum, String rowNum, boolean hasTotalCount, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		SecurityUtil.assertNull(fabSite, fabs);

		Map<String, Object> returnMap = new HashMap<String, Object>();
		String query = "";

		try {
			if (rowNum == null || rowNum.equals("")) {
				rowNum = "1000";
			}

			if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
				fabs = LogpressoMcslogQuery.getFabsList(fabSite);
			}

			int limit = Integer.parseInt(rowNum);
			List<Map<String, Object>> dataResult = new ArrayList<>();

			for (String fab : fabs) {
				String suffix = MongodbMcslogQuery.getSuffix(fab);
				String collection = "secs_data_" + suffix;

				HashMap<String, Object> args = new HashMap<String, Object>();
				args.put("Collection", collection);
				args.put("From", QueryUtil.convertToUtcTimezone(from));
				args.put("To", QueryUtil.convertToUtcTimezone(to));
				args.put("Level", "ALL".equals(levels.get(0)) ? "" : String.join("','", levels));
				args.put("Host", hosts.size() == 0 ? "" : String.join("','", hosts));
				args.put("HasCondition", !StringUtils.isAllBlank(secs, text));
				args.put("Secs", secs);
				args.put("Text", text);
				args.put("SecsTextConditionCheckBox",
						StringUtils.isBlank(secsTextConditionCheckBox) ? "and" : secsTextConditionCheckBox);
				args.put("Key",
						lastKeys == null || lastKeys.containsKey(collection) == false ? "" : lastKeys.get(collection));
				args.put("Limit", limit);

				var bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_SECS_LOG", args));

				dataResult
						.addAll(MongodbAPI.aggregate(fab, collection, bsonMatch).maxTime(2, TimeUnit.MINUTES).toList());
				query = bsonMatch.toString();
			}

			dataResult = dataResult.stream()
					.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString())).limit(limit)
					.collect(Collectors.toList());

			if (lastKeys == null) {
				lastKeys = new HashMap<String, Object>();
			}

			for (Map<String, Object> row : dataResult) {
				if (row.get("_table") != null) {
					lastKeys.put(row.get("_table").toString(), row.get("Key"));
				}
			}

			returnMap.put("rows", dataResult);
			returnMap.put("total", 0);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getSecsLogList(final String fabSite, List<String> fabs, List<String> levels,
			List<String> hosts, String secs, String text, String secsTextConditionCheckBox, String from, String to,
			String pageNum, String rowNum, boolean hasTotalCount, String userId) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertNull(fabSite, fabs);

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<String, Object>();

		String resultQuery = "";

		try {
			if (pageNum == null || pageNum.equals("")) {
				pageNum = "1";
			}

			if (rowNum == null || rowNum.equals("")) {
				rowNum = "100";
			}

			if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
				fabs = LogpressoMcslogQuery.getFabsList(fabSite);
			}

			McslogSecsVo secsVo = new McslogSecsVo();
			secsVo.setFabSite(fabSite);
			secsVo.setFab(fabs);
			secsVo.setLevel(levels);
			secsVo.setHost(hosts);
			secsVo.setSecs(secs);
			secsVo.setText(text);
			secsVo.setSecsTextConditionCheckBox(secsTextConditionCheckBox);
			secsVo.setFrom(from);
			secsVo.setTo(to);
			secsVo.setPageNum(pageNum);
			secsVo.setRowNum(rowNum);

			List<Map<String, Object>> dataList = null;
			long offset = (Long.parseLong(secsVo.getPageNum()) - 1) * Long.parseLong(secsVo.getRowNum());
			int limit = Integer.parseInt(secsVo.getRowNum());
			resultQuery = LogpressoMcslogQuery.getSecsLogListQueryParser(secsVo);

			if (resultQuery != null && !(resultQuery.isEmpty())) {

				String resultQuery2 = resultQuery;
				if (!(resultQuery2.contains("sort"))) {
					// 2022.06.20 X0122410 _id 정렬조건 추가
					resultQuery2 += LogpressoMcslogQuery.sPipeLine + LogpressoMcslogQuery.sSort
							+ LogpressoMcslogQuery.s_TIME + LogpressoMcslogQuery.sComma + LogpressoMcslogQuery.s_ID; // 결과
					// 출력에 대해 time sort를 적용한 쿼리
				}
				resultQuery2 += LogpressoMcslogQuery.sPipeLine + "limit " + offset + " " + limit;// 결과 출력에 대해 limit을 적용한
				// 쿼리
				resultQuery2 += String.format(LogpressoMcslogQuery.sEval, "No", "seq()") + LogpressoMcslogQuery.sPlus
						+ offset;
				// 2022.09.05 X0122410 fabSite 추가
				dataList = LogpressoAPI.executeQuery(fabSite, resultQuery2);
			}

			String sCnt = "0";
			if (dataList != null && dataList.size() > 0) {
				if (hasTotalCount) {
					// 2022.09.05 X0122410 fabSite 추가
					sCnt = LogpressoAPI.responseResult(fabSite, resultQuery + " | stats count").get(0).get("count")
							.toString();
				}
			}

			returnMap.put("total", sCnt);
			returnMap.put("rows", dataList);
		} catch (Exception e) {
			logger.error("An error while running getSecsLogList", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				resultQuery);

		return returnMap;
	}

	/* RawLog */
	public List<Map<String, Object>> getSelectProcessListForMongodb(final String fabSite, final List<String> fabs,
			final List<String> types, final String userId) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertNull(fabSite, fabs);

		long start = System.currentTimeMillis();

		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();

		try {
			for (String fab : fabs) {
				String suffix = MongodbMcslogQuery.getSuffix(fab);
				String collection = "master_" + suffix;
				List<String> masterTypes = new ArrayList<>();

				if (types.contains("TS")) {
					masterTypes.add("TS_PROCESS");
				}

				if (types.contains("CS")) {
					masterTypes.add("CS_PROCESS");
				}

				if (types.contains("DS")) {
					masterTypes.add("DS_PROCESS");
				}

				if (types.contains("EI")) {
					masterTypes.add("EI_PROCESS");
				}

				for (String masterType : masterTypes) {
					var partialResult = MongodbAPI
							.find(fab, collection, Document.parse("{ TYPE: '" + masterType + "' }"))
							.projection(Document.parse("{ PROCESS: '$VALUE' }")).toList();

					result.addAll(partialResult);
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				"[]");

		return result;
	}

	public List<Map<String, Object>> getSelectProcessList(final String fabSite, final List<String> fabs,
			final List<String> types, final String userId) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertNull(fabSite, fabs);

		long start = System.currentTimeMillis();

		McslogMachineVo machineVo = new McslogMachineVo();
		// 2022.0628 X0122410 fabSite 추가
		machineVo.setFabSite(fabSite);
		machineVo.setSelectFab(fabs);
		machineVo.setSelectType(types);

		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();

		StringBuilder sQuery = new StringBuilder();
		try {
			String ProcessQuery = "memlookup name=ProcessList2 | sort PROCESS";
			sQuery.append(ProcessQuery);

			if (machineVo.getSelectType() != null && machineVo.getSelectType().size() > 0) {
				StringBuilder sLogType = new StringBuilder();
				sLogType.append(LogpressoMcslogQuery.sCRLF + String.format(LogpressoMcslogQuery.sSearch_in, "PROCESS"));

				for (String s : machineVo.getSelectType()) {
					if (s.indexOf(LogpressoMcslogQuery.sALL) >= 0) {
						sLogType = null;
						break;
					} else {
						sLogType.append(LogpressoMcslogQuery.sComma + LogpressoMcslogQuery.sDoubleQuotation
								+ s.toLowerCase(Locale.ENGLISH) + LogpressoMcslogQuery.sAsterisk
								+ LogpressoMcslogQuery.sDoubleQuotation);
					}
				}

				if (sLogType != null && !(sLogType.toString().isEmpty())) {
					if (sLogType.toString().indexOf("(") >= 0) {
						sLogType.append(" )");
					} // search in ( ... )
					sQuery.append(sLogType.toString());
				}
			}

			// Type
			if (machineVo.getSelectFab() != null && machineVo.getSelectFab().size() > 0) {
				StringBuilder sFabType = new StringBuilder();
				sFabType.append(LogpressoMcslogQuery.sCRLF + String.format(LogpressoMcslogQuery.sSearch_in, "FAB"));

				for (String s : machineVo.getSelectFab()) {
					if (s.indexOf(LogpressoMcslogQuery.sALL) >= 0) {
						sFabType = null;
						break;
					} else {

						sFabType.append(LogpressoMcslogQuery.sComma + LogpressoMcslogQuery.sDoubleQuotation
								+ s.toUpperCase(Locale.ENGLISH) + LogpressoMcslogQuery.sAsterisk
								+ LogpressoMcslogQuery.sDoubleQuotation);
					}
				}

				if (sFabType != null && !(sFabType.toString().isEmpty())) {
					if (sFabType.toString().indexOf("(") >= 0) {
						sFabType.append(" )");
					} // search in ( ... )
					sQuery.append(sFabType.toString());
				}
			}

			sQuery.append(" | stats count by PROCESS | fields PROCESS");

			// 2022.09.05 X0122410 fabSite 추가
			result = LogpressoAPI.responseResult(fabSite, sQuery.toString());
		} catch (Exception e) {
			logger.error("An error while running getSelectProcessList", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				sQuery.toString());

		return result;
	}

	public Map<String, Object> getRawLogListForMongodb(final String fabSite, List<String> fabs, List<String> levels,
			List<String> hosts, List<String> logs, String process, String text, String eiTextConditionCheckBox,
			String from, String to, String pageNum, String rowNum, boolean hasTotalCount, Map<String, Object> lastKeys,
			String userId) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertNull(fabSite, fabs);

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("rows", List.of(), "total", 0, "lastKeys", Map.of()));
		String query = "";

		try {
			if (rowNum == null || rowNum.equals("")) {
				rowNum = "100";
			}

			if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
				fabs = LogpressoMcslogQuery.getFabsList(fabSite);
			}

			int limit = Integer.parseInt(rowNum);
			List<Map<String, Object>> dataResult = new ArrayList<>();

			for (String fab : fabs) {
				String suffix = MongodbMcslogQuery.getSuffix(fab);
				List<String> collections = new ArrayList<>();

				if (logs.contains("TS")) {
					collections.add("ts_data_" + suffix);
				}

				if (logs.contains("CS")) {
					collections.add("cs_data_" + suffix);
				}

				if (logs.contains("DS")) {
					collections.add("ds_data_" + suffix);
				}

				if (logs.contains("EI")) {
					collections.add("ei_data_" + suffix);
				}

				for (String collection : collections) {
					HashMap<String, Object> args = new HashMap<String, Object>();
					args.put("Collection", collection);
					args.put("From", QueryUtil.convertToUtcTimezone(from));
					args.put("To", QueryUtil.convertToUtcTimezone(to));
					args.put("IsTS", String.valueOf(logs.contains("TS")));
					args.put("Level", "ALL".equals(levels.get(0)) ? "" : String.join("','", levels));
					args.put("Host", hosts.size() == 0 ? "" : String.join("','", hosts));
					args.put("Process", process == null ? null : process.toLowerCase());
					args.put("Text", "");

					if (StringUtils.isNotBlank(text)) {
						if ("and".equals(eiTextConditionCheckBox)) {
							args.put("Text", "(?=" + String.join(")(?=", text.split(",")) + ")");
						} else {
							args.put("Text", "(" + String.join(")|(", text.split(",")) + ")");
						}
					}

					args.put("Key", lastKeys == null || lastKeys.containsKey(collection) == false ? ""
							: lastKeys.get(collection));
					args.put("Limit", limit);

					var bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_RAW_LOG", args));

					dataResult.addAll(MongodbAPI.aggregate(fab, collection, bsonMatch).toList());

					query = bsonMatch.toString();
				}
			}

			dataResult = dataResult.stream()
					.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString())).limit(limit)
					.collect(Collectors.toList());

			if (lastKeys == null) {
				lastKeys = new HashMap<String, Object>();
			}

			for (Map<String, Object> row : dataResult) {
				if (row.get("_table") != null) {
					lastKeys.put(row.get("_table").toString(), row.get("Key"));
				}
			}

			returnMap.put("rows", dataResult);
			returnMap.put("total", 0);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getRawLogList(final String fabSite, List<String> fabs, List<String> levels,
			List<String> hosts, List<String> logs, String process, String text, String eiTextConditionCheckBox,
			String from, String to, String pageNum, String rowNum, boolean hasTotalCount, String userId) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertNull(fabSite, fabs);

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<String, Object>();
		String resultQuery = "";

		try {
			if (pageNum == null || pageNum.equals("")) {
				pageNum = "1";
			}

			if (rowNum == null || rowNum.equals("")) {
				rowNum = "100";
			}

			if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
				fabs = LogpressoMcslogQuery.getFabsList(fabSite);
			}

			McslogEiVo eiVo = new McslogEiVo();
			eiVo.setFabSite(fabSite);
			eiVo.setFab(fabs);
			eiVo.setLevel(levels);
			eiVo.setHost(hosts);
			eiVo.setLog(logs);
			eiVo.setProcess(process);
			eiVo.setText(text);
			eiVo.setEiTextConditionCheckBox(eiTextConditionCheckBox);
			eiVo.setFrom(from);
			eiVo.setTo(to);
			eiVo.setPageNum(pageNum);
			eiVo.setRowNum(rowNum);

			List<Map<String, Object>> dataList = null;
			long offset = (Long.parseLong(eiVo.getPageNum()) - 1) * Long.parseLong(eiVo.getRowNum());
			int limit = Integer.parseInt(eiVo.getRowNum());
			resultQuery = LogpressoMcslogQuery.getRawLogListQueryParser(eiVo);

			if (resultQuery != null && !(resultQuery.isEmpty())) {

				String resultQuery2 = resultQuery;
				if (!(resultQuery2.contains("sort"))) {
					// 2022.06.20 X0122410 _id 정렬조건 추가
					resultQuery2 += LogpressoMcslogQuery.sPipeLine + LogpressoMcslogQuery.sSort
							+ LogpressoMcslogQuery.s_TIME + LogpressoMcslogQuery.sComma + LogpressoMcslogQuery.s_ID; // 결과
					// 출력에 대해 time sort를 적용한 쿼리
				}
				resultQuery2 += LogpressoMcslogQuery.sPipeLine + "limit " + offset + " " + limit;// 결과 출력에 대해 limit을 적용한
				// 쿼리
				resultQuery2 += String.format(LogpressoMcslogQuery.sEval, "No", "seq()") + LogpressoMcslogQuery.sPlus
						+ offset;
				// 2022.09.05 X0122410 fabSite 추가
				dataList = LogpressoAPI.executeQuery(fabSite, resultQuery2);
			}

			String sCnt = "0";
			if (dataList != null && dataList.size() > 0) {
				if (hasTotalCount) {
					// 2022.09.05 X0122410 fabSite 추가
					sCnt = LogpressoAPI.responseResult(fabSite, resultQuery + " | stats count").get(0).get("count")
							.toString();
				}
			}

			returnMap.put("total", sCnt);
			returnMap.put("rows", dataList);
		} catch (Exception e) {
			logger.error("An error while running getRawLogList", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				resultQuery);

		return returnMap;
	}

	public List<Map<String, Object>> getTransactionLogAppNameListForMongodb(final String fabSite, List<String> fabs,
			final String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		SecurityUtil.assertNull(fabSite, fabs);

		List<Map<String, Object>> dataResult = new ArrayList<>();
		String query = "";

		try {
			if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
				fabs = LogpressoMcslogQuery.getFabsList(fabSite);
			}

			for (String fab : fabs) {
				String suffix = MongodbMcslogQuery.getSuffix(fab);
				String collection = "ts_end_data_" + suffix;

				var hourAgo = new Date(System.currentTimeMillis() - 3600 * 1000);

				HashMap<String, Object> args = new HashMap<String, Object>();
				args.put("From", QueryUtil.convertToUtcTimezone(QueryUtil.convertToQueryString(hourAgo)));
				args.put("To", QueryUtil.convertToUtcTimezone(QueryUtil.convertToQueryString(new Date())));

				var bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_TRANSACTION_LOG_APPNAME", args));
				var partResult = MongodbAPI.aggregate(fab, collection, bsonMatch).toList();

				if (partResult != null) {
					dataResult.addAll(partResult);
				}

				query = bsonMatch.toString();
			}

			dataResult = dataResult.stream().sorted(
					(o1, o2) -> o1.get("Application_Name").toString().compareTo(o2.get("Application_Name").toString()))
					.distinct().collect(Collectors.toList());
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return dataResult;
	}

	/* Transaction */
	public List<Map<String, Object>> getTransactionLogAppNameList(final String fabSite, List<String> fabs,
			final String userId) {
		if (!isEnabled)
			return null;
		SecurityUtil.assertNull(fabSite, fabs);

		long start = System.currentTimeMillis();
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		StringBuilder sQuery = new StringBuilder();

		try {
			String ProcessQuery = "table duration=1h ";
			sQuery.append(ProcessQuery);

			if (fabs != null && fabs.size() > 0) {
				if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
					fabs = LogpressoMcslogQuery.getFabsList(fabSite);
				}

				List<String> tableNames = new ArrayList<String>();
				for (int i = 0; i < fabs.size(); i++) {
					String tableName = LogpressoMcslogQuery.getTransactionLogFabTableList(fabSite, fabs.get(i));
					if (!tableNames.contains(tableName))
						tableNames.add(tableName);
				}
				sQuery.append(String.join(", ", tableNames));
			}

			sQuery.append(" | stats count by Application_Name | fields Application_Name | sort Application_Name");
			// 2022.09.05 X0122410 fabSite 추가
			result = LogpressoAPI.executeQuery(fabSite, sQuery.toString());
		} catch (Exception e) {
			logger.error("An error while running getTransactionLogAppNameList", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				sQuery.toString());

		return result;
	}

	public List<Map<String, Object>> getTransactionLogTxNameListForMongodb(final String fabSite, List<String> fabs,
			final String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		SecurityUtil.assertNull(fabSite, fabs);

		List<Map<String, Object>> dataResult = new ArrayList<>();
		String query = "";

		try {
			if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
				fabs = LogpressoMcslogQuery.getFabsList(fabSite);
			}

			for (String fab : fabs) {
				String suffix = MongodbMcslogQuery.getSuffix(fab);
				String collection = "ts_end_data_" + suffix;

				var hourAgo = new Date(System.currentTimeMillis() - 3600 * 1000);

				HashMap<String, Object> args = new HashMap<String, Object>();
				args.put("From", QueryUtil.convertToUtcTimezone(QueryUtil.convertToQueryString(hourAgo)));
				args.put("To", QueryUtil.convertToUtcTimezone(QueryUtil.convertToQueryString(new Date())));

				var bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_TRANSACTION_LOG_TXNAME", args));
				var partResult = MongodbAPI.aggregate(fab, collection, bsonMatch).toList();

				if (partResult != null) {
					dataResult.addAll(partResult);
				}

				query = bsonMatch.toString();
			}

			dataResult = dataResult.stream().sorted(
					(o1, o2) -> o1.get("Transaction_Name").toString().compareTo(o2.get("Transaction_Name").toString()))
					.distinct().collect(Collectors.toList());
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return dataResult;
	}

	public List<Map<String, Object>> getTransactionLogTxNameList(final String fabSite, List<String> fabs,
			final String userId) {
		if (!isEnabled)
			return null;
		SecurityUtil.assertNull(fabSite, fabs);

		long start = System.currentTimeMillis();
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		StringBuilder sQuery = new StringBuilder();

		try {
			String ProcessQuery = "table duration=1h ";
			sQuery.append(ProcessQuery);

			if (fabs != null && fabs.size() > 0) {
				if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
					fabs = LogpressoMcslogQuery.getFabsList(fabSite);
				}

				List<String> tableNames = new ArrayList<String>();
				for (int i = 0; i < fabs.size(); i++) {
					String tableName = LogpressoMcslogQuery.getTransactionLogFabTableList(fabSite, fabs.get(i));
					if (!tableNames.contains(tableName))
						tableNames.add(tableName);
				}
				sQuery.append(String.join(", ", tableNames));
			}

			sQuery.append(" | stats count by Transaction_Name | fields Transaction_Name | sort Transaction_Name");
			// 2022.09.05 X0122410 fabSite 추가
			result = LogpressoAPI.executeQuery(fabSite, sQuery.toString());

		} catch (Exception e) {
			logger.error("An error while running getTransactionLogTxNameList", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				sQuery.toString());

		return result;
	}

	public Map<String, Object> getTransactionLogItemsForMongodb(final String fabSite, List<String> fabs,
			List<String> appNames, List<String> txNames, String txID, String elapsedFrom, String elapsedTo, String from,
			String to, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		SecurityUtil.assertNull(fabSite, fabs);

		Map<String, Object> returnMap = new HashMap<String, Object>();
		String query = "";

		try {
			if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
				fabs = LogpressoMcslogQuery.getFabsList(fabSite);
			}

			List<Map<String, Object>> dataResult = new ArrayList<>();

			for (String fab : fabs) {
				String suffix = MongodbMcslogQuery.getSuffix(fab);
				String collection = "ts_end_data_" + suffix;

				HashMap<String, Object> args = new HashMap<String, Object>();
				args.put("Collection", collection);
				args.put("From", QueryUtil.convertToUtcTimezone(from));
				args.put("To", QueryUtil.convertToUtcTimezone(to));
				args.put("Appname", "ALL".equals(appNames.get(0)) ? "" : appNames.get(0));
				args.put("Txname", txNames.size() == 0 ? "" : txNames.get(0).replace("*", ".*"));
				args.put("TxID", txID.replace("*", ".*"));
				args.put("ElapsedFrom", "0".equals(elapsedTo) ? "" : elapsedFrom);
				args.put("ElapsedTo", elapsedTo);

				var bsonMatch = BsonArray.parse(MongodbQueryPool.getQuery("MCSLOG_TRANSACTION_LOG", args));
				var partResult = MongodbAPI.aggregate(fab, collection, bsonMatch).toList();

				if (partResult != null) {
					dataResult.addAll(partResult);
				}

				query = bsonMatch.toString();
			}

			dataResult = dataResult.stream()
					.sorted((o1, o2) -> o1.get("TIME").toString().compareTo(o2.get("TIME").toString()))
					.collect(Collectors.toList());

			int no = 1;

			for (var item : dataResult) {
				item.put("No", no++);
			}

			returnMap.put("rows", dataResult);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getTransactionLogItems(final String fabSite, List<String> fabs, List<String> appNames,
			List<String> txNames, String txID, String elapsedFrom, String elapsedTo, String from, String to,
			String userId) {
		if (!isEnabled)
			return null;
		SecurityUtil.assertNull(fabSite, fabs);
		long start = System.currentTimeMillis();
		Map<String, Object> returnMap = new HashMap<String, Object>();
		String resultQuery = "";

		try {

			List<Map<String, Object>> dataList = null;

			if (fabs.get(0).equals(LogpressoMcslogQuery.sALL)) {
				fabs = LogpressoMcslogQuery.getFabsList(fabSite);
			}

			StringBuilder sQuery = new StringBuilder();
			sQuery.append(String.format(LogpressoMcslogQuery.sTable_From, from, to,
					LogpressoMcslogQuery.sOrder + LogpressoMcslogQuery.sEqual_1 + LogpressoMcslogQuery.sAsc
							+ LogpressoMcslogQuery.sParallel + LogpressoMcslogQuery.sSpace));

			// fabs
			if (fabs != null && fabs.size() > 0) {
				List<String> tableNames = new ArrayList<String>();
				for (int i = 0; i < fabs.size(); i++) {
					String tableName = LogpressoMcslogQuery.getTransactionLogFabTableList(fabSite, fabs.get(i));
					if (!tableNames.contains(tableName))
						tableNames.add(tableName);
				}
				sQuery.append(String.join(", ", tableNames));
			}

			// appNames
			if (appNames != null && appNames.size() > 0) {
				if (!appNames.get(0).equals(LogpressoMcslogQuery.sALL)) {
					StringBuilder sQuery2 = new StringBuilder();
					sQuery2.append(LogpressoMcslogQuery.sCRLF
							+ String.format(LogpressoMcslogQuery.sSearch_in, "Application_Name"));

					for (int i = 0; i < appNames.size(); i++) {
						sQuery2.append(LogpressoMcslogQuery.sComma + LogpressoMcslogQuery.sDoubleQuotation
								+ appNames.get(i) + LogpressoMcslogQuery.sDoubleQuotation);
					}

					sQuery2.append(" )");
					sQuery.append(sQuery2.toString());
				}
			}

			// txNames
			if (txNames != null && txNames.size() > 0) {
				if (!txNames.get(0).equals(LogpressoMcslogQuery.sALL)) {
					StringBuilder tempQuery = new StringBuilder();
					tempQuery.append(LogpressoMcslogQuery.sCRLF
							+ String.format(LogpressoMcslogQuery.sSearch_in, "Transaction_Name"));

					for (int i = 0; i < txNames.size(); i++) {
						tempQuery.append(LogpressoMcslogQuery.sComma + LogpressoMcslogQuery.sDoubleQuotation
								+ txNames.get(i) + LogpressoMcslogQuery.sDoubleQuotation);
					}

					tempQuery.append(" )");
					sQuery.append(tempQuery.toString());
				}
			}

			// txID
			if (txID != null && !txID.trim().equals("")) {
				if (txID.contains(LogpressoMcslogQuery.sCommaOrigin)) {
					StringBuilder tempQuery = new StringBuilder();
					String[] textIDArray = txID.split(LogpressoMcslogQuery.sCommaOrigin);
					for (int i = 0; i < textIDArray.length; i++) {
						if (i == 0) {
							tempQuery.append(LogpressoMcslogQuery.sLeftParenthesis
									+ LogpressoMcslogQuery.sLeftParenthesis + "Transaction_ID"
									+ LogpressoMcslogQuery.sEquals + LogpressoMcslogQuery.sDoubleQuotation
									+ LogpressoMcslogQuery.sAsterisk + textIDArray[i].trim()
									+ LogpressoMcslogQuery.sAsterisk + LogpressoMcslogQuery.sDoubleQuotation
									+ LogpressoMcslogQuery.sRightParenthesis);
						} else if (i == (textIDArray.length - 1)) {
							tempQuery.append(LogpressoMcslogQuery.sOr + LogpressoMcslogQuery.sLeftParenthesis
									+ "Transaction_ID" + LogpressoMcslogQuery.sEquals
									+ LogpressoMcslogQuery.sDoubleQuotation + LogpressoMcslogQuery.sAsterisk
									+ textIDArray[i].trim() + LogpressoMcslogQuery.sAsterisk
									+ LogpressoMcslogQuery.sDoubleQuotation + LogpressoMcslogQuery.sRightParenthesis
									+ LogpressoMcslogQuery.sRightParenthesis);
						} else {
							tempQuery.append(LogpressoMcslogQuery.sOr + LogpressoMcslogQuery.sLeftParenthesis
									+ "Transaction_ID" + LogpressoMcslogQuery.sEquals
									+ LogpressoMcslogQuery.sDoubleQuotation + LogpressoMcslogQuery.sAsterisk
									+ textIDArray[i].trim() + LogpressoMcslogQuery.sAsterisk
									+ LogpressoMcslogQuery.sDoubleQuotation + LogpressoMcslogQuery.sRightParenthesis);
						}
					}
					sQuery.append(LogpressoMcslogQuery.sCRLF + LogpressoMcslogQuery.sSearch_0 + tempQuery.toString());
				} else {
					sQuery.append(LogpressoMcslogQuery.sCRLF + LogpressoMcslogQuery.sSearch_0 + "Transaction_ID"
							+ LogpressoMcslogQuery.sEquals + LogpressoMcslogQuery.sDoubleQuotation
							+ LogpressoMcslogQuery.sAsterisk + txID.trim() + LogpressoMcslogQuery.sAsterisk
							+ LogpressoMcslogQuery.sDoubleQuotation);
				}
			}

			// Elapsed_Time
			if (elapsedFrom != null && !elapsedFrom.trim().equals("") && elapsedTo != null
					&& !elapsedTo.trim().equals("")) {
				if (!elapsedFrom.trim().equals("0") || !elapsedTo.trim().equals("0")) {
					sQuery.append(LogpressoMcslogQuery.sCRLF + LogpressoMcslogQuery.sSearch_0 + " Elapsed_Time >= "
							+ elapsedFrom.trim() + " and Elapsed_Time <= " + elapsedTo.trim() + " ");
				}
			}

			resultQuery = sQuery.toString();
			if (resultQuery != null && !(resultQuery.isEmpty())) {
				String resultQuery2 = resultQuery;
				if (!(resultQuery2.contains("sort"))) {
					resultQuery2 += LogpressoMcslogQuery.sPipeLine + LogpressoMcslogQuery.sSort + "TIME_EX";
				}

				resultQuery2 += String.format(LogpressoMcslogQuery.sEval, "No", "seq()");

				resultQuery2 += LogpressoMcslogQuery.sPipeLine + " rename Elapsed_Time as Elapsed ";
				resultQuery2 += LogpressoMcslogQuery.sPipeLine + " rename _time as TIME ";
				resultQuery2 += LogpressoMcslogQuery.sFields
						+ " No, TIME, TIME_EX, Application_Name, Running, Transaction_ID, Transaction_Name, Elapsed ";
				// 2022.09.05 X0122410 fabSite 추가
				dataList = LogpressoAPI.executeQuery(fabSite, resultQuery2);
			}

			returnMap.put("rows", dataList);
		} catch (Exception e) {
			logger.error("An error while running getTransactionLogItems", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				resultQuery);

		return returnMap;
	}

	/*
	 * =============================================================================
	 * = End MCSLOG API
	 * =============================================================================
	 * =
	 */

	/*
	 * =============================================================================
	 * = 지연쿼리 조회 & 취소
	 * =============================================================================
	 * =
	 */
	public Map<String, Object> getSystemQueries(final String id, final String is_end, final String is_eof,
			final String is_cancelled, final String from_elapsed, final String to_elapsed, final String login_name,
			final String remote_ip, String pageNum, String rowNum, final boolean hasTotalCount, final String userId) {
		if (!isEnabled)
			return null;
		long start = System.currentTimeMillis();

		SecurityUtil.assertNull(userId);

		Map<String, Object> returnMap = new HashMap<String, Object>();
		String resultQuery = "system queries | search query_string!=\"system queries*\" ";

		try {
			if (id != null && !id.equals(""))
				resultQuery += " | search id==" + id;

			if (is_end != null && !is_end.equals("") && !is_end.equals("ALL"))
				resultQuery += " | search is_end==" + is_end.toLowerCase();

			if (is_eof != null && !is_eof.equals("") && !is_eof.equals("ALL"))
				resultQuery += " | search is_eof==" + is_eof.toLowerCase();

			if (is_cancelled != null && !is_cancelled.equals("") && !is_cancelled.equals("ALL"))
				resultQuery += " | search is_cancelled==" + is_cancelled.toLowerCase();

			if (from_elapsed != null && !from_elapsed.equals("") && !from_elapsed.equals("0"))
				resultQuery += " | search elapsed >= " + from_elapsed;

			if (to_elapsed != null && !to_elapsed.equals("") && !to_elapsed.equals("0"))
				resultQuery += " | search elapsed <= " + to_elapsed;

			if (login_name != null && !login_name.equals(""))
				resultQuery += " | search login_name==\"" + login_name + "\"";

			if (remote_ip != null && !remote_ip.equals(""))
				resultQuery += " | search remote_ip==\"" + remote_ip + "\"";

			if (pageNum == null || pageNum.equals("")) {
				pageNum = "1";
			}

			if (rowNum == null || rowNum.equals("")) {
				rowNum = "100";
			}

			List<Map<String, Object>> dataList = null;
			long offset = (Long.parseLong(pageNum) - 1) * Long.parseLong(rowNum);
			int limit = Integer.parseInt(rowNum);

			String resultQuery2 = resultQuery;
			resultQuery2 += " | fields id, query_string, is_end, is_eof, is_cancelled, start_time, finish_time, last_started, elapsed, login_name, remote_ip, rows, query_string ";
			resultQuery2 += " | sort id ";
			resultQuery2 += LogpressoMcslogQuery.sPipeLine + "limit " + offset + " " + limit;
			resultQuery2 += String.format(LogpressoMcslogQuery.sEval, "No", "seq()") + LogpressoMcslogQuery.sPlus
					+ offset;
			// fabSite
			dataList = LogpressoAPI.responseResult(resultQuery2);

			String sCnt = "0";
			if (dataList != null && dataList.size() > 0 && hasTotalCount) {
				sCnt = LogpressoAPI.responseResult(resultQuery + " | stats count").get(0).get("count").toString();
			}

			returnMap.put("total", sCnt);
			returnMap.put("rows", dataList);
		} catch (Exception e) {
			logger.error("An error while running getTotalLogList", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				resultQuery);
		return returnMap;
	}

	public Map<String, Object> getMcslogAlarmReportLog(String filterPropertiesJson, boolean hasMongodb, int pageNum,
			int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.ALARM);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_ALARM_REPORT_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogMaterialCarrierLocLog(String filterPropertiesJson, boolean hasMongodb,
			int pageNum, int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.MATERIAL);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_MATERIAL_CARRIER_LOC_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogResourceMachineLog(String filterPropertiesJson, boolean hasMongodb, int pageNum,
			int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.RESOURCE);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_RESOURCE_MACHINE_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogResourcePortLog(String filterPropertiesJson, boolean hasMongodb, int pageNum,
			int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.RESOURCE);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_RESOURCE_PORT_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogResourceShelfLog(String filterPropertiesJson, boolean hasMongodb, int pageNum,
			int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.RESOURCE);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_RESOURCE_SHELF_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogResourceCraneLog(String filterPropertiesJson, boolean hasMongodb, int pageNum,
			int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.RESOURCE);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_RESOURCE_CRANE_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogResourceVehicleLog(String filterPropertiesJson, boolean hasMongodb, int pageNum,
			int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.RESOURCE);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_RESOURCE_VEHICLE_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogResourceStorageLog(String filterPropertiesJson, boolean hasMongodb, int pageNum,
			int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.RESOURCE);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_RESOURCE_STORAGE_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogTransportReturnLog(String filterPropertiesJson, boolean hasMongodb, int pageNum,
			int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.TRANSPORT);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_TRANSPORT_RETURN_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogTransportReturnJobLog(String filterPropertiesJson, boolean hasMongodb,
			int pageNum, int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.TRANSPORT);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_TRANSPORT_RETURN_JOB_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogTransportReturnCommandLog(String filterPropertiesJson, boolean hasMongodb,
			int pageNum, int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.TRANSPORT);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_TRANSPORT_RETURN_COMMAND_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogTransportReturnLogDetail(String filterPropertiesJson, boolean hasMongodb,
			String transportJobID, String transportCommandID, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.TRANSPORT);

			Map<String, Map<String, String>> filterProperties = JsonUtil.getMapMapFromJson(filterPropertiesJson);
			Map<String, Map<String, String>> newFilterProperties = new HashMap<>();

			var isForJob = StringUtils.isNotBlank(transportJobID);
			var dateTimeFrom = QueryUtil.convertToDate(filterProperties.get("McslogTimeRange").get("DateTimeFrom"))
					.toInstant();
			var dateTimeTo = QueryUtil.convertToDate(filterProperties.get("McslogTimeRange").get("DateTimeTo"))
					.toInstant();

			newFilterProperties.remove("McslogTransportReturnLog");
			newFilterProperties.put("McslogFab", filterProperties.get("McslogFab"));
			newFilterProperties.put("McslogTimeRange",
					Map.of("DateTimeFrom", QueryUtil.convertToQueryString(Date.from(dateTimeFrom.minusSeconds(1800))),
							"DateTimeTo", QueryUtil.convertToQueryString(Date.from(dateTimeTo.plusSeconds(1800)))));
			if (isForJob) {
				newFilterProperties.put("McslogTransportReturnJobLog",
						Map.of("Carrier", "", "LotID", "", "JobID", transportJobID));
			} else {
				newFilterProperties.put("McslogTransportReturnCommandLog",
						Map.of("Carrier", "", "CommandID", transportCommandID, "SourceUnit", "", "DestUnit", ""));
			}

			String newFilterPropertiesJson = JsonUtil.getJsonFromMapMap(newFilterProperties);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(newFilterPropertiesJson,
						tablesCollection,
						isForJob ? "MCSLOG_TRANSPORT_RETURN_JOB_LOG" : "MCSLOG_TRANSPORT_RETURN_COMMAND_LOG", null);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery())).toList();

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.collect(Collectors.toList());
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(newFilterPropertiesJson,
						tablesCollection, true);

				query = queries.get(0).getQuery();

				finalResult = LogpressoAPI.responseResult(query);
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", Map.of());
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogTransportReturnJobFailLog(String filterPropertiesJson, boolean hasMongodb,
			int pageNum, int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.TRANSPORT);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_TRANSPORT_RETURN_JOB_FAIL_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public Map<String, Object> getMcslogTransportReturnCommandFailLog(String filterPropertiesJson, boolean hasMongodb,
			int pageNum, int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.TRANSPORT);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_TRANSPORT_RETURN_COMMAND_FAIL_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				var queries = LogpressoCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						true);

				query = queries.get(0).getQuery();

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	public List<String> getMcslogTransportReturnFailLogReason(String site, List<String> fabs, boolean hasMongodb,
			String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		List<String> returnList = new ArrayList<String>();
		String query = "";

		try {
			Set<String> finalResult = new HashSet<String>();

			McslogTablesCollection tables = LogpressoMcslogQuery.getTablesCollection(ENUM_FABLIST_GROUP.MASTER);

			if (hasMongodb) {
				query = "{ TYPE: \"TRANSPORTRETURNFAIL_REASON\" }";

				for (String fab : fabs) {
					var partResult = MongodbAPI.find(fab, tables.get(site, fab), Document.parse(query)).toList();

					if (partResult != null) {
						partResult.forEach(row -> finalResult.add(row.get("VALUE").toString()));
					}
				}
			} else {
				query = "memlookup name=reasonList | fields REASON | sort REASON";

				var partResult = LogpressoAPI.executeQuery(site, query);

				if (partResult != null) {
					partResult.forEach(row -> finalResult.add(row.get("REASON").toString()));
				}
			}

			returnList = finalResult.stream().sorted().collect(Collectors.toList());
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnList;
	}

	public String getMcslogUnitType(String unitName, String site, List<String> fabs, boolean hasMongodb,
			String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		String returnString = "";
		String query = "";

		try {
			McslogTablesCollection tables = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.MASTER_UNITLIST);

			if (hasMongodb) {
				query = String.format("{ _id: \"%s\" }", unitName);

				for (String fab : fabs) {
					var partResult = MongodbAPI.find(fab, tables.get(site, fab), Document.parse(query)).toList();

					if (partResult != null && partResult.size() > 0) {
						returnString = partResult.get(0).get("TYPE").toString();
						break;
					}
				}
			} else {
				var tableNames = new HashSet<String>();

				for (String fab : fabs) {
					tableNames.add(tables.get(site, fab));
				}

				var memQuery = tableNames.stream().map(tableName -> String.format("memlookup name=%s", tableName))
						.collect(Collectors.toList());

				query = String.join(" | union [ ", memQuery);

				if (query.contains("union [") == true) {
					query += " ]";
				}

				query += String.format(" | search NAME==\"%s\"", unitName);

				var partResult = LogpressoAPI.executeQuery(site, query);

				if (partResult != null && partResult.size() > 0) {
					returnString = partResult.get(0).get("TYPE").toString();
				}
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnString;
	}

	public Map<String, Object> getMcslogTransportCompletedCarrierFromToLog(String filterPropertiesJson,
			boolean hasMongodb, int pageNum, int pageSize, Map<String, Object> lastKeys, String userId) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		Map<String, Object> returnMap = new HashMap<>(Map.of("data", List.of(), "lastKeys", Map.of()));
		String query = "";

		try {
			List<Map<String, Object>> finalResult = new ArrayList<>();

			if (pageSize <= 0) {
				pageSize = 1000;
			}

			McslogTablesCollection tablesCollection = LogpressoMcslogQuery
					.getTablesCollection(ENUM_FABLIST_GROUP.JOBCOMPLETED);

			if (hasMongodb) {
				var queries = MongodbCommonFilterQuery.extractCommonFilterBody(filterPropertiesJson, tablesCollection,
						"MCSLOG_TRANSPORT_COMPLETED_CARRIER_FROM_TO_LOG", lastKeys);

				query = queries.get(0).getQuery();

				for (ExtractCommonFilterResult result : queries) {
					var collection = tablesCollection.get(result.getSite(), result.getFab());
					var partResult = MongodbAPI
							.aggregate(result.getFab(), collection, BsonArray.parse(result.getQuery()))
							.toList(pageSize);

					if (partResult != null) {
						finalResult.addAll(partResult);
					}
				}

				finalResult = finalResult.stream()
						.sorted((o1, o2) -> o1.get("Key").toString().compareTo(o2.get("Key").toString()))
						.limit(pageSize).collect(Collectors.toList());

				if (lastKeys == null) {
					lastKeys = new HashMap<String, Object>();
				}

				for (Map<String, Object> row : finalResult) {
					if (row.get("_table") != null) {
						lastKeys.put(row.get("_table").toString(), row.get("Key"));
					}
				}
			} else {
				Map<String, Map<String, String>> filterProperties = JsonUtil.getMapMapFromJson(filterPropertiesJson);
				Map<String, String> filterGroup;

				String from = "";
				String to = "";
				String carrier = "";
				String machineNames = "";
				String machineTypes = "";

				if (filterProperties.containsKey("McslogTimeRange")) {
					filterGroup = filterProperties.get("McslogTimeRange");

					from = filterGroup.get("DateTimeFrom");
					to = filterGroup.get("DateTimeTo");
				}

				if (filterProperties.containsKey("McslogTransportCompletedCarrierFromToLog")) {
					filterGroup = filterProperties.get("McslogTransportCompletedCarrierFromToLog");

					carrier = filterGroup.get("Carrier");
				}

				if (filterProperties.containsKey("McslogMachine")) {
					filterGroup = filterProperties.get("McslogMachine");

					if (StringUtils.isNotBlank(filterGroup.get("MachineTypes"))) {
						machineTypes = LogpressoConditionUtil.createQueryConditionIn("MACHINETYPE",
								Arrays.asList(filterGroup.get("MachineTypes").split(",")));
					}

					if (StringUtils.isNotBlank(filterGroup.get("MachineNames"))) {
						machineNames = LogpressoConditionUtil.createQueryConditionOr("MACHINENAME",
								Arrays.asList(filterGroup.get("MachineNames").split(",")),
								ENUM_RANGE_SEARCH_OPTION.EXACT, true);
					}
				}

				if (StringUtils.isBlank(carrier)) {
					query = String.format("proc COMPLETED_CARRIER_FROM_TO('%s', '%s')", from, to);
				} else {
					query = String.format("proc COMPLETED_CARRIER_FROM_TO_CARRIER('%s', '%s', \"%s\")", from, to,
							carrier);
				}

				if (StringUtils.isNotBlank(machineTypes)) {
					query = query.concat(" | search " + machineTypes);
				}

				if (StringUtils.isNotBlank(machineNames)) {
					query = query.concat(" | search " + machineNames);
				}

				if (pageNum >= 1 && pageSize >= 1) {
					query = query.concat(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
				}

				finalResult = LogpressoAPI.responseResult(query);
				lastKeys = new HashMap<>();
			}

			returnMap.put("data", finalResult);
			returnMap.put("lastKeys", lastKeys);
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query);

		return returnMap;
	}

	@SuppressWarnings("unchecked")
	public List<Map<String, Object>> testMongoDbSample(String collection, String startDate, int unitHour, int poolSize,
			int peekCount, String asyncKey) {
		if (!isEnabled)
			return null;

		long start = System.currentTimeMillis();

		List<Map<String, Object>> returnList = new ArrayList<Map<String, Object>>();
		String query = "";
		final Gson gson = new Gson();

		try {
			var cacheFilePath = "D:\\smartATLAS_MDSample\\MongoCarrierSampleCache.dat";

			// Carrier 결과 캐싱
			Map<String, List<String>> cacheCarrier = new HashMap<>();

			try {
				var cacheCarrierJson = new String(Files.readAllBytes(Path.of(cacheFilePath)));
				cacheCarrier = (Map<String, List<String>>) gson.fromJson(cacheCarrierJson,
						new TypeToken<Map<String, List<String>>>() {
						}.getType());

				var expiredTime = Calendar.getInstance();
				expiredTime.add(Calendar.DAY_OF_MONTH, -31);

				for (String cacheKey : cacheCarrier.keySet()) {
					try {
						var from = Long.parseLong(cacheKey.split("-")[0]);
						var to = Long.parseLong(cacheKey.split("-")[1]);

						if (from < expiredTime.getTimeInMillis() && to < expiredTime.getTimeInMillis()) {
							cacheCarrier.remove(cacheKey);
						}
					} catch (Exception e) {
						cacheCarrier.remove(cacheKey);
					}
				}
			} catch (Exception e) {
			}

			// 표본
			var fromCalendarPool = new ArrayList<Calendar>(poolSize);
			var carrierPool = new ArrayList<List<String>>(poolSize);
			var from = Calendar.getInstance();

			from.setTime(QueryUtil.convertToDate(startDate));

			for (var poolIndex = 0; poolIndex < poolSize; poolIndex++) {
				from.add(Calendar.HOUR, -unitHour);
				fromCalendarPool.add((Calendar) from.clone());
			}

			// Carrier 정보 픽
			for (int calendarIndex = 0; calendarIndex < fromCalendarPool.size(); calendarIndex++) {
				var fromCalendar = fromCalendarPool.get(calendarIndex);
				var toCalendar = (Calendar) fromCalendar.clone();
				toCalendar.add(Calendar.HOUR, unitHour);

				var partitionCollection = QueryUtil.getTsViewPartitionCollection(collection, fromCalendar.getTime(),
						toCalendar.getTime());

				AsyncUtil.put(asyncKey,
						List.of(Map.of("CarrierProgress",
								Double.parseDouble(String.valueOf(calendarIndex)) / fromCalendarPool.size() * 100d,
								"PeekingProgress", 0)));

				var cacheKey = String.format("%d-%d", fromCalendar.getTimeInMillis(), toCalendar.getTimeInMillis());

				if (cacheCarrier.containsKey(cacheKey) && cacheCarrier.get(cacheKey).size() > 0) {
					carrierPool.add(cacheCarrier.get(cacheKey));
				} else {
					String fromQueryFormat = new SimpleDateFormat("yyyyMMddHHmmss").format(fromCalendar.getTime());
					String toQueryFormat = new SimpleDateFormat("yyyyMMddHHmmss").format(toCalendar.getTime());

					query = String.format("" + "[" + "{ $match: {\r\n"
							+ "	\"TIME_EX\": {\"$gte\": {\"$date\": \"%s\"}, \"$lte\": {\"$date\": \"%s\"}},\r\n"
							+ "	\"level\": {\"$in\": [\"WELL\", \"WARN\", \"ERROR\", \"FATAL\"]},\r\n"
							+ "	\"CARRIER\": { $ne: null }}\r\n" + "},\r\n"
							+ "{ $group: { _id: \"$CARRIER\", \"count\": { $sum: 1 } } },\r\n" + "{ $limit: 5 }" + "]",
							QueryUtil.convertToUtcTimezone(fromQueryFormat),
							QueryUtil.convertToUtcTimezone(toQueryFormat));

					var carriers = MongodbAPI.aggregate("ICPKT", partitionCollection, BsonArray.parse(query)).toList();
					var limit5 = new ArrayList<String>(5);

					for (Map<String, Object> row : carriers) {
						limit5.add(row.get("_id").toString());
					}

					carrierPool.add(limit5);

					try {
						cacheCarrier.put(cacheKey, (List<String>) limit5);
						Files.writeString(Path.of(cacheFilePath), gson.toJson(cacheCarrier), StandardOpenOption.CREATE,
								StandardOpenOption.TRUNCATE_EXISTING);
					} catch (Exception e) {
						logger.error("", e);
					}
				}
			}

			// 무작위 픽
			var randInstance = new SecureRandom();

			for (int index = 0; index < peekCount; index++) {
				AsyncUtil.put(asyncKey, List.of(Map.of("CarrierProgress", 100, "PeekingProgress",
						Double.parseDouble(String.valueOf(index)) / peekCount * 100d)));

				var randIndex = Math.abs(randInstance.nextInt()) % poolSize;
				var fromCalendar = fromCalendarPool.get(randIndex);
				var toCalendar = (Calendar) fromCalendar.clone();
				toCalendar.add(Calendar.HOUR, unitHour);

				var partitionCollection = QueryUtil.getTsViewPartitionCollection(collection, fromCalendar.getTime(),
						toCalendar.getTime());
				String fromQueryFormat = new SimpleDateFormat("yyyyMMddHHmmss").format(fromCalendar.getTime());
				String toQueryFormat = new SimpleDateFormat("yyyyMMddHHmmss").format(toCalendar.getTime());
				String carrier = "";
				long startTime = 0, endTime = 0;
				List<Map<String, Object>> dataResult = new ArrayList<>();

				if (carrierPool.get(randIndex).size() > 0) {
					carrier = carrierPool.get(randIndex)
							.get(Math.abs(randInstance.nextInt()) % carrierPool.get(randIndex).size());
					startTime = System.currentTimeMillis();
					query = String.format(
							"" + "[{ $match: {\r\n"
									+ "	\"TIME_EX\": {\"$gte\": ISODate(\"%s\"), \"$lte\": ISODate(\"%s\")},\r\n"
									+ "	\"level\": {\"$in\": [\"WELL\", \"WARN\", \"ERROR\", \"FATAL\"]},\r\n"
									+ "	\"$text\": {\"$search\": \"%s\", \"$caseSensitive\": true},\r\n"
									+ "	\"$or\": [{\"CARRIER\": \"%s\"}, {\"line\": /%s/}]\r\n" + "}}" + "]",
							QueryUtil.convertToUtcTimezone(fromQueryFormat),
							QueryUtil.convertToUtcTimezone(toQueryFormat), carrier, carrier, carrier);
					dataResult = MongodbAPI.aggregate("ICPKT", partitionCollection, BsonArray.parse(query)).toList();
					endTime = System.currentTimeMillis() - startTime;
				}

				returnList.add(Map.of("From", "'" + QueryUtil.convertToCommonDateFormat(fromQueryFormat), "To",
						"'" + QueryUtil.convertToCommonDateFormat(toQueryFormat), "Elapsed", endTime, "Count",
						dataResult.size(), "Carrier", carrier, "Collection", partitionCollection));
			}
		} catch (Exception e) {
			logger.error("", e);
		} finally {
			AsyncUtil.put(asyncKey, List.of(Map.of("CarrierProgress", 100, "PeekingProgress", 100)));
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), "TEST", (System.currentTimeMillis() - start),
				query);

		return returnList;
	}

	public List<Map<String, Object>> queryLogHistory(String startDate, String endDate, String limit, String logLevel,
			String thread, String filter, final List<String> serverList, final List<String> processList,
			final int pageNum, final int pageSize, String userId) {
		if (!isEnabled)
			return null;
		long start = System.currentTimeMillis();

		List<Map<String, Object>> listMap = new ArrayList<Map<String, Object>>();
		StringBuilder query4Logprs = new StringBuilder();
		try {
			if (!startDate.isEmpty() && !endDate.isEmpty()) {
				query4Logprs
						.append("table from=\"" + startDate + "\" to=\"" + endDate + "\" order=asc table_msglog_final");
			} else if (!startDate.isEmpty() && endDate.isEmpty()) {
				query4Logprs.append("table from=\"" + startDate + "\" order=asc table_msglog_final");
			} else if (startDate.isEmpty() && !endDate.isEmpty()) {
				query4Logprs.append("table to=\"" + endDate + "\" order=asc table_msglog_final");
			} else {
				query4Logprs.append("table order=asc table_msglog_final");
			}

			if (serverList != null && serverList.size() > 0) {
				query4Logprs.append(" | search in(serverName");
				for (int i = 0; i < serverList.size(); i++) {
					query4Logprs.append(", \"" + serverList.get(i) + "\"");
				}
				query4Logprs.append(")");
			}

			// 20210716 X0122410 조회 대상 서버/프로세스 선택기능 : 프로세스선택기능
			// 계산프로세스(CALCURATOR01,CALCURATOR02,CALCURATOR03,CALCURATOR04),
			// 수집기프로세스(datamaker) : 5개 프로세스 선택가능
			if (processList != null && processList.size() > 0) {
				query4Logprs.append(" | search in(sourceFile");
				for (int i = 0; i < processList.size(); i++) {
					query4Logprs.append(", \"" + processList.get(i) + ".log\"");
				}
				query4Logprs.append(")");
			}

			if (!logLevel.equalsIgnoreCase("ALL")) {
				query4Logprs.append(" | search level==\"" + logLevel.toUpperCase(Locale.ENGLISH) + "\"");
			}

			if (!thread.isEmpty()) {
				query4Logprs.append(" | search thread==\"*" + thread + "\"");
			}

			if (!filter.isEmpty()) {
				query4Logprs.append(" | search line==\"*" + filter + "*\"");
			}

			int limitInt = 0;
			if (StringUtils.isEmpty(limit) == false && StringUtils.isNumeric(limit) == true) {
				limitInt = Integer.parseInt(limit);
			} else {
				limitInt = 1000;
			}

			query4Logprs.append(" | limit " + limitInt);
			query4Logprs.append(" | sort _time ");
			query4Logprs.append(" | fields serverName, sourceFile, createDate, level, thread, category, line");

			/*
			 * IC에서는 ATLAS DATAMAKER 로그 수집(table_mcslog_* 테이블)을 IC가 아닌 M14 로그프레소 에서 진행 IC의
			 * DATANAKER 로그를 조회하는 경우 IC -> M14로 변경해야 함
			 */
			if (StringUtils.isNotEmpty(limit)) {
				if (limitInt > 0) {
					if (pageNum >= 1 && pageSize >= 1) {
						listMap.add(new HashMap<>());
						listMap.get(0).put("total",
								LogpressoConditionUtil.getQueryTotalCount(null, query4Logprs.toString()));

						query4Logprs.append(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
						listMap.get(0).put("data", LogpressoAPI.executeQuery(query4Logprs.toString()));
					} else {
						listMap = LogpressoAPI.executeQuery(query4Logprs.toString());
					}
				} else {
					if (pageNum >= 1 && pageSize >= 1) {
						listMap.add(new HashMap<>());
						listMap.get(0).put("total", 0);
						listMap.get(0).put("data", new ArrayList<>());
					}
				}
			} else {
				if (pageNum >= 1 && pageSize >= 1) {
					listMap.add(new HashMap<>());
					listMap.get(0).put("total",
							LogpressoConditionUtil.getQueryTotalCount(null, query4Logprs.toString()));

					query4Logprs.append(" | limit " + (pageNum - 1) * pageSize + " " + pageSize);
					listMap.get(0).put("data", LogpressoAPI.responseResult(query4Logprs.toString()));
				} else {
					listMap = LogpressoAPI.responseResult(query4Logprs.toString());
				}
			}
		} catch (Exception e) {
			logger.error("An error while searching the log history.", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start),
				query4Logprs.toString());
		return listMap;
	}

	public String SshMongoDbJsConsoleOutput() {
		if (!isEnabled)
			return null;

		SecurityUtil.assertAccessLevel(AccessLevel.SystemAdministrator);

		MemoryTailerUtil.startListener(SecurityUtil.getCurrentUserId());

		return MemoryTailerUtil.getContent(SecurityUtil.getCurrentUserId());
	}

	public boolean SshMongoDbJsMaintenanceStatus(String ip, String serverID, String serverPassword) {
		if (!isEnabled)
			return false;

		SecurityUtil.assertAccessLevel(AccessLevel.SystemAdministrator);

		var jsCommand = "ps -ef | grep mongosh";

		try {
			var result = RemoteCommandUtil.execute(ip, serverID, serverPassword, jsCommand);

			return StringUtils.contains(result, "mongodb://");
		} catch (Exception e) {
			logger.error("", e);
		}

		return false;
	}

	public boolean SshMongoDbJsMaintenanceCommand(String ip, String serverID, String serverPassword,
			String mongoPassword, boolean isTurnON) {
		if (!isEnabled)
			return false;

		SecurityUtil.assertAccessLevel(AccessLevel.SystemAdministrator);

		var jsCommand = isTurnON ? "sh ~/@start_js.sh " + mongoPassword : "sh ~/@stop_js.sh";

		try {
			var result = RemoteCommandUtil.execute(ip, serverID, serverPassword, jsCommand);

			MemoryTailerUtil.appendContent(SecurityUtil.getCurrentUserId(), result);
		} catch (Exception e) {
			logger.error("", e);

			return false;
		}

		return true;
	}

	public String SshMongoDbJsCommand(String ip, String serverID, String serverPassword, String command,
			String jsFileName, String jsContents) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertAccessLevel(AccessLevel.SystemAdministrator);

		var tempFileName = "temp_" + SecurityUtil.getCurrentUserId() + ".txt";

		jsFileName = SecurityUtil.safeFileName(jsFileName);

		try {
			switch (command) {
			case "List": {
				var fullCommand = String.format("find /app/mongo/JS -name \"*.js\"");
				var result = RemoteCommandUtil.execute(ip, serverID, serverPassword, fullCommand);

				return result;
			}
			case "Update": {
				var fullCommand = String.format("cat > /app/mongo/JS/%s", jsFileName);

				Files.writeString(Path.of(tempFileName), jsContents, StandardOpenOption.CREATE,
						StandardOpenOption.TRUNCATE_EXISTING);
				RemoteCommandUtil.execute(ip, serverID, serverPassword, fullCommand, tempFileName);
				Files.delete(Path.of(tempFileName));

				MemoryTailerUtil.appendContent(SecurityUtil.getCurrentUserId(), "Write JS : " + jsFileName);
				break;
			}
			case "Select": {
				var fullCommand = String.format("cat /app/mongo/JS/%s", jsFileName);
				var result = RemoteCommandUtil.execute(ip, serverID, serverPassword, fullCommand);

				MemoryTailerUtil.appendContent(SecurityUtil.getCurrentUserId(), "Read JS : " + jsFileName);
				return result;
			}
			case "Delete": {
				var fullCommand = String.format("rm /app/mongo/JS/%s", jsFileName);

				RemoteCommandUtil.execute(ip, serverID, serverPassword, fullCommand);
				MemoryTailerUtil.appendContent(SecurityUtil.getCurrentUserId(), "Delete JS : " + jsFileName);
				break;
			}
			default:
				break;
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		return "";
	}

	public List<String> getAllMybatisQueryFiles(String userId) {
		long start = System.currentTimeMillis();
		List<String> result = MybatisQueryHandler.getAllQueryFileNames();
		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start));
		return result;
	}

	public List<String> getQueryList(String fileName, String userId) {
		long start = System.currentTimeMillis();
		List<String> result = MybatisQueryHandler.getQueryList(fileName);
		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start));
		return result;
	}

	public String getQueryContent(String fileName, String queryId, String userId) {
		long start = System.currentTimeMillis();
		String result = MybatisQueryHandler.getQueryContent(fileName, queryId);
		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start));
		return result;
	}

	public boolean updateQueryContent(String fileName, String queryId, String queryContent, String userId) {
		long start = System.currentTimeMillis();
		boolean result = MybatisQueryHandler.updateQueryContent(fileName, queryId, queryContent);
		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start));
		return result;
	}

	public String loadRepositoryXml(String fileName, String userId) {
		if (!isEnabled)
			return null;

		SecurityUtil.assertNull(fileName);

		long start = System.currentTimeMillis();

		String xml = "";

		try {
			fileName = SecurityUtil.safeFileName(fileName);

			var path = String.format("%s/%s", System.getProperty("SMARTFX_REPOSITORY"), fileName);

			if (path.toLowerCase().endsWith(".xml")) {
				xml = Files.readString(Paths.get(path));
			} else {
				logger.error("Invalid Extension : " + fileName);
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start));
		return xml;
	}

	public boolean saveRepositoryXml(String fileName, String content, String userId) {
		if (!isEnabled)
			return false;

		SecurityUtil.assertNull(fileName, content);

		long start = System.currentTimeMillis();

		boolean isSucceed = false;

		try {
			fileName = SecurityUtil.safeFileName(fileName);

			var path = String.format("%s/%s", System.getProperty("SMARTFX_REPOSITORY"), fileName);
			var backupPath = path + "." + System.currentTimeMillis();

			if (path.toLowerCase().endsWith(".xml")) {
				if (XmlUtil.verifyXml(content) == true) {
					Files.copy(Paths.get(path), Paths.get(backupPath), StandardCopyOption.REPLACE_EXISTING);
					Files.writeString(Paths.get(path), content);
					isSucceed = true;
				} else {
					logger.error("Invalid XML Syntax " + content);
				}
			} else {
				logger.error("Invalid Extension : " + fileName);
			}
		} catch (Exception e) {
			logger.error("", e);
		}

		logger.info(MethodLog, ReflectionUtil.getCurrentMethodName(), userId, (System.currentTimeMillis() - start));
		return isSucceed;
	}
}
