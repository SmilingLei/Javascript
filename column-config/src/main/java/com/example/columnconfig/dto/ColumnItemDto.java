package com.example.columnconfig.dto;

public class ColumnItemDto {

    private String columnName;
    private String label;
    private Integer width;
    private Integer order;
    private Boolean display;
    private Boolean configurable;

    public ColumnItemDto() {
    }

    public ColumnItemDto(String columnName, String label, Integer width, Integer order) {
        this.columnName = columnName;
        this.label = label;
        this.width = width;
        this.order = order;
    }

    public String getColumnName() {
        return columnName;
    }

    public void setColumnName(String columnName) {
        this.columnName = columnName;
    }

    public String getLabel() {
        return label;
    }

    public void setLabel(String label) {
        this.label = label;
    }

    public Integer getWidth() {
        return width;
    }

    public void setWidth(Integer width) {
        this.width = width;
    }

    public Integer getOrder() {
        return order;
    }

    public void setOrder(Integer order) {
        this.order = order;
    }

    public Boolean getDisplay() {
        return display;
    }

    public void setDisplay(Boolean display) {
        this.display = display;
    }

    public Boolean getConfigurable() {
        return configurable;
    }

    public void setConfigurable(Boolean configurable) {
        this.configurable = configurable;
    }
}
