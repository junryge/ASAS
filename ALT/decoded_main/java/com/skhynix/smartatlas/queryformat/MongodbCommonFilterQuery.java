package com.skhynix.smartatlas.queryformat;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.stream.Collectors;

import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.db.mongodb.MongodbQueryPool;
import com.skhynix.smartatlas.queryformat.type.ENUM_FULLTEXT_COND;
import com.skhynix.smartatlas.queryformat.type.ExtractCommonFilterResult;
import com.skhynix.smartatlas.queryformat.type.FormatQueryCondition;
import com.skhynix.smartatlas.queryformat.type.McslogTablesCollection;
import com.skhynix.smartatlas.util.JsonUtil;
import com.skhynix.smartatlas.util.QueryUtil;

public class MongodbCommonFilterQuery {
	private static final Logger logger = LoggerFactory.getLogger(MongodbCommonFilterQuery.class);

	public static List<ExtractCommonFilterResult> extractCommonFilterBody(
			String filterPropertiesJson, McslogTablesCollection tablesCollection, String queryName, Map<String, Object> lastKeys) {
		var queries = new ArrayList<ExtractCommonFilterResult>();
		Map<String, String> filterGroup;
		
		try {
			Map<String, Map<String, String>> filterProperties = JsonUtil.getMapMapFromJson(filterPropertiesJson);
			Map<String, FormatQueryCondition> conditions = new HashMap<>();
			Map<String, String> fabTablesMap = new HashMap<>();
			
			var site = "";
			var fabs = new ArrayList<String>();
			
			if (filterProperties.containsKey("McslogFab")) {
				filterGroup = filterProperties.get("McslogFab");
				
				site = filterGroup.get("Site");
				fabTablesMap = tablesCollection.get(site);
				
				for (String fab : filterGroup.get("Fabs").split(",")) {
					fabs.add(fab);
				}
			}
			
			if (filterProperties.containsKey("McslogTimeRange")) {
				filterGroup = filterProperties.get("McslogTimeRange");
				
				conditions.put("From", new FormatQueryCondition(
					QueryUtil.convertToUtcTimezone(filterGroup.get("DateTimeFrom")))
				);
				conditions.put("To", new FormatQueryCondition(
					QueryUtil.convertToUtcTimezone(filterGroup.get("DateTimeTo")))
				);
			}
			
			if (filterProperties.containsKey("McslogMachine")) {
				filterGroup = filterProperties.get("McslogMachine");
				
				conditions.put("MachineTypes", new FormatQueryCondition(
					String.join("','", filterGroup.get("MachineTypes").split(",")))
				);
				conditions.put("MachineNames", new FormatQueryCondition(
					String.join("','", filterGroup.get("MachineNames").split(","))
					, ENUM_FULLTEXT_COND.TRUE)
				);
			}
			
			if (filterProperties.containsKey("McslogMachineTransport")) {
				filterGroup = filterProperties.get("McslogMachineTransport");
				
				conditions.put("MachineTypesTransport", new FormatQueryCondition(
					String.join("','", filterGroup.get("MachineTypes").split(",")))
				);
				conditions.put("MachineNamesTransport", new FormatQueryCondition(
					String.join("','", filterGroup.get("MachineNames").split(","))
					, ENUM_FULLTEXT_COND.TRUE)
				);
			}
			
			if (filterProperties.containsKey("McslogMachineSource")) {
				filterGroup = filterProperties.get("McslogMachineSource");
				
				conditions.put("MachineTypesSource", new FormatQueryCondition(
					String.join("','", filterGroup.get("MachineTypes").split(",")))
				);
				conditions.put("MachineNamesSource", new FormatQueryCondition(
					String.join("','", filterGroup.get("MachineNames").split(","))
					, ENUM_FULLTEXT_COND.TRUE)
				);
			}
			
			if (filterProperties.containsKey("McslogMachineDest")) {
				filterGroup = filterProperties.get("McslogMachineDest");
				
				conditions.put("MachineTypesDest", new FormatQueryCondition(
					String.join("','", filterGroup.get("MachineTypes").split(",")))
				);
				conditions.put("MachineNamesDest", new FormatQueryCondition(
					String.join("','", filterGroup.get("MachineNames").split(","))
					, ENUM_FULLTEXT_COND.TRUE)
				);
			}
			
			if (filterProperties.containsKey("McslogAlarmReportLog")) {
				filterGroup = filterProperties.get("McslogAlarmReportLog");
				
				conditions.put("UnitName", new FormatQueryCondition(filterGroup.get("UnitName"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("AlarmID", new FormatQueryCondition(filterGroup.get("AlarmID"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("AlarmCode", new FormatQueryCondition(filterGroup.get("AlarmCode"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("AlarmText", new FormatQueryCondition(filterGroup.get("AlarmText"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("State", new FormatQueryCondition(filterGroup.get("State"), ENUM_FULLTEXT_COND.FALSE));
			}
			
			if (filterProperties.containsKey("McslogMaterialCarrierLocLog")) {
				filterGroup = filterProperties.get("McslogMaterialCarrierLocLog");
				
				conditions.put("CarrierName", new FormatQueryCondition(filterGroup.get("Carrier"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("LotID", new FormatQueryCondition(filterGroup.get("LotID"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("TransportCommandID", new FormatQueryCondition(filterGroup.get("CommandID"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("UnitName", new FormatQueryCondition(filterGroup.get("UnitName"), ENUM_FULLTEXT_COND.TRUE));
			}
			
			if (filterProperties.containsKey("McslogResourceMachineLog")) {
				filterGroup = filterProperties.get("McslogResourceMachineLog");
				
				conditions.put("State", new FormatQueryCondition(filterGroup.get("State"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("ConnectionState", new FormatQueryCondition(filterGroup.get("ConnectionState"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("ControlState", new FormatQueryCondition(filterGroup.get("ControlState"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("TSCState", new FormatQueryCondition(filterGroup.get("TSCState"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("ProcessingState", new FormatQueryCondition(filterGroup.get("ProcessingState"), ENUM_FULLTEXT_COND.TRUE));
			}
			
			if (filterProperties.containsKey("McslogResourcePortLog")) {
				filterGroup = filterProperties.get("McslogResourcePortLog");
				
				conditions.put("PortName", new FormatQueryCondition(filterGroup.get("PortName"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("State", new FormatQueryCondition(filterGroup.get("State"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("SubState", new FormatQueryCondition(filterGroup.get("SubState"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("ProcessingState", new FormatQueryCondition(filterGroup.get("ProcessingState"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("Banned", new FormatQueryCondition(filterGroup.get("Banned"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("InOutType", new FormatQueryCondition(filterGroup.get("InOutType"), ENUM_FULLTEXT_COND.FALSE));
				conditions.put("Manual", new FormatQueryCondition(filterGroup.get("Manual"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("AccessMode", new FormatQueryCondition(filterGroup.get("AccessMode"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("IdReadState", new FormatQueryCondition(filterGroup.get("IdReadState"), ENUM_FULLTEXT_COND.TRUE));
			}
			
			if (filterProperties.containsKey("McslogResourceShelfLog")) {
				filterGroup = filterProperties.get("McslogResourceShelfLog");
				
				conditions.put("ShelfName", new FormatQueryCondition(filterGroup.get("ShelfName"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("State", new FormatQueryCondition(filterGroup.get("State"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("ProcessingState", new FormatQueryCondition(filterGroup.get("ProcessingState"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("Banned", new FormatQueryCondition(filterGroup.get("Banned"), ENUM_FULLTEXT_COND.TRUE));
			}
			
			if (filterProperties.containsKey("McslogResourceCraneLog")) {
				filterGroup = filterProperties.get("McslogResourceCraneLog");
				
				conditions.put("CraneName", new FormatQueryCondition(filterGroup.get("CraneName"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("State", new FormatQueryCondition(filterGroup.get("State"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("SubState", new FormatQueryCondition(filterGroup.get("SubState"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("ProcessingState", new FormatQueryCondition(filterGroup.get("ProcessingState"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("TrCommand", new FormatQueryCondition(filterGroup.get("TrCommand"), ENUM_FULLTEXT_COND.TRUE));
			}
			
			if (filterProperties.containsKey("McslogResourceVehicleLog")) {
				filterGroup = filterProperties.get("McslogResourceVehicleLog");
				
				conditions.put("VehicleName", new FormatQueryCondition(filterGroup.get("VehicleName"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("State", new FormatQueryCondition(filterGroup.get("State"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("SubState", new FormatQueryCondition(filterGroup.get("SubState"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("ProcessingState", new FormatQueryCondition(filterGroup.get("ProcessingState"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("TrCommand", new FormatQueryCondition(filterGroup.get("TrCommand"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("Carrier", new FormatQueryCondition(filterGroup.get("Carrier"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("TransferPort", new FormatQueryCondition(filterGroup.get("TransferPort"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("IdReadState", new FormatQueryCondition(filterGroup.get("IdReadState"), ENUM_FULLTEXT_COND.FALSE));
			}
			
			if (filterProperties.containsKey("McslogResourceStorageLog")) {
				filterGroup = filterProperties.get("McslogResourceStorageLog");
				
				conditions.put("State", new FormatQueryCondition(filterGroup.get("State"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("FullState", new FormatQueryCondition(filterGroup.get("FullState"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("ProcessingState", new FormatQueryCondition(filterGroup.get("ProcessingState"), ENUM_FULLTEXT_COND.TRUE));
			}
			
			if (filterProperties.containsKey("McslogTransportReturnLog")) {
				filterGroup = filterProperties.get("McslogTransportReturnLog");
				
				conditions.put("CarrierName", new FormatQueryCondition(filterGroup.get("Carrier"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("LotID", new FormatQueryCondition(filterGroup.get("LotID"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("TransportJobID", new FormatQueryCondition(filterGroup.get("JobID"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("State", new FormatQueryCondition(filterGroup.get("State"), ENUM_FULLTEXT_COND.FALSE));
				
				if (filterGroup.get("CommandID") != null) {
					conditions.put("TransportCommandID", new FormatQueryCondition(filterGroup.get("CommandID"), ENUM_FULLTEXT_COND.TRUE));
				}
			}
			
			if (filterProperties.containsKey("McslogTransportReturnJobLog")) {
				filterGroup = filterProperties.get("McslogTransportReturnJobLog");
				
				conditions.put("CarrierName", new FormatQueryCondition(filterGroup.get("Carrier"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("LotID", new FormatQueryCondition(filterGroup.get("LotID"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("TransportJobID", new FormatQueryCondition(filterGroup.get("JobID"), ENUM_FULLTEXT_COND.TRUE));
			}
			
			if (filterProperties.containsKey("McslogTransportReturnCommandLog")) {
				filterGroup = filterProperties.get("McslogTransportReturnCommandLog");
				
				conditions.put("CarrierName", new FormatQueryCondition(filterGroup.get("Carrier"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("TransportCommandID", new FormatQueryCondition(filterGroup.get("CommandID"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("UnitNameSource", new FormatQueryCondition(filterGroup.get("SourceUnit"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("UnitNameDest", new FormatQueryCondition(filterGroup.get("DestUnit"), ENUM_FULLTEXT_COND.TRUE));
			}
			
			if (filterProperties.containsKey("McslogTransportReturnJobFailLog")) {
				filterGroup = filterProperties.get("McslogTransportReturnJobFailLog");
				
				conditions.put("CarrierName", new FormatQueryCondition(filterGroup.get("Carrier"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("LotID", new FormatQueryCondition(filterGroup.get("LotID"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("TransportJobID", new FormatQueryCondition(filterGroup.get("JobID"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("Reason", new FormatQueryCondition(
						String.join("','", filterGroup.get("Reason").split(","))
						, ENUM_FULLTEXT_COND.TRUE)
					);
			}
			
			if (filterProperties.containsKey("McslogTransportReturnCommandFailLog")) {
				filterGroup = filterProperties.get("McslogTransportReturnCommandFailLog");
				
				conditions.put("CarrierName", new FormatQueryCondition(filterGroup.get("Carrier"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("TransportCommandID", new FormatQueryCondition(filterGroup.get("CommandID"), ENUM_FULLTEXT_COND.TRUE));
				conditions.put("Reason", new FormatQueryCondition(
						String.join("','", filterGroup.get("Reason").split(","))
						, ENUM_FULLTEXT_COND.TRUE)
					);
			}
			
			if (filterProperties.containsKey("McslogTransportJobState")
					|| filterProperties.containsKey("McslogTransportCommandState")) {
				filterGroup = (Map<String, String>)Objects.requireNonNullElse(
						filterProperties.get("McslogTransportJobState"), filterProperties.get("McslogTransportCommandState"));
				
				conditions.put("States", new FormatQueryCondition(
					String.join("','", filterGroup.get("States").split(",")))
				);
			}
			
			if (filterProperties.containsKey("McslogTransportCompletedCarrierFromToLog")) {
				filterGroup = filterProperties.get("McslogTransportCompletedCarrierFromToLog");
				
				conditions.put("CarrierName", new FormatQueryCondition(filterGroup.get("Carrier"), ENUM_FULLTEXT_COND.TRUE));
			}
			
			for (String fab : fabs) {
				var args = new HashMap<String, Object>();
				var fulltext = String.join(" ", conditions.values().stream()
						.filter(x -> StringUtils.isNotEmpty(x.condition) && x.isFulltextCondition == ENUM_FULLTEXT_COND.TRUE)
						.map(x -> x.condition.trim().replace("'", "").replace(",", " "))
						.collect(Collectors.toList()));
				
				conditions.entrySet().forEach(x -> args.put(x.getKey(), x.getValue().toString()));
				
				args.put("FullText", fulltext);
				args.put("Collection", fabTablesMap.get(fab));
				args.put("Key", lastKeys == null || lastKeys.containsKey(fabTablesMap.get(fab)) == false ? "" : lastKeys.get(fabTablesMap.get(fab)));
				
				queries.add(new ExtractCommonFilterResult(site, fab, MongodbQueryPool.getQuery(queryName, args)));
			}
		} catch (Exception e) {
			logger.error("", e);
		}
		
		return queries;
	}
}