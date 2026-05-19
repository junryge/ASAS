//package com.skhynix.supply.common;
//
//import java.io.File;
//import java.io.FileInputStream;
//import java.io.InputStream;
//import java.util.Enumeration;
//import java.util.Properties;
//import java.util.ArrayList;
//import java.util.List;
//import java.util.Locale;
//
//import org.springframework.context.i18n.LocaleContextHolder;
//
//public class McslogCommon {
//
////	public static String sFAB_SITE							="IC";	// M15 or M11 or M14 or C2 or IC
//	public static String sFAB_SITE							= null;	// M15 or M11 or M14 or C2 or IC	
//	public static String sBUILD_VER							= "1.5";	//2021. 03. 31.	X0122410
//	public static int searchDelayTime						= 15000;	// 200601 hgJeon 검색 delay value 추가, millisecond단위
//	
//	public  static char CR  										= (char) 0x0D;
//	public  static char LF  										= (char) 0x0A; 
//
//	public  static String sCRLF  								= "" + CR + LF;     // "" forces conversion to string
//
//	public  static String sPipeLine 		    				= " | "; 
//	public  static String sDoubleQuotation  		    	= "\"";
//	public  static String sComma  					    	= ", ";
//	public  static String sCommaOrigin						= ",";			// 200303 hgJeon 기본 comma 추가
//	public  static String sEquals 								= "==";
//	public  static String sEqual_1							= "=";
//	public  static String sSpace 								= " ";
//	public  static String sLeftParenthesis 					= "(";
//	public  static String sRightParenthesis 				= ")";
//	public  static String sMinus 								= "-";
//	public  static String sUnderbar 							= "_";
//	public  static String sSlash 								= "/";
//	public  static String sAsterisk							= "*";	//170727 추가
//	public  static String sPlus									= "+";	//180713  추가
//	public  static String sEmpty								= "";		//201201 추가
//	
//	public  static String sParallel								= " parallel=t";	//200825 paraller 옵션 추가
//	public  static String sOrder								= "order";	//180709 추가
//	public  static String sAsc									= "asc";		//180709 추가		
//	public  static String sALL 									= "ALL";
//	public  static String sACCESSMODE 					= "ACCESSMODE";
//	public  static String sALARMID 							= "ALARMID";
//	public  static String sALARMCODE 						= "ALARMCODE";
//	public  static String sALARMTEXT						= "ALARMTEXT";
//	public  static String sBANNED							= "BANNED";
//	public  static String sBATCHTYPE						= "BATCHTYPE";
//	public  static String sLEVEL 								= "LEVEL";
//	//public  static String sSOURCELEVEL 							= "SOURCELEVEL";
//	//public  static String sDESTLEVEL 							= "DESTLEVEL";
//	public  static String sTRANSPORTFAB 						= "TRANSPORTFAB";	// 2021. 4.13	X0122410 : TRANSPORTFAB 추가
//	public  static String sSOURCEFAB 							= "SOURCEFAB";		// 2021. 4.12	X0122410 : SOURCEFAB 추가
//	public  static String sDESTFAB								= "DESTFAB";		// 2021. 4.12	X0122410 : DESTFAB 추가
//	public  static String sTYPE 								= "TYPE";	
//	public  static String sMACHINETYPE 							= "MACHINETYPE";	// 2021.03.22	X0122410 : MACHINETYPE 추가
//	public  static String sSOURCEMACHINETYPE 		= "SOURCEMACHINETYPE";
//	public  static String sSOURCEMACHINETYPE2 		= "SOURCEMACHINETYPE2";			// 2021.03.22	X0122410 : SOURCEMACHINETYPE2 추가
//	public  static String sDESTTYPE 						= "DESTTYPE";
//	public  static String sDESTTYPE2 						= "DESTMACHINETYPE2";	// 2021.03.22	X0122410 : DESTMACHINETYPE2 추가
//	public  static String sINOUTTYPE 						= "INOUTTYPE";
//	public  static String sIDREADSTATE 					= "IDREADSTATE";
//	public  static String sCRANENAME 						= "CRANENAME";
//	public  static String sCONNECTIONSTATE 			= "CONNECTIONSTATE";
//	public  static String sCONTROLSTATE 				= "CONTROLSTATE";
//	public  static String sCURRENTMACHINENAME 		= "CURRENTMACHINENAME";
//	public  static String sCURRENTUNITNAME 			= "CURRENTUNITNAME";
//	public  static String sCOMMAND 						= "COMMAND";
//	public  static String sCREATEUSER 					= "CREATEUSER";
//	public  static String sAREANAME 	        	    	= "AREANAME";
//	public  static String sSOURCEAREANAME 	        = "SOURCEAREANAME";
//	public  static String sSOURCEUNITNAME 	        = "SOURCEUNITNAME";
//	public  static String sDESTAREANAME 	        	= "DESTAREANAME";
//	public  static String sDESTUNITNAME 	        	= "DESTUNITNAME";
//	public  static String sBAYNAME 							= "BAYNAME";
//	public  static String sBATCHID 							= "BATCHID";
//	public  static String sSOURCEBAYNAME 				= "SOURCEBAYNAME";
//	public  static String sDESTBAYNAME 					= "DESTBAYNAME";
//	public  static String sNOTDESIGNATED 		        = "NOTDESIGNATED";
//	public  static String sMACHINENAME 			    	= "MACHINENAME";
//	public  static String sDESTMACHINENAME 			= "DESTMACHINENAME";
//	public  static String sSOURCEMACHINENAME 		= "SOURCEMACHINENAME";
//	public  static String sSTATE			 					= "STATE";
//	public  static String sFULLSTATE			 			= "FULLSTATE";
//	public  static String sSHELFNAME			 			= "SHELFNAME";
//	public  static String sSUBSTATE			 				= "SUBSTATE";
//	public  static String sSTEPID			 					= "STEPID";
//	public  static String sPROCESSNAME 			    	= "PROCESS";
//	public  static String sPROCESSINGSTATE 			= "PROCESSINGSTATE";
//	public  static String sTRANSPORTCOMMANDID 	= "TRANSPORTCOMMANDID";
//	public  static String sTRANSPORTAREANAME 		= "TRANSPORTAREANAME";
//	public  static String sTRANSPORTBAYNAME 		= "TRANSPORTBAYNAME";
//	public  static String sTRANSPORTTYPE 				= "TRANSPORTTYPE";
//	public  static String sTRANSPORTTYPE2 				= "TRANSPORTTYPE2";			// 2021.03.22	X0122410 : TRANSPORTTYPE2 추가	
//	public  static String sTRANSPORTMACHINENAME 	= "TRANSPORTMACHINENAME";
//	public  static String sTRANSPORTUNITNAME 		= "TRANSPORTUNITNAME";
//	public  static String sTRANSFERPORTNAME 			= "TRANSFERPORTNAME";
//	public  static String sTHREADNAME 			        = "THREAD";
//	public  static String sTRANSACTIONID 		        = "TRANSACTIONID";
//	public  static String sGTXN_ID 		        			= "GTXN_ID";
//	public  static String sTRANSPORTJOBID 		        = "TRANSPORTJOBID";
//	public  static String sTRANSPORTUNITACCESSIBLE 	= "TRANSPORTUNITACCESSIBLE";
//	public  static String sTSCSTATE 		        	= "TSCSTATE";
//	public  static String sTIME_EX 		        	= "TIME_EX";
//	public  static String s_TIME 		        		= "_time";
//	public  static String sMESSAGENAME 			= "MESSAGENAME";
//	public  static String sMANUAL 			    	= "MANUAL";
//	public  static String sMETHOD 			    	= "method";
//	public  static String sCOMMSGNAME 			= "COMMAND";
//	public  static String sCRANEAVAILABLE 		= "CRANEAVAILABLE";
//	public  static String sOPERATIONNAME     	= "OPERATION_NAME";
//	public  static String sOCCUPIED     	        = "OCCUPIED";
//	public  static String sPORTNAME     	       	= "PORTNAME";
//	public  static String sCARRIER 					= "CARRIER";
//	public  static String sCOMMANDID 			    = "COMMANDID";
//	public  static String sUNIT 						= "UNITNAME";
//	public  static String sTEXT 						= "TEXT";
//	public  static String sLOTID 						= "LOTID";
//	public  static String sREASON                    = "REASON";
//	public  static String sVEHICLENAME 			= "VEHICLENAME";
//	public  static String sPRIORITY 				= "PRIORITY";
//	public  static String sPROCESSID 				= "PROCESSID";
//	public  static String sDESCRIPTION 			= "DESCRIPTION";
//	public  static String sFIXEDROUTE 			= "FIXEDROUTE";
//	public  static String sCOMPLETED 				= "COMPLETED";
//	public  static String sCANCELED 				= "CANCELED";
//	public  static String sTRANS_JOBSTART 		= "TRANS_JOBSTART";
//	public  static String sTRANS_JOBEND 			= "TRANS_JOBEND";
//	public  static String sKey 							= "key";
//	public  static String sXML 							= "XML";
//	public  static String sSECS 						= "SECSII";
//	public  static String sRESULTCODE				= "RESULTCODE";
//	public  static String sHOST						= "HOST"; 
//	//FAB SITEs
//	public static final String sFABSITE_IC			= "IC";
//	public static final String sFABSITE_M11			= "M11";
//	public static final String sFABSITE_M14			= "M14";
//	public static final String sFABSITE_M15			= "M15";
//	public static final String sFABSITE_C2			= "C2";
//	//MACHINE TYPE
//	public  static String sSTB 						= "STB";
//	public  static String sSTOCKER 					= "STOCKER";
//	public  static String sCONVEYOR 				= "CONVEYOR";
//	public  static String sLIFTER 					= "LIFTER";
//	public  static String sOHT 						= "OHT";
//	public  static String sPROCESS 					= "PROCESS";
//	public  static String sINTERAILSEMITS 			= "INTERAILSEMITS";
//	public  static String sRETICLE 					= "RETICLE";
//	public  static String sINTERLAYER 				= "INTERLAYER";
//	public  static String sPODZIPTOWER 				= "PODZIPTOWER";
//	public  static String sZIPTOWER 				= "ZIPTOWER";
//	//FAB
//	public  static String sFAB_M11					="M11";		
//	public  static String sFAB_M11A					="M11A";	//2021.04.01	X0122410	FAB(SHOPNAME):M11A 추가
//	public  static String sFAB_M11B					="M11B";	//2021.04.01	X0122410	FAB(SHOPNAME):M11B 추가
//	public  static String sFAB_M14					="M14";
//	public  static String sFAB_M14A					="M14A";
//	public  static String sFAB_M14B					="M14B";
//	public  static String sFAB_M15					="M15";
//	public  static String sFAB_M16					="M16";		//2021. 4. 6	X0122410	사용안함
//	public  static String sFAB_M16A					="M16A";	//2021.03.31	X0122410	FAB(SHOPNAME):M16A 추가
//	public  static String sFAB_M16E					="M16E";	//2021.03.31	X0122410	FAB(SHOPNAME):M16E 추가
//	public  static String sFAB_C2					="C2";		//2021.04.01	X0122410	FAB(SHOPNAME):C2 추가
//	public  static String sFAB_C2F					="C2F";		//2021.04.01	X0122410	FAB(SHOPNAME):C2F 추가
//	// LEVEL
//	public  static String sWELL 						= "WELL";	
//	public  static String sWARN 						= "WARN";
//	public  static String sERROR 						= "ERROR";
//	public  static String sDEBUG 						= "DEBUG";
//	public  static String sINFO 						= "INFO";
//	public  static String sFINE 						= "FINE";
//	public  static String sFATAL 						= "FATAL";
//	public  static String sTIME 						= "TIME";
//	public  static String sRECV 						= "RECV";
//	public  static String sSEND 						= "SEND";
//	
//	//M14 table 기준정보
//	public static String sTS_DATA_M14B					= "ts_data_m14b, ts_data_view_m14b";	//180822 수정
//	public static String sTS_DATA 						= "ts_data, ts_data_view_m14a";
//	public static String sTS_DATA_M14A 					= "ts_data_m14a, ts_data_view_m14a";		   // 201216 추가
//	public static String sTS_DATA_VIEW_M14A 			= "ts_data_view_m14a"; //180822 추가
//	public static String sTS_DATA_VIEW_M14B 			= "ts_data_view_m14b"; //180822 추가
//	public static String sTS_TRANSPORT 					= "ts_transport";
//	public static String sTS_TRANSPORT_M14A 			= "ts_transport_m14a";	// 201216 추가
//	public static String sTS_TRANSPORT_M14B 			= "ts_transport_m14b";	// 2021.03.22	X0122410 : ts_transport_m14b 추가 
//	public static String sTS_ALARM 						= "ts_alarm";
//	public static String sTS_ALARM_M14A					= "ts_alarm_m14a";			// 201216 추가	
//	public static String sTS_MATERIAL 					= "ts_material";
//	public static String sTS_MATERIAL_M14A				= "ts_material_m14a";		// 201216 추가
//	public static String sTS_RESOURCE 					= "ts_resource";
//	public static String sTS_RESOURCE_M14A				= "ts_resource_m14a";		// 201216 추가
//	public static String sTS_JOB_COMPLETED 				= "ts_job_completed";
//	public static String sTS_JOB_COMPLETED_M14A			= "ts_job_completed_m14a";	// 201216 추가
//	public static String sSECS_DATA						= "secs_data"; //170816 추가
//	public static String sSECS_DATA_M14B				= "secs_data_m14b"; //170816 추가
//	public static String sEI_DATA						= "ei_data";
//	//public static String sEI_DATA_M14B				= "ei_data_m14b";
//	public static String sCS_DATA						= "cs_data";
//	//public static String sCS_DATA_M14B				= "cs_data_m14b";
//	public static String sDS_DATA						= "ds_data";
//	//public static String sDS_DATA_M14B				= "ds_data_m14b";
//	
//	//M15 table 기준정보
//	public  static String sTS_DATA_M15 					= "ts_data_m15, ts_data_view_m15";	//= "ts_data_c2, ts_data_view_c2";
//	public  static String sTS_DATA_VIEW_M15 			= "ts_data_view_m15";	//= "ts_data_c2, ts_data_view_c2"; //20190108 추가 90일 이후 수정필요 (ts_data_view_c2)
//	public  static String sTS_TRANSPORT_M15 			= "ts_transport_m15";		//= "ts_transport_c2";
//	public  static String sTS_ALARM_M15 					= "ts_alarm_m15";			//= "ts_alarm_c2";
//	public  static String sTS_MATERIAL_M15 			= "ts_material_m15";		//= "ts_material_c2";
//	public  static String sTS_RESOURCE_M15 			= "ts_resource_m15";		//= "ts_resource_c2";
//	public  static String sTS_JOB_COMPLETED_M15 	= "ts_job_completed_m15";		//= "ts_job_completed_c2";
//	public  static String sSECS_DATA_M15				= "secs_data_m15";			//= "secs_data_c2"; //170816 추가
//	public static String sEI_DATA_M15					= "ei_data_m15";
//	public static String sCS_DATA_M15					= "cs_data_m15";
//	public static String sDS_DATA_M15					= "ds_data_m15";
//	
//	//M11 table 기준정보
//	public  static String sTS_DATA_M11 					= "ts_data_m11, ts_data_view_m11";	//= "ts_data_c2, ts_data_view_c2";
//	public  static String sTS_DATA_M11B					= "ts_data_m11b, ts_data_view_m11b";	//= "ts_data_c2f, ts_data_view_c2f";	//170727 추가
//	public  static String sTS_DATA_VIEW_M11 			= "ts_data_view_m11";	//= "ts_data_c2, ts_data_view_c2"; //20190108 추가 90일 이후 수정필요 (ts_data_view_c2)
//	public  static String sTS_DATA_VIEW_M11B 		= "ts_data_view_m11b";	 
//	public  static String sTS_TRANSPORT_M11 			= "ts_transport_m11";		 
//	public  static String sTS_TRANSPORT_M11B 		= "ts_transport_m11b";	 
//	public  static String sTS_ALARM_M11 					= "ts_alarm_m11";			 
//	public  static String sTS_ALARM_M11B 				= "ts_alarm_m11b";			
//	public  static String sTS_MATERIAL_M11 			= "ts_material_m11";		 
//	public  static String sTS_MATERIAL_M11B 			= "ts_material_m11b";		
//	public  static String sTS_RESOURCE_M11 			= "ts_resource_m11";		
//	public  static String sTS_RESOURCE_M11B 			= "ts_resource_m11b";		
//	public  static String sTS_JOB_COMPLETED_M11 	= "ts_job_completed_m11";		
//	public  static String sTS_JOB_COMPLETED_M11B 	= "ts_job_completed_m11b";	
//	public  static String sSECS_DATA_M11				= "secs_data_m11";				
//	public  static String sSECS_DATA_M11B				= "secs_data_m11b";				
//	public static String sEI_DATA_M11					= "ei_data_m11";
//	public static String sEI_DATA_M11B					= "ei_data_m11b";
//	public static String sCS_DATA_M11					= "cs_data_m11";
//	public static String sCS_DATA_M11B					= "cs_data_m11b";
//	public static String sDS_DATA_M11					= "ds_data_m11";
//	public static String sDS_DATA_M11B					= "ds_data_m11b";
//	
//	//wuxi table 기준정보
//	public  static String sTS_DATA_C2 				= "ts_data_c2, ts_data_view_c2";	//= "ts_data_c2, ts_data_view_c2";
//	public  static String sTS_DATA_C2F				= "ts_data_c2f, ts_data_view_c2f";	//= "ts_data_c2f, ts_data_view_c2f";	//170727 추가
//	public  static String sTS_DATA_VIEW_C2 		= "ts_data_view_c2";	//= "ts_data_c2, ts_data_view_c2"; //20190108 추가 90일 이후 수정필요 (ts_data_view_c2)
//	public  static String sTS_DATA_VIEW_C2F 		= "ts_data_view_c2f";	//= "ts_data_view_c2f";
//	public  static String sTS_TRANSPORT_C2 		= "ts_transport_c2";		//= "ts_transport_c2";
//	public  static String sTS_TRANSPORT_C2F 		= "ts_transport_c2f";	//= "ts_transport_c2f";
//	public  static String sTS_ALARM_C2 				= "ts_alarm_c2";			//= "ts_alarm_c2";
//	public  static String sTS_ALARM_C2F 				= "ts_alarm_c2f";			//= "ts_alarm_c2f";
//	public  static String sTS_MATERIAL_C2 			= "ts_material_c2";		//= "ts_material_c2";
//	public  static String sTS_MATERIAL_C2F 		= "ts_material_c2f";		//= "ts_material_c2f";
//	public  static String sTS_RESOURCE_C2 			= "ts_resource_c2";		//= "ts_resource_c2";
//	public  static String sTS_RESOURCE_C2F 		= "ts_resource_c2f";		//= "ts_resource_c2f";
//	public  static String sTS_JOB_COMPLETED_C2 		= "ts_job_completed_c2";		//= "ts_job_completed_c2";
//	public  static String sTS_JOB_COMPLETED_C2F 	= "ts_job_completed_c2f";		//= "ts_job_completed_c2f";
//	public  static String sSECS_DATA_C2				= "secs_data_c2";			//= "secs_data_c2"; //170816 추가
//	public  static String sSECS_DATA_C2F				= "secs_data_c2f";			//= "secs_data_c2f";//190104 추가
//	public static String sEI_DATA_C2					= "ei_data_c2";
//	public static String sEI_DATA_C2F					= "ei_data_c2f";
//	public static String sCS_DATA_C2					= "cs_data_c2";
//	public static String sCS_DATA_C2F					= "cs_data_c2f";
//	public static String sDS_DATA_C2					= "ds_data_c2";
//	public static String sDS_DATA_C2F					= "ds_data_c2f";
//	
//	//M16 table 기준정보
//	public  static String sTS_DATA_M16 					= "ts_data_m16, ts_data_view_m16";	
//	public  static String sTS_DATA_VIEW_M16 			= "ts_data_view_m16";	
//	public  static String sTS_TRANSPORT_M16 			= "ts_transport_m16";		
//	public  static String sTS_ALARM_M16 				= "ts_alarm_m16";			
//	public  static String sTS_MATERIAL_M16 				= "ts_material_m16";		
//	public  static String sTS_RESOURCE_M16 				= "ts_resource_m16";		
//	public  static String sTS_JOB_COMPLETED_M16 		= "ts_job_completed_m16";		
//	public  static String sSECS_DATA_M16				= "secs_data_m16";			
//	public static String sEI_DATA_M16					= "ei_data_m16";
//	public static String sCS_DATA_M16					= "cs_data_m16";
//	public static String sDS_DATA_M16					= "ds_data_m16";
//	
//	public static String sProc									= "proc ";    					// table 
//	public static String sTable									= "table ";    					// table 
//	public static String sTable_From 				    	= "table from=%s to=%s  %s ";  	// FromDateTime, ToDateTime, TableName
//	public static String sFulltext_From_DATA			= "fulltext from=%s to=%s %s from ts_data";	// 사용안함
//	//public static String sFulltext_From_TRAN			= "fulltext from=%s to=%s %s from ts_transport_m15";
//	public static String sFulltext_From_TRAN			= "TRANS_JOB_HISTORY_FULLTEXT(%s, %s, %s)";	// 200819 hgJeon 기존쿼리 프로시저로 수정
//	public static String sFulltext_Arg0						= "fulltext from=%s to=%s ";
//	public static String sFulltext_Arg0_key1				= "fulltext from=%s to=%s %s ";
//	public static String sSearch_0 							= " | search ";        			// Search
//	public static String sSearch_1 							= " | search %s == %s ";        // ColumnName == Value
//	public static String sSearch_not							= " | search %s != %s";		// ColumnName != Value
//	public  static String sSearch_in 							= " | search in (%s ";          // search in (ColumnName 
//	public static String sFulltext								= "fulltext \"%s\" from %s";    // Fulltext Search in Table 
//	public static String sFulltext0							= "fulltext ";    				 
////	public static String sGetMachineQuery				= "memlookup name=machine_info";     
//	public static String sGetMachineQuery				= "memlookup name=machine_list";	// 2021. 03. 31. X0122410 대상 테이블 변경	machine_info > machine_list
//	public static String sAnd									= " and ";     
//	public static String sOr										= " or ";     
//	public static String sFields								= " | fields ";     
//	public static String sFrom_Arg1							= " from %s ";     
//	public static String sFrom									= " from ";     
//	public static String sSort									= " sort ";     
//	public static String sEval									= " | eval %s = %s ";		//20180713 추가
//	
///**
// *  2017-07-18일자로 아래의 3개의 내용 추가
// */
//	//public static String sTable_From_TRAN             = "table from=%s to=%s ts_transport_m15 | search (method==\"createTransportJobHistory\" or method==\"createTransportCommandHistory\")  and TRANSPORTJOBID==\"%s\"";
//	public static String sTable_From_TRAN             = "TRANS_JOB_HISTORY_DETAIL(%s, %s, %s)";					// 200818 hgJeon 기존쿼리 프로시저로 수정		
//	public static String METHOD_INFO_CREATE_TRANSPORT_JOB_HISTORY = "createTransportJobHistory";           // 반송이력 세부조회
//	public static String METHOD_INFO_CREATE_TRANSPORT_COMMAND_HISTORY = "createTransportCommandHistory";
//	
//	public static String sCOMPLETED_CARRIER_FROM_TO			= "COMPLETED_CARRIER_FROM_TO(%s, %s)";  	// 프로시저 COMPLETED_CARRIER_FROM_TO   
//	public static String sCOMPLETED_CARRIER_FROM_TO_CARRIER	= "COMPLETED_CARRIER_FROM_TO_CARRIER(%s, %s, %s)";  // 프로시저 COMPLETED_CARRIER_FROM_TO_CARRIER   
//	public static String sCARRIER_STEP_ELAPSED_TIME			= "CARRIER_STEP_ELAPSED_TIME(%s, %s, %s)";  // 프로시저 CARRIER_STEP_ELAPSED_TIME  
//
//	public static List<String> Levels = null;	// 2021. 04. 06 X0122410 Levels 리스트 추가
//	
//	static
//	{
//		// 2021. 04. 05, X0122410 : FAB SITE서정
//		//sFAB_SITE = sFABSITE_IC;
//		//sFAB_SITE = sFABSITE_M15;
//		sFAB_SITE = sFABSITE_M11;
//		//sFAB_SITE = sFABSITE_M14;
//		/*
//		sFAB_SITE = sFABSITE_C2;
//		sParallel = " ";
//		*/
//		
//		// 2021. 4. 6, X0122410 : level 리스트 생성
//		Levels = getLevelList();
//	}
//	
//	static List<String> getLevelList(){
//		List<String> list = new ArrayList<String>();
//		list.add(sDEBUG);
//		list.add(sINFO);
//		list.add(sFINE);
//		list.add(sWELL);
//		list.add(sWARN);
//		list.add(sERROR);
//		list.add(sFATAL);
//		return list;
//	}
//	
//	public static List<String> getFabList(String menu, String fabSite){
//		List<String> list = new ArrayList<String>();		
//		if(menu.equals("tot") || menu.equals("tran"))
//		{
//			switch(fabSite) {
//				case sFABSITE_M14 : {
//					list.add(sFAB_M14A);
//					list.add(sFAB_M14B);
//					break;
//				}
//				case sFABSITE_M15 : {
//					list.add(sFAB_M15);
//					break;
//				}
//				case  sFABSITE_M11 : {
//					list.add(sFAB_M11A);
//					list.add(sFAB_M11B);
//					break;
//				}
//				case sFABSITE_C2 : {
//					list.add(sFAB_C2);
//					list.add(sFAB_C2F);
//					break;
//				}
//				case sFABSITE_IC : {
//					list.add(sFAB_M14A);
//					list.add(sFAB_M14B);
//					list.add(sFAB_M16);
//					break;
//				}
//			}
//		}
//		else
//		{
//			switch(fabSite) {
//				case sFABSITE_M14 : {
//					list.add(sFAB_M14);
//					break;
//				}
//				case sFABSITE_M15 : {
//					list.add(sFAB_M15);
//					break;
//				}
//				case  sFABSITE_M11 : {
//					list.add(sFAB_M11A);
//					list.add(sFAB_M11B);
//					break;
//				}
//				case sFABSITE_C2 : {
//					list.add(sFAB_C2);
//					list.add(sFAB_C2F);
//					break;
//				}
//				case sFABSITE_IC : {
//					list.add(sFAB_M14);
//					list.add(sFAB_M16);
//					break;
//				}
//			}
//		}
//		
//		return list;
//	}
//	
//	// 화면로당시 기본체크되는 fab 
//	public static List<String> getBasicFabList(String menu, String fabSite){
//		List<String> list = new ArrayList<String>();
//		if(menu.equals("tot") || menu.equals("tran"))
//		{
//			switch(fabSite) {				
//				case sFABSITE_M14 : {
//					list.add(sFAB_M14A);
//					list.add(sFAB_M14B);
//					break;
//				}
//				case sFABSITE_M15 : {
//					list.add(sFAB_M15);
//					break;
//				}
//				case  sFABSITE_M11 : {
//					list.add(sFAB_M11A);
//					list.add(sFAB_M11B);
//					break;
//				}
//				case sFABSITE_C2 : {
//					list.add(sFAB_C2);
//					list.add(sFAB_C2F);
//					break;
//				}
//				case sFABSITE_IC : {
//					list.add(sFAB_M14A);
//					list.add(sFAB_M14B);
//					//list.add(sFAB_M16);
//					break;
//				}
//			}
//		}
//		else
//		{
//			switch(fabSite) {				
//				case sFABSITE_M14 : {
//					list.add(sFAB_M14);
//					break;
//				}
//				case sFABSITE_M15 : {
//					list.add(sFAB_M15);
//					break;
//				}
//				case  sFABSITE_M11 : {
//					list.add(sFAB_M11A);
//					list.add(sFAB_M11B);
//					break;
//				}
//				case sFABSITE_C2 : {
//					list.add(sFAB_C2);
//					list.add(sFAB_C2F);
//					break;
//				}
//				case sFABSITE_IC : {
//					list.add(sFAB_M14);
//					//list.add(sFAB_M16);
//					break;
//				}
//			}
//		}
//		
//		return list;
//	}
//	
//	/*
//	 * 생성일 : 2021. 04. 01, 강병민
//	 * 함수명 : getColumnFromFab
//	 * 파라미터 : String fabSite, String fab
//	 * fabSite : Fab Site
//	 */
//	public static String getColumnFromFab(String fabSite, String fab) {
//				
//		switch(fabSite) {
//			case sFABSITE_M14 : {
//				if(fab.equals(sFAB_M14A)) {
//					return sComma + sDoubleQuotation + sFAB_M14A + sDoubleQuotation;
//				}else if (fab.equals(sFAB_M14B)) {
//					return sComma + sDoubleQuotation + sFAB_M14B + sDoubleQuotation;
//				}else if (fab.equals(sFAB_M14)) {
//					return sComma + sDoubleQuotation + sFAB_M14 + sAsterisk + sDoubleQuotation;
//				}				
//			}
//			case sFABSITE_M15 : {
//				return sComma + sDoubleQuotation + sFAB_M15 + sAsterisk + sDoubleQuotation;
//			}
//			case sFABSITE_M11 : {
//				if(fab.equals(sFAB_M11A)) {
//					return sComma + sDoubleQuotation + sFAB_M11A + sDoubleQuotation;
//				}else if (fab.equals(sFAB_M11B)) {
//					return sComma + sDoubleQuotation + sFAB_M11B + sDoubleQuotation;
//				}else if (fab.equals(sFAB_M11)) {
//					return sComma + sDoubleQuotation + sFAB_M11 + sAsterisk + sDoubleQuotation;
//				}
//			}
//			case sFABSITE_C2 : {
//				if(fab.equals(sFAB_C2)) {
//					return sComma + sDoubleQuotation + sFAB_C2 + sDoubleQuotation;
//				}else if (fab.equals(sFAB_C2F)) {
//					return sComma + sDoubleQuotation + sFAB_C2F + sDoubleQuotation;
//				}
//			}
//			case sFABSITE_IC : {				
//				if(fab.equals(sFAB_M14A)) {
//					return sComma + sDoubleQuotation + sFAB_M14A + sDoubleQuotation;
//				}else if (fab.equals(sFAB_M14B)) {
//					return sComma + sDoubleQuotation + sFAB_M14B + sDoubleQuotation;
//				}else if (fab.equals(sFAB_M14)) {
//					return sComma + sDoubleQuotation + sFAB_M14 + sAsterisk + sDoubleQuotation;
//				}else if(fab.equals(sFAB_M16A)) {
//					return sComma + sDoubleQuotation + sFAB_M16A + sDoubleQuotation;
//				}else if (fab.equals(sFAB_M16E)) {
//					return sComma + sDoubleQuotation + sFAB_M16E + sDoubleQuotation;
//				}else if (fab.equals(sFAB_M16)) {
//					return sComma + sDoubleQuotation + sFAB_M16 + sAsterisk + sDoubleQuotation;	
//				}
//			}
//			default : return null;
//		}
//	}
//
//	/*
//	 * X0122410
//	 * 현재 Locate 가져오기
//	 */
//	public static Locale getLocale() {
//		 return LocaleContextHolder.getLocale();
//	 }
//	
//	//M11,M14,M15,M16 > FAB_A/B/C 로 변환
////	public static String getFabABC(String menu, String fabSite, String fab){
////		String _fab = null;
////		if(menu.equals("tot") || menu.equals("tran"))
////		{
////			switch(fabSite) {
////				case sFABSITE_M14 : {
////					if(fab.equals(sFAB_M14A)) {
////						_fab = "FAB_A";
////					}else if (fab.equals(sFAB_M14B)) {
////						_fab = "FAB_B";
////					}
////					break;
////				}
////				case sFABSITE_M15 : {
////					_fab = "FAB_A";		
////					break;
////				}
////				case  sFABSITE_M11 : {
////					if(fab.equals(sFAB_M11A)) {
////						_fab = "FAB_A";
////					}else if (fab.equals(sFAB_M11B)) {
////						_fab = "FAB_B";
////					}
////					break;
////				}
////				case sFABSITE_C2 : {
////					if(fab.equals(sFAB_C2)) {
////						_fab = "FAB_A";
////					}else if (fab.equals(sFAB_C2F)) {
////						_fab = "FAB_B";
////					}
////					break;
////				}
////				case sFABSITE_IC : {
////					if(fab.equals(sFAB_M14A)) {
////						_fab = "FAB_A";
////					}else if (fab.equals(sFAB_M14B)) {
////						_fab = "FAB_B";
////					}else if (fab.equals(sFAB_M16)) {
////						_fab = "FAB_C";
////					}
////					break;
////				}
////			}
////		}
////		else
////		{
////			switch(fabSite) {
////				case sFABSITE_M14 : {
////					_fab = "FAB_A";
////					break;
////				}
////				case sFABSITE_M15 : {
////					_fab = "FAB_A";
////					break;
////				}
////				case  sFABSITE_M11 : {
////					if(fab.equals(sFAB_M11A)) {
////						_fab = "FAB_A";
////					}else if (fab.equals(sFAB_M11B)) {
////						_fab = "FAB_B";
////					}
////					break;
////				}
////				case sFABSITE_C2 : {
////					if(fab.equals(sFAB_C2)) {
////						_fab = "FAB_A";
////					}else if (fab.equals(sFAB_C2F)) {
////						_fab = "FAB_B";
////					}
////					break;
////				}
////				case sFABSITE_IC : {
////					if(fab.equals(sFAB_M14)) {
////						_fab = "FAB_A";
////					}else if (fab.equals(sFAB_M16)) {
////						_fab = "FAB_B";
////					}
////					break;
////				}
////			}
////		}
////		return _fab;
////	}
//}
