package com.skhynix.smartatlas.data;

import java.util.Map;

public class TibrvSendMsg {
    String key;
    String type;
    Map<String, Object> data;
    SEND_MSG_FORMAT format = SEND_MSG_FORMAT.XML;

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
    
    public TibrvSendMsg(
            String tibrvKey,
            String type,
            SEND_MSG_FORMAT format,
            Map<String, Object> data
    ) {
        super();
        this.key = tibrvKey;
        this.type = type;
        this.format = format;
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
    
    public SEND_MSG_FORMAT getFormat() {
        return format;
    }
    
    public enum SEND_MSG_FORMAT{JSON, XML}
}
