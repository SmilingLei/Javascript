package com.example.columnconfig.dto;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

import java.util.ArrayList;
import java.util.List;

public class SaveColumnConfigRequest {

    @NotBlank
    private String moduleMark;

    private String configName;

    @NotNull
    @Valid
    private List<SaveColumnItem> columns = new ArrayList<>();

    public String getModuleMark() {
        return moduleMark;
    }

    public void setModuleMark(String moduleMark) {
        this.moduleMark = moduleMark;
    }

    public String getConfigName() {
        return configName;
    }

    public void setConfigName(String configName) {
        this.configName = configName;
    }

    public List<SaveColumnItem> getColumns() {
        return columns;
    }

    public void setColumns(List<SaveColumnItem> columns) {
        this.columns = columns;
    }

    public static class SaveColumnItem {

        @NotBlank
        private String columnName;

        private Integer width;

        public String getColumnName() {
            return columnName;
        }

        public void setColumnName(String columnName) {
            this.columnName = columnName;
        }

        public Integer getWidth() {
            return width;
        }

        public void setWidth(Integer width) {
            this.width = width;
        }
    }
}
