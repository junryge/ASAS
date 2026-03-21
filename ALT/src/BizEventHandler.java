@Component
@Singleton
public class BizEventHandler implements ServiceInvokeEventHandler {
	private final Logger logger = LoggerFactory.getLogger(getClass()); 
	
	@Override
	public void beforeInvoke(ServiceInvokeData invokeData) {
		logger.debug("afterInvoke: " + invokeData.getServiceId());
	}

	@Override
	public void onSuccess(ServiceInvokeData invokeData, Object returnValue) {
		logger.debug("beforeInvoke: " + invokeData.getServiceId());
	}

	@Override
	public void onError(ServiceInvokeData invokeData, Throwable cause) {
		logger.debug("onError: " + invokeData.getServiceId());
	}

	@Override
	public void afterInvoke(ServiceInvokeData invokeData) {
		logger.debug("onSuccess: " + invokeData.getServiceId());
	}
}
