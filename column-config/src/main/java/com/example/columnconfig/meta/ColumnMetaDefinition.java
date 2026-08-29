package com.example.columnconfig.meta;

public class ColumnMetaDefinition {

    private final String columnName;
    private final String label;
    private final boolean display;
    private final boolean configurable;
    private final int defaultWidth;
    private final int defaultOrder;

    public ColumnMetaDefinition(String columnName,
                                String label,
                                boolean display,
                                boolean configurable,
                                int defaultWidth,
                                int defaultOrder) {
        this.columnName = columnName;
        this.label = label;
        this.display = display;
        this.configurable = configurable;
        this.defaultWidth = defaultWidth;
        this.defaultOrder = defaultOrder;
    }

    public String getColumnName() {
        return columnName;
    }

    public String getLabel() {
        return label;
    }

    public boolean isDisplay() {
        return display;
    }

    public boolean isConfigurable() {
        return configurable;
    }

    public int getDefaultWidth() {
        return defaultWidth;
    }

    public int getDefaultOrder() {
        return defaultOrder;
    }
}
