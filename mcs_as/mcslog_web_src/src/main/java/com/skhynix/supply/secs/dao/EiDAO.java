package com.skhynix.supply.secs.dao;

import java.util.List;
import java.util.Map;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.stereotype.Repository;

import com.skhynix.supply.common.DBManager;
//import com.skhynix.supply.common.ThreadPool;

/**
 * @Package Name   : com.skhynix.supply.secs.dao
 * @FileName   : EiDAO.java
 * @작성일        : 2020. 3. 25. 
 * @작성자        :  전현구
 * @프로그램 설명 : EI_CS_DS 로그 조회 DAO
 */

@Repository("eiDAO")
public class EiDAO {
	
	DBManager dbManager = null;

	Log log = LogFactory.getLog(EiDAO.class);
	
	public EiDAO() {
		
	}
	
	@SuppressWarnings("rawtypes")
	public List<Map> dbExecuteQuery(String fabSite, String queryStmt) throws Exception {
		// 2021.10.08	X0122410	ThreadPool 적용
//		DBManager dbManager = new DBManager();
//		return dbManager.executeQuery(queryStmt);
		
		dbManager = new DBManager(fabSite);
		List<Map> dataList = null;
		try {		
			dataList 	= this.dbManager.executeQuery(queryStmt);
		}
		catch (Exception ex) {
			log.warn("Problem occurred at executing operation :" + ex.getMessage());
		}
		finally {
			if (this.dbManager != null) { try { this.dbManager = null; } catch (Exception e) { } }
		}
		return dataList;
		
		// Callable
//	    Future<List<Map>> future = ThreadPool.getInstance().executor.submit(new Callable<List<Map>>() {
//	        public List<Map> call() throws Exception {
//	        	
////	        	log.info(" Current Thread Name : " + Thread.currentThread().getName());
//	        	
//	    		dbManager = new DBManager();
//	    		return dbManager.executeQuery(queryStmt);	    		
//	        }
//	    });
//	    
//	    try {
//	    	return future.get();
//	    } catch (Exception e) {
//	        // Exception Handling
//	    	log.warn("Problem occurred at executing operation :" + e.getMessage());
//	    	return null;
//	    }
//	    finally {
//			if (this.dbManager != null) { try { this.dbManager = null; } catch (Exception e) { } }
//		}
	}

	public void dbExecuteQueryStop() throws Exception {
		 try {
			 if (this.dbManager != null) {  
				 this.dbManager.executeQueryStop();  
			 }
		 }
		 catch (Exception ex) {
			log.warn("Problem occurred at executing operation :" + ex.getMessage());
		}
		finally {
			if (this.dbManager != null) { try { this.dbManager = null; } catch (Exception e) { } }
		}
	}
}
