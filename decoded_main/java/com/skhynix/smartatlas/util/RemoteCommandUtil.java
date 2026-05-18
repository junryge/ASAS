package com.skhynix.smartatlas.util;

import java.io.File;
import java.lang.ProcessBuilder.Redirect;
import java.util.Scanner;

public class RemoteCommandUtil {
	public static String execute(String ip, String serverID, String serverPassword, String command) throws Exception {
		return execute(ip, serverID, serverPassword, command, null);
	}
	
	public static String execute(String ip, String serverID, String serverPassword, String command,  String inputFile) throws Exception {
		var processBuilder = new ProcessBuilder("plink", "-ssh", serverID + "@" + ip, "-pw", serverPassword, "-batch", command)
				.redirectOutput(Redirect.PIPE)
				.redirectError(Redirect.PIPE);
		
		if (inputFile != null) {
			processBuilder = processBuilder.redirectInput(new File(inputFile));
		}
		
		var prs = processBuilder.start();
		var outputStream = new Scanner(prs.getInputStream());
		var line = "";
		
		try {
			while (outputStream.hasNextLine()) {
				line += outputStream.nextLine() + "\n";
			}
		} catch (Exception e) {
			throw e;
		} finally {
			outputStream.close();
		}
		
		return line;
	}
}
