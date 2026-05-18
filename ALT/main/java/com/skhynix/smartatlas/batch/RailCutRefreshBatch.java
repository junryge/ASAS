package com.skhynix.smartatlas.batch;

import com.skhynix.smartatlas.data.DataSet;
import com.skhynix.smartatlas.data.McpProperties;
import com.skhynix.smartatlas.data.RailCutRecordItem;
import com.skhynix.smartatlas.data.raw.Mcp75Config;
import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.environment.type.FunctionItem;
import com.skhynix.smartatlas.map.edge.RailEdge;
import com.skhynix.smartatlas.navi.Navigator;
import com.skhynix.smartatlas.process.OhtMsgWorkerRunnable.OHT_TIB_STATE;
import com.skhynix.smartatlas.service.TibrvService.*;
import com.skhynix.smartatlas.util.*;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.data.FabProperties;

public class RailCutRefreshBatch implements Job{
	private final Logger logger = LoggerFactory.getLogger(getClass());
	private boolean initialized = false;
	final int DELAYED_TIME = 1000 * 60;

	@Override
	public void execute(JobExecutionContext arg0) throws JobExecutionException {
		if (Util.isCurrentIC()) {
			this._init();

			/*
			 * sequence
			 * 1. `inactive_SCH_1.dat` 파일의 '마지막으로 수정된 날짜'를 기준으로 다운로드 시도
			 * 2. 파일을 다운로드 받은 경우, 파일의 내용을 파싱해 키 값으로 산출 (예: M14A:A:1000-1001)
			 * 3. 산출한 키 값을 통해 현재 가지고 있는 RAIL CUT 데이터(RailCutRecordItem)와 비교해 세 가지 CASE 로 구분
			 * 4. CASE 에 따라 일렬의 로직(tibco message 등)을 수행한 뒤 RAIL CUT 의 데이터에 저장
			 */
			ConcurrentMap<String, RailCutRecordItem> totalData 	= new ConcurrentHashMap<>();

			for (Map.Entry<String, FunctionItem> functionItemEntry : Env.getSwitchMap().entrySet()) {
				FunctionItem functionItem = functionItemEntry.getValue();

				if (functionItem != null && functionItem.isUseRailCut()) {
					String fabId 	= functionItem.getFabId();
					String mcpName 	= functionItem.getMcpName();
					long timer 		= System.currentTimeMillis();

					ConcurrentMap<String, RailCutRecordItem> data = this._run(fabId, mcpName);

					totalData.putAll(data);

					long checkTimer = System.currentTimeMillis() - timer;

					if (checkTimer >= DELAYED_TIME) {
						logger.error("... !!!DELAYED!!! `RailCutRefreshBatch` has finished [fab: {} | mcp: {}] [elapsed time: {}m ({}ms)]", fabId, mcpName, checkTimer / (60 * 1000), checkTimer);
					} else {
						logger.info("... `RailCutRefreshBatch` has finished [fab: {} | mcp: {}] [elapsed time: {}ms]", fabId, mcpName, checkTimer);
					}
				}
			}

			DataService.getDataSet().setRailCutRecordMap(totalData);

			if (!this.initialized) {
				DataService.getInstance().setRailCutInitialized(true); // RAIL CUT 초기화 완료
			}
		}
	}
	//======================================================================================================================
	// INIT(preprocessing)
	private void _init() {
		try {
			this.initialized = DataService.getInstance().getRailCutInitialized();
		} catch (Exception e) {
			this.initialized = false;

			logger.error("", e);
		}
	}
	//======================================================================================================================
	private ConcurrentMap<String, RailCutRecordItem> _run(String fabId, String mcpName) {
		ConcurrentMap<String, RailCutRecordItem> updated;

		if (this.initialized) {
			// RAIL CUT 파일 다운로드
			List<Integer> downloadFileTypes = this._downloader(fabId, mcpName);
			ConcurrentMap<String, RailCutRecordItem> originalRailCutMap = new ConcurrentHashMap<>();

			ConcurrentMap<String, RailCutRecordItem> entryOriginalRailCutMap
					= DataService.getDataSet().getRailCutRecordMap();

			if (entryOriginalRailCutMap != null && !entryOriginalRailCutMap.isEmpty()) {
				for (Map.Entry<String, RailCutRecordItem> recordItemEntry : entryOriginalRailCutMap.entrySet()) {
					String key = recordItemEntry.getKey();

					if (key.contains(fabId + ":" + mcpName)) {
						originalRailCutMap.put(key, recordItemEntry.getValue());
					}
				}
			}

			// RAIL CUT 초기화 완료 이후
			if (!downloadFileTypes.isEmpty()) {
				// 다운로드 받은 RAIL CUT 파일을 파싱한 뒤 키 값 산출
				Set<String> railCutKeySet = this._buildNewRailCutKeySet(fabId, mcpName);

				updated = this._updateRailCutHandler(railCutKeySet, originalRailCutMap, fabId, mcpName);

				this._insertLogpresso(updated);

				this._addTibSenderWaiting(updated, fabId);

				ConcurrentMap<String, RailCutRecordItem> result = new ConcurrentHashMap<>();

				for (Map.Entry<String, RailCutRecordItem> recordItemEntry : updated.entrySet()) {
					String key 				= recordItemEntry.getKey();
					RailCutRecordItem value	= recordItemEntry.getValue();

					if (value.getState().equals(OHT_TIB_STATE.NORMAL)) {
						String railEdgeId = value.getRailEdgeId();
						RailEdge railEdge = DataService.getDataSet().getRailEdgeMap(railEdgeId);

						railEdge.setAvailable(true);

						DataService.getDataSet().getRailCutRecordMap().remove(key);
					} else {
						result.put(key, value);
					}
				}

				return result;
			} else {
				return originalRailCutMap;
			}
		} else {
			// RAIL CUT 초기화 완료 이전
			Set<String> railCutKeySet = this._buildNewRailCutKeySet(fabId, mcpName);

			updated = this._updateRailCutHandler(railCutKeySet, new ConcurrentHashMap<>(), fabId, mcpName);

			this._insertLogpresso(updated);

			this._addTibSenderWaiting(updated, fabId);
		}

		return updated;
	}
	//======================================================================================================================
	private List<Integer> _downloader(String fabId, String mcpName){
		logger.info("... check and download `RAIL CUT` file [fab: {} | mcp: {}]", fabId, mcpName);

		// inactive_SCH_1.dat 파일 만 다운로드 --- 마지막으로 수정된 날짜 확인
		return Util.getAllOhtLayoutFileOverFtp(
				fabId,
				mcpName,
				true,
				false,
				false,
				false,
				true
		);
	}

