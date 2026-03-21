public class Fio extends Eqp {
	public enum FIOTYPE{NORMAL, VM};
	
	private FIOTYPE fioType = FIOTYPE.NORMAL;
	
	public Fio(
				String fabId,
				String id, 
				String name, 
				Set<PROCESS_TYPE> processTypeSet, 
				ConcurrentLinkedQueue<String> portNodeIdList, 
				boolean isAvailable, 
				boolean isUpdate, 
				boolean isVm, 
				String mcsBayNm
	) {		
		super(fabId, id, name, EQP_TYPE.FIO, processTypeSet, portNodeIdList, isAvailable, isUpdate, mcsBayNm);
		
		if (isVm) {
			fioType = FIOTYPE.VM;
		}
	}
	
	public FIOTYPE getFioType() {
		return fioType;
	}
	
	public void setFioType(FIOTYPE fioType) {
		this.fioType = fioType;
	}
}
