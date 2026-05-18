package com.skhynix.smartatlas.comm;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartfx.dataaccessfx.DataTable;
import com.skhynix.smartfx.dataaccessfx.QueryExecutorFactory;

public class OracleAPI {
	public static Logger logger = LoggerFactory.getLogger(OracleAPI.class);
		
	public static DataTable select(String connectionID, String mybatisID) {
		try (var executor = QueryExecutorFactory.build(connectionID)) {
			return executor.selectDataTable(mybatisID);
		} catch (Exception e) {
			return null;
		}
	}
	
	public static int insert(String connectionID, String mybatisID) {
		try (var executor = QueryExecutorFactory.build(connectionID)) {
			return executor.insert(mybatisID);
		} catch (Exception e) {
			return -1;
		}
	}
	
	public static int delete(String connectionID, String mybatisID) {
		try (var executor = QueryExecutorFactory.build(connectionID)) {
			return executor.delete(mybatisID);
		} catch (Exception e) {
			return -1;
		}
	}
	
}
