package com.skhynix.smartatlas.queryformat;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;

import com.skhynix.smartatlas.queryformat.type.ENUM_FABLIST_GROUP;
import com.skhynix.smartatlas.queryformat.type.McslogEiVo;
import com.skhynix.smartatlas.queryformat.type.McslogMachineVo;
import com.skhynix.smartatlas.queryformat.type.McslogSecsVo;
import com.skhynix.smartatlas.queryformat.type.McslogTablesCollection;
import com.skhynix.smartatlas.queryformat.type.McslogTotalVo;

public class LogpressoMcslogQuery {
	public static String sBUILD_VER							= "1.5";	//2021. 03. 31.	X0122410
	public static int searchDelayTime						= 15000;	// 200601 hgJeon 검색 delay value 추가, millisecond단위
	
	public static char CR  										= (char) 0x0D;
	public static char LF  										= (char) 0x0A; 

	public static String sCRLF  								= "" + CR + LF;	 // "" forces conversion to string

	public static String sPipeLine 							= " | "; 
	public static String sDoubleQuotation  				= "\"";
	public static String sComma  							= ", ";
	public static String sCommaOrigin						= ",";			// 200303 hgJeon 기본 comma 추가
	public static String sEquals 								= "==";
	public static String sEqual_1							= "=";
	public static String sSpace 								= " ";
	public static String sLeftParenthesis 					= "(";
	public static String sRightParenthesis 				= ")";
	public static String sMinus 								= "-";
	public static String sUnderbar 							= "_";
	public static String sSlash 								= "/";
	public static String sAsterisk							= "*";	//170727 추가
	public static String sPlus									= "+";	//180713  추가
	public static String sEmpty								= "";		//201201 추가
	
	public static String sParallel								= " parallel=t";	//200825 paraller 옵션 추가
	public static String sOrder								= "order";	//180709 추가
	public static String sAsc									= "asc";		//180709 추가		
	public static String sALL 									= "ALL";
	public static String sACCESSMODE 					= "ACCESSMODE";
	public static String sALARMID 							= "ALARMID";
	public static String sALARMCODE 						= "ALARMCODE";
	public static String sALARMTEXT						= "ALARMTEXT";
	public static String sBANNED							= "BANNED";
	public static String sBATCHTYPE						= "BATCHTYPE";
	public static String sLEVEL 								= "LEVEL";
	//public static String sSOURCELEVEL 							= "SOURCELEVEL";
	//public static String sDESTLEVEL 							= "DESTLEVEL";
	public static String sTRANSPORTFAB 						= "TRANSPORTFAB";	// 2021. 4.13	X0122410 : TRANSPORTFAB 추가
	public static String sSOURCEFAB 							= "SOURCEFAB";		// 2021. 4.12	X0122410 : SOURCEFAB 추가
	public static String sDESTFAB								= "DESTFAB";		// 2021. 4.12	X0122410 : DESTFAB 추가
	public static String sTYPE 								= "TYPE";	
	public static String sMACHINETYPE 							= "MACHINETYPE";	// 2021.03.22	X0122410 : MACHINETYPE 추가
	public static String sSOURCEMACHINETYPE 		= "SOURCEMACHINETYPE";
	public static String sSOURCEMACHINETYPE2 		= "SOURCEMACHINETYPE2";			// 2021.03.22	X0122410 : SOURCEMACHINETYPE2 추가
	public static String sDESTTYPE 						= "DESTTYPE";
	public static String sDESTTYPE2 						= "DESTMACHINETYPE2";	// 2021.03.22	X0122410 : DESTMACHINETYPE2 추가
	public static String sINOUTTYPE 						= "INOUTTYPE";
	public static String sIDREADSTATE 					= "IDREADSTATE";
	public static String sCRANENAME 						= "CRANENAME";
	public static String sCONNECTIONSTATE 			= "CONNECTIONSTATE";
	public static String sCONTROLSTATE 				= "CONTROLSTATE";
	public static String sCURRENTMACHINENAME 		= "CURRENTMACHINENAME";
	public static String sCURRENTUNITNAME 			= "CURRENTUNITNAME";
	public static String sCOMMAND 						= "COMMAND";
	public static String sCREATEUSER 					= "CREATEUSER";
	public static String sAREANAME 						= "AREANAME";
	public static String sSOURCEAREANAME 			= "SOURCEAREANAME";
	public static String sSOURCEUNITNAME 			= "SOURCEUNITNAME";
	public static String sDESTAREANAME 				= "DESTAREANAME";
	public static String sDESTUNITNAME 				= "DESTUNITNAME";
	public static String sBAYNAME 							= "BAYNAME";
	public static String sBATCHID 							= "BATCHID";
	public static String sSOURCEBAYNAME 				= "SOURCEBAYNAME";
	public static String sDESTBAYNAME 					= "DESTBAYNAME";
	public static String sNOTDESIGNATED 				= "NOTDESIGNATED";
	public static String sMACHINENAME 					= "MACHINENAME";
	public static String sDESTMACHINENAME 			= "DESTMACHINENAME";
	public static String sSOURCEMACHINENAME 		= "SOURCEMACHINENAME";
	public static String sSTATE			 					= "STATE";
	public static String sFULLSTATE			 			= "FULLSTATE";
	public static String sSHELFNAME			 			= "SHELFNAME";
	public static String sSUBSTATE			 				= "SUBSTATE";
	public static String sSTEPID			 					= "STEPID";
	public static String sPROCESSNAME 					= "PROCESS";
	public static String sPROCESSINGSTATE 			= "PROCESSINGSTATE";
	public static String sTRANSPORTCOMMANDID 	= "TRANSPORTCOMMANDID";
	public static String sTRANSPORTAREANAME 		= "TRANSPORTAREANAME";
	public static String sTRANSPORTBAYNAME 		= "TRANSPORTBAYNAME";
	public static String sTRANSPORTTYPE 				= "TRANSPORTTYPE";
	public static String sTRANSPORTTYPE2 				= "TRANSPORTTYPE2";			// 2021.03.22	X0122410 : TRANSPORTTYPE2 추가	
	public static String sTRANSPORTMACHINENAME 	= "TRANSPORTMACHINENAME";
	public static String sTRANSPORTUNITNAME 		= "TRANSPORTUNITNAME";
	public static String sTRANSFERPORTNAME 			= "TRANSFERPORTNAME";
	public static String sTHREADNAME 					= "THREAD";
	public static String sTRANSACTIONID 				= "TRANSACTIONID";
	public static String sGTXN_ID 							= "GTXN_ID";
	public static String sTRANSPORTJOBID 				= "TRANSPORTJOBID";
	public static String sTRANSPORTUNITACCESSIBLE 	= "TRANSPORTUNITACCESSIBLE";
	public static String sTSCSTATE 					= "TSCSTATE";
	public static String sTIME_EX 					= "TIME_EX";
	public static String s_TIME 						= "_time";
	public static String s_ID 						= "_id";
	public static String sMESSAGENAME 			= "MESSAGENAME";
	public static String sMANUAL 					= "MANUAL";
	public static String sMETHOD 					= "method";
	public static String sCOMMSGNAME 			= "COMMAND";
	public static String sCRANEAVAILABLE 		= "CRANEAVAILABLE";
	public static String sOPERATIONNAME	 	= "OPERATION_NAME";
	public static String sOCCUPIED	 			= "OCCUPIED";
	public static String sPORTNAME	 			= "PORTNAME";
	public static String sCARRIER 					= "CARRIER";
	public static String sCOMMANDID 				= "COMMANDID";
	public static String sUNIT 						= "UNITNAME";
	public static String sTEXT 						= "TEXT";
	public static String sLOTID 						= "LOTID";
	public static String sREASON					= "REASON";
	public static String sVEHICLENAME 			= "VEHICLENAME";
	public static String sPRIORITY 				= "PRIORITY";
	public static String sPROCESSID 				= "PROCESSID";
	public static String sDESCRIPTION 			= "DESCRIPTION";
	public static String sFIXEDROUTE 			= "FIXEDROUTE";
	public static String sCOMPLETED 				= "COMPLETED";
	public static String sCANCELED 				= "CANCELED";
	public static String sTRANS_JOBSTART 		= "TRANS_JOBSTART";
	public static String sTRANS_JOBEND 			= "TRANS_JOBEND";
	public static String sKey 							= "key";
	public static String sXML 							= "XML";
	public static String sSECS 						= "SECSII";
	public static String sRESULTCODE				= "RESULTCODE";
	public static String sHOST						= "HOST";
	public static String sBPEL						= "BPEL";
	//FAB SITEs
	public static final String sFABSITE_IC				= "IC";
	public static final String sFABSITE_M11			= "M11";
	public static final String sFABSITE_M14			= "M14";
	public static final String sFABSITE_M15			= "M15";
	public static final String sFABSITE_WX 			= "WX";
	//MACHINE TYPE
	public static String sSTB 						= "STB";
	public static String sSTOCKER 					= "STOCKER";
	public static String sCONVEYOR 				= "CONVEYOR";
	public static String sLIFTER 					= "LIFTER";
	public static String sOHT 						= "OHT";
	public static String sPROCESS 					= "PROCESS";
	public static String sINTERAILSEMITS 			= "INTERAILSEMITS";
	public static String sRETICLE 					= "RETICLE";
	public static String sINTERLAYER 				= "INTERLAYER";
	public static String sPODZIPTOWER 				= "PODZIPTOWER";
	public static String sZIPTOWER 					= "ZIPTOWER";
	public static String _sTable 					= "_table";
	//FAB
	public static String sFAB_M11					="M11";		
	public static String sFAB_M11A					="M11A";	//2021.04.01	X0122410	FAB(SHOPNAME):M11A 추가
	public static String sFAB_M11B					="M11B";	//2021.04.01	X0122410	FAB(SHOPNAME):M11B 추가
	//public static String sFAB_M14					="M14";
	public static String sFAB_M14A					="M14A";
	public static String sFAB_M14B					="M14B";
	//public static String sFAB_M15					="M15";
	public static String sFAB_M15A					="M15A";	//2022.09.02	X0122410	FAB(SHOPNAME):M15A 추가
	public static String sFAB_M15B					="M15B";	//2022.09.02	X0122410	FAB(SHOPNAME):M15B 추가
	//public static String sFAB_M16					="M16";		//2021. 4. 6	X0122410	사용안함
	public static String sFAB_M16A					="M16A";	//2021.03.31	X0122410	FAB(SHOPNAME):M16A 추가
	public static String sFAB_M16B					="M16B";	//2022.08.30	X0122410	FAB(SHOPNAME):M16B 추가
	public static String sFAB_M16E					="M16E";	//2021.03.31	X0122410	FAB(SHOPNAME):M16E 추가
	public static String sFAB_C2					="C2";		//2021.04.01	X0122410	FAB(SHOPNAME):C2 추가
	public static String sFAB_C2F					="C2F";		//2021.04.01	X0122410	FAB(SHOPNAME):C2F 추가
	public static String sFab_ICPKT					="ICPKT";
	public static String sFab_NWT					="NWT";
	// LEVEL
	public static String sWELL 						= "WELL";	
	public static String sWARN 						= "WARN";
	public static String sERROR 					= "ERROR";
	public static String sDEBUG 					= "DEBUG";
	public static String sINFO 						= "INFO";
	public static String sFINE 						= "FINE";
	public static String sFATAL 					= "FATAL";
	public static String sTIME 						= "TIME";
	public static String sRECV 						= "RECV";
	public static String sSEND 						= "SEND";
	
	//M14 table 기준정보
	public static String sTS_DATA_M14B					= "ts_data_m14b, ts_data_view_m14b";	//180822 수정
	public static String sTS_DATA 						= "ts_data, ts_data_view_m14a";
	public static String sTS_DATA_M14A 					= "ts_data_m14a, ts_data_view_m14a";		// 201216 추가
	public static String sTS_DATA_VIEW_M14A 			= "ts_data_view_m14a"; //180822 추가
	public static String sTS_DATA_VIEW_M14B 			= "ts_data_view_m14b"; //180822 추가
	public static String sTS_TRANSPORT 					= "ts_transport";
	public static String sTS_TRANSPORT_M14A 			= "ts_transport_m14a";	// 201216 추가
	public static String sTS_TRANSPORT_M14B 			= "ts_transport_m14b";	// 2021.03.22	X0122410 : ts_transport_m14b 추가 
	public static String sTS_ALARM 						= "ts_alarm";
	public static String sTS_ALARM_M14A					= "ts_alarm_m14a";			// 201216 추가	
	public static String sTS_MATERIAL 					= "ts_material";
	public static String sTS_MATERIAL_M14A				= "ts_material_m14a";		// 201216 추가
	public static String sTS_RESOURCE 					= "ts_resource";
	public static String sTS_RESOURCE_M14A				= "ts_resource_m14a";		// 201216 추가
	public static String sTS_RESOURCE_M14B				= "ts_resource_m14b";		// 201216 추가
	public static String sTS_JOB_COMPLETED 				= "ts_job_completed";
	public static String sTS_JOB_COMPLETED_M14A			= "ts_job_completed_m14a";	// 201216 추가
	public static String sSECS_DATA						= "secs_data"; //170816 추가
	public static String sSECS_DATA_M14B				= "secs_data_m14b"; //170816 추가
	public static String sEI_DATA						= "ei_data";
	public static String sEI_DATA_M14B					= "ei_data_m14b";
	public static String sCS_DATA						= "cs_data";
	public static String sCS_DATA_M14B					= "cs_data_m14b";
	public static String sDS_DATA						= "ds_data";
	public static String sDS_DATA_M14B					= "ds_data_m14b";
	public static String sUNIT_LIST_M14					= "unit_list_m14";
	
