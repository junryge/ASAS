package com.skhynix.smartatlas;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.skhynix.smartatlas.environment.Env;
import com.skhynix.smartatlas.service.BizDataInitializer;
import com.skhynix.smartatlas.service.UiLogpresso;
import com.skhynix.smartfx.launcher.api.LauncherContext;
import com.skhynix.smartfx.launcher.api.LauncherEventListenerSupport;
import com.skhynix.smartfx.server.api.BizExecutionContext;

public class LauncherListener extends LauncherEventListenerSupport {
	private final Logger logger = LoggerFactory.getLogger(getClass());
	
	@Override
	protected void onStarted(LauncherContext context) {
		super.onStarted(context);
		logger.debug("************** LauncherListener Started!! **************");
		Env.initialize();
		UiLogpresso.initialize();
		
		var beanFactory = BizExecutionContext.beanFactory();
		beanFactory.getBean("USER_IF_LOG");
		
		new BizDataInitializer().initialization();
		
		logger.info("************** Bean Created!! **************");
	}
}
