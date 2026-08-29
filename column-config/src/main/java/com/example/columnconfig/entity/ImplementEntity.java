package com.example.columnconfig.entity;

import com.example.columnconfig.annotation.ColumnMeta;
import com.example.columnconfig.annotation.ColumnModule;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.time.LocalDateTime;

/**
 * 贯彻表主表实体。可显示 / 可配置由 {@link ColumnMeta} 声明，不落配置库。
 */
@Entity
@Table(name = "implement_table")
@ColumnModule("implement_table")
public class ImplementEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ColumnMeta(label = "文件名称", display = true, configurable = true, defaultWidth = 160, defaultOrder = 1)
    @Column(name = "file_name")
    private String fileName;

    @ColumnMeta(label = "文件路径", display = true, configurable = true, defaultWidth = 240, defaultOrder = 2)
    @Column(name = "file_path")
    private String filePath;

    @ColumnMeta(label = "业务类型", display = true, configurable = true, defaultWidth = 120, defaultOrder = 3)
    @Column(name = "biz_type")
    private String bizType;

    @ColumnMeta(label = "创建时间", display = true, configurable = true, defaultWidth = 180, defaultOrder = 4)
    @Column(name = "created_at")
    private LocalDateTime createdAt;

    @ColumnMeta(label = "修改时间", display = true, configurable = true, defaultWidth = 180, defaultOrder = 5)
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @ColumnMeta(label = "内部备注", display = false, configurable = false, defaultWidth = 200, defaultOrder = 99)
    @Column(name = "inner_remark")
    private String innerRemark;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getFileName() {
        return fileName;
    }

    public void setFileName(String fileName) {
        this.fileName = fileName;
    }

    public String getFilePath() {
        return filePath;
    }

    public void setFilePath(String filePath) {
        this.filePath = filePath;
    }

    public String getBizType() {
        return bizType;
    }

    public void setBizType(String bizType) {
        this.bizType = bizType;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }

    public String getInnerRemark() {
        return innerRemark;
    }

    public void setInnerRemark(String innerRemark) {
        this.innerRemark = innerRemark;
    }
}