	//M15 table 기준정보
	public static String sTS_DATA_M15 					= "ts_data_m15, ts_data_view_m15";	//= "ts_data_c2, ts_data_view_c2";	
	public static String sTS_DATA_VIEW_M15 				= "ts_data_view_m15";	//= "ts_data_c2, ts_data_view_c2"; //20190108 추가 90일 이후 수정필요 (ts_data_view_c2)
	public static String sTS_TRANSPORT_M15 				= "ts_transport_m15";		//= "ts_transport_c2";
	public static String sTS_ALARM_M15 					= "ts_alarm_m15";			//= "ts_alarm_c2";
	public static String sTS_MATERIAL_M15 				= "ts_material_m15";		//= "ts_material_c2";
	public static String sTS_RESOURCE_M15 				= "ts_resource_m15";		//= "ts_resource_c2";
	public static String sTS_JOB_COMPLETED_M15 			= "ts_job_completed_m15";		//= "ts_job_completed_c2";
	public static String sSECS_DATA_M15					= "secs_data_m15";			//= "secs_data_c2"; //170816 추가
	public static String sEI_DATA_M15					= "ei_data_m15";
	public static String sCS_DATA_M15					= "cs_data_m15";
	public static String sDS_DATA_M15					= "ds_data_m15";
	
	public static String sTS_DATA_M15B 					= "ts_data_m15b, ts_data_view_m15b";	//= "ts_data_c2, ts_data_view_c2";	
	public static String sTS_DATA_VIEW_M15B 			= "ts_data_view_m15b";	//= "ts_data_c2, ts_data_view_c2"; //20190108 추가 90일 이후 수정필요 (ts_data_view_c2)
	public static String sTS_TRANSPORT_M15B 			= "ts_transport_m15b";		//= "ts_transport_c2";
	public static String sTS_ALARM_M15B 				= "ts_alarm_m15b";			//= "ts_alarm_c2";
	public static String sTS_MATERIAL_M15B 				= "ts_material_m15b";		//= "ts_material_c2";
	public static String sTS_RESOURCE_M15B 				= "ts_resource_m15b";		//= "ts_resource_c2";
	public static String sTS_JOB_COMPLETED_M15B 		= "ts_job_completed_m15b";		//= "ts_job_completed_c2";
	public static String sSECS_DATA_M15B				= "secs_data_m15b";			//= "secs_data_c2"; //170816 추가
	public static String sEI_DATA_M15B					= "ei_data_m15b";
	public static String sCS_DATA_M15B					= "cs_data_m15b";
	public static String sDS_DATA_M15B					= "ds_data_m15b";
	public static String sUNIT_LIST_M15					= "unit_list_m15";
	
	//M11 table 기준정보
	public static String sTS_DATA_M11 					= "ts_data_m11, ts_data_view_m11";	//= "ts_data_c2, ts_data_view_c2";
	public static String sTS_DATA_M11B					= "ts_data_m11b, ts_data_view_m11b";	//= "ts_data_c2f, ts_data_view_c2f";	//170727 추가
	public static String sTS_DATA_VIEW_M11 			= "ts_data_view_m11";	//= "ts_data_c2, ts_data_view_c2"; //20190108 추가 90일 이후 수정필요 (ts_data_view_c2)
	public static String sTS_DATA_VIEW_M11B 		= "ts_data_view_m11b";	 
	public static String sTS_TRANSPORT_M11 			= "ts_transport_m11";		 
	public static String sTS_TRANSPORT_M11B 		= "ts_transport_m11b";	 
	public static String sTS_ALARM_M11 					= "ts_alarm_m11";			 
	public static String sTS_ALARM_M11B 				= "ts_alarm_m11b";			
	public static String sTS_MATERIAL_M11 			= "ts_material_m11";		 
	public static String sTS_MATERIAL_M11B 			= "ts_material_m11b";		
	public static String sTS_RESOURCE_M11 			= "ts_resource_m11";		
	public static String sTS_RESOURCE_M11B 			= "ts_resource_m11b";		
	public static String sTS_JOB_COMPLETED_M11 	= "ts_job_completed_m11";		
	public static String sTS_JOB_COMPLETED_M11B 	= "ts_job_completed_m11b";	
	public static String sSECS_DATA_M11				= "secs_data_m11";				
	public static String sSECS_DATA_M11B				= "secs_data_m11b";				
	public static String sEI_DATA_M11					= "ei_data_m11";
	public static String sEI_DATA_M11B					= "ei_data_m11b";
	public static String sCS_DATA_M11					= "cs_data_m11";
	public static String sCS_DATA_M11B					= "cs_data_m11b";
	public static String sDS_DATA_M11					= "ds_data_m11";
	public static String sDS_DATA_M11B					= "ds_data_m11b";
	public static String sUNIT_LIST_M11					= "unit_list_m11";
	
	//wuxi table 기준정보
	public static String sTS_DATA_C2 				= "ts_data_c2, ts_data_view_c2";	//= "ts_data_c2, ts_data_view_c2";
	public static String sTS_DATA_C2F				= "ts_data_c2f, ts_data_view_c2f";	//= "ts_data_c2f, ts_data_view_c2f";	//170727 추가
	public static String sTS_DATA_VIEW_C2 		= "ts_data_view_c2";	//= "ts_data_c2, ts_data_view_c2"; //20190108 추가 90일 이후 수정필요 (ts_data_view_c2)
	public static String sTS_DATA_VIEW_C2F 		= "ts_data_view_c2f";	//= "ts_data_view_c2f";
	public static String sTS_TRANSPORT_C2 		= "ts_transport_c2";		//= "ts_transport_c2";
	public static String sTS_TRANSPORT_C2F 		= "ts_transport_c2f";	//= "ts_transport_c2f";
	public static String sTS_ALARM_C2 				= "ts_alarm_c2";			//= "ts_alarm_c2";
	public static String sTS_ALARM_C2F 				= "ts_alarm_c2f";			//= "ts_alarm_c2f";
	public static String sTS_MATERIAL_C2 			= "ts_material_c2";		//= "ts_material_c2";
	public static String sTS_MATERIAL_C2F 		= "ts_material_c2f";		//= "ts_material_c2f";
	public static String sTS_RESOURCE_C2 			= "ts_resource_c2";		//= "ts_resource_c2";
	public static String sTS_RESOURCE_C2F 		= "ts_resource_c2f";		//= "ts_resource_c2f";
	public static String sTS_JOB_COMPLETED_C2 		= "ts_job_completed_c2";		//= "ts_job_completed_c2";
	public static String sTS_JOB_COMPLETED_C2F 	= "ts_job_completed_c2f";		//= "ts_job_completed_c2f";
	public static String sSECS_DATA_C2				= "secs_data_c2";			//= "secs_data_c2"; //170816 추가
	public static String sSECS_DATA_C2F				= "secs_data_c2f";			//= "secs_data_c2f";//190104 추가
	public static String sEI_DATA_C2					= "ei_data_c2";
	public static String sEI_DATA_C2F					= "ei_data_c2f";
	public static String sCS_DATA_C2					= "cs_data_c2";
	public static String sCS_DATA_C2F					= "cs_data_c2f";
	public static String sDS_DATA_C2					= "ds_data_c2";
	public static String sDS_DATA_C2F					= "ds_data_c2f";
	public static String sUNIT_LIST_C2					= "unit_list_c2";
	
	//M16 table 기준정보
	public static String sTS_DATA_M16 					= "ts_data_m16, ts_data_view_m16";	
	public static String sTS_DATA_VIEW_M16 			= "ts_data_view_m16";	
	public static String sTS_TRANSPORT_M16 			= "ts_transport_m16";		
	public static String sTS_ALARM_M16 				= "ts_alarm_m16";			
	public static String sTS_MATERIAL_M16 				= "ts_material_m16";		
	public static String sTS_RESOURCE_M16 				= "ts_resource_m16";		
	public static String sTS_JOB_COMPLETED_M16 		= "ts_job_completed_m16";		
	public static String sSECS_DATA_M16				= "secs_data_m16";			
	public static String sEI_DATA_M16					= "ei_data_m16";
	public static String sCS_DATA_M16					= "cs_data_m16";
	public static String sDS_DATA_M16					= "ds_data_m16";
		
	public static String sTS_DATA_M16B 					= "ts_data_m16b, ts_data_view_m16b";	
	public static String sTS_DATA_VIEW_M16B 			= "ts_data_view_m16b";	
	public static String sTS_TRANSPORT_M16B 			= "ts_transport_m16b";		
	public static String sTS_ALARM_M16B 				= "ts_alarm_m16b";			
	public static String sTS_MATERIAL_M16B 				= "ts_material_m16b";		
	public static String sTS_RESOURCE_M16B 				= "ts_resource_m16b";		
	public static String sTS_JOB_COMPLETED_M16B 		= "ts_job_completed_m16b";		
	public static String sSECS_DATA_M16B				= "secs_data_m16b";			
	public static String sEI_DATA_M16B					= "ei_data_m16b";
	public static String sCS_DATA_M16B					= "cs_data_m16b";
	public static String sDS_DATA_M16B					= "ds_data_m16b";
	public static String sUNIT_LIST_M16					= "unit_list_m16";
	
	//ICPKT table 기준정보
	public static String sTS_DATA_ICPKT 				= "ts_data_icpkt";	
	public static String sTS_DATA_VIEW_ICPKT 			= "ts_data_view_icpkt";	
	public static String sTS_TRANSPORT_ICPKT 			= "ts_transport_icpkt";
	public static String sTS_ALARM_ICPKT 				= "ts_alarm_icpkt";		
	public static String sTS_MATERIAL_ICPKT				= "ts_material_icpkt";
	public static String sTS_RESOURCE_ICPKT 			= "ts_resource_icpkt";
	public static String sTS_JOB_COMPLETED_ICPKT		= "ts_job_completed_icpkt";
	public static String sMASTER_ICPKT					= "master_icpkt";
	public static String sMASTER_MACHINE_LIST_ICPKT		= "master_machine_list_icpkt";
	public static String sMASTER_MACHINE_TYPEINFO_ICPKT	= "master_machine_typeinfo_icpkt";
	public static String sMASTER_UNIT_LIST_ICPKT		= "master_unit_list_icpkt";
	
	//NWT table 기준정보
	public static String sTS_DATA_NWT 					= "ts_data_nwt";	
	public static String sTS_DATA_VIEW_NWT 				= "ts_data_view_nwt";	
	public static String sTS_TRANSPORT_NWT 				= "ts_transport_nwt";
	public static String sTS_ALARM_NWT 					= "ts_alarm_nwt";		
	public static String sTS_MATERIAL_NWT				= "ts_material_nwt";
	public static String sTS_RESOURCE_NWT 				= "ts_resource_nwt";
	public static String sTS_JOB_COMPLETED_NWT			= "ts_job_completed_nwt";
	public static String sMASTER_NWT					= "master_nwt";
	public static String sMASTER_MACHINE_LIST_NWT		= "master_machine_list_nwt";
	public static String sMASTER_MACHINE_TYPEINFO_NWT	= "master_machine_typeinfo_nwt";
	public static String sMASTER_UNIT_LIST_NWT			= "master_unit_list_nwt";
	
