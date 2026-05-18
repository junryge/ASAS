package com.skhynix.smartatlas.data;

import com.skhynix.smartatlas.map.edge.RailEdge;
import com.skhynix.smartatlas.service.TibrvService.*;
import com.skhynix.smartatlas.util.DataService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;
import java.util.stream.Collectors;

public class RailCutRecordItem {
	private final Logger logger = LoggerFactory.getLogger(getClass());

	private final String id;	// {fabId}:{startAddress}-{endAddress}
	private final String fabId;
	private final String facId;
	private final String mcpName;
	private final String deviceId;
	private final Date eventDateTime;
	private final int railCutFromAddress;
	private final int railCutToAddress;
	private Set<String> affectedAddress;
	private List<String> affectedPort;
	private String state;
	private final String railEdgeId;
	private boolean isModified;

	public RailCutRecordItem (
			String id,
			String fabId,
			String facId,
			String mcpName,
			String deviceId,
			String railEdgeId,
			int railCutFromAddress,
			int railCutToAddress,
			Set<String> affectedAddress,
			List<String> affectedPort,
			String state,
			boolean isModified
	) {
		this.id			= id;
		this.fabId		= fabId;
		this.facId		= facId;
		this.mcpName	= mcpName;
		this.deviceId	= deviceId;
		this.railEdgeId = railEdgeId;
		this.railCutFromAddress	= railCutFromAddress;
		this.railCutToAddress	= railCutToAddress;
		this.affectedAddress = affectedAddress;
		this.affectedPort = affectedPort;
		this.state		= state;
		this.eventDateTime = new Date();
		this.isModified = isModified;
	}

	public void setState (String state) {
		this.state = state;
	}

	public void setAffectedAddress(Set<String> affectedAddress) {
		this.affectedAddress = affectedAddress;
	}

	public void setAffectedPort(List<String> affectedPort) {
		this.affectedPort = affectedPort;
	}

	public String getFabId () {
		return fabId;
	}

	public String getFacId () {
		return facId;
	}

	public Set<String> getAffectedAddress() {
		return affectedAddress;
	}

	public List<String> getAffectedPort() {
		return affectedPort;
	}

	public String getAffectedAddressString () {
		if (this.affectedAddress == null || this.affectedAddress.isEmpty()) return "";

		return affectedAddress.stream()
				.filter(address -> !address.isEmpty())
				.collect(Collectors.joining(","));
	}

	public String getAffectedPortString () {
		if (this.affectedPort == null || this.affectedPort.isEmpty()) return "";

		return affectedPort.stream()
				.filter(port -> !port.isEmpty())
				.collect(Collectors.joining(","));
	}

	public String getState () {
		return state;
	}

	public String getRailEdgeId () {
		return railEdgeId;
	}

	public RailEdge getRailEdge () {
		RailEdge railEdge = null;
		String railEdgeId;

		FabProperties fabProperties = DataService.getInstance().getFabPropertiesMap().get(fabId);

		if (fabProperties != null) {
			railEdgeId = DataSet.address2RailEdgeId(this.fabId, this.mcpName, this.railCutFromAddress, this.railCutToAddress);

			if (DataService.getDataSet().getRailEdgeMap() != null && DataService.getDataSet().getRailEdgeMap().containsKey(railEdgeId)) {
				railEdge = DataService.getDataSet().getRailEdgeMap().get(railEdgeId);
			} else {
				logger.warn("... not matching the railEdgeId [railEdgeId: {}]", railEdgeId);
			}
		}

		return railEdge;
	}

	public String getId () {
		return id;
	}

	public boolean getModify() {
		return isModified;
	}

	public void setModify(boolean isModified) {
		this.isModified = isModified;
	}

	public String getAlarmType () {
		return SEND_SUB_SUBJECT.RAIL_CUT;
	}

	public String getDeviceId () {
		return deviceId;
	}

	public Date getEventDateTime () {
		return eventDateTime;
	}

	public String getEventDateTimeString () {
		SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

		return dateFormat.format(this.eventDateTime);
	}

	public Integer getRailCutFromAddress () {
		return railCutFromAddress;
	}

	public Integer getRailCutToAddress () {
		return railCutToAddress;
	}

	public String getMcpName () {
		return mcpName;
	}
}