	private void _addTibSenderWaiting(Map<String, RailCutRecordItem> recordMap, String fabId) {
		List<Map<String, String>> dataList = new ArrayList<>();

		if (recordMap == null || recordMap.isEmpty()) return;

		for (RailCutRecordItem recordItem : recordMap.values()) {
			if (this.initialized && !recordItem.getModify()) continue;

			Map<String, String> dataMap = LayoutUtil.buildLayoutMessageDataMap(recordItem);

			if (!dataMap.isEmpty()) {
				dataList.add(dataMap);

				recordItem.setModify(false);
			}
		}

		if (!dataList.isEmpty()) {
			for (String tibrvKey : DataService.getInstance().getTibrvSenderLikeMap(fabId + ":send:").keySet()) {
				DataService.getInstance().addTibrvMessageQueue(
						tibrvKey,
						SEND_SUB_SUBJECT.RAIL_CUT,
						dataList
				);
			}
		}
	}

	private void _insertLogpresso(Map<String, RailCutRecordItem> recordMap) {
		logger.info("... formalization of `RAIL CUT` data has started, before an logpresso data was inserted [record size: {}]", recordMap.size());

		if (recordMap.isEmpty()) {
			logger.info("... recorded data with `RAIL CUT` is empty, then it's skipped");

			return;
		}

		List<Tuple> logpressoData = new ArrayList<>();

		for (RailCutRecordItem railCutItem : recordMap.values()) {
			if (railCutItem == null) continue;

			Tuple tuple = this._getTuple(railCutItem);

			if (tuple != null) {
				logpressoData.add(tuple);
			}
		}

		if (recordMap.size() != logpressoData.size()) {
			// logpresso 에 적재하기 위해 변환한 값 중 exception 발생으로 어긋난 데이터가 존재하는 경우에 표시
			logger.error("... recorded or formatted data is included invalid value [record={} | format={}]", recordMap.size(), logpressoData.size());
		}

		Util.insertInLogpressoDatabase(logpressoData, "ATLAS_OHT_RAIL_CUT", this.getClass().getSimpleName());
	}

	private Tuple _getTuple(RailCutRecordItem railCutItem) {
		Tuple tuple = new Tuple();

		tuple.put("INIT", !this.initialized);

		try {
			tuple.put("FAB_ID", railCutItem.getFabId());
			tuple.put("MCP_NM", railCutItem.getMcpName());
			tuple.put("FROM_ADDR", railCutItem.getRailCutFromAddress());
			tuple.put("TO_ADDR", railCutItem.getRailCutToAddress());
			tuple.put("EVENT_DT", railCutItem.getEventDateTimeString());
			tuple.put("AFFECT_ADDR_LST", railCutItem.getAffectedAddressString());
			tuple.put("AFFECT_PORT_LST", railCutItem.getAffectedPortString());
			tuple.put("STATE", railCutItem.getState());
			tuple.put("ENV", Env.getEnv());
		} catch (Exception e) {
			logger.error("... an exception occurred duration tuple formatting:", e);

			return null;
		}

		return tuple;
	}

