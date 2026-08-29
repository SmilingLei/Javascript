package com.example.columnconfig.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;

import java.time.LocalDateTime;

@Entity
@Table(name = "config_column_detail")
public class ConfigColumnDetail {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "C_configColumn_id", length = 64, nullable = false)
    private String configColumnId;

    @Column(name = "C_column_Name", length = 128, nullable = false)
    private String columnName;

    @Column(name = "C_arrange_order", nullable = false)
    private Integer arrangeOrder;

    @Column(name = "C_column_width")
    private Integer columnWidth;

    @Column(name = "C_create_time", nullable = false)
    private LocalDateTime createTime;

    @Column(name = "C_modify_time", nullable = false)
    private LocalDateTime modifyTime;

    @PrePersist
    public void prePersist() {
        LocalDateTime now = LocalDateTime.now();
        if (createTime == null) {
            createTime = now;
        }
        modifyTime = now;
    }

    @PreUpdate
    public void preUpdate() {
        modifyTime = LocalDateTime.now();
    }

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getConfigColumnId() {
        return configColumnId;
    }

    public void setConfigColumnId(String configColumnId) {
        this.configColumnId = configColumnId;
    }

    public String getColumnName() {
        return columnName;
    }

    public void setColumnName(String columnName) {
        this.columnName = columnName;
    }

    public Integer getArrangeOrder() {
        return arrangeOrder;
    }

    public void setArrangeOrder(Integer arrangeOrder) {
        this.arrangeOrder = arrangeOrder;
    }

    public Integer getColumnWidth() {
        return columnWidth;
    }

    public void setColumnWidth(Integer columnWidth) {
        this.columnWidth = columnWidth;
    }

    public LocalDateTime getCreateTime() {
        return createTime;
    }

    public void setCreateTime(LocalDateTime createTime) {
        this.createTime = createTime;
    }

    public LocalDateTime getModifyTime() {
        return modifyTime;
    }

    public void setModifyTime(LocalDateTime modifyTime) {
        this.modifyTime = modifyTime;
    }
}
