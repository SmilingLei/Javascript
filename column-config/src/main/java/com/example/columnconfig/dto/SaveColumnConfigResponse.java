package com.example.columnconfig.dto;

public class SaveColumnConfigResponse {

    private String configUuid;
    private boolean created;
    private int columnCount;

    public SaveColumnConfigResponse() {
    }

    public SaveColumnConfigResponse(String configUuid, boolean created, int columnCount) {
        this.configUuid = configUuid;
        this.created = created;
        this.columnCount = columnCount;
    }

    public String getConfigUuid() {
        return configUuid;
    }

    public void setConfigUuid(String configUuid) {
        this.configUuid = configUuid;
    }

    public boolean isCreated() {
        return created;
    }

    public void setCreated(boolean created) {
        this.created = created;
    }

    public int getColumnCount() {
        return columnCount;
    }

    public void setColumnCount(int columnCount) {
        this.columnCount = columnCount;
    }
}