	/**
	 * 새롭게 다운로드 받은 inactive_SCH_1.dat 파일을 파싱 한 뒤 Set 형태로 반환{@link Mcp75Config}
	 * @return Set[{fabId}:{mcpName}:{rawRailCut}]
	 */
	private Set<String> _buildNewRailCutKeySet(String fabId, String mcpName) {
		Set<String> result 			= new HashSet<>();
		String prefix 				= fabId + ":" + mcpName;
		FabProperties fabProperties	= DataService.getInstance().getFabPropertiesMap().get(fabId);

		if (fabProperties == null) {
			logger.error("... it's invalid key with fab properties [key: {}]", fabId);
		} else if (fabProperties.getMcpPropertiesMap() == null) {
			logger.error("... mcp properties mapping data is null, check an building factory foundation process [fab: {}]", fabId);
		} else {
			String mapDirectory 		= fabProperties.getMapDir();
			McpProperties mcpProperties	= fabProperties.getMcpPropertiesMap().get(mcpName);

			if (mcpProperties == null) {
				logger.error("... mcp properties is null");
			} else {
				Mcp75Config mcp75Config	= mcpProperties.getMcp75Config();

				mcp75Config.updateRawRailCut(mapDirectory, mcpName); // RAIL CUT data parsing and refresh

				for (String rawRailCut : mcp75Config.getRawRailCutSet()) {
					result.add(prefix + ":" + rawRailCut);
				}
			}
		}

		return result;
	}

	/*
		RAIL CUT은 3가지로 구분 후 업데이트(기존 railCut 집합을 α, 새롭게 다운로드 받은 railCut 집합을 β 로 서술)
		- case A: 기존에 존재하는 데이터가 다운로드 받은 데이터에는 존재하지 않는 경우, α-β 	---> 기존 railCut 치유 및 해소
		- case B: 기존 데이터에는 존재하지 않으나 다운로드 받은 데이터에는 존재하는 경우, β-α 	---> 새로운 railCut 발생
		- case C: 기존 데이터와 다운로드 받은 데이터 모두 존재하는 경우, α∩β 				---> 형상 유지

		!!! isModified 를 통해 메세지 송신 여부 결정. {A, B} === isModified=true | {C} === isModified=false
	 */
	/**
	 * <h4>RAIL CUT 데이터를 3가지로 분류</h4>
	 * <hr/>
	 * <table>
	 *     <tr><th>CASE A</th><td>RAIL CUT 해소 및 치유</td></tr>
	 *     <tr><th>CASE B</th><td>새로운 RAIL CUT 발생</td></tr>
	 *     <tr><th>CASE C</th><td>RAIL CUT 형상 유지</td></tr>
	 * </table>
	 * @param newRailCutKeySet 새롭게 다운로드 받은 railCut key 모음
	 */
	private ConcurrentMap<String, RailCutRecordItem> _updateRailCutHandler(
			Set<String> newRailCutKeySet,
			Map<String, RailCutRecordItem> originalRailCutMap,
			String fabId,
			String mcpName
	) {
		String searchKey = fabId + ":" + mcpName;
		ConcurrentMap<String, RailCutRecordItem> result = new ConcurrentHashMap<>();

		// log
		List<String> aRailCutList = new ArrayList<>();
		List<String> bRailCutList = new ArrayList<>();
		List<String> cRailCutList = new ArrayList<>();
		int aCnt 			= 0;
		int bCnt 			= 0;
		int cCnt 			= 0;
		int exceptionCnt 	= 0;

		if (!DataService.getInstance().isDataServiceRunning()) {
			// 데이터가 존재하지 않는 경우
			return new ConcurrentHashMap<>();
		}
//----------------------------------------------------------------------------------------------------------------------
		if (!originalRailCutMap.isEmpty()) {
			Set<String> recoverySet	= new HashSet<>();    	// 해소된 RAIL CUT 키 목록 (A)
			Set<String> retainSet 	= new HashSet<>();      // 형상 유지 되는 RAIL CUT 키 목록 (C)

			if (newRailCutKeySet.isEmpty()) {
				recoverySet.addAll(originalRailCutMap.keySet());
			} else {
				for (String key : originalRailCutMap.keySet()) {
					if (newRailCutKeySet.contains(key)) {
						retainSet.add(key);
					} else {
						recoverySet.add(key);
					}
				}
			}
//----------------------------------------------------------------------------------------------------------------------
			// CASE A ---> tibco message 송신 후 해당 데이터 삭제
			for (String key : recoverySet) {
				RailCutRecordItem railCutItem = originalRailCutMap.get(key);

				if (railCutItem != null) {
					RailEdge railEdge = railCutItem.getRailEdge();

					if (railEdge == null) {
						exceptionCnt++;
					} else {
						railCutItem.setState(OHT_TIB_STATE.NORMAL);
						railCutItem.setModify(true);

						result.put(key, railCutItem);

						// 결과 표시용
						aRailCutList.add(railEdge.getAddress());

						aCnt++;
					}
				}
			}
//----------------------------------------------------------------------------------------------------------------------
			// CASE C
			for (String key : retainSet) {
				RailCutRecordItem railCutItem = originalRailCutMap.get(key);

				if (railCutItem != null) {
					RailEdge railEdge = railCutItem.getRailEdge();

					if (railEdge == null) {
						exceptionCnt++;
					} else {
						railCutItem.setModify(false);

						result.put(key, railCutItem);

						// 결과 표시용
						cRailCutList.add(railEdge.getAddress());

						cCnt++;
					}
				}
			}
		}
//----------------------------------------------------------------------------------------------------------------------
		// CASE B
		if (!newRailCutKeySet.isEmpty()) {
			Set<String> newRailCutSet = new HashSet<>();

			if (originalRailCutMap.isEmpty()) {
				newRailCutSet.addAll(newRailCutKeySet);
			} else {
				for (String key : newRailCutKeySet) {
					if (!originalRailCutMap.containsKey(key)) {
						newRailCutSet.add(key);
					}
				}
			}

			for (String key : newRailCutSet) {
				RailCutRecordItem recordItem = this._createRailCutObject(key);

				if (recordItem != null) {
					result.put(key, recordItem);

					// 결과 표시용
					bRailCutList.add(recordItem.getRailCutFromAddress() + ":" + recordItem.getRailCutToAddress());

					bCnt++;
				}
			}
		}

		List<String> logs = new ArrayList<>();

		logs.add("<RAIL CUT STATUS [" + searchKey + "]>");

		if (aCnt > 0 || bCnt > 0 || cCnt > 0) {
			String resultA 		= String.join(", ", aRailCutList);
			String resultB 		= String.join(", ", bRailCutList);
			String resultC 		= String.join(", ", cRailCutList);
			String commentA 	= String.format("%-22s(%02d): %s", "(A) RECOVERED RAILCUT", aCnt, resultA);
			String commentB 	= String.format("%-22s(%02d): %s", "(B) NEW RAILCUT", bCnt, resultB);
			String commentC 	= String.format("%-22s(%02d): %s", "(C) RETAIN RAILCUT", cCnt, resultC);
			String commentEtc 	= "(ETC) !SKIPPED : " + exceptionCnt;

			logs.add(commentA);
			logs.add(commentB);
			logs.add(commentC);

			String boundary = "-".repeat(Util.maxLength(logs));

			logs.add(boundary);
			logs.add(commentEtc);
		} else {
			logs.add("... NOT CHANGED, THE NUMBER OF ALL CASE IS ZERO");
		}

		Util.printHelper(logs);

		return result;
	}