	public static String sProc									= "proc ";						// table 
	public static String sTable									= "table ";						// table 
	public static String sTable_From 						= "table from=%s to=%s  %s ";  	// FromDateTime, ToDateTime, TableName
	public static String sFulltext_From_DATA			= "fulltext from=%s to=%s %s from ts_data";	// 사용안함
	//public static String sFulltext_From_TRAN			= "fulltext from=%s to=%s %s from ts_transport_m15";
	public static String sFulltext_From_TRAN			= "TRANS_JOB_HISTORY_FULLTEXT(%s, %s, %s)";	// 200819 hgJeon 기존쿼리 프로시저로 수정
	public static String sFulltext_Arg0						= "fulltext from=%s to=%s ";
	public static String sFulltext_Arg0_key1				= "fulltext from=%s to=%s %s ";
	public static String sSearch_0 							= " | search ";					// Search
	public static String sSearch_1 							= " | search %s == %s ";		// ColumnName == Value
	public static String sSearch_not							= " | search %s != %s";		// ColumnName != Value
	public static String sSearch_in 							= " | search in (%s ";		  // search in (ColumnName 
	public static String sFulltext								= "fulltext \"%s\" from %s";	// Fulltext Search in Table 
	public static String sFulltext0							= "fulltext ";					 
//	public static String sGetMachineQuery				= "memlookup name=machine_info";	 
	public static String sGetMachineQuery				= "memlookup name=machine_list";	// 2021. 03. 31. X0122410 대상 테이블 변경	machine_info > machine_list
	public static String sAnd									= " and ";	 
	public static String sOr										= " or ";	 
	public static String sFields								= " | fields ";	 
	public static String sFrom_Arg1							= " from %s ";	 
	public static String sFrom									= " from ";	 
	public static String sSort									= " sort ";	 
	public static String sEval									= " | eval %s = %s ";		//20180713 추가
	
/**
 *  2017-07-18일자로 아래의 3개의 내용 추가
 */
	//public static String sTable_From_TRAN			 = "table from=%s to=%s ts_transport_m15 | search (method==\"createTransportJobHistory\" or method==\"createTransportCommandHistory\")  and TRANSPORTJOBID==\"%s\"";
	public static String sTable_From_TRAN			 = "TRANS_JOB_HISTORY_DETAIL(%s, %s, %s)";					// 200818 hgJeon 기존쿼리 프로시저로 수정		
	public static String METHOD_INFO_CREATE_TRANSPORT_JOB_HISTORY = "createTransportJobHistory";		// 반송이력 세부조회
	public static String METHOD_INFO_CREATE_TRANSPORT_COMMAND_HISTORY = "createTransportCommandHistory";
	
	public static String sCOMPLETED_CARRIER_FROM_TO			= "COMPLETED_CARRIER_FROM_TO(%s, %s)";  	// 프로시저 COMPLETED_CARRIER_FROM_TO
	public static String sCOMPLETED_CARRIER_FROM_TO_CARRIER	= "COMPLETED_CARRIER_FROM_TO_CARRIER(%s, %s, %s)";  // 프로시저 COMPLETED_CARRIER_FROM_TO_CARRIER
	public static String sCARRIER_STEP_ELAPSED_TIME			= "CARRIER_STEP_ELAPSED_TIME(%s, %s, %s)";  // 프로시저 CARRIER_STEP_ELAPSED_TIME  

	public static final List<String> Levels;	// 2021. 04. 06 X0122410 Levels 리스트 추가
	private static final Map<ENUM_FABLIST_GROUP, McslogTablesCollection> _SiteFabTablesMap;
	private static final Map<String, List<String>> _SiteFabsMap;
	
	static
	{
		//sFAB_SITE = sFABSITE_IC;
		//sFAB_SITE = sFABSITE_M15;
		//sFAB_SITE = sFABSITE_M11;
		//sFAB_SITE = sFABSITE_M14;
		//sFAB_SITE = sFABSITE_C2;
		/*
		sParallel = " ";
		*/
		
		Levels = initLevelList();
		_SiteFabTablesMap = initSiteFabTablesMap();
		_SiteFabsMap = initSiteFabsMap();
	}
	
	private static List<String> initLevelList() {
		return List.of(
			sDEBUG,
			sINFO,
			sFINE,
			sWELL,
			sWARN,
			sERROR,
			sFATAL
		);
	}
	
	private static Map<ENUM_FABLIST_GROUP, McslogTablesCollection> initSiteFabTablesMap() {
		Map<ENUM_FABLIST_GROUP, McslogTablesCollection> mapSiteFabtables = new HashMap<>();
		Map<String, Map<String, String>> fabTables = new HashMap<>();
		
		fabTables = Map.of(
				sFABSITE_IC, Map.of(
					sFAB_M14A, sTS_ALARM_M14A,
					sFAB_M14B, sTS_ALARM_M14A,
					sFAB_M16A, sTS_ALARM_M16,
					sFAB_M16B, sTS_ALARM_M16B,
					sFab_ICPKT, sTS_ALARM_ICPKT
				),
				sFABSITE_M15, Map.of(
					sFAB_M15A, sTS_ALARM_M15,
					sFAB_M15B, sTS_ALARM_M15B,
					sFab_NWT, sTS_ALARM_NWT
				),
				sFABSITE_M11, Map.of(
					sFAB_M11A, sTS_ALARM_M11,
					sFAB_M11B, sTS_ALARM_M11B
				),
				sFABSITE_WX, Map.of(
					sFAB_C2, sTS_ALARM_C2,
					sFAB_C2F, sTS_ALARM_C2F
				)
			);
		mapSiteFabtables.put(ENUM_FABLIST_GROUP.ALARM, new McslogTablesCollection(fabTables));
		
		fabTables = Map.of(
			sFABSITE_IC, Map.of(
				sFAB_M14A, sTS_TRANSPORT_M14A,
				sFAB_M14B, sTS_TRANSPORT_M14A,
				sFAB_M16A, sTS_TRANSPORT_M16,
				sFAB_M16B, sTS_TRANSPORT_M16B,
				sFab_ICPKT, sTS_TRANSPORT_ICPKT
			),
			sFABSITE_M15, Map.of(
				sFAB_M15A, sTS_TRANSPORT_M15,
				sFAB_M15B, sTS_TRANSPORT_M15B,
				sFab_NWT, sTS_TRANSPORT_NWT
			),
			sFABSITE_M11, Map.of(
				sFAB_M11A, sTS_TRANSPORT_M11,
				sFAB_M11B, sTS_TRANSPORT_M11B
			),
				sFABSITE_WX, Map.of(
				sFAB_C2, sTS_TRANSPORT_C2,
				sFAB_C2F, sTS_TRANSPORT_C2F
			)
		);
		mapSiteFabtables.put(ENUM_FABLIST_GROUP.TRANSPORT, new McslogTablesCollection(fabTables));
			
		fabTables = Map.of(
			sFABSITE_IC, Map.of(
				sFAB_M14A, sTS_MATERIAL_M14A,
				sFAB_M14B, sTS_MATERIAL_M14A,
				sFAB_M16A, sTS_MATERIAL_M16,
				sFAB_M16B, sTS_MATERIAL_M16B,
				sFab_ICPKT, sTS_MATERIAL_ICPKT
			),
			sFABSITE_M15, Map.of(
				sFAB_M15A, sTS_MATERIAL_M15,
				sFAB_M15B, sTS_MATERIAL_M15B,
				sFab_NWT, sTS_MATERIAL_NWT
			),
			sFABSITE_M11, Map.of(
				sFAB_M11A, sTS_MATERIAL_M11,
				sFAB_M11B, sTS_MATERIAL_M11B
			),
				sFABSITE_WX, Map.of(
				sFAB_C2, sTS_MATERIAL_C2,
				sFAB_C2F, sTS_MATERIAL_C2F
			)
		);
		mapSiteFabtables.put(ENUM_FABLIST_GROUP.MATERIAL, new McslogTablesCollection(fabTables));
		
		fabTables = Map.of(
			sFABSITE_IC, Map.of(
				sFAB_M14A, sTS_RESOURCE_M14A,
				sFAB_M14B, sTS_RESOURCE_M14B,
				sFAB_M16A, sTS_RESOURCE_M16,
				sFAB_M16B, sTS_RESOURCE_M16B,
				sFab_ICPKT, sTS_RESOURCE_ICPKT
			),
			sFABSITE_M15, Map.of(
				sFAB_M15A, sTS_RESOURCE_M15,
				sFAB_M15B, sTS_RESOURCE_M15B,
				sFab_NWT, sTS_RESOURCE_NWT
			),
			sFABSITE_M11, Map.of(
				sFAB_M11A, sTS_RESOURCE_M11,
				sFAB_M11B, sTS_RESOURCE_M11B
			),
				sFABSITE_WX, Map.of(
				sFAB_C2, sTS_RESOURCE_C2,
				sFAB_C2F, sTS_RESOURCE_C2F
			)
		);
		mapSiteFabtables.put(ENUM_FABLIST_GROUP.RESOURCE, new McslogTablesCollection(fabTables));
		
		fabTables = Map.of(
				sFABSITE_IC, Map.of(
					sFAB_M14A, sTS_JOB_COMPLETED_M14A,
					sFAB_M14B, sTS_JOB_COMPLETED_M14A,
					sFAB_M16A, sTS_JOB_COMPLETED_M14A,
					sFAB_M16B, sTS_JOB_COMPLETED_M14A,
					sFab_ICPKT, sTS_JOB_COMPLETED_ICPKT
				),
				sFABSITE_M15, Map.of(
					sFAB_M15A, sTS_JOB_COMPLETED_M15,
					sFAB_M15B, sTS_JOB_COMPLETED_M15B,
					sFab_NWT, sTS_JOB_COMPLETED_NWT
				),
				sFABSITE_M11, Map.of(
					sFAB_M11A, sTS_JOB_COMPLETED_M11,
					sFAB_M11B, sTS_JOB_COMPLETED_M11B
				),
				sFABSITE_WX, Map.of(
					sFAB_C2, sTS_JOB_COMPLETED_C2,
					sFAB_C2F, sTS_JOB_COMPLETED_C2F
				)
			);
		mapSiteFabtables.put(ENUM_FABLIST_GROUP.JOBCOMPLETED, new McslogTablesCollection(fabTables));
		
		fabTables = Map.of(
			sFABSITE_IC, Map.of(
				sFAB_M14A, "",
				sFAB_M14B, "",
				sFAB_M16A, "",
				sFAB_M16B, "",
				sFab_ICPKT, sMASTER_MACHINE_LIST_ICPKT
			),
			sFABSITE_M15, Map.of(
				sFAB_M15A, "",
				sFAB_M15B, "",
				sFab_NWT, sMASTER_MACHINE_LIST_NWT
			),
			sFABSITE_M11, Map.of(
				sFAB_M11A, "",
				sFAB_M11B, ""
			),
				sFABSITE_WX, Map.of(
				sFAB_C2, "",
				sFAB_C2F, ""
			)
		);
		mapSiteFabtables.put(ENUM_FABLIST_GROUP.MASTER_MACHINELIST, new McslogTablesCollection(fabTables));
		
		fabTables = Map.of(
			sFABSITE_IC, Map.of(
				sFAB_M14A, sUNIT_LIST_M14,
				sFAB_M14B, sUNIT_LIST_M14,
				sFAB_M16A, sUNIT_LIST_M16,
				sFAB_M16B, sUNIT_LIST_M16,
				sFab_ICPKT, sMASTER_UNIT_LIST_ICPKT
			),
			sFABSITE_M15, Map.of(
				sFAB_M15A, sUNIT_LIST_M15,
				sFAB_M15B, sUNIT_LIST_M15,
				sFab_NWT, sMASTER_UNIT_LIST_NWT
			),
			sFABSITE_M11, Map.of(
				sFAB_M11A, sUNIT_LIST_M11,
				sFAB_M11B, sUNIT_LIST_M11
			),
				sFABSITE_WX, Map.of(
				sFAB_C2, sUNIT_LIST_C2,
				sFAB_C2F, sUNIT_LIST_C2
			)
		);
		mapSiteFabtables.put(ENUM_FABLIST_GROUP.MASTER_UNITLIST, new McslogTablesCollection(fabTables));
		
		fabTables = Map.of(
			sFABSITE_IC, Map.of(
				sFAB_M14A, "",
				sFAB_M14B, "",
				sFAB_M16A, "",
				sFAB_M16B, "",
				sFab_ICPKT, sMASTER_ICPKT
			),
			sFABSITE_M15, Map.of(
				sFAB_M15A, "",
				sFAB_M15B, "",
				sFab_NWT, sMASTER_NWT
			),
			sFABSITE_M11, Map.of(
				sFAB_M11A, "",
				sFAB_M11B, ""
			),
				sFABSITE_WX, Map.of(
				sFAB_C2, "",
				sFAB_C2F, ""
			)
		);
		mapSiteFabtables.put(ENUM_FABLIST_GROUP.MASTER, new McslogTablesCollection(fabTables));
		
		return mapSiteFabtables;
	}
	
	public static McslogTablesCollection getTablesCollection(ENUM_FABLIST_GROUP group) {
		return _SiteFabTablesMap.get(group);
	}
	
