public class TibrvSendMsg {
    String key;
    String type;
    Map<String, Object> data;

    public TibrvSendMsg(
            String tibrvKey,
            String type,
            Map<String, Object> data
    ) {
        super();
        this.key = tibrvKey;
        this.type = type;
        this.data = data;
    }

    public String getKey() {
        return key;
    }

    public String getType() {
        return type;
    }

    public Map<String, Object> getData() {
        return data;
    }
}
