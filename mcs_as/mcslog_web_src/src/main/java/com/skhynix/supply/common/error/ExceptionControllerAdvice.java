package com.skhynix.supply.common.error;

import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.servlet.ModelAndView;

/**
 * @Package Name   : com.skhynix.supply.common.error
 * @FileName   : ExceptionControllerAdvice.java
 * @작성일        : 2017. 3. 14. 
 * @작성자        :  박민호
 * @프로그램 설명 : Exception 처리(공통)
 */
@ControllerAdvice
public class ExceptionControllerAdvice {
	@ExceptionHandler(Exception.class)
	public ModelAndView exception(Exception e) {
		ModelAndView mav = new ModelAndView();
		mav.addObject("name", e.getClass().getSimpleName());
		mav.addObject("message", e.getMessage());
		e.printStackTrace();
		mav.setViewName("common/error/errorPage");
		return mav;
	}
}