package com.example.columnconfig.dto;

import java.util.ArrayList;
import java.util.List;

public class ColumnFieldsResponse {

    private List<ColumnItemDto> allFields = new ArrayList<>();
    private List<ColumnItemDto> selected = new ArrayList<>();

    public List<ColumnItemDto> getAllFields() {
        return allFields;
    }

    public void setAllFields(List<ColumnItemDto> allFields) {
        this.allFields = allFields;
    }

    public List<ColumnItemDto> getSelected() {
        return selected;
    }

    public void setSelected(List<ColumnItemDto> selected) {
        this.selected = selected;
    }
}
