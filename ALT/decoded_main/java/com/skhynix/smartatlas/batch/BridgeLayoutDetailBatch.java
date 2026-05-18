package com.skhynix.smartatlas.batch;

import java.awt.*;
import java.io.File;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Map.Entry;
import java.util.function.Function;
import java.util.stream.Collectors;

import com.skhynix.smartatlas.util.Util;
import org.quartz.Job;
import org.quartz.JobExecutionContext;
import org.quartz.JobExecutionException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.logpresso.client.Tuple;
import com.skhynix.smartatlas.db.logpresso.LogpressoAPI;
import com.skhynix.smartatlas.util.FilePathUtil;
import com.skhynix.smartatlas.util.XmlUtil;
import com.skhynix.smartfx.dataaccessfx.QueryExecutorFactory;

public class BridgeLayoutDetailBatch implements Job{
	private final Logger logger 	= LoggerFactory.getLogger(getClass());
	private final int DELAYED_TIME	= 1000 * 60;

	@Override
	public void execute(JobExecutionContext context) throws JobExecutionException {
		if (Util.isCurrentIC()){
			logger.info("... `{}` has started", this.getClass().getSimpleName());

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
		final List<Tuple> countList = new ArrayList<>();
		final List<Tuple> countList2 = new ArrayList<>();
		List<Map<String, Object>> finalList;

		try {
			List<Map<String, Object>> dataList = getDetailDataByOracle();

			List<Map<String, Object>> logpressoList = getDetailDataLogpresso();

			// 과거 state 값
			List<Map<String, Object>> preStateList = getPreStateDataLogpresso();

			dataList.addAll(logpressoList);

			Map<Object, List<Map<String, Object>>> groupData = dataList.stream().collect(Collectors
					.groupingBy(row -> row.get("EVENT_DT") + "|" + row.get("FROM_FAB_ID") + "|" + row.get("TO_FAB_ID") + "|"
							+ row.get("EQP_TYP") + "|" + row.get("DET_AREA_TYP")
					));

			Map<Object, List<Map<String, Object>>> preStateGroupData = preStateList.stream().collect(Collectors
					.groupingBy(row -> row.get("EVENT_DT") + "|" + row.get("FROM_FAB_ID") + "|" + row.get("TO_FAB_ID") + "|"
							+ row.get("EQP_TYP") + "|" + row.get("DET_AREA_TYP")));

			for (Entry<Object, List<Map<String, Object>>> entry : groupData.entrySet()) {
				String key = entry.getKey().toString();
				List<Map<String, Object>> groupRows = entry.getValue();

				List<Map<String, Object>> preGroupRows = preStateGroupData.getOrDefault(key, new ArrayList<>());
				Map<String, Map<String, Object>> preRowMap = preGroupRows.stream()
						.collect(Collectors.toMap(row -> row.get("EQP_ID").toString(), row -> row));

				for (Map<String, Object> row : groupRows) {
					try {
						String eqpId = row.get("EQP_ID").toString();
						String currentResult = row.get("RSLT_VAL").toString();
						String detIdcNm = row.get("DET_IDC_NM").toString();

						//장비 상태알람 관련
						if (detIdcNm.equals("STATE")) {
							Map<String, Object> preRow = preRowMap.get(eqpId);
							String previousResult = preRow != null ? preRow.get("RSLT_VAL").toString() : "0";

							if (previousResult.equals("0") && currentResult.equals("1")) {
								String alarmText = XmlUtil.getMessage("DETAIL_ALARM_DOWN", eqpId);
								row.put("ALARM_MSG", alarmText);
								System.out.println("0->1 변경:  "+alarmText);
							} else if (previousResult.equals("1") && currentResult.equals("0")) {
								String alarmText = XmlUtil.getMessage("DETAIL_ALARM_UP", eqpId);
								row.put("ALARM_MSG", alarmText);
								System.out.println("1->0 변경:  "+alarmText);
							} else {
								row.put("ALARM_MSG", "");
								System.out.println("정상");
							}
						} else {
							row.put("ALARM_MSG", "");
						}
					} catch (Exception e) {
						logger.error("", e);
					}
				}
			}

			for(Map<String, Object> map : dataList) {
				final Tuple countMapSet = new Tuple();

				mapToTplConvert(map, countMapSet);

				countList.add(countMapSet);
			}


			//1. 10분 평균계산 적용용 위한 temp 데이터 저장
			Util.insertInLogpressoDatabase(countList, "bridge_layout_tmp", this.getClass().getSimpleName());

			finalList = getFinalData(dataList);

			//BRIDGE IMAGE ALARM 추가 ( 최종 테이블 저장 직전 판단 메모리 데이터로 판단 )
			List<Map<String, Object>> bridgeImgList =  validationBridgeAlarm(finalList);

			if (!bridgeImgList.isEmpty()) {
				finalList.addAll(bridgeImgList);
			}

			for (Map<String, Object> map : finalList) {
				final Tuple countMapSet2 = new Tuple();

				mapToTplConvert(map, countMapSet2);

				countList2.add(countMapSet2);
			}

			//최종 결과값 저장
			Util.insertInLogpressoDatabase(countList2, "bridge_layout_detail", this.getClass().getSimpleName());
		}catch (Exception e) {
			logger.error("", e);
		}
	}

	//Bridge_ALARM_IMAGE 지표값 추가 적용
	public List<Map<String, Object>> validationBridgeAlarm(List<Map<String, Object>> detailLilst){
		List<Map<String, Object>> result = new ArrayList<>();

		try {
			//알람 판정값 최종 적용
//			boolean finalflag = false;

			String eventDt = detailLilst.get(0).get("EVENT_DT").toString();

			// 알람 객체 취합용 리스트
			List<Map<String, Object>> alarmData = new ArrayList<>();

			//Port down 비율에 대한 flag IMAGE ALARM 01 ~ 12 # *미사용
//			List<Map<String, Object>> detailPortDataFlag = getDetailPortDataValidation(detailLilst);

			//Storage Util 지표 추가 15~16 # *미사용
//			List<Map<String, Object>> storageUtilDataFlag = getStorageUtilDataValidation(detailLilst);


			//추가 지표에 대한 flag 13 ~ 14 # *미사용
//			List<Map<String, Object>>  hubroomDataFlag = getHubroomDataValidation();


			//Hubroom - Bridge Time/HUB TOTAL QUE flag 17 ~ 20
			List<Map<String, Object>>  hubroomOHTDeadLock = getHubroomOHTDeadLock();

			//장비 down flag 21 ~ 24 (※지표등록 편의를 위해 BRIDGEIMAGE 로 등록 하였으나 ,이미지는 X )
			List<Map<String, Object>> machineDownAlarm = getMachineDownValidation();

//			alarmData.addAll(detailPortDataFlag);
//			alarmData.addAll(storageUtilDataFlag);
//			alarmData.addAll(hubroomDataFlag);
			alarmData.addAll(hubroomOHTDeadLock);
			alarmData.addAll(machineDownAlarm);

			Map<String, Object> bridgeImgAlarm = new HashMap<String, Object>();

			bridgeImgAlarm.put("EVENT_DT", eventDt);
			bridgeImgAlarm.put("FROM_FAB_ID", "M14");
			bridgeImgAlarm.put("TO_FAB_ID", "M16");
			bridgeImgAlarm.put("EQP_ID", "BRIDGE");
			bridgeImgAlarm.put("EQP_TYP", "BRIDGE_ALL");
			bridgeImgAlarm.put("DET_AREA_TYP", "ALL");
			bridgeImgAlarm.put("DET_IDC_NM", "BRIDGEIMAGE");
			bridgeImgAlarm.put("RSLT_VAL", "0");
			bridgeImgAlarm.put("ALARM_DESC", "");
			bridgeImgAlarm.put("ALARM_TITLE", "");


			//flag list 값이 하나라도 있는 경우 alarm 발생 상황
			if(alarmData.size()>0) {
				// dataList를 순회하며 문자열로 변환
				for (Map<String, Object> map : alarmData) {

					bridgeImgAlarm = new HashMap<>();

					bridgeImgAlarm.put("EVENT_DT", eventDt);
					bridgeImgAlarm.put("FROM_FAB_ID", "M14");
					bridgeImgAlarm.put("TO_FAB_ID", "M16");
					bridgeImgAlarm.put("EQP_ID", "BRIDGE");
					bridgeImgAlarm.put("EQP_TYP", "BRIDGE_ALL");
					bridgeImgAlarm.put("DET_AREA_TYP", "ALL");
					bridgeImgAlarm.put("DET_IDC_NM", "BRIDGEIMAGE");
					bridgeImgAlarm.put("RSLT_VAL", "0");
					String alarmCd = (String) map.get("ALARM_CD");
					bridgeImgAlarm.put("JUDGE_VAL", "2");
					bridgeImgAlarm.put("ALARM_YN", "Y");
					bridgeImgAlarm.put("ALARM_CD",alarmCd);
					String alarmTxt = XmlUtil.getMessage("BRIDGE_IMAGE_DEFAULT");
					String alarmDesc = XmlUtil.getMessage("BRIDGE_IMAGE_DEFAULT_NAME");
					String alarmTitle = XmlUtil.getMessage("BRIDGE_IMAGE_DEFAULT_TITLE");

					if (alarmTxt.contains(XmlUtil.DEFAULT_VALUE)) {
						alarmTxt = "";
					}

					if (alarmDesc.contains(XmlUtil.DEFAULT_VALUE)) {
						alarmDesc = "";
					}

					if (alarmTitle.contains(XmlUtil.DEFAULT_VALUE)) {
						alarmTitle = "";
					}


					//4. CURR_VAL HUBROOM TRANSFER Q
					String hubroomCurrVal = getHubRoomCurrValue();

					//5. 10분뒤 HUBROOM DATA
					String hubroomPredictVal = getHubRoomPredictValue();

					//6. VHL 가동률
					String vhlRunRateVal = getvhlRunRateValue();

					//7. MLUD 출고큐
					//8. OFS 차수
					String mludVal= "";
					String ofsVal= "";
					List<Map<String, Object>> alarmTextValue = getAlarmTextVal();

					if (!alarmTextValue.isEmpty()) {
						mludVal = alarmTextValue.get(0).get("CD_M16HUBMLUD").toString();
						ofsVal = alarmTextValue.get(0).get("CD_OFS").toString();
					}

					//9. ERROR VHL
					String errorVhl = getVhlErrorCount();


					if (alarmCd.equals("CD00000014")) {
						//주평균
						String weekVal = map.get("WEEK_AVG") == null ? "": map.get("WEEK_AVG").toString();
						//분당
						String dayVal = map.get("DAY_AVG") == null ? "": map.get("DAY_AVG").toString();
						//현재
						String currVal = map.get("CURR") == null ? "": map.get("CURR").toString();

						alarmTxt = XmlUtil.getMessage("BRIDGE_IMAGE_C0014",weekVal,dayVal,currVal);
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);
					}else if(alarmCd.equals("CD00000015")) {

						//0. STORAGE 사용률
						String storageRate = map.get("STORAGE_RATE").toString();

						//1. CNV INPUT CAPA DOWN COUNT
						String downCnt = map.get("DOWN_CNT").toString();

						//2. DOWN_PORT_NAME
						String downPortName = map.get("DOWN_PORT_NAME").toString();

						//3. CNV INPUT CAPA TOTAL
						//4. CURRVAL
						String inputCapaTotal = map.get("INPUT_CAPA_TOTAL").toString();
						String inputCapaCurrVal = map.get("INPUT_CAPA_CURR").toString();


						alarmTxt = XmlUtil.getMessage("BRIDGE_IMAGE_C0015",
								storageRate,
								downCnt,
								downPortName,
								inputCapaTotal,
								inputCapaCurrVal,
								hubroomCurrVal,
								hubroomPredictVal,
								vhlRunRateVal,
								mludVal,
								ofsVal);
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);


						bridgeImgAlarm.put("ALARM_DESC", "HUB Room Carrier 저장공간 사용률 높음");
						bridgeImgAlarm.put("ALARM_TITLE", "- M16-M14 Bridge 구간에 이상이 감지 되었습니다.");


						//JUDGE VALUE 5분지속인 경우에만 2 아니면 1


						//판단범위 넘기는지 검증
						String strCntQuery = "table duration=4m bridge_layout_detail    \r\n"
								+ "                        		| search string(FROM_FAB_ID) != \"\"  and string(TO_FAB_ID) != \"\"  and string(EQP_ID)  != \"\"  and string(EQP_TYP) != \"\"  \r\n"
								+ "                        		and  string(DET_AREA_TYP) != \"\"   and  string(DET_IDC_NM) != \"\"    \r\n"
								+ "                        		| rename FROM_FAB_ID as FR_FAB_ID , DET_IDC_NM as IDC_NM    \r\n"
								+ "                        		| eval  RSLT_VAL = int(RSLT_VAL) , JUDGE_VAL = if(( len(ALARM_MSG)>0  and IDC_NM ==\"STATE\"), 1, int(JUDGE_VAL)), ALARM_CD=if(isnull(ALARM_CD) , \"\", ALARM_CD)           \r\n"
								+ "                        		| fields EVENT_DT, FR_FAB_ID , TO_FAB_ID ,EQP_ID, EQP_TYP , DET_AREA_TYP , IDC_NM , RSLT_VAL, JUDGE_VAL,ALARM_CD,ALARM_MSG   \r\n"
								+ "                        		| sort FR_FAB_ID            \r\n"
								+ "                        		| rename ALARM_MSG as ALARM_MSG_CTN\r\n"
								+ "                        		| search ALARM_CD == \""+alarmCd+"\"		\r\n"
								+ "                        		| stats count(EVENT_DT) as CNT";


						List<Map<String, Object>> alarmCntRes  = LogpressoAPI.responseResult(strCntQuery.toString());
						String alarmCnt = alarmCntRes.get(0).get("CNT").toString();
						int totalAlarmCnt= Integer.parseInt(alarmCnt) + 1; // 현재 발생 수 더하기

						if(totalAlarmCnt >= 5) {
							bridgeImgAlarm.put("JUDGE_VAL", "2");
							bridgeImgAlarm.put("ALARM_YN", "Y");
						}else {
							bridgeImgAlarm.put("JUDGE_VAL", "1");
							bridgeImgAlarm.put("ALARM_YN", "N");
						}
					}else if(alarmCd.equals("CD00000016")){

						//0. STORAGE 사용률
						String storageRate = map.get("STORAGE_RATE").toString();

						//1. CNV INPUT CAPA DOWN COUNT
						String downCnt = map.get("DOWN_CNT").toString();
						//2. DOWN PORT NAME
						String downPortName = map.get("DOWN_PORT_NAME").toString();
						//3. DOWN RATE
						String downRate = map.get("DOWN_RATE").toString();




						alarmTxt = XmlUtil.getMessage("BRIDGE_IMAGE_C0016",
								storageRate,
								downCnt,
								downPortName,
								hubroomCurrVal,
								hubroomPredictVal,
								vhlRunRateVal,
								mludVal,
								ofsVal,
								errorVhl);
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);

						bridgeImgAlarm.put("ALARM_DESC", "HUB Room Carrier 저장공간 사용률 높음");
						bridgeImgAlarm.put("ALARM_TITLE", "- M16-M14 Bridge 구간에 이상이 감지 되었습니다.");
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);


						//JUDGE VALUE 5분지속인 경우에만 2 아니면 1


						//판단범위 넘기는지 검증
						String strCntQuery = "table duration=4m bridge_layout_detail    \r\n"
								+ "                        		| search string(FROM_FAB_ID) != \"\"  and string(TO_FAB_ID) != \"\"  and string(EQP_ID)  != \"\"  and string(EQP_TYP) != \"\"  \r\n"
								+ "                        		and  string(DET_AREA_TYP) != \"\"   and  string(DET_IDC_NM) != \"\"    \r\n"
								+ "                        		| rename FROM_FAB_ID as FR_FAB_ID , DET_IDC_NM as IDC_NM    \r\n"
								+ "                        		| eval  RSLT_VAL = int(RSLT_VAL) , JUDGE_VAL = if(( len(ALARM_MSG)>0  and IDC_NM ==\"STATE\"), 1, int(JUDGE_VAL)), ALARM_CD=if(isnull(ALARM_CD) , \"\", ALARM_CD)           \r\n"
								+ "                        		| fields EVENT_DT, FR_FAB_ID , TO_FAB_ID ,EQP_ID, EQP_TYP , DET_AREA_TYP , IDC_NM , RSLT_VAL, JUDGE_VAL,ALARM_CD,ALARM_MSG   \r\n"
								+ "                        		| sort FR_FAB_ID            \r\n"
								+ "                        		| rename ALARM_MSG as ALARM_MSG_CTN\r\n"
								+ "                        		| search ALARM_CD == \""+alarmCd+"\"		\r\n"
								+ "                        		| stats count(EVENT_DT) as CNT";


						List<Map<String, Object>> alarmCntRes  = LogpressoAPI.responseResult(strCntQuery.toString());
						String alarmCnt = alarmCntRes.get(0).get("CNT").toString();
						int totalAlarmCnt= Integer.parseInt(alarmCnt) + 1; // 현재 발생 수 더하기

						if(totalAlarmCnt >= 5) {
							bridgeImgAlarm.put("JUDGE_VAL", "2");
							bridgeImgAlarm.put("ALARM_YN", "Y");
						}else {
							bridgeImgAlarm.put("JUDGE_VAL", "1");
							bridgeImgAlarm.put("ALARM_YN", "N");
						}
					}else if(alarmCd.equals("CD00000017")){//M16 LFT 6F->3F OHT 몰림 발생 (1단계)


						alarmTxt = XmlUtil.getMessage("BRIDGE_IMAGE_C0017",
								map.get("BRIDGE_TIME_LIMIT").toString(),
								map.get("BRIDGE_TIME").toString(),
								map.get("M16ZT_Q_LIMIT").toString(),
								map.get("M16ZT_Q_TOTAL").toString(),
								map.get("M16_6F_ZT_MAXCAPA_LIMIT").toString(),
								map.get("OFS_LIMIT").toString(),
								map.get("STORAGE_UTIL").toString(),
								map.get("MACHINE_TRANSFER_CNT").toString());
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);

						bridgeImgAlarm.put("ALARM_DESC", "M14 HUB OHT 몰림 발생 1단계(6F ▶ 3F)");
						bridgeImgAlarm.put("ALARM_TITLE", "- M16-M14 Bridge 구간에 이상이 감지 되었습니다.");
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);

					}else if(alarmCd.equals("CD00000018")){//M16 LFT 6F->3F OHT 몰림 발생 (2단계)
						alarmTxt = XmlUtil.getMessage("BRIDGE_IMAGE_C0018",
								map.get("HUB_TOTAL_LIMIT").toString(),
								map.get("HUB_TOTAL_VAL").toString(),
								map.get("M16ZT_Q_LIMIT").toString(),
								map.get("M16ZT_Q_TOTAL").toString(),
								map.get("M16_6F_ZT_MAXCAPA_LIMIT").toString(),
								map.get("OFS_LIMIT").toString(),
								map.get("STORAGE_UTIL").toString(),
								map.get("MACHINE_TRANSFER_CNT").toString());
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);

						bridgeImgAlarm.put("ALARM_DESC", "M14 HUB OHT 몰림 발생 2단계(6F ▶ 3F)");
						bridgeImgAlarm.put("ALARM_TITLE", "- M16-M14 Bridge 구간에 이상이 감지 되었습니다.");
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);
					}else if(alarmCd.equals("CD00000019")){//M16 LFT 3F->6F OHT 몰림 발생 (1단계)
						alarmTxt = XmlUtil.getMessage("BRIDGE_IMAGE_C0019",
								map.get("BRIDGE_TIME_LIMIT").toString(),
								map.get("BRIDGE_TIME").toString(),
								map.get("M16ZT_Q_LIMIT").toString(),
								map.get("M16ZT_Q_TOTAL").toString(),
								map.get("OFS_LIMIT").toString(),
								map.get("STORAGE_UTIL").toString(),
								map.get("MACHINE_TRANSFER_CNT").toString());
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);

						bridgeImgAlarm.put("ALARM_DESC", "M16 HUB OHT 몰림 발생 1단계(3F ▶ 6F)");
						bridgeImgAlarm.put("ALARM_TITLE", "- M16-M14 Bridge 구간에 이상이 감지 되었습니다.");
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);
					}else if(alarmCd.equals("CD00000020")){//M16 LFT 3F->6F OHT 몰림 발생 (2단계)
						alarmTxt = XmlUtil.getMessage("BRIDGE_IMAGE_C0020",
								map.get("HUB_TOTAL_LIMIT").toString(),
								map.get("HUB_TOTAL_VAL").toString(),
								map.get("M16ZT_Q_LIMIT").toString(),
								map.get("M16ZT_Q_TOTAL").toString(),
								map.get("M16_6F_ZT_MAXCAPA_LIMIT").toString(),
								map.get("OFS_LIMIT").toString(),
								map.get("STORAGE_UTIL").toString(),
								map.get("MACHINE_TRANSFER_CNT").toString());
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);

						bridgeImgAlarm.put("ALARM_DESC", "M16 HUB OHT 몰림 발생 2단계(3F ▶ 6F)");
						bridgeImgAlarm.put("ALARM_TITLE", "- M16-M14 Bridge 구간에 이상이 감지 되었습니다.");
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);
					}else if(alarmCd.equals("CD00000021")){//M14A CNV DOWN
						int totalCnt = Integer.parseInt(map.get("INSERVICE_CNT").toString()) + Integer.parseInt(map.get("OUTOFSERVICE_CNT").toString());

						//bold 체
						alarmTitle = XmlUtil.getMessage("BRIDGE_IMAGE_C0021",
								map.get("MACHINELIST").toString(),
								totalCnt,
								map.get("OUTOFSERVICE_CNT").toString()
						);


						alarmTxt = XmlUtil.getMessage("HUBTOTAL_MSG",
								map.get("HUB_TOTAL_CNT").toString()
						);
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);
						bridgeImgAlarm.put("ALARM_DESC", "M14A Conveyor Down 발생");
						bridgeImgAlarm.put("ALARM_TITLE", alarmTitle);
					}else if(alarmCd.equals("CD00000022")) {//M14B BRIDGE LFT DOWN
						int totalCnt = Integer.parseInt(map.get("INSERVICE_CNT").toString()) + Integer.parseInt(map.get("OUTOFSERVICE_CNT").toString());

						alarmTitle = XmlUtil.getMessage("BRIDGE_IMAGE_C0022",
								map.get("MACHINELIST").toString(),
								totalCnt,
								map.get("OUTOFSERVICE_CNT").toString()
						);

						alarmTxt = XmlUtil.getMessage("HUBTOTAL_MSG",
								map.get("HUB_TOTAL_CNT").toString()
						);
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);

						bridgeImgAlarm.put("ALARM_DESC", "M14B Bridge Lifter Down 발생");
						bridgeImgAlarm.put("ALARM_TITLE", alarmTitle);
					}else if(alarmCd.equals("CD00000023")) {//M16A HUB OHT DOWN
						int totalCnt = Integer.parseInt(map.get("INSERVICE_CNT").toString()) + Integer.parseInt(map.get("OUTOFSERVICE_CNT").toString());

						alarmTitle = XmlUtil.getMessage("BRIDGE_IMAGE_C0023",
								map.get("MACHINELIST").toString(),
								totalCnt,
								map.get("OUTOFSERVICE_CNT").toString()
						);

						alarmTxt = XmlUtil.getMessage("STBUTIL_MSG",
								map.get("STORAGE_UTIL").toString()
						);
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);

						bridgeImgAlarm.put("ALARM_DESC", "M16HUB OHT Down 발생");
						bridgeImgAlarm.put("ALARM_TITLE",alarmTitle);
					}else if(alarmCd.equals("CD00000024")) {//M16A ZT DOWN
						int totalCnt = Integer.parseInt(map.get("INSERVICE_CNT").toString()) + Integer.parseInt(map.get("OUTOFSERVICE_CNT").toString());

						alarmTitle = XmlUtil.getMessage("BRIDGE_IMAGE_C0024",
								map.get("MACHINELIST").toString(),
								totalCnt,
								map.get("OUTOFSERVICE_CNT").toString()
						);
						alarmTxt = XmlUtil.getMessage("HUBTOTAL_MSG",
								map.get("HUB_TOTAL_CNT").toString()
						);
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);

						bridgeImgAlarm.put("ALARM_DESC", "M16A FAB내 Lifter Down 발생");
						bridgeImgAlarm.put("ALARM_TITLE", alarmTitle);
					}else {
						bridgeImgAlarm.put("ALARM_MSG",alarmTxt);
						bridgeImgAlarm.put("ALARM_DESC", alarmDesc);
						bridgeImgAlarm.put("ALARM_TITLE",alarmTitle);
					}

					String idx = alarmCd.replace("CD", "");
					int index = Integer.parseInt(idx);
					bridgeImgAlarm.put("DET_IDC_NM", "BRIDGEIMAGE"+String.valueOf(index));

					result.add(bridgeImgAlarm);
				}

			}else {
				//값이 없으면 정상 상황
				bridgeImgAlarm.put("JUDGE_VAL", "0");
				bridgeImgAlarm.put("ALARM_YN", "N");
				bridgeImgAlarm.put("ALARM_MSG", "");
				result.add(bridgeImgAlarm);
			}
		}catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}

	public List<Map<String, Object>> getDetailPortDataValidation(List<Map<String, Object>> detailList) {
		List<Map<String, Object>> result = new ArrayList<>();
		boolean flag = false;
		try {
			Map<String, String> alarmMessages = new HashMap<>();
			alarmMessages.put("CD_M14AAI", "CD00000001"); //14 cnv
			alarmMessages.put("CD_7FAIM14B7FM163F", "CD00000002");   //14 lft
			alarmMessages.put("CD_3FLFT3FAI", "CD00000003"); // m16 lft
			alarmMessages.put("CD_M16AAI", "CD00000004"); //16 cnv
			alarmMessages.put("CD_3FAI3FM14B7F", "CD00000005"); // 14 lft
			alarmMessages.put("CD_6FLFT6FAI", "CD00000006"); // // 16 lft
			alarmMessages.put("CD_M16AAO", "CD00000007"); // 14 cnv
			alarmMessages.put("CD_3FAOM14B7FB7F", "CD00000008"); // 14 lft
			alarmMessages.put("CD_6FAO2F3F6F", "CD00000009"); // 16 lft
			alarmMessages.put("CD_M14AAO", "CD00000010"); // 14 cnv
			alarmMessages.put("CD_M14B7FAO3FM14B7F", "CD00000011"); // 14 lft
			alarmMessages.put("CD_3FAO6F2F3F", "CD00000012"); // 16 lft

			Map<String, Double> alarmThresholds = new HashMap<>();
			String m16LftValid = XmlUtil.getVariableEnv("M16_LFT_PORT_DOWN_RATE",null);
			String m14CnvValid = XmlUtil.getVariableEnv("M14_CNV_PORT_DOWN_RATE",null);
			String m14LftValid = XmlUtil.getVariableEnv("M14_LFT_PORT_DOWN_RATE",null);
			double m16LftRate;
			double m14CnvRate;
			double m14LftRate;
			try {
				m16LftRate = m16LftValid.contains("Unknown ALARM CODE") ? 20.0 : Double.parseDouble(m16LftValid.toString());
				m14CnvRate = m14CnvValid.contains("Unknown ALARM CODE") ? 30.0 : Double.parseDouble(m14CnvValid.toString());
				m14LftRate = m14LftValid.contains("Unknown ALARM CODE") ? 33.0 : Double.parseDouble(m14LftValid.toString());
			}catch (Exception e) {
				m16LftRate = 20.0;
				m14CnvRate = 30.0;
				m14LftRate = 33.0;
			}

			// EQP_TYP 별 알람 발생 기준 설정
			alarmThresholds.put("CD_M16LFT", m16LftRate);
			alarmThresholds.put("CD_M14CNV", m14CnvRate);
			alarmThresholds.put("CD_M14LFT", m14LftRate);

			// 죽은 포트 비율 기준
			Map<Object, List<Map<String, Object>>> groupData = detailList.stream().collect(Collectors
					.groupingBy(row -> row.get("EVENT_DT") + "|"
							+ row.get("EQP_TYP") + "|" + row.get("DET_AREA_TYP")
					));


			Map<String, Map<String, Integer>> totalMap = new HashMap<>();
			Map<String, Map<String, Integer>> currentValMap = new HashMap<>();

			for (Map.Entry<Object, List<Map<String, Object>>> entry : groupData.entrySet()) {
				List<Map<String, Object>> groupRows = entry.getValue();
				for (Map<String, Object> row : groupRows) {
					try {
						String eqpTyp = row.get("EQP_TYP").toString();
						String detIdcNm = row.get("DET_IDC_NM").toString();
						String currentResult = row.get("RSLT_VAL").toString();
						String detAreaTyp = row.get("DET_AREA_TYP").toString();

						if (detIdcNm.contains("PORT")) {
							String key = eqpTyp + "_" + detAreaTyp;

							int value = Integer.parseInt(currentResult);

							if (detIdcNm.equals("CD_PORTTOTAL")) {
								totalMap.computeIfAbsent(eqpTyp, k -> new HashMap<>())
										.put(detAreaTyp, totalMap.getOrDefault(eqpTyp, new HashMap<>()).getOrDefault(detAreaTyp, 0) + value);
							} else if (detIdcNm.equals("CD_PORTINSERVICE")) {
								currentValMap.computeIfAbsent(eqpTyp, k -> new HashMap<>())
										.put(detAreaTyp, currentValMap.getOrDefault(eqpTyp, new HashMap<>()).getOrDefault(detAreaTyp, 0) + value);
							}
						}
					} catch (Exception e) {
						logger.error("", e);
					}
				}
			}
			Map<String, Object> resultMap = new HashMap<>();

			for (String eqpTyp : totalMap.keySet()) {
				Map<String, Integer> totalValues = totalMap.get(eqpTyp);
				Map<String, Integer> currentValues = currentValMap.getOrDefault(eqpTyp, new HashMap<>());

				double sumDownRates = 0;
				int count = 0;
				double downRate = 0.0;
				for (String detAreaTyp : totalValues.keySet()) {
					int total = totalValues.get(detAreaTyp);
					int currentVal = currentValues.getOrDefault(detAreaTyp, 0);
					downRate = total == 0 ? 0 : (double) (total - currentVal) / total * 100;


					double threshold = alarmThresholds.getOrDefault(eqpTyp, 0.0);

					if (downRate > threshold) {
						resultMap = new HashMap<>();
						String alarmCode = alarmMessages.getOrDefault(detAreaTyp, "");
						resultMap.put("ALARM_CD", alarmCode);
						resultMap.put("ALARM", true);
						if(!alarmCode.equals("")) {
							result.add(resultMap);
						}
					}
				}
			}


		}catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}

	public List<Map<String, Object>> getStorageUtilDataValidation(List<Map<String, Object>> detailList){
		List<Map<String, Object>> result = new ArrayList<>();
		boolean flag = false;

		try {

			Map<String, String> alarmMessages = new HashMap<>();
			alarmMessages.put("CD_3FAI3FM14B7F", "CD00000015");
			alarmMessages.put("CD_M16AAI", "CD00000016");
			Map<String, Double> alarmThresholds = new HashMap<>();
			String storageUtilPortDown = XmlUtil.getVariableEnv("STORAGE_UTIL_PORT_DOWN",null);
			List<Map<String, Object>> storageUtils = new ArrayList<Map<String, Object>>();
			List<Map<String, Object>> m14LftDownPortName = new ArrayList<Map<String, Object>>();
			List<Map<String, Object>> m16CnvDownPortName = new ArrayList<Map<String, Object>>();

			String storageUtil = XmlUtil.getVariableEnv("STORAGE_UTIL_RATE",null);

			double portDownRate;
			double storageUtilRate = 0.0;

			try {
				portDownRate = storageUtilPortDown.contains("Unknown ALARM CODE") ? 99.0 : Double.parseDouble(storageUtilPortDown.toString());
				storageUtilRate = storageUtil.contains("Unknown ALARM CODE") ? 50.0 : Double.parseDouble(storageUtil.toString());
			}catch (Exception e) {
				portDownRate = 99.0;
			}
			alarmThresholds.put("CD_M14CNV", portDownRate);
			alarmThresholds.put("CD_M14LFT", portDownRate);


			// 죽은 포트 비율 기준
			Map<Object, List<Map<String, Object>>> groupData = detailList.stream().collect(Collectors
					.groupingBy(row -> row.get("EVENT_DT") + "|"
							+ row.get("EQP_TYP") + "|" + row.get("DET_AREA_TYP")
					));


			Map<String, Map<String, Integer>> totalMap = new HashMap<>();
			Map<String, Map<String, Integer>> currentValMap = new HashMap<>();


			for (Map.Entry<Object, List<Map<String, Object>>> entry : groupData.entrySet()) {
				List<Map<String, Object>> groupRows = entry.getValue();
				for (Map<String, Object> row : groupRows) {
					try {
						String eqpTyp = row.get("EQP_TYP").toString();
						String detIdcNm = row.get("DET_IDC_NM").toString();
						String currentResult = row.get("RSLT_VAL").toString();
						String detAreaTyp = row.get("DET_AREA_TYP").toString();

						if (detIdcNm.contains("PORT")) {
							String key = eqpTyp + "_" + detAreaTyp;

							int value = Integer.parseInt(currentResult);

							if (detIdcNm.equals("CD_PORTTOTAL")) {
								totalMap.computeIfAbsent(eqpTyp, k -> new HashMap<>())
										.put(detAreaTyp, totalMap.getOrDefault(eqpTyp, new HashMap<>()).getOrDefault(detAreaTyp, 0) + value);
							} else if (detIdcNm.equals("CD_PORTINSERVICE")) {
								currentValMap.computeIfAbsent(eqpTyp, k -> new HashMap<>())
										.put(detAreaTyp, currentValMap.getOrDefault(eqpTyp, new HashMap<>()).getOrDefault(detAreaTyp, 0) + value);
							}
						}
					} catch (Exception e) {
						logger.error("", e);
					}
				}
			}

			Map<String, Object> resultMap = new HashMap<>();

			for (String eqpTyp : totalMap.keySet()) {
				Map<String, Integer> totalValues = totalMap.get(eqpTyp);
				Map<String, Integer> currentValues = currentValMap.getOrDefault(eqpTyp, new HashMap<>());

				double downRate = 0.0;
				for (String detAreaTyp : totalValues.keySet()) {
					int total = totalValues.get(detAreaTyp);
					int currentVal = currentValues.getOrDefault(detAreaTyp, 0);
					downRate = Math.round((total == 0 ? 0 : (double) (total - currentVal) / total * 100) * 10.0) / 10.0;

					double threshold = alarmThresholds.getOrDefault(eqpTyp, 0.0);
					if (downRate > threshold) {
						resultMap = new HashMap<>();
						String alarmCode = alarmMessages.getOrDefault(detAreaTyp, "");
						resultMap.put("ALARM_CD", alarmCode);
						resultMap.put("ALARM", true);
//                        resultMap.put("DOWN_CNT", (total - currentVal));
						resultMap.put("DOWN_RATE", downRate);
						resultMap.put("INPUT_CAPA_TOTAL",total);
						resultMap.put("INPUT_CAPA_CURR",currentVal);


						if(!alarmCode.equals("")) {
							result.add(resultMap);
						}
					}
				}
			}

			if(result.size() > 0) {//Port DownRate 판단 이후
				//STORAGE UTIL 값 추가 판단
				try {
					// Oracle 데이터 조회
					for (String fab : new String[] { "M16A","M14B","M14A"}) {
						String xmlPath = "";
						String dynamicQuery = "";
						String xmlPath2 = "";
						String dynamicQuery2 = "";
						String xmlPath3 = "";
						String dynamicQuery3 = "";
						switch (fab) {
							case "M16A":
								var factory = QueryExecutorFactory.getQueryExecutor(fab);
								xmlPath = FilePathUtil.factoryPath(factory.getConnectionId());
								dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_M16A_STORAGE_UTIL");
								List<Map<String, Object>> m16a_detailList = factory.selectList(dynamicQuery);
								storageUtils.addAll(m16a_detailList);
								factory.close();
								break;
							case "M14B":
								var factory2 = QueryExecutorFactory.getQueryExecutor(fab);
								xmlPath2 = FilePathUtil.factoryPath(factory2.getConnectionId());
								dynamicQuery2 = XmlUtil.loadQuery(xmlPath2 , "SELECT_M14LFT_DOWN_PORTLIST");
								List<Map<String, Object>> m14_lft_portName = factory2.selectList(dynamicQuery2);
//        					storageUtils.addAll(m14_lft_portName);
								m14LftDownPortName.addAll(m14_lft_portName);
								factory2.close();
								break;
							case "M14A":
								var factory3 = QueryExecutorFactory.getQueryExecutor(fab);
								xmlPath3 = FilePathUtil.factoryPath(factory3.getConnectionId());
								dynamicQuery3 = XmlUtil.loadQuery(xmlPath3, "SELECT_M16CNV_DOWN_PORTLIST");
								List<Map<String, Object>> m16_cnv_portName  = factory3.selectList(dynamicQuery3);
//        					storageUtils.addAll(m16_cnv_portName);
								m16CnvDownPortName.addAll(m16_cnv_portName);
								factory3.close();
								break;
							default:
								continue;
						}
					}

					if(storageUtils.size() > 0 ) {
						String currValue = storageUtils.get(0).get("CURR_VAL").toString();



						double currVal = Double.parseDouble(currValue);
						if(currVal > storageUtilRate) {
							for(Map<String, Object> res : result) {
								if(res.get("ALARM_CD") != null) {
									if(res.get("ALARM_CD").toString().equals("CD00000016")) {
//        								 resultMap.put("DOWN_CNT", (total - currentVal));


										String downPortName = m14LftDownPortName.get(0).get("DOWN_PORT_NAME")  == null ? "": m14LftDownPortName.get(0).get("DOWN_PORT_NAME").toString();
										String downPortCnt = m14LftDownPortName.get(0).get("OVER") == null ? "" : m14LftDownPortName.get(0).get("OVER").toString();
										res.put("DOWN_CNT", downPortCnt);

										String[] portNames = downPortName.split(",");
										StringBuilder formattedPortNames = new StringBuilder();

										for (int i = 0; i < portNames.length; i++) {
											String port = portNames[i].trim();
											if (i > 0) {
												formattedPortNames.append(", \n");
											}
											formattedPortNames.append(port);
										}
										res.put("DOWN_PORT_NAME", formattedPortNames);
									}else {
										String downPortName = m16CnvDownPortName.get(0).get("DOWN_PORT_NAME") == null ? "":  m16CnvDownPortName.get(0).get("DOWN_PORT_NAME").toString();
										String downPortCnt = m16CnvDownPortName.get(0).get("OVER") == null ? "" : m16CnvDownPortName.get(0).get("OVER").toString();
										res.put("DOWN_CNT", downPortCnt);

										String[] portNames = downPortName.split(",");
										StringBuilder formattedPortNames = new StringBuilder();

										for (int i = 0; i < portNames.length; i++) {
											String port = portNames[i].trim();
											if (i > 0) {
												formattedPortNames.append(", \n");
											}
											formattedPortNames.append(port);
										}
										res.put("DOWN_PORT_NAME", formattedPortNames);
									}
								}
								res.put("STORAGE_RATE", currValue);
							}
							return result;
						}else { // STORAGE UTIL 조건이 아닌경우 알람 보고 X
							result = new ArrayList<Map<String,Object>>();
						}
					}


				}catch (Exception e) {
					e.printStackTrace();
					result = new ArrayList<Map<String,Object>>();
				}
			}

		}catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}


	public List<Map<String, Object>> getHubroomOHTDeadLock(){
		List<Map<String, Object>> result = new ArrayList<Map<String,Object>>();
		List<Map<String, Object>> queryResByBridgeTimeAvg = new ArrayList<Map<String,Object>>();
		List<Map<String, Object>> queryResByM16LftTransferCnt = new ArrayList<Map<String,Object>>();
		List<Map<String, Object>> queryResByM16LftHubTotalCnt = new ArrayList<Map<String,Object>>();
		try {

			String birdgeTimeLimit = XmlUtil.getVariableEnv("BRIDGE_TIME_LIMIT",null);
			if(birdgeTimeLimit.contains("Unknown ALARM CODE")) {
				birdgeTimeLimit = "5";
			}
			String m16ZTQLimit = XmlUtil.getVariableEnv("M16ZT_Q_LIMIT",null);
			if(m16ZTQLimit.contains("Unknown ALARM CODE")) {
				m16ZTQLimit = "130";
			}
			String m16ZTQLimit2 = XmlUtil.getVariableEnv("M16ZT_Q_LIMIT_2",null);
			if(m16ZTQLimit2.contains("Unknown ALARM CODE")) {
				m16ZTQLimit2 = "200";
			}
			String hubroomTotalLimit = XmlUtil.getVariableEnv("M16_HUBROOM_TOTAL_LIMIT",null);
			if(hubroomTotalLimit.contains("Unknown ALARM CODE")) {
				hubroomTotalLimit = "600";
			}
			String m166FMaxcapaLimit = XmlUtil.getVariableEnv("M16_6F_ZT_MAXCAPA_LIMIT",null);
			if(m166FMaxcapaLimit.contains("Unknown ALARM CODE")) {
				m166FMaxcapaLimit = "3";
			}
			String m166FMaxcapaLimit2 = XmlUtil.getVariableEnv("M16_6F_ZT_MAXCAPA_LIMIT_2",null);
			if(m166FMaxcapaLimit2.contains("Unknown ALARM CODE")) {
				m166FMaxcapaLimit2 = "1";
			}
			String m166FMaxcapaLimit3 = XmlUtil.getVariableEnv("M16_6F_ZT_MAXCAPA_LIMIT_3",null);
			if(m166FMaxcapaLimit3.contains("Unknown ALARM CODE")) {
				m166FMaxcapaLimit3 = "3";
			}
			boolean levelFlag = false;

			Map<String, String> alarmMessages = new HashMap<>();


			//1단계 조건 만족 이후 2단게 조건 추가 만족 시 -> 2단계 발생

			//1. Bridge Time Check 1단계 발생상황인지 검증
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "bridgeTimeAverage");
			queryResByBridgeTimeAvg = LogpressoAPI.responseResult(strQuery.toString());

			//5분간 평균 bridgeTime 5분이상인지 check
			double bridgeTimeAvg = Double.parseDouble(queryResByBridgeTimeAvg.get(0).get("AVG_VAL").toString());


			String alarmText = "";
			double birdgeTimeLimitVal = Double.parseDouble(birdgeTimeLimit);
			if(bridgeTimeAvg > birdgeTimeLimitVal) {//variable
				//2. M14 방향 / M16 방향 ZT 층간 반송량 Check

				String strQuery2 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "m16LftTransferCnt");
				queryResByM16LftTransferCnt = LogpressoAPI.responseResult(strQuery2.toString());

				double lft6f3fAvg = 0.0;
				int lft6f3fTotal = 0;
				double lft3f6fAvg = 0.0;
				int lft3f6fTotal = 0;
				StringBuilder res6F3FTXT = new StringBuilder();
				StringBuilder res3F6FTXT = new StringBuilder();
				for(Map<String, Object> row : queryResByM16LftTransferCnt) {
					if(row.get("IDC_NM").equals("CD_6F3F")) {
						lft6f3fAvg = Double.parseDouble(row.get("AVG_VAL").toString());
						lft6f3fTotal = Integer.parseInt(row.get("TOTAL_VAL").toString());

					}
					if(row.get("IDC_NM").equals("CD_3F6F")) {
						lft3f6fAvg = Double.parseDouble(row.get("AVG_VAL").toString());
						lft3f6fTotal = Integer.parseInt(row.get("TOTAL_VAL").toString());
					}
				}
				int m16ZTQLimitVal = Integer.parseInt(m16ZTQLimit);
				int m16ZTQLimitVal2 = Integer.parseInt(m16ZTQLimit2);


				//문자열 생성
				Map<String, Map<String, Integer>> groupedData = new HashMap<>();

				for (Map<String, Object> entry : queryResByM16LftTransferCnt) {
					String idcNm = (String) entry.get("IDC_NM");
					String machineName = (String) entry.get("MACHINENAME");
					Integer cntVal = Integer.parseInt(entry.get("CNT_VAL").toString());

					groupedData.putIfAbsent(idcNm, new HashMap<>());
					Map<String, Integer> machineMap = groupedData.get(idcNm);
					machineMap.putIfAbsent(machineName, 0);
					machineMap.put(machineName, machineMap.get(machineName) + cntVal);
				}

				Map<String, String> results = new HashMap<>();
				results.put("CD_3F6F", "");
				results.put("CD_6F3F", "");

				for (Map.Entry<String, Map<String, Integer>> idcEntry : groupedData.entrySet()) {
					String idcNm = idcEntry.getKey();
					Map<String, Integer> machineMap = idcEntry.getValue();

					// 정렬 기능 추가
					List<Map.Entry<String, Integer>> sortedMachineEntries = new ArrayList<>(machineMap.entrySet());
					sortedMachineEntries.sort(Map.Entry.comparingByKey());

					List<String> machineEntries = new ArrayList<>();
					for (Map.Entry<String, Integer> machineEntry : sortedMachineEntries) {
						machineEntries.add(machineEntry.getKey() + ": " + machineEntry.getValue());
					}

					String re = "";
					for (int i = 0; i < machineEntries.size(); i += 2) {
						re += machineEntries.get(i);
						if (i + 1 < machineEntries.size()) {
							re += " | " + machineEntries.get(i + 1);
						}
						re += "\\n\n";
					}
					results.put(idcNm, re);
				}


				String resultCD6F3F = results.get("CD_6F3F");
				resultCD6F3F = "3. 6F▶3F ZT현황 (평균"+ lft6f3fAvg +" 총합"+ lft6f3fTotal +")\\n\n"+ resultCD6F3F;
				String resultCD3F6F = results.get("CD_3F6F");
				resultCD3F6F = "3. 3F▶6F ZT현황 (평균"+ lft3f6fAvg +" 총합"+ lft3f6fTotal +")\\n\n"+ resultCD3F6F;


				//OFS / MLUD VALUE M16->M14
				String ofsVal ="";
				List<Map<String, Object>> ofsMludValue = getAlarmTextVal();
				if(ofsMludValue.size()>0) {
					ofsVal = ofsMludValue.get(0).get("CD_OFS").toString();
				}
				String ofsVal2 ="";
				List<Map<String, Object>> ofsMludValue2 = getAlarmTextVal2();
				if(ofsMludValue2.size()>0) {
					ofsVal2 = ofsMludValue2.get(0).get("CD_OFS").toString();
				}


				//STORAGE UTIL
				List<Map<String, Object>> storageUtils = new ArrayList<Map<String, Object>>();

				for (String fab : new String[] { "M16A"}) {
					String xmlPath = "";
					String dynamicQuery = "";
					switch (fab) {
						case "M16A":
							var factory = QueryExecutorFactory.getQueryExecutor(fab);
							xmlPath = FilePathUtil.factoryPath(factory.getConnectionId());
							dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_M16A_STORAGE_UTIL");
							List<Map<String, Object>> m16a_detailList = factory.selectList(dynamicQuery);
							storageUtils.addAll(m16a_detailList);
							factory.close();
							break;
						default:
							continue;
					}
				}
				String storageUtilsVal = "";

				if(storageUtils.size() > 0 ) {
					storageUtilsVal = storageUtils.get(0).get("CURR_VAL").toString();
				}




				//HUBROOM CURRVAL
				String hubroomCurrVal = getHubRoomCurrValue();

				//HUBROOM PREDICTVAL
				String hubroomPredictVal = getHubRoomPredictValue();

				//HUBROOM TOTAL
				String strQuery3 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "m16HubTotalCnt");
				queryResByM16LftHubTotalCnt = LogpressoAPI.responseResult(strQuery3.toString());

				int queryResByM16LftHubTotalCntVal = Integer.parseInt(queryResByM16LftHubTotalCnt.get(0).get("IDC_VAL").toString());
				int hubroomTotalLimitVal = Integer.parseInt(hubroomTotalLimit);

				if(lft6f3fTotal > m16ZTQLimitVal) {//6F->3F

					//3. HUB TOTAL check 2단계 발생 상황시 1단계알람->2단계 알람 변경 적용
					Map<String, Object> warningData = new HashMap<>();
					if((lft6f3fTotal > m16ZTQLimitVal2) & (queryResByM16LftHubTotalCntVal >hubroomTotalLimitVal)) {
						warningData.put("HUB_TOTAL_LIMIT", hubroomTotalLimitVal);
						warningData.put("HUB_TOTAL_VAL", queryResByM16LftHubTotalCntVal);
						//M16LFT ZT 반송량 Limit 변수 값
						warningData.put("M16ZT_Q_LIMIT", m16ZTQLimitVal);

						//M16LFT ZT 6->3F 현재 반송 전체수량
						warningData.put("M16ZT_Q_TOTAL", lft6f3fTotal);

						warningData.put("M16_6F_ZT_MAXCAPA_LIMIT", m166FMaxcapaLimit2);

						warningData.put("OFS_LIMIT", ofsVal);
						warningData.put("STORAGE_UTIL", storageUtilsVal);
						warningData.put("FLAG", true);
						warningData.put("ALARM_CD", "CD00000018");
						warningData.put("MACHINE_TRANSFER_CNT", resultCD6F3F);

						result.add(warningData);
					}else {

						//bridgeTime Limit 변수 값
						warningData.put("BRIDGE_TIME_LIMIT", birdgeTimeLimitVal);

						//bridgeTime 현재 값
						warningData.put("BRIDGE_TIME", bridgeTimeAvg);

						//M16LFT ZT 반송량 Limit 변수 값
						warningData.put("M16ZT_Q_LIMIT", m16ZTQLimitVal);

						//M16LFT ZT 6->3F 현재 반송 전체수량
						warningData.put("M16ZT_Q_TOTAL", lft6f3fTotal);

						//M16 6F ZT AI MAXCAPA Limit 변수 값
						warningData.put("M16_6F_ZT_MAXCAPA_LIMIT", m166FMaxcapaLimit);


						warningData.put("OFS_LIMIT", ofsVal);
						warningData.put("HUBROOM_CURR", hubroomCurrVal);
						warningData.put("HUBROOM_PRED", hubroomPredictVal);
						warningData.put("STORAGE_UTIL", storageUtilsVal);

						//장비별 반송큐 현황
						warningData.put("MACHINE_TRANSFER_CNT", resultCD6F3F);


						warningData.put("FLAG", true);
						warningData.put("ALARM_CD", "CD00000017");
						result.add(warningData);

					}

				}
				if(lft3f6fTotal >= m16ZTQLimitVal) {//3F->6F
					//3. HUB TOTAL check 2단계 발생 상황시 1단계알람->2단계 알람 변경 적용
					Map<String, Object> warningData = new HashMap<>();

					if((lft3f6fTotal > m16ZTQLimitVal2) & (queryResByM16LftHubTotalCntVal >hubroomTotalLimitVal)) {

						warningData.put("HUB_TOTAL_LIMIT", hubroomTotalLimitVal);
						warningData.put("HUB_TOTAL_VAL", queryResByM16LftHubTotalCntVal);
						//M16LFT ZT 반송량 Limit 변수 값
						warningData.put("M16ZT_Q_LIMIT", m16ZTQLimitVal);

						//M16LFT ZT 6->3F 현재 반송 전체수량
						warningData.put("M16ZT_Q_TOTAL", lft6f3fTotal);

						warningData.put("M16_6F_ZT_MAXCAPA_LIMIT", m166FMaxcapaLimit3);
						warningData.put("OFS_LIMIT", ofsVal);
						warningData.put("STORAGE_UTIL", storageUtilsVal);
						warningData.put("FLAG", true);
						warningData.put("ALARM_CD", "CD00000020");
						warningData.put("MACHINE_TRANSFER_CNT", resultCD3F6F);

						result.add(warningData);
					}else {

						//bridgeTime Limit 변수 값
						warningData.put("BRIDGE_TIME_LIMIT", birdgeTimeLimitVal);

						//bridgeTime 현재 값
						warningData.put("BRIDGE_TIME", bridgeTimeAvg);

						//M16LFT ZT 반송량 Limit 변수 값
						warningData.put("M16ZT_Q_LIMIT", m16ZTQLimitVal);

						//M16LFT ZT 6->3F 현재 반송 전체수량
						warningData.put("M16ZT_Q_TOTAL", lft6f3fTotal);
//
//            			//M16 6F ZT AI MAXCAPA Limit 변수 값
//            			warningData.put("M16_6F_ZT_MAXCAPA_LIMIT", m166FMaxcapaLimit);


						warningData.put("OFS_LIMIT", ofsVal2);
						warningData.put("HUBROOM_CURR", hubroomCurrVal);
						warningData.put("HUBROOM_PRED", hubroomPredictVal);
						warningData.put("STORAGE_UTIL", storageUtilsVal);

						//장비별 반송큐 현황
						warningData.put("MACHINE_TRANSFER_CNT", resultCD3F6F);

						warningData.put("FLAG", true);
						warningData.put("ALARM_CD", "CD00000019");
						result.add(warningData);

					}
				}

			}

		}catch (Exception e) {
			logger.error("",e);
		}

		return result;
	}


	//신규 추가
	public List<Map<String, Object>> getMachineDownValidation(){
		List<Map<String, Object>> result = new ArrayList<Map<String,Object>>();
		try {

			Map<String, Object> downMapData = new HashMap<>();

			Map<String, Object> m14aCnvDown = new HashMap<String, Object>();
			Map<String, Object> m14bBrLftDown = new HashMap<String, Object>();
			Map<String, Object> m16aHubOhtDown = new HashMap<String, Object>();
			Map<String, Object> m16aZtDown = new HashMap<String, Object>();
			List<Map<String, Object>> storageUtils = new ArrayList<Map<String, Object>>();

			String storageUtilsVal = "";
			boolean m14aCNVFlag = false;
			boolean m14bBRLFTFlag = false;
			boolean m16aHUBOHTFlag = false;
			boolean m16aZTFlag = false;
			for (String fab : new String[] { "M14A", "M14B", "M16A" }) {
				String xmlPath = "";
				String dynamicQuery = "";
				switch (fab) {
					case "M14A":
						var factory = QueryExecutorFactory.getQueryExecutor(fab);
						xmlPath = FilePathUtil.factoryPath(factory.getConnectionId());
						dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_MACHINE_DOWN_CNT");
						List<Map<String, Object>> m14a_downList = factory.selectList(dynamicQuery);
						factory.close();

						if(m14a_downList.size() > 0) {
							m14aCnvDown = m14a_downList.get(0);
							if(m14aCnvDown.get("ID") != null) {
								m14aCNVFlag = true;
							}
						}

						break;
					case "M14B":
						var factory2 = QueryExecutorFactory.getQueryExecutor(fab);
						xmlPath = FilePathUtil.factoryPath(factory2.getConnectionId());
						dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_MACHINE_DOWN_CNT");
						List<Map<String, Object>> m14b_downList = factory2.selectList(dynamicQuery);
						factory2.close();


						if(m14b_downList.size() > 0) {
							m14bBrLftDown = m14b_downList.get(0);
							if(m14bBrLftDown.get("ID") != null) {
								m14bBRLFTFlag = true;
							}
						}

						break;
					case "M16A":
						var factory3 = QueryExecutorFactory.getQueryExecutor(fab);
						xmlPath = FilePathUtil.factoryPath(factory3.getConnectionId());
						dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_MACHINE_DOWN_CNT");
						List<Map<String, Object>> m16a_hub_downList = factory3.selectList(dynamicQuery);
						factory3.close();

						if(m16a_hub_downList.size() > 0) {
							m16aHubOhtDown = m16a_hub_downList.get(0);

							if(m16aHubOhtDown.get("ID") != null) {
								m16aHUBOHTFlag = true;
							}
						}


						var factory4 = QueryExecutorFactory.getQueryExecutor(fab);
						xmlPath = FilePathUtil.factoryPath(factory4.getConnectionId());
						dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_MACHINE_DOWN_CNT2");
						List<Map<String, Object>> m16a_zt_downList = factory4.selectList(dynamicQuery);
						factory4.close();

						if(m16a_zt_downList.size() > 0) {
							m16aZtDown = m16a_zt_downList.get(0);

							if(m16aZtDown.get("ID") != null) {
								m16aZTFlag = true;
							}
						}


						var factory5 = QueryExecutorFactory.getQueryExecutor(fab);
						xmlPath = FilePathUtil.factoryPath(factory5.getConnectionId());
						dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_M16A_STORAGE_UTIL");
						List<Map<String, Object>> storage_utilList = factory5.selectList(dynamicQuery);
						storageUtils.addAll(storage_utilList);
						factory5.close();

						if(storageUtils.size() > 0 ) {
							storageUtilsVal = storageUtils.get(0).get("CURR_VAL").toString();
						}

						break;
					default:
						continue;
				}
			}

			String strQuery3 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "m16HubTotalCnt");
			List<Map<String, Object>> hubTotalCnt= LogpressoAPI.responseResult(strQuery3.toString());

			int hubTotalCntVal = Integer.parseInt(hubTotalCnt.get(0).get("IDC_VAL").toString());

			if(m14aCNVFlag) {//M14A CNV 장비 DOWN
				downMapData.put("ALARM_CD", "CD00000021");
				downMapData.put("FLAG", true);
				downMapData.put("HUB_TOTAL_CNT", hubTotalCntVal);

				downMapData.put("MACHINELIST", m14aCnvDown.get("ID").toString());
				downMapData.put("INSERVICE_CNT", m14aCnvDown.get("INSERVICE_CNT").toString());
				downMapData.put("OUTOFSERVICE_CNT", m14aCnvDown.get("OUTOFSERVICE_CNT").toString());
				result.add(downMapData);
			}
			if(m14bBRLFTFlag) {//M14B BRIDGE LFT 장비 DOWN
				downMapData.put("ALARM_CD", "CD00000022");
				downMapData.put("FLAG", true);
				downMapData.put("HUB_TOTAL_CNT", hubTotalCntVal);

				downMapData.put("MACHINELIST", m14bBrLftDown.get("ID").toString());
				downMapData.put("INSERVICE_CNT", m14bBrLftDown.get("INSERVICE_CNT").toString());
				downMapData.put("OUTOFSERVICE_CNT", m14bBrLftDown.get("OUTOFSERVICE_CNT").toString());
				result.add(downMapData);
			}
			if(m16aHUBOHTFlag) {//M16A HUB OHT 장비 DOWN
				downMapData.put("ALARM_CD", "CD00000023");
				downMapData.put("FLAG", true);
				downMapData.put("STORAGE_UTIL", storageUtilsVal);

				downMapData.put("MACHINELIST", m16aHubOhtDown.get("ID").toString());
				downMapData.put("INSERVICE_CNT", m16aHubOhtDown.get("INSERVICE_CNT").toString());
				downMapData.put("OUTOFSERVICE_CNT", m16aHubOhtDown.get("OUTOFSERVICE_CNT").toString());
				result.add(downMapData);
			}
			if(m16aZTFlag) {//M16A ZT 장비 DOWN
				downMapData.put("ALARM_CD", "CD00000024");
				downMapData.put("FLAG", true);
				downMapData.put("HUB_TOTAL_CNT", hubTotalCntVal);


				downMapData.put("MACHINELIST", m16aZtDown.get("ID").toString());
				downMapData.put("INSERVICE_CNT", m16aZtDown.get("INSERVICE_CNT").toString());
				downMapData.put("OUTOFSERVICE_CNT", m16aZtDown.get("OUTOFSERVICE_CNT").toString());
				result.add(downMapData);
			}
		}catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}

	public List<Map<String, Object>> getHubroomDataValidation() {
		boolean flag = false;
		StringBuilder sQuery = new StringBuilder();
		StringBuilder sQuery2 = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<>();
		List<Map<String, Object>> m16a_qCompleteList = new ArrayList<Map<String, Object>>();
		List<Map<String, Object>> judgeRange = new ArrayList<>();
		try {
			// Oracle 데이터 조회
			for (String fab : new String[] { "M16A"}) {
				String xmlPath = "";
				String dynamicQuery = "";
				switch (fab) {
					case "M16A":
						var factory = QueryExecutorFactory.getQueryExecutor(fab);
						xmlPath = FilePathUtil.factoryPath(factory.getConnectionId());
						dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_M16A_DAT");
						List<Map<String, Object>> m16a_detailList = factory.selectList(dynamicQuery);
						m16a_qCompleteList.addAll(m16a_detailList);
						factory.close();
						break;
					default:
						continue;
				}
			}


			//판단범위 넘기는지 검증
			String strQuery2 = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "bridgeJudgeRangeQCompleted");
			sQuery2.append(strQuery2);
			judgeRange = LogpressoAPI.responseResult(sQuery2.toString());



			// judgeRange 를 Map 으로 변환하여 빠른 조회 가능하도록 함
			Map<String, Map<String, Object>> judgeRangeMap = judgeRange.stream()
					.collect(Collectors.toMap(
							row -> row.get("FR_FAB_ID") + "|" + row.get("TO_FAB_ID") + "|"
									+ row.get("IDC_NM") + "|" + row.get("FR_LOC_NM") + "|" + row.get("TO_LOC_NM"),
							Function.identity()
					));



			for (Map<String, Object> data : m16a_qCompleteList) {
				String idcNm = data.get("IDC_NM").toString();

				String key = data.get("FR_FAB_ID") + "|" + data.get("TO_FAB_ID") + "|"
						+ data.get("IDC_NM") + "|" + data.get("FR_LOC_NM") + "|" + data.get("TO_LOC_NM");
				Map<String, Object> range = judgeRangeMap.get(key);

				if (range != null) {
					double currVal = Double.parseDouble(data.get("CURR_VAL").toString());
					double lowerVal = Double.parseDouble(range.get("LOWER_VAL").toString());
					double upperVal = Double.parseDouble(range.get("UPPER_VAL").toString());

					if (currVal < lowerVal || currVal > upperVal) { // 지표 발생
						//CD_M16TOHUBQCPT : 00000013 / CD_HUBTOM16QCPT: 00000014
						if(idcNm.equals("CD_M16TOHUBQCPT")) {
							Map<String, Object> warningData = new HashMap<>();
							warningData.put("FLAG", true);
							warningData.put("ALARM_CD", "CD00000013" );
							result.add(warningData);
						}
						if(idcNm.equals("CD_HUBTOM16QCPT")) {
//	                		주평균 {0} \n
//	                		분당 {1} \n
//	                		현재 {2} \n
							List<Map<String, Object>> avgList = new ArrayList<Map<String,Object>>();
							String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "hubToM16QPTAvg");
							sQuery.append(strQuery);
							avgList = LogpressoAPI.responseResult(sQuery.toString());
							Map<String, Object> warningData = new HashMap<>();

							if(avgList.size() > 0 ) {
								warningData.put("WEEK_AVG", avgList.get(0).get("WEEK_AVG"));
								warningData.put("DAY_AVG", avgList.get(0).get("DAY_AVG"));
								warningData.put("CURR", currVal);
							}

							warningData.put("FLAG", true);
							warningData.put("ALARM_CD", "CD00000014");
							result.add(warningData);
						}
					}
				}
			}
		}catch (Exception e) {
			e.printStackTrace();
		}
		return result;
	}


	public List<Map<String, Object>> getDetailDataByOracle(){
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		try {
			for (String fab : new String[] { "M14B", "M16A", "M14A" }) {
				String xmlPath = "";
				String dynamicQuery = "";
				switch (fab) {
					case "M14B":
						var factory = QueryExecutorFactory.getQueryExecutor(fab);
						xmlPath = FilePathUtil.factoryPath(factory.getConnectionId());
						dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_M14B_DETAIL_DAT");
						List<Map<String, Object>> m14b_detailList = factory.selectList(dynamicQuery);
						result.addAll(m14b_detailList);
						factory.close();
						break;
					case "M16A":
						var factory2 = QueryExecutorFactory.getQueryExecutor(fab);
						xmlPath = FilePathUtil.factoryPath(factory2.getConnectionId());
						dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_M16A_DETAIL_DAT");
						List<Map<String, Object>> m16a_detailList = factory2.selectList(dynamicQuery);
						result.addAll(m16a_detailList);
						factory2.close();
						break;
					case "M14A":
						var factory3 = QueryExecutorFactory.getQueryExecutor(fab);
						xmlPath = FilePathUtil.factoryPath(factory3.getConnectionId());
						dynamicQuery = XmlUtil.loadQuery(xmlPath , "SELECT_M14A_DETAIL_DAT");
						List<Map<String, Object>> m14a_detailList = factory3.selectList(dynamicQuery);
						result.addAll(m14a_detailList);
						factory3.close();
						break;
					default:
						continue;
				}
			}
		}catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}
	public List<Map<String, Object>> getPreStateDataLogpresso(){

		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "bridgeDetailState");
			sQuery.append(strQuery);
			result = LogpressoAPI.responseResult(sQuery.toString());

		}catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}
	public List<Map<String, Object>> getDetailDataLogpresso() {
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "bridgeDetail");
			sQuery.append(strQuery);
			result = LogpressoAPI.responseResult(sQuery.toString());

		} catch (Exception e) {
			logger.error("",e);
		}
		return result;
	}

	// countlist : 현재 값
	// 이전 데이터 평균값
	public List<Map<String, Object>> getFinalData(List<Map<String, Object>> dataList){
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		List<Map<String, Object>> finalList = new ArrayList<>();
		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "bridgeLayoutTemp");
			sQuery.append(strQuery);

			//과거 10분 데이터 평균 값
			result = LogpressoAPI.responseResult(sQuery.toString());

			finalList = calculateAverages(result,dataList);


		}catch (Exception e) {
			e.printStackTrace();
		}
		return finalList;
	}

	//10분뒤 hubroom 값 조회
	public String getHubRoomCurrValue(){
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		String resultData = "";
		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "currentHubroomValForAlarm");
			sQuery.append(strQuery);
			result = LogpressoAPI.responseResult(sQuery.toString());

			if(result.size() > 0) {
				resultData = result.get(0).get("VAL").toString();
			}else {
				resultData = "0";
			}
		}catch (Exception e) {
			e.printStackTrace();
		}
		return resultData;
	}
	public String getHubRoomPredictValue(){
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		String resultData = "";
		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "hubroomPredictValue");
			sQuery.append(strQuery);
			result = LogpressoAPI.responseResult(sQuery.toString());

			if(result.size() > 0) {
				resultData = result.get(0).get("PREDICTVAL").toString();
			}else {
				resultData = "0";
			}
		}catch (Exception e) {
			e.printStackTrace();
		}
		return resultData;
	}
	public String getvhlRunRateValue(){
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		String resultData = "";
		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "vhlRunRateSearch");
			sQuery.append(strQuery);
			result = LogpressoAPI.responseResult(sQuery.toString());

			if(result.size() > 0) {
				resultData = result.get(0).get("IDC_VAL").toString();
			}else {
				resultData = "0.0";
			}
		}catch (Exception e) {
			e.printStackTrace();
		}
		return resultData;
	}
	public String getVhlErrorCount(){
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		String resultData = "";
		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "errorVhlVal");
			sQuery.append(strQuery);
			result = LogpressoAPI.responseResult(sQuery.toString());

			if(result.size() > 0) {
				resultData = String.valueOf(result.size());
			}else {
				resultData = "0";
			}
		}catch (Exception e) {
			e.printStackTrace();
		}
		return resultData;
	}


	public List<Map<String, Object>> getAlarmTextVal(){
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "bridgeAlarmTextVal");
			sQuery.append(strQuery);
			result = LogpressoAPI.responseResult(sQuery.toString());
		}catch (Exception e) {
			e.printStackTrace();
		}
		return result;
	}
	public List<Map<String, Object>> getAlarmTextVal2(){
		StringBuilder sQuery = new StringBuilder();
		List<Map<String, Object>> result = new ArrayList<Map<String, Object>>();
		try {
			String strQuery = XmlUtil.loadQuery(FilePathUtil.LOGPRESSO_CUSTOM_QUERY, "bridgeAlarmTextVal");
			strQuery = strQuery.replace("FR_FAB_ID == \"M16\"", "FR_FAB_ID == \"M14\"");
			sQuery.append(strQuery);
			result = LogpressoAPI.responseResult(sQuery.toString());
		}catch (Exception e) {
			e.printStackTrace();
		}
		return result;
	}
	private List<Map<String, Object>> calculateAverages(List<Map<String, Object>> prevData , List<Map<String,Object>> currentData) {
		List<Map<String, Object>> finalList = new ArrayList<>();
		try {
			Map<String, Map<String, Object>> prevGroupData = prevData.stream()
					.collect(Collectors.toMap(
							row -> row.get("FR_FAB_ID") + "|"
									+ row.get("TO_FAB_ID") + "|" + row.get("EQP_ID") + "|" + row.get("EQP_TYP") + "|" +
									row.get("DET_AREA_TYP") + "|" + row.get("IDC_NM"),
							row -> row
					));

			// 현재 데이터를 순회하면서 조건에 맞는 데이터를 처리
			for (Map<String, Object> currentRow : currentData) {
				String idcNm = (String) currentRow.get("DET_IDC_NM");
				if ("CD_OHTCMD".equals(idcNm) || "CD_ZT10MININPUT".equals(idcNm)) {
					String key = currentRow.get("FROM_FAB_ID") + "|"
							+ currentRow.get("TO_FAB_ID") + "|" + currentRow.get("EQP_ID") + "|" + currentRow.get("EQP_TYP") + "|" +
							currentRow.get("DET_AREA_TYP") + "|" + currentRow.get("DET_IDC_NM");


					Map<String, Object> prevRow = prevGroupData.get(key);
					if (prevRow != null) {
						double prevAvgVal = (Double) prevRow.get("RSLT_VAL");

						double currentRsltVal = Double.parseDouble(String.valueOf(currentRow.get("RSLT_VAL")));

						double res = (((prevAvgVal*prevRow.size()) - prevAvgVal)+currentRsltVal)/prevRow.size();

						System.out.println("prevAvgVal : "+prevAvgVal);
						System.out.println("prevRow.size()  : "+prevRow.size());
						System.out.println("currentRsltVal  : "+currentRsltVal);
						System.out.println(res);
						int resultVal = Integer.parseInt(String.valueOf(Math.round((res))));
						currentRow.put("RSLT_VAL",resultVal);
					}
				}
			}
			finalList.addAll(currentData);
		}catch (Exception e) {
			e.printStackTrace();
		}
		return finalList;
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