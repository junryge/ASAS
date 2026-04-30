public class RailVibrationRecordItem {
	private final Logger logger = LoggerFactory.getLogger(getClass());

	private final String id;
	private final String fabId;
	private final String facId;
	private final double term1;	// (대조군) 현재 ~ 시간1(term1)
	private final double term2;	// (비교군) 시간1 ~ 시간2(term2)
	private final Date eventDateTime;
	private final int address;	// 이상 진동 발생지
	private Double x;
	private Double y;
	private Double z;
	private Double avgX;	// 비교군 x 평균값
	private Double avgY;	// 비교군 y 평균값
	private Double avgZ;	// 비교군 z 평균값
	private List<String> directory;	// 이상 현상 발생 방향 목록 (X -> Y -> Z 순)
	private String state;

	public RailVibrationRecordItem(
			String id,
			String fabId,
			String facId,
			int address,
			Double x,
			Double y,
			Double z,
			Double avgX,
			Double avgY,
			Double avgZ,
			double term1,
			double term2,
			List<String> directory,
			String state
	) {
		this.id			= id;
		this.fabId		= fabId;
		this.facId		= facId;
		this.address	= address;
		this.x 			= x;
		this.y 			= y;
		this.z 			= z;
		this.avgX 		= avgX;
		this.avgY 		= avgY;
		this.avgZ 		= avgZ;
		this.term1 		= term1;
		this.term2 		= term2;
		this.directory = directory;
		this.state		= state;
		this.eventDateTime = new Date();
	}

	public String getId () {
		return id;
	}

	public String getFabId () {
		return fabId;
	}

	public String getFacId () {
		return facId;
	}

	public int getAddress () {
		return address;
	}

	public String getAddressString() {
		return String.valueOf(address);
	}

	public Double getX () {
		return x;
	}

	public Double getY () {
		return y;
	}

	public Double getZ () {
		return z;
	}

	public String getAlarmType () {
		return SEND_SUB_SUBJECT.RAIL_VIBRATION;
	}

	public void setEachDirectoryForce(Double x, Double y, Double z) {
		this.x = x;
		this.y = y;
		this.z = z;
	}

	public void setAvgX(Double avgX) {
		this.avgX = avgX;
	}

	public void setAvgY(Double avgY) {
		this.avgY = avgY;
	}

	public void setAvgZ(Double avgZ) {
		this.avgZ = avgZ;
	}

	public Double getAvgX() {
		return avgX;
	}

	public Double getAvgY() {
		return avgY;
	}

	public Double getAvgZ() {
		return avgZ;
	}

	public String getState () {
		return state;
	}

	public Date getEventDateTime () {
		return eventDateTime;
	}

	public String getEventDateTimeString () {
		SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

		return dateFormat.format(this.eventDateTime);
	}

	public double getTerm1 () {
		return term1;
	}

	public double getTerm2 () {
		return term2;
	}

	public void setState (String state) {
		this.state = state;
	}

	public String getDeviceId () {
		return fabId;
	}

	public void setDirectory(String... directory) {
		if (!this.directory.isEmpty()) {
			this.directory = new ArrayList<>();
		}

		if (directory == null || directory.length == 0) {
			this.directory.add("N");
		} else {

			List<String> tmp = new ArrayList<>();

			for (String dir : directory) {
				if (dir != null && !dir.isEmpty() && !tmp.contains(dir)) {
					tmp.add(dir);
				}
			}

			if (!tmp.isEmpty()) {
				this.directory = tmp.stream()
						.sorted()
						.collect(Collectors.toList());
			}
		}
	}

	public String getUpDownRate() {
		List<Double> list1 = this.getEachGForce(false);
		List<Double> list2 = this.getEachGForce(true);
		List<String> temp = new ArrayList<>();

		for (int i = 0; i < list1.size(); i++) {
			Double num1 = list1.get(i);
			Double num2 = list2.get(i);
			double rate = (num1 - num2) / num2 * 100.0;

			// 소수점 둘째 첫째 반올림 처리
			rate = Math.round(rate * 10.0) / 10.0;

			temp.add(rate + "%");
		}

		return String.join(" / ", temp);
	}

	public String getTerm1EachGForce() {
		List<Double> list = this.getEachGForce(false);
		List<String> temp = new ArrayList<>();

		for (Double i : list) {
			if (i != null) {
				temp.add(i + "G");
			}
		}

		return String.join(" / ", temp);
	}

	public String getTerm2EachGForce() {
		List<Double> list = this.getEachGForce(true);
		List<String> temp = new ArrayList<>();

		for (Double i : list) {
			if (i != null) {
				temp.add(i + "G");
			}
		}

		return String.join(" / ", temp);
	}

	public List<Double> getEachGForce(boolean isAverage) {
		List<Double> result = new ArrayList<>();

		for (String dir : this.directory) {
			Double _t = this.getGForce(dir, isAverage);

			if (_t != null) {
				result.add(_t);
			}
		}

		return result;
	}

	public Double getGForce(String dir, boolean isAverage) {
		if (isAverage) {
			switch (dir) {
				case "X": {
					return avgX;
				}
				case "Y": {
					return avgY;
				}
				case "Z": {
					return avgZ;
				}
				default: {
					return null;
				}
			}
		} else {
			switch (dir) {
				case "X": {
					return x;
				}
				case "Y": {
					return y;
				}
				case "Z": {
					return z;
				}
				default: {
					return null;
				}
			}
		}
	}

	public List<String> getDirectory() {
		return directory;
	}

    public Logger getLogger() {
        return logger;
    }
}
