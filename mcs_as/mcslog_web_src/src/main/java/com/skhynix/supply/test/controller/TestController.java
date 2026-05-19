package com.skhynix.supply.test.controller;

import java.util.Locale;

import javax.servlet.http.HttpServletRequest;

import org.apache.commons.logging.Log;
import org.apache.commons.logging.LogFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.MessageSource;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;
import org.springframework.web.servlet.i18n.SessionLocaleResolver;

import com.skhynix.supply.common.Common;
//import com.skhynix.supply.common.ThreadPool;
import com.skhynix.supply.tot.controller.TotalController;

/*
 * @Package Name : com.skhynix.supply.test.controller
 * @FileName : TestController.java
 * @작성일 : 2021. 10. 7.
 * @작성자 : 강병민
 * @프로그램 설명 : test 로그 조회 Controller
 */
@Controller
public class TestController {
	
	protected Log log = LogFactory.getLog(TestController.class);
	
	@Autowired
    SessionLocaleResolver localeResolver;
	
	@Autowired
    MessageSource messageSource;
	
	private static final org.slf4j.Logger logger = org.slf4j.LoggerFactory.getLogger(TotalController.class);	
    
    @RequestMapping(value = "/i18n.do", method = RequestMethod.GET) 
    public String i18n(Locale locale, HttpServletRequest request, Model model) 
    { 
    	log.info("i18n : Start!!!");
    	// RequestMapingHandler로 부터 받은 Locale 객체를 출력해 봅니다.
    	logger.info("Welcome i18n! The client locale is {}.", locale);
    	// localeResolver 로부터 Locale 을 출력해 봅니다.
    	logger.info("Session locale is {}.", localeResolver.resolveLocale(request));
    	logger.info("site.title : {}", messageSource.getMessage("site.title", null, "default text", locale));
    	logger.info("site.count : {}", messageSource.getMessage("site.count", new String[] {"첫번째"}, "default text", locale));
    	logger.info("not.exist : {}", messageSource.getMessage("not.exist", null, "default text", locale));
    	//logger.info("not.exist 기본값 없음 : {}", messageSource.getMessage("not.exist", null, locale));
    	// JSP 페이지에서 EL 을 사용해서 arguments 를 넣을 수 있도록 값을 보낸다.
    	model.addAttribute("siteCount", messageSource.getMessage("msg.first", null, locale));
    	model.addAttribute("siteLang", Common.getLocale());
    	
    	log.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
		logger.info("Welcome i18n! The client locale is {}.", Common.getLocale());
		logger.info("Session locale is {}.", localeResolver.resolveLocale(request));
		log.info("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$");
		
    	return "i18n";    	
    }
    
    @RequestMapping(value = "/monitoring.do", method = RequestMethod.GET) 
    public String monitoring(Locale locale, HttpServletRequest request, Model model) 
    { 
    	log.info("monitoring : Start!!!");
    	
    	return "monitoring";    	
    }
    
    @RequestMapping(value = "/tmp.do", method = RequestMethod.GET) 
    public String tmp(Locale locale, HttpServletRequest request, Model model) 
    { 
    	log.info("tmp : Start!!!");
    	
//    	HttpSession    session     = request.getSession();
//
//    	for(int i=0;i<20;i++)
//    	{
//    		// Callable
//    		Future<List<Map>> future = ThreadPool.getInstance().executor.submit(new Callable<List<Map>>() {
//    	        public List<Map> call() throws Exception {
//    	        
//    	        	log.info("Session ID : " + session.getId() + ",   Current Thread Name : " + Thread.currentThread().getName());
//    	        	
//    	        	Thread.sleep(1*1000);
//    	        	
//    	    		return null;	    		
//    	        }
//    	    });
//    	    
//    		try {		    	
//    		    List<Map> x = future.get();		        
//    		} catch (Exception e) {
//    			// Exception Handling
//    			return null;
//    		}	
//    	}
    	
    	return "tmp";    	
    }
}
