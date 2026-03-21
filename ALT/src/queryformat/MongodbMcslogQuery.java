public class MongodbMcslogQuery {

	public static String getSuffix(String fab) {
		fab = fab.toUpperCase();
		
		switch (fab) {
			case "ICPKT":
				return "icpkt";
			case "ICPNT":
				return "icpnt";
			case "NWT":
				return "nwt";
		}
		
		return "";
	}
}
