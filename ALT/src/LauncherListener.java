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
