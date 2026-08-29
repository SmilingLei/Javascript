package com.example.columnconfig.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;

import java.time.LocalDateTime;

@Entity
@Table(
        name = "config_column",
        uniqueConstraints = @UniqueConstraint(
                name = "uk_config_column_user_module_range",
                columnNames = {"C_owning_user", "C_module_mark", "C_range"}
        )
)
public class ConfigColumn {

    public static final String RANGE_USER = "USER";

    @Id
    @Column(name = "C_UUID", length = 64, nullable = false)
    private String uuid;

    @Column(name = "C_configName", length = 128, nullable = false)
    private String configName;

    @Column(name = "C_range", length = 32, nullable = false)
    private String range;

    @Column(name = "C_owning_user", length = 64, nullable = false)
    private String owningUser;

    @Column(name = "C_module_mark", length = 64, nullable = false)
    private String moduleMark;

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

    public String getUuid() {
        return uuid;
    }

    public void setUuid(String uuid) {
        this.uuid = uuid;
    }

    public String getConfigName() {
        return configName;
    }

    public void setConfigName(String configName) {
        this.configName = configName;
    }

    public String getRange() {
        return range;
    }

    public void setRange(String range) {
        this.range = range;
    }

    public String getOwningUser() {
        return owningUser;
    }

    public void setOwningUser(String owningUser) {
        this.owningUser = owningUser;
    }

    public String getModuleMark() {
        return moduleMark;
    }

    public void setModuleMark(String moduleMark) {
        this.moduleMark = moduleMark;
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
