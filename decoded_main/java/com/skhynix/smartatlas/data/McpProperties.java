package com.skhynix.smartatlas.data;

import com.skhynix.smartatlas.data.raw.Mcp75Config;

public class McpProperties {
	String mcpName 			= "";
	String daemon 			= "";
	String subject 			= "";
	String ip 				= "";
	int port 				= -1;	
	String ftpIp 			= "";
	String ftpUser 			= "";
	String ftpPassword 		= "";
	String ftpLaneCutPath 	= "";
	String ftpMcp75Path 	= "";
	String ftpStationPath 	= "";
//	String ftpRoutePath 	= "";
	String ftpLayoutPath 	= "";
	Mcp75Config mcp75Config	= null;
	public McpProperties() {}

//	public McpProperties(
//							String mcpName,
//							String daemon,
//							String subject,
//							String ip,
//							int port,
//							String ftpIp,
//							String ftpUser,
//							String ftpPassword,
//							String ftpLaneCutPath,
//							String ftpMcp75Path,
//							String ftpStationPath,
//							String ftpRoutePath,
//							String ftpLayoutPath,
//							Mcp75Config mcp75Config
//	) {
//		super();
//
//		this.mcpName 		= mcpName;
//		this.daemon 		= daemon;
//		this.subject 		= subject;
//		this.ip 			= ip;
//		this.port 			= port;
//		this.ftpIp 			= ftpIp;
//		this.ftpUser 		= ftpUser;
//		this.ftpPassword 	= ftpPassword;
//		this.ftpLaneCutPath = ftpLaneCutPath;
//		this.ftpMcp75Path 	= ftpMcp75Path;
//		this.ftpStationPath = ftpStationPath;
//		this.ftpRoutePath 	= ftpRoutePath;
//		this.ftpLayoutPath 	= ftpLayoutPath;
//		this.mcp75Config 	= mcp75Config;
//	}

	public String getDaemon() {
		return daemon;
	}

	public void setDaemon(String daemon) {
		this.daemon = daemon;
	}

	public String getSubject() {
		return subject;
	}

	public void setSubject(String subject) {
		this.subject = subject;
	}

	public String getIp() {
		return ip;
	}

	public void setIp(String ip) {
		this.ip = ip;
	}

	public int getPort() {
		return port;
	}

	public void setPort(int port) {
		this.port = port;
	}

	public String getFtpIp() {
		return ftpIp;
	}

	public void setFtpIp(String ftpIp) {
		this.ftpIp = ftpIp;
	}

	public String getFtpUser() {
		return ftpUser;
	}

	public void setFtpUser(String ftpUser) {
		this.ftpUser = ftpUser;
	}

	public String getFtpPassword() {
		return ftpPassword;
	}

	public void setFtpPassword(String ftpPassword) {
		this.ftpPassword = ftpPassword;
	}

	public String getFtpLaneCutPath() {
		return ftpLaneCutPath;
	}

	public void setFtpLaneCutPath(String ftpLaneCutPath) {
		this.ftpLaneCutPath = ftpLaneCutPath;
	}

	public String getFtpMcp75Path() {
		return ftpMcp75Path;
	}

	public void setFtpMcp75Path(String ftpMcp75Path) {
		this.ftpMcp75Path = ftpMcp75Path;
	}

	public String getFtpStationPath() {
		return ftpStationPath;
	}

	public void setFtpStationPath(String ftpStationPath) {
		this.ftpStationPath = ftpStationPath;
	}

//	public String getFtpRoutePath() {
//		return ftpRoutePath;
//	}
//
//	public void setFtpRoutePath(String ftpRoutePath) {
//		this.ftpRoutePath = ftpRoutePath;
//	}

	public String getFtpLayoutPath() {
		return ftpLayoutPath;
	}

	public void setFtpLayoutPath(String ftpLayoutPath) {
		this.ftpLayoutPath = ftpLayoutPath;
	}

	public Mcp75Config getMcp75Config() {
		return mcp75Config;
	}

	public void setMcp75Config(Mcp75Config mcp75Config) {
		this.mcp75Config = mcp75Config;
	}

	public String getMcpName() {
		return mcpName;
	}

	public void setMcpName(String mcpName) {
		this.mcpName = mcpName;
	}	
}