	private static Map<String, List<String>> initSiteFabsMap() {
		return Map.of(
			sFABSITE_IC, List.of(
				sFAB_M14A,
				sFAB_M14B,
				sFAB_M16A,
				sFAB_M16B
			),
			sFABSITE_M14, List.of(
				sFAB_M14A,
				sFAB_M14B
			),
			sFABSITE_M15, List.of(
				sFAB_M15A,
				sFAB_M15B
			),
			sFABSITE_M11, List.of(
				sFAB_M11A,
				sFAB_M11B
			),
				sFABSITE_WX, List.of(
				sFAB_C2,
				sFAB_C2F
			)
		);
	}
	
	public static List<String> getFabsList(String site) {
		return _SiteFabsMap.get(site);
	}
		
	public static String getColumnFromFab(String fabSite, String fab) {
		switch (fabSite) {
			case sFABSITE_M14 : {
				if (fab.equals(sFAB_M14A)) {
					return sComma + sDoubleQuotation + sFAB_M14A + sDoubleQuotation;
				} else if (fab.equals(sFAB_M14B)) {
					return sComma + sDoubleQuotation + sFAB_M14B + sDoubleQuotation;
				}
//				else if (fab.equals(sFAB_M14)) {
//					return sComma + sDoubleQuotation + sFAB_M14 + sAsterisk + sDoubleQuotation;
//				}				
			}
			case sFABSITE_M15 : {
				if (fab.equals(sFAB_M15A)) {
					return sComma + sDoubleQuotation + sFAB_M15A + sDoubleQuotation;
				} else if (fab.equals(sFAB_M15B)) {
					return sComma + sDoubleQuotation + sFAB_M15B + sDoubleQuotation;
				}
				else if (fab.equals(sFab_NWT)) {
					return sComma + sDoubleQuotation + sFab_NWT + sDoubleQuotation;
				}
//				else if (fab.equals(sFAB_M15)) {
//					return sComma + sDoubleQuotation + sFAB_M15 + sAsterisk + sDoubleQuotation;
//				}	
			}
			case sFABSITE_M11 : {
				if (fab.equals(sFAB_M11A)) {
					return sComma + sDoubleQuotation + sFAB_M11A + sDoubleQuotation;
				} else if (fab.equals(sFAB_M11B)) {
					return sComma + sDoubleQuotation + sFAB_M11B + sDoubleQuotation;
				} else if (fab.equals(sFAB_M11)) {
					return sComma + sDoubleQuotation + sFAB_M11 + sAsterisk + sDoubleQuotation;
				}
			}
			case sFABSITE_WX: {
				if (fab.equals(sFAB_C2)) {
					return sComma + sDoubleQuotation + sFAB_C2 + sDoubleQuotation;
				} else if (fab.equals(sFAB_C2F)) {
					return sComma + sDoubleQuotation + sFAB_C2F + sDoubleQuotation;
				}
			}
			case sFABSITE_IC : {				
				if (fab.equals(sFAB_M14A)) {
					return sComma + sDoubleQuotation + sFAB_M14A + sDoubleQuotation;
				} else if (fab.equals(sFAB_M14B)) {
					return sComma + sDoubleQuotation + sFAB_M14B + sDoubleQuotation;
				}
//				else if (fab.equals(sFAB_M14)) {
//					return sComma + sDoubleQuotation + sFAB_M14 + sAsterisk + sDoubleQuotation;
//				}
				else if (fab.equals(sFAB_M16A)) {
					return sComma + sDoubleQuotation + sFAB_M16A + sDoubleQuotation;
				} else if (fab.equals(sFAB_M16B)) {
					return sComma + sDoubleQuotation + sFAB_M16B + sDoubleQuotation;
				} else if (fab.equals(sFAB_M16E)) {
					return sComma + sDoubleQuotation + sFAB_M16E + sDoubleQuotation;
				}
//				else if (fab.equals(sFAB_M16)) {
//					return sComma + sDoubleQuotation + sFAB_M16 + sAsterisk + sDoubleQuotation;	
//				}
				else if (fab.equals(sFab_ICPKT)) {
					return sComma + sDoubleQuotation + sFab_ICPKT + sDoubleQuotation;
				}
			}
			default : return null;
		}
	}
	
	public static String getTSTableFromFab(String fabSite, String fab, boolean isAll) {
		switch (fabSite) {
			case sFABSITE_M14 : {
				return isAll ? "ts_data, ts_data_m14b, ts_data_view_m14a, ts_data_view_m14b"
						: "ts_data, ts_data_m14b, ts_data_view_m14a, ts_data_view_m14b";
			}
			case sFABSITE_M15 : {
				if (fab.equals(sFAB_M15A)) {
					return isAll ? sTS_DATA_M15 : sTS_DATA_VIEW_M15;
				} else if (fab.equals(sFAB_M16B)) {
					return isAll ? sTS_DATA_M16B : sTS_DATA_VIEW_M16B; 
				} else { // B 일경우 
					return isAll ? sTS_DATA_M15B : sTS_DATA_VIEW_M15B;
				}
			}
			case sFABSITE_M11 : {
				if (fab.equals(sFAB_M11A)) {
					return isAll ? sTS_DATA_M11 : sTS_DATA_VIEW_M11;
				} else { // B 일경우 
					return isAll ? sTS_DATA_M11B : sTS_DATA_VIEW_M11B;
				}
			}
			case sFABSITE_WX: {
				if (fab.equals(sFAB_C2)) {
					return isAll ? sTS_DATA_C2 : sTS_DATA_VIEW_C2;
				} else { // B 일경우 
					return isAll ? sTS_DATA_C2F : sTS_DATA_VIEW_C2F;
				}
			}
			case sFABSITE_IC : {
				if (fab.equals(sFAB_M14A)) {
					return isAll ? sTS_DATA_M14A : sTS_DATA_VIEW_M14A; 
				} else if (fab.equals(sFAB_M14B)) {
					return isAll ? sTS_DATA_M14B : sTS_DATA_VIEW_M14B; 
				} else if (fab.equals(sFAB_M16A)) {
					return isAll ? sTS_DATA_M16 : sTS_DATA_VIEW_M16; 
				} else if (fab.equals(sFAB_M16B)) {
					return isAll ? sTS_DATA_M16B : sTS_DATA_VIEW_M16B; 
				}
			}
			default : return sEmpty;
		}
	}
	
	public static String getEITableFromFab(String fabSite, String fab) {
		switch (fabSite) {
			case sFABSITE_M14 : {
				if (fab.equals(sFAB_M14A)) {
					return sEI_DATA;
				} else {
					return sEI_DATA_M14B;
				}
			}
			case sFABSITE_M15 : {
				if (fab.equals(sFAB_M15A)) {
					return sEI_DATA_M15;
				} else { // B 일경우
					return sEI_DATA_M15B;
				}
			}
			case sFABSITE_M11 : {
				if (fab.equals(sFAB_M11A)) {
					return sEI_DATA_M11;
				} else { // B 일경우
					return sEI_DATA_M11B;
				}
			}
			case sFABSITE_WX: {
				if (fab.equals(sFAB_C2)) {
					return sEI_DATA_C2;
				} else { // B 일경우
					return sEI_DATA_C2F;
				}
			}
			case sFABSITE_IC : {
				if (fab.equals(sFAB_M14A)) {
					return sEI_DATA;
				} else if (fab.equals(sFAB_M14B)) {
					return sEI_DATA_M14B;
				} else if (fab.equals(sFAB_M16A)) {
					return sEI_DATA_M16;
				} else if (fab.equals(sFAB_M16B)) {
					return sEI_DATA_M16B;
				}
			}
			default : return sEmpty;
		}
	}
	
	public static String getCSTableFromFab(String fabSite, String fab) {
		switch (fabSite) {
			case sFABSITE_M14 : {
				if (fab.equals(sFAB_M14A)) {
					return sCS_DATA;
				} else {
					return sCS_DATA_M14B;
				}
			}
			case sFABSITE_M15 : {				
				if (fab.equals(sFAB_M15A)) {
					return sCS_DATA_M15;
				} else { // B 일경우
					return sCS_DATA_M15B;
				}
			}
			case sFABSITE_M11 : {
				if (fab.equals(sFAB_M11A)) {
					return sCS_DATA_M11;
				} else { // B 일경우
					return sCS_DATA_M11B;
				}
			}
			case sFABSITE_WX: {
				if (fab.equals(sFAB_C2)) {
					return sCS_DATA_C2;
				} else { // B 일경우
					return sCS_DATA_C2F;
				}
			}
			case sFABSITE_IC : {
				if (fab.equals(sFAB_M14A)) {
					return sCS_DATA;
				} else if (fab.equals(sFAB_M14B)) {
					return sCS_DATA_M14B;
				} else if (fab.equals(sFAB_M16A)) {
					return sCS_DATA_M16;
				} else if (fab.equals(sFAB_M16B)) {
					return sCS_DATA_M16B;
				}
			}
			default : return sEmpty;
		}
	}
	
	public static String getDSTableFromFab(String fabSite, String fab) {
		
		switch (fabSite) {
			case sFABSITE_M14 : {
				if (fab.equals(sFAB_M14A)) {
					return sDS_DATA;
				} else if (fab.equals(sFAB_M14B)) {
					return sDS_DATA_M14B;
				}
			}
			case sFABSITE_M15 : {
				if (fab.equals(sFAB_M15A)) {
					return sDS_DATA_M15;
				} else { // B 일경우, M15B
					return sDS_DATA_M15B;
				}
			}
			case sFABSITE_M11 : {
				if (fab.equals(sFAB_M11A)) {
					return sDS_DATA_M11;
				} else { // B 일경우, M11B
					return sDS_DATA_M11B;
				}
			}			
			case sFABSITE_WX: {
				if (fab.equals(sFAB_C2)) {
					return sDS_DATA_C2;
				} else { // B 일경우, C2
					return sDS_DATA_C2F;
				}
			}
			case sFABSITE_IC : {
				if (fab.equals(sFAB_M14A)) {
					return sDS_DATA;
				} else if (fab.equals(sFAB_M14B)) {
					return sDS_DATA_M14B;
				} else if (fab.equals(sFAB_M16A)) {
					return sDS_DATA_M16;
				} else if (fab.equals(sFAB_M16B)) {
					return sDS_DATA_M16B;
				}
			}
			default : return sEmpty;
		}
	}

	public static String getTotalLogTableFromFab(String fabSite, String fab, boolean isAll) {
		switch (fabSite) {
			case sFABSITE_M14 : {
				if (fab.equals(sFAB_M14A)) {
					return isAll ? sTS_DATA : sTS_DATA;
				} else if (fab.equals(sFAB_M14B)) {
					return isAll ? sTS_DATA_M14B : sTS_DATA_M14B;
				}
			}
			case sFABSITE_M15 : {
				if (fab.equals(sFAB_M15A)) {
					return isAll ? sTS_DATA_M15 : sTS_DATA_VIEW_M15;
				} else if (fab.equals(sFAB_M16B)) {
					return isAll ? sTS_DATA_M16B : sTS_DATA_VIEW_M16B;
				} else if (fab.equals(sFAB_M15B)) {
					return isAll ? sTS_DATA_M15B : sTS_DATA_VIEW_M15B;
				}
			}
			case sFABSITE_M11 : {
				if (fab.equals(sFAB_M11A)) {
					return isAll ? sTS_DATA_M11 : sTS_DATA_VIEW_M11;
				}
				else if (fab.equals(sFAB_M11B)) {
					return isAll ? sTS_DATA_M11B : sTS_DATA_VIEW_M11B;
				}
			}
			case sFABSITE_WX: {
				if (fab.equals(sFAB_C2)) {
					return isAll ? sTS_DATA_C2 : sTS_DATA_VIEW_C2;
				}
				else if (fab.equals(sFAB_C2F)) {
					return isAll ? sTS_DATA_C2F : sTS_DATA_VIEW_C2F;
				}
			}
			case sFABSITE_IC : {
				if (fab.equals(sFAB_M14A)) {
					return isAll ? sTS_DATA_M14A : sTS_DATA_VIEW_M14A; 
				} else if (fab.equals(sFAB_M14B)) {
					return isAll ? sTS_DATA_M14B : sTS_DATA_VIEW_M14B; 
				} else if (fab.equals(sFAB_M16A)) { 
					return isAll ? sTS_DATA_M16 : sTS_DATA_VIEW_M16; 
				} else if (fab.equals(sFAB_M16B)) { 
					return isAll ? sTS_DATA_M16B : sTS_DATA_VIEW_M16B;
				}
			}
			default : return null;
		}
	}