	/**
	 * @param key {fabId}:{mcpName}:{fromAddress}-{toAddress}
	 */
	private RailCutRecordItem _createRailCutObject(String key) {
		if (key.isEmpty()) return null;

		String[] splitKey = key.split(":");

		if (splitKey.length < 3) return null;

		String fabId 		= splitKey[0];
		String mcpName 		= splitKey[1];
		String[] address 	= splitKey[2].split("-");
		String facId;

		if (address.length < 2) return null;

		if (fabId.contains("M14")) {
			facId = "M14";
		} else if (fabId.contains("M16")) {
			facId = "M16";
		} else {
			facId = "NA";
		}

		int fromAddress 	= Integer.parseInt(address[0]);
		int toAddress 		= Integer.parseInt(address[1]);
		String railEdgeId 	= DataSet.address2RailEdgeId(fabId, mcpName, fromAddress, toAddress);

		// 데이터 저장
		RailCutRecordItem recordItem = new RailCutRecordItem(
				key,
				fabId,
				facId,
				mcpName,
				fromAddress + ":" + toAddress,
				railEdgeId,
				fromAddress,
				toAddress,
				null,
				null,
				OHT_TIB_STATE.ABNORMAL,
				true
		);

		// RAIL CUT 영향도 설정
		RailEdge railEdge = recordItem.getRailEdge();

		if (railEdge != null) {
			Navigator navigator 	= new Navigator(railEdge);
			Set<String> addressSet 	= navigator.getAffectedRailSet();
			List<String> portList 	= navigator.getAffectedPortSortedList();

			recordItem.setAffectedAddress(addressSet);
			recordItem.setAffectedPort(portList);
		}

		return recordItem;
	}
}