	public static String getSecsLogListTableFromFab(String fabSite, String fab) {
		switch (fabSite) {
			case sFABSITE_M14 : {
				if (fab.equals(sFAB_M14A)) {
					return sSECS_DATA;
				} else if (fab.equals(sFAB_M14B)) {
					return sSECS_DATA_M14B;
				}
			}
			case sFABSITE_M15 : {
				if (fab.equals(sFAB_M15A)) {
					return sSECS_DATA_M15;
				} else if (fab.equals(sFAB_M15B)) {
					return sSECS_DATA_M15B;
				}
			}
			case sFABSITE_M11 : {
				if (fab.equals(sFAB_M11A)) {
					return sSECS_DATA_M11;
				} else if (fab.equals(sFAB_M11B)) {
					return sSECS_DATA_M11B;
				}
			}
			case sFABSITE_WX: {
				if (fab.equals(sFAB_C2)) {
					return sSECS_DATA_C2;
				} else if (fab.equals(sFAB_C2F)) {
					return sSECS_DATA_C2F;
				}
			}
			case sFABSITE_IC : {
				if (fab.equals(sFAB_M14A)) {
					return sSECS_DATA;
				} else if (fab.equals(sFAB_M14B)) {
					return sSECS_DATA_M14B;
				} else if (fab.equals(sFAB_M16A)) {
					return sSECS_DATA_M16;
				} else if (fab.equals(sFAB_M16B)) {
					return sSECS_DATA_M16B;
				}				
			}
			default : return null;
		}
	}
	
	public static String getRawLogListQueryParser(McslogEiVo eiVo) {
		if (eiVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(sTable_From, eiVo.getFrom(), eiVo.getTo(),	sOrder+ sEqual_1+sAsc + sParallel + sSpace));	// 200918 hgJeon 병렬화 옵션 적용
		
		// 190107 FAB 선택시 테이블 쿼리 변경
		if ((eiVo.getFab() != null && eiVo.getFab().size() > 0) 
			&& (eiVo.getLog() != null && eiVo.getLog().size() > 0)) {
			List<String> fab = eiVo.getFab();
			List<String> logType = eiVo.getLog();		// ts, ei, cs, ds
			List<String> tableName = null;
			LinkedHashSet<String> tableNameSet = new LinkedHashSet<String>();
						
			for (int i = 0; i<eiVo.getFab().size(); i++) {
				tableName = new ArrayList<String>();
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//tableName = eiVo.getLevel().contains(Common.sALL) || eiVo.getLevel().contains("INFO") || eiVo.getLevel().contains("FINE") || eiVo.getLevel().contains("DEBUG") ? 
				//				getTableSelect(fab.get(i), logType, true): getTableSelect(fab.get(i), logType, false); 
				tableName = eiVo.getLevel().contains(sALL) || eiVo.getLevel().contains("INFO") || eiVo.getLevel().contains("FINE") || eiVo.getLevel().contains("DEBUG") ? 
						getRawLogListTableSelect(eiVo.getFabSite(), fab.get(i), logType, true): getRawLogListTableSelect(eiVo.getFabSite(), fab.get(i), logType, false);
				// 중복제거
				tableNameSet.addAll(tableName);
			}	// end of for
			
			tableName = new ArrayList<>(tableNameSet);
			sQuery.append(String.join(", ", tableName));
		}
		// 컬럼 설정 (CLASS, FAB, LOG, HOST, TEXT_XML)
		if (eiVo.getLog() != null && eiVo.getLog().contains("TS")) {	// 200921 hgJeon TS 조건 추가
			
			sQuery.append(sCRLF + String.format(sEval, "CLASS", "OPERATION_NAME"));
			sQuery.append(sCRLF + sPipeLine 
								+ "eval FAB = case(contains(PROCESS, " + sDoubleQuotation + "m11a" + sDoubleQuotation + " ), " + sDoubleQuotation + "M11A"+ sDoubleQuotation 
								+ ", contains(PROCESS, " + sDoubleQuotation + "m11b" + sDoubleQuotation+ "), " + sDoubleQuotation + "M11B" + sDoubleQuotation
								+ ", contains(PROCESS, " + sDoubleQuotation + "m14a" + sDoubleQuotation+ "), " + sDoubleQuotation + "M14A" + sDoubleQuotation
								+ ", contains(PROCESS, " + sDoubleQuotation + "m14b" + sDoubleQuotation+ "), " + sDoubleQuotation + "M14B" + sDoubleQuotation
								+ ", contains(PROCESS, " + sDoubleQuotation + "m15b" + sDoubleQuotation+ "), " + sDoubleQuotation + "M15B" + sDoubleQuotation
								+ ", contains(PROCESS, " + sDoubleQuotation + "m15" + sDoubleQuotation+ "), " + sDoubleQuotation + "M15A" + sDoubleQuotation
								+ ", contains(PROCESS, " + sDoubleQuotation + "m16a" + sDoubleQuotation+ "), " + sDoubleQuotation + "M16A" + sDoubleQuotation
								+ ", contains(PROCESS, " + sDoubleQuotation + "m16b" + sDoubleQuotation+ "), " + sDoubleQuotation + "M16B" + sDoubleQuotation
								+ ")");
			sQuery.append(sCRLF + sPipeLine + "eval LOG = case(contains(PROCESS, " + sDoubleQuotation + "ts" 
								+ sDoubleQuotation + "), " + sDoubleQuotation + "TS"+ sDoubleQuotation+ ")");
			sQuery.append(sCRLF + sPipeLine + "eval HOST = if (contains(PROCESS, "+ sDoubleQuotation + "ts0"+ sDoubleQuotation 
								+"), "+ sDoubleQuotation + "primary" + sDoubleQuotation + ", "+ sDoubleQuotation 
								+ "secondary" + sDoubleQuotation + ")");
			sQuery.append(sCRLF + String.format(sEval, "TEXT_XML", "XML"));
		}
		
		// 200921 hgJeon fields 정렬 순서조정 ( 맨뒤 -> 앞 )
		sQuery.append(sCRLF + sFields + s_TIME + sComma + s_ID + sComma + sTIME_EX 
				+ sComma + "FAB" + sComma + "LOG" + sComma + sLEVEL
				+ sComma + "THREAD" + sComma + "CLASS" + sComma + sTEXT 
				+ sComma + "HOST" + sComma + sPROCESS + sComma + "TEXT_XML"
				);
		
		// Add Search filed Fab
		if (eiVo.getLog().contains("EI") || eiVo.getLog().contains("CS") || eiVo.getLog().contains("DS")) {
			StringBuilder sFab = new StringBuilder();
			sFab.append(sCRLF + String.format(sSearch_in, "FAB"));
			
			for (int i = 0; i<eiVo.getFab().size(); i++) {	
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//sFab.append(Common.getColumnFromFab(Common.sFAB_SITE, eiVo.getFab().get(i)));
				sFab.append(getColumnFromFab(eiVo.getFabSite(), eiVo.getFab().get(i)));
			}
			
			sFab.append(" )");
			sQuery.append(sFab.toString());
		}
		
		// 5.Add LEVEL
		if (eiVo.getLevel() != null && eiVo.getLevel().size() > 0) {
			StringBuilder sLevel = new StringBuilder();
			sLevel.append(sCRLF + String.format(sSearch_in, sLEVEL));
			/*log.info("level1:"+sLevel);*/
			for (String s : eiVo.getLevel()) {
				if (s.indexOf(sALL) >= 0) {	// level 이 ALL 일때 
					sLevel = new StringBuilder();
					break;
				} else {
					sLevel.append(sComma + sDoubleQuotation + s + sDoubleQuotation);
				}
			}

			if (sLevel != null || !(sLevel.toString().isEmpty())) {
				/*log.info("level2:"+sLevel);*/
				if (sLevel.toString().indexOf("(") >= 0) {
					sLevel.append(" )");
				} // search in ( ... )
				sQuery.append(sLevel.toString());
			}
		}
		
		// 6.Condition & Filter --> AND , OR
		// 6-1
		if (eiVo.getHost() != null && eiVo.getHost().size() > 0) {
			StringBuilder sHost = new StringBuilder();
			sHost.append(sCRLF + String.format(sSearch_in, sHOST));
			
			for (String s : eiVo.getHost()) {
				sHost.append(sComma + sDoubleQuotation + s + sDoubleQuotation);
			}

			if (sHost != null || !(sHost.toString().isEmpty())) {
				/*log.info("level2:"+sLevel);*/
				if (sHost.toString().indexOf("(") >= 0) {
					sHost.append(" )");
				} // search in ( ... )
				sQuery.append(sHost.toString());
			}
		}
		
		if (eiVo.getProcess() != null && !eiVo.getProcess().trim().equals("")) {
			// 200304 hgJeon "," 추가시 multi 검색조건 검색 가능하게	
			if (eiVo.getProcess().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] textNameArray = eiVo.getProcess().split(sCommaOrigin);
				for (int i = 0; i<textNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(
						sLeftParenthesis + sLeftParenthesis
						+ sPROCESS + sEquals
						+ sDoubleQuotation +sAsterisk + textNameArray[i].trim() +sAsterisk
						+ sDoubleQuotation + sRightParenthesis 
						);
					} else if (i == (textNameArray.length-1)) {
						tempQuery.append(
						 sOr + sLeftParenthesis
						+ sPROCESS + sEquals
						+ sDoubleQuotation +sAsterisk + textNameArray[i].trim() +sAsterisk
						+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
						);
					} else {
						tempQuery.append(
						 sOr + sLeftParenthesis
						+ sPROCESS + sEquals
						+ sDoubleQuotation +sAsterisk + textNameArray[i].trim() +sAsterisk
						+ sDoubleQuotation + sRightParenthesis
						);
					}
				}sQuery.append(sCRLF + sSearch_0 + tempQuery.toString());
			} else {
				sQuery.append(sCRLF + sSearch_0
						+ sPROCESS + sEquals
						+ sDoubleQuotation + eiVo.getProcess().trim() + sDoubleQuotation);
			}
		}

		
		// 200304 hgJeon "," 추가시 multi 검색조건 검색 가능하게
		if (eiVo.getText() != null && !eiVo.getText().trim().equals("")) {
			
			if (eiVo.getText().toString().contains(sAsterisk)) {		// 201223 hgJeon text 검색 시 * 문자 제외
				eiVo.setText(eiVo.getText().replaceAll("\\*", sEmpty));
			}
			
			if (eiVo.getText().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] textNameArray = eiVo.getText().split(sCommaOrigin);
				String condition = sOr;
				// 200305 hgJeon TEXT 검색 시 and, or 조건 검색 기능추가
				if (eiVo.getEiTextConditionCheckBox() != null && !(eiVo.getEiTextConditionCheckBox().isEmpty())) {
					condition = eiVo.getEiTextConditionCheckBox().trim().equals(sOr.trim()) ? sOr : sAnd;
				}
				
				for (int i = 0; i<textNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(
						sLeftParenthesis + sLeftParenthesis
						+ sTEXT + sEquals
						+ sDoubleQuotation +sAsterisk + textNameArray[i].trim() +sAsterisk
						+ sDoubleQuotation + sRightParenthesis 
						);
					} else if (i == (textNameArray.length-1)) {
						tempQuery.append(
						condition + sLeftParenthesis
						+ sTEXT + sEquals
						+ sDoubleQuotation +sAsterisk + textNameArray[i].trim() +sAsterisk
						+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
						);
					} else {
						tempQuery.append(
						condition + sLeftParenthesis
						+ sTEXT + sEquals
						+ sDoubleQuotation +sAsterisk + textNameArray[i].trim() +sAsterisk
						+ sDoubleQuotation + sRightParenthesis
						);
					}
				}
				sQuery.append(sCRLF + sSearch_0 + tempQuery.toString());
			} else {
				sQuery.append(sCRLF + sSearch_0
						+ sTEXT + sEquals 
						+ sDoubleQuotation +sAsterisk + eiVo.getText().trim() + sAsterisk
						+ sDoubleQuotation );
			}
		}
		
		return sQuery.toString();
	}

	public static String getAreaBayQueryParser(McslogMachineVo machineVo) {
		StringBuilder sQuery = new StringBuilder();
		String buildQuery;
		sQuery.append(sGetMachineQuery);
		
		// FAB 선택 machineVo SecsFab 사용
		if (machineVo.getSelectFab() != null && machineVo.getSelectFab().size() > 0) {
			StringBuilder sFab = new StringBuilder();
			//SHOPNAME == FAB
			sFab.append(sCRLF + String.format(sSearch_in, "SHOPNAME"));
			
			for (String s : machineVo.getSelectFab()) {
				if (s.indexOf(sALL) >= 0) {
					sFab = null;
					break;
				} else {							
					//sFab.append(getColumnFromFab(sFAB_SITE, s));
					sFab.append(getColumnFromFab(machineVo.getFabSite(), s));
				}
			}

			if (sFab != null && !(sFab.toString().isEmpty())) {
				if (sFab.toString().indexOf("(") >= 0) {
					sFab.append(" )");
				}
				sQuery.append(sFab.toString());
			}
		}
		
		if (machineVo.getAreaName() != null && !machineVo.getAreaName().equals("")) {	// Bay 호출일때
			if (machineVo.getAreaName().toUpperCase(Locale.ENGLISH).equals(sALL)) {	
				
			}
			else{
				sQuery.append(sCRLF + String.format(sSearch_1, sAREANAME, sDoubleQuotation + machineVo.getAreaName() + sDoubleQuotation));
			}
			buildQuery = " | stats count by BAYNAME | fields BAYNAME | sort BAYNAME | search len(BAYNAME) > 1";
			
		} else {	// Area 호출일때
			buildQuery = " | stats count by AREANAME | fields AREANAME | sort AREANAME | search len(AREANAME) > 1";
		}
		
		sQuery.append(sCRLF + buildQuery);
		
		return sQuery.toString();
	}

	public static String getMachineQueryParser(McslogMachineVo machineVo) {
		StringBuilder sQuery = new StringBuilder();
		sQuery.append(sGetMachineQuery);

		// FAB 선택 machineVo SecsFab 사용
		if (machineVo.getSelectFab() != null && machineVo.getSelectFab().size() > 0) {
			StringBuilder sFab = new StringBuilder();
			//SHOPNAME == FAB
			sFab.append(sCRLF + String.format(sSearch_in, "SHOPNAME"));
			
			for (String s : machineVo.getSelectFab()) {
				if (s.indexOf(sALL) >= 0) {
					sFab = null;
					break;
				} else {					
					//sFab.append(getColumnFromFab(sFAB_SITE, s));				
					sFab.append(getColumnFromFab(machineVo.getFabSite(), s));
				}
			}

			if (sFab != null && !(sFab.toString().isEmpty())) {
				if (sFab.toString().indexOf("(") >= 0) {
					sFab.append(" )");
				} // search in ( ... )
				sQuery.append(sFab.toString());
			}
		}		
		// Area Name
		if (machineVo.getAreaName() != null && !machineVo.getAreaName().equals("")) {
			if (machineVo.getAreaName().toUpperCase(Locale.ENGLISH).equals(sALL)) {
			} else {
				sQuery.append(sCRLF + String.format(sSearch_1, sAREANAME, sDoubleQuotation + machineVo.getAreaName() + sDoubleQuotation));
			}
		}

		// Bay Name
		if (machineVo.getBayName() != null && !machineVo.getBayName().equals("")) {
			if (machineVo.getBayName().toUpperCase(Locale.ENGLISH).equals(sALL)) {
			} else {
				sQuery.append(sCRLF + String.format(sSearch_1, sBAYNAME, sDoubleQuotation + machineVo.getBayName() + sDoubleQuotation));
			}
		}
		
		// sMACHINETYPE
		if (machineVo.getMachineType() != null && machineVo.getMachineType().size() > 0) {
			StringBuilder sMachine = new StringBuilder();
			//2022.06.08	X0122410 : machine_list 데이타 변경,  MACHINETYPE -> TYPE
			//sMachine.append(sCRLF + String.format(sSearch_in, sMACHINETYPE));
			sMachine.append(sCRLF + String.format(sSearch_in, sTYPE));
	
			for (String s : machineVo.getMachineType()) {
				if (s.indexOf(sALL) >= 0) {
					sMachine = null;
					break;
				} else {
					sMachine.append(sComma + sDoubleQuotation + s + sDoubleQuotation);
				}
			}
	
			if (sMachine != null && !(sMachine.toString().isEmpty())) {
				if (sMachine.toString().indexOf("(") >= 0) {
					sMachine.append(" )");
				} // search in ( ... )
				sQuery.append(sMachine.toString());
			}
		}
		
		sQuery.append(" | stats count by MACHINENAME | fields MACHINENAME | sort MACHINENAME");
		
		return sQuery.toString();
	}

	public static String getTotalLogListQueryParser(McslogTotalVo totVo) {
		if (totVo == null) {
			return null;
		} // null exception
		
		if ( ( (totVo.getProcess() == null || totVo.getProcess().equals("")) &&
				(totVo.getCarrier()==null || totVo.getCarrier().equals("")) &&
				(totVo.getThread() == null || totVo.getThread().equals("")) &&
				(totVo.getGtxnId() == null || totVo.getGtxnId().equals("")) &&
				(totVo.getTransactionId() == null || totVo.getTransactionId().equals(""))&& 
				(totVo.getMessageName() == null || totVo.getMessageName().equals(""))&& 
				(totVo.getComMsgName() == null || totVo.getComMsgName().equals(""))&& 
				(totVo.getOperationName() == null || totVo.getOperationName().equals(""))&& 
				(totVo.getCommandId() == null || totVo.getCommandId().equals(""))&&
				(totVo.getTable() == null || totVo.getTable().equals(""))&& 
				(totVo.getUnit() == null || totVo.getUnit().equals(""))&& 
				(totVo.getText() == null || totVo.getText().equals(""))&&
				(totVo.getMachineType()==null || totVo.getMachineType().size() < 1) && 
				(totVo.getMachineName()==null || totVo.getMachineName().size() < 1) ) )
		{
			
			StringBuilder tQuery= new StringBuilder();
			tQuery.append(String.format(sTable_From, totVo.getFrom(), totVo.getTo(), sOrder+ sEqual_1+sAsc+ sParallel + sSpace));
			
			// 180808 FAB 선택시 테이블 쿼리 변경
			if (totVo.getFab() != null && totVo.getFab().size() > 0) {
				List<String> fab = totVo.getFab();
				String fabName = "";
				
				for (int i = 0; i<totVo.getFab().size(); i++) {
					fabName = totVo.getLevel().contains(sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
							getTotalLogTableFromFab(totVo.getFabSite(),fab.get(i), true) : getTotalLogTableFromFab(totVo.getFabSite(),fab.get(i), false);
					if (fabName != null && !fabName.isEmpty()) {
						if (i == 0) {
							tQuery.append(fabName);
						} else if (i == (totVo.getFab().size()-1)) {
							tQuery.append(sComma + fabName);
						} else {
							tQuery.append(sComma + fabName);
						}
					}
				}
			}
			
			// 2021.03.22	X0122410 : MACHINETYPE조건 추가
			//2022.06.20	X0122410	_id 정렬조건 추가 
			tQuery.append(sCRLF
					+ sFields + s_TIME + sComma + s_ID + sComma + sTIME_EX + sComma + sMACHINENAME + sComma + sMACHINETYPE
					+ sComma + sUNIT + sComma + sCARRIER + sComma + sCOMMANDID
					+ sComma + sCOMMAND + sComma + sOPERATIONNAME + sComma
					+ sMESSAGENAME + sComma + sPROCESS + sComma + sTRANSACTIONID
					+ sComma + sTEXT + sComma + sTHREADNAME + sComma + sKey
					 + sComma + sLEVEL + sComma + sXML + sComma + sSECS 
					 + sComma + sRESULTCODE
					 + sComma + _sTable
					);
			
			tQuery.append(sCRLF
					+ String.format(sEval, sBPEL, sMESSAGENAME));
			
			// 5.Add LEVEL
			if (totVo.getLevel() != null && totVo.getLevel().size() > 0) {
				StringBuilder sLevel = new StringBuilder();
				sLevel.append(sCRLF + String.format(sSearch_in, sLEVEL));
				for (String s : totVo.getLevel()) {
					if (s.indexOf(sALL) >= 0) {	// 200414 hgJeon All 일경우 level 선택안함
						sLevel = new StringBuilder();
						break;
					} else {
						sLevel.append(sComma + sDoubleQuotation + s + sDoubleQuotation);
					}
				}

				if (sLevel != null || !(sLevel.toString().isEmpty())) {
					if (sLevel.toString().indexOf("(") >= 0) {
						sLevel.append(" )");
					} // search in ( ... )
					tQuery.append(sLevel.toString());
				}
			}
			
			SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMddHHss");
			try {
				Date fromTime = sdf.parse(totVo.getFrom());
				Date toTime = sdf.parse(totVo.getTo());
				long diff = toTime.getTime() - fromTime.getTime();
				//log.info("fromtime:"+fromTime);
				//log.info("totime:"+toTime);
				if (diff < 500001) {	//5분 이하 쿼리시 sort 적용
					//2022.06.20	X0122410	_id 정렬조건 추가 
					//tQuery.append(sPipeLine + sSort + s_TIME);
					tQuery.append(sPipeLine + sSort + s_TIME + sComma + s_ID);
				}
			} catch (Exception ignore) {}
			
			//20180625 fulltext 검색추가
			if (totVo.getFulltext() != null && !totVo.getFulltext().trim().equals("")) {
				if (totVo.getFulltext().toString().contains("\"")) {
					totVo.setFulltext(totVo.getFulltext().replaceAll("\"", "\\\\\""));
				}
				tQuery.append(sCRLF + String.format(sSearch_1, sTEXT,
						sDoubleQuotation + sAsterisk + totVo.getFulltext().trim() + sAsterisk + sDoubleQuotation));
			}
			
			return tQuery.toString();
		}	// end of table query
		
		// fulltext query
		boolean LevelIsAll = false;
		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(sFulltext_Arg0, totVo.getFrom(), totVo.getTo()));
		
		// Add LEVEL and CARRIER
		if (totVo.getLevel() != null && totVo.getLevel().size() > 0) {
			List<String> level = totVo.getLevel();
			
			if (!totVo.getLevel().contains(sALL)) {
				for (int i = 0; i<totVo.getLevel().size(); i++) {
					if (i == 0) {
						if (totVo.getLevel().size()==1) {
							sQuery.append(sLeftParenthesis+sLEVEL+sEquals
									+ sDoubleQuotation + level.get(i)
									+ sDoubleQuotation + sRightParenthesis);
						} else {
							sQuery.append(sLeftParenthesis+sLEVEL+sEquals
									+ sDoubleQuotation + level.get(i)
									+ sDoubleQuotation + sOr);
						}
					} else if (i!=totVo.getLevel().size()-1) {
						sQuery.append(sLEVEL+sEquals
						+ sDoubleQuotation + level.get(i) 
						+ sDoubleQuotation + sOr);
					} else {
						sQuery.append(sLEVEL+sEquals
						+ sDoubleQuotation + level.get(i) 
						+ sDoubleQuotation+sRightParenthesis);
					}
				}	// end of for
			} else {
				LevelIsAll = true;
			}
		}
		
		// 6.Condition & Filter --> AND , OR
		
		List<String> conditionList = new ArrayList<String>();

		//20180419 ,로 멀티조건 검색위해 수정
		if (totVo.getProcess()!= null && !totVo.getProcess().trim().equals("")) {
			if (totVo.getProcess().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] processNameArray = totVo.getProcess().split(sCommaOrigin);
				for (int i = 0; i<processNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(
								sCRLF + sLeftParenthesis + sLeftParenthesis
								+ sPROCESSNAME + sEquals
								+ sDoubleQuotation + processNameArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis 
								);
					} else if (i == (processNameArray.length-1)) {
						tempQuery.append(
								 sOr + sLeftParenthesis
								+ sPROCESSNAME + sEquals
								+ sDoubleQuotation + processNameArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
								);
					} else {
						tempQuery.append(
								 sOr + sLeftParenthesis
								+ sPROCESSNAME + sEquals
								+ sDoubleQuotation + processNameArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis
								);
					}
				}
				conditionList.add(tempQuery.toString());
			} else {
				conditionList.add(sCRLF + sLeftParenthesis 
						+ sPROCESSNAME + sEquals 
						+ sDoubleQuotation + totVo.getProcess().trim() 
						+ sDoubleQuotation + sRightParenthesis);
			}
		}
		
		// getCarrierName 
		//20180419 ,로 멀티조건 검색위해 수정
		if (totVo.getCarrier() != null && !totVo.getCarrier().trim().equals("")) {
			if (totVo.getCarrier().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] carrierNameArray = totVo.getCarrier().split(sCommaOrigin);
				for (int i = 0; i<carrierNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(
						sCRLF + sLeftParenthesis + sLeftParenthesis
						+ sCARRIER + sEquals
						+ sDoubleQuotation + carrierNameArray[i].trim()
						+ sDoubleQuotation + sRightParenthesis 
						);
					} else if (i == (carrierNameArray.length-1)) {
						tempQuery.append(
						 sOr + sLeftParenthesis
						+ sCARRIER + sEquals
						+ sDoubleQuotation + carrierNameArray[i].trim()
						+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
						);
					} else {
						tempQuery.append(
						 sOr + sLeftParenthesis
						+ sCARRIER + sEquals
						+ sDoubleQuotation + carrierNameArray[i].trim()
						+ sDoubleQuotation + sRightParenthesis
						);
					}
				}
				conditionList.add(tempQuery.toString());
			} else {
				conditionList.add(sCRLF + sLeftParenthesis
						+ sCARRIER + sEquals
						+ sDoubleQuotation + totVo.getCarrier().trim()
						+ sDoubleQuotation + sRightParenthesis);
			}
		}
		
		// getThread 170802 인덱스빌드 이후 코드 수정
		//20180419 ,로 멀티조건 검색위해 수정
		if (totVo.getThread() != null && !totVo.getThread().trim().equals("")) {
			if (totVo.getThread().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] threadNameArray = totVo.getThread().split(sCommaOrigin);
				for (int i = 0; i<threadNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(
						sCRLF + sLeftParenthesis + sLeftParenthesis
						+ sTHREADNAME + sEquals
						+ sDoubleQuotation + threadNameArray[i].trim()
						+ sDoubleQuotation + sRightParenthesis 
						);
					} else if (i == (threadNameArray.length-1)) {
						tempQuery.append(
						 sOr + sLeftParenthesis
						+ sTHREADNAME + sEquals
						+ sDoubleQuotation + threadNameArray[i].trim()
						+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
						);
					} else {
						tempQuery.append(
						 sOr + sLeftParenthesis
						+ sTHREADNAME + sEquals
						+ sDoubleQuotation + threadNameArray[i].trim()
						+ sDoubleQuotation + sRightParenthesis
						);
					}
				}
				conditionList.add(tempQuery.toString());
			} else {
				conditionList.add(sCRLF + sLeftParenthesis
						+ sTHREADNAME + sEquals 
						+ sDoubleQuotation + totVo.getThread().trim()
						+ sDoubleQuotation + sRightParenthesis);
			}
		}
		
		// getGtxnId	201023 hgJeon GTXN_ID 검색 추가
		if (totVo.getGtxnId() != null && !totVo.getGtxnId().trim().equals("")) {
			if (totVo.getGtxnId().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String [] transNameArray = totVo.getGtxnId().split(sCommaOrigin);
				for (int i = 0; i<transNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(
								sCRLF + sLeftParenthesis + sLeftParenthesis
								+ sGTXN_ID + sEquals
								+ sDoubleQuotation + transNameArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis
								);
					} else if (i ==transNameArray.length-1) {
						tempQuery.append(
								sOr + sLeftParenthesis 
								+ sGTXN_ID + sEquals
								+ sDoubleQuotation + transNameArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
								);
					} else {
						tempQuery.append(
								sOr + sLeftParenthesis 
								+ sGTXN_ID + sEquals
								+ sDoubleQuotation + transNameArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis
								);
					}
				}
				conditionList.add(tempQuery.toString());
			} else {
				conditionList.add(sCRLF + sLeftParenthesis
						+ sGTXN_ID + sEquals 
						+ sDoubleQuotation + totVo.getGtxnId().trim() 
						+ sDoubleQuotation + sRightParenthesis);
			}
		}
		
		// getTransactionId
		//20180419 ,로 멀티조건 검색위해 수정
		if (totVo.getTransactionId() != null && !totVo.getTransactionId().trim().equals("")) {
			if (totVo.getTransactionId().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String [] transNameArray = totVo.getTransactionId().split(sCommaOrigin);
				for (int i = 0; i<transNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(
								sCRLF + sLeftParenthesis + sLeftParenthesis
								+ sTRANSACTIONID + sEquals
								+ sDoubleQuotation + transNameArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis
								);
					} else if (i ==transNameArray.length-1) {
						tempQuery.append(
								sOr + sLeftParenthesis 
								+ sTRANSACTIONID + sEquals
								+ sDoubleQuotation + transNameArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
								);
					} else {
						tempQuery.append(
								sOr + sLeftParenthesis 
								+ sTRANSACTIONID + sEquals
								+ sDoubleQuotation + transNameArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis
								);
					}
				}
				conditionList.add(tempQuery.toString());
			} else {
				conditionList.add(sCRLF + sLeftParenthesis
						+ sTRANSACTIONID + sEquals 
						+ sDoubleQuotation + totVo.getTransactionId().trim() 
						+ sDoubleQuotation + sRightParenthesis);
			}
		}

		// getMessageName 170802 인덱스빌드 이후 코드 수정
		if (totVo.getMessageName() != null && !totVo.getMessageName().trim().equals("")) {
			conditionList.add(sCRLF + sLeftParenthesis
					+ sMESSAGENAME + sEquals 
					+ sDoubleQuotation + totVo.getMessageName().trim() 
					+ sDoubleQuotation + sRightParenthesis);
		}

		// getComMsgName 170802 인덱스빌드 이후 코드 수정
		if (totVo.getComMsgName() != null && !totVo.getComMsgName().trim().equals("")) {
			conditionList.add(sCRLF + sLeftParenthesis
					+ sLeftParenthesis
					+ sCOMMSGNAME + sEquals 
					+ sDoubleQuotation + totVo.getComMsgName().trim() 
					+ sDoubleQuotation + sRightParenthesis + sOr
					+ sLeftParenthesis
					+ sMESSAGENAME + sEquals 
					+ sDoubleQuotation + totVo.getComMsgName().trim() 
					+ sDoubleQuotation + sRightParenthesis
					+sRightParenthesis);
		}

		// getOperationName
		if (totVo.getOperationName() != null && !totVo.getOperationName().trim().equals("")) {
			conditionList.add(sCRLF + sLeftParenthesis
					+ sOPERATIONNAME + sEquals 
					+ sDoubleQuotation + totVo.getOperationName().trim() 
					+ sDoubleQuotation + sRightParenthesis);
		}

		// getCommandId
		//20180419 ,로 멀티조건 검색위해 수정
		if (totVo.getCommandId() != null && !totVo.getCommandId().trim().equals("")) {
			if (totVo.getCommandId().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String [] commandIdArray = totVo.getCommandId().split(sCommaOrigin);
				for (int i = 0; i<commandIdArray.length; i++) {
					if (i == 0) {
						tempQuery.append(
								sCRLF + sLeftParenthesis + sLeftParenthesis
								+ sCOMMANDID + sEquals 
								+ sDoubleQuotation + commandIdArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis
								);
					} else if (i == commandIdArray.length-1) {
						tempQuery.append(
								sOr + sLeftParenthesis
								+ sCOMMANDID + sEquals 
								+ sDoubleQuotation + commandIdArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
								);
						} else {
							tempQuery.append(
									sOr + sLeftParenthesis
									+ sCOMMANDID + sEquals 
									+ sDoubleQuotation + commandIdArray[i].trim()
									+ sDoubleQuotation + sRightParenthesis
									);
						}
				}conditionList.add(tempQuery.toString());
			} else {
				conditionList.add(sCRLF + sLeftParenthesis
						+ sCOMMANDID + sEquals 
						+ sDoubleQuotation + totVo.getCommandId().trim()
						+ sDoubleQuotation + sRightParenthesis);
			}
		}

		// getUnit 170802 인덱스빌드 이후 코드 수정
		if (totVo.getUnit() != null && !totVo.getUnit().trim().equals("")) {
			if (totVo.getUnit().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String [] unitNameArray = totVo.getUnit().split(sCommaOrigin);
				for (int i = 0; i< unitNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(sCRLF + sLeftParenthesis + sLeftParenthesis
								+ sUNIT + sEquals
								+ sDoubleQuotation + unitNameArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis
								);
					} else if (i == unitNameArray.length-1) {
						tempQuery.append(
								sOr + sLeftParenthesis
								+ sUNIT + sEquals 
								+ sDoubleQuotation + unitNameArray[i].trim()
								+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
								);
						} else {
							tempQuery.append(
									sOr + sLeftParenthesis
									+ sUNIT + sEquals 
									+ sDoubleQuotation + unitNameArray[i].trim()
									+ sDoubleQuotation + sRightParenthesis
									);
						}
				}conditionList.add(tempQuery.toString());
			} else {
				conditionList.add(sCRLF + sLeftParenthesis
						+ sUNIT + sEquals 
						+ sDoubleQuotation + totVo.getUnit().trim()
						+ sDoubleQuotation + sRightParenthesis);
			}
		}
		
		// getTable
		// ,로 멀티조건 검색위해 수정
		if (totVo.getTable() != null && !totVo.getTable().trim().equals("")) {
			if (totVo.getTable().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] tableNameArray = totVo.getTable().split(sCommaOrigin);
				for (int i = 0; i<tableNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(
						sCRLF + sLeftParenthesis + sLeftParenthesis
						+ _sTable + sEquals
						+ sDoubleQuotation + tableNameArray[i].trim()
						+ sDoubleQuotation + sRightParenthesis 
						);
					} else if (i == (tableNameArray.length-1)) {
						tempQuery.append(
						 sOr + sLeftParenthesis
						+ _sTable + sEquals
						+ sDoubleQuotation + tableNameArray[i].trim()
						+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
						);
					} else {
						tempQuery.append(
						 sOr + sLeftParenthesis
						+ _sTable + sEquals
						+ sDoubleQuotation + tableNameArray[i].trim()
						+ sDoubleQuotation + sRightParenthesis
						);
					}
				}
				conditionList.add(tempQuery.toString());
			} else {
				conditionList.add(sCRLF + sLeftParenthesis
						+ _sTable + sEquals
						+ sDoubleQuotation + totVo.getTable().trim()
						+ sDoubleQuotation + sRightParenthesis);
			}
		}

		// getText 특수문자 ", ', [, ] 추가시 사용할 코드
		if (totVo.getText() != null && !totVo.getText().trim().equals("")) {
			if (totVo.getText().toString().contains("\"")) {
				totVo.setText(totVo.getText().replaceAll("\"", "\\\\\""));
			}
			
			if (totVo.getText().toString().contains(sAsterisk)) {	// 201223 hgJeon text 검색 시 * 문자 제외
				totVo.setText(totVo.getText().replaceAll("\\*", sEmpty));
			}
			
			if (totVo.getText().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] textNameArray = totVo.getText().split(sCommaOrigin);
				for (int i = 0; i<textNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(
						sCRLF + sLeftParenthesis + sLeftParenthesis
						+ sTEXT + sEquals
						+ sDoubleQuotation + sAsterisk + textNameArray[i].trim() +sAsterisk
						+ sDoubleQuotation + sRightParenthesis 
						);
					} else if (i == (textNameArray.length-1)) {
						tempQuery.append(
						 sOr + sLeftParenthesis
						+ sTEXT + sEquals
						+ sDoubleQuotation + sAsterisk + textNameArray[i].trim() +sAsterisk
						+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
						);
					} else {
						tempQuery.append(
						 sOr + sLeftParenthesis
						+ sTEXT + sEquals
						+ sDoubleQuotation + sAsterisk + textNameArray[i].trim() +sAsterisk
						+ sDoubleQuotation + sRightParenthesis
						);
					}
				}conditionList.add(tempQuery.toString());
			} else {
				conditionList.add(sCRLF + sLeftParenthesis
						+ sTEXT + sEquals 
						+ sDoubleQuotation + sAsterisk + totVo.getText().trim() + sAsterisk
						+ sDoubleQuotation + sRightParenthesis);
			}			
		}		
		
		String searchOption = sOr;
		if (totVo.getSearchOption() != null && !(totVo.getSearchOption().equals(""))) {
			searchOption = sSpace + totVo.getSearchOption().toLowerCase(Locale.ENGLISH) + sSpace;	// 'and' or 'or'
		}
		if (!LevelIsAll) {
			if (conditionList.size()>0) {
				if (conditionList.size()==1) {
					sQuery.append(sCRLF + sAnd + sLeftParenthesis 
						+ conditionList.get(0) + sRightParenthesis);
				} else {
					for (int i = 0; i<conditionList.size(); i++) {
						if (i == 0) {
							sQuery.append(sCRLF + sAnd + sLeftParenthesis + conditionList.get(i));
						} else if (i ==conditionList.size()-1) {
							sQuery.append(searchOption + conditionList.get(i) + sRightParenthesis);
						} else {
							sQuery.append(searchOption + conditionList.get(i));
						}
					}
				}
			}
		} else {	// level 이 All 일경우
			if (conditionList.size()>0) {
				if (conditionList.size()==1) {
					sQuery.append(conditionList.get(0));
				} else {
					for (int i = 0; i<conditionList.size(); i++) {
						if (i == 0) {
							sQuery.append(conditionList.get(i));
						} else if (i ==conditionList.size()-1) {
							sQuery.append(searchOption + conditionList.get(i));
						} else {
							sQuery.append(searchOption + conditionList.get(i));
						}
					}
				}
			}
		}
				
		// sMACHINETYPE		
		StringBuilder subMachineTypeQuery = new StringBuilder();
		if (totVo.getMachineType() != null && totVo.getMachineType().size() > 0) {			
			subMachineTypeQuery.append(sCRLF + String.format(sSearch_in, sMACHINETYPE));
			for (String s : totVo.getMachineType()) {
				if (s.indexOf(sALL) >= 0) {	
					subMachineTypeQuery = new StringBuilder();
					break;
				} else {
					subMachineTypeQuery.append(sComma + sDoubleQuotation + s + sDoubleQuotation);
				}
			}

			if (subMachineTypeQuery != null || !(subMachineTypeQuery.toString().isEmpty())) {
				if (subMachineTypeQuery.toString().indexOf("(") >= 0) {
					subMachineTypeQuery.append(" )");
				}				
			}
		}
		
		// sMACHINENAME
		if (totVo.getMachineName() != null && totVo.getMachineName().size() > 0) {
			List<String> machineList = totVo.getMachineName();
			if (machineList.contains(sNOTDESIGNATED) == false)
			{
				if (!LevelIsAll) sQuery.append(sAnd);
				for (int i = 0; i<machineList.size(); i++) {
					if (i == 0) {
						sQuery.append(sLeftParenthesis +
							sMACHINENAME + sEquals +
							sDoubleQuotation + machineList.get(i)+ sDoubleQuotation);
					} else {
						sQuery.append(sOr +
							sMACHINENAME + sEquals +
							sDoubleQuotation + machineList.get(i)+ sDoubleQuotation);
					}
				}
				sQuery.append(sRightParenthesis);		
			}
		}
		
		// 180615 FAB 선택시 테이블 쿼리 변경
		if (totVo.getFab() != null && totVo.getFab().size() > 0) {
			List<String> fab = totVo.getFab();
			String fabName = "";
			
			for (int i = 0; i<totVo.getFab().size(); i++) {
				fabName = totVo.getLevel().contains(sALL) || totVo.getLevel().contains("INFO") || totVo.getLevel().contains("FINE") || totVo.getLevel().contains("DEBUG") ?
						getTotalLogTableFromFab(totVo.getFabSite(),fab.get(i), true) : getTotalLogTableFromFab(totVo.getFabSite(),fab.get(i), false);
				if (fabName != null && !fabName.isEmpty()) {
					if (i == 0) {
						sQuery.append(sFrom + fabName);
					} else if (i == (totVo.getFab().size()-1)) {
						sQuery.append(sComma + fabName);
					} else {
						sQuery.append(sComma + fabName);
					}
				}
			}
		}
		
		//2021.03.24	X0122410 : MachineType조건
		sQuery.append(subMachineTypeQuery.toString());
		
		//2022.06.20	X0122410	_id 정렬조건 추가 
		sQuery.append(
				sCRLF + sFields + s_TIME + sComma + s_ID + sComma + sTIME_EX + sComma + sMACHINENAME + sComma + sMACHINETYPE
				+ sComma + sUNIT + sComma + sCARRIER + sComma + sCOMMANDID
				+ sComma + sCOMMAND + sComma + sOPERATIONNAME + sComma
				+ sMESSAGENAME + sComma + sPROCESS + sComma + sTRANSACTIONID
				+ sComma + sTEXT + sComma + sTHREADNAME /*+ sComma + sKey*/
				 + sComma + sLEVEL + sComma + sXML + sComma + sSECS
				 + sComma + sRESULTCODE
				 + sComma + _sTable
				);
		sQuery.append(sCRLF
				+ String.format(sEval, sBPEL, sMESSAGENAME));
		
		//20180625 fulltext 검색추가
		if (totVo.getFulltext() != null && !totVo.getFulltext().trim().equals("")) {
			if (totVo.getFulltext().toString().contains("\"")) {
				totVo.setFulltext(totVo.getFulltext().replaceAll("\"", "\\\\\""));
			}
			if (totVo.getFulltext().toString().contains(sAsterisk)) {	// 201223 hgJeon text 검색 시 * 문자 제외
				totVo.setFulltext(totVo.getFulltext().replaceAll("\\*", sEmpty));
			}
			sQuery.append(sCRLF + String.format(sSearch_1, sTEXT,
					sDoubleQuotation + sAsterisk + totVo.getFulltext().trim() + sAsterisk + sDoubleQuotation));
		}
		
		//sQuery.append(sPipeLine + sSort + s_TIME);
		LevelIsAll = false;	// 200414 hgJeon boolean 초기화
		
		return sQuery.toString();
	}

	public static String getSecsLogListQueryParser(McslogSecsVo secsVo) {
		if (secsVo == null) {
			return null;
		} // null exception

		StringBuilder sQuery = new StringBuilder();
		sQuery.append(String.format(sTable_From, secsVo.getFrom(), secsVo.getTo(), sOrder+ sEqual_1+sAsc + sParallel + sSpace));	// 200918 hgJeon 병렬화 옵션 적용
		
		if (secsVo.getFab() != null && secsVo.getFab().size() > 0) {
			List<String> fab = secsVo.getFab();
			String fabName = "";
			
			for (int i = 0; i<secsVo.getFab().size(); i++) {
				//2022. 6.15. X0122410 : fab site 접근로직 변경 
				//fabName = getTableFromFab(Common.sFAB_SITE,fab.get(i));
				//2022.06.28	X0122410	: fab Site 추가
				fabName = getSecsLogListTableFromFab(secsVo.getFabSite(),fab.get(i)); 
				if (fabName != null && !fabName.isEmpty()) {
					if (i == 0) {
						sQuery.append(fabName);
					} else if (i == (secsVo.getFab().size()-1)) {
						sQuery.append(sComma + fabName);
					} else {
						sQuery.append(sComma + fabName);
					}
				}
			}
		}
		
		// 5.Add LEVEL
		if (secsVo.getLevel() != null && secsVo.getLevel().size() > 0) {
			StringBuilder sLevel = new StringBuilder();
			sLevel.append(sCRLF + String.format(sSearch_in, sLEVEL));			
			for (String s : secsVo.getLevel()) {
				if (s.indexOf(sALL) >= 0) {					
					sLevel = new StringBuilder();
					break;
				} else {
					sLevel.append(sComma + sDoubleQuotation + s + sDoubleQuotation);
				}
			}

			if (sLevel != null || !(sLevel.toString().isEmpty())) {
				if (sLevel.toString().indexOf("(") >= 0) {
					sLevel.append(" )");
				} // search in ( ... )
				sQuery.append(sLevel.toString());
			}
		}
		
		// 6.Condition & Filter --> AND , OR
		// 6-1
		if (secsVo.getSecs() != null && !secsVo.getSecs().trim().equals("")) {
			// 200304 hgJeon "," 추가시 multi 검색조건 검색 가능하게	
			if (secsVo.getSecs().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] textNameArray = secsVo.getSecs().split(sCommaOrigin);
				for (int i = 0; i<textNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(sLeftParenthesis + sLeftParenthesis
						+ sSECS + sEquals
						+ sDoubleQuotation + sAsterisk + textNameArray[i].trim() + sAsterisk
						+ sDoubleQuotation + sRightParenthesis 
						);
					} else if (i == (textNameArray.length-1)) {
						tempQuery.append(sOr + sLeftParenthesis
						+ sSECS + sEquals
						+ sDoubleQuotation + sAsterisk + textNameArray[i].trim() + sAsterisk
						+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
						);
					} else {
						tempQuery.append(sOr + sLeftParenthesis
						+ sSECS + sEquals
						+ sDoubleQuotation + sAsterisk + textNameArray[i].trim() + sAsterisk
						+ sDoubleQuotation + sRightParenthesis
						);
					}
				}sQuery.append(sCRLF + sSearch_0 + tempQuery.toString());
			} else {
				sQuery.append(sCRLF + sSearch_0
						+ sSECS + sEquals
						+ sDoubleQuotation + secsVo.getSecs().trim() 
						+ sDoubleQuotation);
			}
		}
		
		//6-2
		if (secsVo.getHost() != null && secsVo.getHost().size() > 0) {
			StringBuilder sHost = new StringBuilder();
			sHost.append(sCRLF + String.format(sSearch_in, sHOST));
			
			for (String s : secsVo.getHost()) {
				sHost.append(sComma + sDoubleQuotation + s + sDoubleQuotation);
			}

			if (sHost != null || !(sHost.toString().isEmpty())) {
				if (sHost.toString().indexOf("(") >= 0) {
					sHost.append(" )");
				} // search in ( ... )
				sQuery.append(sHost.toString());
			}
		}
		
		// 200304 hgJeon "," 추가시 multi 검색조건 검색 가능하게
		if (secsVo.getText() != null && !secsVo.getText().trim().equals("")) {
			
			if (secsVo.getText().toString().contains(sAsterisk)) {		// 201223 hgJeon text 검색 시 * 문자 제외
				secsVo.setText(secsVo.getText().replaceAll("\\*", sEmpty));
			}
			
			if (secsVo.getText().contains(sCommaOrigin)) {
				StringBuilder tempQuery = new StringBuilder();
				String[] textNameArray = secsVo.getText().split(sCommaOrigin);
				String condition = sOr;
				// 200305 hgJeon TEXT 검색 시 and, or 조건 검색 기능추가
				if (secsVo.getSecsTextConditionCheckBox() != null && !(secsVo.getSecsTextConditionCheckBox().isEmpty())) {
					condition = secsVo.getSecsTextConditionCheckBox().trim().equals(sOr.trim()) ? sOr : sAnd;
				}
				
				for (int i = 0; i<textNameArray.length; i++) {
					if (i == 0) {
						tempQuery.append(sLeftParenthesis + sLeftParenthesis
						+ sTEXT + sEquals
						+ sDoubleQuotation + sAsterisk + textNameArray[i].trim() + sAsterisk
						+ sDoubleQuotation + sRightParenthesis 
						);
					} else if (i == (textNameArray.length-1)) {
						tempQuery.append(
						condition + sLeftParenthesis
						+ sTEXT + sEquals
						+ sDoubleQuotation + sAsterisk + textNameArray[i].trim() + sAsterisk
						+ sDoubleQuotation + sRightParenthesis + sRightParenthesis
						);
					} else {
						tempQuery.append(
						condition + sLeftParenthesis
						+ sTEXT + sEquals
						+ sDoubleQuotation + sAsterisk + textNameArray[i].trim() + sAsterisk
						+ sDoubleQuotation + sRightParenthesis
						);
					}
				}
				sQuery.append(sCRLF + sSearch_0 + tempQuery.toString());
			} else {
				sQuery.append(sCRLF + sSearch_0
						+ sTEXT + sEquals 
						+ sDoubleQuotation + sAsterisk + secsVo.getText().trim() + sAsterisk
						+ sDoubleQuotation );
			}
		}
				
		sQuery.append(sCRLF + sFields + s_TIME
				+ sComma + s_ID + sComma + sTIME_EX 
				+ sComma + sSECS + sComma + sLEVEL + sComma + "S/F"
				+ sComma + "SB" + sComma + "NAME" + sComma + "DATA" 
				+ sComma + sTEXT + sComma + "SKEY" + sComma + "HOST"
				);
		
		return sQuery.toString();
	}
	
	public static List<String> getRawLogListTableSelect(String fabSite, String fab, List<String>LogTypes, boolean isAll) {
		List<String> tableName = new ArrayList<String>();
		
		for (String log : LogTypes) {		// ei, cs, ds
			switch (log) {
				case "TS" :
				{
					tableName.add(getTSTableFromFab(fabSite, fab, isAll));
				}
				break;
				case "EI" : 
				{
					tableName.add(getEITableFromFab(fabSite, fab));
				}
				break;
				case "CS" :
				{
					tableName.add(getCSTableFromFab(fabSite, fab));
				}
				break;
				case "DS" :
				{
					tableName.add(getDSTableFromFab(fabSite, fab));
				}
				break;
				default : break;
			}
		}
		return tableName;
	}

	public static String getTransactionLogFabTableList(String fabSite, String fab) {
		switch (fabSite) {
			case sFABSITE_M15 : {				
				if (fab.equals(sFAB_M15A)) {
					return "ts_end_data_m15";
				} else if (fab.equals(sFAB_M15B)) {
					return "ts_end_data_m15b";
				}
			}
			case sFABSITE_M11 : {
				if (fab.equals(sFAB_M11A)) {
					return "ts_end_data_m11a";
				} else if (fab.equals(sFAB_M11B)) {
					return "ts_end_data_m11b";
				}
			}
			case sFABSITE_WX: {
				if (fab.equals(sFAB_C2)) {
					return "ts_end_data_c2";
				} else if (fab.equals(sFAB_C2F)) {
					return "ts_end_data_c2f";
				}
			}
			case sFABSITE_IC : {
				if (fab.equals(sFAB_M14A)) {
					return "ts_end_data_m14a"; 
				} else if (fab.equals(sFAB_M14B)) {
					return "ts_end_data_m14b";
				} else if (fab.equals(sFAB_M16A)) { 
					return "ts_end_data_m16"; 
				} else if (fab.equals(sFAB_M16B)) { 	//2022.08.30  X0122410 M16B 추가
					return "ts_end_data_m16b"; 
				}				
			}
			default : return null;
		}
	}
}
